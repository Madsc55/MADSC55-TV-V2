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

    def test_multiple_urls_same_name_retained(self):
        a=playlist(("same.id","TR","Same","https://example.invalid/a.m3u8"))
        b=playlist(("same.id","TR","Same","https://example.invalid/b.m3u8"))
        result=discover([("a",a),("b",b)],"#EXTM3U\\n",{"a":"TR","b":"TR"})
        self.assertEqual(len(result),2)

    def test_non_http_stream_ignored(self):
        data='#EXTM3U\\n#EXTINF:-1,TRT Haber\\nfile:///tmp/stream\\n'
        self.assertEqual(list(entries(data)),[])

    def test_malformed_and_non_stream_lines(self):
        data='#EXTM3U\n#EXTINF:-1,TRT Haber\n#EXTVLCOPT:http-user-agent=Foo\nhttps://example.invalid/a.m3u8\n'
        self.assertEqual(len(list(entries(data))),1)

if __name__=="__main__":
    unittest.main()
