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

## Invoke Subagent

Delegate validation to validate-impl-agent:

Use the Task tool to invoke the Subagent with file path patterns:

```
Task(
  subagent_type="validate-impl-agent",
  description="Validate implementation",
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
