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
    def test_reject_http_page(self):
        with self.assertRaises(ValueError):
            discover_playlist_links("http://example.com", "")
if __name__ == "__main__":
    unittest.main(verbosity=2)
