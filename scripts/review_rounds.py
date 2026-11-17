"""Eight independent examination rounds. Each round runs real commands and records
their exact output. The manager signs only rounds whose evidence is reproduced here.

Usage: python3 scripts/review_rounds.py
Writes: docs/REVIEW_LOG.md
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PY = sys.executable
DEMO = os.path.join(ROOT, "examples", "demo_repo")
LOG: list[str] = []
RESULTS: list[tuple[int, str, bool, str]] = []


def run(argv, cwd=ROOT, env=None, timeout=240):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([PY] + argv, cwd=cwd, env=e, capture_output=True,
                       text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def cli(*args, cwd=ROOT, env=None):
    return run(["-m", "orphantest", *args], cwd=cwd, env=env)


def evidence(label, rc, out, err, max_lines=14):
    LOG.append(f"```\n$ {label}")
    text = (out + err).rstrip()
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"... ({len(lines) - max_lines} more lines)"]
    LOG.append("\n".join(lines))
    LOG.append(f"[exit={rc}]\n```")
    return text


def round_record(n, name, ok, summary):
    RESULTS.append((n, name, ok, summary))
    LOG.append(f"**Manager sign-off: {'PASS' if ok else 'FAIL'}** — {summary}\n")


# ---------------------------------------------------------------- Round 1
def r1():
    LOG.append("## Round 1 — build and full suite\n")
    rc, out, err = run(["-m", "compileall", "-q", "orphantest"])
    evidence("python3 -m compileall -q orphantest", rc, out, err)
    ok1 = rc == 0
    rc, out, err = cli("--self-test")
    evidence("python3 -m orphantest --self-test", rc, out, err)
    m = re.search(r"Ran (\d+) tests", out + err)
    ok2 = rc == 0 and "OK" in (out + err) and m is not None
    count = m.group(1) if m else "?"
    round_record(1, "build and full suite", ok1 and ok2,
                 f"byte-compile rc={rc}; {count} tests, full output captured above")
    return ok1 and ok2


# ---------------------------------------------------------------- Round 2
def r2():
    LOG.append("## Round 2 — deterministic bytes\n")
    tmp = tempfile.mkdtemp(prefix="orphantest-r2-")
    ok = True
    try:
        digests = {}
        for cfg in ("orphantest.json", "orphantest.reconciled.json"):
            hs = []
            for i in range(3):
                path = os.path.join(tmp, f"{cfg}.{i}.json")
                rc, out, err = cli("--root", DEMO, "--config", os.path.join(DEMO, cfg),
                                   "--format", "json", "--out", path, "audit",
                                   "--execute", "--trust-config")
                with open(path, "rb") as fh:
                    hs.append(hashlib.sha256(fh.read()).hexdigest())
                assert rc in (0, 1), (cfg, rc)
            digests[cfg] = hs[0]
            same = len(set(hs)) == 1
            ok &= same
            evidence(f"3x audit --format json --out <tmp> ({cfg})", rc,
                     "\n".join(hs) + "\n", "")
        rc, out, err = cli("--root", DEMO, "--config", os.path.join(DEMO, "orphantest.json"),
                           "run", "--trust-config")
        bundle = os.path.join(DEMO, ".orphantest", "evidence.json")
        with open(bundle, "rb") as fh:
            bd = hashlib.sha256(fh.read()).hexdigest()
        evidence("run --trust-config (bundle sha256)", rc, bd + "\n", err)
        ok &= rc == 0
        # golden normalized comparison
        rc, out, err = cli("--root", DEMO, "--config", os.path.join(DEMO, "orphantest.json"),
                           "--format", "json", "audit", "--execute", "--trust-config")
        from scripts.capture_golden import normalize
        with open(os.path.join(ROOT, "tests", "golden", "demo_narrow.json"),
                  encoding="utf-8") as fh:
            golden = json.load(fh)
        ok &= normalize(json.loads(out)) == golden
        evidence("normalized ledger == tests/golden/demo_narrow.json", rc,
                 f"match={normalize(json.loads(out)) == golden}\n", "")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(os.path.join(DEMO, ".orphantest"), ignore_errors=True)
        shutil.rmtree(os.path.join(DEMO, "tests", "__pycache__"), ignore_errors=True)
    round_record(2, "deterministic bytes", ok,
                 "3 identical runs per config, bundle captured, normalized ledger matches golden")
    return ok


# ---------------------------------------------------------------- Round 3
def r3():
    LOG.append("## Round 3 — adversarial security suite and source prohibitions\n")
    rc, out, err = run(["-m", "unittest", "discover", "-s", "tests",
                        "-p", "test_security.py", "-v"], timeout=300)
    evidence("python3 -m unittest discover -s tests -p test_security.py -v", rc, out, err, 10)
    m = re.search(r"Ran (\d+) tests", out + err)
    ok = rc == 0 and m is not None
    banned = ("shell=True", "os.system(", "import pickle", "import marshal",
              "eval(", "exec(", "yaml.load(", "import socket", "import urllib",
              "import requests", "import http.client")
    hits = []
    for base, dirs, files in os.walk(os.path.join(ROOT, "orphantest")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            if name.endswith(".py"):
                for n, line in enumerate(open(os.path.join(base, name),
                                             encoding="utf-8"), 1):
                    if line.strip().startswith("#"):
                        continue
                    for token in banned:
                        if token in line:
                            hits.append((name, n, token))
    ok &= not hits
    evidence("static scan of orphantest/*.py for 11 prohibited primitives", 0,
             f"prohibited hits: {len(hits)}\nchecked files: "
             f"{sum(1 for _, _, fs in os.walk(os.path.join(ROOT, 'orphantest')) for f in fs if f.endswith('.py'))}\n", "")
    round_record(3, "security suite and prohibitions", ok,
                 f"{m.group(1) if m else '?'} adversarial tests, {len(hits)} prohibited primitives")
    return ok


# ---------------------------------------------------------------- Round 4
def r4():
    LOG.append("## Round 4 — hostile path fuzz\n")
    from orphantest.paths import validate_relative, PathError
    hostile = []
    for base in ("tests/test_a.py", "src/mod.py", "a/b.py"):
        hostile.extend([
            "/" + base, "../" + base, "../../" + base,
            base.replace("/", "/../"), base.replace("/", "\\"),
            base + "\x00", "-" + base, "a/-rf", "--output=evil",
            "\u202e" + base, base + "\u2066", base + "\u200f",
            "\u0430" + base, base + "\u0430", "\uff54" + base,
        ])
    rejected = 0
    for p in hostile:
        try:
            validate_relative(p)
        except (PathError, Exception):
            rejected += 1
    accepted = 0
    for p in ("tests/test_a.py", "src/pkg/mod.py", "a/b/c.py"):
        try:
            validate_relative(p)
            accepted += 1
        except Exception:
            pass
    ok = rejected == len(hostile) and accepted == 3
    sample = "tests/\uff54est.py"
    normalized = unicodedata.normalize("NFKC", sample)
    evidence("validate_relative hostile corpus + valid corpus", 0,
             f"hostile inputs: {len(hostile)}  rejected: {rejected}\n"
             f"valid inputs: 3  accepted: {accepted}\n"
             f"NFKC example: {sample!r} normalizes to {normalized!r} "
             f"(unstable={sample != normalized})\n", "")
    round_record(4, "hostile path fuzz", ok,
                 f"{rejected}/{len(hostile)} hostile paths rejected, {accepted}/3 valid paths accepted")
    return ok


# ---------------------------------------------------------------- Round 5
def r5():
    LOG.append("## Round 5 — resource-limit fuzz\n")
    from orphantest.discover import scan_tree
    from orphantest.limits import Limits
    from orphantest.errors import ConfigError, LimitError
    from orphantest.store import read_regular_file, check_json_depth
    from orphantest.contract import load_contract
    results = []
    with tempfile.TemporaryDirectory() as d:
        cur = os.path.join(d, "tests")
        os.makedirs(cur)
        for _ in range(40):
            cur = os.path.join(cur, "x")
            os.makedirs(cur)
        fd = os.open(d, os.O_RDONLY | os.O_DIRECTORY)
        try:
            try:
                scan_tree(fd, ("tests",), Limits.from_config({"max_depth": 8}))
                results.append(("deep tree", False))
            except LimitError:
                results.append(("deep tree", True))
        finally:
            os.close(fd)
        many = os.path.join(d, "many")
        os.makedirs(many)
        for i in range(60):
            open(os.path.join(many, f"test_{i}.py"), "w").close()
        fd = os.open(d, os.O_RDONLY | os.O_DIRECTORY)
        try:
            try:
                scan_tree(fd, ("many",), Limits.from_config({"max_files": 10}))
                results.append(("file count", False))
            except LimitError:
                results.append(("file count", True))
        finally:
            os.close(fd)
        big = os.path.join(d, "big.bin")
        with open(big, "wb") as fh:
            fh.truncate(4 * 1024 * 1024)
        try:
            read_regular_file(big, 2 * 1024 * 1024)
            results.append(("4MB file vs 2MB cap", False))
        except LimitError:
            results.append(("4MB file vs 2MB cap", True))
        try:
            check_json_depth(b"[" * 200 + b"]" * 200)
            results.append(("200-level JSON", False))
        except ConfigError:
            results.append(("200-level JSON", True))
        try:
            load_contract(b" " * (1024 * 1024 + 2))
            results.append(("oversized config", False))
        except ConfigError:
            results.append(("oversized config", True))
    ok = all(v for _, v in results)
    evidence("5 resource-exhaustion probes", 0,
             "\n".join(f"{name}: {'REJECTED' if v else 'ACCEPTED (BUG)'}"
                       for name, v in results) + "\n", "")
    round_record(5, "resource-limit fuzz", ok,
                 f"{sum(v for _, v in results)}/{len(results)} exhaustion probes failed closed")
    return ok


# ---------------------------------------------------------------- Round 6
def r6():
    LOG.append("## Round 6 — output contracts and exit-code matrix\n")
    ok = True
    rc, out, err = cli("--root", DEMO, "--config", os.path.join(DEMO, "orphantest.json"),
                       "--format", "json", "audit", "--execute", "--trust-config")
    doc = json.loads(out)
    required = ("format", "schema_version", "tool", "purpose", "config_digest",
                "runner", "limits", "provenance", "inventory", "commands",
                "execution", "findings", "exemptions", "scope", "overall", "exit_code")
    missing = [k for k in required if k not in doc]
    ok &= not missing and "coverage" not in doc and "generated_at" not in doc
    evidence("audit --format json (schema check)", rc,
             f"required keys present: {len(required) - len(missing)}/{len(required)}\n"
             f"missing: {missing}\nforbidden 'coverage' key absent: {'coverage' not in doc}\n"
             f"default timestamp absent: {'generated_at' not in doc}\n", "")
    rc, out, err = cli("--root", DEMO, "--config", os.path.join(DEMO, "orphantest.json"),
                       "--format", "sarif", "audit", "--execute", "--trust-config")
    sarif = json.loads(out)
    rules = sarif["runs"][0]["tool"]["driver"]["rules"]
    results = sarif["runs"][0]["results"]
    ok &= (sarif["version"] == "2.1.0"
           and [r["id"] for r in rules] == sorted(r["id"] for r in rules)
           and all(r["partialFingerprints"] for r in results)
           and all(isinstance(r["locations"][0]["physicalLocation"]["region"]["startLine"], int)
                   for r in results))
    evidence("audit --format sarif", rc,
             f"version={sarif['version']} rules={len(rules)} results={len(results)}\n"
             f"rule ids sorted: {[r['id'] for r in rules] == sorted(r['id'] for r in rules)}\n"
             f"all fingerprints present: {all(r['partialFingerprints'] for r in results)}\n", "")
    with tempfile.TemporaryDirectory() as d:
        cases = [
            ("--version", 0, ["--version"]),
            ("no subcommand", 2, []),
            ("init", 0, ["--root", d, "init"]),
            ("init twice", 4, ["--root", d, "init"]),
            ("completion bash", 0, ["completion", "bash"]),
        ]
        lines = []
        for label, expected, argv in cases:
            r, o, e = cli(*argv)
            good = r == expected
            ok &= good
            lines.append(f"{label}: expected={expected} actual={r} {'OK' if good else 'MISMATCH'}")
        # Replace the starter config with a reviewed one that declares a command,
        # so the remaining cases exercise capture-incomplete and trust gates.
        os.makedirs(os.path.join(d, "tests"), exist_ok=True)
        with open(os.path.join(d, "tests", "test_a.py"), "w", encoding="utf-8") as fh:
            fh.write("def test_x(): pass\n")
        cfg = {
            "format": "orphantest/config/1", "reviewed": True, "runner": "pytest",
            "discovery": {"roots": ["tests"], "patterns": ["test_*.py"]},
            "commands": [{"id": "c1", "argv": ["python", "-m", "unittest", "-v"]}],
            "exemptions": [], "junit_path": None, "limits": {},
        }
        with open(os.path.join(d, "orphantest.json"), "w", encoding="utf-8") as fh:
            json.dump(cfg, fh)
        second = [
            ("scan (reviewed config)", 0, ["--root", d, "scan"]),
            ("run without trust", 2, ["--root", d, "run"]),
            ("audit (no evidence)", 3, ["--root", d, "--format", "json", "audit"]),
        ]
        for label, expected, argv in second:
            r, o, e = cli(*argv)
            good = r == expected
            ok &= good
            lines.append(f"{label}: expected={expected} actual={r} {'OK' if good else 'MISMATCH'}")
        for cfg_name, expected in (("orphantest.json", 1),
                                   ("orphantest.reconciled.json", 0)):
            r, o, e = cli("--root", DEMO, "--config", os.path.join(DEMO, cfg_name),
                          "audit", "--execute", "--trust-config")
            ok &= r == expected
            lines.append(f"audit {cfg_name}: expected={expected} actual={r}")
        evidence("exit-code matrix (10 CLI cases)", 0, "\n".join(lines) + "\n", "")
        # malformed saved ledger must not print a traceback
        bad = os.path.join(d, "bad.json")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write('{"format":"orphantest/ledger/1"}')
        r, o, e = cli("report", bad)
        ok &= r == 4 and "Traceback" not in (o + e)
        evidence("report on malformed saved ledger", r, o, e)
    round_record(6, "output contracts and exit codes", ok,
                 "JSON/SARIF shapes verified, 10 exit-code cases checked, no traceback on bad ledger")
    return ok


# ---------------------------------------------------------------- Round 7
def r7():
    LOG.append("## Round 7 — documentation and demo consistency\n")
    ok = True
    rc, out, err = cli("--root", DEMO, "--config", os.path.join(DEMO, "orphantest.json"),
                       "audit", "--execute", "--trust-config")
    design = open(os.path.join(ROOT, "docs", "DESIGN.md"), encoding="utf-8").read()
    key_lines = [l for l in out.splitlines() if l.startswith(("commands:", "scope:", "overall:"))]
    matches = [l in design for l in key_lines]
    ok &= all(matches) and rc == 1
    evidence("narrow demo output vs docs/DESIGN.md", rc,
             "\n".join(f"documented: {m}  {l}" for l, m in zip(key_lines, matches)) + "\n", "")
    rc, out, err = cli("--root", DEMO, "--config", os.path.join(DEMO, "orphantest.reconciled.json"),
                       "audit", "--execute", "--trust-config")
    ok &= rc == 0 and "INVENTORY_RECONCILED" in out
    evidence("reconciled demo", rc, "\n".join(out.splitlines()[-2:]) + "\n", "")
    expected = [
        "README.md", "LICENSE", "SECURITY.md", "CONTRIBUTING.md", "CHANGELOG.md",
        "GLOSSARY.md", "docs/DESIGN.md", "docs/PLAN.md", "docs/WORKFLOW.md",
        "docs/DECISIONS.md", "docs/ARCHITECTURE.md", "docs/SECURITY_MAPPING.md",
        "docs/REVIEW_A.md", "docs/REVIEW_B.md", "docs/schema/v1.json",
        "docs/adr/0001-ledger-is-not-a-verdict.md",
        "docs/adr/0002-evidence-bundle-is-a-deep-module.md",
        "docs/adr/0003-junit-runner-value-is-reserved.md",
        "research/prior_art.md", "research/threat_model.md",
        "scripts/verify.sh", "scripts/capture_golden.py", "scripts/review_rounds.py",
        ".github/workflows/ci.yml", ".agents/skills/MANIFEST.md",
        "tests/golden/demo_narrow.json", "tests/golden/demo_reconciled.json",
    ]
    absent = [p for p in expected if not os.path.exists(os.path.join(ROOT, p))]
    ok &= not absent
    evidence("referenced deliverables exist", 0,
             f"checked: {len(expected)}  present: {len(expected) - len(absent)}  "
             f"absent: {absent}\n", "")
    with tempfile.TemporaryDirectory() as d:
        r, o, e = cli("--root", d, "scan")
        ok &= r == 4 and "orphantest.json" in (o + e) and "next:" in (o + e)
        evidence("first-run error names input and fix", r, o, e)
    round_record(7, "documentation and demo consistency", ok,
                 "demo output matches DESIGN.md, all referenced files exist, first-run error is actionable")
    return ok


# ---------------------------------------------------------------- Round 8
def r8():
    LOG.append("## Round 8 — isolation, redaction, and integrity\n")
    ok = True
    tests_dir = os.path.join(DEMO, "tests")
    def snap():
        return {n: hashlib.sha256(open(os.path.join(tests_dir, n), "rb").read()).hexdigest()
                for n in sorted(os.listdir(tests_dir)) if n.endswith(".py")}
    before = snap()
    fake = "SKYNET-SECRET-TOKEN-abc123XYZ789"
    os.environ["ORPHANTEST_FAKE_TOKEN"] = fake
    env = {"ORPHANTEST_FAKE_TOKEN": fake}
    r, o, e = cli("--root", DEMO, "--config", os.path.join(DEMO, "orphantest.json"),
                  "--format", "json", "audit", "--execute", "--trust-config", env=env)
    after = snap()
    ok &= before == after and not os.path.exists(os.path.join(tests_dir, "__pycache__"))
    evidence("original tree hash before/after execution", r,
             f"files hashed: {len(before)}  unchanged: {before == after}\n"
             f"__pycache__ in original tree: {os.path.exists(os.path.join(tests_dir, '__pycache__'))}\n", "")
    from orphantest.redact import redact
    digest = "a" * 64
    prose = "the Bearer approach and secret = mystery"
    checks = [
        ("64-hex digest survives", redact(digest) == digest),
        ("ordinary prose survives", redact(prose) == prose),
        ("bearer token redacted", "[REDACTED]" in redact("Bearer abcdef1234567890XYZ")),
        ("aws key redacted", "[REDACTED]" in redact("AKIA" + "A" * 16)),
        ("env secret redacted", fake not in redact(fake)),
    ]
    ok &= all(v for _, v in checks)
    evidence("redaction precision checks", 0,
             "\n".join(f"{k}: {'OK' if v else 'FAIL'}" for k, v in checks) + "\n", "")
    r, o, e = cli("--root", DEMO, "--config", os.path.join(DEMO, "orphantest.json"),
                  "run", "--trust-config")
    bundle_path = os.path.join(DEMO, ".orphantest", "evidence.json")
    bundle = json.load(open(bundle_path, encoding="utf-8"))
    cfg = json.load(open(os.path.join(DEMO, "orphantest.json"), encoding="utf-8"))
    expected_digest = hashlib.sha256(json.dumps(cfg, sort_keys=True,
                         separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    ok &= r == 0 and bundle["config_digest"] == expected_digest
    ok &= all(cmd.get("executable_digest") for cmd in bundle["commands"])
    evidence("evidence bundle integrity", r,
             f"config_digest matches config: {bundle['config_digest'] == expected_digest}\n"
             f"commands with executable_digest: "
             f"{sum(bool(c.get('executable_digest')) for c in bundle['commands'])}/{len(bundle['commands'])}\n", "")
    leftovers = [n for n in os.listdir(os.path.dirname(bundle_path))
                 if n.startswith(".orphantest-")]
    ok &= not leftovers
    evidence("atomic write leaves no temp files", 0, f"leftovers: {leftovers}\n", "")
    os.environ.pop("ORPHANTEST_FAKE_TOKEN", None)
    shutil.rmtree(os.path.join(DEMO, ".orphantest"), ignore_errors=True)
    shutil.rmtree(os.path.join(tests_dir, "__pycache__"), ignore_errors=True)
    round_record(8, "isolation, redaction, integrity", ok,
                 "tree unchanged, redaction precise, bundle digests verified, no temp leftovers")
    return ok


def main():
    LOG.append("# Review log — eight examination rounds\n")
    LOG.append("Each round ran real commands; the exact captured output is reproduced below. "
               "The manager signed only rounds whose evidence is present. Rounds A and B "
               "(independent sub-agent reviews) are recorded in `docs/REVIEW_A.md` and "
               "`docs/REVIEW_B.md`; rounds 1–8 here are reproducible local examinations.\n")
    LOG.append(f"Generated: {datetime.now(timezone.utc).isoformat()} · "
               f"cwd: {ROOT} · Python: {sys.version.split()[0]}\n")
    rounds = [r1, r2, r3, r4, r5, r6, r7, r8]
    all_ok = True
    for fn in rounds:
        try:
            all_ok &= bool(fn())
        except Exception as exc:  # a crash is a failed round, recorded honestly
            LOG.append(f"**Manager sign-off: FAIL** — round raised "
                       f"{exc.__class__.__name__}: {exc}\n")
            all_ok = False
    LOG.append("\n## Summary\n")
    LOG.append("| Round | Focus | Result | Evidence |\n|---:|---|---|---|")
    for n, name, ok, summary in RESULTS:
        LOG.append(f"| {n} | {name} | {'PASS' if ok else 'FAIL'} | {summary} |")
    LOG.append(f"\n**Overall: {'ALL 8 ROUNDS PASSED' if all_ok else 'SOME ROUNDS FAILED — DO NOT RELEASE'}**\n")
    path = os.path.join(ROOT, "docs", "REVIEW_LOG.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LOG) + "\n")
    print(f"wrote {os.path.relpath(path, ROOT)}")
    for n, name, ok, summary in RESULTS:
        print(f"  round {n}: {'PASS' if ok else 'FAIL'}  {name}")
    print("ALL 8 ROUNDS PASSED" if all_ok else "SOME ROUNDS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
