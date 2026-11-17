#!/usr/bin/env python3
"""Regression checks for protected user-authorized playlist staging."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PLAY=ROOT/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
def run(script,*args):
    return subprocess.run([sys.executable,str(ROOT/"v2"/script),*map(str,args)],capture_output=True,text=True)
def main():
    original=PLAY.read_bytes()
    with tempfile.TemporaryDirectory() as d:
        d=Path(d)
        staged=d/"turkish.m3u8"
        report=d/"turkish.json"
        r=run("prepare_authorized_turkish_backups.py","--input",PLAY,"--output",staged,"--report",report)
        assert r.returncode==0,r.stderr+r.stdout
        assert staged.exists() and report.exists()
        info=json.loads(report.read_text())
        assert info["status"]=="REVIEW_REQUIRED_NOT_PUBLISHED"
        assert info["total"]==18912 and info["yedekler"]==18074
        assert PLAY.read_bytes()==original
        assert run("prepare_authorized_turkish_backups.py","--input",PLAY,"--output",staged,"--report",report).returncode!=0
        bad=d/"bad.json"
        bad.write_text(json.dumps({"approved":False,"placements":[]}))
        assert run("stage_approved_backup_placements.py","--input",PLAY,"--manifest",bad,"--output",d/"bad.m3u8","--report",d/"bad-report.json").returncode!=0
        assert not (d/"bad.m3u8").exists()
        missing=d/"missing.json"
        missing.write_text(json.dumps({"approved":True,"placements":[{"backup_name":"DOES_NOT_EXIST","target":"HABER","av_verified":True,"av_evidence":"https://example.org/evidence"}]}))
        assert run("stage_approved_backup_placements.py","--input",PLAY,"--manifest",missing,"--output",d/"missing.m3u8","--report",d/"missing-report.json").returncode!=0
        assert PLAY.read_bytes()==original
    print("PASS: staged preparation, 18,912 inventory, 18,074 backups, no overwrite, unauthorized placement rejected, live playlist unchanged")
if __name__=="__main__":main()
