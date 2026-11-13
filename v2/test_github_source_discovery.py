import unittest
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

if __name__ == "__main__":
    unittest.main()
