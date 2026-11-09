#!/usr/bin/env python3
"""Grouped offline, tamper-resistant AV evidence union regression tests."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from traz_av_evidence_union import BASE,_read,merge

class CrossRunAVTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources = [BASE/'traz-api-av-acceptance.json',
                   BASE/'traz-missing-target-real-av.json',
                   BASE/'traz-missing-stream-epg-crosswalk.json']
        present = [p.is_file() for p in sources]
        if not any(present):
            raise unittest.SkipTest('Pinned Actions artifact inputs absent from ordinary offline checkout')
        if not all(present):
            raise RuntimeError('Incomplete pinned Actions AV evidence inputs; partial evidence cannot be accepted')
        cls.p = _read(BASE/'traz-api-av-acceptance.json')[0]
        cls.n = _read(BASE/'traz-missing-target-real-av.json')[0]
        cls.g = _read(BASE/'traz-missing-stream-epg-crosswalk.json')[0]

    def test_real_pinned_evidence_counts_not_new_probe(self):
        r = merge(self.p,self.n,self.g)
        self.assertEqual(r['previous_video_audio_channel_ids'],147)
        self.assertEqual(r['total_distinct_video_audio_channel_ids'],150)
        self.assertEqual(r['total_distinct_video_audio_stream_hashes'],174)
        self.assertEqual(r['newly_av_proven_channel_ids'],['Cine1.tr','DMAX.tr','TLC.tr'])
        self.assertEqual(r['source_lead_identities_still_without_new_av'],81)
        self.assertEqual(r['other_m3u_no_lead_identities'],225)
        self.assertEqual(r['additional_xmltv_id_candidates_not_schedule_proof'],2)
        self.assertFalse(r['ibo_device_verified'])
        self.assertFalse(r['long_term_stability_verified'])
        self.assertFalse(r['sweden_access_verified'])
        self.assertNotIn('https://',str(r))

    def test_fake_av_rejected(self):
        a,b,c = copy.deepcopy((self.p,self.n,self.g))
        row = next(x for x in b['results'] if x['decoded'])
        row['audio'] = False
        with self.assertRaises(ValueError):merge(a,b,c)

    def test_wrong_channel_identity_rejected(self):
        a,b,c = copy.deepcopy((self.p,self.n,self.g))
        b['results'][0]['exact_channel_id'] = 'Wrong.tr'
        with self.assertRaises(ValueError):merge(a,b,c)

    def test_incomplete_or_duplicate_hash_rejected(self):
        a,b,c = copy.deepcopy((self.p,self.n,self.g))
        b['results'].pop()
        with self.assertRaises(ValueError):merge(a,b,c)
        a,b,c = copy.deepcopy((self.p,self.n,self.g))
        b['results'][1]['url_sha256'] = b['results'][0]['url_sha256']
        with self.assertRaises(ValueError):merge(a,b,c)

    def test_protected_device_claim_rejected(self):
        a,b,c = copy.deepcopy((self.p,self.n,self.g))
        b['ibo_device_verified'] = True
        with self.assertRaises(ValueError):merge(a,b,c)

    def test_plaintext_report_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'report.json'
            p.write_text('{"stream_url":"https://example.org/video.m3u8"}')
            with self.assertRaises(ValueError):_read(p)

class PinnedEvidencePresenceTests(unittest.TestCase):
    """Presence checks must run even when real pinned artifacts are unavailable."""

    def test_all_absent_is_explicitly_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(CrossRunAVTests.setUpClass.__func__.__globals__,
                            {'BASE': Path(tmp)}):
                with self.assertRaises(unittest.SkipTest):
                    CrossRunAVTests.setUpClass()

    def test_one_or_two_inputs_fail_closed(self):
        names = ('traz-api-av-acceptance.json',
                 'traz-missing-target-real-av.json',
                 'traz-missing-stream-epg-crosswalk.json')
        for count in (1, 2):
            with self.subTest(present=count), tempfile.TemporaryDirectory() as tmp:
                for name in names[:count]:
                    (Path(tmp) / name).write_text('{}', encoding='utf-8')
                with patch.dict(CrossRunAVTests.setUpClass.__func__.__globals__,
                                {'BASE': Path(tmp)}):
                    with self.assertRaisesRegex(RuntimeError, 'Incomplete pinned Actions AV evidence'):
                        CrossRunAVTests.setUpClass()


if __name__ == '__main__':
    unittest.main()
