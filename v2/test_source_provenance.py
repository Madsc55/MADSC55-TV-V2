#!/usr/bin/env python3
"""Offline regression: URL provenance survives deduplication and source reordering."""
import hashlib
from discover import discover

url = "https://example.org/live.m3u8"
m3u = '#EXTM3U\n#EXTINF:-1 tvg-id="TRT1.tr" group-title="Türkiye",TRT 1\n' + url + '\n'
scopes = {"source-a": "TR", "source-b": "TR"}
for order in (("source-a", "source-b"), ("source-b", "source-a")):
    candidates = discover([(source, m3u) for source in order], "#EXTM3U\n", scopes)
    assert len(candidates) == 1, candidates
    item = candidates[0]
    assert item["url_sha256"] == hashlib.sha256(url.encode()).hexdigest()
    assert set(item["source_ids"]) == set(order), item
    assert len(item["source_ids"]) == 2, item
    assert item["source"] == order[0], item
assert discover([("source-a", m3u)], m3u, scopes) == []
print("V2 source provenance regression: PASS")
