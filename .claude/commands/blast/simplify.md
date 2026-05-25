---
description: "Odchudzanie kodu po impl — blast usuwa złożoność z gwarancją zachowania zachowania"
allowed-tools: Read, Task, Bash
argument-hint: [feature-name] [--apply] [--debate|--no-debate]
---

# blast:simplify — Mniej kodu, to samo zachowanie

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Extract `--apply` flag (default OFF → report-only, no code changes)
- Extract `--debate` / `--no-debate` flags
- Extract feature name (first non-flag token, kebab-case, optional)
- If empty: auto-detect (single active spec, or most recent `/blast:impl` in history)

Examples:
```
"zoo-garden"            → feature=zoo-garden, apply=false (report only)
"zoo-garden --apply"     → feature=zoo-garden, apply=true (cut + verify)
"--apply"                → feature=auto-detect, apply=true
""                        → feature=auto-detect, apply=false
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`. Parse it yourself.

## Auto-Detection

**If feature empty**:
- Single active spec in `.blast/specs/` → use it
- Else parse conversation for last `/blast:impl <feature>` → use that feature
- Else scan `.blast/specs/*/tasks.md` for `[x]` checkboxes (implemented features)
- If still ambiguous → ask which feature

## Routing Decision (deterministic — execute in order)

### Step 1: Parse `--no-debate`
Set `NO_DEBATE = true` if the literal token is present; strip it. Strip `--apply` and `--debate` before extracting the feature name too.

### Step 2: Read debate routing config
Read `.blast/steering/llm-routing.md`. Locate the YAML block under `debate_config.simplify`. Extract `enabled` and `trigger`.
**If the block does not exist** (simplify not yet configured): treat as `enabled: true, trigger: high_stakes` (safe default — solo unless the spec is high-risk).

### Step 3: Compute decision (first match wins)
```
if enabled == false:        DECISION = SKIP   reason = "config disabled"
elif NO_DEBATE == true:     DECISION = SKIP   reason = "user passed --no-debate"
elif "--debate" present:    DECISION = FIRE   reason = "user passed --debate"
elif trigger == "always":   DECISION = FIRE   reason = "trigger=always"
elif trigger == "high_stakes":
    # read spec.json + design.md; fire only if risk_level=high or security_critical=true
    DECISION = FIRE if (high_risk or security_critical) else SKIP
else:                       DECISION = SKIP   reason = "default solo"
```

### Step 4: Emit routing line (required, before any tool invocation)
```
Routing: <FIRE|SKIP> — <reason>
```

### Step 5: Branch

#### Path FIRE: spawn debate
```
Task(
  subagent_type="general-purpose",
  description="Occam — debate path (simplify)",
  prompt="""
Run the slash command: /blast:debate {feature} simplify --protocol B

Apply mode: {true if --apply present, else false}
Auto-approve: true

Adopt the debate's verdict envelope as final output. Prefix with `**Debate-driven verdict**`.
"""
)
```
After debate returns, display its verdict. STOP — do not also invoke the solo agent.

#### Path SKIP: invoke solo agent
```
Task(
  subagent_type="simplify-agent",
  description="Occam — simplify implemented code",
  prompt="""
Feature: {feature or auto-detected}
Apply: {true if --apply present, otherwise false}

File patterns to read:
- .blast/specs/{feature}/*.{json,md}
- .blast/settings/rules/code-principles.md
- .blast/steering/tech.md
- .blast/steering/structure.md

Mode: {report-only | apply}
Reminder: report-only must leave git status clean; apply must re-run design.md::Verification Strategy and revert on red.
"""
)
```
After agent returns, display its verdict.

## Display Result

Show the agent summary, then next-step guidance:

**Report mode (no --apply)**:
- If findings exist: "Run `/blast:simplify {feature} --apply` to cut and verify, or review candidates first."
- If clean (PASS, 0 findings): "Code already lean — nothing to remove."

**Apply mode**:
- `APPLIED: true` → "Cut {LOC_DELTA} lines, tests green. Proceed to `/blast:complete {feature}`."
- `APPLIED: false` (reverted) → "Cuts broke tests, reverted. Findings flagged for manual review."

**Note**: simplify is optional and never blocks the pipeline (`BLOCKING: false` always). It runs after `validate-impl`, before `complete`.
