#!/usr/bin/env bash
# Evidence-first runner. Does not certify hardware playback or overwrite protected IBO.
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
mkdir -p v2/evidence v2/packages v2/evidence/device_results
command -v python3 >/dev/null
command -v ffprobe >/dev/null
test -s v2/tasks/state.json || { echo "Missing canonical state.json" >&2; exit 2; }
find v2/input -maxdepth 1 -type f \( -name '*.m3u' -o -name '*.m3u8' \) -print -quit | grep -q . || { echo "No input M3U files" >&2; exit 2; }
python3 - <<'PY'
import pathlib, json, csv, concurrent.futures, subprocess, time, hashlib, datetime, xml.etree.ElementTree as ET
root=pathlib.Path('v2'); ev=root/'evidence'; pk=root/'packages'; inp=root/'input'
entries=[]
for f in sorted(list(inp.glob('*.m3u'))+list(inp.glob('*.m3u8'))):
    meta=None
    for line in f.read_text(encoding='utf-8-sig',errors='replace').splitlines():
        line=line.strip()
        if line.startswith('#EXTINF:'): meta=line
        elif line.startswith(('http://','https://')):
            if meta: entries.append((meta,line))
            meta=None
urls=list(dict.fromkeys(u for _,u in entries))
if not urls: raise SystemExit('No EXTINF+URL pairs')
def probe(u):
    err=''
    for attempt in range(3):
        try:
            r=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json','-rw_timeout','30000000',u],capture_output=True,text=True,timeout=45)
            if r.returncode==0:
                streams=json.loads(r.stdout).get('streams',[])
                kinds={s.get('codec_type') for s in streams}
                if {'video','audio'} <= kinds: return (u,'AV_OK',attempt+1,'')
                err='missing video or audio'
            else: err=r.stderr[-500:]
        except Exception as e: err=str(e)
        time.sleep((1,2,4)[attempt])
    return (u,'NO_AV',3,err)
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    results=list(ex.map(probe,urls))
with (ev/'av_report.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['url','status','attempts','error']);w.writerows(results)
with (ev/'recovery.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['url','status','attempts','error']);w.writerows(r for r in results if r[1]!='AV_OK')
ids=set()
import re
for f in list(inp.glob('*.m3u'))+list(inp.glob('*.m3u8')):
    ids.update(re.findall(r'tvg-id="([^"]+)"',f.read_text(errors='replace')))
xmlids=set(); xml_errors=[]
for f in inp.glob('*.xml'):
    try: xmlids.update(c.get('id','') for c in ET.parse(f).iter('channel'))
    except Exception as e: xml_errors.append(str(f)+': '+str(e))
with (ev/'epg_gap.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['missing_tvg_id']);w.writerows((x,) for x in sorted(ids-xmlids))
if xml_errors: (ev/'epg_errors.log').write_text('\n'.join(xml_errors)+'\n')
verified={u for u,s,_,_ in results if s=='AV_OK'}
dedup={}
for m,u in entries:
    if u in verified: dedup.setdefault(u,m)
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
packages=[]
for size in (1000,2000):
    rows=list(dedup.items())
    for offset in range(0,len(rows),size):
        chunk=rows[offset:offset+size]
        path=pk/f'ibo_{size}_{offset//size+1:03}.m3u'
        if path.exists(): raise SystemExit('Refusing to overwrite existing package: '+str(path))
        path.write_text('#EXTM3U\n'+''.join(m+'\n'+u+'\n' for u,m in chunk))
        manifest={'channel_count':len(chunk),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'date':stamp}
        (pk/(path.name+'.manifest.json')).write_text(json.dumps(manifest,indent=2))
        packages.append(str(path))
(ev/'package_manifest.json').write_text(json.dumps({'date':stamp,'verified_channels':len(dedup),'packages':packages},indent=2))
(ev/'device_checklist.md').write_text('# Device acceptance — #28–#32\n\nTest M3U import, first/middle/last channels, video and audio on Android TV, IPTV box and Smart TV where available. Record device model, firmware, player, timestamp, result and screenshot/video paths in v2/evidence/device_results/. Physical device verification is mandatory.\n')
(ev/'stage_A_acceptance.md').write_text(f'# Stage A\n\nProbed URLs: {len(urls)}\nAV_OK: {len(verified)}\nEPG gaps: {len(ids-xmlids)}\nXML parse errors: {len(xml_errors)}\n')
PY
python3 - <<'PY'
import pathlib,json,datetime,subprocess,os,hashlib
ev=pathlib.Path('v2/evidence'); packages=sorted(pathlib.Path('v2/packages').glob('ibo_*.m3u'))
result={'status':'failed','reason':'No verified packages or ARCHIVE_PASS / 7z unavailable'}
if packages and os.getenv('ARCHIVE_PASS') and subprocess.run(['which','7z'],capture_output=True).returncode==0:
    arc=ev/'ibo_verified.7z'
    if arc.exists(): raise SystemExit('Refusing to overwrite archive')
    password=os.environ['ARCHIVE_PASS']
    cmd=['7z','a','-y','-mhe=on','-p'+password,str(arc),*[str(p) for p in packages]]
    a=subprocess.run(cmd,capture_output=True,text=True)
    t=subprocess.run(['7z','t','-p'+password,str(arc)],capture_output=True,text=True) if a.returncode==0 else a
    if a.returncode==0 and t.returncode==0:
        sha=hashlib.sha256(arc.read_bytes()).hexdigest()
        (ev/'ibo_verified.7z.sha256').write_text(sha+'  ibo_verified.7z\n')
        v=subprocess.run(['sha256sum','-c','ibo_verified.7z.sha256'],cwd=ev,capture_output=True)
        if v.returncode==0: result={'status':'ok','sha256':sha,'archive':str(arc)}
    if result['status']!='ok': result['reason']='7z archive creation, test or SHA256 failed'
(ev/'archive_result.json').write_text(json.dumps(result,indent=2))
PY
python3 - <<'PY'
import pathlib,json,csv,datetime
root=pathlib.Path('v2'); ev=root/'evidence'; state=root/'tasks/state.json'
data=json.loads(state.read_text()); statuses=data.get('statuses')
if not isinstance(statuses,list): raise SystemExit('Unexpected state schema; refusing modification')
ids={15,17,18,19,20,21,28,29,30,31,32,33,34}
device={28,29,30,31,32}
files={15:'av_report.csv',17:'epg_gap.csv',18:'recovery.csv',19:'av_report.csv',20:'recovery.csv',21:'av_report.csv',33:'archive_result.json',34:'discovery_result.json'}
av_ok=sum(r['status']=='AV_OK' for r in csv.DictReader((ev/'av_report.csv').open()))
archive_ok=json.loads((ev/'archive_result.json').read_text()).get('status')=='ok'
# Per-task acceptance cannot be inferred from one generic CSV. Keep all unverified tasks open.
for t in statuses:
    n=t.get('id')
    if n not in ids: continue
    if n in device:
        t['status']='pending_device';t['evidence']='v2/evidence/device_checklist.md'
    else:
        t['status']='failed'
        log=ev/f'task_{n}_error.log'
        reason=('Discovery has not been independently verified' if n==34 else
                'Independent archive restore unverified' if n==33 else
                'Per-task acceptance not established by generic AV/EPG evidence')
        log.write_text(reason+'\n')
        t['error_log']=str(log)
        t.pop('evidence',None)
counts={k:sum(t.get('status')==k for t in statuses if t.get('id') in ids) for k in ('done','pending_device','failed')}
for t in statuses:
    if t.get('id') in ids and t.get('status')=='done':
        p=pathlib.Path(t.get('evidence',''))
        if not p.is_file() or p.stat().st_size==0:
            t['status']='failed';counts['done']-=1;counts['failed']+=1
state.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
(ev/'FINAL_ACCEPTANCE.md').write_text('# FINAL ACCEPTANCE\n\n'+''.join(f'- {k}: {v}\n' for k,v in counts.items())+f'\nAV_OK streams: {av_ok}\nArchive verified: {archive_ok}\n\nDevice and independent acceptance still required.\n')
print((ev/'FINAL_ACCEPTANCE.md').read_text())
PY
