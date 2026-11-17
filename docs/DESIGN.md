# Design: orphantest

Date: 2026-11-11. Status: approved by delegation. The user asked for the work to run
end to end without a question round, so the brainstorming approval gate is satisfied by
that instruction. Every open design choice below is recorded as a manager call.

## Intent

AI coding agents now write tests. Teams trust a green CI run. A green run says nothing
about tests the runner never collected, tests the declared command excluded, or tests
that exist on disk but no command reaches. That gap is silent, and it ships bugs.

`orphantest` builds an execution ledger. It reconciles three inventories and reports the
discrepancy:

1. test files present in the repository,
2. test nodes discovered by static analysis of those files,
3. test nodes observed as executed when the repository's own declared commands run.

It does not claim a test is dead, useless, redundant, or safe to delete. It reports an
execution-inventory discrepancy under specified commands. That is the whole claim.

## Why this function

Five research agents checked the field. Two concepts were killed by collisions:

- `showwork` v0.6.5 on PyPI already records agent claims and runs deterministic checks
  with a hash-chained receipt and a CI gate. Any "declare criteria, run checks, report
  pass/fail" product is a clone. Killed.
- keel's `revert-check`, `mustfail`, and FixProof already revert a real diff in a scratch
  worktree and rerun declared checks. A "revert the change and see if tests fail" product
  is a clone. Killed.
- `testguard`, TestSeal, and the `nitpicker tests` skill already detect assertion-free,
  swallowed, skipped, and weakened tests. A "tests that cannot fail" static scanner is
  crowded. Demoted to out of scope.

The white-space audit found the missing integrated layer: reconciliation across
discovery, declared commands, and observed execution. `pytest --collect-only` shows what
one runner would collect. coverage.py shows executed lines. CI linters check workflow
syntax. None binds test-file inventory, declared commands, and observed execution into one
deterministic ledger with `NOT_RECONCILED` and exemption evidence.

## Approaches considered

| Approach | What it does | Why not |
|---|---|---|
| A. Acceptance-contract verifier | Declare checks, run them, gate on results | `showwork` already ships this. Rejected. |
| B. Diff-revert sensitivity | Revert each changed hunk, rerun tests | keel, mustfail, FixProof already ship this. Rejected. |
| C. Agent provenance and recovery | Snapshot per agent turn, restore selectively | oops, agentckpt, agent-undo, Reasonix, ReCall already ship this. Rejected. |
| D. Execution-inventory reconciler | Reconcile files, discovered nodes, executed nodes | Chosen. Narrow, verifiable, unbuilt as an integrated CLI. |

Manager call: D. The user handed over implementation choices, so language, packaging, and
output formats are my calls and are recorded below.

## Goals

- One command produces a deterministic, machine-readable ledger from a clean checkout.
- No network, no credentials, no LLM, no daemon, no shell, no third-party runtime deps.
- The original working tree is never modified. Execution happens in a copied tree.
- Findings name a specific file, a specific command, and specific evidence.
- Output is honest about what it did not observe.

## Non-goals

- Judging test quality, correctness, assertions, or behavioral coverage.
- Calling any test dead, unused, or safe to delete.
- Replacing CI, coverage.py, mutation testing, or code review.
- Ranking, scoring, or evaluating individual developers.
- Signing anything that could be presented as human approval.

## Anti-goals

- A `READY` / `PASS` / `GREEN` verdict about the repository. The grill found that a
  binary label turns a bounded inventory comparison into a false safety claim. Forbidden.
- Productivity telemetry. Default output contains no user name, host name, wall-clock
  timestamp, or stable machine identifier.
- A new signed attestation format.

## Constraints and honest limits

- Bounded novelty. A web and registry search on 2026-11-11 found no tool combining the
  four properties below. That is a bounded negative result, not proof of global novelty.
  The four properties: (P1) versioned operator-authored command config, (P2) static
  discovery of test nodes without importing target code, (P3) execution of declared
  commands in an isolated copy with captured structured evidence, (P4) three-way
  reconciliation with `NOT_RECONCILED` and exemption evidence, JSON and SARIF output.
- 105,000 GitHub stars is an aspiration, not a forecast. Research found 100k+ stars is a
  tail event (0.0004% of starred repositories in one 32.6M-repo snapshot) and that stars
  are a weak utility proxy. The plan optimizes for a 30-second reproducible result, not
  for a star count. No honest method can guarantee the number.
- The repository's own commands are the source of truth. A misconfigured command produces
  a false negative. The tool reports `COMMAND_FAILED` and `CAPTURE_INCOMPLETE` instead of
  inventing a result.
- Skipped tests may be platform-specific, quarantined, or manually run. Exemptions must
  carry a reason and are always reported.

## Vocabulary

- **Command**: an argv list from the trusted config. Never a shell string.
- **Test file**: a repository file matching the configured discovery grammar.
- **Node**: a test identity, `relative/path.py::Class::test_name`.
- **Ledger**: the deterministic reconciliation result.
- **Seam**: the boundary between a runner adapter and the reconciliation core.
- **Adapter**: a runner-specific discovery or execution-evidence parser.

## Output states

Overall states describe the ledger, not the repository:

- `INVENTORY_RECONCILED` - every discovered node has an observed execution record or a
  declared exemption, and capture is complete.
- `DISCREPANCY_REPORTED` - at least one `NOT_DISCOVERED`, `DISCOVERED_NOT_EXECUTED`, or
  `NOT_RECONCILED` finding exists.
- `CAPTURE_INCOMPLETE` - a command failed, timed out, was skipped, or produced no
  parsable evidence.
- `NO_COMMANDS_DECLARED` - the config has no commands. Never treated as a clean result.
- `CONFIG_NOT_REVIEWED` - the config lacks a reviewed marker.

Per-node states: `EXECUTED`, `DISCOVERED_NOT_EXECUTED`, `NOT_DISCOVERED`,
`NOT_RECONCILED`, `EXEMPT`, `COLLECTION_ERROR`, `COMMAND_FAILED`.

## Output formats

Human table, deterministic JSON (sorted keys, no timestamps by default), SARIF 2.1.0 with
`partialFingerprints`. Exit codes: 0 no discrepancy, 1 discrepancy, 2 usage/input error,
3 internal failure, 4 config error.

## The 30-second demo

The checked-in fixture has four test files and one declared command. That command
targets only `test_math.py`, so four discovered nodes in `test_billing.py` and
`test_exports.py` never appear in execution evidence. A fourth file sits outside the
discovery grammar. This output was captured from the checked-in fixture, not invented.

```
$ python3 -m orphantest --root examples/demo_repo \
    --config examples/demo_repo/orphantest.json \
    audit --execute --trust-config
orphantest 1.0.0  ledger v1
commands: 1   files: 4   discovered nodes: 6   observed records: 2
DISCOVERED_NOT_EXECUTED    tests/test_billing.py::TestBilling::test_invoice_total
DISCOVERED_NOT_EXECUTED    tests/test_billing.py::TestBilling::test_tax_rounding
DISCOVERED_NOT_EXECUTED    tests/test_exports.py::TestExports::test_csv_header
DISCOVERED_NOT_EXECUTED    tests/test_exports.py::TestExports::test_row_count
NOT_DISCOVERED             tests/legacy_test_tax.py
scope: execution-inventory discrepancy under declared commands
overall: DISCREPANCY_REPORTED (ledger state only; not a code-correctness verdict)   exit=1
```

Swap the config to `orphantest.reconciled.json`, which widens the command and records a
reasoned exemption for the legacy file:

```
$ python3 -m orphantest --root examples/demo_repo \
    --config examples/demo_repo/orphantest.reconciled.json \
    audit --execute --trust-config
orphantest 1.0.0  ledger v1
commands: 1   files: 4   discovered nodes: 6   observed records: 6
noted: 1 (exemptions and skipped observations are always reported; review them)
scope: execution-inventory discrepancy under declared commands
overall: INVENTORY_RECONCILED (ledger state only; not a code-correctness verdict)   exit=0
```

Same repository, different declared command, different ledger. That is the honest wow:
the gap was in the wiring, not in the code. Exit code 0 describes the ledger, never the
repository.

## What is left to the builder

Exact schema, adapter set, resource limits, error text, and CI matrix. All are fixed in
`docs/PLAN.md` and `docs/schema/v1.json`.
