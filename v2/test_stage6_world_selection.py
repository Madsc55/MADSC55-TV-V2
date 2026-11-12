#!/usr/bin/env python3
"""No-network tests for worldwide source selection and protected playlist policy."""
import unittest
from real_ibo_scan import include_candidate

class Stage6WorldSelectionTests(unittest.TestCase):
    def setUp(self):
        self.world = {'name':'France 24 English','group':'News','tvg_id':'France24.fr'}
        self.turkish = {'name':'TRT 1','group':'Türkiye','tvg_id':'TRT1.tr'}

    def test_world_feed_opt_in(self):
        self.assertFalse(include_candidate(self.world, 'world'))
        self.assertTrue(include_candidate(self.world, 'world', True))

    def test_world_opt_in_does_not_reclassify_local_feeds(self):
        self.assertFalse(include_candidate(self.world, 'TR', True))
        self.assertFalse(include_candidate(self.world, 'AZ', True))

    def test_tr_az_identity_kept_without_world(self):
        self.assertTrue(include_candidate(self.turkish, 'TR'))
        self.assertTrue(include_candidate(self.turkish, 'world'))

if __name__ == '__main__':
    unittest.main()
