# Workflow and agent roster

The manager owns the plan, resolves conflicts, and signs every gate. Agents specialize;
none of them approves its own work.

## Roster

| ID | Agent | Input | Output | Acceptance gate |
|---|---|---|---|---|
| A1 | Prior Art & Novelty Auditor | candidate shortlist | verified prior-art table, weighted matrix | arithmetic recomputed by manager; every URL opened |
| A2 | Adversarial Griller | current concept | numbered attacks, fatal flaw, minimum fix | must name a fatal flaw; no compliments |
| A3 | Growth & DX Strategist | product concept | 20+ command-checkable requirements, 30-second demo | no fabricated star counts |
| A4 | Security & Architecture Critic | system description | STRIDE model, secure architecture, 40 tests | manager maps every prohibition to code |
| A5 | White-Space Auditor | collisions found by manager | narrow defensible claim, name check | must retract its own weak recommendation |
| A6 | Implementation Engineer | approved design | code and tests | TDD, full suite run and read |
| A7 | Independent Code Reviewer | code at a round | findings by severity | manager verifies each finding against the diff |
| A8 | Architecture Deepening Reviewer | stable code plus golden ledger | before/after architecture report | golden ledger byte-identical after refactor |
| A9 | Verification & Release Auditor | final tree | fresh full-suite output, checklist | no success claim without fresh output |

## Sequence

```
A1 A2 A3 A4  (parallel, independent generation first)
      |
      v
manager grades  -> reject / revise  (done: A1 x2, A2 x2, A3 x2)
      |
      v
A5 (collision check) -> concept locked
      |
      v
A6 build, steps 1-15 of PLAN.md
      |
      v
A7 review rounds 1..8+  -> manager fixes -> re-run fresh
      |
      v
A8 architecture deepening -> golden ledger comparison
      |
      v
A9 final verification -> release
```

## Gate rules

1. **Evidence gate.** No completion claim without the exact command and full output in
   the same message.
2. **Rejection gate.** Low-quality, missing, or unverifiable work goes back to the same
   agent with the defects named. Applied here: the first prior-art report had wrong
   weighted scores and `github.com/example/...` citations; the first growth report had a
   wrong repository owner and unverifiable star figures; the first grilling report cited
   three sources that did not support its statistic.
3. **Conflict gate.** A1 said turn-provenance is crowded; A2 recommended pivoting to it.
   The manager rejected A2's pivot. A2 retracted it in round 2. Recorded in
   `docs/DECISIONS.md`.
4. **Collision gate.** A direct product collision kills the concept, no matter how far
   along. Two concepts died this way.
5. **No-function-change gate.** Any refactor must prove a byte-identical golden ledger
   before and after.

## Installed GitHub skills

Seventeen skill definitions from five repositories are vendored under
`.agents/skills/`. They govern this project's engineering work, not the shipped program.

| Source | Skills used for |
|---|---|
| `anthropics/skills` | skill-creator: authoring the project's own skill files |
| `mattpocock/skills` | tdd, grilling, codebase-design, improve-codebase-architecture, diagnosing-bugs, code-review |
| `obra/superpowers` | brainstorming, writing-plans, test-driven-development, verification-before-completion, requesting-code-review, systematic-debugging, subagent-driven-development, dispatching-parallel-agents |
| `hardikpandya/stop-slop` | prose quality gates for all documentation |
| `vercel-labs/agent-skills` | writing-guidelines, docs consistency |
| `anthropics/skills` | skill-creator, authoring reference |
| `hardikpandya/stop-slop` | README and docs voice |
| `vercel-labs/agent-skills` | writing-guidelines |
| `vercel-labs/skills` | skills CLI reference (kept in `skills_src/`, not vendored) |

See `.agents/skills/MANIFEST.md` for the exact file list and licenses.
