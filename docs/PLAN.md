# Implementation plan

Every step has a test that must fail first, then pass. No step is complete until the full
suite is run and its output is read.

| # | Step | Files | Test that proves it | Gate |
|---:|---|---|---|---|
| 1 | Typed path model and containment | `paths.py` | `test_paths.py` traversal, symlink, NUL, dash, absolute | fail closed on every rejection |
| 2 | Versioned config loader | `contract.py` | `test_contract.py` unknown keys, bad types, empty commands, no shell strings | `NO_COMMANDS_DECLARED` |
| 3 | Resource budgets | `limits.py` | `test_limits.py` file count, bytes, depth, timeout | no unbounded read |
| 4 | Safe git gateway | `git.py` | `test_git.py` argv equality, `--`, env allowlist, blocked subcommands | no `shell=True` |
| 5 | Static test discovery | `discover.py` | `test_discover.py` pytest and unittest nodes, no import of target code | deterministic node IDs |
| 6 | Execution evidence parsers | `adapters.py` | `test_adapters.py` pytest -v, unittest -v, JUnit XML, truncation | no regex from untrusted input |
| 7 | Isolated runner | `runner.py` | `test_runner.py` original tree unchanged, timeout, sanitized env, bounded output | copy, never mutate |
| 8 | Reconciliation | `audit.py` | `test_audit.py` all seven node states, exemptions, empty config | no READY vocabulary |
| 9 | Deterministic evidence bundle | `store.py` | `test_store.py` sorted JSON, atomic replace, no timestamps by default | `orphantest audit` twice is byte-identical |
| 10 | Redaction | `redact.py` | `test_redact.py` token, env var, absolute home path | applied at serialization |
| 11 | Reporters | `report.py` | `test_report.py` JSON schema, SARIF fingerprint, human table | stable exit codes |
| 12 | CLI | `cli.py` | `test_cli.py` every command, `--self-test`, `--version`, bad args | errors name input and fix |
| 13 | Fixture demo repo | `examples/demo_repo/` | `test_golden.py` exact expected ledger | 30-second reproducible output |
| 14 | Docs, license, CI | README, LICENSE, SECURITY.md, CI | docs build check, `scripts/verify.sh` | full suite green |
| 15 | Adversarial security suite | `test_security.py` | symlink, TOCTOU, huge file, bidi, pickle, secret, arg injection | 40+ cases |
| 16 | Eight-plus review rounds | `docs/REVIEW_LOG.md` | fresh full-suite run per round | manager signs each round |
| 17 | Architecture deepening | `docs/ARCHITECTURE.md` | golden ledger byte-identical before and after | zero function change |

## Manager rules for every agent

- An agent delivers evidence, not a status word. "Done" without command output is rejected.
- A report with an unverified URL, a wrong arithmetic result, or a placeholder name goes
  back. It already happened twice in this project.
- Conflicting agent findings are resolved by the manager in writing, not averaged.
- Any claim of a fix requires the exact command and the exact output that proves it.
