#!/usr/bin/env python3
"""Make a PRIVATE, separate IBO test list only from authenticated FFmpeg AV evidence.

The user supplies the RSA private key LOCALLY. Never commit, publish, upload
or automatically promote an unencrypted M3U into the protected main playlist.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from discover import ROOT
from traz_api_source_batch import public_stream

REPORTS = ROOT / "v2/reports"
DEFAULT_REPORT = REPORTS / "ci/traz-api-av-acceptance.json"
DEFAULT_SEALED = REPORTS / "ci/traz-api-av-evidence.sealed"
DEFAULT_OUT = REPORTS / "private-verified-ibo-device-test.m3u8"
HASH = __import__("re").compile(r"[0-9a-f]{64}\Z")


def esc(value):
    return str(value or "").replace("\r", " ").replace("\n", " ").replace('"', "'").strip()[:160]


def select(report, decrypted):
    if (not isinstance(report,dict)
            or report.get("schema")!=1
            or report.get("kind")!="TR_AZ_IPTV_API_REAL_FFMPEG_AV_ACCEPTANCE"
            or report.get("policy")!="ANONYMOUS_HASH_ONLY_RSA_ENCRYPTED_URLS"
            or report.get("protected_playlist_modified") is not False
            or report.get("ibo_device_verified") is not False
            or not isinstance(decrypted,list)):
        raise ValueError("Invalid AV report or authenticated rows")
    references=report.get("streams")
    if (not isinstance(references,list)
            or len(references)!=report.get("unique_url_candidates")
            or len(decrypted)!=len(references)):
        raise ValueError("Report and authenticated archive disagree")
    expected={}
    for item in references:
        if not isinstance(item,dict) or "url" in item:
            raise ValueError("Public report must contain hashes only")
        digest=item.get("url_sha256")
        if not isinstance(digest,str) or not HASH.fullmatch(digest) or digest in expected:
            raise ValueError("Invalid or duplicate public digest")
        expected[digest]=item
    matched=set()
    accepted=[]
    ambiguous=0
    for item in decrypted:
        if not isinstance(item,dict):
            raise ValueError("Invalid decrypted record")
        url=item.get("url")
        digest=item.get("url_sha256")
        if (not isinstance(url,str) or not public_stream(url)
                or any(ord(c)<32 for c in url)
                or digest!=hashlib.sha256(url.encode("utf-8")).hexdigest()
                or digest not in expected or digest in matched):
            raise ValueError("URL/hash or record mismatch")
        matched.add(digest)
        proof=expected[digest]
        if (item.get("status") not in (None,"VIDEO_AUDIO_DECODED")
                and item.get("probe_status")!="VIDEO_AUDIO_DECODED"):
            # Unsuccessful evidence can be retained but cannot be exported.
            pass
        for field in ("video","audio","decoded"):
            if item.get(field) is True and proof.get(field) is not True:
                raise ValueError("Decrypted AV evidence exceeds public proof")
        if item.get("probe_status")!=proof.get("status"):
            raise ValueError("Conflicting AV probe status")
        if (proof.get("status")!="VIDEO_AUDIO_DECODED"
                or proof.get("video") is not True
                or proof.get("audio") is not True
                or proof.get("decoded") is not True
                or item.get("video") is not True
                or item.get("audio") is not True
                or item.get("decoded") is not True):
            continue
        ids=item.get("channel_ids")
        if not isinstance(ids,list) or not all(isinstance(i,str) and i for i in ids):
            raise ValueError("Missing channel identity")
        if sorted(ids)!=proof.get("channel_ids"):
            raise ValueError("Channel ID source evidence mismatch")
        if len(ids)!=1:
            ambiguous+=1
            continue
        accepted.append((ids[0],url))
    if matched!=set(expected):
        raise ValueError("Incomplete authenticated URL evidence")
    lines=["#EXTM3U"]
    for cid,url in sorted(accepted):
        lines.extend(['#EXTINF:-1 tvg-id="'+esc(cid)+'" group-title="V2 AV KANITLI TEST",'+esc(cid),
                      url])
    return "\n".join(lines)+"\n", {
        "policy":"LOCAL_PRIVATE_SEPARATE_IBO_TEST_FFMPEG_VIDEO_PLUS_AUDIO_ONLY",
        "verified_entries":len(accepted),
        "ambiguous_multi_channel_url_skipped":ambiguous,
        "total_candidate_hashes":len(expected),
        "ibo_device_verified":False,
        "protected_main_playlist_modified":False,
        "status":"PRIVATE_TEST_OUTPUT_READY" if accepted else "NO_VERIFIED_STREAM_TO_EXPORT"}


def validate_destination(out):
    out=Path(out)
    base=REPORTS.resolve()
    if (out.is_symlink() or out.exists()
            or out.parent.resolve()!=base
            or not out.name.startswith("private-")
            or out.suffix!=".m3u8"):
        raise ValueError("Export requires new private-only file in v2/reports")
    return out


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--private-key",type=Path,required=True)
    parser.add_argument("--sealed",type=Path,default=DEFAULT_SEALED)
    parser.add_argument("--report",type=Path,default=DEFAULT_REPORT)
    parser.add_argument("--out",type=Path,default=DEFAULT_OUT)
    parser.add_argument("--batch-out",type=Path,
                        help="Offline encrypted 1000/2000-record test packages; no plaintext playlist")
    parser.add_argument("--xmltv",type=Path,help="Existing XMLTV snapshot for exact ID mapping audit")
    args=parser.parse_args()
    if args.batch_out is not None:
        from bulk_candidate_acceptance import main as batch_main
        batch_args=["--report",str(args.report),"--sealed",str(args.sealed),
                    "--private-key",str(args.private_key),"--out",str(args.batch_out)]
        if args.xmltv is not None:
            batch_args.extend(["--xmltv",str(args.xmltv)])
        batch_main(batch_args)
        return
    if args.xmltv is not None:
        parser.error("--xmltv requires --batch-out")
    out=validate_destination(args.out)
    for path in (args.report,args.sealed,args.private_key):
        if path.is_symlink() or not path.is_file():
            raise SystemExit("Missing or unsafe private evidence input")
    payload=args.sealed.read_bytes()
    report=json.loads(args.report.read_text(encoding="utf-8"))
    manifest=report.get("encrypted_evidence") or {}
    if (manifest.get("sha256")!=hashlib.sha256(payload).hexdigest()
            or manifest.get("records")!=report.get("unique_url_candidates")):
        raise SystemExit("Encrypted report and source evidence mismatch")
    from stage3_sealed_export import open_rows
    content,summary=select(report,open_rows(args.sealed,args.private_key))
    if not summary["verified_entries"]:
        print(json.dumps(summary,sort_keys=True))
        raise SystemExit("No verified AV streams - refusing an empty or fabricated IBO file")
    out.parent.mkdir(parents=True,exist_ok=True)
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_NOFOLLOW",0)
    fd=os.open(out,flags,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as stream:
        stream.write(content)
    print(json.dumps(summary,sort_keys=True))


if __name__=="__main__":
    main()
