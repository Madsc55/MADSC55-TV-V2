"""Rank independently verified streams without changing production playlists."""
import re
import unicodedata
from collections import defaultdict


def normalize(value):
    return " ".join(re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", str(value or "")).casefold()))


def positive_int(value):
    return value if type(value) is int and value > 0 else 0


def decide(rows):
    """Require verified decoded AV and independent observed identity.
    
    observed_channel_id must come from reviewed broadcast evidence, not the
    playlist name, EPG metadata, or the candidate's declared identity.
    Rank by measured height, width, then video bitrate in bits per second.
    """
    groups = defaultdict(list)
    decisions = []
    for row in rows:
        expected = normalize(row.get("channel_id"))
        observed = normalize(row.get("observed_channel_id"))
        verified = row.get("identity_evidence_verified") is True
        av = row.get("decoded_video") is True and row.get("decoded_audio") is True
        height = positive_int(row.get("height"))
        width = positive_int(row.get("width"))
        bitrate = positive_int(row.get("video_bitrate"))
        digest = row.get("url_sha256", "")
        valid_digest = isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest)
        status = "IDENTITY_REVIEW_REQUIRED"
        if verified and expected and observed and expected != observed:
            status = "IDENTITY_MISMATCH"
        elif verified and expected and expected == observed:
            status = "ELIGIBLE" if av and height and width and bitrate and valid_digest else "INSUFFICIENT_MEASUREMENTS"
        result = {"channel_id": row.get("channel_id"), "url_sha256": digest if valid_digest else None,
                  "height": height, "width": width, "video_bitrate": bitrate,
                  "status": status, "selected": False}
        decisions.append(result)
        if status == "ELIGIBLE":
            groups[expected].append(result)
    for candidates in groups.values():
        best = min(candidates, key=lambda x: (-x["height"], -x["width"], -x["video_bitrate"], x["url_sha256"]))
        best["selected"] = True
    return {"policy": "READ_ONLY_REVIEW_NO_PLAYLIST_MUTATION", "decisions": decisions}
