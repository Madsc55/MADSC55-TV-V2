#!/usr/bin/env bash
# Stage A: evidence-first AV/EPG/recovery, no protected production writes.
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
mkdir -p v2/evidence
command -v python3 >/dev/null || { echo "python3 required" >&2; exit 2; }
command -v ffprobe >/dev/null || { echo "ffprobe required" >&2; exit 2; }
test -s v2/tasks/state.json || { echo "canonical state missing" >&2; exit 2; }
python3 - <<'PY'
import pathlib,subprocess,json,csv,re,concurrent.futures,time,datetime,xml.etree.ElementTree as ET,hashlib
root=pathlib.Path('v2'); ev=root/'evidence'; inp=root/'input'; ev.mkdir(exist_ok=True)
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
sources=sorted([*inp.glob('*.m3u'),*inp.glob('*.m3u8')]) if inp.is_dir() else []
pairs=[]; ids=set(); input_hashes={}
for path in sources:
    data=path.read_bytes()
    input_hashes[str(path)]=hashlib.sha256(data).hexdigest()
    meta=None
    for line in data.decode('utf-8-sig',errors='replace').splitlines():
        line=line.strip()
        if line.startswith('#EXTINF:'):
            meta=line
            m=re.search(r'tvg-id="([^"]+)"',line)
            if m and m.group(1): ids.add(m.group(1))
        elif line.startswith(('http://','https://')):
            if meta: pairs.append((meta,line))
            meta=None
urls=list(dict.fromkeys(u for _,u in pairs))
def probe(url):
    errors=[]
    for i,delay in enumerate((1,2,4),1):
        try:
            p=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json','-rw_timeout','30000000',url],capture_output=True,text=True,timeout=45)
            if p.returncode==0:
                streams=json.loads(p.stdout).get('streams',[])
                types={s.get('codec_type') for s in streams}
                if 'audio' in types and 'video' in types: return [url,'AV_OK',i,'']
                errors.append('missing audio/video: '+','.join(sorted(str(x) for x in types)))
            else: errors.append(p.stderr[-400:].replace('\n',' '))
        except Exception as e: errors.append(str(e))
        if i<3: time.sleep(delay)
    return [url,'NO_AV',3,' | '.join(errors)]
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
    results=list(pool.map(probe,urls))
with (ev/'av_report.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['url','status','attempts','error']);w.writerows(results)
with (ev/'recovery.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['url','status','attempts','error']);w.writerows(r for r in results if r[1]!='AV_OK')
xmlids=set();xml_errors=[]
for path in sorted(inp.glob('*.xml')) if inp.is_dir() else []:
    try:
        for _,element in ET.iterparse(path,events=('end',)):
            if element.tag=='channel' and element.get('id'): xmlids.add(element.get('id'))
            element.clear()
    except Exception as e: xml_errors.append(f'{path}: {e}')
with (ev/'epg_gap.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['tvg_id']);w.writerows((x,) for x in sorted(ids-xmlids))
with (ev/'input_sha256.json').open('w') as f: json.dump(input_hashes,f,indent=2)
status='PASS' if urls and not xml_errors and len(results)==len(urls) else 'BLOCKED'
report=f'''# Stage A acceptance\n\nDate: {stamp}\nStatus: {status}\nM3U source files: {len(sources)}\nUnique URLs: {len(urls)}\nAV_OK: {sum(r[1]=='AV_OK' for r in results)}\nNO_AV: {sum(r[1]!='AV_OK' for r in results)}\nEPG gaps: {len(ids-xmlids)}\nXML parse errors: {len(xml_errors)}\n\nThis report is evidence of scanning only; it does not certify individual tasks or physical playback.\n'''
(ev/'stage_A_acceptance.md').write_text(report)
(ev/'stage_A_errors.log').write_text(('No input M3U files\n' if not urls else '')+'\n'.join(xml_errors)+'\n')
print(report)
if status!='PASS': raise SystemExit(2)
PY
