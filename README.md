# orphantest

**Your CI is green. Did your tests actually run?**

`orphantest` reconciles three inventories and reports the gap:

1. test files present in the repository,
2. test nodes discovered by static analysis of those files,
3. test nodes observed as executed when your own declared commands run.

It does not judge your code. It does not call a test dead, useless, or safe to delete.
It reports an **execution-inventory discrepancy under the commands you declared**.
That is the whole claim.

## Why

An AI coding agent can add a test file that no CI command collects. A config change can
silently narrow a discovery pattern. A monorepo can ship `tests/` for years without
anyone noticing that half of it never runs. `pytest --collect-only` shows what one runner
would collect. coverage.py shows executed lines. Neither binds the file inventory, the
declared commands, and observed execution into one deterministic ledger.

## Install

```bash
python -m pip install orphantest        # when published
# or, from a checkout, with zero runtime dependencies:
python3 -m pip install --no-deps .
orphantest --version
python3 -m orphantest --version        # also works without installing
```

Requires Python 3.10+ and, for git provenance only, `git`. No network, no credentials,
no LLM, no daemon, no third-party runtime dependencies.

## 30-second demo

From this repository:

```bash
python3 -m orphantest --root examples/demo_repo \
  --config examples/demo_repo/orphantest.json \
  audit --execute --trust-config
```

Four discovered nodes never appear in execution evidence, and one file never enters the
discovery grammar. Exit code is 1. Then:

```bash
python3 -m orphantest --root examples/demo_repo \
  --config examples/demo_repo/orphantest.reconciled.json \
  audit --execute --trust-config
```

The ledger reconciles and exits 0. Same repository, different declared command.

## Quick start

```bash
orphantest init                         # writes orphantest.json
# edit orphantest.json: add your real test commands as argv lists, set reviewed=true
orphantest audit --execute --trust-config
```

`scan` is read-only and never executes anything. `run` executes declared commands in a
throwaway copy and writes an evidence bundle. `audit` builds the ledger from that bundle,
or inline with `--execute`. `report` re-renders a saved ledger.

`--trust-config` is mandatory for anything that executes. A human must read every argv
in the config first. There is no shell: commands are argv lists, executed with
`shell=False`, a minimal environment, and a timeout.

## What the output means

| Overall state | Meaning |
|---|---|
| `INVENTORY_RECONCILED` | Every discovered node has an observed execution record or a declared exemption, and capture is complete. |
| `DISCREPANCY_REPORTED` | At least one `NOT_DISCOVERED`, `DISCOVERED_NOT_EXECUTED`, `NOT_RECONCILED`, `COLLECTION_ERROR`, or `COMMAND_FAILED` finding. |
| `CAPTURE_INCOMPLETE` | A command failed, timed out, or produced no usable evidence. No conclusion drawn. |
| `NO_COMMANDS_DECLARED` | The config has no commands. Never treated as clean. |
| `CONFIG_NOT_REVIEWED` | `reviewed` is false. |

Exit codes: `0` reconciled, `1` discrepancy, `2` usage error, `3` internal or capture
failure, `4` config error.

Every overall state describes the **ledger**, not your code. An exit code of 0 does not
mean your tests pass, your code is correct, your coverage is adequate, or the change is
safe to merge.

## Findings

| Kind | Meaning |
|---|---|
| `NOT_DISCOVERED` | A Python file exists under a discovery root but matches no pattern. |
| `DISCOVERED_NOT_EXECUTED` | A node was discovered statically but no command observed it. |
| `NOT_RECONCILED` | A runner reported an identity with no unambiguous discovered node. |
| `COLLECTION_ERROR` | A test file could not be parsed. |
| `COMMAND_FAILED` / `CAPTURE_ERROR` | A declared command failed or the evidence bundle is unusable. |
| `OBSERVED_SKIPPED` | A node was observed as skipped. |
| `EXEMPT` | A declared, reasoned exemption. Always reported, never hidden. |

Skipped tests may be platform-specific, quarantined, or run manually. Exemptions need a
concrete reason. Nothing here tells you to delete a test.

## Output formats

```bash
orphantest audit --execute --trust-config --format json
orphantest audit --execute --trust-config --format sarif --out report.sarif
```

JSON is deterministic: sorted keys, no timestamps by default, no user or host identity.
`--include-time` opts into a UTC timestamp and breaks byte-for-byte determinism. SARIF
2.1.0 includes stable `partialFingerprints` and real line numbers.

## Config

`orphantest.json` is versioned JSON (`orphantest/config/1`). It declares discovery roots
and patterns, a runner adapter, and a list of commands. Each command is an argv list with
an expected timeout. See `docs/schema/v1.json` and `examples/demo_repo/`.

- No includes, no YAML, no pickle, no eval, no shell strings.
- Unknown keys are rejected.
- An absolute executable is allowed only after `--trust-config`; its digest is recorded
  in the evidence bundle.
- Exemptions require a reason of at least 8 characters.

## Safety properties

- The original working tree is never modified by `scan` or `audit`. Execution happens
  in a copied tree.
- Symlinks are never followed while establishing scope.
- Files are opened once with `O_NOFOLLOW`; measurement and reading use the same fd.
- Every resource axis has a hard cap: files, bytes, depth, output, command count, nodes,
  timeouts.
- Secrets, environment values, and home paths are redacted at the serialization boundary.
- Reports contain no user name, host name, wall-clock time, or productivity metric by
  default. Do not use these records to evaluate individuals.

See `docs/SECURITY_MAPPING.md` and `research/threat_model.md`.

## What this is not

- Not a correctness verifier, a coverage tool, a mutation tester, or a replacement for
  code review.
- Not an "AI agent said done" gate. `showwork` already records agent claims and runs
  declared checks; `keel` already reverts a fix and asks whether a test fails;
  `test-guard`, `TestSeal`, and `Skylos done` already detect deleted, skipped, or
  weakened tests. Those collisions were resolved before this concept was chosen.
  Verified sources are in `research/prior_art.md` and `docs/DECISIONS.md`.
- Not a promise about GitHub stars. 100k+ stars is a tail event and a weak utility
  proxy. The project optimizes for a reproducible 30-second result.

## Development

```bash
python3 -m orphantest --self-test     # bundled suite
bash scripts/verify.sh                # full verification gates
```

## License

MIT. See `LICENSE`.
