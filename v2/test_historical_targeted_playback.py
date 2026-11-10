#!/usr/bin/env python3
"""Grouped offline fixtures for bounded historical-only audio/video probes."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from historical_targeted_playback import (audit, find_exact_urls, probe_one,
                                         public_dns, load_missing_report)


def sha(url):
    return hashlib.sha256(url.encode()).hexdigest()


class HistoricalTargetedPlaybackTests(unittest.TestCase):
    def test_safe_host_rejects_private_dns_destinations(self):
        host = "https://stream.example.org/test.m3u8"
        private = lambda *args, **kwargs: [(0, 0, 0, "", ("10.12.4.5", 443))]
        public = lambda *args, **kwargs: [(0, 0, 0, "", ("8.8.8.8", 443))]
        self.assertFalse(public_dns(host, private))
        self.assertTrue(public_dns(host, public))

    def test_exact_genuine_sha_identity_matched_without_exporting_url(self):
        url = "https://stream.example.org/private-token.m3u8"
        identity = sha(url)
        results = audit({identity}, {identity: url},
                        runner=lambda command, **kwargs: subprocess.CompletedProcess(
                            command, 0, json.dumps({"streams": [
                                {"codec_type": "video"}, {"codec_type": "audio"}]}), ""),
                        resolver=lambda _: True)
        self.assertEqual(results["status_counts"], {"VIDEO_STREAM_OBSERVED": 1})
        self.assertTrue(results["results"][0]["video_stream"])
        self.assertNotIn(url, str(results))
        self.assertFalse(results["ibo_device_verified"])

    def test_failed_probe_not_declared_dead(self):
        url = "https://stream.example.org/bad.m3u8"
        result = probe_one((sha(url), url),
                           runner=lambda command, **kw: subprocess.CompletedProcess(command, 1, "", ""),
                           resolver=lambda _: True)
        self.assertEqual(result["status"], "PROBE_FAILED_NOT_PROVEN_DEAD")
        self.assertNotIn(url, str(result))

    def test_unsafe_error_text_is_never_reported(self):
        url = "https://stream.example.org/live.m3u8?token=PRIVATE"
        result = probe_one((sha(url), url),
                           runner=lambda cmd, **k: subprocess.CompletedProcess(
                               cmd, 1, "", "HTTP error 403 at " + url),
                           resolver=lambda _: True)
        self.assertEqual(result["status"], "PROBE_FAILED_NOT_PROVEN_DEAD")
        self.assertEqual(result["diagnostic_category"], "HTTP_FORBIDDEN")
        self.assertNotIn(url, str(result))
        self.assertNotIn("PRIVATE", str(result))

    def test_unrecognized_ffprobe_option_is_distinct_from_stream_death(self):
        url = "https://stream.example.org/live.m3u8"
        result = probe_one((sha(url), url),
                           runner=lambda cmd, **k: subprocess.CompletedProcess(
                               cmd, 1, "", "Unrecognized option 'max_redirects'"),
                           resolver=lambda _: True)
        self.assertEqual(result["diagnostic_category"], "FFPROBE_OPTION_UNSUPPORTED")

    def test_compatible_ffprobe_arguments_and_no_plaintext_log(self):
        url = "https://stream.example.org/safe.m3u8"
        called = []
        def fake_runner(args, **kwargs):
            called.extend(args)
            return subprocess.CompletedProcess(args, 0, json.dumps({"streams": [
                {"codec_type": "video"}]}), "")
        output = probe_one((sha(url), url), runner=fake_runner,
                           resolver=lambda _: True)
        self.assertEqual(output["status"], "VIDEO_STREAM_OBSERVED")
        self.assertNotIn("-max_redirects", called)
        self.assertNotIn("-nostdin", called)
        self.assertIn("-protocol_whitelist", called)
        self.assertNotIn(url, str(output))


    def test_bounded_public_compatibility_retry_can_recover_real_av(self):
        url = "https://stream.example.org/public.m3u8"
        attempts = []
        def run(args, **kwargs):
            attempts.append((args, kwargs["timeout"]))
            if len(attempts) == 1:
                return subprocess.CompletedProcess(args, 1, "", "HTTP error 403")
            return subprocess.CompletedProcess(args, 0,
                json.dumps({"streams": [{"codec_type": "video"}, {"codec_type": "audio"}]}), "")
        result = probe_one((sha(url), url), runner=run, resolver=lambda _: True)
        self.assertEqual(result["status"], "VIDEO_STREAM_OBSERVED")
        self.assertTrue(result["video_stream"] and result["audio_stream"])
        self.assertEqual(len(attempts), 2)
        self.assertIn("-user_agent", attempts[1][0])
        self.assertLessEqual(attempts[1][1], 35)
        self.assertNotIn(url, str(result))

    def test_authenticated_streams_are_not_bypassed_or_called_verified(self):
        url = "https://stream.example.org/restricted.m3u8"
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 1, "", "401 Unauthorized")
        result = probe_one((sha(url), url), runner=run, resolver=lambda _: True)
        self.assertEqual(result["diagnostic_category"], "AUTH_REQUIRED")
        self.assertFalse(result["video_stream"] or result["audio_stream"])
        self.assertEqual(len(calls), 1)

    def test_unresolved_host_does_not_invoke_media_process(self):
        url = "https://stream.example.org/bad.m3u8"
        called = []
        result = probe_one((sha(url), url), runner=lambda *args, **kwargs: called.append(args),
                           resolver=lambda _: False)
        self.assertEqual(result["status"], "UNSAFE_OR_UNRESOLVABLE_HOST")
        self.assertEqual(called, [])

    def test_missing_exact_git_identity_is_reported_without_guess(self):
        url = "https://stream.example.org/a.m3u8"
        identity = sha(url)
        report = audit({identity}, {}, resolver=lambda _: True)
        self.assertEqual(report["not_found_in_git_history_count"], 1)
        self.assertEqual(report["exact_git_history_urls_recovered"], 0)

    def test_git_history_exact_match_rejects_name_only_guess(self):
        url = "https://stream.example.org/actual.m3u8"
        identity = sha(url)
        with (patch("historical_targeted_playback.candidate_blobs",
                    return_value=([("a"*40, "old.m3u")], 0)),
              patch("historical_targeted_playback.git", return_value=b"example"),
              patch("historical_targeted_playback.iter_url_entries",
                    return_value=iter([{"url": url, "name": "unrelated"}]))):
            found, evidence = find_exact_urls({identity})
        self.assertEqual(found, {identity: url})
        self.assertEqual(evidence["oversized_git_blobs_skipped"], 0)

    def test_bounded_sample_accepted_when_total_missing_is_larger(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(__file__).resolve().parent
            baseline = root / "history/stage3-4955-hash-only.jsonl"
            identities = sorted(json.loads(line)["url_sha256"]
                                for line in baseline.read_text().splitlines() if line.strip())
            report_path = Path(folder) / "report.json"
            report_path.write_text(json.dumps({"source_content_audit": {
                "historical_identifiers_absent_from_current_sources": 31,
                "historical_identifiers_absent_sha256_sample": identities[:30]}}))
            self.assertEqual(load_missing_report(report_path, baseline), set(identities[:30]))

    def test_truncated_missing_report_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            report_path = Path(folder) / "report.json"
            report_path.write_text(json.dumps({"source_content_audit": {
                "historical_identifiers_absent_from_current_sources": 31,
                "historical_identifiers_absent_sha256_sample": []}}))
            root = Path(__file__).resolve().parent
            with self.assertRaisesRegex(ValueError, "truncated"):
                load_missing_report(report_path,
                                    root / "history/stage3-4955-hash-only.jsonl")


if __name__ == "__main__":
    unittest.main()
