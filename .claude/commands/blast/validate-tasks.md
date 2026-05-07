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

## Routing Decision (deterministic — execute in order, do NOT skip)

This slash command is a **deterministic router**. Before invoking any subagent, you MUST:

### Step 1: Parse `--no-debate` flag

Check `$ARGUMENTS` for the literal token `--no-debate`. Set:
- `NO_DEBATE = true` if found, else `false`
- Strip the flag before extracting other arguments

### Step 2: Read debate routing config

Use the Read tool on `.blast/steering/llm-routing.md`. Locate the YAML block under `debate_config.validate-tasks`. Extract:
- `enabled` (true | false)
- `trigger` (always | debate_default | high_stakes | thorough_flag | thorough_flag_or_high_complexity)

### Step 3: Compute routing decision (algorithm — first match wins)

```
if enabled == false:
    DECISION = SKIP    reason = "config disabled"
elif NO_DEBATE == true:
    DECISION = SKIP    reason = "user passed --no-debate"
elif trigger == "always":
    DECISION = FIRE    reason = "trigger=always"
elif trigger == "debate_default":
    DECISION = FIRE    reason = "SOTA #1 default trigger"
elif trigger == "high_stakes":
    # legacy — read spec.json + design.md, fire only if risk_level=high or security_critical=true
    DECISION = FIRE if (high_risk or security_critical) else SKIP
elif trigger in ("thorough_flag", "thorough_flag_or_high_complexity"):
    # legacy — fire only on explicit Force-debate hint
    DECISION = SKIP    reason = "legacy trigger; no Force-debate signal"
else:
    DECISION = SKIP    reason = "unknown trigger, defaulting safe"
```

### Step 4: Emit routing line (required, before any tool invocation)

Output this exact line to the user:

```
Routing: <FIRE|SKIP> — <reason>
```

This is non-negotiable. The user must see your routing decision BEFORE any subagent runs.

### Step 5: Branch on DECISION

#### Path FIRE: spawn debate via Task tool

```
Task(
  subagent_type="general-purpose",
  description="Pragmatist — debate path (kiss-sota)",
  prompt="""
Run the slash command: /blast:debate {feature} kiss-sota --protocol B

Auto-approve: true

Adopt the debate's verdict envelope as the final output. Prefix with `**Debate-driven verdict**`.
"""
)
```

After debate returns, display its verdict to the user. STOP — do NOT also invoke the solo agent.

#### Path SKIP: invoke solo agent

```
Task(
  subagent_type="validate-tasks-agent",
  description="Pragmatist — KISS + SOTA review",
  prompt="""
Feature: {feature}
Spec dir: .blast/specs/{feature}/

Files to read:
- spec.json, requirements.md, design.md, tasks.md
- .blast/steering/{tech,structure,INVENTORY}.md

Mode: {default | thorough}
Auto-approve: true

Output verdict envelope per agent rubric.
"""
)
```

After agent returns, display its verdict to the user.


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
