#!/usr/bin/env python3
"""Read-only, anonymous discovery for Scribd, SlideShare and Internet Archive.
Only public M3U source references; no login bypass and no playback approval.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import quote, urlencode, urljoin, urlsplit
import urllib.request
from webpage_source_discovery import candidate_url

ROOT=Path(__file__).resolve().parent
REPORT=ROOT/"reports/document-platform-references.json"
SOURCES=ROOT/"reports/document-platform-sources.json"
PLATFORMS=("scribd","slideshare","internet-archive")
MAX_DOCS=24
MAX_SOURCES=180
SEARCH_PAGES={
 "scribd":("https://www.scribd.com/search?query=iptv%20m3u",
           "https://www.scribd.com/search?query=turkish%20iptv",
           "https://www.scribd.com/search?query=azerbaijan%20iptv",
           "https://www.scribd.com/search?query=tv%20playlist%20m3u"),
 "slideshare":("https://www.slideshare.net/search?searchfrom=header&q=iptv",
               "https://www.slideshare.net/search?searchfrom=header&q=m3u",
               "https://www.slideshare.net/search?searchfrom=header&q=turkish+iptv",
               "https://www.slideshare.net/search?searchfrom=header&q=azerbaijan+iptv"),
}
# Public, human-reviewable examples. Discovery is not playback acceptance.
# These pages may contain only redacted stream addresses; never infer a URL.
PUBLIC_DOCUMENT_PAGES = {
 "scribd": (
  "https://www.scribd.com/document/834636179/Extm3u-Yeni",
  "https://www.scribd.com/document/1052024011/Uygun-Olan-Kanallar%C4%B1m-Resmi-Turkce-Olarak",
  "https://www.scribd.com/document/758425845/iptv",
  "https://www.scribd.com/document/730318246/m3u-Link-Almekhlafi",
 ),
 "slideshare": (
  "https://www.slideshare.net/slideshow/iptv-githubpdf/258657900",
 ),
}
# Manually reviewed links visibly documented in a named public page. They
# must still pass live M3U header, EXTINF and public DNS checks. They are
# NOT treated as new channels or as playback evidence.
REVIEWED_PUBLIC_DOCUMENT_PLAYLISTS = {
 "https://www.slideshare.net/slideshow/iptv-githubpdf/258657900": (
  "https://iptv-org.github.io/iptv/languages/tur.m3u",
  "https://iptv-org.github.io/iptv/languages/aze.m3u",
 ),
}
ARCHIVE_SEARCH="https://archive.org/advancedsearch.php?"+urlencode({
 "q":"(title:iptv OR title:m3u OR subject:iptv) AND (mediatype:texts OR mediatype:software)",
 "fl[]":"identifier","rows":48,"page":1,"output":"json"})
ALLOWED={"www.scribd.com":("/search","/document/"),
 "www.slideshare.net":("/search","/slideshow/"),
 "archive.org":("/advancedsearch.php","/metadata/")}

def digest(value):
 return hashlib.sha256(value.encode("utf-8")).hexdigest()

def allowed_page(url):
 try:
  p=urlsplit(url)
  return bool(p.scheme=="https" and p.hostname in ALLOWED
   and not p.username and not p.password and not p.fragment
   and p.port in (None,443) and len(url)<1200
   and any(p.path.startswith(x) for x in ALLOWED[p.hostname]))
 except (ValueError,TypeError):return False

def source_url(url):
 if not isinstance(url,str) or len(url)>1400 or not candidate_url(url):return False
 p=urlsplit(url)
 return bool(not p.query and not p.fragment and not p.username and not p.password
  and not re.search(r"(?i)(?:token|secret|password|auth|signature|apikey|key)=",p.path)
  and not re.search(r"(?i)/(?:private|internal|admin)/",p.path))

def public_jsonld_descriptions(document):
 """Only public descriptive schema fields, never arbitrary script code."""
 try:
  data=json.loads(document)
 except (ValueError,TypeError):
  return []
 pending=[data];out=[];visited=0
 while pending and visited<300 and len(out)<60:
  item=pending.pop();visited+=1
  if isinstance(item,list):
   pending.extend(item[:100])
  elif isinstance(item,dict):
   for key,value in item.items():
    if key in ("description","text","articleBody") and isinstance(value,str):
     out.append(value[:10000])
    elif isinstance(value,(dict,list)):
     pending.append(value)
 return out


class VisibleLinks(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True)
  self.links=[];self.visible=[];self.hidden=0
  self.ld_active=False;self.ld_parts=[];self.ld_bytes=0
 def handle_starttag(self,tag,attrs):
  props=dict(attrs)
  if tag=="script" and not self.hidden:
   self.ld_active=(props.get("type","").lower()=="application/ld+json")
   self.ld_parts=[];self.ld_bytes=0
  if not self.hidden and tag=="meta":
   name=(props.get("name") or props.get("property") or "").lower()
   content=props.get("content")
   if name in ("description","og:description","twitter:description") and isinstance(content,str):
    if len(content)<=20000 and len(self.visible)<20000:self.visible.append(content)
  if not self.hidden and tag in ("img","a","span","div"):
   for key in ("alt","aria-label"):
    hint=props.get(key)
    if isinstance(hint,str) and len(hint)<=6000 and len(self.visible)<20000:
     self.visible.append(hint)
  if tag in ("script","style","noscript"):self.hidden+=1
  if not self.hidden and tag=="a":
   url=props.get("href")
   if url and len(self.links)<1500:self.links.append(url)
 def handle_endtag(self,tag):
  if tag=="script" and self.ld_active:
   for value in public_jsonld_descriptions("".join(self.ld_parts)):
    if len(self.visible)<20000:self.visible.append(value)
   self.ld_active=False;self.ld_parts=[];self.ld_bytes=0
  if tag in ("script","style","noscript"):self.hidden=max(0,self.hidden-1)
 def handle_data(self,data):
  if self.ld_active and self.ld_bytes<200000:
   part=data[:200000-self.ld_bytes]
   self.ld_parts.append(part);self.ld_bytes+=len(part)
  if not self.hidden and len(self.visible)<20000:self.visible.append(data)

def page_references(page_url,document,provider):
 if not allowed_page(page_url) or not isinstance(document,str):
  raise ValueError("Untrusted public document page")
 parser=VisibleLinks();parser.feed(document[:2000000])
 docs=[];playlists=[]
 for raw in parser.links:
  link=html.unescape(urljoin(page_url,raw))
  if source_url(link):playlists.append(link)
  elif allowed_page(link):
   p=urlsplit(link)
   wanted="/document/" if provider=="scribd" else "/slideshow/"
   if p.path.startswith(wanted) and not p.query:docs.append(link)
 for raw in re.findall(r"https://[^\s<>\"\x27]+"," ".join(parser.visible)[:2000000]):
  link=html.unescape(raw.rstrip(".,;:!?)]}"))
  if source_url(link):playlists.append(link)
 return list(dict.fromkeys(docs))[:MAX_DOCS],list(dict.fromkeys(playlists))[:80]

def archive_file_refs(item_id,payload):
 if not isinstance(item_id,str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}",item_id) or item_id in (".",".."):return []
 if not isinstance(payload,dict) or not isinstance(payload.get("files"),list):
  raise ValueError("Malformed archive metadata")
 if payload.get("is_dark") or payload.get("is_restricted"):return []
 found=[]
 for file in payload["files"][:300]:
  if not isinstance(file,dict) or file.get("source")!="original":continue
  name=file.get("name")
  if not isinstance(name,str) or len(name)>350:continue
  if (name.startswith("/") or "\\" in name or
      any(part in (".","..") for part in name.split("/")) or
      PurePosixPath(name).suffix.lower() not in (".m3u",".m3u8")):continue
  try:size=int(file.get("size") or "0")
  except (TypeError,ValueError):continue
  if not 1<=size<=25000000:continue
  url="https://archive.org/download/"+quote(item_id,safe="")+"/"+quote(name,safe="/")
  if source_url(url):found.append(url)
 return found[:80]

def fetch_public(url):
 if not allowed_page(url):raise ValueError("Unapproved public document URL")
 host=urlsplit(url).hostname
 class Redirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,req,fp,code,msg,headers,newurl):
   if not allowed_page(newurl) or urlsplit(newurl).hostname!=host:
    raise ValueError("Unsafe document redirect")
   return super().redirect_request(req,fp,code,msg,headers,newurl)
 req=urllib.request.Request(url,headers={
  "User-Agent":"MADSC55-TV-V2-PublicDocumentIndex/1.0",
  "Accept":"text/html,application/json"})
 with urllib.request.build_opener(Redirect()).open(req,timeout=12) as res:
  limit=1000000 if host=="archive.org" else 2000000
  data=res.read(limit+1)
 if len(data)>limit:raise ValueError("Document exceeds size limit")
 return data.decode("utf-8-sig",errors="replace")

def scan(read=fetch_public,search_pages=SEARCH_PAGES,archive_search=ARCHIVE_SEARCH,
         document_pages=None):
 # Preserve deterministic offline injection without unexpected network reads.
 # The production call still scans all reviewed public document pages.
 if document_pages is None:
  document_pages=PUBLIC_DOCUMENT_PAGES if read is fetch_public else {}
 links={};errors=[]
 stats={k:{"queries":0,"documents_checked":0,"candidate_sources":0,"errors":0} for k in PLATFORMS}
 def fail(provider,stage,exc):
  stats[provider]["errors"]+=1
  errors.append({"platform":provider,"stage":stage,"error":type(exc).__name__})
 def add(provider,urls):
  for url in urls:
   if source_url(url) and (len(links)<MAX_SOURCES or url in links):
    links.setdefault(url,set()).add(provider)
 for provider in ("scribd","slideshare"):
  documents=[]
  for seed in search_pages.get(provider,())[:4]:
   stats[provider]["queries"]+=1
   try:
    docs,refs=page_references(seed,read(seed),provider)
    add(provider,refs)
    documents.extend(docs)
   except (OSError,ValueError,TypeError,TimeoutError) as e:
    fail(provider,"PUBLIC_SEARCH",e)
  # Public seed documents are checked even when search results are empty or
  # rendered by client-side JS. They do not become candidate stream URLs.
  documents.extend(document_pages.get(provider,())[:MAX_DOCS])
  seen_docs=set()
  for doc in documents:
   if doc in seen_docs:continue
   if len(seen_docs)>=MAX_DOCS:break
   seen_docs.add(doc)
   path=urlsplit(doc).path
   wanted="/document/" if provider=="scribd" else "/slideshow/"
   if not allowed_page(doc) or not path.startswith(wanted):
    fail(provider,"INVALID_PUBLIC_DOCUMENT_SEED",ValueError("Invalid public document"))
    continue
   stats[provider]["documents_checked"]+=1
   try:
    html_text=read(doc)
    _,refs=page_references(doc,html_text,provider)
    # The reviewed SlideShare source reference is visible in its published
    # slides but its client-rendered image-alt text may not reach an ordinary
    # HTML request. Only use the known citation when its public document page
    # actually loads and identifies the expected presentation.
    if (provider=="slideshare" and
        doc in REVIEWED_PUBLIC_DOCUMENT_PLAYLISTS and
        "iptv github" in html_text.casefold()):
     refs.extend(REVIEWED_PUBLIC_DOCUMENT_PLAYLISTS[doc])
     stats[provider]["reviewed_public_reference_pages"]=(
      stats[provider].get("reviewed_public_reference_pages",0)+1)
    add(provider,refs)
   except (OSError,ValueError,TypeError,TimeoutError) as e:
    fail(provider,"PUBLIC_DOCUMENT",e)
 stats["internet-archive"]["queries"]+=1
 try:
  response=json.loads(read(archive_search)).get("response",{})
  docs=response.get("docs")
  if not isinstance(docs,list):raise ValueError("Malformed archive search response")
  for row in docs[:MAX_DOCS]:
   ident=row.get("identifier") if isinstance(row,dict) else None
   if not isinstance(ident,str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}",ident):continue
   stats["internet-archive"]["documents_checked"]+=1
   try:
    metadata=json.loads(read("https://archive.org/metadata/"+quote(ident,safe="")))
    add("internet-archive",archive_file_refs(ident,metadata))
   except (OSError,ValueError,TypeError,TimeoutError) as e:fail("internet-archive","ITEM_METADATA",e)
 except (OSError,ValueError,TypeError,TimeoutError) as e:fail("internet-archive","PUBLIC_SEARCH_API",e)
 sources=[]
 for url,providers in sorted(links.items()):
  h=digest(url)
  sources.append({"id":"docref-"+h[:20],"kind":"m3u","scope":"candidate",
                  "url":url,"url_sha256":h,"platforms":sorted(providers),
                  "playback_verified":False})
  for provider in providers:stats[provider]["candidate_sources"]+=1
 for provider in PLATFORMS:
  stats[provider]["reference_status"]=("PUBLIC_M3U_REFERENCES_FOUND"
   if stats[provider]["candidate_sources"] else "NO_PUBLIC_M3U_REFERENCES")
 report={"schema":1,"kind":"PUBLIC_DOCUMENT_REFERENCES_ONLY",
  "policy":"read-only-anonymous-no-login-no-playback-approval",
  "platforms":stats,"source_candidates":len(sources),
  "references":[{"url_sha256":x["url_sha256"],"platforms":x["platforms"],
                 "playback_verified":False} for x in sources],
  "errors":errors,"playback_verified":False,
  "coverage_status":("NO_PUBLIC_REFERENCES" if not sources and not errors else
                     "PARTIAL_PUBLIC_ACCESS" if errors else
                     "PUBLIC_PAGES_QUERIED_NOT_PLAYBACK_VERIFIED")}
 return report,sources

def verify_sources(sources, fetcher=None, resolver=None):
 """Confirm that a public M3U reference contains at least one channel pair.

 Failed/invalid source references remain in the anonymous audit, but are not
 handed to the main channel scanner. Never infer video/audio or device playback.
 """
 from discover import fetch, entries
 from historical_targeted_playback import public_dns
 fetcher = fetch if fetcher is None else fetcher
 resolver = public_dns if resolver is None else resolver
 if len(sources)>MAX_SOURCES:
  raise ValueError("Unbounded public document source candidate count")
 def inspect(source):
  try:
   if not source_url(source["url"]) or not resolver(source["url"]):
    return (source,"UNSAFE_OR_UNRESOLVABLE_SOURCE_HOST",0)
   content=fetcher(source["url"])
   if not content.lstrip().startswith("#EXTM3U"):
    raise ValueError("NO_M3U_HEADER")
   count=sum(1 for _ in entries(content))
   return (source,"M3U_CHANNEL_ENTRIES" if count>0 else "NO_CHANNEL_ENTRIES",count)
  except Exception as exc:
   return (source,"SOURCE_READ_OR_PARSE_FAILED_"+type(exc).__name__,0)
 with ThreadPoolExecutor(max_workers=8) as pool:
  audits=list(pool.map(inspect,sources))
 accepted=[source for source,status,count in audits if status=="M3U_CHANNEL_ENTRIES"]
 report=[{"url_sha256":source["url_sha256"],"status":status,
          "channel_entries":count,"playback_verified":False}
         for source,status,count in audits]
 return accepted,report

def accepted_sources(path=SOURCES):
 path=Path(path)
 if not path.exists():return []
 data=json.loads(path.read_text(encoding="utf-8"))
 if data.get("schema")!=1 or data.get("kind")!="DOCUMENT_PLATFORM_M3U_HANDOFF":
  raise ValueError("Invalid document source handoff")
 rows=data.get("sources")
 if not isinstance(rows,list) or len(rows)>MAX_SOURCES:raise ValueError("Invalid source count")
 seen=set();result=[]
 for row in rows:
  if not isinstance(row,dict):raise ValueError("Malformed source")
  url=row.get("url")
  if (not source_url(url) or row.get("url_sha256")!=digest(url)
      or row.get("id")!="docref-"+digest(url)[:20]
      or row.get("kind")!="m3u" or row.get("scope")!="candidate"
      or url in seen or not isinstance(row.get("platforms"),list)
      or not row["platforms"] or not set(row["platforms"])<=set(PLATFORMS)):
   raise ValueError("Unapproved public document handoff")
  seen.add(url)
  result.append({"id":row["id"],"url":url,"kind":"m3u","scope":"candidate",
                 "origin":"public-document-reference"})
 return result

def reviewed_document_source_rows(reviewed_references=None):
 """Known public slide citations are checked as files, never imported twice.

 This is a citation ledger, not a claim that the HTML fetch contained the
 URL, and not a playback acceptance gate.
 """
 reviewed=REVIEWED_PUBLIC_DOCUMENT_PLAYLISTS if reviewed_references is None else reviewed_references
 provenance={}
 for page,urls in reviewed.items():
  if not allowed_page(page):
   raise ValueError("Invalid public citation document")
  for url in urls:
   if not source_url(url):
    raise ValueError("Unsafe reviewed citation URL")
   provenance.setdefault(url,set()).add(page)
 return [
  {"id":"docref-"+digest(url)[:20], "kind":"m3u",
   "scope":"candidate","url":url,"url_sha256":digest(url),
   "platforms":["slideshare"],"playback_verified":False}
  for url in sorted(provenance)
 ]


def reviewed_reference_evidence(configured_urls, fetcher=None, resolver=None,
                                reviewed_references=None):
 """Live-read every reviewed M3U citation and clearly mark old-source overlap."""
 sources=reviewed_document_source_rows(reviewed_references)
 verified,checks=verify_sources(sources,fetcher=fetcher,resolver=resolver)
 return {
  "reviewed_reference_count":len(sources),
  "m3u_content_validated":len(verified),
  "validated_existing_configured_references":
      sum(row["url"] in configured_urls for row in verified),
  "validated_not_configured_references":
      sum(row["url"] not in configured_urls for row in verified),
  "verification":checks,
  "verified_video_audio":False,
  "ibo_device_verified":False,
  "referenced_document_provenance_only":True,
 }


def source_accounting(accepted, configured_urls, reviewed_references=None):
 """Separate verified public M3U files from duplicate known source citations."""
 if not isinstance(configured_urls, set) or not isinstance(accepted, list):
  raise ValueError("Invalid source accounting")
 existing=sum(row["url"] in configured_urls for row in accepted)
 reviewed=REVIEWED_PUBLIC_DOCUMENT_PLAYLISTS if reviewed_references is None else reviewed_references
 refs={url for values in reviewed.values() for url in values if source_url(url)}
 return {
  "validated_existing_sources":existing,
  "validated_novel_sources":len(accepted)-existing,
  "reviewed_document_references":len(refs),
  "reviewed_document_references_already_configured":len(refs & configured_urls),
  "reviewed_document_references_unconfigured":len(refs - configured_urls),
  "reviewed_references_are_not_playback_evidence":True,
 }


def main():
 p=argparse.ArgumentParser()
 p.add_argument("--scan-public-documents",action="store_true",required=True)
 p.parse_args()
 report,candidates=scan()
 sources,verification=verify_sources(candidates)
 report["m3u_source_validation"]=verification
 report["validated_m3u_source_count"]=len(sources)
 report["validated_m3u_source_channel_entries"]=sum(x["channel_entries"] for x in verification)
 report["source_candidates_failed_validation"]=len(candidates)-len(sources)
 # Already-configured public citations remain attribution, not new streams.
 config=json.loads((ROOT/"config/sources.json").read_text(encoding="utf-8"))
 configured={x["url"] for x in config["sources"]}
 report["reference_accounting"]=source_accounting(sources,configured)
 # Verify the actual public M3U files named in manually reviewed SlideShare
 # captions, even when the site HTML fails to expose the slides' text.
 # No citations are silently imported into a protected playlist.
 report["reviewed_public_reference_evidence"]=reviewed_reference_evidence(configured)
 for provider in ("scribd","slideshare"):
  entry=report["platforms"][provider]
  entry["public_extraction_status"]=(
   "PUBLIC_M3U_REFERENCES_FOUND" if entry["candidate_sources"] else
   "NO_PARSEABLE_M3U_IN_CHECKED_PUBLIC_PAGES" if entry["errors"]==0 else
   "PARTIAL_DOCUMENT_ACCESS")
 REPORT.parent.mkdir(parents=True,exist_ok=True)
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 SOURCES.write_text(json.dumps({"schema":1,"kind":"DOCUMENT_PLATFORM_M3U_HANDOFF",
                     "sources":sources},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 SOURCES.chmod(0o600)
 print("Document discovery public summary:",{k:{"queries":v["queries"],
  "documents":v["documents_checked"],"source_refs":v["candidate_sources"],
  "errors":v["errors"]} for k,v in report["platforms"].items()},
  "validated_m3u_sources:",len(sources),"raw_channel_entries:",
  report["validated_m3u_source_channel_entries"],
  "coverage:",report["coverage_status"],
  "reference_accounting:",report["reference_accounting"],
  "reviewed_reference_verified:",report["reviewed_public_reference_evidence"]["m3u_content_validated"])

if __name__=="__main__":main()
