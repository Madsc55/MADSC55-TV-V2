#!/usr/bin/env python3
"""Read-only Turkish-channel triage; never proves stream availability or approval.

Distinguishes broadcaster origin, spoken language, subtitle language and title.
Unknown evidence remains unknown. No network requests or playlist writes.
"""
import re

TR_COUNTRIES = {"TR", "TUR", "TURKEY", "TÜRKİYE"}
TR_CYPRUS = {"KKTC", "NORTHERN CYPRUS"}
TURKIC = {"AZ", "AZE", "AZERBAIJAN", "AZERBAYCAN", "TM", "TKM", "TURKMENISTAN"}
NAME_MARKERS = re.compile(r"(?<![A-Z0-9])(?:TÜRK(?:İYE|ÇE)?|TURK(?:IYE|ISH)?|TRT|KKTC|KIBRIS|AZƏRBAYCAN|AZERBAYCAN)(?![A-Z0-9])", re.I)
TR_LANGUAGE = {"tr", "tr-tr"}
OTHER_TURKIC_LANGUAGES = {"az", "az-az", "tk", "tk-tm"}

def classify_channel(name, origin_country=None, spoken_language=None,
                     subtitle_language=None, video_decoded=False,
                     audio_decoded=False, stream_checked=False):
    """Classify review candidates, not production channels.

    A channel can be Turkish without Turkish words in its name. A Turkish
    title, country, or subtitle alone must never certify spoken Turkish.
    """
    if not isinstance(name, str) or not name.strip() or len(name) > 512:
        raise ValueError("Invalid channel name")
    for value in (origin_country, spoken_language, subtitle_language):
        if value is not None and (not isinstance(value, str) or len(value) > 64):
            raise ValueError("Invalid metadata")
    if any(type(value) is not bool for value in
           (video_decoded, audio_decoded, stream_checked)):
        raise ValueError("Invalid media evidence")
    origin = (origin_country or "").strip().upper()
    spoken = (spoken_language or "").strip().lower()
    subtitle = (subtitle_language or "").strip().lower()
    title_hint = bool(NAME_MARKERS.search(name.upper()))
    origin_tr = origin in TR_COUNTRIES or origin in TR_CYPRUS
    origin_turkic = origin in TURKIC
    spoken_tr = spoken in TR_LANGUAGE
    spoken_turkic = spoken in OTHER_TURKIC_LANGUAGES
    subtitle_tr = subtitle in TR_LANGUAGE
    av = stream_checked and video_decoded and audio_decoded
    # Explicit separate facets: foreign-origin Turkish speech is not discarded;
    # Turkish-origin English speech is not labeled Turkish-spoken.
    if spoken_tr:
        category = "TURKISH_SPOKEN_REVIEW"
    elif spoken_turkic:
        category = "OTHER_TURKIC_SPOKEN_REVIEW"
    elif subtitle_tr:
        category = "TURKISH_SUBTITLED_REVIEW"
    elif origin_tr:
        category = "TURKEY_OR_NORTHERN_CYPRUS_ORIGIN_REVIEW"
    elif origin_turkic:
        category = "TURKIC_ORIGIN_REVIEW"
    elif title_hint:
        category = "TURKISH_NAME_REVIEW"
    else:
        category = "UNCLASSIFIED_REVIEW"
    return {
        "category": category,
        "turkish_name_hint": title_hint,
        "turkish_origin_hint": origin_tr,
        "other_turkic_origin_hint": origin_turkic,
        "turkish_spoken_hint": spoken_tr,
        "other_turkic_spoken_hint": spoken_turkic,
        "turkish_subtitle_hint": subtitle_tr,
        "av_decoded_in_supplied_check": av,
        "working_channel_verified": False,
        "source_country_verified": False,
        "language_evidence_verified": False,
        "review_approved": False,
        "playlist_modified": False,
    }
