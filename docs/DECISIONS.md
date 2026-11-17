# Decision log

The manager owns these decisions. Each entry records what was rejected, why, and
what evidence changed the plan. Agent reports are evidence, not authority.

## D1 — No star count is a requirement

The brief asked for a program that could get over 105k GitHub stars. A star count is
a tail event and a weak utility proxy; no honest method can guarantee it. Decision:
optimize for a **30-second reproducible result** and a defensible narrow claim.
Stars are an outcome, not a design input. No star figure is quoted in the README.

## D2 — Prior art killed three candidate concepts

Independent prior-art rounds checked adjacent spaces. Verified examples:

| Space | Existing work | Why it kills a candidate |
|---|---|---|
| Agent claims vs deterministic checks | `showwork` (PyPI, "falsifiable claims and deterministic verification for AI agents") | A "did the agent do what it said" tool already exists. |
| Revert-the-fix and rerun | `keel` revert-check gate | A "would a test fail if the fix were undone" tool already exists. |
| Detect deleted / skipped / weakened tests | `test-guard` (npm), `TestSeal`, `Skylos done` | A "did the agent weaken the suite" tool already exists. |

Two earlier concepts died on direct collision. The first prior-art report contained
wrong weighted scores and `github.com/example/...` citations; it was rejected and
rewritten. The first growth report contained an unverifiable owner and star figures;
it was rejected and rewritten. Neither bad report was averaged into the decision.

## D3 — The collision that forced a narrower claim

The surviving concept had to be narrower than "verify AI-written tests". It became:

> Reconcile **test files present**, **test nodes statically discovered**, and **test
> nodes observed as executed under the repository's own declared commands**, and
> report the discrepancy as a deterministic ledger.

`pytest --collect-only` reports what one runner would collect. coverage.py reports
executed lines. Neither binds all three inventories. The gap is in the wiring, and
the tool reports the wiring, not the code.

## D4 — Conflict: A1 vs A2

The prior-art auditor said turn-provenance is crowded. The adversarial griller
recommended pivoting to turn-provenance anyway. The manager rejected the pivot:
a griller's job is to find fatal flaws, not to override a verified collision. The
griller retracted the recommendation in round 2. Recorded here so it is not silently
averaged.

## D5 — No READY / GREEN / PASS vocabulary

ADR 0001. The output field is `scope`, not `coverage`; the human overall line carries
`(ledger state only; not a code-correctness verdict)`. Review round B caught the word
`coverage` in both the human renderer and the JSON key; both were renamed.

## D6 — Demo must match reality

Review round B compared `docs/DESIGN.md`'s demo with actual output and found six
mismatches (command count, node count, field names, class-method node IDs, config
filename). The demo was rewritten from the real captured output. Nothing in the docs
is allowed to be illustrative fiction.

## D7 — Architecture deepening is constrained by the user

The user required zero function change before applying the architecture skill. The
independent reviewer's top candidate (`Capture` ABC) was rejected as too large. The
accepted candidate (evidence-bundle deep module) was proven byte-identical before
and after. Details and hashes in `docs/ARCHITECTURE.md` and ADR 0002.

## D8 — Machine-specific golden data is normalized

Golden files omit `provenance`, `generated_at`, `output_digest`,
`executable_digest`, `stdout_bytes`, and `stderr_bytes` so they are portable across
machines. The **raw** ledger is still compared byte-for-byte by `scripts/verify.sh`
and the architecture gate. A golden file that only passes on one machine is useless.

## D9 — Honest limitations are shipped, not hidden

- `runner: "junit"` is accepted but has no dedicated dispatch (ADR 0003).
- Adapters cover pytest verbose, unittest verbose, and JUnit XML only.
- Git provenance records HEAD and its parents, not worktree cleanliness.
- Windows is not in CI; `O_NOFOLLOW` and `os.replace` semantics differ there.

Each is listed in `SECURITY.md` and `docs/schema/v1.json`.
