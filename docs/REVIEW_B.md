# Independent code review B — product honesty, output contracts, docs

Reviewer: independent sub-agent with fresh context, read-only. Round B of the review
log. This round found the most user-visible defects: the docs described a demo that
did not exist, and the output used a word the product forbids.

## Accepted and fixed

| # | Finding | Severity | Fix |
|---:|---|---|---|
| B-01 | Human output line `coverage: ...` uses a term the design forbids | High | Renamed to `scope: ...`. |
| B-16 | JSON key `coverage` is misleading | Medium | Renamed to `scope`; integration test updated. |
| B-02 | `INVENTORY_RECONCILED` can be read as a code-correctness verdict | Medium | Human overall line now ends `(ledger state only; not a code-correctness verdict)`. |
| B-17 | The 30-second demo in `DESIGN.md` did not match reality: commands 2 vs 1, nodes 9 vs 6, "executed nodes" vs "observed records", free-function node IDs vs class methods, `orphantest.toml` vs `orphantest.json` | High | Demo rewritten from real captured output of both demo configs. `scripts/verify.sh` greps the exact documented line. |
| B-18 | `init` success message told the user to run `orphantest run` before adding commands | Medium | Now says: add commands, set `reviewed=true`, then run `orphantest audit --execute --trust-config`. |
| B-19 | No README | Medium | `README.md` written and checked against actual behavior. |
| B-25 | Error messages reference `docs/schema/v1.json`, which did not exist | Medium | Created `docs/schema/v1.json` with config, bundle, and ledger descriptions. |
| B-26 | `PLAN.md` step 14 references `scripts/verify.sh`, which did not exist | Low | Created `scripts/verify.sh` with nine gates; a tenth packaging gate was added in the final release pass. |
| B-28 | `PYTHONDWRITEBYTECODE` typo in `runner._safe_env` | Low | Removed; `PYTHONDONTWRITEBYTECODE` remains. |
| B-14 | SARIF rule order relies on dict insertion order | Medium | Rules explicitly sorted by rule id. |
| B-15 | SARIF `startLine` always 1; discovered line numbers ignored | Low | `_finding` now carries `line`, propagated from discovery; renderer uses it. |
| B-13 | Fingerprint did not include `observed_status` | Medium | Seed now includes `observed_status`; status changes produce a new fingerprint. |
| B-08/10/11/30 | `--config`, `--write-ledger`, `--include-time`, `--quiet` had no help text | Low | All flags documented; `--include-time` warns it breaks determinism. |
| B-21 | "non-blocking" wording downplays exemptions | Low | Changed to `noted: N (exemptions and skipped observations are always reported; review them)`. |
| B-07 | `init` writes a file despite "read-only by default" | Low | Help text now says it writes `orphantest.json` into the root. |

## Verified, no change needed

- B-05/B-06: exit-code matrix checked by running every command. `CAPTURE_INCOMPLETE`
  returning 3 is consistent with "internal / capture failure".
- B-09: `audit --execute` without `--trust-config` exits 2 with a clear message.
- B-22: `scope.declared_subset_only` is honest wording, kept.
- B-24: deterministic JSON verified; `--include-time` is opt-in.
- B-27: no `READY` / `GREEN` / `PASS` verdict vocabulary in code or output.

## Rejected

| # | Claim | Disposition |
|---:|---|---|
| B-11 | `cmd_report` returns `EXIT_INTERNAL` for a malformed ledger | **Moot after fix.** It now raises `ConfigError` → 4, which is the reviewer's own suggested taxonomy. |
| B-04 | `"executed"` status could be misread as "passed" | **Rejected.** The status means "the runner reported this node ran"; renaming it would change findings and goldens. Documented in `GLOSSARY.md` and README instead. |
| B-13 (partial) | Fingerprints are "unstable across runs" | **Rejected.** Only the identity fields are in the seed; two runs of the same repo produced byte-identical SARIF. The real gap was missing `observed_status`, which was fixed. |
| B-29 | PowerShell completion string is "non-Python code in a Python file" | **Rejected.** It is a printed string, by design. |

## Manager note

B-17 was the most important finding: a demo that does not match the shipped fixture
is a broken promise to the first user. Every code block in `README.md` and
`DESIGN.md` was re-run before signing this round.
