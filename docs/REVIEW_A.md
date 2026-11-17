# Independent code review A — correctness and security

Reviewer: independent sub-agent with fresh context, read-only. Round A of the review
log. The manager verified each finding against the source and recorded a disposition.
Rejected findings are kept here rather than silently dropped.

Baseline at review time: `python3 -m orphantest --self-test` → `Ran 100 tests ... OK`.

## Accepted and fixed

| # | Finding | Severity (reviewer) | Manager disposition |
|---:|---|---|---|
| 1 | `report.render_human` / `render_sarif` index ledger dicts directly; a hand-built or malformed saved ledger prints a raw `KeyError` traceback | Critical | **Fixed.** Added `report.validate_ledger`, called by `cmd_report` and by every renderer. Missing/mistyped fields now raise `CONFIG_ERROR` (exit 4). Also added strict `_validate_bundle` → now `bundle.validate_bundle`. |
| 4 | Redaction patterns were over-broad: `Bearer\s+[A-Za-z0-9._-]{8,}` redacted prose such as "the Bearer approach"; the `secret=...` rule redacted ordinary words | Important | **Fixed.** Token-like shape is now required (digit/`_`/`-`, or ≥20 chars). Added `_looks_secret` with an entropy-ish class test for env values; common short values are allowlisted. Digests (64 hex chars) are no longer destroyed. |
| 5 | Environment-value substitution could redact ordinary short strings | Important | **Fixed** as part of #4: lengths 12–512, at least 3 character classes, safe-value allowlist. |
| 7 | `copy_repository` `os.makedirs` is not atomic | Important (defense in depth) | **Accepted as documented risk, not changed.** The copy is built from an already-scanned tree that rejects symlinks; `O_EXCL` protects the final file. Changing it would alter capture semantics. |
| 9 | Dead logic in `_normalize_status` | Minor | **Not changed.** Harmless and behavior-preserving; removing it was outside the zero-function-change gate. |
| 11 | `cmd_report` returned exit 3 for a malformed ledger | Minor | **Fixed** by `validate_ledger` raising `ConfigError` → exit 4. |
| 12 | `os.replace` on Windows cannot replace an open file | Minor | **Documented** in `SECURITY.md`; Windows is not in CI. |

## Rejected (false positives, with evidence)

| # | Reviewer claim | Why the manager rejected it |
|---:|---|---|
| 3 | "`max_output_bytes` is not capped by `Limits.from_config`; a hostile config can allocate 8 exabytes" | **False.** `limits.py` has `_INT_KEYS = tuple(DEFAULTS)` and `max_output_bytes` is a key of `DEFAULTS`; `from_config` applies `min(value, DEFAULTS[key])` to every key. Verified by reading lines of `limits.py`, not by accepting the report. |
| 8 | "`scan_tree` skips directories before `budget.add_file`, so many empty directories bypass the file-count limit" | **False and safe.** `_walk_dir` checks `len(entries) + budget.files > limits.max_files` where `entries` includes directories. It over-counts and fails closed earlier, not later. |
| 6 | "Any absolute executable under `--trust-config` is effectively an RCE primitive" | **True by design, not a defect.** Mitigated by requiring explicit trust, an allowlisted environment, and by recording `executable_digest` in the bundle. Documented in `SECURITY.md` and `SECURITY_MAPPING.md`. |
| 2 | Config `unknown_keys` check is inconsistent for non-object `discovery` | **Not reproducible.** `load_contract` guards `isinstance(doc, dict)` and `_require(isinstance(disc, dict), ...)` before the key check. Fail-closed. |

## Category results

- Unhandled exceptions / raw tracebacks: 1 critical fixed, 1 minor fixed.
- Path containment / symlink / TOCTOU: no defect found; `O_NOFOLLOW` + one-fd reads throughout.
- Resource limit bypasses: none found (two claims rejected as false positives).
- Subprocess argv / option injection: no defect beyond the documented trust boundary.
- Secret leakage: two over-redaction defects fixed.
- Nondeterminism: no defect found (`sort_keys`, UTC opt-in, no env-derived values).
- Reconciliation logic: no defect found (exemptions, `NOT_RECONCILED`, empty commands, skipped observations all fail closed).

## Manager note

The reviewer's self-test count was 100 tests at that time. It is now 113 after the
architecture round added 13 tests at the new module's interface. No reviewer finding
was implemented without a source check first.
