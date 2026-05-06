# Debate: {{TOPIC}}

**Feature**: `{{FEATURE}}`
**Protocol**: {{PROTOCOL}} ({{PROTOCOL_NAME}})
**Started**: {{TIMESTAMP}}
**Models**: Author={{AUTHOR_MODEL}}, Critic={{CRITIC_MODEL}}{{JUDGE_LINE}}
**Cost ceiling**: {{COST_CEILING}} tokens

## Protocol Reference

- **A** Critique-Revise-Judge — single round; Author proposes, Critic challenges, Judge verdicts
- **B** Multi-Jury Vote — N jurors vote independently; Aggregator tallies
- **C** Round-robin — multi-round Author↔Critic; max 4 rounds → Round 5 Synthesis if no convergence
- **D** Devil's Advocate — Author proposes; Critic hard-required to disagree

## Termination Rules

- Author/Critic round-robin: stop on `## I CONCEDE` line OR `## ESCALATE` OR round 4 reached
- Cost ceiling: stop if total tokens > `cost_ceiling` (configurable)
- Stalemate detection: ≥2 consecutive rounds where last entries are semantically identical (haiku similarity check)
- Round 5 Synthesis: triggered when round-robin reaches 4 without convergence (or `ESCALATE_TO_ROUND_5` from Judge)

---

<!-- Append-only below this line. Each entry: ## Round N — <Role> (<model>, <timestamp>) -->
