import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import github_source_discovery as discovery
from github_source_discovery import discover_gists

class GistDiscoveryTests(unittest.TestCase):
    def test_recent_public_gist_m3u_is_parsed_as_candidate(self):
        calls, fetched = [], []
        def api(url):
            calls.append(url)
            if "page=1" in url:
                return [{
                    "id": "gist-1",
                    "files": {
                        "turkiye.m3u": {
                            "raw_url": "https://gist.githubusercontent.com/gist-1/raw/turkiye.m3u"
                        }
                    }
                }]
            return []
        def fetch(url):
            fetched.append(url)
            return "#EXTM3U\n#EXTINF:-1,TRT Haber\nhttps://cdn.example/live.m3u8\n"
        rows, errors, checked = discover_gists(api_fn=api, fetch_fn=fetch)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["repository"], "gist:gist-1")
        self.assertEqual(rows[0]["entries"], 1)
        self.assertEqual(rows[0]["status"], "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED")
        self.assertEqual(errors, [])
        self.assertEqual(checked, 1)
        self.assertEqual(len(fetched), 1)
        self.assertEqual(len(calls), 2)

    def test_configured_gist_url_is_not_added_twice(self):
        url = "https://gist.githubusercontent.com/gist-1/raw/turkiye.m3u"
        def api(endpoint):
            if "page=1" in endpoint:
                return [{"id": "gist-1", "files": {"turkiye.m3u": {"raw_url": url}}}]
            return []
        rows, errors, checked = discover_gists(api_fn=api, fetch_fn=lambda _: self.fail("duplicate fetch"),
                                                configured_urls={url})
        self.assertEqual(rows, [])
        self.assertEqual(errors, [])
        self.assertEqual(checked, 1)

    def test_non_gist_hosts_and_non_playlist_files_are_ignored(self):
        def api(endpoint):
            if "page=1" in endpoint:
                return [{"id": "gist-2", "files": {
                    "readme.md": {"raw_url": "https://gist.githubusercontent.com/gist-2/raw/readme.md"},
                    "bad.m3u": {"raw_url": "https://example.com/bad.m3u"},
                }}]
            return []
        rows, errors, checked = discover_gists(api_fn=api, fetch_fn=lambda _: self.fail("must not fetch"))
        self.assertEqual(rows, [])
        self.assertEqual(errors, [])
        self.assertEqual(checked, 1)


class DiscoveryOutputTests(unittest.TestCase):
    def test_main_writes_single_json_document_with_real_line_ending(self):
        """The real scan must parse this report with json.loads."""
        with tempfile.TemporaryDirectory() as temp:
            report = pathlib.Path(temp) / "github-source-discovery.json"
            config = pathlib.Path(temp) / "sources.json"
            config.write_text('{"sources": []}', encoding="utf-8")
            with (
                patch.object(discovery, "OUT", report),
                patch.object(discovery, "CONFIG", config),
                patch.object(discovery, "QUERIES", []),
                patch.object(discovery, "discover_gists", return_value=([], [], 0)),
            ):
                discovery.main()
            raw = report.read_text(encoding="utf-8")
            self.assertTrue(raw.endswith("\n"))
            self.assertFalse(raw.endswith("\\n"))
            parsed = json.loads(raw)
            self.assertEqual(parsed["sources"], [])
            self.assertEqual(parsed["errors"], [])

if __name__ == "__main__":
    unittest.main()
