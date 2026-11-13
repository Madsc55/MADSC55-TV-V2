#!/usr/bin/env python3
"""Offline archive integrity and final acceptance gate; no network or publishing."""
import argparse
import hashlib
import json
import pathlib
import re

def sha(data):
    return hashlib.sha256(data).hexdigest()

def audit_archive(original, restored):
    if not isinstance(original, bytes) or not isinstance(restored, bytes):
        raise ValueError("archive inputs must be bytes")
    if not original or not restored:
        raise ValueError("missing archive or restored bytes")
    if original != restored:
        raise ValueError("archive restore integrity mismatch")
    return {"status":"ROUNDTRIP_BYTES_MATCH","sha256":sha(original),"bytes":len(original)}

def audit_encrypted_archive(original, ciphertext, passphrase):
    from secure_archive import MAGIC, decrypt
    if type(original) is not bytes or type(ciphertext) is not bytes:
        raise ValueError("encrypted archive inputs must be bytes")
    if not ciphertext.startswith(MAGIC):
        raise ValueError('not an authenticated encrypted V2 archive')
    restored = decrypt(ciphertext, passphrase)
    result = audit_archive(original, restored)
    result['encrypted'] = True
    result['external_restore_verified'] = False
    return result

def audit_external_restore(original, external_ciphertext, external_restored, passphrase):
    """Verify bytes restored from a separately retrieved encrypted archive."""
    from secure_archive import MAGIC, decrypt
    if type(original) is not bytes or type(external_ciphertext) is not bytes or type(external_restored) is not bytes:
        raise ValueError("external restore inputs must be bytes")
    if not external_ciphertext.startswith(MAGIC):
        raise ValueError("external archive is not an authenticated V2 archive")
    decrypted = decrypt(external_ciphertext, passphrase)
    if decrypted != external_restored:
        raise ValueError("external restore bytes do not match decrypted archive")
    result = audit_archive(original, external_restored)
    result["encrypted"] = True
    result["external_restore_verified"] = True
    result["external_archive_sha256"] = sha(external_ciphertext)
    return result

def final_gate(package_report, archive_report, independent_restore=False, live_av=False):
    if not isinstance(package_report, dict) or not isinstance(archive_report, dict):
        raise ValueError("invalid acceptance report type")
    required=("target","records","sha256","status")
    if not all(k in package_report for k in required):
        raise ValueError("incomplete package evidence")
    if (type(package_report["target"]) is not int or type(package_report["records"]) is not int
            or package_report["target"] not in (1000,2000)
            or package_report["records"] != package_report["target"]
            or package_report["status"] != "EVIDENCE_GATED"
            or not isinstance(package_report["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", package_report["sha256"]) is None):
        raise ValueError("package acceptance incomplete")
    if (archive_report.get("status") != "ROUNDTRIP_BYTES_MATCH"
            or not isinstance(archive_report.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", archive_report["sha256"]) is None
            or type(archive_report.get("bytes")) is not int
            or archive_report["bytes"] <= 0):
        raise ValueError("archive integrity incomplete")
    if archive_report["sha256"] != package_report["sha256"]:
        raise ValueError("archived bytes do not match accepted IBO package digest")
    if type(independent_restore) is not bool or type(live_av) is not bool:
        raise ValueError("invalid acceptance flag types")
    if independent_restore and archive_report.get("external_restore_verified") is not True:
        raise ValueError("independent external restore evidence required")
    if independent_restore and live_av and archive_report.get("encrypted") is not True:
        raise ValueError("authenticated encrypted archive evidence required for production review")
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
