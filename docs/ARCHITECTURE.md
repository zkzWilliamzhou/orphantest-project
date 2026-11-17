# Architecture deepening (round 17 of the plan)

This document records the application of the vendored
`mattpocock/improve-codebase-architecture` skill, using the vocabulary of
`mattpocock/codebase-design` (**module, interface, depth, seam, adapter, leverage,
locality**) and the deletion test. Domain terms come from `GLOSSARY.md`.

The user's hard constraint was: **first make sure you didn't change any function of
the program's function**. That is why the proof below is a byte comparison, not a
test-suite pass alone.

## 1. Explore — scope before scan

No commit history existed, so YAGNI scoped the scan to the recently changed hot spot:
`cli.py`, `store.py`, `report.py`, `audit.py`, and `runner.py`. `docs/adr/` was empty
at scan time, so no ADR conflict existed; three ADRs were created as a result.

An independent sub-agent walked the package and reported three deepening candidates.
The manager graded them against the constraint.

| # | Candidate | Strength (agent) | Manager decision |
|---:|---|---|---|
| A | Extract a `Capture` ABC with `PytestCapture` / `UnittestCapture` / `JunitCapture`, move `junit_path` into the adapter, delete `adapters.py` | Strong | **Rejected for 1.0.0.** It changes the config-to-capture contract, moves path resolution, and risks `obs.source` strings, which appear in findings. Too large for a zero-function-change release. |
| B | Extract a deep evidence **module** from `cli.py` | Worth exploring | **Accepted as the minimum safe diff.** Two real adapters cross the seam; the deletion test passes; no behavior change. |
| C | Unify `classify` and the `junit_path` discovery branch | Speculative | **Rejected.** It changes node-source semantics and would break the byte-identical ledger gate. |

Candidate B was chosen. It is the smallest diff that still produces a deeper module.

## 2. Candidates HTML report

A self-contained visual report with before/after diagrams for all three candidates
was written outside the repository, as the skill requires. In the release zip it
sits next to the repository folder:

```
architecture-review-20261111.html   (zip root, sibling of orphantest/)
```

It uses Tailwind and Mermaid via CDN, one card per candidate with files, problem,
solution, benefits, before/after diagrams, and a recommendation-strength badge, and
ends with the top recommendation. Nothing from the exploration landed in the repo;
the HTML is a review artifact, not a program input.

## 3. Grilling (delegated decisions, recorded)

The grill worked a design tree in two rounds. Frontier questions and answers:

**Round 1**

1. *What is the risk to the byte-for-byte deterministic JSON ledger?* None for a
   pure extract: `canonical_json` uses sorted keys, findings are sorted in
   `audit.py`, nodes are sorted in `discover.py`. None of these live in `cli.py`.
   Mitigation: capture raw ledgers before the diff and `cmp` after.
2. *Does the refactor change any output, exit code, error text, or error code?* No,
   provided all `ConfigError` messages, `EVIDENCE_UNUSABLE:<kind>` strings, and
   digests are preserved verbatim. Verified by the byte comparison.
3. *Is there a real seam with two adapters, or hypothetical indirection?* Real:
   inline execution and a persisted bundle are two adapters. One adapter would not
   justify the module.
4. *Which tests cross the seam and survive?* `test_run_then_audit_from_bundle`,
   `test_stale_config_digest_is_rejected`, `test_deterministic_json`,
   `test_32_malformed_bundle_observation_fails_closed`. All survived unchanged.
5. *What is the minimum diff?* Move three helpers, delete one shallow wrapper,
   introduce two value types, keep every call site's behavior.
6. *What would make you reject it?* Any change to field names, redaction, error
   kinds, or the ledger's `format` / `schema_version`.

**Round 2**

7. *Should `reconcile_observations` move too?* No. It belongs to the ledger core;
   moving it adds risk with no locality gain for this diff.
8. *Should `Observation` move out of `adapters.py`?* No. Six construction sites and
   the `source` strings are load-bearing; a rename would be a hidden behavior change.
9. *Should `junit_path` move into an adapter?* No. Recorded in ADR 0003 instead.
10. *Should the CLI keep a `ledger_from_bundle` wrapper?* No — deletion test says it
    is a pass-through; `load_bundle` returns `BundleData` and `cmd_audit` calls
    `build_ledger` directly.
11. *Does `Inventory` need to be frozen?* Yes; it is shared by scan, run, and audit.
12. *Is a Protocol needed?* No. One adapter means a hypothetical seam; here the seam
    already has two concrete callers. Adding a Protocol would be indirection.

## 4. The change

**Before** — `cli.py` was 356 lines and owned the evidence format:

```
cli.py  ── _bundle_to_dict ── serialize_bundle ── atomic_write
        ── load_json_file ── _validate_bundle ── _ledger_from_bundle ── build_ledger
```

**After** — `cli.py` is an adapter; `bundle.py` is a deep module:

```
cli.py ── write_bundle(...) ──┐
                              ├──> bundle.py  (format, validation, redaction,
cli.py ── load_bundle(...)  ──┘                reconstruction, Inventory, BundleData)
                                     │
                                     └──> audit.build_ledger(...)
```

- **Module**: `orphantest/bundle.py`.
- **Interface**: `write_bundle`, `load_bundle`, `validate_bundle`, plus the `Inventory`
  and `BundleData` values. Callers no longer know any field name of the format.
- **Depth**: schema knowledge, strict validation, symlink-resistant loading, and
  type reconstruction sit behind four names instead of three scattered helpers.
- **Seam**: the evidence source. Two **adapters** cross it (inline execution and the
  persisted bundle).
- **Leverage**: producer and consumer both use one format definition; a new field is
  one edit in one module.
- **Locality**: `validate_bundle` is the single place where the bundle's invariants
  are checked before anything is indexed.
- **Deletion test**: delete `bundle.py` and the complexity reappears in `cmd_run`
  and `cmd_audit`. The module earns its keep.
- **Interface is the test surface**: `tests/test_bundle.py` (13 tests) crosses the
  same seam callers cross, including round-trip, stale digest, symlink, deep JSON,
  pickle payload, malformed observation, and executable digest preservation.

## 5. Zero-function-change proof

Captured **before** the refactor (scratch directory, not shipped):

```
narrow.json       sha256 7003da6d0f3438dbd5db31879d68a3331266e33293d786e2d72fe26f937d31b0
reconciled.json   sha256 9173836515002af27a224446cbbce5eb5d66b6c877c617cbbc9e687ce63e8860
evidence.json     sha256 bc83a3ecea0dc74dcf820ee0a55f5820028fa3ecc3a4f26ac3d2f5ac0e35cd49
```

Commands run after the refactor:

```
python3 -m orphantest --root examples/demo_repo \
  --config examples/demo_repo/orphantest.json --format json \
  --out /data/workspace/baseline/narrow_after.json audit --execute --trust-config
python3 -m orphantest --root examples/demo_repo \
  --config examples/demo_repo/orphantest.reconciled.json --format json \
  --out /data/workspace/baseline/reconciled_after.json audit --execute --trust-config
python3 -m orphantest --root examples/demo_repo \
  --config examples/demo_repo/orphantest.json run --trust-config
```

Result of `cmp`:

```
NARROW BYTE-IDENTICAL
RECONCILED BYTE-IDENTICAL
BUNDLE BYTE-IDENTICAL
```

This is stronger than JSON equality: it catches key order, whitespace, redaction,
digest strings, and every error field. Two independent runs before the refactor were
also byte-identical, so determinism was not introduced by the change.

Full suite:

```
Before: Ran 100 tests ... OK
After:  Ran 113 tests ... OK
```

The 13 extra tests are new interface tests; no existing test was modified or
deleted. Exit codes were rechecked: narrow demo 1, reconciled demo 0.

## 6. Rejected findings from the independent review

The manager did not accept every agent finding:

- "Extract a `Capture` ABC" — real architecture value, but violates the
  zero-function-change constraint for this release. Deferred.
- "`max_output_bytes` is uncapped" — **false positive**. `limits.py` defines
  `_INT_KEYS = tuple(DEFAULTS)`, and `from_config` caps every key with
  `min(value, DEFAULTS[key])`; `max_output_bytes` is in `DEFAULTS`. Verified by
  reading the code, not by accepting the report.
- "`scan_tree` bypasses the file count limit with directories" — **false positive**.
  `len(entries) + budget.files > limits.max_files` over-counts directory entries;
  it fails closed earlier than necessary, which is safe.
- "Any absolute executable under `--trust-config` is an RCE primitive" — true by
  design, not a bug. Mitigated by requiring explicit trust, recording
  `executable_digest` in the bundle, and documenting it in `SECURITY.md`.

## 7. What did not change

No config key, no output field, no finding kind, no exit code, no error message, no
redaction rule, no discovery pattern, no timeout, and no status string changed. The
`scope` key, SARIF line numbers, and the `executable_digest` field predate this
round; they were part of the earlier review fixes, not the architecture diff.
