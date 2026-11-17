# ADR 0002 — The evidence bundle is one deep module, not CLI helpers

- Status: Accepted
- Date: 2026-11-11
- Decider: manager, after independent architecture review and grilling

## Context

`cli.py` had grown three private helpers: `_bundle_to_dict`, `_validate_bundle`, and
`_ledger_from_bundle`. They were near-mirror-image serializers plus a hand-rolled
schema check. To answer "what fields does a persisted bundle have?", a reader had to
open the CLI, the store, and the runner. That is a locality failure: the format's
knowledge was spread across three modules while its interface lived in none of them.

The deletion test: deleting those helpers would not remove complexity; it would push
schema knowledge back into `cmd_run` and `cmd_audit`. So the helpers were earning
their keep, but in the wrong module.

## Decision

Create `orphantest/bundle.py`. It owns the evidence format, its field set, its
validation, its redaction-safe serialization, and reconstruction of `CommandEvidence`
and `Observation`. Its interface is small:

- `write_bundle(path, evidences, meta, contract, inventory)` — producer side.
- `load_bundle(path, contract) -> BundleData` — consumer side; loads, validates, and
  reconstructs in one call.
- `validate_bundle(bundle, contract)` — the test surface for the format.
- `Inventory` and `BundleData` — the two values that cross the seam.

`cli.py` becomes an adapter: it parses arguments, opens a root fd, obtains an
`Inventory`, and calls the bundle module or the ledger core. The shallow wrapper
`_ledger_from_bundle` was deleted rather than moved.

## Why the seam is real

Two adapters cross the evidence-source seam: inline execution (`audit --execute`)
and a persisted bundle (`audit` reading `.orphantest/evidence.json`). Both must
produce the same ledger. Validation therefore belongs to the module, not to either
caller. One adapter would have been hypothetical indirection; two make it real.

## Verification of zero function change

Before the refactor, three raw artifacts were captured to a scratch directory:

```
narrow.json       sha256 7003da6d0f3438dbd5db31879d68a3331266e33293d786e2d72fe26f937d31b0
reconciled.json   sha256 9173836515002af27a224446cbbce5eb5d66b6c877c617cbbc9e687ce63e8860
evidence.json     sha256 bc83a3ecea0dc74dcf820ee0a55f5820028fa3ecc3a4f26ac3d2f5ac0e35cd49
```

After the refactor, the exact same commands produced byte-identical files (`cmp`),
including key order and whitespace. No finding, exit code, error text, digest, or
status string changed. The full suite passed with 100 tests before and 113 tests
after: the 13 new tests target the module's interface, not its internals.

## Consequences

- Adding a bundle field now means editing one module and one validator.
- Tests cross the same seam callers cross (`tests/test_bundle.py`).
- The CLI no longer contains a second copy of the format definition.
- The `junit` runner value remains reserved (ADR 0003); it was deliberately not
  touched by this refactor because that would change observable config behavior.
