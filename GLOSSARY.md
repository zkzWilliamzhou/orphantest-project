# Glossary

Domain language used by `orphantest`. Terms are deliberately narrow: if a word here
sounds like a verdict about code quality, it is the wrong word.

## Domain terms

- **Command**: an argv list from the operator-trusted config. Never a shell string.
  It is a declaration of what the repository claims it runs, not proof that it runs.
- **Test file**: a repository file under a discovery root that matches the configured
  discovery grammar.
- **Node**: a canonical test identity, `relative/path.py::Class::test_name`.
- **Discovery grammar**: the configured roots and filename patterns. A file outside
  it is reported as `NOT_DISCOVERED`, never silently ignored.
- **Observation**: one runner-reported execution record. It carries a node identity,
  a status, the command id, and the capture source. An observation is not a pass.
- **Evidence bundle**: a versioned, inert JSON document recording what the declared
  commands printed, with digests and provenance. It is data, never executable state.
- **Ledger**: the deterministic reconciliation of file inventory, discovered nodes,
  and observed records. Its overall state describes **the ledger**, not the repository.
- **Finding**: one row of the ledger. Blocking findings create an exit code of 1.
- **Exemption**: a declared, reasoned statement that a specific file or node is
  intentionally outside the declared commands. Always reported; never hidden.
- **Capture source**: the channel an observation arrived on: `pytest-verbose`,
  `unittest-verbose`, or `junit-xml`.
- **Inventory value**: the immutable snapshot passed from scanning into evidence
  writing and ledger construction (see `orphantest.bundle.Inventory`).
- **Evidence source**: the seam behind which evidence can come from inline execution
  or from a persisted bundle. Two adapters cross it.
- **Scope**: the bounded claim of the ledger. It is intentionally called `scope`,
  never `coverage`.

## Architecture vocabulary

From the vendored `mattpocock/codebase-design` skill, used exactly as defined there:

- **Module**: anything with an interface and an implementation.
- **Interface**: everything a caller must know: signature, invariants, error modes,
  ordering, and performance characteristics. The interface is the test surface.
- **Implementation**: what sits inside the module.
- **Depth**: leverage at the interface; behaviour per unit of interface to learn.
- **Seam**: the location where a module's interface lives; a place where behaviour
  can change without editing that place.
- **Adapter**: a concrete thing satisfying an interface at a seam. One adapter is a
  hypothetical seam; two adapters make a real one.
- **Leverage**: what callers get from depth.
- **Locality**: what maintainers get from depth; change concentrates in one place.
- **Deletion test**: delete the module. If complexity reappears across N callers, it
  was earning its keep.
