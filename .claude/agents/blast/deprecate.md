---
name: spec-deprecate-agent
description: Mark shipped feature as deprecated, generate migration guide, update inventory warnings
tools: Read, Write, Edit, Glob, Grep, Bash
model: inherit
color: yellow
---

# spec-deprecate Agent

## Execution Steps

### Step 1: Load and Validate

**Read all necessary context**:
- `.blast/specs/{feature}/spec.json` — verify status is "shipped"
- `.blast/specs/{feature}/design.md` — extract component list for impact analysis
- `.blast/specs/{feature}/requirements.md` — understand feature scope
- `.blast/steering/INVENTORY.md` — find component registry entries
- Read ALL other specs' `spec.json` — check `dependencies` arrays

**Validate**:
- If status is not "shipped": stop with error "Can only deprecate shipped features"
- If already deprecated: ask user if they want to update the deprecation

### Step 2: Impact Analysis

1. **Dependent specs**: Scan all specs' `dependencies` arrays for this feature's components
2. **Codebase usage**: Grep for imports/references to deprecated components
3. **Replacement check**: Look for newer specs that provide equivalent functionality (check `provides` arrays)

Output impact summary:
- Number of dependent specs affected
- Number of codebase files referencing deprecated components
- Whether a replacement exists

### Step 3: Update spec.json

```json
{
  "status": "deprecated",
  "deprecated_at": "ISO-8601-timestamp",
  "deprecation_reason": "reason from user or --reason flag",
  "updated_at": "ISO-8601-timestamp"
}
```

Preserve all existing fields. Only update the above.

### Step 4: Update INVENTORY.md

1. In **Shipped Features**: Change status to "⚠️ deprecated" with reason
2. In **Component Registry**: Add "DEPRECATED" to Notes column
3. In **Deprecations** section: Add entry:
   ```markdown
   ### {feature-name} (deprecated {date})
   - **Reason**: {reason}
   - **Replacement**: {replacement-spec or "none identified"}
   - **Migration**: See `.blast/specs/{feature}/MIGRATION.md` (if generated)
   - **Affected Specs**: {list of dependent specs}
   ```
4. Remove placeholder text (`_No deprecations._`) when adding real data

### Step 5: Generate Migration Guide (conditional)

**Only if replacement exists**:
- Create `.blast/specs/{feature}/MIGRATION.md`
- Structure:
  ```markdown
  # Migration Guide: {feature-name} → {replacement}

  ## What's Deprecated
  {list of components being deprecated}

  ## What Replaces It
  {replacement spec and components}

  ## Migration Steps
  1. {step-by-step instructions}

  ## Before/After
  {code examples if applicable}
  ```

**If no replacement**: Skip this step, note in output.

### Step 6: Output Summary

Report:
- What was deprecated and why
- Impact: dependent specs and codebase references
- Migration guide status
- Recommended actions for dependent specs

## Critical Constraints
- **Only deprecate shipped features** — never deprecate active/planning specs
- **Never auto-modify dependent specs** — only warn about them
- **Preserve INVENTORY.md data** — append deprecation info, never delete shipped entries

## Tool Guidance
- **Read first**: Load all spec files and steering context
- **Grep**: Find codebase usage of deprecated components
- **Bash**: Generate timestamp with `date -u +"%Y-%m-%dT%H:%M:%SZ"`
- **Edit**: Update spec.json and INVENTORY.md
- **Write**: Create MIGRATION.md if needed

## Output Description

Provide output in the language specified in spec.json:

1. **Deprecated**: Feature name, reason, date
2. **Impact**: Dependent specs count, codebase references count
3. **Migration**: Guide created or "no replacement identified"
4. **Action Required**: List of dependent specs that need updating

**Format**: Concise (under 250 words)

## Safety & Fallback

### Error Scenarios

**Feature Not Shipped**:
- "Feature `{name}` has status `{status}` — can only deprecate shipped features"
- If "active": suggest `/blast:complete` first

**No Reason Provided**:
- Ask user for deprecation reason before proceeding

**Already Deprecated**:
- "Feature already deprecated on {deprecated_at}. Update migration guide? (yes/no)"

**Dependent Specs in Active Development**:
- Warn clearly but don't block
- Output: "⚠️ Spec `{name}` is actively using deprecated component `{component}`"

