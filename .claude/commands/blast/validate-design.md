---
description: "Review designu — blast sprawdza czy architektura trzyma się kupy"
allowed-tools: Read, Task
argument-hint: <feature-name>
---

# blast:validate-design — Czy to się trzyma kupy?

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Strip any flags (tokens starting with `-`) — this command has no flags
- Extract feature name from remaining tokens (kebab-case identifier)

Examples:
```
"zoo-garden"     → feature=zoo-garden
"zoo-garden -y"  → feature=zoo-garden (flag ignored)
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`. Parse it yourself.

## Validate

Check that design exists:
- Verify `.blast/specs/{feature}/spec.json` exists
- Verify `.blast/specs/{feature}/design.md` exists

If missing, instruct user to complete `/blast:design` first.

## Routing Decision (deterministic — execute in order, do NOT skip)

This slash command is a **deterministic router**. Before invoking any subagent, you MUST:

### Step 1: Parse `--no-debate` flag

Check `$ARGUMENTS` for the literal token `--no-debate`. Set:
- `NO_DEBATE = true` if found, else `false`
- Remove the flag from feature name extraction

### Step 2: Read debate routing config

Use the Read tool on `.blast/steering/llm-routing.md`. Locate the YAML block under `debate_config.validate-design`. Extract:
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
    # legacy — fire only on explicit Force-debate hint (not used by default)
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
  description="Crucible — debate path (design-soundness)",
  prompt="""
Run the slash command: /blast:debate {feature} design-soundness --protocol B

Auto-approve: true

Adopt the debate's verdict envelope as the final output. Prefix it with `**Debate-driven verdict**`.
"""
)
```

After debate returns, display its verdict to the user. STOP — do NOT also invoke the solo agent.

#### Path SKIP: invoke solo agent

```
Task(
  subagent_type="validate-design-agent",
  description="Crucible — Interactive design review",
  prompt="""
Feature: {feature}
Spec directory: .blast/specs/{feature}/

File patterns to read:
- .blast/specs/{feature}/spec.json
- .blast/specs/{feature}/requirements.md
- .blast/specs/{feature}/design.md
- .blast/steering/*.md
- .blast/settings/rules/design-review.md
"""
)
```

After agent returns, display its verdict to the user.

## Display Result

Show Subagent summary to user, then provide next step guidance:

### Next Phase: Task Generation

**If Design Passes Validation (GO Decision)**:
- Review feedback and apply changes if needed
- Run `/blast:tasks {feature}` to generate implementation tasks
- Or `/blast:tasks {feature} -y` to auto-approve and proceed directly

**If Design Needs Revision (NO-GO Decision)**:
- Address critical issues identified
- Re-run `/blast:design {feature}` with improvements
- Re-validate with `/blast:validate-design {feature}`

**Note**: Design validation is recommended but optional. Quality review helps catch issues early.
