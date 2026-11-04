#!/usr/bin/env python3
"""One offline batch for public document and YouTube metadata verification."""
import json
import unittest
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from youtube_official_live_api import classify, verify_ids
from document_platform_discovery import PUBLIC_DOCUMENT_PAGES, page_references, scan


class PlatformVerificationTests(unittest.TestCase):
    def test_official_api_live_requires_active_start_and_no_end(self):
        row = {"id": "ABCDEFGHIJK",
               "snippet": {"liveBroadcastContent": "live"},
               "liveStreamingDetails": {"actualStartTime": "2026-11-04T11:00:00Z"}}
        self.assertEqual(classify(row),
                         ("LIVE_METADATA_VERIFIED", "OFFICIAL_API_ACTIVE_LIVE"))
        row["liveStreamingDetails"]["actualEndTime"] = "2026-11-04T12:00:00Z"
        self.assertIsNone(classify(row))
        row["snippet"]["liveBroadcastContent"] = "none"
        self.assertEqual(classify(row),
                         ("NOT_CURRENTLY_LIVE", "OFFICIAL_API_NOT_LIVE"))

    def test_official_api_missing_key_is_unknown(self):
        with patch.dict("os.environ", {}, clear=True):
            statuses, state = verify_ids(["ABCDEFGHIJK"])
        self.assertEqual(statuses, {})
        self.assertEqual(state, "API_KEY_NOT_CONFIGURED")

    def test_official_api_batched_and_no_fabricated_unknown(self):
        ids = [f"{i:011d}" for i in range(105)]
        batches = []
        def read(url):
            query = parse_qs(urlsplit(url).query)
            batch = query["id"][0].split(",")
            batches.append(batch)
            self.assertEqual(query["part"], ["snippet,liveStreamingDetails"])
            return {"items": [
                {"id": batch[0],
                 "snippet": {"liveBroadcastContent": "live"},
                 "liveStreamingDetails": {"actualStartTime": "2026-11-04T11:00:00Z"}}
            ]}
        statuses,state = verify_ids(ids, key="fake-private-test-key",request=read)
        self.assertEqual([len(x) for x in batches],[50,50,5])
        self.assertEqual(state,"API_QUERIES_FINISHED")
        self.assertEqual(len(statuses),3)
        self.assertNotIn("fake-private-test-key",str((statuses,state)))

    def test_official_api_http_error_does_not_expose_key(self):
        def forbidden(url):
            raise HTTPError(url, 403, "denied", {}, None)
        statuses,state=verify_ids(["ABCDEFGHIJK"],key="private-key-123",request=forbidden)
        self.assertEqual(statuses,{})
        self.assertEqual(state,"API_HTTP_403")
        self.assertNotIn("private-key-123",str((statuses,state)))
        self.assertEqual(verify_ids(["../bad"],key="key")[1],"INVALID_VIDEO_IDS")

    def test_slide_accessibility_image_alt_public_m3u_reference(self):
        page="https://www.slideshare.net/slideshow/iptv-githubpdf/258657900"
        document='<img alt="Turkish M3U https://example.org/tr.m3u">'
        _,refs=page_references(page,document,"slideshare")
        self.assertEqual(refs,["https://example.org/tr.m3u"])
        _,refs=page_references(page,
            '<script><img alt="https://example.org/hidden.m3u"></script>',"slideshare")
        self.assertEqual(refs,[])

    def test_reviewed_slideshare_public_reference_still_requires_real_m3u(self):
        from document_platform_discovery import verify_sources
        slide=PUBLIC_DOCUMENT_PAGES["slideshare"][0]
        def fetch_page(url):
            if "advancedsearch.php" in url:
                return json.dumps({"response":{"docs":[]}})
            if url == slide:
                return "<title>IPTV Github.pdf</title>"
            return ""
        opts={"read":fetch_page,
              "search_pages":{"scribd":(),"slideshare":()},
              "document_pages":{"scribd":(),"slideshare":(slide,)}}
        report,links=scan(**opts)
        self.assertEqual(len(links),1)
        self.assertEqual(report["platforms"]["slideshare"]["candidate_sources"],1)
        self.assertEqual(report["platforms"]["slideshare"]["reviewed_public_reference_pages"],1)
        def valid_source(url):
            return '#EXTM3U\n#EXTINF:-1,TRT 1\nhttps://example.org/live.m3u8\n'
        accepted,proof=verify_sources(links,fetcher=valid_source,resolver=lambda url:True)
        self.assertEqual(len(accepted),1)
        self.assertEqual(proof[0]["status"],"M3U_CHANNEL_ENTRIES")
        self.assertFalse(proof[0]["playback_verified"])
        def no_marker(url):
            if "advancedsearch.php" in url:
                return json.dumps({"response":{"docs":[]}})
            return "anonymous document"
        _,invalid=scan(**dict(opts,read=no_marker))
        self.assertEqual(invalid,[])

    def test_direct_public_documents_even_with_empty_search_results(self):
        def read(url):
            if "advancedsearch.php" in url:
                return json.dumps({"response":{"docs":[]}})
            if "/document/834636179/" in url:
                return '<p>#EXTM3U #EXTINF:-1 TR channel [Link]</p>'
            if "/slideshow/iptv-githubpdf/" in url:
                return '<img alt="Turkish https://example.org/tr.m3u">'
            return "<html></html>"
        report,found=scan(read=read,document_pages={
            "scribd":PUBLIC_DOCUMENT_PAGES["scribd"][:1],
            "slideshare":PUBLIC_DOCUMENT_PAGES["slideshare"]})
        self.assertEqual(report["platforms"]["scribd"]["documents_checked"],1)
        self.assertEqual(report["platforms"]["slideshare"]["documents_checked"],1)
        self.assertEqual(report["platforms"]["scribd"]["candidate_sources"],0)
        self.assertEqual(report["platforms"]["slideshare"]["candidate_sources"],1)
        self.assertEqual(len(found),1)
        self.assertNotIn("https://example.org/tr.m3u",str(report))


if __name__=="__main__":
    unittest.main()
