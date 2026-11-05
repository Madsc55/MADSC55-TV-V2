#!/usr/bin/env python3
"""One grouped no-network acceptance suite for real IPTV-org API AV probes."""
import unittest
from traz_api_av_batch import prepare,summarize

class TrAzApiRealAvTests(unittest.TestCase):
    def test_identical_url_multiple_channel_ids_one_probe(self):
        rows=[{"channel_id":"One.tr","url":"https://cdn.example.org/a.m3u8"},
              {"channel_id":"Two.az","url":"https://cdn.example.org/a.m3u8"}]
        data=prepare(rows)
        self.assertEqual(len(data),1)
        self.assertEqual(next(iter(data.values()))["channel_ids"],{"One.tr","Two.az"})

    def test_ffprobe_codec_metadata_is_not_real_decode(self):
        data=prepare([{"channel_id":"TR.tr","url":"https://cdn.example.org/a.m3u8"}])
        h=next(iter(data))
        codeclist={h:{"url_sha256":h,"status":"VIDEO_AUDIO_STREAMS_ONLY",
                      "video":True,"audio":True,"decoded":False}}
        self.assertEqual(summarize(data,codeclist)["video_audio_decoded"],0)
        decoded={h:{"url_sha256":h,"status":"VIDEO_AUDIO_DECODED",
                    "video":True,"audio":True,"decoded":True}}
        self.assertEqual(summarize(data,decoded)["video_audio_decoded"],1)

    def test_wrong_hash_false_av_are_rejected(self):
        data=prepare([{"channel_id":"TV.tr","url":"https://cdn.example.org/a.m3u8"}])
        h=next(iter(data))
        bad=[{"url_sha256":"0"*64,"status":"VIDEO_AUDIO_DECODED",
              "video":True,"audio":True,"decoded":True},
             {"url_sha256":h,"status":"VIDEO_AUDIO_DECODED",
              "video":True,"audio":False,"decoded":True},
             {"url_sha256":h,"status":"VIDEO_AUDIO_STREAMS_ONLY",
              "video":True,"audio":True,"decoded":True}]
        for row in bad:
            with self.subTest(row=row),self.assertRaises(ValueError):
                summarize(data,{h:row})

    def test_unsafe_stream_and_youtube_page_never_accepted(self):
        for url in ("http://127.1/a.m3u8","http://localhost/a",
                    "https://www.youtube.com/watch?v=ABCDEFGHIJK"):
            with self.subTest(url=url),self.assertRaises(ValueError):
                prepare([{"channel_id":"TV.tr","url":url}])

    def test_missing_probe_does_not_claim_working_channel(self):
        data=prepare([{"channel_id":"TV.tr","url":"https://cdn.example.org/a.m3u8"}])
        report=summarize(data,{})
        self.assertEqual(report["unprobed"],1)
        self.assertEqual(report["video_audio_decoded"],0)
        self.assertEqual(report["streams"][0]["status"],"NOT_PROBED_BUDGET")
        self.assertFalse(report["ibo_device_verified"])

if __name__=="__main__":
    unittest.main()
