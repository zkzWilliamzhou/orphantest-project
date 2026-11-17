import os
import tempfile
import unittest

from orphantest.adapters import (normalize_node, parse_junit, parse_pytest,
                                parse_unittest, reconcile_observations)
from orphantest.contract import load_contract, FORMAT
from orphantest.discover import classify, discover_nodes, scan_tree
from orphantest.limits import Budget, Limits
from orphantest.paths import validate_relative

CONFIG = {
    "format": FORMAT, "reviewed": True, "runner": "unittest",
    "discovery": {"roots": ["tests"], "patterns": ["test_*.py", "*_test.py"]},
    "commands": [], "exemptions": [], "junit_path": None, "limits": {},
}


def make_repo(files: dict) -> str:
    d = tempfile.mkdtemp(prefix="orphantest-disc-")
    os.makedirs(os.path.join(d, "tests"), exist_ok=True)
    for rel, content in files.items():
        path = os.path.join(d, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
    return d


def scan(d, config=None):
    c = load_contract(__import__("json").dumps(config or CONFIG).encode())
    fd = os.open(d, os.O_RDONLY | os.O_DIRECTORY)
    try:
        s = scan_tree(fd, c.discovery.roots, c.limits)
        matched, unmatched = classify(s.files, c.discovery.patterns)
        nodes, errors = discover_nodes(fd, matched, c.runner, c.limits,
                                       Budget(c.limits))
        return c, s, matched, unmatched, nodes, errors
    finally:
        os.close(fd)


class DiscoverTests(unittest.TestCase):
    def test_pytest_functions_and_classes(self):
        src = """import pytest

def test_one():
    assert True

class TestGroup:
    def test_two(self):
        assert 1

class Helper:
    def test_ignored(self):
        assert 1
"""
        d = make_repo({"tests/test_a.py": src})
        cfg = dict(CONFIG, runner="pytest")
        c, s, matched, unmatched, nodes, errors = scan(d, cfg)
        self.assertEqual([n["node"] for n in nodes], [
            "tests/test_a.py::TestGroup::test_two",
            "tests/test_a.py::test_one",
        ])
        self.assertEqual(errors, [])

    def test_unittest_only_testcase_subclasses(self):
        src = """import unittest
class TestReal(unittest.TestCase):
    def test_a(self): pass
class Plain:
    def test_b(self): pass
class TestPytestStyle:
    def test_c(self): pass
"""
        d = make_repo({"tests/test_a.py": src})
        c, s, matched, unmatched, nodes, errors = scan(d)
        self.assertEqual([n["node"] for n in nodes],
                         ["tests/test_a.py::TestReal::test_a"])

    def test_syntax_error_is_collection_error_not_crash(self):
        d = make_repo({"tests/test_broken.py": "def test_x(:\n"})
        c, s, matched, unmatched, nodes, errors = scan(d)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["kind"], "COLLECTION_ERROR")

    def test_unmatched_python_file_only(self):
        d = make_repo({"tests/legacy_test_tax.py": "x=1\n",
                       "tests/data.bin": "xx", "tests/notes.txt": "hi"})
        c, s, matched, unmatched, nodes, errors = scan(d)
        self.assertEqual([e.path.text for e in unmatched],
                         ["tests/legacy_test_tax.py"])

    def test_generated_dirs_skipped(self):
        d = make_repo({"tests/__pycache__/test_cached.py": "x=1\n",
                       "tests/test_real.py": "def test_x(): pass\n"})
        cfg = dict(CONFIG, runner="pytest")
        c, s, m, u, n, e = scan(d, cfg)
        self.assertEqual([x.path.text for x in m], ["tests/test_real.py"])
        self.assertTrue(any("generated directory" in w for w in s.warnings))

    def test_symlink_never_followed(self):
        d = make_repo({"tests/test_real.py": "def test_x(): pass\n"})
        outside = os.path.join(tempfile.gettempdir(), "orphantest-outside-src")
        with open(outside, "w") as fh:
            fh.write("def test_evil(): pass\n")
        os.symlink(outside, os.path.join(d, "tests", "test_link.py"))
        cfg = dict(CONFIG, runner="pytest")
        c, s, m, u, n, e = scan(d, cfg)
        self.assertIn("tests/test_link.py", s.symlinks)
        self.assertEqual([x.path.text for x in m], ["tests/test_real.py"])
        os.unlink(outside)

    def test_deterministic_node_order(self):
        src = "def test_z(): pass\ndef test_a(): pass\ndef test_m(): pass\n"
        d = make_repo({"tests/test_order.py": src})
        cfg = dict(CONFIG, runner="pytest")
        c, s, m, u, n, e = scan(d, cfg)
        self.assertEqual([x["node"] for x in n], sorted(x["node"] for x in n))


class AdapterTests(unittest.TestCase):
    def test_pytest_verbose(self):
        text = "tests/test_a.py::test_one PASSED\ntests/test_a.py::test_two FAILED\n"
        obs = parse_pytest(text, "c1")
        self.assertEqual([o.node for o in obs],
                         ["tests/test_a.py::test_one", "tests/test_a.py::test_two"])
        self.assertEqual([o.status for o in obs], ["executed", "failed"])

    def test_pytest_parameterized_normalizes(self):
        obs = parse_pytest("tests/test_a.py::test_x[1-a] PASSED\n", "c1")
        self.assertEqual(obs[0].node, "tests/test_a.py::test_x")

    def test_unittest_verbose_identity(self):
        text = "test_add (test_math.TestMath) ... ok\ntest_bad (test_math.TestMath) ... FAIL\n"
        obs = parse_unittest(text, "c1")
        self.assertEqual([o.node for o in obs],
                         ["test_math.TestMath.test_add", "test_math.TestMath.test_bad"])
        self.assertEqual([o.status for o in obs], ["executed", "failed"])

    def test_unittest_skipped_reason(self):
        obs = parse_unittest("test_x (a.B) ... skipped 'no db'\n", "c1")
        self.assertEqual(obs[0].status, "skipped")

    def test_junit_xml(self):
        xml = b"""<testsuite><testcase classname="test_math.TestMath" name="test_add" file="tests/test_math.py"/><testcase classname="x.Y" name="test_bad" file="tests/test_x.py"><failure/></testcase></testsuite>"""
        obs = parse_junit(xml, "c1")
        self.assertEqual(len(obs), 2)
        self.assertEqual(obs[0].status, "executed")
        self.assertEqual(obs[1].status, "failed")

    def test_junit_malformed_returns_empty(self):
        self.assertEqual(parse_junit(b"<broken", "c1"), [])

    def test_reconcile_maps_unittest_identity(self):
        discovered = [{"node": "tests/test_math.py::TestMath::test_add",
                       "file": "tests/test_math.py", "line": 1}]
        obs = parse_unittest("test_add (test_math.TestMath) ... ok\n", "c1")
        mapped, unrec = reconcile_observations(obs, discovered, "unittest")
        self.assertEqual(len(mapped), 1)
        self.assertEqual(mapped[0]["node"], discovered[0]["node"])
        self.assertEqual(unrec, [])

    def test_reconcile_reports_unknown_identity(self):
        obs = parse_unittest("test_ghost (missing.Mod) ... ok\n", "c1")
        mapped, unrec = reconcile_observations(obs, [], "unittest")
        self.assertEqual(mapped, [])
        self.assertEqual(unrec[0]["kind"], "NOT_RECONCILED")

    def test_pytest_reconcile_normalizes_leading_dot(self):
        discovered = [{"node": "tests/test_a.py::test_one"}]
        from orphantest.adapters import Observation
        obs = [Observation("./tests/test_a.py::test_one", "executed", "c1", "pytest-verbose")]
        mapped, unrec = reconcile_observations(obs, discovered, "pytest")
        self.assertEqual(mapped[0]["node"], "tests/test_a.py::test_one")
        self.assertEqual(unrec, [])

    def test_normalize_node(self):
        self.assertEqual(normalize_node("./a//b.py::x"), "a/b.py::x")


if __name__ == "__main__":
    unittest.main()
