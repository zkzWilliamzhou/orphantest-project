"""Adversarial inputs. Every case must fail closed or produce a bounded result."""

import io
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from orphantest.adapters import reconcile_observations, Observation
from orphantest.cli import main
from orphantest.contract import FORMAT, load_contract
from orphantest.discover import scan_tree, classify
from orphantest.errors import ConfigError, LimitError, PathError
from orphantest.limits import Limits
from orphantest.paths import validate_relative
from orphantest.redact import redact
from orphantest.runner import _safe_env
from orphantest.store import (check_json_depth, load_json_file, read_regular_file,
                              BUNDLE_FORMAT)

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            rc = main(argv)
        except SystemExit as exc:
            rc = int(exc.code) if exc.code is not None else 0
    return rc, out.getvalue(), err.getvalue()


BASE_CONFIG = {
    "format": FORMAT, "reviewed": True, "runner": "pytest",
    "discovery": {"roots": ["tests"], "patterns": ["test_*.py"]},
    "commands": [], "exemptions": [], "junit_path": None, "limits": {},
}


class PathAttackTests(unittest.TestCase):
    def test_01_absolute_diff_path(self):
        with self.assertRaises(PathError):
            validate_relative("/etc/hosts")

    def test_02_dotdot_traversal(self):
        with self.assertRaises(PathError):
            validate_relative("../../tmp/x")

    def test_03_backslash_separator(self):
        with self.assertRaises(PathError):
            validate_relative("src\\evil.py")

    def test_04_nul_byte(self):
        with self.assertRaises(PathError):
            validate_relative("a\x00b.py")

    def test_05_leading_dash_option_injection(self):
        for name in ("-rf", "a/-config", "--output=evil"):
            with self.subTest(name=name):
                with self.assertRaises(PathError):
                    validate_relative(name)

    def test_06_bidi_control(self):
        for text in ("tests/\u202eevil.py", "tests/\u2066x.py", "a\u200fb.py"):
            with self.subTest(text=text):
                with self.assertRaises(PathError):
                    validate_relative(text)

    def test_07_homoglyph_identifier(self):
        with self.assertRaises(PathError):
            validate_relative("tests/test_payl\u043ead.py")

    def test_08_nfkc_instability(self):
        with self.assertRaises(PathError):
            validate_relative("tests/\uff54est.py")

    def test_09_directory_symlink_escape(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tests"))
            outside = tempfile.mkdtemp(prefix="orphantest-outside-")
            try:
                with open(os.path.join(outside, "test_evil.py"), "w") as fh:
                    fh.write("def test_x(): pass\n")
                os.symlink(outside, os.path.join(d, "tests", "escape"))
                fd = os.open(d, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    s = scan_tree(fd, ("tests",), Limits())
                finally:
                    os.close(fd)
                self.assertIn("tests/escape", s.symlinks)
                self.assertFalse(any("test_evil" in x.path.text for x in s.files))
            finally:
                shutil.rmtree(outside, ignore_errors=True)

    def test_10_final_component_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "target.py"), "w") as fh:
                fh.write("x=1\n")
            os.symlink("target.py", os.path.join(d, "link.py"))
            fd = os.open(d, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with self.assertRaises(PathError):
                    from orphantest.paths import read_scoped
                    read_scoped(fd, validate_relative("link.py"), Limits())
            finally:
                os.close(fd)


class InputAttackTests(unittest.TestCase):
    def test_11_invalid_utf8_config(self):
        with self.assertRaises(ConfigError):
            load_contract(b'{"format": "orphantest/config/1", "bad": "\xff"}')

    def test_12_deep_json_nesting(self):
        raw = b"[" * 200 + b"]" * 200
        with self.assertRaises(ConfigError):
            check_json_depth(raw)
        with self.assertRaises(ConfigError):
            load_contract(raw)

    def test_13_braces_inside_strings_are_allowed(self):
        raw = json.dumps({"a": "{" * 200}).encode()
        check_json_depth(raw)  # must not raise

    def test_14_huge_config_rejected(self):
        with self.assertRaises(ConfigError):
            load_contract(b" " * (1024 * 1024 + 2))

    def test_15_pickle_payload_is_inert_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "e.json")
            with open(p, "wb") as fh:
                fh.write(b"\x80\x04\x95cos\nsystem\n(S'echo pwned'\ntR.")
            with self.assertRaises(ConfigError):
                load_json_file(p, BUNDLE_FORMAT)

    def test_16_unknown_format_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "e.json")
            with open(p, "w") as fh:
                fh.write('{"format":"evil/1"}')
            with self.assertRaises(ConfigError):
                load_json_file(p, BUNDLE_FORMAT)

    def test_17_symlinked_input_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            real = os.path.join(d, "real.json")
            with open(real, "w") as fh:
                fh.write('{"format":"orphantest/evidence/1"}')
            link = os.path.join(d, "link.json")
            os.symlink(real, link)
            with self.assertRaises(ConfigError):
                load_json_file(link, BUNDLE_FORMAT)

    def test_18_huge_file_limit(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "big.bin")
            with open(p, "wb") as fh:
                fh.truncate(4 * 1024 * 1024)
            with self.assertRaises(LimitError):
                read_regular_file(p, 2 * 1024 * 1024)

    def test_19_deep_tree_limit(self):
        with tempfile.TemporaryDirectory() as d:
            cur = os.path.join(d, "tests")
            os.makedirs(cur)
            for _ in range(40):
                cur = os.path.join(cur, "x")
                os.makedirs(cur)
            fd = os.open(d, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with self.assertRaises(LimitError):
                    scan_tree(fd, ("tests",), Limits.from_config({"max_depth": 8}))
            finally:
                os.close(fd)

    def test_20_file_count_limit(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tests"))
            for i in range(60):
                with open(os.path.join(d, "tests", f"test_{i}.py"), "w") as fh:
                    fh.write("x=1\n")
            fd = os.open(d, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with self.assertRaises(LimitError):
                    scan_tree(fd, ("tests",),
                              Limits.from_config({"max_files": 10}))
            finally:
                os.close(fd)


class ExecutionAttackTests(unittest.TestCase):
    def test_21_safe_env_has_no_secrets(self):
        os.environ["AWS_SECRET_ACCESS_KEY"] = "supersecretvalue123"
        try:
            env = _safe_env("/tmp/repo", "/tmp/home")
            self.assertNotIn("AWS_SECRET_ACCESS_KEY", env)
            self.assertNotIn("supersecretvalue123", json.dumps(env))
            self.assertEqual(env["HOME"], "/tmp/home")
            self.assertNotEqual(env["HOME"], os.path.expanduser("~"))
        finally:
            os.environ.pop("AWS_SECRET_ACCESS_KEY", None)

    def test_22_no_shell_in_source(self):
        hits = []
        for base, dirs, files in os.walk(os.path.join(PROJECT, "orphantest")):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for name in files:
                if name.endswith(".py"):
                    with open(os.path.join(base, name), encoding="utf-8") as fh:
                        for lineno, line in enumerate(fh, 1):
                            if "shell=True" in line or "os.system(" in line:
                                # A comment or a prohibition string is allowed.
                                if "must never" in line.lower() or line.strip().startswith("#"):
                                    continue
                                hits.append((name, lineno, line.strip()))
        self.assertEqual(hits, [])

    def test_23_no_pickle_or_eval_import(self):
        banned = ("import pickle", "import marshal", "eval(", "exec(", "yaml.load(")
        hits = []
        for base, dirs, files in os.walk(os.path.join(PROJECT, "orphantest")):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for name in files:
                if name.endswith(".py"):
                    with open(os.path.join(base, name), encoding="utf-8") as fh:
                        for lineno, line in enumerate(fh, 1):
                            for token in banned:
                                if token in line and not line.strip().startswith("#"):
                                    hits.append((name, lineno, token))
        self.assertEqual(hits, [])

    def test_24_no_network_imports(self):
        banned = ("import socket", "import urllib", "import requests", "import http.client")
        hits = []
        for base, dirs, files in os.walk(os.path.join(PROJECT, "orphantest")):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for name in files:
                if name.endswith(".py"):
                    with open(os.path.join(base, name), encoding="utf-8") as fh:
                        for line in fh:
                            for token in banned:
                                if token in line and not line.strip().startswith("#"):
                                    hits.append((name, token))
        self.assertEqual(hits, [])

    def test_25_git_gateway_rejects_option_like_path(self):
        from orphantest.git import GitGateway
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-q", d], check=True)
            g = GitGateway(d)
            try:
                with self.assertRaises(Exception):
                    g.run("diff", paths=("--upload-pack=/bin/sh",))
            finally:
                g.close()

    def test_26_config_rejects_unknown_include_key(self):
        doc = dict(BASE_CONFIG, **{"!include": "/etc/passwd"})
        with self.assertRaises(ConfigError):
            load_contract(json.dumps(doc).encode())

    def test_27_config_rejects_absolute_junit_path(self):
        doc = dict(BASE_CONFIG, junit_path="/etc/passwd")
        with self.assertRaises((ConfigError, PathError)):
            load_contract(json.dumps(doc).encode())

    def test_28_redaction_survives_nested_report(self):
        from orphantest.redact import redact_obj
        obj = {"findings": [{"evidence": "Bearer abcdef1234567890"}]}
        self.assertNotIn("abcdef1234567890", json.dumps(redact_obj(obj)))

    def test_29_redaction_does_not_destroy_digests(self):
        digest = "a" * 64
        self.assertEqual(redact(digest), digest)

    def test_30_error_output_hides_home_path(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out, err = run_cli(["--root", d, "scan"])
            self.assertEqual(rc, 4)
            self.assertNotIn(os.path.expanduser("~"), err + out)

    def test_31_command_timeout_is_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tests"))
            with open(os.path.join(d, "tests", "test_slow.py"), "w") as fh:
                fh.write("import unittest\nclass T(unittest.TestCase):\n"
                         "    def test_x(self):\n        import time; time.sleep(30)\n")
            cfg = dict(BASE_CONFIG, runner="unittest",
                       commands=[{"id": "slow", "argv": ["python", "-m", "unittest",
                                                        "discover", "-s", "tests", "-v"],
                                  "timeout_seconds": 2}])
            with open(os.path.join(d, "orphantest.json"), "w") as fh:
                json.dump(cfg, fh)
            rc, out, _ = run_cli(["--root", d, "--format", "json", "audit",
                                  "--execute", "--trust-config"])
            ledger = json.loads(out)
            errs = [e for c in ledger["commands"] for e in c["errors"]]
            self.assertIn("COMMAND_TIMEOUT", errs)
            self.assertEqual(ledger["overall"], "CAPTURE_INCOMPLETE")

    def test_32_malformed_bundle_observation_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tests"))
            with open(os.path.join(d, "tests", "test_a.py"), "w") as fh:
                fh.write("def test_x(): pass\n")
            cfg = dict(BASE_CONFIG, commands=[{"id": "x",
                                               "argv": ["python", "-m", "unittest",
                                                        "discover", "-s", "tests", "-v"]}])
            with open(os.path.join(d, "orphantest.json"), "w") as fh:
                json.dump(cfg, fh)
            from orphantest.contract import load_contract as lc
            digest = lc(json.dumps(cfg).encode()).digest
            os.makedirs(os.path.join(d, ".orphantest"))
            with open(os.path.join(d, ".orphantest", "evidence.json"), "w") as fh:
                json.dump({"format": BUNDLE_FORMAT, "config_digest": digest,
                           "commands": [{"id": "x", "argv": ["python"],
                                         "observations": ["not-an-object"],
                                         "errors": [], "returncode": 0}]}, fh)
            rc, out, _ = run_cli(["--root", d, "--format", "json", "audit"])
            self.assertEqual(rc, 3)
            self.assertIn("CAPTURE_ERROR", out)

    def test_33_unreconciled_observation_is_not_silently_dropped(self):
        obs = [Observation("ghost.module.test_x", "executed", "c1", "unittest-verbose")]
        mapped, unrec = reconcile_observations(obs, [], "unittest")
        self.assertEqual(mapped, [])
        self.assertEqual(unrec[0]["kind"], "NOT_RECONCILED")

    def test_34_original_tree_unchanged_after_run(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tests"))
            with open(os.path.join(d, "tests", "test_a.py"), "w") as fh:
                fh.write("def test_x(): pass\n")
            cfg = dict(BASE_CONFIG, runner="pytest",
                       commands=[{"id": "c", "argv": ["python", "-m", "unittest",
                                                      "discover", "-s", "tests", "-v"]}])
            with open(os.path.join(d, "orphantest.json"), "w") as fh:
                json.dump(cfg, fh)
            with open(os.path.join(d, "tests", "test_a.py"), "rb") as fh:
                before = fh.read()
            run_cli(["--root", d, "run", "--trust-config"])
            with open(os.path.join(d, "tests", "test_a.py"), "rb") as fh:
                self.assertEqual(fh.read(), before)
            self.assertFalse(os.path.exists(os.path.join(d, "tests", "__pycache__")))

    def test_35_atomic_write_leaves_no_partial_file(self):
        from orphantest.store import atomic_write
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "out.json")
            atomic_write(p, "{}")
            self.assertEqual([x for x in os.listdir(d) if x.startswith(".orphantest-")], [])
            self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
