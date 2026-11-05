#!/usr/bin/env python3
"""Offline grouped AV handoff tests; production only uses real ffprobe/ffmpeg."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from blocked_official_current_av import scan, validate
from blocked_official_source_handoff import SOURCES, TARGETS


def fixture():
    cfg = {"sources": [{"id": sid, "url": "https://example.org/" + sid + ".m3u"}
                       for sid in sorted(SOURCES)]}
    docs = {sid: "#EXTM3U\n" for sid in SOURCES}
    samples = [
        ("TRTSpor.tr", "TRT Spor"),
        ("TV100.tr", "TV 100"),
        ("BenguturkTV.tr", "Benguturk TV"),
        ("UlusalKanal.tr", "Ulusal Kanal"),
        ("HalkTV.tr", "Halk TV"),
    ]
    for index, (tvg, name) in enumerate(samples):
        sid = sorted(SOURCES)[index]
        docs[sid] += (f'#EXTINF:-1 tvg-id="{tvg}",{name}\n'
                      f'https://example.org/{index}.m3u8\n')
    return cfg, lambda url: docs[url.rsplit("/", 1)[-1].removesuffix(".m3u")]


def fake_probe(item):
    sha, url = item
    ok = url.endswith("/0.m3u8") or url.endswith("/1.m3u8")
    return {"url_sha256": sha, "status": "VIDEO_AUDIO_DECODED" if ok
            else "PROBE_FAILED_NETWORK_TIMEOUT",
            "video": ok, "audio": ok, "decoded": ok, "audio_lang_tags": []}


class BlockedOfficialCurrentAVTests(unittest.TestCase):
    def test_five_exact_channels_all_probed_two_decoded(self):
        config, reader = fixture()
        report, private = scan(config, reader=reader, prober=fake_probe, workers=3)
        self.assertEqual(report["pages_with_exact_source_candidates"], len(TARGETS))
        self.assertEqual(report["source_valid_count"], len(SOURCES))
        self.assertEqual(report["candidate_url_count"], 5)
        self.assertEqual(report["candidate_urls_probed"], 5)
        self.assertEqual(report["current_real_video_audio_decoded_count"], 2)
        self.assertEqual(report["current_real_video_audio_unverified_count"], 3)
        self.assertFalse(report["all_candidates_current_av_verified"])
        self.assertFalse(report["ibo_device_verified"])
        self.assertNotIn("https://", json.dumps(report))
        self.assertTrue(all(x["url_sha256"] == hashlib.sha256(x["url"].encode()).hexdigest()
                            for x in private))

    def test_bounded_transient_retry_in_same_group_without_403_404_bypass(self):
        config, reader = fixture()
        attempts = {}
        def prober(item):
            digest, url = item
            index = int(url.rsplit("/", 1)[-1].removesuffix(".m3u8"))
            attempts[index] = attempts.get(index, 0) + 1
            if index == 0 and attempts[index] == 2:
                status = "VIDEO_AUDIO_DECODED"
            elif index == 0:
                status = "PROBE_FAILED_NETWORK_TIMEOUT"
            elif index == 1:
                status = "PROBE_FAILED_HTTP_FORBIDDEN"
            elif index == 2:
                status = "PROBE_FAILED_HTTP_NOT_FOUND"
            elif index == 3:
                status = "UNSAFE_OR_UNRESOLVED_HOST"
            else:
                status = "PROBE_UNCONFIRMED"
            success = status == "VIDEO_AUDIO_DECODED"
            return {"url_sha256": digest, "status": status,
                    "video": success, "audio": success, "decoded": success}
        result, _ = scan(config, reader=reader, prober=prober)
        self.assertEqual(attempts, {0: 2, 1: 1, 2: 1, 3: 1, 4: 2})
        self.assertEqual(result["candidate_urls_probed"], 5)
        self.assertEqual(result["transient_retry_attempt_count"], 2)
        self.assertEqual(result["transient_retry_av_recovered_count"], 1)
        self.assertEqual(result["current_real_video_audio_decoded_count"], 1)
        self.assertFalse(result["all_candidates_current_av_verified"])
        self.assertNotIn("https://", json.dumps(result))


    def test_supplementary_source_candidate_gets_real_av_group_check(self):
        cfg, original_reader = fixture()
        cfg["sources"].append({"id": "extra-allowed-tr",
                               "url": "https://example.org/extra-allowed-tr.m3u",
                               "scope": "TR"})
        extra_url = "https://example.org/extra-channel.m3u8"
        def reader(uri):
            if uri.endswith("/extra-allowed-tr.m3u"):
                return ('#EXTM3U\n'
                        '#EXTINF:-1 tvg-id="UlusalKanal.tr",Ulusal Kanal\n'
                        + extra_url + '\n')
            return original_reader(uri)
        def prober(pair):
            if pair[1] == extra_url:
                return {"url_sha256": pair[0], "status": "VIDEO_AUDIO_DECODED",
                        "video": True, "audio": True, "decoded": True}
            return fake_probe(pair)
        report, private = scan(cfg, reader=reader, prober=prober)
        self.assertEqual(report["source_valid_count"], 6)
        self.assertEqual(report["all_configured_active_sources_checked"], 7)
        self.assertEqual(report["all_configured_active_sources_valid"], 7)
        self.assertTrue(report["full_configured_catalog_source_coverage_complete"])
        self.assertEqual(report["candidate_url_count"], 6)
        self.assertEqual(report["candidate_urls_probed"], 6)
        self.assertEqual(report["current_real_video_audio_decoded_count"], 3)
        self.assertTrue(any(x["url"] == extra_url for x in private))
        self.assertNotIn(extra_url, json.dumps(report))

    def test_invalid_second_probe_is_rejected(self):
        config, reader = fixture()
        attempts = {}
        def prober(item):
            digest, _ = item
            attempts[digest] = attempts.get(digest, 0) + 1
            if attempts[digest] == 2:
                return {"url_sha256": digest, "status": "VIDEO_AUDIO_DECODED",
                        "video": False, "audio": True, "decoded": True}
            return {"url_sha256": digest, "status": "PROBE_FAILED_NETWORK_TIMEOUT",
                    "video": False, "audio": False, "decoded": False}
        with self.assertRaisesRegex(ValueError, "False decoded"):
            scan(config, reader=reader, prober=prober)

    def test_false_decoder_success_refused(self):
        config, reader = fixture()
        def liar(item):
            return {"url_sha256": item[0], "status": "VIDEO_AUDIO_DECODED",
                    "video": True, "audio": False, "decoded": True}
        with self.assertRaisesRegex(ValueError, "False"):
            scan(config, reader=reader, prober=liar)

    def test_partial_source_does_not_claim_complete(self):
        config, reader = fixture()
        def broken(url):
            if sorted(SOURCES)[0] in url:
                raise OSError("unavailable")
            return reader(url)
        report, rows = scan(config, reader=broken, prober=fake_probe)
        self.assertEqual(report["source_valid_count"], 5)
        self.assertFalse(report["source_inventory_complete"])
        self.assertEqual(len(rows), 4)

    def test_sealed_report_validation_rejects_tampering(self):
        config, reader = fixture()
        report, private = scan(config, reader=reader, prober=fake_probe)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            sealed = Path(tmp) / "evidence.sealed"
            path.write_text(json.dumps(report), encoding="utf-8")
            sealed.write_text(json.dumps({
                "schema": 1, "kind": "RSA_OAEP_SHA256_AES256_GCM_ZLIB",
                "records_encrypted": len(private), "nonce": "a",
                "wrapped_key": "b", "ciphertext": "c"}))
            result = validate(path, sealed, require_complete=True)
            self.assertEqual(result["current_video_audio_decoded"], 2)
            self.assertTrue(result["source_coverage_complete"])
            report["candidates"][0]["decoded"] = True
            report["candidates"][0]["audio"] = False
            path.write_text(json.dumps(report))
            with self.assertRaises(ValueError):
                validate(path, sealed)

    def test_untrusted_source_inventory_fails_closed(self):
        config, reader = fixture()
        config["sources"][0]["url"] = "http://127.0.0.1/private.m3u"
        with self.assertRaises(ValueError):
            scan(config, reader=reader, prober=fake_probe)


if __name__ == "__main__":
    unittest.main()
