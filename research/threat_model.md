# Threat model

## Assets

1. The operator's working tree and its files.
2. The operator's environment variables and home directory path.
3. The integrity of the ledger as evidence.
4. The host running the declared commands.

## Trust boundary

| Side | Classification |
|---|---|
| CLI arguments, `orphantest.json`, `--trust-config` | Trusted, operator-controlled |
| Repository filenames, file contents, `.orphantest/evidence.json`, any JSON file read | Untrusted data |
| Runner stdout/stderr, JUnit XML produced by a command | Untrusted data |
| Git output | Untrusted, advisory only |

The trust boundary is crossed exactly once: when the operator passes
`--trust-config` after reading every argv. There is no way for repository data to
promote itself into policy.

## STRIDE

| Threat | Attack | Control |
|---|---|---|
| **Spoofing** | A repository file named like an `orphantest` config influences the run | Config path comes only from `--config` or `<root>/orphantest.json`, both operator-supplied. No includes, no auto-discovery of config-shaped files. |
| **Spoofing** | A symlinked evidence bundle points at a chosen file | `store.read_regular_file` opens once with `O_NOFOLLOW` and `fstat`s that fd. |
| **Spoofing** | Homoglyph or bidi characters make a reviewer see a different path than the runner | `paths.validate_relative` rejects NFKC-unstable strings, bidi controls, and a conservative homoglyph set. |
| **Tampering** | Edit the config after producing a bundle | The bundle stores `config_digest`; `bundle.validate_bundle` rejects a mismatch and the ledger reports `CAPTURE_ERROR`. |
| **Tampering** | Hand-craft a bundle with extra fields or malformed observations | Strict field allowlist, type checks, count caps. Failure yields `CAPTURE_INCOMPLETE`, not a fabricated pass. |
| **Tampering** | Swap a file between check and open (TOCTOU) | One fd per measurement; no reopen by name. |
| **Repudiation** | Claim a command ran when it did not | Evidence carries argv, returncode, output digest, executable digest, timeout flag, and per-command errors. Git HEAD and parents are advisory. |
| **Information disclosure** | Secrets in runner output reach CI logs | `redact_obj` applied at serialization; token-like patterns only; sensitive env values substituted; home paths replaced with `~`. No stack traces from typed errors. |
| **Information disclosure** | Ledger leaks username, hostname, wall-clock time | None are included by default. `--include-time` is explicit. |
| **Denial of service** | Huge files, deep trees, deep JSON, huge output, long commands | Nine capped axes; JSON depth guard; subprocess timeout; output read cap; all fail with typed errors. |
| **Denial of service** | Regex built from untrusted input, catastrophic backtracking | All patterns are module-level compiled constants. |
| **Elevation of privilege** | Shell metacharacters in argv, option injection in paths | `subprocess.Popen(argv, shell=False)`; paths reject leading dashes, NUL, backslash, absolute paths, `..`; git argv ends with `--`. |
| **Elevation of privilege** | Execute arbitrary binaries via repository content | Only operator-declared absolute executables run, only after `--trust-config`; their digest is recorded. Documented as a deliberate RCE primitive, not a hidden one. |
| **Deserialization** | Pickle/YAML/eval payload in an evidence file | JSON only, UTF-8 only, depth guard, `RecursionError` caught, unknown formats rejected. |

## What the tool does not defend against

- An operator who passes `--trust-config` on an unreviewed config.
- A declared command that intentionally prints fake runner output. The ledger
  reports what was observed; it does not authenticate it.
- A compromised host or a compromised Python interpreter.
- Social misuse: using these records to rank or evaluate individuals. The LICENSE
  explicitly prohibits that use.

## Fail-closed rule

Any integrity failure stops the conclusion: `CAPTURE_INCOMPLETE` (exit 3) or a
config error (exit 4). The tool never continues past a failed check and never
converts missing evidence into a clean result.
