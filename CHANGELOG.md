# Changelog

All notable changes to this project are documented here. The format is based on
Keep a Changelog; the version follows SemVer.

## 1.0.0 — 2026-11-12

First release. Concept, design, implementation and eight examination rounds were
completed 2026-11-11; packaging and the final ten-gate verification on 2026-11-12. Zero runtime dependencies, Python 3.10+, offline by default.

### Added

- `init`, `scan`, `run`, `audit`, `report`, `completion`, `--self-test`, `--version`.
- Deterministic JSON ledger (`orphantest/ledger/1`) with sorted keys and no
  timestamps by default. `--include-time` opts into a UTC timestamp.
- Human and SARIF 2.1.0 renderers, with sorted rule IDs, real `startLine` numbers,
  and `partialFingerprints` seeded from finding identity plus observed status.
- Three reconciled inventories: files present, nodes statically discovered (AST,
  never imports target code), and nodes observed as executed under declared commands.
- Runner adapters for pytest verbose, unittest verbose, and JUnit XML.
- Eight finding kinds plus reasoned exemptions that are always reported.
- Isolated execution in a throwaway copy: `shell=False`, minimal environment,
  per-command timeout, bounded output, recorded executable digest.
- Strict versioned config with unknown-key rejection, no includes, no shell strings.
- Hard resource budgets on nine axes; every configured value is capped.
- Symlink-resistant, single-fd file reads; Unicode confusable and bidi rejection.
- Redaction of token-like secrets, environment values, and home paths at the
  serialization boundary.
- Evidence bundle (`orphantest/evidence/1`) with strict validation and stale-config
  digest rejection.
- A checked-in demo repository with a narrow and a reconciled config, plus portable
  golden ledgers.
- 113 bundled tests: core, discovery/adapters, integration, bundle module, and 35
  adversarial security cases.
- `scripts/verify.sh` with ten verification gates, `scripts/review_rounds.py` with
  eight reproducible examination rounds, and a reproducible golden capture script.
- `pyproject.toml` with a `orphantest` console entry point and zero dependencies.
- Documentation: README, DESIGN, PLAN, WORKFLOW, DECISIONS, ARCHITECTURE,
  SECURITY_MAPPING, REVIEW_LOG, schema, ADRs, threat model, prior-art notes,
  SECURITY, CONTRIBUTING, LICENSE.
- Seventeen vendored GitHub skill definitions under `.agents/skills/` that govern
  the engineering process. They are not loaded by the shipped program.

### Design decisions

- The overall state describes the ledger, never the repository (ADR 0001).
- The evidence bundle is one deep module with `write_bundle` / `load_bundle` as its
  interface (ADR 0002). Before/after raw ledgers are byte-identical.
- `runner: "junit"` is reserved but has no dedicated dispatch (ADR 0003).

### Known limitations

- Windows is not in CI; `O_NOFOLLOW` and `os.replace` semantics differ there.
- Git provenance records HEAD and its parents, not worktree cleanliness.
- Runner adapters are heuristic; unparsable output yields `NOT_RECONCILED` or
  `CAPTURE_INCOMPLETE`, never a fabricated result.
- No claim is made about GitHub stars, correctness, coverage, or test quality.
