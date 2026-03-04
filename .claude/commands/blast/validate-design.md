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
Check that design has been completed:
- Verify `.blast/specs/{feature}/` exists
- Verify `.blast/specs/{feature}/design.md` exists

If validation fails, inform user to complete design phase first.

## Invoke Subagent

Delegate design validation to validate-design-agent:

Use the Task tool to invoke the Subagent with file path patterns:

```
Task(
  subagent_type="validate-design-agent",
  description="Interactive design review",
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
