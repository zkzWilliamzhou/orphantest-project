"""Regenerate normalized golden ledgers from the checked-in demo fixtures.

Portable across machines: machine-specific provenance and evidence digests are
stripped. The full raw ledger is compared byte-for-byte by scripts/verify.sh and
by docs/ARCHITECTURE.md's architecture-deepening gate.

Usage: python3 scripts/capture_golden.py
"""

from __future__ import annotations

import io
import json
import os
import sys
from contextlib import redirect_stdout, redirect_stderr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from orphantest.cli import main  # noqa: E402

VOLATILE_COMMAND_FIELDS = ("output_digest", "executable_digest",
                           "stdout_bytes", "stderr_bytes")


def normalize(ledger: dict) -> dict:
    doc = json.loads(json.dumps(ledger))
    doc.pop("provenance", None)
    doc.pop("generated_at", None)
    for row in doc.get("commands", []):
        for key in VOLATILE_COMMAND_FIELDS:
            row.pop(key, None)
    return doc


def capture(config_name: str) -> dict:
    argv = ["--root", os.path.join(ROOT, "examples", "demo_repo"),
            "--config", os.path.join(ROOT, "examples", "demo_repo", config_name),
            "--format", "json", "audit", "--execute", "--trust-config"]
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main(argv)
    if rc not in (0, 1):
        raise SystemExit(f"unexpected exit {rc}: {out.getvalue()} {err.getvalue()}")
    return normalize(json.loads(out.getvalue()))


def main_entry() -> int:
    targets = {
        "demo_narrow.json": "orphantest.json",
        "demo_reconciled.json": "orphantest.reconciled.json",
    }
    dest = os.path.join(ROOT, "tests", "golden")
    os.makedirs(dest, exist_ok=True)
    for filename, config in targets.items():
        doc = capture(config)
        path = os.path.join(dest, filename)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, sort_keys=True, indent=2, ensure_ascii=False)
            fh.write("\n")
        print(f"wrote {os.path.relpath(path, ROOT)}  "
              f"overall={doc['overall']}  findings={len(doc['findings'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_entry())
