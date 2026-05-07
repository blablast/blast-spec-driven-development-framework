---
description: "Audyt bezpieczeństwa — skanuj kod pod kątem typowych luk i zagrożeń"
allowed-tools: Read, Bash, Glob, Grep, Edit, Write, Task
argument-hint: <feature-name | --all> [--fix]
---

# blast:security — Audyt bezpieczeństwa kodu

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Split by spaces
- Extract flags: `--fix` (auto-fix what's possible), `--all` (scan entire codebase)
- Ignore unknown flags (tokens starting with `-` that aren't `--fix`/`--all`)
- Extract feature name (first non-flag token — kebab-case identifier)
- If no feature name and no `--all`: auto-detect (single active spec)

Examples:
```
"zoo-garden"           → feature=zoo-garden, fix=false
"zoo-garden --fix"     → feature=zoo-garden, fix=true
"--all"                → scope=all, fix=false
"--all --fix"          → scope=all, fix=true
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`. Parse it yourself.

## Execution

## Routing Decision (deterministic — execute in order, do NOT skip)

This slash command is a **deterministic router**. Before invoking any subagent, you MUST:

### Step 1: Parse `--no-debate` flag

Check `$ARGUMENTS` for the literal token `--no-debate`. Set:
- `NO_DEBATE = true` if found, else `false`
- Strip the flag before extracting other arguments

### Step 2: Read debate routing config

Use the Read tool on `.blast/steering/llm-routing.md`. Locate the YAML block under `debate_config.security`. Extract:
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
  description="Sentinel — debate path (security-posture)",
  prompt="""
Run the slash command: /blast:debate {feature} security-posture --protocol B

Auto-approve: true

Adopt the debate's verdict envelope as the final output. Prefix with `**Debate-driven verdict**`.
"""
)
```

After debate returns, display its verdict to the user. STOP — do NOT also invoke the solo agent.

#### Path SKIP: invoke solo agent

```
Task(
  subagent_type="security-audit-agent",
  description="Sentinel — Security audit",
  prompt="""
Feature: {feature} | Scope: --all
Fix mode: {yes/no}

Execute full security audit following your protocol.
File patterns to expand:
- .blast/steering/*.md
- .blast/specs/{feature}/*.md (if feature-scoped)
"""
)
```

After agent returns, display its verdict to the user.


## Post-Agent

After agent returns:

1. **Display verdict** prominently: PASS / FIX REQUIRED / BLOCK
2. **Show report location**
3. **Suggest next step**:
   - PASS: "Kod jest bezpieczny. Kontynuuj pipeline."
   - FIX REQUIRED: "Popraw znalezione problemy lub uruchom `/blast:security {feature} --fix`"
   - BLOCK: "⛔ Krytyczne luki! Napraw PRZED wdrożeniem."

## Output

Provide concise summary (under 200 words) in the language from spec.json.
