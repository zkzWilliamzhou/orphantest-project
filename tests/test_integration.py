import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from orphantest import __version__
from orphantest.cli import main
from orphantest.contract import FORMAT
from orphantest.store import load_json_file, BUNDLE_FORMAT, LEDGER_FORMAT

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
DEMO = os.path.join(PROJECT, "examples", "demo_repo")
GOLDEN = os.path.join(HERE, "golden")


def run_cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            rc = main(argv)
        except SystemExit as exc:
            rc = int(exc.code) if exc.code is not None else 0
    return rc, out.getvalue(), err.getvalue()


VOLATILE_COMMAND_FIELDS = ("output_digest", "executable_digest",
                           "stdout_bytes", "stderr_bytes")


def normalize_ledger(ledger):
    """Strip machine-specific evidence so a golden file can ship in CI.

    The full raw ledger still gets a byte-for-byte comparison during the
    architecture-deepening round; see docs/ARCHITECTURE.md.
    """
    doc = json.loads(json.dumps(ledger))
    doc.pop("provenance", None)
    doc.pop("generated_at", None)
    for row in doc.get("commands", []):
        for key in VOLATILE_COMMAND_FIELDS:
            row.pop(key, None)
    return doc


def make_repo():
    d = tempfile.mkdtemp(prefix="orphantest-it-")
    os.makedirs(os.path.join(d, "tests"))
    with open(os.path.join(d, "tests", "test_math.py"), "w") as fh:
        fh.write("import unittest\nclass TestMath(unittest.TestCase):\n"
                 "    def test_add(self):\n        self.assertEqual(1+1, 2)\n")
    with open(os.path.join(d, "tests", "test_billing.py"), "w") as fh:
        fh.write("import unittest\nclass TestBilling(unittest.TestCase):\n"
                 "    def test_tax(self):\n        self.assertEqual(1, 1)\n")
    cfg = {
        "format": FORMAT, "reviewed": True, "runner": "unittest",
        "discovery": {"roots": ["tests"], "patterns": ["test_*.py"]},
        "commands": [{"id": "one", "argv": ["python", "-m", "unittest", "discover",
                                            "-s", "tests", "-p", "test_math.py", "-v"],
                      "timeout_seconds": 20}],
        "exemptions": [], "junit_path": None, "limits": {},
    }
    with open(os.path.join(d, "orphantest.json"), "w") as fh:
        json.dump(cfg, fh)
    return d


class CLITests(unittest.TestCase):
    def test_version(self):
        rc, out, _ = run_cli(["--version"])
        self.assertEqual(rc, 0)
        self.assertIn(__version__, out)

    def test_no_command_returns_usage(self):
        rc, out, _ = run_cli([])
        self.assertEqual(rc, 2)
        self.assertIn("usage", out)

    def test_init_writes_reviewed_false_config(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out, _ = run_cli(["--root", d, "init"])
            self.assertEqual(rc, 0)
            with open(os.path.join(d, "orphantest.json")) as fh:
                doc = json.load(fh)
            self.assertFalse(doc["reviewed"])
            self.assertEqual(doc["commands"], [])
            rc2, _, _ = run_cli(["--root", d, "init"])
            self.assertEqual(rc2, 4)

    def test_scan_is_read_only(self):
        d = make_repo()
        try:
            before = {p: os.stat(os.path.join(d, p)).st_mtime_ns
                      for p in os.listdir(d)}
            rc, out, _ = run_cli(["--root", d, "scan"])
            self.assertEqual(rc, 0)
            self.assertIn("nodes: 2", out)
            after = {p: os.stat(os.path.join(d, p)).st_mtime_ns
                     for p in os.listdir(d)}
            self.assertEqual(before, after)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_run_requires_trust(self):
        d = make_repo()
        try:
            rc, _, err = run_cli(["--root", d, "run"])
            self.assertEqual(rc, 2)
            self.assertIn("--trust-config", err)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_run_then_audit_from_bundle(self):
        d = make_repo()
        try:
            rc, _, _ = run_cli(["--root", d, "run", "--trust-config"])
            self.assertEqual(rc, 0)
            bundle = load_json_file(os.path.join(d, ".orphantest", "evidence.json"),
                                    BUNDLE_FORMAT)
            with open(os.path.join(d, "orphantest.json"), encoding="utf-8") as fh:
                cfg = json.load(fh)
            expected = __import__("hashlib").sha256(
                json.dumps(cfg, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False).encode("utf-8")).hexdigest()
            self.assertEqual(bundle["config_digest"], expected)
            rc2, out, _ = run_cli(["--root", d, "--format", "json", "audit"])
            self.assertEqual(rc2, 1)
            ledger = json.loads(out)
            self.assertEqual(ledger["format"], LEDGER_FORMAT)
            self.assertEqual(ledger["overall"], "DISCREPANCY_REPORTED")
            self.assertTrue(any(f["kind"] == "DISCOVERED_NOT_EXECUTED"
                                for f in ledger["findings"]))
            self.assertTrue(ledger["scope"]["declared_subset_only"])
            self.assertNotIn("generated_at", ledger)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_audit_without_evidence_is_capture_incomplete(self):
        d = make_repo()
        try:
            rc, out, _ = run_cli(["--root", d, "--format", "json", "audit"])
            self.assertEqual(rc, 3)
            ledger = json.loads(out)
            self.assertEqual(ledger["overall"], "CAPTURE_INCOMPLETE")
            self.assertTrue(any(f["kind"] == "CAPTURE_ERROR" for f in ledger["findings"]))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_stale_config_digest_is_rejected(self):
        d = make_repo()
        try:
            run_cli(["--root", d, "run", "--trust-config"])
            with open(os.path.join(d, "orphantest.json")) as fh:
                cfg = json.load(fh)
            cfg["commands"][0]["id"] = "changed"
            with open(os.path.join(d, "orphantest.json"), "w") as fh:
                json.dump(cfg, fh)
            rc, out, _ = run_cli(["--root", d, "--format", "json", "audit"])
            self.assertEqual(rc, 3)
            ledger = json.loads(out)
            self.assertEqual(ledger["overall"], "CAPTURE_INCOMPLETE")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_deterministic_json(self):
        d = make_repo()
        try:
            _, a, _ = run_cli(["--root", d, "--format", "json", "audit",
                              "--execute", "--trust-config"])
            _, b, _ = run_cli(["--root", d, "--format", "json", "audit",
                              "--execute", "--trust-config"])
            self.assertEqual(a, b)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_include_time_is_opt_in(self):
        d = make_repo()
        try:
            _, out, _ = run_cli(["--root", d, "--format", "json", "audit",
                                "--execute", "--trust-config", "--include-time"])
            self.assertIn("generated_at", json.loads(out))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_sarif_has_fingerprints_and_rules(self):
        d = make_repo()
        try:
            rc, out, _ = run_cli(["--root", d, "--format", "sarif", "audit",
                                  "--execute", "--trust-config"])
            self.assertEqual(rc, 1)
            doc = json.loads(out)
            self.assertEqual(doc["version"], "2.1.0")
            self.assertTrue(doc["runs"][0]["results"][0]["partialFingerprints"])
            self.assertTrue(doc["runs"][0]["tool"]["driver"]["rules"])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_report_rerenders_saved_ledger(self):
        d = make_repo()
        try:
            run_cli(["--root", d, "--format", "json", "--out",
                     os.path.join(d, "ledger.json"), "audit", "--execute",
                     "--trust-config"])
            rc, out, _ = run_cli(["--root", d, "report", os.path.join(d, "ledger.json")])
            self.assertEqual(rc, 1)
            self.assertIn("DISCREPANCY_REPORTED", out)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_completion_lists_commands(self):
        for shell in ("bash", "zsh", "fish", "powershell"):
            rc, out, _ = run_cli(["completion", shell])
            self.assertEqual(rc, 0)
            self.assertIn("audit", out)

    def test_error_message_names_input_and_fix(self):
        with tempfile.TemporaryDirectory() as d:
            rc, _, err = run_cli(["--root", d, "scan"])
            self.assertEqual(rc, 4)
            self.assertIn("orphantest.json", err)
            self.assertIn("next:", err)


class DemoTests(unittest.TestCase):
    def _ledger(self, config):
        rc, out, err = run_cli(["--root", DEMO, "--config",
                                os.path.join(DEMO, config), "--format", "json",
                                "audit", "--execute", "--trust-config"])
        return rc, json.loads(out), err

    def test_narrow_command_reports_gap(self):
        rc, ledger, _ = self._ledger("orphantest.json")
        self.assertEqual(rc, 1)
        self.assertEqual(ledger["overall"], "DISCREPANCY_REPORTED")
        kinds = {f["kind"] for f in ledger["findings"]}
        self.assertIn("NOT_DISCOVERED", kinds)
        self.assertIn("DISCOVERED_NOT_EXECUTED", kinds)

    def test_reconciled_config_reconciles(self):
        rc, ledger, _ = self._ledger("orphantest.reconciled.json")
        self.assertEqual(rc, 0)
        self.assertEqual(ledger["overall"], "INVENTORY_RECONCILED")
        self.assertTrue(any(f["kind"] == "EXEMPT" for f in ledger["findings"]))

    def test_golden_ledger_matches(self):
        path = os.path.join(GOLDEN, "demo_narrow.json")
        if not os.path.exists(path):
            self.skipTest("golden not captured yet")
        with open(path, encoding="utf-8") as fh:
            expected = json.load(fh)
        _, ledger, _ = self._ledger("orphantest.json")
        self.assertEqual(normalize_ledger(ledger), expected)

    def test_original_tree_unchanged_by_execute(self):
        def snapshot():
            result = {}
            for base, dirs, files in os.walk(DEMO):
                dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git",
                                                        ".orphantest")]
                for name in files:
                    p = os.path.join(base, name)
                    result[os.path.relpath(p, DEMO)] = os.stat(p).st_mtime_ns
            return result
        before = snapshot()
        self._ledger("orphantest.json")
        self.assertEqual(before, snapshot())


class SelfTestTests(unittest.TestCase):
    def test_self_test_runs(self):
        if os.environ.get("ORPHANTEST_SELFTEST_CHILD"):
            self.skipTest("re-entrant self-test")
        previous = os.environ.get("ORPHANTEST_SELFTEST_CHILD")
        os.environ["ORPHANTEST_SELFTEST_CHILD"] = "1"
        try:
            rc, out, err = run_cli(["--self-test"])
        finally:
            if previous is None:
                os.environ.pop("ORPHANTEST_SELFTEST_CHILD", None)
            else:
                os.environ["ORPHANTEST_SELFTEST_CHILD"] = previous
        self.assertEqual(rc, 0, msg=out + err)
        self.assertIn("OK", out + err)


if __name__ == "__main__":
    unittest.main()
