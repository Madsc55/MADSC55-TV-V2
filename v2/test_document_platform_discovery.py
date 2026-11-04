#!/usr/bin/env python3
"""Three-platform grouped adapter regression; no network or device playback."""
import json
from pathlib import Path
import tempfile
import unittest
from document_platform_discovery import (ARCHIVE_SEARCH,SEARCH_PAGES,PLATFORMS,accepted_sources,
 allowed_page,archive_file_refs,digest,page_references,scan,source_url,verify_sources)

class ThreePlatformAdapterTests(unittest.TestCase):
 def test_tokenless_public_https_only(self):
  self.assertTrue(source_url("https://example.org/live.m3u"))
  for url in ("http://example.org/live.m3u","https://127.0.0.1/a.m3u",
      "https://example.org/tr.m3u?token=one","https://user:pass@example.org/a.m3u",
      "https://localhost/list.m3u","https://example.org/private/a.m3u",
      "https://example.org/tv.mp4"):
   with self.subTest(url=url):self.assertFalse(source_url(url))
 def test_public_page_allowlist(self):
  self.assertTrue(allowed_page("https://www.scribd.com/search?query=iptv"))
  self.assertTrue(allowed_page("https://www.slideshare.net/slideshow/tv/2"))
  self.assertTrue(allowed_page(ARCHIVE_SEARCH))
  self.assertFalse(allowed_page("https://localhost/search"))
  self.assertFalse(allowed_page("https://www.scribd.com/account/profile"))
 def test_scribd_document_and_visible_url(self):
  docs,links=page_references("https://www.scribd.com/search?query=iptv",
     '<a href="/document/123/tv">doc</a><a href="https://example.org/a.m3u">list</a>',"scribd")
  self.assertEqual(len(docs),1)
  self.assertEqual(links,["https://example.org/a.m3u"])
  _,links=page_references(docs[0],"<p>https://example.org/az.m3u8</p>","scribd")
  self.assertEqual(links,["https://example.org/az.m3u8"])
 def test_slideshare_excludes_script_and_private_pages(self):
  docs,links=page_references("https://www.slideshare.net/search?q=m3u",
     '<script>https://example.org/bad.m3u</script><a href="https://example.org/ok.m3u">ok</a><a href="/account">login</a>',"slideshare")
  self.assertEqual(docs,[])
  self.assertEqual(links,["https://example.org/ok.m3u"])
 def test_archive_original_list_files_only(self):
  files={"files":[{"name":"tr.m3u","size":"100","source":"original"},
   {"name":"a/az.m3u8","size":"200","source":"original"},
   {"name":"../unsafe.m3u","size":"100","source":"original"},
   {"name":"auto.m3u","size":"100","source":"derivative"}]}
  self.assertEqual(len(archive_file_refs("public-iptv",files)),2)
  self.assertEqual(archive_file_refs("../bad",files),[])
 def test_three_platforms_and_no_playback_claim(self):
  def read(url):
   if "scribd.com/search" in url:return '<a href="https://example.org/tr.m3u">TR</a>'
   if "slideshare.net/search" in url:return '<a href="/slideshow/tv/123">TV</a>'
   if "/slideshow/" in url:return "https://example.org/az.m3u8"
   if "advancedsearch.php" in url:return json.dumps({"response":{"docs":[{"identifier":"item1"}]}})
   if "/metadata/item1" in url:return json.dumps({"files":[{"name":"channels.m3u","size":"100","source":"original"}]})
   raise AssertionError(url)
  report,rows=scan(read=read)
  self.assertEqual(report["source_candidates"],3)
  self.assertEqual(report["errors"],[])
  self.assertEqual(set(report["platforms"]),set(PLATFORMS))
  self.assertFalse(report["playback_verified"])
  self.assertNotIn("https://example.org/tr.m3u",str(report))
  self.assertEqual(len({x["url_sha256"] for x in rows}),3)
 def test_partial_access_does_not_erase_other_sources(self):
  def read(url):
   if "scribd.com" in url:raise OSError("blocked")
   if "slideshare.net" in url:return '<a href="https://example.org/tr.m3u">ok</a>'
   if "advancedsearch.php" in url:return json.dumps({"response":{"docs":[]}})
   raise AssertionError(url)
  report,rows=scan(read=read)
  self.assertEqual(len(rows),1)
  self.assertEqual(report["platforms"]["scribd"]["errors"],len(SEARCH_PAGES["scribd"]))
  self.assertEqual(report["platforms"]["scribd"]["queries"],len(SEARCH_PAGES["scribd"]))
  self.assertEqual(report["coverage_status"],"PARTIAL_PUBLIC_ACCESS")
 def test_archive_reviews_all_48_search_results_including_last_record(self):
  def read(url):
   if "advancedsearch.php" in url:
    return json.dumps({"response":{"numFound":120,"docs":[
     {"identifier":"iptv-item-"+str(i)} for i in range(48)]}})
   if "/metadata/iptv-item-" in url:
    index=int(url.rsplit("iptv-item-",1)[-1])
    files=([{"name":"tr.m3u","size":"150","source":"original"}]
     if index==47 else [])
    return json.dumps({"files":files})
   raise AssertionError("Unexpected document endpoint: "+url)
  report,sources=scan(read=read,search_pages={},document_pages={})
  info=report["platforms"]["internet-archive"]
  self.assertEqual(info["queries"],1)
  self.assertEqual(info["documents_checked"],48)
  self.assertEqual(info["search_rows_returned"],48)
  self.assertEqual(info["indexed_result_count"],120)
  self.assertTrue(info["search_window_limited"])
  self.assertEqual(len(sources),1)
  self.assertEqual(sources[0]["id"],"docref-"+digest(
   "https://archive.org/download/iptv-item-47/tr.m3u")[:20])
  self.assertFalse(report["playback_verified"])
  self.assertEqual(report["errors"],[])

 def test_handoff_rejects_tampering_and_duplicates(self):
  url="https://example.org/tr.m3u";h=digest(url)
  row={"id":"docref-"+h[:20],"kind":"m3u","scope":"candidate",
       "url":url,"url_sha256":h,"platforms":["scribd"]}
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"handoff.json"
   def write(rows):
    p.write_text(json.dumps({"schema":1,"kind":"DOCUMENT_PLATFORM_M3U_HANDOFF","sources":rows}))
   write([row]);self.assertEqual(len(accepted_sources(p)),1)
   for invalid in ([row,row],[dict(row,id="incorrect")],[dict(row,url=url+"?token=1")]):
    write(invalid)
    with self.assertRaises(ValueError):accepted_sources(p)


 def test_m3u_source_validation_blocks_empty_bad_and_retains_good(self):
  from document_platform_discovery import digest
  def src(url):
   return {"url":url,"url_sha256":digest(url),"id":"docref-"+digest(url)[:20],
           "kind":"m3u","scope":"candidate","platforms":["internet-archive"]}
  rows=[src("https://example.org/valid.m3u"),src("https://example.org/empty.m3u"),
        src("https://example.org/failed.m3u")]
  def fetch(url):
   if url.endswith("valid.m3u"):
    return '#EXTM3U\n#EXTINF:-1 tvg-id="TRT1.tr",TRT 1\nhttps://video.example.org/live.m3u8\n'
   if url.endswith("empty.m3u"):return "#EXTM3U\n#EXT-X-STREAM-INF:PROGRAM-ID=1\n"
   raise OSError("unavailable")
  good,report=verify_sources(rows,fetch,resolver=lambda url: True)
  self.assertEqual(len(good),1)
  self.assertEqual(good[0]["id"],rows[0]["id"])
  self.assertEqual([x["status"] for x in report],
      ["M3U_CHANNEL_ENTRIES","NO_CHANNEL_ENTRIES","SOURCE_READ_OR_PARSE_FAILED_OSError"])
  self.assertEqual(sum(x["channel_entries"] for x in report),1)
  self.assertNotIn("https://example.org/",str(report))

 def test_block_private_resolved_document_source_without_fetch(self):
  url="https://example.org/live.m3u"
  row={"url":url,"url_sha256":digest(url),"id":"docref-"+digest(url)[:20],
       "kind":"m3u","scope":"candidate","platforms":["internet-archive"]}
  good,report=verify_sources([row],
    fetcher=lambda url:self.fail("No fetch after unsafe DNS"),
    resolver=lambda url:False)
  self.assertEqual(good,[])
  self.assertEqual(report[0]["status"],"UNSAFE_OR_UNRESOLVABLE_SOURCE_HOST")
  self.assertFalse(report[0]["playback_verified"])

if __name__=="__main__":unittest.main()
