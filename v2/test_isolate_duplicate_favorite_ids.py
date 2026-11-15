import unittest
from isolate_duplicate_favorite_ids import isolate, entries

class FavoriteIdentityTests(unittest.TestCase):
    def test_distinct_trt_sources_get_distinct_ids(self):
        source = ('#EXTM3U\n'
                  '#EXTINF:-1 tvg-id="same" group-title="YEDEKLER",TRT 1\nhttps://example.com/a.m3u8\n'
                  '#EXTINF:-1 tvg-id="same" group-title="YEDEKLER",TRT 1\nhttps://example.com/b.m3u8\n')
        output, report = isolate(source)
        self.assertEqual(report["rewritten"], 2)
        ids = [x[1] for x in entries(output.splitlines(keepends=True))]
        self.assertEqual(len(set(ids)), 2)
        self.assertIn("https://example.com/a.m3u8", output)
        self.assertIn("https://example.com/b.m3u8", output)
        self.assertEqual(output, isolate(source)[0])
    def test_non_duplicates_unchanged(self):
        source = '#EXTM3U\n#EXTINF:-1 tvg-id="unique",TV\nhttps://example.com/tv\n'
        self.assertEqual(isolate(source)[0],source)
if __name__=="__main__":unittest.main()
