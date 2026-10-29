#!/usr/bin/env python3
"""Probe pending streams without adding unverified or non-Turkish channels."""
import json,concurrent.futures,urllib.request,urllib.error,datetime
from pathlib import Path
root=Path(__file__).resolve().parents[1]
src=root/'v2/reports/turkish-discovery.json'
data=json.loads(src.read_text(encoding='utf-8'))
items=data['new_streams_pending_live_probe']
def probe(item):
 url=item['url']
 result={'name':item['name'],'id':item['id'],'url':url,'status':'failed','http_status':None}
 if not url.startswith(('http://','https://')):return result
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/vnd.apple.mpegurl,application/x-mpegURL,*/*'})
  with urllib.request.urlopen(req,timeout=12) as response:
   body=response.read(262144)
   result['http_status']=response.status
   text=body.decode('utf-8','replace')
   typ=response.headers.get('Content-Type','').lower()
   if '#EXTM3U' in text[:1000] and ('#EXT-X-STREAM-INF' in text or '#EXTINF:' in text or '#EXT-X-TARGETDURATION' in text):
    result['status']='hls_manifest_ok'
   elif '#EXTM3U' in text[:1000]:result['status']='m3u_unverified'
   elif 'video/mp2t' in typ:result['status']='transport_stream_unverified'
   else:result['status']='not_hls'
 except Exception as e:result['error']=str(e)[:180]
 return result
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:results=list(pool.map(probe,items))
report={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checked':len(results),'manifest_ok':sum(r['status']=='hls_manifest_ok' for r in results),'failed_or_unverified':sum(r['status']!='hls_manifest_ok' for r in results),'limitations':'Manifest accessibility is not proof of decodable video, Turkish language, rights or IBO compatibility','results':results}
dest=root/'v2/reports/turkish-live-probe.json';dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='results'},ensure_ascii=False))
