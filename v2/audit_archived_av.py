#!/usr/bin/env python3
"""Read-only archived-stream audiovisual audit. Never changes the live playlist."""
import argparse,concurrent.futures,json,re,subprocess,hashlib,os
from pathlib import Path
P=Path(__file__).resolve().parents[1]
A=P/'v2/archives/category-rollback-2026-10-29.m3u8'
def records():
 lines=A.read_text(encoding='utf-8-sig').splitlines()
 out=[];info=''
 for line in lines:
  if line.startswith('#EXTINF:'): info=line
  elif line and not line.startswith('#') and info:
   name=info.split(',',1)[-1].strip()
   out.append({'name':name,'url':line.strip(),'metadata':info})
   info=''
 return out
def run(args,timeout=20):
 try:
  p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
  return p.returncode,p.stdout,p.stderr[:400]
 except (subprocess.TimeoutExpired,OSError) as e:return -1,'',str(e)
def check(item):
 url=item['url']
 # Never expose signed/private stream URLs in published reports.
 key=hashlib.sha256(url.encode()).hexdigest()[:20]
 result={'stream_id':key,'name':item['name'],'video_decoded':False,'audio_decoded':False,'audio_language':None,'turkish_status':'REVIEW_REQUIRED'}
 if not url.startswith(('http://','https://')):result['reason']='UNSUPPORTED_SCHEME';return result
 cmd=['ffprobe','-v','error','-rw_timeout','8000000','-analyzeduration','3000000','-probesize','2000000','-show_entries','stream=codec_type,codec_name:stream_tags=language','-of','json',url]
 code,out,err=run(cmd,18)
 if code!=0:result['reason']='PROBE_FAILED';return result
 try: streams=json.loads(out).get('streams',[])
 except ValueError:result['reason']='INVALID_PROBE';return result
 videos=[x for x in streams if x.get('codec_type')=='video']
 audios=[x for x in streams if x.get('codec_type')=='audio']
 result['video_stream_detected']=bool(videos)
 result['audio_stream_detected']=bool(audios)
 result['audio_language']=next((a.get('tags',{}).get('language') for a in audios if a.get('tags',{}).get('language')),None)
 # Decode one frame and a short audio interval separately, to avoid treating a manifest as playback.
 if videos:
  code,_,_=run(['ffmpeg','-nostdin','-v','error','-rw_timeout','8000000','-i',url,'-map','0:v:0','-frames:v','1','-f','null','-'],22)
  result['video_decoded']=code==0
 if audios:
  code,_,_=run(['ffmpeg','-nostdin','-v','error','-rw_timeout','8000000','-i',url,'-map','0:a:0','-t','2','-f','null','-'],22)
  result['audio_decoded']=code==0
 lang=(result['audio_language'] or '').lower()
 if result['video_decoded'] and result['audio_decoded'] and lang in ('tur','tr','turkish'):
  result['turkish_status']='TURKISH_AUDIO_TAG_CANDIDATE'
 elif lang and lang not in ('und','tur','tr','turkish'):
  result['turkish_status']='NON_TURKISH_AUDIO_TAG'
 result['reason']='TESTED'
 return result
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--shard',type=int,required=True);ap.add_argument('--shards',type=int,default=16)
 ap.add_argument('--workers',type=int,default=5)
 args=ap.parse_args()
 data=records()
 assert len(data)==11810, f'Expected 11810 archived entries, got {len(data)}'
 selection=[x for i,x in enumerate(data) if i%args.shards==args.shard]
 with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
  results=list(ex.map(check,selection))
 out=P/'v2/reports/av-audit'
 out.mkdir(parents=True,exist_ok=True)
 file=out/f'shard-{args.shard:02}.json'
 file.write_text(json.dumps({'total_archive':len(data),'shard':args.shard,'shards':args.shards,'tested':len(results),'results':results},ensure_ascii=False,indent=1)+'\n')
 print('Shard',args.shard,'tested',len(results),'video',sum(x['video_decoded'] for x in results),'audio',sum(x['audio_decoded'] for x in results))
if __name__=='__main__':main()
