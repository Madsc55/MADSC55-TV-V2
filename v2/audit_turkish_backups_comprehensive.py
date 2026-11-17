#!/usr/bin/env python3
"""Audit remaining YEDEKLER Turkish candidates; default is read-only.

Metadata/URL hints are not spoken-language proof. --apply moves only strong
identity matches, preserves EXTINF+URL pairs and checks the protected prefix.
"""
import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PLAYLIST = ROOT / "MADSC55_TV_IBO_YEDEKLER_DUZELTILMIS_TEST.m3u8"
TR_CITIES = ("ADANA ADIYAMAN AFYON AGRI AKSARAY AMASYA ANKARA ANTALYA ARTVIN AYDIN "
"BALIKESIR BARTIN BATMAN BAYBURT BILECIK BINGOL BITLIS BOLU BURDUR BURSA "
"CANAKKALE CANKIRI CORUM DENIZLI DIYARBAKIR DUZCE EDIRNE ELAZIG ERZINCAN "
"ERZURUM ESKISEHIR GAZIANTEP GIRESUN GUMUSHANE HAKKARI HATAY IGDIR ISPARTA "
"ISTANBUL IZMIR KAHRAMANMARAS KARABUK KARAMAN KARS KASTAMONU KAYSERI KILIS "
"KIRIKKALE KIRKLARELI KIRSEHIR KOCAELI KONYA KUTAHYA MALATYA MANISA MARDIN "
"MERSIN MUGLA MUS NEVSEHIR NIGDE ORDU OSMANIYE RIZE SAKARYA SAMSUN SANLIURFA "
"SIIRT SINOP SIRNAK SIVAS TEKIRDAG TOKAT TRABZON TUNCELI USAK VAN YALOVA YOZGAT ZONGULDAK").split()
CITY_RE = re.compile(r"\b(?:" + "|".join(TR_CITIES) + r")\b")
TR_RE = re.compile(r"\b(?:TURK|TURKCE|TURKIYE|TURKEY|TURKISH|TR)\b|(?:^|[.])TR(?:[.@]|$)")
TV_RE = re.compile(r"\b(?:TV|TELEVIZYON|KANAL|HABER|RADYO|LIVE|CANLI)\b")
NEGATIVE = re.compile(r"\b(?:TURKMENISTAN|TURKMEN|TURKMENELI|TRAVEL|TOURISM|MOVIE|FILM|SERIES|VOD|EPISODE)\b|S\d+E\d+")
KNOWN = re.compile(r"\b(?:TRT|HABERTURK|CNNTURK|EKOTURK|TGRT|TV100|TELE1|SOZCU|MINIKA|LALEGUL|AKSU TV|ETV KAYSERI|KANAL 23|AS TV BURSA)\b")
ATTR = re.compile(r'([\w-]+)="([^"]*)"')

def norm(value):
    value = value.replace("ı", "i").replace("İ", "I")
    return "".join(c for c in unicodedata.normalize("NFKD", value.upper()) if not unicodedata.combining(c))

def parse(text):
    lines = text.splitlines(keepends=True)
    entries = []
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF:"):
            if i + 1 >= len(lines) or lines[i+1].startswith("#"):
                raise ValueError("Invalid EXTINF/URL pair at line " + str(i+1))
            entries.append((i, line, lines[i+1]))
    return lines, entries

def classify(meta, url):
    attrs = dict(ATTR.findall(meta))
    title = meta.split(",", 1)[-1].strip() if "," in meta else ""
    identity = norm(" ".join((title, attrs.get("tvg-name",""), attrs.get("tvg-id",""))))
    group = norm(attrs.get("group-title",""))
    host = norm(urlsplit(url.strip()).hostname or "")
    reasons = []
    if TR_RE.search(identity): reasons.append("identity-tr")
    if KNOWN.search(identity): reasons.append("known-station")
    if CITY_RE.search(identity) and TV_RE.search(identity): reasons.append("regional-station")
    if TR_RE.search(group) and "YEDEKLER" not in group: reasons.append("group-tr")
    if host.endswith(".COM.TR") or host.endswith(".GOV.TR") or host.endswith(".ORG.TR") or host.endswith(".NET.TR"): reasons.append("turkish-host")
    if NEGATIVE.search(identity): return "review", ["ambiguous-or-vod"] + reasons
    if any(x in reasons for x in ("identity-tr", "known-station", "regional-station")):
        return "strong", reasons
    if reasons: return "review", reasons
    return "none", []

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", default="v2/reports/turkish-backups-comprehensive.json")
    args = parser.parse_args()
    old = PLAYLIST.read_text(encoding="utf-8-sig")
    lines, entries = parse(old)
    original = [(meta, url) for _,meta,url in entries]
    backup = [(i, meta, url) for i,meta,url in entries if "YEDEKLER" in dict(ATTR.findall(meta)).get("group-title","").upper()]
    findings = []
    selected = []
    for i,meta,url in backup:
        level,reasons = classify(meta,url)
        if level == "none": continue
        title = meta.split(",",1)[-1].strip()
        findings.append({"entry_index": next(j+1 for j,e in enumerate(entries) if e[0]==i),
                         "name":title,"level":level,"reasons":reasons,
                         "url_sha256":hashlib.sha256(url.strip().encode()).hexdigest()})
        if level=="strong": selected.append(i)
    report = {"total_entries":len(entries),"backup_entries":len(backup),
              "strong_candidates":len(selected),"review_candidates":sum(f["level"]=="review" for f in findings),
              "spoken_turkish_verified":False,"findings":findings}
    out = ROOT / args.report
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if args.apply:
        # The user explicitly excluded 48 blocked/error entries from the 18,122
        # YEDEKLER pool. Never reorder them until they can be identified precisely.
        if len(backup) != 18074:
            raise SystemExit(
                f"BLOCKED: found {len(backup)} YEDEKLER entries, expected exactly 18074 eligible. "
                "Identify and exclude the 48 blocked/error entries before any move."
            )
        if not selected: raise SystemExit("No strong candidates: refusing no-op")
        # Reorder intact EXTINF+URL pairs immediately after protected 1003 entries.
        selected_set=set(selected)
        prefix_end=entries[1002][0]+2
        if any(i < prefix_end for i in selected): raise SystemExit("Protected prefix overlap")
        chunks=[(meta,url) for _,meta,url in entries]
        chosen=[(meta,url) for i,meta,url in entries if i in selected_set]
        remaining=[(meta,url) for i,meta,url in entries if i not in selected_set]
        # Preserve all non-channel header lines by requiring the conventional two-line layout.
        if len(lines)!=1+2*len(entries) or not lines[0].startswith("#EXTM3U"):
            raise SystemExit("Non-standard layout: audit only; do not apply")
        rebuilt=[lines[0]]
        for meta,url in remaining[:1003]+chosen+remaining[1003:]:
            rebuilt.extend((meta,url))
        result="".join(rebuilt)
        _,after=parse(result)
        if len(after)!=len(entries) or sorted((m,u) for _,m,u in after)!=sorted(original):
            raise SystemExit("Playlist integrity check failed")
        if [(m,u) for _,m,u in after[:1003]]!=original[:1003]:
            raise SystemExit("Protected first 1003 changed")
        PLAYLIST.write_text(result,encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="findings"},ensure_ascii=False))
if __name__=="__main__":
    main()
