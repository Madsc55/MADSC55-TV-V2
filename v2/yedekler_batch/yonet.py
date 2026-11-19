#!/usr/bin/env python3
"""YEDEKLER: reversible batch status management; never edits main playlist."""
import argparse,hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
STATE=P/"state.json"
ARCHIVE=P/"YEDEKLER_ARCHIVE.m3u8"
STATES=("ANA_ARSIV","TEST","TURK","YABANCI")

def verify_history(state):
    """Replay the batch transactions against the original unassigned archive."""
    replay = {}
    for event in state["history"]:
        target = event["after"]
        if target not in STATES:
            raise ValueError("Geçersiz arşiv hedefi")
        for key, previous in event["before"].items():
            if (not key.isascii() or not key.isdecimal() or str(int(key)) != key
                    or not 1 <= int(key) <= state["total"]
                    or replay.get(key, "ANA_ARSIV") != previous):
                raise ValueError("Arşiv işlem geçmişi kaynağa uymuyor")
            if target == "ANA_ARSIV":
                replay.pop(key, None)
            else:
                replay[key] = target
    if replay != state["status"]:
        raise ValueError("Arşiv işlem geçmişi güncel durumla uyuşmuyor")

def load():
 s=json.loads(STATE.read_text(encoding="utf-8"))
 if not ARCHIVE.exists(): raise SystemExit("Arşiv eksik; işlem durduruldu")
 if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()!=s["source_sha256"]: raise SystemExit("SHA-256 uyuşmuyor")
 verify_history(s)
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
  if any(v=="TEST" for v in s["status"].values()):raise SystemExit("REFUSED: mevcut TEST paketi bitmeden yeni paket yüklenemez")
  change(s,ids,"TEST","batch");print(len(ids),"kanal TEST havuzuna alındı");return
 if not 1<=x.start<=x.end<=s["total"]:raise SystemExit("Geçersiz aralık")
 ids=list(range(x.start,x.end+1))
 if x.to in ("TURK","YABANCI") and any(s["status"].get(str(i))!="TEST" for i in ids):
  raise SystemExit("REFUSED: yalnız TEST kanalları taşınabilir")
 change(s,ids,x.to,"assign")
 print(len(ids),"kanal",x.to,"arşivine atandı; yeni kanal otomatik yüklenmedi")

if __name__=="__main__":main()
