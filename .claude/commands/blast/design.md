---
description: "Design techniczny — blast rysuje architekturę"
allowed-tools: Read, Task
argument-hint: <feature-name> [-y]
---

# blast:design — Jak to zbudujemy?

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Split by spaces
- Extract feature name (first non-flag token)
- Check for `-y` flag anywhere in the string

Examples:
```
"zoo-garden -y"  → feature=zoo-garden, auto_approve=true
"zoo-garden"     → feature=zoo-garden, auto_approve=false
"-y zoo-garden"  → feature=zoo-garden, auto_approve=true
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`/`$2`. Parse it yourself.

## Validate
Check that requirements have been completed:
- Verify `.blast/specs/{feature}/` exists
- Verify `.blast/specs/{feature}/requirements.md` exists

If validation fails, inform user to complete requirements phase first.

## Approval Gate (Requirements -> Design)

Read `.blast/specs/{feature}/spec.json` and inspect `approvals.requirements.approved`.

Decision matrix:
- **`approvals.requirements.approved === true`** -> gate PASS, continue.
- **`approvals.requirements.approved !== true` AND `-y` flag present** -> gate BYPASS (the subagent will set `approvals.requirements.approved = true` after generating), continue.
- **`approvals.requirements.approved !== true` AND no `-y`** -> gate **STOP**. Print:
  ```
  Approval gate failed: requirements not approved.

  Review:    .blast/specs/{feature}/requirements.md
  Approve:   /blast:approve {feature} requirements
  Or skip:   /blast:design {feature} -y    (auto-approves requirements)
  ```
  Do NOT invoke the subagent. Exit cleanly.

## Invoke Subagent

Delegate design generation to spec-design-agent:

Use the Task tool to invoke the Subagent with file path patterns:

```
Task(
  subagent_type="spec-design-agent",
  description="Atlas — Generate technical design and update research log",
  prompt="""
Feature: {feature}
Spec directory: .blast/specs/{feature}/
Auto-approve: {true if -y flag present, else false}

File patterns to read:
- .blast/specs/{feature}/*.{json,md}
- .blast/steering/*.md
- .blast/settings/rules/design-*.md
- .blast/settings/rules/quality-gates.md
- .blast/settings/templates/specs/design.md
- .blast/settings/templates/specs/research.md

Discovery: auto-detect based on requirements
Mode: {generate or merge based on design.md existence}
Language: respect spec.json language for design.md/research.md outputs
"""
)
```

## Display Result

Show Subagent summary to user, then provide next step guidance:

### Next Phase: Task Generation

**If Design Approved**:
- Review generated design at `.blast/specs/{feature}/design.md`
- **Optional**: Run `/blast:validate-design {feature}` for interactive quality review
- Then `/blast:tasks {feature} -y` to generate implementation tasks

**If Modifications Needed**:
- Provide feedback and re-run `/blast:design {feature}`
- Existing design used as reference (merge mode)

**Note**: Design approval is mandatory before proceeding to task generation.
