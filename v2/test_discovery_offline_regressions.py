#!/usr/bin/env python3
"""Offline fixtures for V2 discovery regressions. No network or playlist writes."""
import hashlib
import unittest
from discover import entries, discover, turkish_candidate

def playlist(*items):
    return "#EXTM3U\n" + "".join(
        f'#EXTINF:-1 tvg-id="{tvg}" group-title="{group}",{name}\n{url}\n'
        for tvg, group, name, url in items
    )

class DiscoveryOfflineRegression(unittest.TestCase):
    def test_offline_snapshot_and_comparison_fail_closed(self):
        import sys
        from unittest.mock import patch
        import discover as module
        for flags in (["--offline", "--snapshot-output"], ["--offline", "--previous-report", "old.json"], ["--limit", "-1"]):
            with self.subTest(flags=flags), patch.object(sys, "argv", ["discover.py", *flags]):
                with self.assertRaises(SystemExit) as raised:
                    module.main()
                self.assertEqual(raised.exception.code, 2)

    def test_source_loss_audit_integration_contract(self):
        import inspect
        import discover as module
        body = inspect.getsource(module.main)
        self.assertIn("--previous-report", body)
        self.assertIn("source_loss_audit", body)
        self.assertIn("compare(previous, result)", body)

    def test_extinf_comma_parsing(self):
        line = '#EXTINF:-1 group-title="News, Turkey",Channel, Extra'
        data = "\n".join(["#EXTM3U", line, "https://example.invalid/live.m3u8"])
        parsed = list(entries(data))
        self.assertEqual(parsed[0]["name"], "Channel, Extra")
        self.assertEqual(parsed[0]["group"], "News, Turkey")

    def test_world_turkey_metadata(self):
        self.assertTrue(turkish_candidate({"name":"Turkey Live TV", "group":"World", "tvg_id":""}, "world"))
        self.assertTrue(turkish_candidate({"name":"TRT Haber", "group":"News", "tvg_id":""}, "world"))
        self.assertTrue(turkish_candidate({"name":"Azərbaycan TV", "group":"World", "tvg_id":""}, "world"))
        self.assertFalse(turkish_candidate({"name":"English News", "group":"World", "tvg_id":""}, "world"))

    def test_country_candidate_is_not_language_proof(self):
        self.assertTrue(turkish_candidate({"name":"Unknown", "group":"", "tvg_id":""}, "AZ"))

    def test_provenance_and_dedup(self):
        u="https://example.invalid/live.m3u8"
        data=playlist(("tr.example", "TR", "TRT Haber", u))
        result=discover([("first",data),("second",data)],"#EXTM3U\n",{"first":"TR","second":"TR"})
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["source_ids"],["first","second"])
        self.assertEqual(result[0]["url_sha256"],hashlib.sha256(u.encode()).hexdigest())
        self.assertNotIn("url",result[0])

    def test_live_stream_exclusion(self):
        u="https://example.invalid/live.m3u8"
        data=playlist(("tr.example","TR","TRT Haber",u))
        self.assertEqual(discover([("first",data)],data,{"first":"TR"}),[])

    def test_turkish_url_not_language_proof(self):
        self.assertFalse(turkish_candidate({"name":"English News","group":"World","tvg_id":""},"world"))

    def test_world_source_recovers_matching_regional_tvg_id(self):
        regional = playlist(("TR.Sample", "Turkey", "Kanal", "https://example.invalid/tr.m3u8"))
        world = playlist(("tr.sample", "World", "Channel", "https://example.invalid/world.m3u8"))
        result = discover([("regional", regional), ("world", world)],
                          "#EXTM3U\n", {"regional": "TR", "world": "world"})
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1]["source"], "world")

    def test_world_generic_name_does_not_cross_match(self):
        regional = playlist(("", "Turkey", "News", "https://example.invalid/tr.m3u8"))
        world = playlist(("", "World", "News", "https://example.invalid/world.m3u8"))
        result = discover([("regional", regional), ("world", world)],
                          "#EXTM3U\n", {"regional": "TR", "world": "world"})
        self.assertEqual(len(result), 1)

    def test_multiple_urls_same_name_retained(self):
        a=playlist(("same.id","TR","Same","https://example.invalid/a.m3u8"))
        b=playlist(("same.id","TR","Same","https://example.invalid/b.m3u8"))
        result=discover([("a",a),("b",b)],"#EXTM3U\n",{"a":"TR","b":"TR"})
        self.assertEqual(len(result),2)

    def test_fetch_rejects_private_source_before_network(self):
        from discover import fetch
        for url in ("https://127.0.0.1/secret.m3u",
                    "https://192.168.1.1/private.m3u8",
                    "https://localhost/test.m3u",
                    "http://example.org/list.m3u"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                fetch(url)

    def test_non_http_stream_ignored(self):
        data='#EXTM3U\n#EXTINF:-1,TRT Haber\nfile:///tmp/stream\n'
        self.assertEqual(list(entries(data)),[])

    def test_malformed_and_non_stream_lines(self):
        data='#EXTM3U\n#EXTINF:-1,TRT Haber\n#EXTVLCOPT:http-user-agent=Foo\nhttps://example.invalid/a.m3u8\n'
        self.assertEqual(len(list(entries(data))),1)

if __name__=="__main__":
    unittest.main()
