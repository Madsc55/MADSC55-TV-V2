#!/usr/bin/env python3
"""No-network grouped TR/AZ API, EPG, URL safety and IBO evidence regressions."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from traz_api_source_batch import build,public_stream
import build_verified_test_playlist as playlist

class TrAzEnrichmentTests(unittest.TestCase):
    def fixture(self):
        channels=[
            {"id":"SZCTV.tr","country":"TR","alt_names":["Sözcü TV","SZC TV"]},
            {"id":"Baku.az","country":"AZ"},
            {"id":"EuroTurk.de","country":"DE"},
            {"id":"Other.de","country":"DE"},
            {"id":"Closed.tr","country":"TR","closed":"2024-01-01"}]
        feeds=[{"channel":"EuroTurk.de","languages":["tur"]},
               {"channel":"Other.de","languages":["eng"]}]
        streams=[
            {"channel":"SZCTV.tr","url":"https://cdn.example.org/szc.m3u8"},
            {"channel":"SZCTV.tr","url":"https://cdn.example.org/szc.m3u8"},
            {"channel":"Baku.az","url":"http://cdn.example.org/baku.ts","referrer":"https://tv.example.org","labels":["Geo-blocked"]},
            {"channel":"EuroTurk.de","url":"https://cdn.example.org/euro.m3u8"},
            {"channel":"Other.de","url":"https://cdn.example.org/other.m3u8"},
            {"channel":"Closed.tr","url":"https://cdn.example.org/closed.m3u8"},
            {"channel":"SZCTV.tr","url":"http://127.1/private.m3u8"}]
        guides=[{"channel":"SZCTV.tr"},{"channel":"Other.de"}]
        return channels,feeds,streams,guides

    def test_exact_identity_worldwide_feed_epg_and_no_raw_urls(self):
        report,private=build(*self.fixture())
        self.assertEqual(report["target_unique_channel_ids"],3)
        self.assertEqual(report["worldwide_language_feed_identities"],1)
        self.assertEqual(report["epg_target_identities"],1)
        self.assertEqual(report["unique_channel_url_pairs"],3)
        self.assertEqual(report["custom_header_candidates"],1)
        self.assertEqual(report["geoblock_label_candidates"],1)
        self.assertEqual(len(private),3)
        self.assertNotIn("cdn.example.org",json.dumps(report))
        self.assertTrue(all(not r["av_verified"] for r in report["stream_references"]))
        self.assertFalse(report["ibo_device_verified"])

    def test_different_channels_sharing_url_not_merged(self):
        ch,feeds,streams,guides=self.fixture()
        streams.append({"channel":"Baku.az","url":"https://cdn.example.org/szc.m3u8"})
        report,_=build(ch,feeds,streams,guides)
        self.assertEqual(report["same_url_multiple_channel_id_pairs"],1)

    def test_invalid_url_hosts_and_inputs_fail_closed(self):
        for url in ["http://127.1/a","http://127.0.0.1/a",
                    "http://192.168.1.2/a","https://localhost/a",
                    "https://user:pass@example.org/a",
                    "https://www.youtube.com/watch?v=ABCDEFGHIJK",
                    "https://r.googlevideo.com/a","file:///etc/passwd",
                    "https://example.org/a#frag","https://example.org:9999/a"]:
            with self.subTest(url=url): self.assertFalse(public_stream(url))
        self.assertTrue(public_stream("https://cdn.example.org/live.m3u8"))
        with self.assertRaises(ValueError): build({},[],[],[])
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            build([{"id":"test.tr","country":"TR"},{"id":"test.tr","country":"TR"}],[],[],[])

    def test_separate_test_playlist_accepts_only_decoded_video_plus_audio(self):
        baseline="#EXTM3U\n#EXTINF:-1,Original\nhttps://example.org/original.m3u8\n"
        rows=[
            {"channel_id":"ProbeOnly","url":"https://example.org/probe.m3u8",
             "status":"SHORT_DECODE_VERIFIED","media_types":["video","audio"]},
            {"channel_id":"VideoOnly","url":"https://example.org/video.m3u8",
             "status":"VIDEO_AUDIO_DECODED","proof_source":"FFMPEG_BOTH_DECODED",
             "video_decoded":True,"audio_decoded":False,"media_types":["video"]},
            {"channel_id":"RealAV","url":"https://example.org/real.m3u8",
             "status":"VIDEO_AUDIO_DECODED","proof_source":"FFMPEG_BOTH_DECODED",
             "video_decoded":True,"audio_decoded":True,"media_types":["video","audio"]}]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            live,queue,out,summary=(root/k for k in ("main.m3u8","queue.json","test.m3u8","summary.json"))
            live.write_text(baseline)
            queue.write_text(json.dumps({"items":rows}))
            with patch.object(playlist,"LIVE",live),patch.object(playlist,"REPORT",queue),\
                 patch.object(playlist,"OUT",out),patch.object(playlist,"SUMMARY",summary):
                playlist.main()
            self.assertEqual(live.read_text(),baseline)
            self.assertEqual(out.read_text().count("#EXTINF:"),1)
            self.assertIn("RealAV",out.read_text())
            self.assertEqual(json.loads(summary.read_text())["entries"],1)

if __name__=="__main__":
    unittest.main()
