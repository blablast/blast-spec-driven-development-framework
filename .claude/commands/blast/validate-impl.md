---
description: "Walidacja kodu vs spec — blast sprawdza czy dowieźliśmy"
allowed-tools: Read, Task, Bash
argument-hint: [feature-name] [task-numbers] [--prove]
---

# blast:validate-impl — Dowieźliśmy czy nie?

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Split by spaces
- Extract `--prove` flag if present (enables Behavioral Verification / Prove Mode)
- Extract feature name (first non-flag token — kebab-case identifier, optional)
- Extract task numbers (remaining non-flag tokens, optional — e.g. "1.1" or "1.1,1.2")

Examples:
```
"zoo-garden 1.1"          → feature=zoo-garden, tasks=["1.1"], prove=false
"zoo-garden 1.1,1.2"      → feature=zoo-garden, tasks=["1.1","1.2"], prove=false
"zoo-garden --prove"       → feature=zoo-garden, tasks=auto-detect, prove=true
"zoo-garden 1.1 --prove"   → feature=zoo-garden, tasks=["1.1"], prove=true
""                          → feature=auto-detect, tasks=auto-detect, prove=false
```

`--prove` adds Behavioral Verification: runs the commands from `design.md :: Verification Strategy` (local test, smoke, e2e probe) and reports whether outputs match the Expected Signal. Use it when static validation isn't enough — you want runtime proof the feature actually works.

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`/`$2`. Parse it yourself.

## Auto-Detection Logic

**Perform detection before invoking Subagent**:

**If no arguments** (empty `$ARGUMENTS`):
- Parse conversation history for `/blast:impl <feature> [tasks]` patterns
- OR scan `.blast/specs/*/tasks.md` for `[x]` checkboxes
- Pass detected features and tasks to Subagent

**If feature only** (feature present, no task numbers):
- Read `.blast/specs/{feature}/tasks.md` and find all `[x]` checkboxes
- Pass feature and detected tasks to Subagent

**If both provided** (feature and task numbers):
- Pass directly to Subagent without detection

## Routing Decision (deterministic — execute in order, do NOT skip)

This slash command is a **deterministic router**. Before invoking any subagent, you MUST:

### Step 1: Parse `--no-debate` flag

Check `$ARGUMENTS` for the literal token `--no-debate`. Set:
- `NO_DEBATE = true` if found, else `false`
- Strip the flag before extracting other arguments

### Step 2: Read debate routing config

Use the Read tool on `.blast/steering/llm-routing.md`. Locate the YAML block under `debate_config.validate-impl`. Extract:
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
  description="Auditor — debate path (impl-correctness)",
  prompt="""
Run the slash command: /blast:debate {feature} impl-correctness --protocol B

Auto-approve: true

Adopt the debate's verdict envelope as the final output. Prefix with `**Debate-driven verdict**`.
"""
)
```

After debate returns, display its verdict to the user. STOP — do NOT also invoke the solo agent.

#### Path SKIP: invoke solo agent

```
Task(
  subagent_type="validate-impl-agent",
  description="Auditor — Validate implementation",
  prompt="""
Feature: {feature or auto-detected}
Target tasks: {tasks or auto-detected}
Mode: {auto-detect, feature-all, or explicit}
Prove: {true if --prove flag present, otherwise false}

File patterns to read:
- .blast/specs/{feature}/*.{json,md}
- .blast/steering/*.md

Validation scope: {based on detection results}
"""
)
```

After agent returns, display its verdict to the user.


## Display Result

Show Subagent summary to user, then provide next step guidance:

### Next Steps Guidance

**If GO Decision**:
- Implementation validated and ready
- Proceed to deployment or next feature

**If NO-GO Decision**:
- Address critical issues listed
- Re-run `/blast:impl {feature} [tasks]` for fixes
- Re-validate with `/blast:validate-impl {feature} [tasks]`

**Note**: Validation is recommended after implementation to ensure spec alignment and quality.
