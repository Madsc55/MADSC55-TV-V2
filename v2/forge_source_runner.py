#!/usr/bin/env python3
"""Compatibility wrapper for the canonical paginated forge source scanner.

All forge scans use run_forge_source_discovery: one implementation of paging,
limits, review schemas and public HTTPS API checks.
"""
from run_forge_source_discovery import api_json, scan, main

if __name__ == "__main__":
    main()
