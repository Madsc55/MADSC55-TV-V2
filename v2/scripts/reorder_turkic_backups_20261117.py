#!/usr/bin/env python3
"""Safely prepare a user-authorized Turkic backup reorder. Never writes main directly."""
from pathlib import Path
from collections import Counter
import hashlib, json, re, sys
ROOT=Path(__file__).resolve().parents[2]
PATH=ROOT/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
MANIFEST=ROOT/"v2/ibo_authorized_change.json"
NAMES={"TURKMENİSTAN SPORT (406P) [NOT 24/7]","TURKMENISTAN (406P)","TURKMEN OWAZY (406P)","TURKMENISTAN SPORT (406P)","TURKMEN OWAZY (406P) [NOT 24/7]","TURKMENİSTAN (406P) [NOT 24/7]"}
def parse(raw):
    lines=raw.splitlines(keepends=True)
    prefix=[]; entries=[]; pending=[]; current=None
    for line in lines:
        if line.startswith(b"#EXTINF:"):
            if current is not None: entries.append(current)
            current=[b"".join(pending)+line]; pending=[]
        elif current is not None and line.startswith((b"http://",b"https://")):
            current.append(line)
            entries.append(current); current=None
        elif current is None:
            pending.append(line)
        else:
            current.append(line)
    if current is not None: raise ValueError("incomplete EXTINF record")
    if not entries: raise ValueError("no records")
    return b"".join(prefix),[b"".join(x) for x in entries],b"".join(pending)
def name(record):
    return record.split(b"#EXTINF:",1)[1].splitlines()[0].decode("utf-8").rsplit(",",1)[-1]
def group(record):
    return b'group-title="\xf0\x9f\x97\x82\xef\xb8\x8f YEDEKLER (18074)"' in record
def main():
    original=PATH.read_bytes()
    prefix,items,trailing=parse(original)
    assert len(items)==18912 and sum(map(group,items))==18074
    assert name(items[1751])=="TRT (GREECE) (720P)"
    assert len(items[1003:2398])==1395
    indices=[i for i in range(2398,len(items)) if name(items[i]) in NAMES]
    assert len(indices)==6 and {name(items[i]) for i in indices}==NAMES
    picked=set(indices)
    changed=items[:1003]+[x for i,x in enumerate(items[1003:2398],1003) if i!=1751]+[items[i] for i in indices]+[items[1751]]+[x for i,x in enumerate(items[2398:],2398) if i not in picked]
    assert changed[:1003]==items[:1003]
    assert Counter(changed)==Counter(items) and len(changed)==len(items)
    assert sum(map(group,changed))==18074
    assert name(changed[1003+1394+6])=="TRT (GREECE) (720P)"
    result=prefix+b"".join(changed)+trailing
    assert result!=original
    manifest={"base_sha256":hashlib.sha256(original).hexdigest(),"result_sha256":hashlib.sha256(result).hexdigest(),"operation":"reorder","request":"Kullanıcı 17 Kasım 2026: Türkmenistan ve Azerbaycan dahil Türkî kanalları 1003 sonrası Türk bloğuna al, yabancı TRT Greece'i blok dışına çıkar; tüm kayıtları ve URL'leri koru.","channels":[name(items[i]) for i in indices]+["TRT (GREECE) (720P)"]}
    if "--apply" not in sys.argv:
        print(json.dumps({"dry_run":True,"moves":manifest["channels"],"sha256":manifest["result_sha256"]},ensure_ascii=False,indent=2))
        return
    PATH.write_bytes(result)
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Reordered safely; run security gate before merging.")
if __name__=="__main__":main()
