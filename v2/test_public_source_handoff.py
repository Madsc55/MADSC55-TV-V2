#!/usr/bin/env python3
"""Grouped offline source handoff acceptance without fake live URLs."""
import json
from pathlib import Path
import tempfile
import unittest

from public_source_handoff import staged_references, approved_live_index_sources


def gh(url="https://raw.githubusercontent.com/public/tv/1" + "a"*39 + "/tr.m3u"):
    return {"url": url,
            "status": "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED", "entries": 3}


def forge(url="https://codeberg.org/public/tv/raw/branch/main/tr.m3u"):
    return {"source_url": url, "forge": "codeberg"}


class SourceHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.g = base / "github.json"
        self.f = base / "forge.json"
        self.l = base / "live.json"
        self.write([gh()], [forge()])

    def write(self, g, f):
        self.g.write_text(json.dumps({
            "policy": "READ_ONLY_NO_AUTOMATIC_SOURCE_OR_PLAYLIST_IMPORT",
            "sources_found": len(g), "sources": g}), encoding="utf-8")
        self.f.write_text(json.dumps({"schema": 1, "status": "source_references_only",
                                     "source_count": len(f), "sources": f}), encoding="utf-8")

    def test_github_gist_gitlab_codeberg_inspection_is_bounded_and_not_av(self):
        refs, report = staged_references(self.g, self.f, set())
        self.assertEqual(len(refs), 2)
        self.assertEqual(report["accepted_for_inspection"], {
            "github_gist": 1, "gitlab_codeberg": 1})
        self.assertTrue(all(x["scope"] == "candidate" for x in refs))
        self.assertTrue(all(x["origin"] == "reviewed-public-source-reference" for x in refs))
        self.assertFalse(report["playback_verified"])

    def test_no_auto_approval_of_unparsed_or_sensitive_sources(self):
        self.write([{"url": gh()["url"], "entries": 0, "status": "UNVERIFIED"},
                    gh("https://example.com/secret.m3u?token=bad")],
                   [forge("https://codeberg.org/private/tv/raw/branch/main/tr.m3u")])
        refs, report = staged_references(self.g, self.f, set())
        self.assertEqual(refs, [])
        self.assertEqual(report["accepted_for_inspection"]["github_gist"], 0)

    def test_duplicate_sources_and_budgets(self):
        self.write([gh(), gh()], [forge()])
        refs, stats = staged_references(self.g, self.f, {gh()["url"]})
        self.assertEqual(len(refs), 1)
        self.assertEqual(stats["skipped_unreviewed_or_duplicate"]["github_gist"], 2)
        with self.assertRaises(ValueError):
            staged_references(self.g, self.f, set(), max_per_provider=65)

    def test_full_valid_reference_budget_does_not_truncate_48_references(self):
        github = [gh("https://raw.githubusercontent.com/public/tv/main/list%02d.m3u" % i)
                  for i in range(48)]
        self.write(github, [forge()])
        refs, result = staged_references(self.g, self.f, set())
        self.assertEqual(result["accepted_for_inspection"]["github_gist"], 48)
        self.assertEqual(result["bounded_truncation"]["github_gist"], 0)
        self.assertEqual(len(refs), 49)

    def test_invalid_missing_partial_reports_never_claim_success(self):
        self.g.unlink()
        with self.assertRaises(ValueError):
            staged_references(self.g, self.f, set())
        self.write([gh()], [forge()])
        bad = json.loads(self.f.read_text())
        bad["source_count"] = 100
        self.f.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(ValueError):
            staged_references(self.g, self.f, set())

    def test_approved_live_pages_enter_html_index_only(self):
        self.l.write_text(json.dumps({
            "schema": 1,
            "policy": "explicitly reviewed public HTTPS origins only; no inferred playback",
            "pages": [{"id": "trt-official", "url": "https://www.trt.net.tr/"},
                      {"id": "aztv-official", "url": "https://www.aztv.az/"}]
        }), encoding="utf-8")
        sources, report = approved_live_index_sources(
            self.l, {"https://www.trt.net.tr/"})
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["id"], "live-index-aztv-official")
        self.assertEqual(sources[0]["kind"], "html")
        self.assertFalse(report["playback_verified"])
        self.assertEqual(report["channel_streams_inferred"], 0)

    def test_invalid_live_origin_or_duplicate_id_rejected(self):
        config = {"schema": 1, "policy":
                  "explicitly reviewed public HTTPS origins only; no inferred playback",
                  "pages": [{"id": "bad-page", "url": "http://127.0.0.1/private"}]}
        self.l.write_text(json.dumps(config), encoding="utf-8")
        with self.assertRaises(ValueError):
            approved_live_index_sources(self.l, set())
        config["pages"] = [{"id": "live", "url": "https://www.trt.net.tr/"}] * 2
        self.l.write_text(json.dumps(config), encoding="utf-8")
        with self.assertRaises(ValueError):
            approved_live_index_sources(self.l, set())


if __name__ == "__main__":
    unittest.main()
