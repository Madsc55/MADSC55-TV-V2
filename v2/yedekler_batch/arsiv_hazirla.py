#!/usr/bin/env python3
"""Safely derive the YEDEKLER archive from a supplied snapshot, never editing it."""
import argparse,hashlib,json,re
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument("playlist",type=Path);p.add_argument("--expected",type=int,default=18074);x=p.parse_args()
 raw=x.playlist.read_bytes();text=raw.decode("utf-8-sig");lines=text.splitlines(keepends=True)
 out=["#EXTM3U\n"];count=0;i=0
 while i<len(lines):
  line=lines[i]
  if line.startswith("#EXTINF"):
   block=[line];i+=1
   while i<len(lines) and not lines[i].startswith("#EXTINF"):
    block.append(lines[i]);i+=1
   if re.search(r'group-title=["\'][^"\']*YEDEKLER',line,re.I):
    out.extend(block);count+=1
  else:i+=1
 if count!=x.expected:raise SystemExit(f"İPTAL: beklenen {x.expected}, bulunan {count}; dosya yazılmadı")
 archive="".join(out).encode("utf-8")
 state_path=Path(__file__).resolve().parent/"state.json"
 state=json.loads(state_path.read_text())
 if state["status"] or state["history"]:raise SystemExit("İPTAL: mevcut çalışma geçmişi var")
 actual=hashlib.sha256(archive).hexdigest()
 if actual!=state["source_sha256"]:raise SystemExit("İPTAL: kaynak arşiv SHA-256 eşleşmiyor; dosya yazılmadı: "+actual)
 path=state_path.parent/"YEDEKLER_ARCHIVE.m3u8"
 path.write_bytes(archive)
 print(f"Doğrulandı: {count} kanal, SHA-256 {actual}")
if __name__=="__main__":main()
