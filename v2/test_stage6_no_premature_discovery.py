#!/usr/bin/env python3
"""Offline policy checks: channel search must not start on code pushes."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Stage6NoPrematureDiscoveryTests(unittest.TestCase):
    def test_live_discovery_requires_explicit_manual_approval(self):
        workflow = (ROOT / ".github/workflows/v2-stage6-live-discovery.yml").read_text()
        header = workflow.split("concurrency:", 1)[0]
        self.assertIn("workflow_dispatch:", header)
        self.assertNotIn("  push:", header)
        self.assertIn("approve_live_discovery:", header)
        self.assertIn("default: false", header)
        self.assertIn("inputs.approve_live_discovery == true", workflow)
        self.assertIn("task_engine.py --check-discovery-prerequisites", workflow)

    def test_preflight_does_not_execute_network_discovery(self):
        workflow = (ROOT / ".github/workflows/v2-stage6-preflight.yml").read_text()
        self.assertNotIn("run_all_discovery.py --run-all", workflow)
        self.assertNotIn("stage6_platform_search.py --execute", workflow)
        self.assertIn("stage6_source_inventory.py --validate-config", workflow)

if __name__ == "__main__":
    unittest.main()
