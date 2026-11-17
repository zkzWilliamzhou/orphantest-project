# Security policy

## Trust model

`orphantest` treats the inspected repository, its filenames, its config-shaped files,
and any evidence bundle as untrusted data. The operator, the CLI arguments, and the
explicitly trusted config are the trusted inputs.

`--trust-config` is a real trust boundary. It asserts that a human read every argv in
`orphantest.json`. Commands run with `shell=False`, an allowlisted environment, a
timeout, and no network helper. An absolute executable can run arbitrary code by design,
so never pass `--trust-config` on a config you did not review.

## Supported versions

| Version | Supported |
|---|---|
| 1.0.x | Yes |

## Reporting a vulnerability

Open a GitHub issue with:

```
Command: <exact command>
Expected: <exit code and output>
Actual: <exit code and output>
OS/Python: <e.g. Ubuntu 24.04 / Python 3.12>
Network: offline
Fixture: <minimal repro if possible>
```

Do not paste secrets into an issue. Redact them; `orphantest` already redacts its own
output at the serialization boundary.

## Hard prohibitions in the codebase

1. No shell for repository data. No `shell=True`, `os.system`, string commands.
2. No repository-controlled configuration as policy.
3. No symlink following while establishing scope.
4. No reopening a path after checking it. One fd per measurement.
5. No executable deserialization. JSON only, strict schema, no pickle, no eval.
6. No writes outside the operator-declared root or output destination.
7. No unlimited reads. Every axis has a cap.
8. No secrets, environment values, stack traces, or absolute home paths in output.
9. No continuing past an integrity failure.
10. No network, credentials, or daemon as an implicit capability.

## Known limitations

- `O_NOFOLLOW` and `os.replace` semantics differ on Windows. Windows is deliberately
  absent from CI and is not a supported platform for 1.0.0.
- Git provenance is best-effort and advisory. It records HEAD and its parents; it does
  not attest worktree cleanliness.
- Runner adapters currently cover pytest verbose, unittest verbose, and JUnit XML. A
  runner with no parsable evidence yields `NOT_RECONCILED` or `CAPTURE_INCOMPLETE`,
  never a fabricated result.
- A command that exits 0 without collecting any tests can still produce an empty
  observation set. The ledger reports the discrepancy; it does not claim coverage.
