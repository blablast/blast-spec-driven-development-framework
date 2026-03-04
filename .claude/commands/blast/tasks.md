---
description: "Plan implementacji — blast rozpisuje taski do zrobienia"
allowed-tools: Read, Task
argument-hint: <feature-name> [-y] [--sequential]
---

# blast:tasks — Co po kolei robimy?

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Split by spaces
- Extract feature name (first non-flag token)
- Check for `-y` flag anywhere in the string
- Check for `--sequential` flag anywhere in the string

Examples:
```
"zoo-garden -y"             → feature=zoo-garden, auto_approve=true, sequential=false
"zoo-garden"                → feature=zoo-garden, auto_approve=false, sequential=false
"zoo-garden -y --sequential" → feature=zoo-garden, auto_approve=true, sequential=true
"-y zoo-garden"             → feature=zoo-garden, auto_approve=true, sequential=false
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`/`$2`/`$3`. Parse it yourself.

## Validate
Check that design has been completed:
- Verify `.blast/specs/{feature}/` exists
- Verify `.blast/specs/{feature}/design.md` exists

If validation fails, inform user to complete design phase first.

## Invoke Subagent

Delegate task generation to spec-tasks-agent:

Use the Task tool to invoke the Subagent with file path patterns:

```
Task(
  subagent_type="spec-tasks-agent",
  description="Generate implementation tasks",
  prompt="""
Feature: {feature}
Spec directory: .blast/specs/{feature}/
Auto-approve: {true if -y flag present, else false}
Sequential mode: {true if --sequential flag present, else false}

File patterns to read:
- .blast/specs/{feature}/*.{json,md}
- .blast/steering/*.md
- .blast/settings/rules/tasks-generation.md
- .blast/settings/rules/tasks-parallel-analysis.md (include only when sequential mode is false)
- .blast/settings/rules/quality-gates.md
- .blast/settings/templates/specs/tasks.md

Mode: {generate or merge based on tasks.md existence}
Instruction highlights:
- Map all requirements to tasks and list requirement IDs only (comma-separated) without extra narration
- Promote single actionable sub-tasks to major tasks and keep container summaries concise
- Apply `(P)` markers only when parallel criteria met (omit in sequential mode)
- Mark optional acceptance-criteria-focused test coverage subtasks with `- [ ]*` only when deferrable post-MVP
"""
)
```

## Display Result

Show Subagent summary to user, then provide next step guidance:

### Next Phase: Implementation

**Before Starting Implementation**:
- **IMPORTANT**: Clear conversation history and free up context before running `/blast:impl`
- This applies when starting first task OR switching between tasks
- Fresh context ensures clean state and proper task focus

**If Tasks Approved**:
- Execute specific task: `/blast:impl {feature} 1.1` (recommended: clear context between each task)
- Execute multiple tasks: `/blast:impl {feature} 1.1,1.2` (use cautiously, clear context between tasks)
- Without arguments: `/blast:impl {feature}` (executes all pending tasks - NOT recommended due to context bloat)

**If Modifications Needed**:
- Provide feedback and re-run `/blast:tasks {feature}`
- Existing tasks used as reference (merge mode)

**Note**: The implementation phase will guide you through executing tasks with appropriate context and validation.
