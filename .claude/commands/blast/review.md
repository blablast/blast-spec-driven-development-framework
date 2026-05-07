---
description: "Code review — blast sprawdza jakość kodu pod kątem zasad i lintingu"
allowed-tools: Read, Task
argument-hint: [feature-name] [--fix]
---

# blast:review — Jak wygląda ten kod?

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Extract feature name (first non-flag token — kebab-case identifier, optional)
- Check for `--fix` flag anywhere in the string
- Ignore any other flags

Examples:
```
"zoo-garden"            → feature=zoo-garden, fix=false
"zoo-garden --fix"      → feature=zoo-garden, fix=true
"--fix zoo-garden"      → feature=zoo-garden, fix=true
""                      → feature=null (review whole codebase), fix=false
"--fix"                 → feature=null (review whole codebase), fix=true
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`/`$2`. Parse it yourself.

## Determine Scope

**If feature name provided**:
- Read `.blast/specs/{feature}/design.md` — extract component list (files to review)
- Read `.blast/specs/{feature}/tasks.md` — find what was implemented
- Scope review to files delivered by this feature

**If no feature name**:
- Review entire `src/` (or project root) — all source files
- Exclude: `tests/`, `node_modules/`, `__pycache__/`, `.blast/`, `.claude/`

## Invoke Subagent

Delegate code review to code-review-agent:

Use the Task tool to invoke the Subagent:

```
Task(
  subagent_type="code-review-agent",
  description="Compass — Code review against principles",
  prompt="""
Feature: {feature or "full codebase"}
Fix mode: {true/false}
Review scope: {list of files/directories to review}

File patterns to read:
- .blast/settings/rules/code-principles.md
- .blast/steering/*.md (for project conventions)
- {scoped source files}

Mode: {"review + fix" if --fix, else "review only"}
"""
)
```

## Display Result

Show Subagent summary to user:

### Review Complete
- Issue count by severity (Critical / Warning / Info)
- If `--fix`: list of auto-fixed issues

### Usage

**Review feature code**:
- `/blast:review zoo-garden` — review only
- `/blast:review zoo-garden --fix` — review + auto-fix

**Review whole codebase**:
- `/blast:review` — review only
- `/blast:review --fix` — review + auto-fix
