import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import discovery_34_integrate as module


class IntegrationAcceptanceTests(unittest.TestCase):
    def test_missing_source_keeps_partial_candidates_and_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            official = root / "official.json"
            official.write_text(json.dumps({"channels": [{"official_site": "https://example.org/tv", "name": "Example"}]}))
            result = module.integrate({"official": official, "youtube": root / "missing.json"})
            self.assertEqual(len(result["candidates"]), 1)
            self.assertFalse(result["candidates"][0]["verified_av"])
            self.assertEqual(result["errors"][0]["source"], "youtube")

    def test_cli_writes_partial_report_then_returns_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            partial = {"candidates": [], "errors": [{"source": "youtube", "error": "FileNotFoundError"}], "verified_av": 0}
            with patch.object(module, "integrate", return_value=partial), patch("sys.argv", ["discovery_34_integrate.py", "--output", str(output)]):
                with self.assertRaises(SystemExit) as exc:
                    module.main()
            self.assertEqual(exc.exception.code, 1)
            self.assertEqual(json.loads(output.read_text()), partial)

    def test_cli_success_when_all_inputs_present(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            complete = {"candidates": [], "errors": [], "verified_av": 0}
            with patch.object(module, "integrate", return_value=complete), patch("sys.argv", ["discovery_34_integrate.py", "--output", str(output)]):
                module.main()
            self.assertEqual(json.loads(output.read_text()), complete)


if __name__ == "__main__":
    unittest.main()
