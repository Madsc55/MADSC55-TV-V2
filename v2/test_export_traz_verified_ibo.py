#!/usr/bin/env python3
"""One grouped offline suite for the isolated private IBO AV-evidence export."""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import export_traz_verified_ibo as exporter

URL="https://cdn.example.org/real.m3u8"
HASH=hashlib.sha256(URL.encode()).hexdigest()

def fixtures(ids=("TV.tr",),status="VIDEO_AUDIO_DECODED",decoded=True):
    public={"unique_url_candidates":1,"unprobed":0,
      "streams":[{"url_sha256":HASH,"status":status,"decoded":decoded,
                  "channel_ids":list(ids)}]}
    private=[{"url":URL,"url_sha256":HASH,"probe_status":status,
              "decoded":decoded,"video":True,"audio":True,"channel_ids":list(ids)}]
    return public,private

class PrivateIboAcceptanceTests(unittest.TestCase):
    def test_only_real_video_and_audio_may_export(self):
        public,private=fixtures()
        selected,ambiguous=exporter.make_entries(public,private)
        self.assertEqual(selected,[("TV.tr",URL)])
        self.assertEqual(ambiguous,0)
        public,private=fixtures("TV.tr", "VIDEO_AUDIO_STREAMS_ONLY",False)
        private[0]["decoded"]=False
        self.assertEqual(exporter.make_entries(public,private)[0],[])

    def test_ambiguous_channel_identity_stays_in_review(self):
        public,private=fixtures(("TV1.tr","TV2.tr"))
        self.assertEqual(exporter.make_entries(public,private),([],1))

    def test_public_private_identity_mismatch_rejected(self):
        public,private=fixtures()
        bad=[dict(private[0],url="https://other.example.org/a.m3u8"),
             dict(private[0],channel_ids=["Different.tr"]),
             dict(private[0],decoded=False)]
        for row in bad:
            with self.subTest(row=row), self.assertRaises(ValueError):
                exporter.make_entries(public,[row])

    def test_incomplete_encrypted_evidence_rejected(self):
        public,private=fixtures()
        with self.assertRaises(ValueError):
            exporter.make_entries(public,[])
        with self.assertRaises(ValueError):
            exporter.make_entries(public,private+private)

    def test_multiple_verified_urls_per_channel_are_primary_plus_alternatives(self):
        import hashlib
        second_url="https://cdn.example.org/backup.m3u8"
        second_hash=hashlib.sha256(second_url.encode()).hexdigest()
        public,private=fixtures()
        public["unique_url_candidates"]=2
        public["streams"].append({
            "url_sha256":second_hash,"status":"VIDEO_AUDIO_DECODED",
            "decoded":True,"channel_ids":["TV.tr"]})
        private.append({
            "url":second_url,"url_sha256":second_hash,
            "probe_status":"VIDEO_AUDIO_DECODED","decoded":True,
            "video":True,"audio":True,"channel_ids":["TV.tr"]})
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            output=root/"test.m3u8"
            main=root/"main.m3u8"
            main.write_text("#EXTM3U\n")
            with patch.object(exporter,"MAIN",main),\
                 patch.object(exporter,"validate",return_value=public),\
                 patch.object(exporter,"open_rows",return_value=private):
                summary=exporter.export(root/"secret.pem",output)
            self.assertEqual(summary["private_test_entries"],2)
            self.assertEqual(summary["distinct_primary_channel_ids"],1)
            self.assertEqual(summary["alternative_av_streams"],1)
            self.assertEqual(output.read_text().count("#EXTINF:"),2)
            self.assertIn("TEST - ALTERNATIF AKIS",output.read_text())
            self.assertEqual(main.read_text(),"#EXTM3U\n")

    def test_output_private_separate_and_main_immutable(self):
        public,private=fixtures()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            main=root/"main.m3u8"
            main.write_text("#EXTM3U\n#EXTINF:-1,Existing\nhttps://cdn.example.org/old.m3u8\n")
            original=main.read_bytes()
            destination=root/"private-device-test.m3u8"
            with patch.object(exporter,"MAIN",main),\
                 patch.object(exporter,"validate",return_value=public),\
                 patch.object(exporter,"open_rows",return_value=private):
                summary=exporter.export(root/"dummy-private-key.pem",destination)
                self.assertEqual(summary["private_test_entries"],1)
                self.assertFalse(summary["ibo_device_verified"])
                self.assertEqual(main.read_bytes(),original)
                self.assertIn(URL,destination.read_text())
                self.assertEqual(destination.stat().st_mode & 0o777,0o600)
                with self.assertRaises(ValueError):
                    exporter.export(root/"dummy-private-key.pem",destination)
                with self.assertRaises(ValueError):
                    exporter.export(root/"dummy-private-key.pem",main)

if __name__=="__main__":
    unittest.main()
