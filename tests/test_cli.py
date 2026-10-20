import contextlib
import io
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
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

    def test_published_wall_conditions_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root/"config.json"
            config.write_text(json.dumps({"base": {"horizon": "0.1"}, "durations": ["0.1"], "grid_points": 3,
                                          "cases": [{"name": "approach", "d": "0.6", "v": 1}]}))
            self.assertEqual(self.invoke("wall-conditions", "--config", str(config), "--output", str(root/"output")), 0)
            self.assertEqual(len(read_json(root/"output/runs.json")), 8)
            self.assertEqual(len(read_json(root/"output/study.json")["single_hold_cases"]), 2)
            self.assertIn("Matched gain", (root/"output/conditions.md").read_text())
            self.assertTrue((root/"output/conditions.csv").exists())

    def test_allocation_audit_artifacts_and_invalid_evidence(self):
        from tick_trap.certification_study import certification_study
        spec = {"base": {"grid_points": 2}, "budget_scope": "per_control", "repeats": 1,
                "budgets": [8], "strategies": ["minimum", "sign", "auxiliary_sign"],
                "cases": [dict(name="precision", p=["1.67", 0], v=[-1, 0], nominal=[1, -1],
                               duration=1, a_max=2, obstacles=[dict(center=[0, 0], radius=1)])]}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            study = root/"study.json"
            study.write_text(json.dumps(certification_study(spec)))
            source = {"configuration": spec, "git_status": "", "git_commit": "test-fixture", "source_sha256": "test-fixture"}
            (root/"metadata.json").write_text(json.dumps(source))
            output = root/"output"
            self.assertEqual(self.invoke("allocation-audit", "--study", str(study), "--output", str(output)), 0)
            self.assertEqual(read_json(output/"audit.json")["status"], "verified")
            self.assertEqual(read_json(output/"metadata.json")["configuration"]["input_source_commit"], "test-fixture")
            self.assertIn("offline counterfactual", (output/"report.md").read_text())
            self.assertTrue((output/"summary.csv").is_file())
            invalid = json.loads(study.read_text())
            invalid["measurements"].pop()
            study.write_text(json.dumps(invalid))
            self.assertEqual(self.invoke("allocation-audit", "--study", str(study), "--output", str(root/"invalid")), 2)
            self.assertFalse((root/"invalid/audit.json").exists())

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

    def test_learning_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder)/"config.json"
            config.write_text(json.dumps({"samples": 8, "methods": ["exact_hold"], "run_config": {"steps": 1}}))
            self.assertEqual(self.invoke("learn", "--config", str(config), "--output", folder), 0)
            self.assertEqual(len(read_json(Path(folder)/"learning.json")["evaluation"]), 4)
            self.assertEqual(len(read_json(Path(folder)/"runs.json")), 4)

    def test_benchmark_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder)/"config.json"
            case = dict(name="safe", p=[2, 0], v=[0, 0], u=[0, 0], center=[0, 0], radius=1, duration=1)
            config.write_text(json.dumps({"cases": [case], "repeats": 2, "budgets": [0, 8]}))
            self.assertEqual(self.invoke("benchmark", "--config", str(config), "--output", folder), 0)
            results = read_json(Path(folder)/"benchmark.json")
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["result"]["continuous_status"], "safe")
            self.assertEqual(len(results[0]["all_certification_ns"]), 2)

    def test_matched_certification_study_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder)/"config.json"
            case = dict(name="safe", p=[2, 0], v=[0, 0], nominal=[0, 0],
                        obstacles=[dict(center=[0, 0], radius=1)], duration="0.1", a_max=1)
            config.write_text(json.dumps({"base": {"grid_points": 2}, "cases": [case], "repeats": 2, "budgets": [0, 8]}))
            self.assertEqual(self.invoke("certification-study", "--config", str(config), "--output", folder), 0)
            result = read_json(Path(folder)/"study.json")
            self.assertEqual(len(result["groups"]), 5)
            self.assertEqual(result["applicable_cases"], 1)
            self.assertTrue((Path(folder)/"summary.csv").is_file())
            self.assertIn("same declared controls", (Path(folder)/"report.md").read_text())
            self.assertIn("configuration_sha256", read_json(Path(folder)/"metadata.json"))

    def test_planar_run_and_sweep_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder)/"config.json"
            base = {"horizon": "0.1", "p": [-2, "0.7"], "v": [0, 0], "goal": [-2, "0.7"],
                    "obstacles": [{"center": ["0.2", "0.1"], "radius": "0.5"}]}
            for command, spec in [("planar-run", base),
                                  ("planar-sweep", {"base": base, "grid": {"method": ["hocbf", "trajectory_candidates"]}})]:
                config.write_text(json.dumps(spec))
                output = Path(folder)/command
                self.assertEqual(self.invoke(command, "--config", str(config), "--output", str(output)), 0)
                runs = read_json(output/"runs.json")
                self.assertTrue(all(r["completed_safe_horizon"] for r in runs))
                self.assertIn("initial_viability", (output/"summary.csv").read_text())
                ET.parse(output/"trajectories"/"run-000.svg")
                self.assertIn("initial viability", (output/"report.md").read_text())

    def test_planar_audit_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder)/"config.json"
            case = dict(name="safe", p=[2, 0], v=[0, 0], nominal=[0, 0],
                        obstacles=[dict(center=[0, 0], radius=1)], duration="0.1", a_max=1)
            config.write_text(json.dumps({"cases": [case]}))
            self.assertEqual(self.invoke("planar-audit", "--config", str(config), "--output", folder), 0)
            self.assertEqual(len(read_json(Path(folder)/"audit.json")), 1)
            self.assertIn("Unsafe admitted", (Path(folder)/"report.md").read_text())

    def test_backup_plan_metrics_are_in_cli_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder)/"config.json"
            config.write_text(json.dumps({"method": "backup_candidates", "p": [-2, 0], "v": [1, 0],
                                          "horizon": "1", "max_candidates": 0}))
            self.assertEqual(self.invoke("planar-run", "--config", str(config), "--output", folder), 0)
            result = read_json(Path(folder)/"runs.json")[0]
            self.assertTrue(result["completed_safe_horizon"])
            self.assertEqual(result["stored_plan_steps"], 5)
            self.assertIn("controller_initialization_status", (Path(folder)/"summary.csv").read_text())
            self.assertIn("stroke-dasharray", (Path(folder)/"trajectories"/"run-000.svg").read_text())
            self.assertEqual(self.invoke("verify", "--runs", str(Path(folder)/"runs.json"), "--output", str(Path(folder)/"verified")), 0)
            self.assertEqual(read_json(Path(folder)/"verified"/"verification.json")["status"], "verified")


if __name__ == "__main__":
    unittest.main()
