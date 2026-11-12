"""Conservative IPTV metadata identity: hints are never verified channel or EPG claims."""
import re

COUNTRY_SUFFIX = re.compile(r"(?:^|[. _-])(tr|az)(?:[. _-]|$)", re.I)
CATEGORY_MAP = {
    "news": "news", "haber": "news", "xəbər": "news",
    "sport": "sports", "spor": "sports", "idman": "sports",
    "music": "music", "müzik": "music", "musiqi": "music",
    "kids": "kids", "çocuk": "kids", "uşaq": "kids",
    "documentary": "documentary", "belgesel": "documentary", "sənədli": "documentary",
}


def identity_metadata(entry, scope):
    if not isinstance(entry, dict):
        raise ValueError("Entry must be an object")
    tvg_id = entry.get("tvg_id", "")
    group = entry.get("group", "")
    if not isinstance(tvg_id, str) or not isinstance(group, str):
        raise ValueError("Invalid identity metadata")
    tvg_id = tvg_id.strip()
    country = scope if scope in ("TR", "AZ") else "unknown"
    if country == "unknown":
        match = COUNTRY_SUFFIX.search(tvg_id)
        if match:
            country = match.group(1).upper()
    normalized = re.sub(r"\s+", " ", group.casefold()).strip()
    category = CATEGORY_MAP.get(normalized, "unclassified")
    name = entry.get("name", "")
    if not isinstance(name, str):
        raise ValueError("Invalid channel name")
    # Labels describe source metadata, not measured video dimensions.
    resolution = None
    label = re.search(r"(?i)(?<![a-z0-9])(?:2160p|1440p|1080p|720p|576p|480p)(?![a-z0-9])", name)
    if label:
        resolution = label.group(0).lower()
    return {
        "resolution_hint": resolution,
        "resolution_verified": False,
        "country_hint": country,
        "country_verified": False,
        "epg_id_candidate": tvg_id or None,
        "epg_verified": False,
        "category_hint": category,
        "category_verified": False,
    }


def verify_epg_ids(candidates, xmltv_text):
    """Match XMLTV channel IDs exactly; programme availability is not implied."""
    import xml.etree.ElementTree as ET
    if not isinstance(xmltv_text, str):
        raise ValueError("XMLTV content must be text")
    if len(xmltv_text) > 25_000_000:
        raise ValueError("XMLTV content exceeds safe size limit")
    if "<!DOCTYPE" in xmltv_text.upper() or "<!ENTITY" in xmltv_text.upper():
        raise ValueError("XMLTV DTD and entities are not permitted")
    root = ET.fromstring(xmltv_text)
    if root.tag != "tv":
        raise ValueError("Expected XMLTV tv root")
    from collections import Counter
    ids = Counter(node.get("id") for node in root.findall("channel") if node.get("id"))
    programme_ids = {node.get("channel") for node in root.findall("programme")
                     if node.get("channel") and node.get("start")}
    output = []
    for row in candidates:
        candidate = row.get("epg_id_candidate")
        matched = isinstance(candidate, str) and ids[candidate] == 1
        programme = bool(matched and candidate in programme_ids)
        output.append({**row, "epg_verified": bool(matched),
                       "epg_programme_available": programme,
                       "epg_match_type": "exact_xmltv_channel_id" if matched else None})
    return output
