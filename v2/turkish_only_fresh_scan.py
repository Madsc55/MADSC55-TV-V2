#!/usr/bin/env python3
"""Fresh Turkish-only IPTV discovery. Read-only; no foreign channel additions."""
import concurrent.futures,json,urllib.request,subprocess,hashlib,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
API='https://iptv-org.github.io/api/'
def fetch(name):
 with urllib.request.urlopen(API+name,timeout=60) as r:return json.load(r)
def probe(item):
 url=item['url']
 result={'name':item['name'],'channel_id':item['id'],'stream_sha256':hashlib.sha256(url.encode()).hexdigest(),'video':False,'audio':False,'audio_language':None,'status':'FAILED'}
 try:
  p=subprocess.run(['ffprobe','-v','error','-rw_timeout','9000000','-analyzeduration','2000000','-show_entries','stream=codec_type:stream_tags=language','-of','json',url],capture_output=True,text=True,timeout=22)
  if p.returncode: return result
  streams=json.loads(p.stdout).get('streams',[])
  result['audio_language']=next((s.get('tags',{}).get('language') for s in streams if s.get('codec_type')=='audio' and s.get('tags',{}).get('language')),None)
  for kind,label in [('v','video'),('a','audio')]:
   if not any(s.get('codec_type')==('video' if kind=='v' else 'audio') for s in streams):continue
   args=['ffmpeg','-nostdin','-v','error','-rw_timeout','9000000','-i',url,'-map','0:'+kind+':0']
   args+=['-frames:v','1'] if kind=='v' else ['-t','2']
   p=subprocess.run(args+['-f','null','-'],capture_output=True,timeout=25)
   result[label]=p.returncode==0
  lang=(result['audio_language'] or '').lower()
  result['status']='VIDEO_AUDIO_OK_TURKISH_TAG' if result['video'] and result['audio'] and lang in ('tur','tr','turkish') else ('VIDEO_AUDIO_OK_LANGUAGE_REVIEW' if result['video'] and result['audio'] else 'PARTIAL_OR_FAILED')
 except Exception:pass
 return result
def main():
 channels=fetch('channels.json');feeds=fetch('feeds.json');streams=fetch('streams.json')
 languages={}
 for f in feeds:languages.setdefault(f.get('channel'),set()).update(f.get('languages') or [])
 allowed={c['id']:c for c in channels if not c.get('closed') and not c.get('is_nsfw') and (c.get('country')=='TR' or 'tur' in languages.get(c['id'],set()))}
 selected=[];seen=set()
 for s in streams:
  id=s.get('channel');url=s.get('url','')
  if id not in allowed or not url.startswith(('http://','https://')) or s.get('referrer') or s.get('user_agent'):continue
  if url in seen:continue
  seen.add(url)
  selected.append({'id':id,'name':allowed[id]['name'],'url':url})
 print('Turkish candidates:',len(selected),flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:results=list(ex.map(probe,selected))
 out=ROOT/'v2/reports/turkish-only-fresh-scan.json';out.parent.mkdir(parents=True,exist_ok=True)
 summary={'candidate_streams':len(selected),'video_decoded':sum(r['video'] for r in results),'audio_decoded':sum(r['audio'] for r in results),'video_and_audio':sum(r['video'] and r['audio'] for r in results),'turkish_audio_tag':sum(r['status']=='VIDEO_AUDIO_OK_TURKISH_TAG' for r in results),'language_review_required':sum(r['status']=='VIDEO_AUDIO_OK_LANGUAGE_REVIEW' for r in results),'note':'Country/language metadata is only candidate filtering. Turkish spoken language not verified without speech analysis. IBO playlist unchanged.'}
 out.write_text(json.dumps({'summary':summary,'results':results},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
