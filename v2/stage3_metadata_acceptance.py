"""Stage 3 conservative channel metadata acceptance.

Only independently observed video/audio can establish playable quality.
Names, country tags and EPG are discovery hints, never playback proof.
"""
from __future__ import annotations



def normalized_identity(record: dict) -> dict:
    """Preserve raw IDs while making conservative country classification."""
    tvg = str(record.get("tvg_id") or "").strip()
    country = str(record.get("country") or "").upper().strip()
    if country not in {"TR", "AZ"}:
        country = "UNVERIFIED"
    return {"tvg_id": tvg, "country": country,
            "name": str(record.get("name") or "").strip(),
            "country_verified": bool(record.get("country_verified") is True and country != "UNVERIFIED")}


def epg_match(channel: dict, programme: dict) -> bool:
    """Require an exact non-empty TVG identity; fuzzy names cannot auto-link."""
    a = str(channel.get("tvg_id") or "").strip()
    b = str(programme.get("channel") or "").strip()
    return bool(a and b and a == b)


def quality_from_probe(probe: dict) -> dict:
    """Require real probe evidence of both streams; avoid name-based resolution."""
    if probe.get("status") != "AV_VERIFIED" or probe.get("video") is not True or probe.get("audio") is not True:
        return {"av_verified": False, "quality": "UNVERIFIED"}
    streams = probe.get("streams")
    if not isinstance(streams, list):
        return {"av_verified": False, "quality": "UNVERIFIED"}
    videos = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "video"
              and isinstance(s.get("width"), int) and isinstance(s.get("height"), int)
              and s["width"] > 0 and s["height"] > 0]
    audio = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "audio"]
    if not videos or not audio:
        return {"av_verified": False, "quality": "UNVERIFIED"}
    best = max(videos, key=lambda s: s["width"] * s["height"])
    return {"av_verified": True, "quality": f'{best["height"]}p',
            "width": best["width"], "height": best["height"]}


def category(record: dict) -> str:
    """Preserve an explicit source category; don't guess from names."""
    value = record.get("group")
    return value.strip() if isinstance(value, str) and value.strip() else "UNCATEGORIZED"
