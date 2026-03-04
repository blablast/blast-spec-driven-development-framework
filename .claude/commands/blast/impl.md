---
description: "Czas na kod — blast implementuje taski w TDD"
allowed-tools: Read, Task
argument-hint: <feature-name> [task-numbers]
---

# blast:impl — Lecimy z kodem!

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Split by spaces
- Ignore any flags (tokens starting with `-`): this command has no flags
- Extract feature name (first non-flag token — kebab-case identifier)
- Extract task numbers (remaining non-flag tokens, if any)
  - Format: "1.1" (single task), "1.1,1.2" (multiple tasks comma-separated), or "1,2,3" (major tasks)
  - If not provided: Execute all pending tasks

Examples:
```
"zoo-garden 1.1"       → feature=zoo-garden, tasks=["1.1"]
"zoo-garden 1.1,1.2"   → feature=zoo-garden, tasks=["1.1","1.2"]
"zoo-garden"            → feature=zoo-garden, tasks=all pending
"zoo-garden 1,2,3"     → feature=zoo-garden, tasks=["1","2","3"]
"zoo-garden -y"         → feature=zoo-garden, tasks=all pending (flag ignored)
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`/`$2`. Parse it yourself.

## Validate
Check that tasks have been generated:
- Verify `.blast/specs/{feature}/` exists
- Verify `.blast/specs/{feature}/tasks.md` exists

If validation fails, inform user to complete tasks generation first.

## Task Selection Logic

**Parse task numbers** (perform this in Slash Command before invoking Subagent):
- If task numbers provided: Parse them (e.g., "1.1", "1.1,1.2,1.3")
- Otherwise: Read `.blast/specs/{feature}/tasks.md` and find all unchecked tasks (`- [ ]`)

## Invoke Subagent

Delegate TDD implementation to spec-tdd-impl-agent:

Use the Task tool to invoke the Subagent with file path patterns:

```
Task(
  subagent_type="spec-tdd-impl-agent",
  description="Execute TDD implementation",
  prompt="""
Feature: {feature}
Spec directory: .blast/specs/{feature}/
Target tasks: {parsed task numbers or "all pending"}

File patterns to read:
- .blast/specs/{feature}/*.{json,md}
- .blast/steering/*.md

TDD Mode: strict (test-first)
"""
)
```

## Display Result

Show Subagent summary to user, then provide next step guidance:

### Task Execution

**Execute specific task(s)**:
- `/blast:impl {feature} 1.1` - Single task
- `/blast:impl {feature} 1.1,1.2,1.3` - Multiple tasks

**Execute all pending**:
- `/blast:impl {feature}` - All unchecked tasks

**Before Starting Implementation**:
- **IMPORTANT**: Clear conversation history and free up context before running `/blast:impl`
- This applies when starting first task OR switching between tasks
- Fresh context ensures clean state and proper task focus
