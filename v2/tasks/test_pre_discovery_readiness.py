#!/usr/bin/env python3
"""Fixture-only tests; never search or modify channels."""
from pre_discovery_readiness import POST_DISCOVERY, check

def main():
    ids = list(range(1, 35))
    specs = {"tasks": [{"id": i, "depends_on": []} for i in ids]}
    statuses = {"statuses": [{"id": i, "status": "completed"} for i in ids]}
    assert check(statuses, specs)["recorded_system_tasks_complete"]
    assert not check(statuses, specs)["system_ready"]
    for i in POST_DISCOVERY:
        statuses["statuses"][i - 1]["status"] = "pending"
    assert check(statuses, specs)["recorded_system_tasks_complete"], "post-discovery tasks must not block system readiness"
    statuses["statuses"][0]["status"] = "pending"
    result = check(statuses, specs)
    assert not result["recorded_system_tasks_complete"] and result["system_unfinished"] == [1]
    specs["tasks"][1]["depends_on"] = [1]
    statuses["statuses"][1]["status"] = "pending"
    assert check(statuses, specs)["blocked_by_system_dependencies"]["2"] == [1]
    statuses["statuses"].pop()
    assert not check(statuses, specs)["recorded_system_tasks_complete"]
    print("Pre-discovery readiness offline fixtures: PASS")

if __name__ == "__main__":
    main()
