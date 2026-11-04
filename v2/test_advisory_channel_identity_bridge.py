#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from advisory_channel_identity_bridge import link_advisory_identities

def h(value):
    return hashlib.sha256(value.encode()).hexdigest()

class AdvisoryBridgeTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.official=Path(self.folder.name)/"official.json"
        self.youtube=Path(self.folder.name)/"youtube.json"
        self.candidates=[{"url_sha256":h("https://media.example.org/a.m3u8"),
                          "name":"TRT Haber","tvg_id":"TRTHaber.tr"}]
        self.official.write_text(json.dumps({
          "policy":"READ_ONLY_NO_PLAYLIST_CHANGES_NO_DRM_BYPASS",
          "count":1, "channels":[{"channel_id":"TRTHaber.tr","name":"TRT Haber",
                                   "official_site":"https://www.trt.net.tr"}]}))
        self.youtube.write_text(json.dumps({
          "policy":"ADVISORY_ONLY_NO_PLAYLIST_WRITES_NO_AUTOMATIC_IBO_IMPORT",
          "results":[{"channel":"TRT Haber","video_id":"A1234567890",
                      "title":"LIVE","status":"LIVE_METADATA_VERIFIED"}]}))
    def test_exact_official_and_live_uploader_are_linked_without_stream_claim(self):
        report=link_advisory_identities(self.candidates,self.official,self.youtube)
        self.assertEqual(report["linked_m3u_candidates"],1)
        self.assertEqual(report["official_exact_identity_connections"],1)
        self.assertEqual(report["youtube_exact_uploader_connections"],1)
        self.assertFalse(report["av_verified"])
        self.assertNotIn("https://",json.dumps(report))
        self.assertEqual(report["links"][0]["candidate_url_sha256"],self.candidates[0]["url_sha256"])
    def test_youtube_title_alone_must_not_match(self):
        item=json.loads(self.youtube.read_text())
        item["results"][0]["channel"]="Unrelated"
        item["results"][0]["title"]="TRT Haber Canlı"
        self.youtube.write_text(json.dumps(item))
        report=link_advisory_identities(self.candidates,self.official,self.youtube)
        self.assertEqual(report["youtube_exact_uploader_connections"],0)
    def test_official_id_without_name_match_rejected(self):
        item=json.loads(self.official.read_text())
        item["channels"][0]["name"]="Different Channel"
        self.official.write_text(json.dumps(item))
        self.assertEqual(link_advisory_identities(self.candidates,self.official,self.youtube)["official_exact_identity_connections"],0)
    def test_youtube_not_live_cannot_link(self):
        item=json.loads(self.youtube.read_text())
        item["results"][0]["status"]="DISCOVERED_NOT_LIVE_VERIFIED"
        self.youtube.write_text(json.dumps(item))
        self.assertEqual(link_advisory_identities(self.candidates,self.official,self.youtube)["youtube_exact_uploader_connections"],0)
    def test_missing_reports_fail_closed(self):
        report=link_advisory_identities(self.candidates,self.official.with_name("missing.json"),
                                        self.youtube.with_name("missing2.json"))
        self.assertEqual(report["links"],[])
        self.assertEqual(report["official_catalog_status"],"MISSING_OR_INVALID")
    def test_bad_candidate_digest_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"hash"):
            link_advisory_identities([dict(self.candidates[0],url_sha256="bad")],self.official,self.youtube)

if __name__=="__main__":
    unittest.main()
