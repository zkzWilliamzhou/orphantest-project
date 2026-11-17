# Prior art notes

Verified during concept selection on 2026-11-11. URLs were opened; claims below are
limited to what those pages actually say. This file exists so a future contributor
does not have to re-litigate the collision check from memory.

| Existing work | What it does (per its own page) | Why it is not this tool |
|---|---|---|
| `showwork` — https://pypi.org/project/showwork/0.6.5 | "Falsifiable claims and deterministic verification for AI agents." Records an agent's claims, runs declared checks, refuses a clean close when checks fail, keeps a hash-chained receipt. | It verifies an agent's declared claims against declared checks. It does not reconcile the repository's file inventory with statically discovered test nodes and observed execution identities. |
| `keel` revert-check — https://keel-ship.dev/revert-check.html | Diffs a branch, checks out a scratch worktree, reverts one production change at a time, and requires a test to fail as an assertion. | It asks "would a test fail if this fix were undone?" It does not ask "which test files never ran at all?" |
| `test-guard` — https://www.npmjs.com/package/test-guard | Blocks agents from deleting, skipping, or weakening tests; rules TG001+ detect removed test files, fewer cases, weakened assertions. Node 20+, git, no network. | It detects **changes that weaken** a suite relative to a baseline. A test that was never wired into any command from the start is not a weakening. |
| `TestSeal` — https://kaiyuanbang.cn/zh-cn/repo/satwiksps-testseal.html | Python/pytest test-integrity scanner with workspace, staged, branch-diff and patch modes; text, JSON, SARIF output; advisory by default. | Same category as test-guard: it inspects test changes for relaxed constraints, not the three-inventory relation. |
| `Skylos done` — https://blog.gitcode.com/dbcf09d9a3bce5f3a2ba0153382dd254.html | Tree-sitter inventory of tests on base and head, detects deleted/skipped/weakened tests and special-cased code, emits a receipt. | It compares two revisions. It does not bind declared commands to observed execution across the whole existing tree. |

## Adjacent tools, not collisions

- `pytest --collect-only`: reports what **one runner** would collect. It does not
  bind the file inventory to a separate declared command set.
- `coverage.py`: reports executed lines. It is a different question; the tool
  deliberately does not use the word `coverage` for its own output field.
- Mutation testing: judges assertion strength. Out of scope here.

## Consequence

The defensible narrow claim is a **deterministic execution-inventory discrepancy
report under declared commands**, not "verify AI-written tests" and not "prove the
suite is good". See `docs/DECISIONS.md` D2–D3 and ADR 0001.

## Honesty note

Two earlier draft reports were rejected: one contained wrong weighted scores and
placeholder `github.com/example/...` citations; another contained an unverifiable
repository owner and star figures. Neither was used. Unverified product names were
removed from the README rather than repeated here.
