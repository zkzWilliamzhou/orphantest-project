# Contributing

## Ground rules

- Every claim needs evidence. Paste the exact command and its full output.
- Tests first. A change without a failing test that now passes is not done.
- No new runtime dependency. The shipped program is Python standard library only.
- No shell, no network, no credentials, no LLM in the shipped program.
- Never rename an output state to something that sounds like a repository verdict.
- Prose quality matters: no filler, no hype, no invented numbers.

## Before you open a PR

```bash
python3 -m orphantest --self-test
bash scripts/verify.sh
```

`scripts/verify.sh` checks compilation, the full suite, golden reproducibility, raw
byte determinism across three runs, demo exit codes, SARIF shape, source
prohibitions, verdict vocabulary, that execution leaves the original tree untouched,
and that the wheel builds with the correct name and console entry point.

## Adding a runner adapter

An adapter is a pure function from bounded bytes to `Observation` objects. It must:

- use fixed compiled regex or a bounded XML parser, never a regex built from input,
- return a stable node identity that `reconcile_observations` can map,
- report `NOT_RECONCILED` when identity is ambiguous, never guess,
- have at least one positive and one negative test,
- keep the `source` string unchanged, because it appears in findings and goldens.

## Changing the ledger schema

Bump `SCHEMA_VERSION` in `orphantest/__init__.py`, update `docs/schema/v1.json` (or
add v2), regenerate `tests/golden/` with `python3 scripts/capture_golden.py`, and
record the migration in `CHANGELOG.md`. Golden files are normalized: they omit
`provenance`, output digests, and byte counts so they stay portable across machines.
The raw ledger must still be byte-identical before and after any refactor; see
`docs/ARCHITECTURE.md`.

## Issue template

```
Command:
Expected:
Actual:
OS/Python:
Network: offline
Fixture: minimal repro if possible
```

Do not paste secrets into an issue.

## License

MIT. By contributing you agree to `LICENSE`, including the clause that records from
this tool must not be used to evaluate individuals.
