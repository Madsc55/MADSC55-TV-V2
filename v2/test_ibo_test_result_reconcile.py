import hashlib
import json
import unittest
from collections import Counter
from ibo_test_result_reconcile import reconcile, digest

def sample():
    return ('#EXTM3U\n' +
            ''.join('#EXTINF:-1 group-title="🗂️ YEDEKLER",C%d\nhttps://example.org/%d\n' % (i,i) for i in range(4))).encode()

def report(raw, statuses):
    from ibo_single_playlist_transfer import parse
    from ibo_test_result_reconcile import identity
    blocks = parse(raw)[1]
    items = []
    for block, status in zip(blocks, statuses):
        items.append({"channel_sha256": digest(block.encode()), "url_sha256": identity(block),
                      "run_id": 123, "evidence_sha256": "a"*64,
                      "attempts": 2 if status == "failed" else 1,
                      "repeatable_av_failure": status == "failed", "status": status})
    return {"schema": 1, "playlist_sha256": digest(raw), "entries": items}

def run(raw, r):
    return reconcile(raw, r, digest(raw),
                     digest(json.dumps(r,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()))

class Tests(unittest.TestCase):
    def test_preserves_multiset_and_moves_only_proven_failure(self):
        raw = sample()
        result, manifest = run(raw, report(raw, ["verified","failed","uncertain","verified"]))
        self.assertEqual(manifest["counts"], {"verified":2,"failed":1,"uncertain":1})
        self.assertEqual(manifest["failed_tail_start_1based"],4)
        self.assertEqual(len(manifest["retry_queue"]),1)
        self.assertTrue(result.decode().endswith("https://example.org/1\n"))
        self.assertEqual(Counter(result.decode().splitlines()), Counter(raw.decode().splitlines()))
    def test_transient_failure_stays_uncertain(self):
        raw=sample(); r=report(raw, ["verified","failed","uncertain","verified"])
        r["entries"][1]["repeatable_av_failure"]=False
        result, manifest=run(raw,r)
        self.assertEqual(manifest["failed_count"],0)
        self.assertEqual(len(manifest["retry_queue"]),2)
        self.assertEqual(result,raw)
    def test_duplicate_and_missing_reports_fail_closed(self):
        raw=sample(); r=report(raw,["verified"]*4)
        r["entries"][1]=r["entries"][0]
        with self.assertRaises(ValueError): run(raw,r)
        r=report(raw,["verified"]*4); r["entries"].pop()
        with self.assertRaises(ValueError): run(raw,r)
    def test_mismatched_url_hash_fails(self):
        raw=sample(); r=report(raw,["verified"]*4)
        r["entries"][0]["url_sha256"]="0"*64
        with self.assertRaises(ValueError): run(raw,r)
    def test_1792_fixture_preserves_1107_and_queues_685(self):
        # Synthetic acceptance fixture, NOT real channel evidence.
        raw = ('#EXTM3U\n' + ''.join(
            '#EXTINF:-1 group-title="🗂️ YEDEKLER",C%d\nhttps://example.org/%d\n' % (i, i)
            for i in range(1792))).encode()
        r = report(raw, ["verified"] * 1107 + ["uncertain"] * 685)
        result, manifest = run(raw, r)
        self.assertEqual(result, raw)
        self.assertEqual(manifest["counts"], {"verified": 1107, "uncertain": 685})
        self.assertEqual(len(manifest["retry_queue"]), 685)
        self.assertEqual(manifest["failed_count"], 0)
        self.assertIsNone(manifest["failed_tail_start_1based"])

    def test_stale_playlist_fails(self):
        raw=sample(); r=report(raw,["verified"]*4)
        with self.assertRaises(ValueError):
            reconcile(raw+b" ",r,digest(raw),digest(b"anything"))
if __name__=="__main__": unittest.main()
