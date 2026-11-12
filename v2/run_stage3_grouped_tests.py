#!/usr/bin/env python3
"""Run all Stage 3 offline regressions as one fail-closed acceptance group.

This checks code behavior, NOT real broadcast playback, device acceptance,
or restoration of encrypted archives from external storage.
"""
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SUITES = (
    "test_identity_metadata",
    "test_stage2_integration",
    "test_discovery_metadata",
    "test_stage3_identity_recovery",
    "test_stage3_metadata_acceptance",
    "test_stage3_recovery_queue",
    "test_stage3_scanner_integration",
)

def main():
    sys.path.insert(0, str(HERE))
    loader = unittest.TestLoader()
    combined = unittest.TestSuite()
    for name in SUITES:
        combined.addTests(loader.loadTestsFromName(name))
    result = unittest.TextTestRunner(verbosity=2).run(combined)
    return 0 if result.wasSuccessful() and result.testsRun > 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
