---
description: "Walidacja kodu vs spec — blast sprawdza czy dowieźliśmy"
allowed-tools: Read, Task
argument-hint: [feature-name] [task-numbers]
---

# blast:validate-impl — Dowieźliśmy czy nie?

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Split by spaces
- Ignore any flags (tokens starting with `-`) — this command has no flags
- Extract feature name (first non-flag token — kebab-case identifier, optional)
- Extract task numbers (remaining non-flag tokens, optional — e.g. "1.1" or "1.1,1.2")

Examples:
```
"zoo-garden 1.1"       → feature=zoo-garden, tasks=["1.1"]
"zoo-garden 1.1,1.2"   → feature=zoo-garden, tasks=["1.1","1.2"]
"zoo-garden"            → feature=zoo-garden, tasks=auto-detect
""                      → feature=auto-detect, tasks=auto-detect
"zoo-garden -y"         → feature=zoo-garden, tasks=auto-detect (flag ignored)
```

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
