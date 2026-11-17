import json
import os
import stat
import subprocess
import tempfile
import unittest

from orphantest.contract import FORMAT, load_contract
from orphantest.errors import ConfigError, LimitError, PathError
from orphantest.git import GitGateway
from orphantest.limits import Limits
from orphantest.paths import read_scoped, validate_relative
from orphantest.redact import redact, redact_obj
from orphantest.store import atomic_write, canonical_json, load_json_file


def valid_config(**overrides):
    doc = {
        "format": FORMAT, "reviewed": True, "purpose": "local_feedback",
        "runner": "unittest",
        "discovery": {"roots": ["tests"], "patterns": ["test_*.py"]},
        "commands": [{"id": "unit", "argv": ["python", "-m", "unittest", "-v"]}],
        "exemptions": [], "junit_path": None, "limits": {},
    }
    doc.update(overrides)
    return json.dumps(doc).encode()


class PathTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_relative("tests/unit/test_a.py").parts,
                         ("tests", "unit", "test_a.py"))

    def test_rejections(self):
        bad = ["", "/etc/passwd", "a/../b", "a/./b", "a//b", "a\\b",
               "a\x00b", "-rf", "a/-x", "tests/\u202eevil.py", "a/b/", ".."]
        for text in bad:
            with self.subTest(text=text):
                with self.assertRaises(PathError):
                    validate_relative(text)

    def test_long_path_rejected(self):
        with self.assertRaises(PathError):
            validate_relative("a" * 600, limits=Limits())

    def test_read_scoped_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            outside = os.path.join(tempfile.gettempdir(), "orphantest-outside")
            with open(outside, "w") as fh:
                fh.write("secret")
            os.symlink(outside, os.path.join(d, "link.py"))
            fd = os.open(d, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with self.assertRaises(PathError):
                    read_scoped(fd, validate_relative("link.py"), Limits())
            finally:
                os.close(fd)
                os.unlink(outside)

    def test_read_scoped_regular_file(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "a.py"), "wb") as fh:
                fh.write(b"x = 1\n")
            fd = os.open(d, os.O_RDONLY | os.O_DIRECTORY)
            try:
                self.assertEqual(read_scoped(fd, validate_relative("a.py"), Limits()),
                                 b"x = 1\n")
            finally:
                os.close(fd)


class LimitsTests(unittest.TestCase):
    def test_unknown_key_rejected(self):
        with self.assertRaises(LimitError):
            Limits.from_config({"bogus": 1})

    def test_non_positive_rejected(self):
        for value in (0, -1, True, 1.5, "10"):
            with self.subTest(value=value):
                with self.assertRaises(LimitError):
                    Limits.from_config({"max_files": value})

    def test_hostile_upper_bound_is_capped(self):
        lim = Limits.from_config({"max_files": 10 ** 9})
        self.assertEqual(lim.max_files, Limits().max_files)


class ContractTests(unittest.TestCase):
    def test_valid(self):
        c = load_contract(valid_config())
        self.assertEqual(len(c.commands), 1)
        self.assertEqual(c.discovery.roots, ("tests",))
        self.assertEqual(len(c.digest), 64)

    def test_unknown_keys(self):
        with self.assertRaises(ConfigError):
            load_contract(valid_config(bogus=1))

    def test_wrong_format(self):
        with self.assertRaises(ConfigError):
            load_contract(valid_config(format="other"))

    def test_no_commands_is_allowed_but_reported(self):
        c = load_contract(valid_config(commands=[]))
        self.assertEqual(c.commands, ())

    def test_shell_string_rejected(self):
        doc = json.loads(valid_config())
        doc["commands"][0]["argv"] = ["bash", "-c", "pytest && rm -rf /"]
        with self.assertRaises(ConfigError):
            load_contract(json.dumps(doc).encode())

    def test_relative_executable_rejected(self):
        doc = json.loads(valid_config())
        doc["commands"][0]["argv"] = ["pytest", "-q"]
        with self.assertRaises(ConfigError):
            load_contract(json.dumps(doc).encode())

    def test_nul_in_argv_rejected(self):
        doc = json.loads(valid_config())
        doc["commands"][0]["argv"] = ["python", "bad\x00arg"]
        with self.assertRaises(ConfigError):
            load_contract(json.dumps(doc).encode())

    def test_short_exemption_reason_rejected(self):
        with self.assertRaises(ConfigError):
            load_contract(valid_config(exemptions=[{"node": "a", "reason": "soon"}]))

    def test_unsafe_root_rejected(self):
        with self.assertRaises((ConfigError, PathError)):
            load_contract(valid_config(discovery={"roots": ["../tests"],
                                                 "patterns": ["test_*.py"]}))

    def test_invalid_json(self):
        with self.assertRaises(ConfigError):
            load_contract(b"{not json")

    def test_non_object(self):
        with self.assertRaises(ConfigError):
            load_contract(b"[]")


class RedactTests(unittest.TestCase):
    def test_bearer_token(self):
        out = redact("Authorization: Bearer abcdef1234567890")
        self.assertNotIn("abcdef1234567890", out)
        self.assertIn("REDACTED", out)

    def test_aws_key(self):
        out = redact("AKIAIOSFODNN7EXAMPLE")
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", out)

    def test_nested(self):
        obj = {"a": ["Bearer abcdef1234567890"], "b": {"c": "AKIAIOSFODNN7EXAMPLE"}}
        self.assertNotIn("abcdef1234567890", json.dumps(redact_obj(obj)))

    def test_home_path(self):
        home = os.path.expanduser("~")
        self.assertNotIn(home, redact(f"file at {home}/thing.py"))


class GitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q", self.tmp], check=True)
        with open(os.path.join(self.tmp, "a.txt"), "w") as fh:
            fh.write("x")
        subprocess.run(["git", "-C", self.tmp, "add", "a.txt"], check=True)
        subprocess.run(["git", "-C", self.tmp, "-c", "user.email=a@b.invalid",
                        "-c", "user.name=a", "commit", "-qm", "init"], check=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_provenance(self):
        g = GitGateway(self.tmp)
        try:
            p = g.provenance()
            self.assertTrue(p["git_available"])
            self.assertEqual(len(p["head"]), 40)
        finally:
            g.close()

    def test_blocked_subcommand(self):
        g = GitGateway(self.tmp)
        try:
            with self.assertRaises(Exception):
                g.run("push")
        finally:
            g.close()

    def test_blocked_argument(self):
        g = GitGateway(self.tmp)
        try:
            with self.assertRaises(Exception):
                g.run("rev-parse", ("--upload-pack=/bin/sh",))
        finally:
            g.close()


class StoreTests(unittest.TestCase):
    def test_atomic_write_is_private_and_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.json")
            atomic_write(path, canonical_json({"b": 1, "a": 2}))
            mode = stat.S_IMODE(os.stat(path).st_mode)
            self.assertEqual(mode, 0o600)
            with open(path, "r", encoding="utf-8") as fh:
                self.assertEqual(fh.read(), canonical_json({"a": 2, "b": 1}))
            leftovers = [n for n in os.listdir(d) if n.startswith(".orphantest-")]
            self.assertEqual(leftovers, [])

    def test_reader_rejects_symlink(self):
        from orphantest.store import read_regular_file
        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "real.json")
            with open(target, "w") as fh:
                fh.write("{}")
            link = os.path.join(d, "link.json")
            os.symlink(target, link)
            with self.assertRaises(ConfigError):
                read_regular_file(link, 1024)

    def test_load_rejects_wrong_format(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.json")
            with open(path, "w") as fh:
                json.dump({"format": "wrong"}, fh)
            with self.assertRaises(ConfigError):
                load_json_file(path, "orphantest/evidence/1")


if __name__ == "__main__":
    unittest.main()
