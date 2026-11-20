"""SHA-chained, fail-closed archive operation journal. No playlist mutation."""
import hashlib
import json
from pathlib import Path

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(record):
    return json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()

def validate(records, initial_sha):
    seen = set()
    head = initial_sha
    for item in records:
        if item["operation_id"] in seen:
            raise ValueError("Duplicate operation id")
        if item["before_sha256"] != head:
            raise ValueError("Broken operation SHA chain")
        if item["before_sha256"] == item["after_sha256"]:
            raise ValueError("No-op archive transfer")
        if not 1 <= item["moved"] <= 2500:
            raise ValueError("Invalid batch size")
        seen.add(item["operation_id"])
        head = item["after_sha256"]
    return head

def append(records, initial_sha, operation):
    current = validate(records, initial_sha)
    if operation["operation_id"] in {x["operation_id"] for x in records}:
        raise ValueError("Operation already processed")
    if operation["before_sha256"] != current:
        raise ValueError("Stale playlist SHA")
    result = records + [operation]
    validate(result, initial_sha)
    return result

def read(path):
    path = Path(path)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("operations"), list):
        raise ValueError("Invalid journal")
    validate(data["operations"], data["initial_sha256"])
    return data
