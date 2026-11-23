.PHONY: run test
PYTHON ?= python3

run: test

test:
	PYTHONPATH=v2:. $(PYTHON) -m unittest -v v2.test_channel_command_engine
	PYTHONPATH=v2:. $(PYTHON) -m unittest -v v2.test_discovery_34_live_contract v2.test_federated_m3u_source_discovery v2.test_discovery_34 v2.test_task_ledger_integrity
	PYTHONPATH=v2:. $(PYTHON) -m unittest -v v2.test_shared_url_identity
	PYTHONPATH=v2:. $(PYTHON) -m unittest -v v2.test_shared_url_safe_probe
	$(PYTHON) v2/test_playlist_invariants.py
	$(PYTHON) -m py_compile v2/discovery_34_live_contract.py v2/federated_m3u_source_discovery.py v2/discovery_provider_requests.py
