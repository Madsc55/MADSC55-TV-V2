#!/usr/bin/env python3
"""Prepare user-authorized Turkish YEDEKLER ordering; never publish to main."""
import argparse
import hashlib
import json
import re
from pathlib import Path

PLAY = "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
TR_NAME = re.compile(r"^(?:TR[: |\\-]|TURKEY[: |\\-]|TÜRKİYE[: |\\-])|(?:\\bTRT\\b|\\bKANAL [D7]\\b|\\bSHOW TV\\b|\\bATV\\b|\\bSTAR TV\\b|\\bHABER\\b|\\bTÜRK\\b|\\bTURK\\b|\\bULUSAL\\b|\\bYEREL\\b|\\bSPOR\\b|\\bÇOCUK\\b|\\bCOCUK\\b|\\bDİYANET\\b|\\bDIYANET\\b|\\bSÖZCÜ\\b|\\bSOZCU\\b|\\bHALK TV\\b|\\bTELE1\\b|\\bTV8\\b|\\bA HABER\\b|\\bBEYAZ TV\\b|\\bTGRT\\b|\\bKRT\\b|\\bNTV\\b|\\bCNN TÜRK\\b|\\bFLASH TV\\b|\\bÜLKE TV\\b|\\bVAV TV\\b|\\bDHA\\b|\\bRİZE\\b|\\bRIZE\\b|\\bTRABZON\\b|\\bKARADENİZ\\b|\\bKARADENIZ\\b)", re.I)
NOT_TR = re.compile(r"TRT WORLD|TRT ARABI|TRT ARABIC", re.I)

def split(data):
    start = data.index("#EXTINF:")
    header = data[:start]
    blocks = re.findall(r"^#EXTINF:[\\s\\S]*?(?=^#EXTINF:|\\Z)", data[start:], re.M)
    return header, blocks

def candidate(block):
    line = block.splitlines()[0]
    name = line.rsplit(",", 1)[-1].strip()
    return not NOT_TR.search(name) and bool(TR_NAME.search(name) or re.search(r"countries/turkey/|turkiye|türkiye", line, re.I))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=PLAY)
    p.add_argument("--output", required=True)
    p.add_argument("--report", required=True)
    args = p.parse_args()
    source = Path(args.input).read_bytes()
    data = source.decode("utf-8-sig")
    header, blocks = split(data)
    if len(blocks) != 18912 or sum('group-title="🗂️ YEDEKLER (18074)"' in b.splitlines()[0] for b in blocks) != 18074:
        raise SystemExit("Protected inventory baseline mismatch")
    if any("YEDEKLER" in b.splitlines()[0] for b in blocks[:838]):
        raise SystemExit("Protected categories changed")
    before = blocks[:1003]
    after = blocks[1003:]
    selected = [b for b in after if candidate(b)]
    remainder = [b for b in after if not candidate(b)]
    result = header + "".join(before + selected + remainder)
    _, check = split(result)
    if len(check) != len(blocks) or check[:1003] != before or sorted(check) != sorted(blocks):
        raise SystemExit("Lossless ordering validation failed")
    if Path(args.output).exists() or Path(args.report).exists():
        raise SystemExit("Refusing to overwrite an existing output")
    Path(args.output).write_bytes(result.encode("utf-8"))
    report = {"status":"REVIEW_REQUIRED_NOT_PUBLISHED", "source_sha256":hashlib.sha256(source).hexdigest(),
              "output_sha256":hashlib.sha256(result.encode()).hexdigest(), "total":len(blocks),
              "yedekler":18074,"unchanged_prefix":1003,"selected_turkish_candidates":len(selected),
              "unclassified_remaining":len(remainder),
              "note":"Name/logo hints are not independent Turkish channel identity or AV evidence; review before production."}
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))

if __name__ == "__main__":
    main()
