# ADR 0003 — `"junit"` is a reserved runner value, not a dispatch branch

- Status: Accepted
- Date: 2026-11-11
- Decider: manager

## Context

`contract.RUNNERS = ("unittest", "pytest", "junit")` accepts `"junit"` as a config
value, but `runner.py` dispatches only on `"pytest"` and `"unittest"`. JUnit XML is
reached today through the optional `junit_path` file, which is runner-agnostic. An
independent architecture review flagged this as an inconsistency and suggested
either implementing `JunitCapture` or removing the value.

## Decision

Leave it as-is for the 1.0.0 release. Record the inconsistency here instead of
silently fixing it.

Reason: the user's constraint for this release is **zero function change**. Removing
`"junit"` from `RUNNERS` would change config validation and therefore observable
behavior; adding `JunitCapture` would change capture semantics. Both are separate
changes with their own tests and their own golden-ledger comparison.

## Consequences

- A config with `"runner": "junit"` and no `junit_path` still produces no stdout
  observations. The ledger reports `CAPTURE_INCOMPLETE` or discrepancies rather than
  inventing a result. This is fail-closed, but it is not obvious from the config
  schema alone.
- `docs/schema/v1.json` documents the runner enum with this note.
- A future release that adds `JunitCapture` must reopen this ADR and prove the golden
  ledgers remain byte-identical for the existing two runners.
