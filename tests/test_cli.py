import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tick_trap.cli import main
from tick_trap.reporting import read_json


class CliTests(unittest.TestCase):
    def invoke(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(list(args))

    def test_counterexample_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(self.invoke("counterexample", "--output", folder), 0)
            result = read_json(Path(folder)/"counterexample.json")
            self.assertEqual(result["continuous_status"], "unsafe")
            self.assertIn("<svg", (Path(folder)/"counterexample.svg").read_text())
            self.assertEqual(read_json(Path(folder)/"metadata.json")["project"], "tick-trap")

    def test_run_and_sweep_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder)/"config.json"
            for command, spec in [("run", {"steps": 1}),
                                  ("sweep", {"base": {"steps": 1}, "grid": {"method": ["endpoint", "exact_hold"]}})]:
                config.write_text(json.dumps(spec))
                output = Path(folder)/command
                self.assertEqual(self.invoke(command, "--config", str(config), "--output", str(output)), 0)
                runs = read_json(output/"runs.json")
                self.assertEqual(len(runs), 1 if command == "run" else 2)
                self.assertIn("Safe complete", (output/"report.md").read_text())
                self.assertIn("configuration_sha256", read_json(output/"metadata.json"))
                self.assertTrue((output/"summary.csv").is_file())

    def test_planar_certificate_and_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder)/"config.json"
            config.write_text(json.dumps(dict(p=[2, 0], v=[0, 0], u=[0, 0], center=[0, 0], radius=1, duration=1)))
            self.assertEqual(self.invoke("certify", "--config", str(config), "--output", folder), 0)
            self.assertEqual(read_json(Path(folder)/"certificate.json")["continuous_status"], "safe")
            config.write_text('{"steps": 0}')
            self.assertEqual(self.invoke("run", "--config", str(config), "--output", folder), 2)
            config.write_text('{"duration": NaN}')
            self.assertEqual(self.invoke("run", "--config", str(config), "--output", folder), 2)

    def test_decimal_json_preserves_input_value(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder)/"config.json"
            config.write_text('{"d": 0.04, "steps": 1}')
            self.assertEqual(read_json(config)["d"], "0.04")


if __name__ == "__main__":
    unittest.main()
