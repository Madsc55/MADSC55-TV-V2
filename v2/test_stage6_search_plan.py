#!/usr/bin/env python3
"""Offline checks for deferred worldwide discovery coverage."""
import unittest
from stage6_search_plan import make_plan

class Stage6SearchPlanTests(unittest.TestCase):
    def test_required_platforms_regions_and_terms(self):
        plan = make_plan()
        self.assertEqual(set(plan["platforms"]), {"github", "gist", "gitlab", "codeberg"})
        self.assertEqual(set(plan["regions"]), {"TR", "AZ", "world"})
        self.assertTrue({"turkiye.m3u", "tr.m3u8", "canli-tv", "yerel-tv"}.issubset(plan["queries"]))
        self.assertEqual(plan["search_jobs_planned"], len(plan["queries"]) * len(plan["platforms"]))

    def test_never_claims_search_or_changes_existing_channels(self):
        plan = make_plan()
        self.assertEqual(plan["search_jobs_executed"], 0)
        self.assertTrue(plan["rules"]["main_ibo_read_only"])
        self.assertTrue(plan["rules"]["existing_channels_not_revalidated"])
        self.assertTrue(plan["rules"]["do_not_close_task_34_from_this_report"])

if __name__ == "__main__":
    unittest.main()
