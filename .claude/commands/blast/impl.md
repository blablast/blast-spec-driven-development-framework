---
description: "Czas na kod — blast implementuje taski w TDD"
allowed-tools: Read, Edit, Task
argument-hint: <feature-name> [task-numbers] [-y] [--max-parallel N] [--sequential]
---

# blast:impl — Lecimy z kodem!

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Split by spaces
- Detect `-y` flag (boolean: present or not)
- Detect `--sequential` flag (boolean: forces sequential execution, ignores `(P)` markers)
- Detect `--max-parallel N` flag (integer; default `4` if absent; clamp to range `1..8`)
- Extract feature name (first non-flag token — kebab-case identifier)
- Extract task numbers (remaining non-flag tokens that are not flag values, if any)
  - Format: "1.1" (single task), "1.1,1.2" (multiple tasks comma-separated), or "1,2,3" (major tasks)
  - If not provided: Execute all pending tasks

Examples:
```
"zoo-garden 1.1"                     → feature=zoo-garden, tasks=["1.1"], y=false, max_parallel=4, sequential=false
"zoo-garden"                         → feature=zoo-garden, tasks=all, max_parallel=4, sequential=false
"zoo-garden -y"                      → feature=zoo-garden, tasks=all, y=true,  max_parallel=4, sequential=false
"zoo-garden --sequential"            → feature=zoo-garden, tasks=all, max_parallel=4, sequential=true
"zoo-garden --max-parallel 2"        → feature=zoo-garden, tasks=all, max_parallel=2, sequential=false
"zoo-garden -y --max-parallel 6 1.1" → feature=zoo-garden, tasks=["1.1"], y=true, max_parallel=6, sequential=false
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`/`$2`. Parse it yourself.

**Flag semantics:**
- `--sequential` and `--max-parallel` are mutually exclusive in effect — if both supplied, `--sequential` wins (max-parallel ignored).
- `--max-parallel N` caps the size of each wave. Per Anthropic 2026 best practices, 3–5 workers is the sweet spot; default 4.

## Validate
Check that tasks have been generated:
- Verify `.blast/specs/{feature}/` exists
- Verify `.blast/specs/{feature}/tasks.md` exists

If validation fails, inform user to complete tasks generation first.

## Approval Gate (Tasks -> Implementation)

Read `.blast/specs/{feature}/spec.json` and inspect `approvals.tasks.approved`.

Decision matrix:
- **`approvals.tasks.approved === true`** -> gate PASS, continue to Task Selection Logic.
- **`approvals.tasks.approved !== true` AND `-y` flag present** -> gate BYPASS. Use the Edit tool to set `approvals.tasks.approved = true` in `.blast/specs/{feature}/spec.json` (also update `updated_at` to current ISO-8601 UTC timestamp). This satisfies the subagent's own approval check (see `agents/blast/impl.md` Step 1). Continue to Task Selection Logic.
- **`approvals.tasks.approved !== true` AND no `-y`** -> gate **STOP**. Print:
  ```
  Approval gate failed: tasks not approved.

  Review:    .blast/specs/{feature}/tasks.md
  Approve:   /blast:approve {feature} tasks
  Or skip:   /blast:impl {feature} -y    (bypass approval, e.g. for /blast:full --auto)
  ```
  Do NOT invoke the subagent. Exit cleanly.

## Task Selection Logic

**Parse task numbers** (perform this in Slash Command before invoking Subagent):
- If task numbers provided: Parse them (e.g., "1.1", "1.1,1.2,1.3")
- Otherwise: Read `.blast/specs/{feature}/tasks.md` and find all unchecked tasks (`- [ ]`)
- **Resume check**: If some tasks are already `[x]`, only pass pending `[ ]` tasks to the agent. Log skipped tasks: "Skipping completed: {task numbers}"
- If ALL tasks are `[x]`: skip agent invocation entirely, report "All tasks completed" and suggest `/blast:complete {feature}`

## Invoke Subagent

Delegate TDD implementation to spec-tdd-impl-agent:

Use the Task tool to invoke the Subagent with file path patterns:

```
Task(
  subagent_type="spec-tdd-impl-agent",
  description="Forge — Execute TDD implementation",
  prompt="""
Feature: {feature}
Spec directory: .blast/specs/{feature}/
Target tasks: {parsed task numbers or "all pending"}

Execution mode: {sequential ? "sequential" : "parallel"}
Max parallel workers per wave: {max_parallel}    # honored only when execution mode=parallel; clamp 1..8

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
