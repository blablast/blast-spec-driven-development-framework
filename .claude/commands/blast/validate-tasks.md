---
description: "Pragmatist — KISS + SOTA review of tasks.md przed impl phase"
allowed-tools: Read, Glob, Grep, Bash, Task
argument-hint: <feature-name> [--debate]
---

# blast:validate-tasks — KISS + SOTA review pre-impl

Sprawdza task decomposition + library/pattern choices ZANIM impl phase commit resources. Catches over-engineering, deprecated libs, accidental scope creep.

## Parse Arguments

Parse `$ARGUMENTS`:
- First non-flag token = feature name (kebab-case)
- `--debate` → activates HYBRID composition (Sonnet + qwen3.6 → Haiku judge)

Validate:
- Spec dir exists. If not: STOP.
- `phase` in spec.json must be `tasks-generated` or later.
- `tasks.md` must exist.

## Auto-fire heuristics (when running standalone or via /blast:full --validate)

Even WITHOUT `--debate`, escalate to HYBRID when:
- tasks.md has >8 major tasks (likely over-engineered or genuinely complex)
- design.md references external dep NOT in `.blast/steering/tech.md::Allowed Dependencies`
- `spec.json.complexity_hint == "high"`
- `spec.json.security_critical == true`

## Invoke Agent

```
Task(
  subagent_type="validate-tasks-agent",
  description="KISS + SOTA review for {feature}",
  prompt="""
Feature: {feature}
Spec dir: .blast/specs/{feature}/

Files to read:
- spec.json, requirements.md, design.md, tasks.md
- .blast/steering/{tech,structure,INVENTORY}.md

Mode: {default | thorough}
Auto-approve: true   # bypass approval gate (validation phase)

Output verdict envelope per agent rubric.
"""
)
```

## Display Result

Show agent output verbatim. Plus:

### Severity legend

- **CRITICAL** — structural issue requiring tasks regeneration
- **WARNING** — over-engineering or deprecated library, fix before impl recommended
- **INFO** — stylistic / cosmetic, optional

### Common remediations

- KISS finding → `/blast:tasks {feature} --simplify` (regenerate with leaner decomposition)
- SOTA finding → `/blast:design {feature} --refresh-libs` (revisit library choices) [TODO: doesn't exist yet, manual edit for now]
- DRY finding → manual: edit tasks.md to depend on existing INVENTORY component

## Safety & Fallback

**Spec not in tasks-generated phase**:
- "Cannot validate-tasks before tasks generated. Run /blast:tasks {feature} first."

**No tasks.md**:
- "tasks.md missing — re-run /blast:tasks {feature}."

**tech.md missing Allowed Dependencies section**:
- Agent flags as INFO (not blocking), suggests `/blast:steering` to add section.

**MCP bridge unavailable** (HYBRID mode):
- Fall back to solo Sonnet with notice: "MCP bridge offline; running solo Sonnet review (HYBRID composition skipped)."
