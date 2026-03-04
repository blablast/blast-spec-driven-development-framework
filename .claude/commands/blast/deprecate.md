---
description: "Deprecjonujemy ficzer — blast oznacza spec jako deprecated z migration guide"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
argument-hint: <feature-name> [--reason "powód"]
---

# blast:deprecate — Wycofujemy ficzer

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Split by spaces
- Extract feature name (first non-flag token — kebab-case identifier)
- Check for `--reason` flag followed by quoted or unquoted value
  - `--reason "quoted text"` → reason = "quoted text"
  - `--reason single-word` → reason = "single-word"
  - If no `--reason` → reason = null (ask user later)

Examples:
```
"zoo-garden --reason \"replaced by safari-park\""  → feature=zoo-garden, reason="replaced by safari-park"
"zoo-garden --reason obsolete"                      → feature=zoo-garden, reason="obsolete"
"zoo-garden"                                         → feature=zoo-garden, reason=null
"--reason security zoo-garden"                       → feature=zoo-garden, reason="security"
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`/`$2`. Parse it yourself.

<background_information>
- **Mission**: Mark a shipped feature as deprecated, generate migration guide, update inventory warnings
- **Success Criteria**:
  - spec.json status set to "deprecated" with reason
  - Migration guide generated if replacement exists
  - INVENTORY.md updated with deprecation warnings
  - Dependent specs flagged with action items
</background_information>

<instructions>
## Core Task
Mark feature as deprecated — update metadata, generate migration guidance, warn dependent specs.

## Execution Steps

### Step 1: Load Context

1. Read `.blast/specs/{feature}/spec.json` — verify status is "shipped"
2. Read `.blast/specs/{feature}/design.md` — extract component list
3. Read `.blast/steering/INVENTORY.md` — find component registry entries
4. Read ALL other specs' `spec.json` — check `dependencies` arrays for this feature
5. Parse `--reason` from arguments if provided

### Step 2: Identify Impact

1. **Dependent specs**: Which active/shipped specs depend on this feature's components?
2. **Replacement**: Is there a newer spec that provides equivalent functionality?
3. **Usage scan**: Grep codebase for imports/references to deprecated components

Output impact summary before proceeding.

### Step 3: Update Metadata

Update `spec.json`:
- `status`: `"deprecated"`
- `deprecated_at`: current ISO 8601 timestamp
- `deprecation_reason`: from `--reason` or ask user

### Step 4: Update INVENTORY.md

1. In **Shipped Features**: Change status from "shipped" to "⚠️ deprecated"
2. In **Component Registry**: Add "DEPRECATED" to Notes column for each component
3. In **Deprecations** section: Add entry with:
   - Feature name
   - Deprecation date
   - Reason
   - Replacement (if known)
   - Migration steps (if applicable)

### Step 5: Generate Migration Guide (if replacement exists)

If a replacement spec/component exists:
- Create `.blast/specs/{feature}/MIGRATION.md` with:
  - What's deprecated and why
  - What replaces it
  - Step-by-step migration instructions
  - Before/after code examples (if applicable)

### Step 6: Warn Dependent Specs

For each spec that depends on deprecated components:
- Output warning with specific component and suggested replacement
- Note: don't modify other specs automatically — just inform

</instructions>

## Tool Guidance
- **Read**: spec.json, design.md, INVENTORY.md, other specs
- **Grep**: Find codebase usage of deprecated components
- **Edit**: Update spec.json, INVENTORY.md
- **Write**: Create MIGRATION.md if needed
- **Bash**: Generate timestamp

## Output Description

Provide output in the language specified in spec.json:

1. **Deprecated**: Feature name and reason
2. **Impact**: Number of dependent specs and codebase references
3. **Migration**: Guide created (or "no replacement identified")
4. **Action Required**: List of dependent specs that need updating

**Format**: Concise (under 250 words)

## Safety & Fallback

### Error Scenarios

**Feature Not Shipped**:
- "Feature `{name}` has status `{status}` — can only deprecate shipped features"
- Suggest `/blast:complete` first if status is "active"

**No Reason Provided**:
- Ask user: "Why is this being deprecated? (replacement / obsolete / security / other)"

**Dependent Specs Exist**:
- Don't block — but output clear warning with affected specs
- Recommend updating dependencies before removing deprecated code

**Already Deprecated**:
- "Feature already deprecated on {deprecated_at}. Update migration guide? (yes/no)"
