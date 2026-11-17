# Vendored skills manifest

Installed 2026-11-11 from GitHub tarballs into `.agents/skills/`. These are source
documents for the project's engineering workflow. `orphantest` itself has zero runtime
dependencies and does not load them.

| Path | Upstream | License (per upstream) | Why it is here |
|---|---|---|---|
| `superpowers/brainstorming` | obra/superpowers | MIT | design gate before creative work |
| `superpowers/test-driven-development` | obra/superpowers | MIT | RED-GREEN-REFACTOR |
| `superpowers/verification-before-completion` | obra/superpowers | MIT | evidence before claims |
| `superpowers/requesting-code-review` | obra/superpowers | MIT | independent review rounds |
| `superpowers/systematic-debugging` | obra/superpowers | MIT | root cause before fix |
| `superpowers/writing-plans` | obra/superpowers | MIT | PLAN.md shape |
| `superpowers/subagent-driven-development` | obra/superpowers | MIT | quality gates per step |
| `superpowers/dispatching-parallel-agents` | obra/superpowers | MIT | parallel research agents |
| `mattpocock/tdd` | mattpocock/skills | MIT | RED-GREEN-REFACTOR |
| `mattpocock/grilling` | mattpocock/skills | MIT | adversarial self-grilling |
| `mattpocock/codebase-design` | mattpocock/skills | MIT | module, interface, depth, seam, adapter |
| `mattpocock/improve-codebase-architecture` | mattpocock/skills | MIT | architecture deepening round |
| `mattpocock/diagnosing-bugs` | mattpocock/skills | MIT | review-round fixes |
| `mattpocock/code-review` | mattpocock/skills | MIT | review checklist |
| `stop-slop` | hardikpandya/stop-slop | MIT | prose quality in docs |
| `vercel/writing-guidelines` | vercel-labs/agent-skills | MIT | docs consistency |
| `anthropics/skill-creator` | anthropics/skills | Apache 2.0 | skill authoring reference |

Upstream license texts were not always present at the skill level; each entry records the
repository-level license as documented by the upstream README. Verify before any
redistribution beyond this workspace.
