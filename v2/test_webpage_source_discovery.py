#!/usr/bin/env python3
"""No network. Verify HTML discovery is limited to public HTTPS playlist links."""
import unittest
from webpage_source_discovery import discover_playlist_links

class WebpageSourceTests(unittest.TestCase):
    def test_relative_and_absolute_playlists(self):
        html = '<a href="/tv/tr.m3u">TR</a><a href="https://example.org/az.m3u8">AZ</a>'
        self.assertEqual(discover_playlist_links("https://example.com/index.html", html),
                         ["https://example.com/tv/tr.m3u", "https://example.org/az.m3u8"])
    def test_reject_unsafe_and_non_playlists(self):
        html = ('<a href="http://example.com/a.m3u">bad</a>'
                '<a href="https://user:secret@example.com/a.m3u">bad</a>'
                '<a href="https://example.com:8080/a.m3u">bad</a>'
                '<a href="javascript:alert(1)">bad</a>'
                '<a href="https://example.com/page.html">bad</a>'
                '<a href="https://example.com/good.m3u">ok</a>')
        self.assertEqual(discover_playlist_links("https://example.com", html),
                         ["https://example.com/good.m3u"])
    def test_dedup_and_fragment(self):
        html = '<a href="/a.m3u">a</a><a href="/a.m3u">a</a><a href="/b.m3u#x">b</a>'
        self.assertEqual(discover_playlist_links("https://example.com", html),
                         ["https://example.com/a.m3u"])
    def test_private_addresses_not_fetched(self):
        document = ('<a href="https://127.0.0.1/test.m3u">loopback</a>'
                    '<a href="https://192.168.1.3/test.m3u">private</a>'
                    '<a href="https://localhost/test.m3u">local</a>'
                    '<a href="https://example.org/test.m3u">public</a>')
        self.assertEqual(discover_playlist_links("https://example.com", document),
                         ["https://example.org/test.m3u"])
    def test_reject_private_and_credentialed_origin(self):
        for page in ("https://localhost/index.html", "https://127.0.0.1/index.html",
                     "https://user:pass@example.com/index.html",
                     "https://example.com:8080/index.html"):
            with self.subTest(page=page), self.assertRaises(ValueError):
                discover_playlist_links(page, '<a href="/tv.m3u">TV</a>')
    def test_github_blob_view_is_canonical_raw_and_deduplicated(self):
        # Regression: run #41915184812 index-d7b8649d94005380 INVALID_SOURCE.
        blob = "https://github.com/Free-TV/IPTV/blob/master/playlist.m3u8"
        raw = "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8"
        document = '<a href="' + blob + '">view</a><a href="' + raw + '">raw</a>'
        self.assertEqual(discover_playlist_links("https://github.com/Free-TV/IPTV", document), [raw])

    def test_github_blob_nested_playlist_and_malformed_paths(self):
        document = ('<a href="https://github.com/iptv-org/iptv/blob/master/streams/tr.m3u">tr</a>'
                    '<a href="https://github.com/org/repo/blob/main/list.m3u?x=1">query</a>')
        self.assertEqual(discover_playlist_links("https://example.com", document),
                         ["https://raw.githubusercontent.com/iptv-org/iptv/master/streams/tr.m3u"])

    def test_reject_http_page(self):
        with self.assertRaises(ValueError):
            discover_playlist_links("http://example.com", "")
if __name__ == "__main__":
    unittest.main(verbosity=2)
