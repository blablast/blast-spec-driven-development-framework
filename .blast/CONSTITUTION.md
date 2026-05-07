# blast Constitution

> Top-level governance for blast — Błażej Strus' AI Development Life Cycle.
> Immutable principles that bind every spec, every phase, every agent.

This file aggregates and elevates the operating principles encoded across `.blast/steering/` and `.blast/settings/rules/`. It exists for two reasons: (1) parity with the SOTA SDD convention (GitHub Spec Kit `constitution.md`, BMAD skill schemas) so newcomers can find the project's binding rules in a single named entry-point; (2) to give agents a stable address — `read CONSTITUTION.md` — that surfaces invariants without iterating the whole steering tree.

If something here conflicts with a steering file, **this document wins** for governance intent; the steering file is the operational detail.

---

## Article I — Spec-Driven, Three-Phase Discipline

Code is never the first artifact. Every feature passes through `requirements → design → tasks → impl`, with explicit gates between phases. Optional but encouraged: `research` between requirements and design; `validate-{design,tasks,impl}` after each productive phase.

**Operational detail:** `.blast/specs/{feature}/spec.json::approvals` and `.claude/hooks/blast-approval-gate.py` enforce this at SDK level — the impl agent cannot start if tasks aren't approved, the tasks agent cannot start if design isn't approved, etc. This is a hard gate, not a guideline.

**See:** `CLAUDE.md` (pipeline diagram), `.claude/commands/blast/full.md` (orchestrator), `.claude/hooks/blast-approval-gate.py` (gate enforcement).

---

## Article II — Steering Is Project Memory

`.blast/steering/` is the single source of truth for what this project is, how it's built, and how it evolves. Steering is loaded at the start of every spec and every agent invocation; it does not need to be re-stated in prompts.

Required files:
- `product.md` — purpose, invariants, capabilities
- `tech.md` — stack, canonical commands, gotchas, allowed dependencies, security patterns
- `structure.md` — file layout, module boundaries, naming
- `INVENTORY.md` — shipped components (cross-spec DRY anchor)

Encouraged:
- `RESEARCH.md` — accumulated research patterns
- `llm-routing.md` — debate compositions and trigger semantics
- `cost-policy.md` — budget ceilings per phase

**Update discipline:** every `/blast:complete` triggers retrospection that may write to steering. Universal rules go to `.blast/settings/rules/`; project-specific rules stay in steering.

---

## Article III — Multi-LLM Debate Is the Default for Validation (SOTA #1)

For all `validate-{design,impl,tasks}` and `security` phases, the debate composition specified in `llm-routing.md::debate_config` runs by default. Solo single-agent review is the **exception**, requested explicitly via `--no-debate`.

Compositions wire real subagents and real MCP tools — no stand-ins, no roleplay. If a juror's tool is unavailable (subagent missing, MCP key not set), the juror is **skipped and logged**, never simulated. Aggregator must reflect degradations honestly in the verdict envelope.

**Anti-plateau guard:** when the jury reaches unanimous agreement with **zero dissent**, the aggregator must flag the result as `consensus_review_recommended: true` and recommend either a Devil's Advocate (Protocol D) round or human review. Source: M3MAD-Bench (Q1 2026) — multi-agent debate plateaus and can be subverted by misleading consensus.

**See:** `.blast/steering/llm-routing.md`, `.claude/commands/blast/debate.md`, `.claude/agents/blast/debate/aggregator.md`.

---

## Article IV — Tiered Cost Routing

Default to the cheapest model that delivers the required quality:
- **Templating + structured output** → Haiku (requirements, tasks, complete, deprecate, tiny, steering-custom)
- **Code reasoning + multi-file analysis** → Sonnet (impl orchestrator, research, review, validate-*)
- **Architecture + high-stakes audits** → Opus (design, security)
- **Local code generation for pure functions / dataclasses** → qwen3-coder via blast-llm-bridge (Forge tiered strategy)
- **External juror** → Gemini 3 Flash via blast-llm-bridge (JURY_3_FLASH3 third juror)

Each phase has a `cost_ceiling_usd` in `llm-routing.md`. Exceeding it triggers `WARN: debate truncated` in the verdict envelope, not a hard stop.

---

## Article V — Privacy Mode Is a First-Class Citizen

`spec.json.privacy: local-only` blocks every external LLM call via `blast-privacy-gate.py` (PreToolUse hook). Routing falls back to local Ollama via MCP. Cost ceiling drops to 0.00. No degraded debate — composition uses `[qwen3.6, qwen3-coder]` jurors and `qwen3.6` aggregator.

This is a hard SDK-level gate, not a recommendation.

**See:** `.claude/hooks/blast-privacy-gate.py`, `.blast/steering/llm-routing.md::privacy mode override`.

---

## Article VI — TDD Is the Default Implementation Discipline

`spec-tdd-impl-agent` (Forge) follows red-green-refactor on every task that has a meaningful behavioral surface. Tests are authored before impl where it matters (state-bearing components, contract surfaces, edge-case-rich logic). Pure templating tasks (init files, dataclass shells) may skip TDD when the test would only restate the implementation.

`/blast:validate-impl --prove` runs the design.md `Verification Strategy` block as runtime probes (single test, smoke check, E2E) and reports pass/fail per probe. A green Prove result is the canonical "feature works" signal.

**See:** `.claude/agents/blast/impl.md::TDD Cycle`, `.claude/commands/blast/validate-impl.md::--prove`.

---

## Article VII — Cross-Spec DRY via INVENTORY

Before designing a new component, agents check `.blast/steering/INVENTORY.md` for an existing implementation. Re-inventing a shipped component is a flag-able offense — the design agent must explicitly justify a new copy (different scope, different SLA, deliberate parallel implementation per Article XI) or depend on the existing one.

`/blast:complete` updates INVENTORY with newly shipped components. `/blast:deprecate` marks components as superseded.

---

## Article VIII — Self-Improvement Loop

Every 5 shipped specs, `/blast:complete` triggers `/blast:learn` automatically. The loop:
- **Lessons** — extract gotchas, anti-patterns, surprises from recent specs into `tech.md::Gotchas` / `product.md::Invariants` / `code-principles.md`
- **Calibrate** — compare estimated vs actual cost per phase, update `llm-routing.md::cost_ceiling_usd`
- **Routing observability** — log which compositions fired, their outcomes, and degradation events
- **Refresh SOTA** — audit `.blast/knowledge/sota/*.md` for >6-month-old recommendations, flag for re-research

Manual invocation: `/blast:learn [--lessons|--calibrate|--routing|--refresh-sota|--all]`.

---

## Article IX — Lifecycle Beyond Ship

A feature is not done when shipped. The lifecycle includes:
- `/blast:evolve {feature} "<change>"` — delta-spec for shipped features. Single approval gate, single impl pass; merges back into the parent spec via `/blast:complete`.
- `/blast:deprecate {feature} --reason "..."` — marks shipped feature as deprecated, generates migration guide if a replacement exists, flags dependent specs.
- `/blast:security {feature}` — re-runnable post-ship audit; trigger `always` (jury) ensures security verdict is never solo Sonnet.

---

## Article X — Determinism Where It Matters

Three places in blast are intentionally **not LLM-decided**, because LLMs proved unreliable in prior runs:
1. **Approval gates** — `blast-approval-gate.py` reads `spec.json::approvals` and exits 2 if not approved. No prompt magic.
2. **Privacy gate** — `blast-privacy-gate.py` reads `spec.json::privacy` and blocks external tool calls if local-only.
3. **Routing decision in slash commands** — orchestrator pattern: validate-* slash commands deterministically evaluate `debate_config.{phase}.trigger` against `--no-debate` flag, emit `Routing: FIRE|SKIP — reason`, then branch.

If you find yourself debugging why an agent "decided" to skip something, check whether the decision should be moved to a deterministic gate.

---

## Article XI — Conscious Duplicates Are Allowed

A spec may consciously duplicate an already-shipped feature (educational, benchmark, A/B implementation). To do this honestly:
- Use a versioned namespace (`src/foo_v4/` not `src/foo/`)
- Suffix class names (`HttpClientV4` not `HttpClient`)
- Record the decision in `memory/` with reason
- Cite the original in research.md / design.md as prior art
- INVENTORY differentiates: parent (canonical) vs duplicate (training/bench)

This is rare. Most "evolve" intents should use `/blast:evolve`, not duplicate.

---

## Amendment Process

This document is amended by editing it directly and running `/blast:steering` to propagate any consequential changes to operational steering files. There is no formal vote — this is one developer's framework — but every amendment commit message must explain *why* the article changed, not just *what*.

History of amendments lives in `git log .blast/CONSTITUTION.md`.

---

*Last reviewed: 2026-05-07*
*Article count target: stable at 11. Adding a 12th means promoting a steering rule to invariant status — high bar.*
