#!/usr/bin/env python3
"""Offline regression tests for worldwide official site discovery."""
import unittest
from unittest.mock import patch
from official_sites_discovery import collect_official_sites

class OfficialSiteCoverageTests(unittest.TestCase):
    @patch('official_sites_discovery.validate_url', side_effect=lambda u: u.startswith('https://'))
    def test_tr_az_world_and_country_filter(self, _validate):
        rows = [
            {'id':'tr','country':'TR','website':'https://tr.example.org','name':'TR'},
            {'id':'az','country':'AZ','website':'https://az.example.org','name':'AZ'},
            {'id':'fr','country':'FR','website':'https://fr.example.org','name':'FR'},
            {'id':'closed','country':'FR','website':'https://closed.example.org','closed':True},
            {'id':'token','country':'AZ','website':'https://az.example.org/?token=secret'},
        ]
        all_sites = collect_official_sites(rows)
        self.assertEqual({x['country'] for x in all_sites}, {'TR','AZ','FR'})
        self.assertEqual(len(all_sites), 3)
        self.assertEqual({x['country'] for x in collect_official_sites(rows, {'TR','AZ'})}, {'TR','AZ'})
        self.assertFalse(any('token=' in x['official_site'] for x in all_sites))

if __name__ == '__main__':
    unittest.main()
