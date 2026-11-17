#!/usr/bin/env python3
"""YEDEKLER: reversible batch status management; never edits main playlist."""
import argparse,hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
STATE=P/"state.json"
ARCHIVE=P/"YEDEKLER_ARCHIVE.m3u8"
STATES=("ANA_ARSIV","TEST","TURK","YABANCI")
def load():
 s=json.loads(STATE.read_text(encoding="utf-8"))
 if not ARCHIVE.exists(): raise SystemExit("Arşiv eksik; işlem durduruldu")
 if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()!=s["source_sha256"]: raise SystemExit("SHA-256 uyuşmuyor")
 return s
def save(s):
 tmp=STATE.with_suffix(".tmp");tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8");tmp.replace(STATE)
def change(s,ids,to,action):
 before={str(i):s["status"].get(str(i),"ANA_ARSIV") for i in ids}
 for i in ids:
  if to=="ANA_ARSIV":s["status"].pop(str(i),None)
  else:s["status"][str(i)]=to
 s["history"].append({"action":action,"before":before,"after":to})
 save(s)
def main():
 p=argparse.ArgumentParser();sp=p.add_subparsers(dest="cmd",required=True)
 b=sp.add_parser("batch");b.add_argument("--count",type=int)
 a=sp.add_parser("assign");a.add_argument("--start",type=int,required=True);a.add_argument("--end",type=int,required=True);a.add_argument("--to",choices=STATES,required=True)
 sp.add_parser("undo");sp.add_parser("status");x=p.parse_args();s=load()
 if x.cmd=="status":
  print(json.dumps({v:sum(s["status"].get(str(i),"ANA_ARSIV")==v for i in range(1,s["total"]+1)) for v in STATES},ensure_ascii=False));return
 if x.cmd=="undo":
  if not s["history"]:raise SystemExit("Geri alınacak işlem yok")
  last=s["history"].pop()
  for k,v in last["before"].items():
   if v=="ANA_ARSIV":s["status"].pop(k,None)
   else:s["status"][k]=v
  save(s);print("Geri alındı");return
 if x.cmd=="batch":
  n=x.count if x.count is not None else s["default_batch_size"]
  if not 1<=n<=s["total"]:raise SystemExit("Geçersiz paket boyutu")
  ids=[i for i in range(1,s["total"]+1) if s["status"].get(str(i),"ANA_ARSIV")=="ANA_ARSIV"][:n]
  if not ids:raise SystemExit("Bekleyen kanal yok")
  change(s,ids,"TEST","batch");print(len(ids),"kanal TEST havuzuna alındı");return
 if not 1<=x.start<=x.end<=s["total"]:raise SystemExit("Geçersiz aralık")
 change(s,list(range(x.start,x.end+1)),x.to,"assign");print("Atama tamamlandı")
if __name__=="__main__":main()
