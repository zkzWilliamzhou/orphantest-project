# ADR 0001 — The ledger states an inventory relation, not a repository verdict

- Status: Accepted
- Date: 2026-11-11
- Decider: manager

## Context

The product exists because a green CI pipeline can coexist with test files that no
command ever runs. The easiest way to make the tool popular would be to print
`READY`, `PASS`, or `GREEN` when the three inventories reconcile. That would also be
the easiest way to make it a lie: a reconciled ledger says nothing about assertion
quality, correctness, behavioural coverage, or merge safety.

Existing tools already occupy adjacent spaces: `showwork` records agent claims and
runs declared checks; `keel` reverts a fix and asks whether a test fails; `test-guard`
and `TestSeal` detect deleted, skipped, or weakened tests; `Skylos` inventories and
compares test changes. None of them binds the file inventory, the declared commands,
and observed execution into one deterministic, read-only ledger.

## Decision

The overall state describes the ledger only. `INVENTORY_RECONCILED` with exit code 0
means: under the declared commands, every discovered node has an observed execution
record or a declared exemption, and capture completed. It never means the code is
correct.

Enforced in code:

- `audit.py` never emits `READY`, `GREEN`, `PASS`, or `SAFE` as an overall state.
- `report.py` appends `(ledger state only; not a code-correctness verdict)` to the
  human overall line.
- The JSON field is named `scope`, not `coverage`.
- `CAPTURE_INCOMPLETE` is never downgraded to a clean result.
- `NO_COMMANDS_DECLARED` is never treated as clean.
- Exemptions and skipped observations are always reported.

## Consequences

- The tool is less satisfying as a badge. That is the price of the honest claim.
- Downstream dashboards must read `scope.declared_subset_only` before presenting any
  number derived from the ledger.
- A future contributor who wants to add a "ready" state must reopen this ADR.
