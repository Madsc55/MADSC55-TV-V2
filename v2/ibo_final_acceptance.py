#!/usr/bin/env python3
"""Offline archive integrity and final acceptance gate; no network or publishing."""
import argparse
import hashlib
import json
import pathlib

def sha(data):
    return hashlib.sha256(data).hexdigest()

def audit_archive(original, restored):
    if not original or not restored:
        raise ValueError("missing archive or restored bytes")
    if original != restored:
        raise ValueError("archive restore integrity mismatch")
    return {"status":"ROUNDTRIP_BYTES_MATCH","sha256":sha(original),"bytes":len(original)}

def audit_encrypted_archive(original, ciphertext, passphrase):
    from secure_archive import MAGIC, decrypt
    if not ciphertext.startswith(MAGIC):
        raise ValueError('not an authenticated encrypted V2 archive')
    restored = decrypt(ciphertext, passphrase)
    result = audit_archive(original, restored)
    result['encrypted'] = True
    result['external_restore_verified'] = False
    return result

def final_gate(package_report, archive_report, independent_restore=False, live_av=False):
    required=("target","records","sha256","status")
    if not all(k in package_report for k in required):
        raise ValueError("incomplete package evidence")
    if package_report["target"] not in (1000,2000) or package_report["records"] != package_report["target"] or package_report["status"] != "EVIDENCE_GATED":
        raise ValueError("package acceptance incomplete")
    if archive_report.get("status") != "ROUNDTRIP_BYTES_MATCH":
        raise ValueError("archive integrity incomplete")
    if not independent_restore or not live_av:
        return {"status":"INFRASTRUCTURE_ONLY","production_accepted":False,"reason":"independent external restore and real AV production acceptance pending"}
    return {"status":"READY_FOR_MANUAL_PRODUCTION_REVIEW","production_accepted":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original",type=pathlib.Path,required=True)
    p.add_argument("--restored",type=pathlib.Path,required=True)
    args=p.parse_args()
    print(json.dumps(audit_archive(args.original.read_bytes(),args.restored.read_bytes())))
if __name__=="__main__":
    main()
