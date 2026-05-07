---
description: "Ficzer shipped! blast zamyka spec i aktualizuje inventory"
allowed-tools: Read, Task
argument-hint: <feature-name>
---

# blast:complete — Zamykamy spec, aktualizujemy pamięć

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

<background_information>
- **Mission**: Mark a feature spec as shipped, update project inventory with delivered components, and trigger steering sync recommendation
- **Success Criteria**:
  - spec.json updated with status "shipped" and completed_at timestamp
  - INVENTORY.md in steering updated with delivered components
  - User reminded to run `/blast:steering` for full memory sync
</background_information>

## Validate

Check that spec exists:
- Verify `.blast/specs/{feature}/spec.json` exists (or evolution path under `.blast/specs/*/evolutions/*/spec.json` matching `feature_name`)
- If missing, instruct user to check `/blast:status`

## Invoke Subagent

Delegate the full completion flow (status update, coverage check, inventory population, retrospection, CHANGELOG entry, evolution merge if applicable) to spec-complete-agent:

```
Task(
  subagent_type="spec-complete-agent",
  description="Ledger — Mark feature as shipped",
  prompt="""
Feature: {feature}
Spec directory: .blast/specs/{feature}/  (or evolution path if parent_feature is set)

File patterns to read:
- .blast/specs/{feature}/spec.json
- .blast/specs/{feature}/requirements.md
- .blast/specs/{feature}/design.md
- .blast/specs/{feature}/tasks.md
- .blast/specs/*/evolutions/*/spec.json  (resolve via parent_feature field)
- .blast/steering/*.md
- .blast/steering/INVENTORY.md
- .blast/settings/templates/steering/inventory.md

Mode: complete
"""
)
```

## Display Result

After agent returns:

1. **Show summary** — shipped status, components added to inventory, coverage %, lessons captured
2. **Suggest next steps**:
   - `/blast:security {feature}` — security audit before deployment (recommended)
   - `/blast:steering` — sync project memory with new patterns from implementation
   - Review if any active specs depend on components just shipped
   - If coverage < 80%: suggest creating a new spec for test improvements

## Safety & Fallback

### Error Scenarios

**Uncompleted Tasks**:
- **Warning**: "Feature has X uncompleted tasks. Mark as shipped anyway?"
- If user confirms: proceed with warning note in inventory
- If not: stop and suggest `/blast:impl {feature}` for remaining tasks

**No design.md**:
- **Warning**: "No design document found — cannot extract deliverables automatically"
- **Action**: Ask user to manually list delivered components

**INVENTORY.md Missing**:
- **Action**: Create from template at `.blast/settings/templates/steering/inventory.md`
- Continue with population

**Spec Already Shipped**:
- **Warning**: "Feature already marked as shipped on {date}"
- **Action**: Ask if user wants to update deliverables list
