.PHONY: run test ibo-visibility-audit
PYTHON ?= python3

run: test

test:
	PYTHONPATH=v2:. $(PYTHON) -m unittest -v v2.test_channel_command_engine
	PYTHONPATH=v2:. $(PYTHON) -m unittest -v v2.test_ibo_import_visibility_audit
	PYTHONPATH=v2:. $(PYTHON) -m unittest -v v2.test_discovery_34_live_contract v2.test_federated_m3u_source_discovery v2.test_discovery_34 v2.test_task_ledger_integrity
	PYTHONPATH=v2:. $(PYTHON) -m unittest -v v2.test_shared_url_identity
	PYTHONPATH=v2:. $(PYTHON) -m unittest -v v2.test_shared_url_safe_probe
	PYTHONPATH=v2:. $(PYTHON) -m unittest -v v2.test_full_playlist_url_audit
	$(PYTHON) v2/test_playlist_invariants.py
	$(PYTHON) -m py_compile v2/discovery_34_live_contract.py v2/federated_m3u_source_discovery.py v2/discovery_provider_requests.py

# Compare source-record counts to the November 23 IBO Player snapshot.
# This command is strictly read-only and does not rewrite the canonical M3U8.
ibo-visibility-audit:
	PYTHONPATH=v2:. $(PYTHON) v2/ibo_import_visibility_audit.py --observed-json '{"BELGESEL":18,"YEDEKLER":1104,"ANA ARŞİV":15606}'
