#!/usr/bin/env python3
"""Offline grouped historical source intersection tests."""
import hashlib
import unittest
from historical_local_match import match_local_sources, validate_index
from historical_inventory_guard import reconcile


def digest(url):
    return hashlib.sha256(url.encode()).hexdigest()


class HistoricalLocalMatchTests(unittest.TestCase):
    def test_real_url_recovered_only_on_exact_sha_match_and_duplicate_merged(self):
        tr = 'https://fixture.example.org/live.m3u8?key=FIRST'
        other = 'https://fixture.example.org/live.m3u8?key=SECOND'
        history = [{'url_sha256': digest(tr), 'region_candidate': 'TR',
                    'classification_evidence': 'METADATA', 'source': '#60'},
                   {'url_sha256': digest(other), 'region_candidate': 'AZ',
                    'classification_evidence': 'METADATA', 'source': '#60'}]
        content = '#EXTM3U\n#EXTINF:-1 tvg-id="TRT1.tr",TRT 1\n' + tr + '\n'
        summary, matches = match_local_sources(history, [('backup1', content), ('backup2', content)], expected=2)
        self.assertEqual(summary['matched_real_url_identities'], 1)
        self.assertEqual(summary['unmatched_hash_identities'], 1)
        self.assertNotIn(tr, str(summary))
        self.assertEqual(matches[0]['url'], tr)
        self.assertEqual(matches[0]['source_ids'], ['backup1', 'backup2'])
        protected, candidates, result = reconcile(history, matches, expected_historical_records=2)
        self.assertEqual(protected[:2], history)
        self.assertEqual(result['historical_hash_only_linked_to_real_urls'], 1)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(result['historical_hash_only_identities'], 2)

    def test_no_false_recovery_by_same_name_or_url_without_valid_hash(self):
        url = 'https://fixture.example.org/other.m3u8?key=DIFFERENT'
        history = [{'url_sha256': digest('https://fixture.example.org/other.m3u8?key=ORIGINAL')}]
        s, rows = match_local_sources(history, [('backup', '#EXTM3U\n#EXTINF:-1,News\n' + url + '\n')], 1)
        self.assertEqual(s['unmatched_hash_identities'], 1)
        self.assertEqual(rows, [])
        self.assertFalse(s['plaintext_url_emitted'])

    def test_history_duplicates_and_unsafe_files_refused(self):
        x = {'url_sha256': digest('https://fixture.example.org/a.m3u8')}
        with self.assertRaises(ValueError):
            validate_index([x, x], 2)
        with self.assertRaises(ValueError):
            validate_index([dict(x, url='https://fixture.example.org/a.m3u8')], 1)
        with self.assertRaises(ValueError):
            match_local_sources([x], [('backup', '#EXTM3U\n'), ('backup', '#EXTM3U\n')], 1)

    def test_invalid_local_m3u_rejected_without_mutation(self):
        history = [{'url_sha256': digest('https://fixture.example.org/a.m3u8')}]
        with self.assertRaises(ValueError):
            match_local_sources(history, [('bad', '<html>not m3u</html>')], 1)
        self.assertEqual(validate_index(history, 1), {history[0]['url_sha256']})


if __name__ == '__main__':
    unittest.main()
