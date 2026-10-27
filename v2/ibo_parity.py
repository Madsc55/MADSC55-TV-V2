#!/usr/bin/env python3
"""Read-only comparison of the user's canonical IBO URL with the V2 playlist."""
import hashlib
import json
import urllib.error
import urllib.request
from discover import ROOT, LIVE, entries

IBO = "https://raw.githubusercontent.com/Madsc55/Madsc55-Tv/main/MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
OUT = ROOT / "v2/reports/ibo-parity.json"

def main():
    v2 = LIVE.read_bytes()
    result = {"ibo_url": IBO, "v2_entries": len(list(entries(v2.decode("utf-8-sig")))),
              "v2_sha256": hashlib.sha256(v2).hexdigest(), "status": "UNVERIFIED"}
    try:
        req = urllib.request.Request(IBO, headers={"User-Agent": "MADSC55-TV-V2-Parity/1.0"})
        with urllib.request.urlopen(req, timeout=20) as response:
            ibo = response.read(8_000_001)
        if len(ibo) > 8_000_000:
            result["status"] = "IBO_TOO_LARGE"
        else:
            old = list(entries(ibo.decode("utf-8-sig")))
            new = list(entries(v2.decode("utf-8-sig")))
            old_urls = {e["url"] for e in old}
            added = [e for e in new if e["url"] not in old_urls]
            result.update({"ibo_entries": len(old), "ibo_sha256": hashlib.sha256(ibo).hexdigest(),
                           "missing_old_urls_in_v2": sum(e["url"] not in {n["url"] for n in new} for e in old),
                           "new_v2_entries_by_url": len(added),
                           "new_v2_names": [e["name"] for e in added][:30],
                           "status": "IDENTICAL" if ibo == v2 else "DIFFERENT_REVIEW_REQUIRED"})
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeError) as exc:
        result.update({"status": "IBO_URL_UNREACHABLE", "error_type": type(exc).__name__})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("IBO parity:", result["status"], "V2:", result["v2_entries"],
          "IBO:", result.get("ibo_entries", "unavailable"),
          "new URLs:", result.get("new_v2_entries_by_url", "unknown"))
if __name__ == "__main__":
    main()
