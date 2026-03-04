---
description: "Gap analysis — blast sprawdza co już mamy a czego brakuje"
allowed-tools: Read, Task
argument-hint: <feature-name>
---

# blast:validate-gap — Co mamy, czego brakuje?

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
Check that requirements have been completed:
- Verify `.blast/specs/{feature}/` exists
- Verify `.blast/specs/{feature}/requirements.md` exists

If validation fails, inform user to complete requirements phase first.

## Invoke Subagent

Delegate gap analysis to validate-gap-agent:

Use the Task tool to invoke the Subagent with file path patterns:

```
Task(
  subagent_type="validate-gap-agent",
  description="Analyze implementation gap",
  prompt="""
Feature: {feature}
Spec directory: .blast/specs/{feature}/

File patterns to read:
- .blast/specs/{feature}/spec.json
- .blast/specs/{feature}/requirements.md
- .blast/steering/*.md
- .blast/settings/rules/gap-analysis.md
"""
)
```

## Display Result

Show Subagent summary to user, then provide next step guidance:

### Next Phase: Design Generation

**If Gap Analysis Complete**:
- Review gap analysis insights
- Run `/blast:design {feature}` to create technical design document
- Or `/blast:design {feature} -y` to auto-approve requirements and proceed directly

**Note**: Gap analysis is optional but recommended for brownfield projects to inform design decisions.
