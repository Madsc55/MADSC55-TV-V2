import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

from v2.stage1_metadata_refresh import (collect_feed, feed_xml, directory_index,
    directory_match, confirm, build_guide, digest, playlist_rows)

class Stage1MetadataTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026,11,28,12,tzinfo=timezone.utc)
        self.row = {"position":1,"record_sha256":"a"*64,"url":"https://tv.example/live.m3u8",
                    "tvg_id":"","logo":""}
        self.channels = [{"id":"TV.tr","name":"TV","website":"https://tv.example/"}]
        self.streams = [{"channel":"TV.tr","feed":None,"url":self.row["url"]}]
        self.logos = [{"channel":"TV.tr","in_use":True,"url":"https://tv.example/logo.png"}]
        self.xml = b'<tv><channel id="TV.tr"/><programme channel="TV.tr" start="20261128110000 +0000" stop="20261128130000 +0000"><title>News</title></programme></tv>'
        self.page = b'<title>TV</title><video src="/live.m3u8"></video><img src="/logo.png" alt="TV">'
    def test_fresh_not_stale(self):
        claimed, fresh = collect_feed(feed_xml(self.xml),{"TV.tr"},self.now)
        self.assertEqual(claimed,{"TV.tr"})
        self.assertEqual(set(fresh),{"TV.tr"})
        _, stale = collect_feed(feed_xml(self.xml),{"TV.tr"},datetime(2026,11,30,tzinfo=timezone.utc))
        self.assertFalse(stale)
        duplicate=self.xml.replace(b'<channel id="TV.tr"/>',b'<channel id="TV.tr"/><channel id="TV.tr"/>')
        self.assertFalse(collect_feed(feed_xml(duplicate),{"TV.tr"},self.now)[1])
    def test_xml_entity_rejected(self):
        with self.assertRaises(ValueError):
            feed_xml(b'<!DOCTYPE tv SYSTEM "file:///etc/passwd"><tv/>')
    def test_conflicting_stream_and_id(self):
        idx=directory_index(self.channels,self.streams+[{"channel":"Other.tr","url":self.row["url"]}],self.logos)
        self.assertIsNone(directory_match(self.row,idx))
        idx=directory_index(self.channels,self.streams,self.logos)
        self.assertIsNone(directory_match(dict(self.row,tvg_id="Wrong.tr"),idx))
        self.assertIsNone(directory_match(dict(self.row,url=self.row["url"]+"?x=1"),idx))
    def test_independent_publisher_and_exact_assets(self):
        match=directory_match(self.row,directory_index(self.channels,self.streams,self.logos))
        _, fresh=collect_feed(feed_xml(self.xml),{"TV.tr"},self.now)
        active={"TV.tr":("https://guide.example/guide.xml",fresh["TV.tr"])}
        def read(url,*args):
            return self.page if url.endswith("/") else b"image"
        p=confirm(self.row,match,active,read,lambda data:None)
        self.assertEqual(p["changes"],{"tvg_id":"TV.tr","logo":"https://tv.example/logo.png"})
        self.assertNotIn("live.m3u8",json.dumps(p))
        self.assertEqual(p["evidence"]["logo"]["content_sha256"],digest(b"image"))
        self.assertFalse(confirm(self.row,match,active,lambda *a:b'<title>TV</title>',lambda d:None))
        def bad_image(_):
            raise ValueError("broken")
        self.assertEqual(confirm(self.row,match,active,read,bad_image)["changes"],{"tvg_id":"TV.tr"})
        guide,existing,new,count=build_guide(active,[],[p])
        self.assertEqual((existing,new,count),(0,1,1))
        self.assertEqual(guide.find("programme").get("channel"),"TV.tr")
    def test_playlist_never_modified_and_duplicate_attr_rejected(self):
        data=b'#EXTM3U\n#EXTINF:-1 group-title="A" tvg-id="" tvg-logo="",TV\nhttps://tv.example/live.m3u8\n'
        rows=playlist_rows(data)
        self.assertEqual(rows[0]["tvg_id"],"")
        self.assertEqual(rows[0]["position"],1)
        self.assertEqual(rows[0]["record_sha256"],digest(data.split(b'\n',1)[1]))
        self.assertTrue(playlist_rows(data.replace(b'tvg-id=""',b'tvg-id="" tvg-id="X"'))[0]["invalid"])
    def test_receipt_reconciles(self):
        p=Path(__file__).resolve().parent/"reports"/"decision-memory-20261127-index.json"
        doc=json.loads(p.read_text())
        r=doc["receipt"]
        self.assertEqual(r["checkpoint_rows"],r["restored_rows"])
        self.assertEqual(sum(r["attached_observations_by_run"].values())+r["unmatched_observations_in_encrypted_ledger"],r["source_observations"])
        self.assertEqual(r["matched_checkpoint_urls"]+r["unmatched_unique_urls"],r["source_unique_urls"])
        self.assertEqual(r["replay_insertions"],0)
        self.assertEqual(doc["artifact_retention_days"],90)

if __name__ == "__main__":
    unittest.main()
