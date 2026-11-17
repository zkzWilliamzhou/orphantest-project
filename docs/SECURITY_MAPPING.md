# Security mapping

Every prohibition from `SECURITY.md` maps to a specific module and a specific test.
The manager checked each row against the source; "implemented" here means a test
exists and passes.

| # | Prohibition | Module / function | Test |
|---:|---|---|---|
| 1 | No shell for repository data | `runner.execute_commands` uses `subprocess.Popen(argv, shell=False)` | `test_security.py::test_22_no_shell_in_source`, `test_23_no_pickle_or_eval_import` |
| 2 | No repository-controlled config as policy | `contract.load_contract` rejects unknown top-level keys, unknown limits keys, non-integer limits, shell strings, relative executables | `test_core.py::ContractTests`, `test_security.py::test_26_config_rejects_unknown_include_key` |
| 3 | No symlink following while establishing scope | `paths.open_scoped` uses `O_NOFOLLOW`; `discover._walk_dir` records and skips symlinks | `test_security.py::test_09_directory_symlink_escape`, `test_10_final_component_symlink`, `test_discover.py::test_symlink_never_followed` |
| 4 | No reopening a path after a check | `store.read_regular_file` opens once with `O_NOFOLLOW`, `fstat`s that fd, reads from it | `test_core.py::test_reader_rejects_symlink`, `test_security.py::test_17_symlinked_input_rejected` |
| 5 | No executable deserialization | `store.load_json_file` uses JSON only, with a depth guard and `RecursionError` catch; config does the same | `test_security.py::test_12_deep_json_nesting`, `test_15_pickle_payload_is_inert_json`, `test_32_malformed_bundle_observation_fails_closed` |
| 6 | No writes outside declared root or output | `runner.copy_repository` writes only inside a `tempfile.mkdtemp` copy; `store.atomic_write` writes to the operator's path | `test_integration.py::test_original_tree_unchanged_by_execute`, `test_security.py::test_34_original_tree_unchanged_after_run` |
| 7 | No unlimited reads | `limits.py` caps 9 axes: files, total bytes, file bytes, depth, path bytes, output bytes, command seconds, commands, nodes; every config value is capped by `min(value, DEFAULTS[key])` | `test_security.py::test_18_huge_file_limit`, `test_19_deep_tree_limit`, `test_20_file_count_limit`, `test_31_command_timeout_is_bounded` |
| 8 | No secrets or home paths in output | `redact.redact_obj` applied at serialization in `store.serialize_bundle` / `serialize_ledger`; token-like patterns only | `test_security.py::test_28_redaction_survives_nested_report`, `test_29_redaction_does_not_destroy_digests`, `test_30_error_output_hides_home_path`, `test_21_safe_env_has_no_secrets` |
| 9 | No continuing past an integrity failure | `bundle.validate_bundle` rejects stale digests, unknown fields, malformed observations; `audit` reports `CAPTURE_ERROR` and `CAPTURE_INCOMPLETE` | `test_integration.py::test_stale_config_digest_is_rejected`, `test_audit_without_evidence_is_capture_incomplete`, `test_bundle.py` |
| 10 | No network, credentials, or daemon | `runner._safe_env` allowlists exactly 9 environment variables, drops all secrets, isolates `HOME`; no socket/urllib/requests/http.client import anywhere | `test_security.py::test_21_safe_env_has_no_secrets`, `test_24_no_network_imports`, `test_bundle.py::test_load_preserves_executable_digest` |

## Additional hardening

- **Unicode path attacks**: `paths.validate_relative` rejects absolute paths,
  `..`, backslash, NUL, leading-dash option injection, bidi controls, NFKC-unstable
  strings, and a conservative set of non-Latin homoglyphs. Tests 01–08.
- **Git argv injection**: `git.GitGateway` allowlists subcommands, rejects
  option-like paths, and always terminates path arguments with `--`. Test 25.
- **Renderer tracebacks**: `report.validate_ledger` checks every required field and
  type before `render_human`, `render_json`, or `render_sarif` indexes anything, so a
  malformed saved ledger yields a typed `CONFIG_ERROR` (exit 4), never a traceback.
- **Trust boundary**: `--trust-config` is required for `run` and `audit --execute`.
  An absolute executable is permitted only after that flag; its SHA-256 digest is
  recorded as `executable_digest` in the evidence bundle so substitution is visible.
- **Determinism**: no timestamps by default, no hostname, no username, no git dirty
  flag, sorted keys, sorted findings, sorted nodes. `--include-time` is opt-in and
  documented as breaking byte-for-byte determinism.

## Residual risks (not claimed as fixed)

- `--trust-config` on an unreviewed absolute executable is arbitrary code execution
  by design. The tool cannot distinguish a reviewed config from an unreviewed one.
- Runner output parsers are heuristic. An unparsable runner produces
  `NOT_RECONCILED` or `CAPTURE_INCOMPLETE`, never a fabricated pass.
- `os.replace` behavior on Windows is untested; Windows is not in CI.
