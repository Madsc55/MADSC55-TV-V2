"""Read-only decisions over independently reviewed evidence, never raw hints."""
import hashlib
import re
from collections import defaultdict
from urllib.parse import urlsplit
from v2.stream_quality_decision import decide

TURKIC_REGIONS = frozenset({"AZ", "TM", "KZ", "KG", "UZ", "TR", "CY-NORTH"})
TURKISH = frozenset({"tr", "tur"})


def digest_url(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def exact_evidence(candidates, evidence):
    """Join by full, case-sensitive channel ID and exact stream URL hash.
    Evidence must be supplied by the trusted review stage, not source metadata.
    Duplicate/conflicting evidence is rejected rather than silently overwritten.
    """
    indexed = defaultdict(list)
    for row in evidence:
        indexed[(row.get("channel_id"), row.get("url_sha256"))].append(row)
    for candidate in candidates:
        channel = candidate["channel_id"]
        digest = digest_url(candidate["url"])
        rows = indexed[(channel, digest)]
        yield channel, digest, rows[0] if len(rows) == 1 else {}


def identity_ok(channel, row):
    return (row.get("identity_evidence_verified") is True
            and row.get("observed_channel_id") == channel)


def languages(channel, row):
    if not identity_ok(channel, row):
        return {"spoken_turkish": False, "turkish_subtitles": False,
                "origin": "UNVERIFIED", "turkic_origin": False}
    audio = (row.get("decoded_audio") is True and row.get("speech_review_verified") is True
             and row.get("speech_language") in TURKISH)
    subtitles = (row.get("subtitle_content_review_verified") is True
                 and row.get("subtitle_language") in TURKISH)
    origin = row.get("broadcast_origin") if row.get("origin_review_verified") is True else None
    origin = origin if origin in TURKIC_REGIONS else "OTHER_OR_UNVERIFIED"
    return {"spoken_turkish": audio, "turkish_subtitles": subtitles,
            "origin": origin, "turkic_origin": origin in TURKIC_REGIONS}


def https_asset(value):
    if not isinstance(value, str) or any(ord(c) <= 32 or ord(c) == 127 for c in value):
        return False
    try:
        u = urlsplit(value)
        return bool(u.scheme == "https" and u.hostname and not u.username
                    and not u.password and not u.fragment and u.port in (None, 443))
    except ValueError:
        return False


def assets(channel, row):
    result = {"tvg_id": None, "logo": None}
    if not identity_ok(channel, row):
        return result
    epg = row.get("epg")
    if isinstance(epg, dict) and epg.get("verified") is True and epg.get("channel_id") == channel:
        identifier = epg.get("tvg_id")
        if isinstance(identifier, str) and re.fullmatch(r"[^\s<>\x00-\x1f]+", identifier) and https_asset(epg.get("source_url")):
            result["tvg_id"] = identifier
    logo = row.get("logo")
    if (isinstance(logo, dict) and logo.get("official_origin_verified") is True
            and logo.get("content_verified") is True and logo.get("channel_id") == channel
            and https_asset(logo.get("url")) and https_asset(logo.get("official_source_url"))
            and isinstance(logo.get("content_sha256"), str)
            and re.fullmatch(r"[a-f0-9]{64}", logo["content_sha256"])):
        result["logo"] = logo["url"]
    return result


def evaluate(candidates, evidence):
    quality, reviews = [], []
    for channel, digest, row in exact_evidence(candidates, evidence):
        # Do not allow normalization to turn a conflicting full ID into a match.
        q = {k: row.get(k) for k in ("decoded_video", "decoded_audio", "height", "width", "video_bitrate",
                                    "identity_evidence_verified", "observed_channel_id")}
        q.update(channel_id=channel, url_sha256=digest)
        if row.get("identity_evidence_verified") is True and row.get("observed_channel_id") != channel:
            q["identity_evidence_verified"] = False
        quality.append(q)
        reviews.append({"channel_id": channel, "url_sha256": digest,
                        "identity_mismatch": row.get("identity_evidence_verified") is True and row.get("observed_channel_id") != channel,
                        "language": languages(channel, row), "assets": assets(channel, row)})
    # Rank exact channel IDs independently to prevent normalized ID collisions.
    grouped = defaultdict(list)
    for q in quality:
        grouped[q["channel_id"]].append(q)
    ranked = [d for group in grouped.values() for d in decide(group)["decisions"]]
    for d in ranked:
        if any(r["channel_id"] == d["channel_id"] and r["url_sha256"] == d["url_sha256"] and r["identity_mismatch"] for r in reviews):
            d.update(status="IDENTITY_MISMATCH", selected=False)
    return {"policy": "READ_ONLY_TRUSTED_REVIEW_EVIDENCE_ONLY", "quality": ranked, "reviews": reviews}
