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

class VisibleLinks(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True)
  self.links=[];self.visible=[];self.hidden=0
 def handle_starttag(self,tag,attrs):
  if tag in ("script","style","noscript"):self.hidden+=1
  if not self.hidden and tag=="a":
   url=dict(attrs).get("href")
   if url and len(self.links)<1500:self.links.append(url)
 def handle_endtag(self,tag):
  if tag in ("script","style","noscript"):self.hidden=max(0,self.hidden-1)
 def handle_data(self,data):
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

def scan(read=fetch_public,search_pages=SEARCH_PAGES,archive_search=ARCHIVE_SEARCH):
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
  for seed in search_pages.get(provider,())[:4]:
   stats[provider]["queries"]+=1
   try:docs,refs=page_references(seed,read(seed),provider);add(provider,refs)
   except (OSError,ValueError,TypeError,TimeoutError) as e:
    fail(provider,"PUBLIC_SEARCH",e);continue
   for doc in docs[:MAX_DOCS]:
    stats[provider]["documents_checked"]+=1
    try:_,refs=page_references(doc,read(doc),provider);add(provider,refs)
    except (OSError,ValueError,TypeError,TimeoutError) as e:fail(provider,"PUBLIC_DOCUMENT",e)
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
  "coverage:",report["coverage_status"])

if __name__=="__main__":main()
