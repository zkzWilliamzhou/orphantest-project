#!/usr/bin/env bash
# Full verification gates. Every gate prints its own evidence. Failure stops the run.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP" build *.egg-info; rm -rf examples/demo_repo/tests/__pycache__' EXIT

pass() { printf 'PASS  %s\n' "$1"; }

echo "=== gate 1: compile ==="
"$PY" -m compileall -q orphantest
pass "byte-compile"

echo "=== gate 2: full test suite ==="
"$PY" -m orphantest --self-test

echo "=== gate 3: golden files are reproducible ==="
cp tests/golden/demo_narrow.json "$TMP/narrow.json"
cp tests/golden/demo_reconciled.json "$TMP/reconciled.json"
"$PY" scripts/capture_golden.py
cmp "$TMP/narrow.json" tests/golden/demo_narrow.json
cmp "$TMP/reconciled.json" tests/golden/demo_reconciled.json
pass "golden byte-identical after regeneration"

echo "=== gate 4: raw ledger determinism (3 runs) ==="
for i in 1 2 3; do
  "$PY" -m orphantest --root examples/demo_repo \
    --config examples/demo_repo/orphantest.json --format json \
    --out "$TMP/raw$i.json" audit --execute --trust-config >/dev/null 2>&1 || true
done
cmp "$TMP/raw1.json" "$TMP/raw2.json"
cmp "$TMP/raw2.json" "$TMP/raw3.json"
pass "raw ledger byte-identical across 3 runs"

echo "=== gate 5: exit codes and demo states ==="
"$PY" -m orphantest --root examples/demo_repo \
  --config examples/demo_repo/orphantest.json \
  audit --execute --trust-config > "$TMP/human.txt" 2>&1 || test $? -eq 1
grep -q "DISCREPANCY_REPORTED" "$TMP/human.txt"
grep -q "ledger state only; not a code-correctness verdict" "$TMP/human.txt"
"$PY" -m orphantest --root examples/demo_repo \
  --config examples/demo_repo/orphantest.reconciled.json \
  audit --execute --trust-config > "$TMP/human2.txt" 2>&1
grep -q "INVENTORY_RECONCILED" "$TMP/human2.txt"
grep -qF "overall: DISCREPANCY_REPORTED (ledger state only; not a code-correctness verdict)   exit=1" docs/DESIGN.md
pass "demo output matches DESIGN.md"

echo "=== gate 6: SARIF shape ==="
"$PY" -m orphantest --root examples/demo_repo \
  --config examples/demo_repo/orphantest.json --format sarif \
  audit --execute --trust-config > "$TMP/report.sarif" 2>&1 || true
"$PY" - "$TMP/report.sarif" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1], encoding="utf-8"))
assert doc["version"] == "2.1.0", doc["version"]
run = doc["runs"][0]
rules = run["tool"]["driver"]["rules"]
assert [r["id"] for r in rules] == sorted(r["id"] for r in rules), "rules not sorted"
for r in run["results"]:
    assert r["partialFingerprints"]["orphantest/v1"], "missing fingerprint"
    assert isinstance(r["locations"][0]["physicalLocation"]["region"]["startLine"], int)
print(f"    sarif: {len(rules)} rules, {len(run['results'])} results")
PY
pass "SARIF 2.1.0 with sorted rules and fingerprints"

echo "=== gate 7: source prohibitions ==="
"$PY" - <<'PY'
import os
banned = ("shell=True", "os.system(", "import pickle", "import marshal", "eval(",
          "exec(", "yaml.load(", "import socket", "import urllib", "import requests",
          "import http.client")
hits = []
for base, dirs, files in os.walk("orphantest"):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for name in files:
        if not name.endswith(".py"):
            continue
        for n, line in enumerate(open(os.path.join(base, name), encoding="utf-8"), 1):
            if line.strip().startswith("#"):
                continue
            for token in banned:
                if token in line:
                    hits.append((name, n, token))
assert not hits, hits
PY
pass "no shell / eval / pickle / network primitives"

echo "=== gate 8: no secrets or forbidden verdict words in shipped output ==="
"$PY" - <<'PY'
import io, json, sys
from contextlib import redirect_stdout, redirect_stderr
sys.path.insert(0, ".")
from orphantest.cli import main
out, err = io.StringIO(), io.StringIO()
with redirect_stdout(out), redirect_stderr(err):
    main(["--root", "examples/demo_repo",
          "--config", "examples/demo_repo/orphantest.json",
          "--format", "json", "audit", "--execute", "--trust-config"])
doc = json.loads(out.getvalue())
assert "coverage" not in doc, "coverage key is forbidden"
for word in ("READY", "GREEN", "PASS ", "verified", "approved"):
    assert word not in out.getvalue(), word
assert "generated_at" not in doc, "timestamp must be opt-in"
print(f"    ledger: overall={doc['overall']} exit={doc['exit_code']}")
PY
pass "no verdict vocabulary, no default timestamp"

echo "=== gate 9: original tree unchanged by execution ==="
find examples/demo_repo/tests -maxdepth 1 -type f -name '*.py' -print0 \
  | sort -z | xargs -0 sha256sum > "$TMP/before.sha"
"$PY" -m orphantest --root examples/demo_repo \
  --config examples/demo_repo/orphantest.json \
  audit --execute --trust-config >/dev/null 2>&1 || true
find examples/demo_repo/tests -maxdepth 1 -type f -name '*.py' -print0 \
  | sort -z | xargs -0 sha256sum > "$TMP/after.sha"
cmp "$TMP/before.sha" "$TMP/after.sha"
test ! -d examples/demo_repo/tests/__pycache__ || { echo "FAIL: __pycache__ created in original tree"; exit 1; }
pass "original test files unchanged; no __pycache__"

echo "=== gate 10: package builds with correct metadata ==="
mkdir -p "$TMP/wheel"
"$PY" -m pip wheel --no-deps --no-build-isolation -w "$TMP/wheel" . >/dev/null 2>&1
ls "$TMP/wheel" | grep -q '^orphantest-1\.0\.0-.*\.whl$'
"$PY" - "$TMP/wheel" <<'PY'
import glob, sys, zipfile
w = glob.glob(sys.argv[1] + "/orphantest-1.0.0-*.whl")[0]
with zipfile.ZipFile(w) as z:
    names = z.namelist()
    assert "orphantest/cli.py" in names, "package missing cli.py"
    ep = [n for n in names if n.endswith("entry_points.txt")]
    assert ep, "missing console script entry point"
    assert b"orphantest = orphantest.cli:main" in z.read(ep[0])
print(f"    wheel: {w.split('/')[-1]}")
PY
pass "wheel name, module, and console entry point"

echo
echo "ALL VERIFICATION GATES PASSED"
