"""The interface is the test surface: exercise the evidence module directly.

These tests cross the seam at `write_bundle` / `load_bundle` / `validate_bundle`
rather than reaching into the CLI's private helpers.
"""

import json
import os
import shutil
import tempfile
import unittest

from orphantest.bundle import (Inventory, load_bundle, make_bundle,
                               validate_bundle, write_bundle)
from orphantest.contract import FORMAT, load_contract
from orphantest.errors import ConfigError
from orphantest.runner import CommandEvidence
from orphantest.store import BUNDLE_FORMAT, canonical_json, load_json_file

CONFIG = {
    "format": FORMAT, "reviewed": True, "runner": "unittest",
    "discovery": {"roots": ["tests"], "patterns": ["test_*.py"]},
    "commands": [{"id": "c1", "argv": ["python", "-m", "unittest", "-v"]}],
    "exemptions": [], "junit_path": None, "limits": {},
}


class _FakePath:
    def __init__(self, text):
        self.text = text


class _FakeEntry:
    def __init__(self, text):
        self.path = _FakePath(text)


class _FakeScan:
    files = (object(),)
    symlinks = ()
    unsupported = ()
    warnings = ()


def inventory():
    return Inventory(_FakeScan(), (), (_FakeEntry("tests/legacy_test_tax.py"),),
                     [{"node": "tests/test_math.py::TestMath::test_add",
                       "file": "tests/test_math.py", "line": 3}], [])


def evidences():
    from orphantest.adapters import Observation
    return [CommandEvidence("c1", ("python", "-m", "unittest", "-v"), 0, False,
                            "a" * 64, 0, 100, "b" * 64,
                            (Observation("test_math.TestMath.test_add", "executed",
                                         "c1", "unittest-verbose"),), ())]


class BundleModuleTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="orphantest-bundle-")
        self.contract = load_contract(json.dumps(CONFIG).encode("utf-8"))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_round_trip_through_the_interface(self):
        path = os.path.join(self.d, "e.json")
        write_bundle(path, evidences(), {"copied_files": 7}, self.contract,
                     inventory())
        data = load_bundle(path, self.contract)
        self.assertEqual(len(data.evidences), 1)
        self.assertEqual(data.evidences[0].observations[0].node,
                         "test_math.TestMath.test_add")
        self.assertEqual(data.meta["copied_files"], 7)

    def test_written_document_is_canonical_and_versioned(self):
        path = os.path.join(self.d, "e.json")
        doc = write_bundle(path, evidences(), {}, self.contract, inventory())
        self.assertEqual(doc["format"], BUNDLE_FORMAT)
        with open(path, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), canonical_json(doc))

    def test_validate_rejects_unknown_command_field(self):
        doc = make_bundle(evidences(), {}, self.contract, inventory())
        doc["commands"][0]["surprise"] = 1
        with self.assertRaises(ConfigError) as ctx:
            validate_bundle(doc, self.contract)
        self.assertIn("unknown fields", str(ctx.exception))

    def test_validate_rejects_malformed_observation(self):
        doc = make_bundle(evidences(), {}, self.contract, inventory())
        doc["commands"][0]["observations"] = ["not-an-object"]
        with self.assertRaises(ConfigError):
            validate_bundle(doc, self.contract)

    def test_validate_rejects_bool_returncode(self):
        doc = make_bundle(evidences(), {}, self.contract, inventory())
        doc["commands"][0]["returncode"] = True
        with self.assertRaises(ConfigError):
            validate_bundle(doc, self.contract)

    def test_stale_config_digest_fails_closed(self):
        doc = make_bundle(evidences(), {}, self.contract, inventory())
        doc["config_digest"] = "0" * 64
        with self.assertRaises(ConfigError):
            validate_bundle(doc, self.contract)

    def test_load_rejects_wrong_format(self):
        path = os.path.join(self.d, "e.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"format":"evil/1"}')
        with self.assertRaises(ConfigError):
            load_bundle(path, self.contract)

    def test_load_rejects_symlinked_input(self):
        real = os.path.join(self.d, "real.json")
        write_bundle(real, evidences(), {}, self.contract, inventory())
        link = os.path.join(self.d, "link.json")
        os.symlink(real, link)
        with self.assertRaises(ConfigError):
            load_bundle(link, self.contract)

    def test_load_rejects_deeply_nested_json(self):
        path = os.path.join(self.d, "e.json")
        with open(path, "wb") as fh:
            fh.write(b"[" * 200 + b"]" * 200)
        with self.assertRaises(ConfigError):
            load_bundle(path, self.contract)

    def test_load_fails_closed_on_pickle_payload(self):
        path = os.path.join(self.d, "e.json")
        with open(path, "wb") as fh:
            fh.write(b"\x80\x04\x95cos\nsystem\n(S'echo pwned'\ntR.")
        with self.assertRaises(ConfigError):
            load_bundle(path, self.contract)

    def test_inventory_value_is_immutable(self):
        inv = inventory()
        with self.assertRaises(Exception):
            inv.scan = None

    def test_make_bundle_records_inventory_counts(self):
        doc = make_bundle(evidences(), {}, self.contract, inventory())
        self.assertEqual(doc["inventory"]["files_total"], 1)
        self.assertEqual(doc["inventory"]["files_unmatched"],
                         ["tests/legacy_test_tax.py"])
        self.assertEqual(doc["inventory"]["discovered_nodes"],
                         ["tests/test_math.py::TestMath::test_add"])

    def test_load_preserves_executable_digest(self):
        path = os.path.join(self.d, "e.json")
        write_bundle(path, evidences(), {}, self.contract, inventory())
        data = load_bundle(path, self.contract)
        self.assertEqual(data.evidences[0].executable_digest, "b" * 64)


if __name__ == "__main__":
    unittest.main()
