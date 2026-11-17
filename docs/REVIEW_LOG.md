# Review log — eight examination rounds

Each round ran real commands; the exact captured output is reproduced below. The manager signed only rounds whose evidence is present. Rounds A and B (independent sub-agent reviews) are recorded in `docs/REVIEW_A.md` and `docs/REVIEW_B.md`; rounds 1–8 here are reproducible local examinations.

Generated: 2026-11-11T16:34:58.938519+00:00 · cwd: /data/workspace/orphantest · Python: 3.10.12

## Round 1 — build and full suite

```
$ python3 -m compileall -q orphantest

[exit=0]
```
```
$ python3 -m orphantest --self-test
.................................................................................................................
----------------------------------------------------------------------
Ran 113 tests in 16.141s

OK
[exit=0]
```
**Manager sign-off: PASS** — byte-compile rc=0; 113 tests, full output captured above

## Round 2 — deterministic bytes

```
$ 3x audit --format json --out <tmp> (orphantest.json)
7003da6d0f3438dbd5db31879d68a3331266e33293d786e2d72fe26f937d31b0
7003da6d0f3438dbd5db31879d68a3331266e33293d786e2d72fe26f937d31b0
7003da6d0f3438dbd5db31879d68a3331266e33293d786e2d72fe26f937d31b0
[exit=1]
```
```
$ 3x audit --format json --out <tmp> (orphantest.reconciled.json)
9173836515002af27a224446cbbce5eb5d66b6c877c617cbbc9e687ce63e8860
9173836515002af27a224446cbbce5eb5d66b6c877c617cbbc9e687ce63e8860
9173836515002af27a224446cbbce5eb5d66b6c877c617cbbc9e687ce63e8860
[exit=0]
```
```
$ run --trust-config (bundle sha256)
bc83a3ecea0dc74dcf820ee0a55f5820028fa3ecc3a4f26ac3d2f5ac0e35cd49
[exit=0]
```
```
$ normalized ledger == tests/golden/demo_narrow.json
match=True
[exit=1]
```
**Manager sign-off: PASS** — 3 identical runs per config, bundle captured, normalized ledger matches golden

## Round 3 — adversarial security suite and source prohibitions

```
$ python3 -m unittest discover -s tests -p test_security.py -v
test_21_safe_env_has_no_secrets (test_security.ExecutionAttackTests) ... ok
test_22_no_shell_in_source (test_security.ExecutionAttackTests) ... ok
test_23_no_pickle_or_eval_import (test_security.ExecutionAttackTests) ... ok
test_24_no_network_imports (test_security.ExecutionAttackTests) ... ok
test_25_git_gateway_rejects_option_like_path (test_security.ExecutionAttackTests) ... ok
test_26_config_rejects_unknown_include_key (test_security.ExecutionAttackTests) ... ok
test_27_config_rejects_absolute_junit_path (test_security.ExecutionAttackTests) ... ok
test_28_redaction_survives_nested_report (test_security.ExecutionAttackTests) ... ok
test_29_redaction_does_not_destroy_digests (test_security.ExecutionAttackTests) ... ok
test_30_error_output_hides_home_path (test_security.ExecutionAttackTests) ... ok
... (30 more lines)
[exit=0]
```
```
$ static scan of orphantest/*.py for 11 prohibited primitives
prohibited hits: 0
checked files: 16
[exit=0]
```
**Manager sign-off: PASS** — 35 adversarial tests, 0 prohibited primitives

## Round 4 — hostile path fuzz

```
$ validate_relative hostile corpus + valid corpus
hostile inputs: 45  rejected: 45
valid inputs: 3  accepted: 3
NFKC example: 'tests/ｔest.py' normalizes to 'tests/test.py' (unstable=True)
[exit=0]
```
**Manager sign-off: PASS** — 45/45 hostile paths rejected, 3/3 valid paths accepted

## Round 5 — resource-limit fuzz

```
$ 5 resource-exhaustion probes
deep tree: REJECTED
file count: REJECTED
4MB file vs 2MB cap: REJECTED
200-level JSON: REJECTED
oversized config: REJECTED
[exit=0]
```
**Manager sign-off: PASS** — 5/5 exhaustion probes failed closed

## Round 6 — output contracts and exit-code matrix

```
$ audit --format json (schema check)
required keys present: 16/16
missing: []
forbidden 'coverage' key absent: True
default timestamp absent: True
[exit=1]
```
```
$ audit --format sarif
version=2.1.0 rules=8 results=5
rule ids sorted: True
all fingerprints present: True
[exit=1]
```
```
$ exit-code matrix (10 CLI cases)
--version: expected=0 actual=0 OK
no subcommand: expected=2 actual=2 OK
init: expected=0 actual=0 OK
init twice: expected=4 actual=4 OK
completion bash: expected=0 actual=0 OK
scan (reviewed config): expected=0 actual=0 OK
run without trust: expected=2 actual=2 OK
audit (no evidence): expected=3 actual=3 OK
audit orphantest.json: expected=1 actual=1
audit orphantest.reconciled.json: expected=0 actual=0
[exit=0]
```
```
$ report on malformed saved ledger
CONFIG_ERROR: ledger is missing required fields
  input: schema_version, tool, purpose, config_digest, runner, limits, provenance, inventory, commands, execution, findings, exemptions, scope, overall, exit_code
  next: generate the ledger with `orphantest audit`
[exit=4]
```
**Manager sign-off: PASS** — JSON/SARIF shapes verified, 10 exit-code cases checked, no traceback on bad ledger

## Round 7 — documentation and demo consistency

```
$ narrow demo output vs docs/DESIGN.md
documented: True  commands: 1   files: 4   discovered nodes: 6   observed records: 2
documented: True  scope: execution-inventory discrepancy under declared commands
documented: True  overall: DISCREPANCY_REPORTED (ledger state only; not a code-correctness verdict)   exit=1
[exit=1]
```
```
$ reconciled demo
scope: execution-inventory discrepancy under declared commands
overall: INVENTORY_RECONCILED (ledger state only; not a code-correctness verdict)   exit=0
[exit=0]
```
```
$ referenced deliverables exist
checked: 27  present: 27  absent: []
[exit=0]
```
```
$ first-run error names input and fix
CONFIG_ERROR: cannot read config
  input: /tmp/tmp7b6dwtb5/orphantest.json
  next: run `orphantest init` first
[exit=4]
```
**Manager sign-off: PASS** — demo output matches DESIGN.md, all referenced files exist, first-run error is actionable

## Round 8 — isolation, redaction, and integrity

```
$ original tree hash before/after execution
files hashed: 4  unchanged: True
__pycache__ in original tree: False
[exit=1]
```
```
$ redaction precision checks
64-hex digest survives: OK
ordinary prose survives: OK
bearer token redacted: OK
aws key redacted: OK
env secret redacted: OK
[exit=0]
```
```
$ evidence bundle integrity
config_digest matches config: True
commands with executable_digest: 1/1
[exit=0]
```
```
$ atomic write leaves no temp files
leftovers: []
[exit=0]
```
**Manager sign-off: PASS** — tree unchanged, redaction precise, bundle digests verified, no temp leftovers


## Summary

| Round | Focus | Result | Evidence |
|---:|---|---|---|
| 1 | build and full suite | PASS | byte-compile rc=0; 113 tests, full output captured above |
| 2 | deterministic bytes | PASS | 3 identical runs per config, bundle captured, normalized ledger matches golden |
| 3 | security suite and prohibitions | PASS | 35 adversarial tests, 0 prohibited primitives |
| 4 | hostile path fuzz | PASS | 45/45 hostile paths rejected, 3/3 valid paths accepted |
| 5 | resource-limit fuzz | PASS | 5/5 exhaustion probes failed closed |
| 6 | output contracts and exit codes | PASS | JSON/SARIF shapes verified, 10 exit-code cases checked, no traceback on bad ledger |
| 7 | documentation and demo consistency | PASS | demo output matches DESIGN.md, all referenced files exist, first-run error is actionable |
| 8 | isolation, redaction, integrity | PASS | tree unchanged, redaction precise, bundle digests verified, no temp leftovers |

**Overall: ALL 8 ROUNDS PASSED**

