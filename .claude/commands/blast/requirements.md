---
description: "Generujemy wymagania EARS — blast wie czego potrzebujesz"
allowed-tools: Read, Task
argument-hint: <feature-name>
---

# blast:requirements — Co dokładnie budujemy?

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Strip any flags (tokens starting with `-`) — this command has no flags
- Extract feature name from remaining tokens (kebab-case identifier)

Examples:
```
"zoo-garden"     → feature=zoo-garden
"zoo-garden -y"  → feature=zoo-garden (flag ignored — see note below)
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`. Parse it yourself.

**Note on `-y`**: Requirements is the FIRST phase of the pipeline — there is no prior phase to auto-approve, so `-y` has no semantic meaning here and is silently ignored. The flag becomes meaningful from `/blast:design` onwards (where it auto-approves the previous phase). To approve generated requirements explicitly, use `/blast:approve {feature} requirements`.

## Validate
Check that spec has been initialized:
- Verify `.blast/specs/{feature}/` exists
- Verify `.blast/specs/{feature}/spec.json` exists

If validation fails, inform user to run `/blast:init` first.

## Invoke Subagent

Delegate requirements generation to spec-requirements-agent:

Use the Task tool to invoke the Subagent with file path patterns:

```
Task(
  subagent_type="spec-requirements-agent",
  description="Generate EARS requirements",
  prompt="""
Feature: {feature}
Spec directory: .blast/specs/{feature}/

File patterns to read:
- .blast/specs/{feature}/spec.json
- .blast/specs/{feature}/requirements.md
- .blast/steering/*.md
- .blast/settings/rules/ears-format.md
- .blast/settings/templates/specs/requirements.md

Mode: generate
"""
)
```

## Display Result

Show Subagent summary to user, then provide next step guidance:

### Next Phase: Design Generation

**If Requirements Approved**:
- Review generated requirements at `.blast/specs/{feature}/requirements.md`
- **Optional Gap Analysis** (for existing codebases):
  - Run `/blast:validate-gap {feature}` to analyze implementation gap with current code
  - Identifies existing components, integration points, and implementation strategy
  - Recommended for brownfield projects; skip for greenfield
- Then `/blast:design {feature} [-y]` to proceed to design phase

**If Modifications Needed**:
- Provide feedback and re-run `/blast:requirements {feature}`

**Note**: Approval is mandatory before proceeding to design phase.
