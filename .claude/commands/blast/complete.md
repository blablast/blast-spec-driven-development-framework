---
description: "Ficzer shipped! blast zamyka spec i aktualizuje inventory"
allowed-tools: Read, Write, Edit, Glob, Bash
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

<instructions>
## Core Task
Mark the parsed feature as shipped — update spec metadata, populate inventory, and sync project memory.

## Execution Steps

### Step 1: Load and Validate

1. Read `.blast/specs/{feature}/spec.json`
2. Verify all tasks are completed:
   - Read `.blast/specs/{feature}/tasks.md`
   - Count `- [x]` vs `- [ ]` — ALL must be checked
   - If uncompleted tasks exist: warn user and ask for confirmation
3. Read `.blast/specs/{feature}/design.md` to extract delivered components

### Step 2: Coverage Check

Run test coverage and record results:

**Python**:
```bash
pytest --cov=src --cov-report=term-missing --cov-report=json 2>/dev/null || true
```

**JavaScript/TypeScript**:
```bash
npx jest --coverage --coverageReporters=text 2>/dev/null || true
```

- Extract total coverage % from output
- If coverage < 80%: **warn** user ("Coverage is {X}% — consider adding tests before shipping")
- If coverage ≥ 80%: note in completion summary
- If no test runner configured: skip with note
- Store coverage % in spec.json `coverage` field

This is a **soft gate** — low coverage warns but doesn't block shipping.

### Step 3: Extract Deliverables

From `design.md`, identify all delivered components:
- Components, services, modules, endpoints
- Shared utilities, types, interfaces
- Test fixtures and helpers (if reusable)

Build a `provides` list from these deliverables.

### Step 4: Update spec.json

Update the following fields:
- `status`: `"shipped"`
- `completed_at`: current ISO 8601 timestamp
- `provides`: array of delivered component names (from Step 3)
- `coverage`: coverage percentage from Step 2 (if available, e.g. `"82%"`)
- `updated_at`: current timestamp

### Step 5: Update INVENTORY.md

1. Check if `.blast/steering/INVENTORY.md` exists
   - If not: copy from `.blast/settings/templates/steering/inventory.md`
2. Add shipped feature to "Shipped Features" section
3. Add delivered components to "Component Registry" table
4. Update "Cross-Spec Dependencies" if this spec resolved any

### Step 6: Update CHANGELOG.md

1. Check if `CHANGELOG.md` exists at project root
   - If not: create with header:
     ```markdown
     # Changelog

     All notable changes to this project will be documented in this file.
     Format based on [Keep a Changelog](https://keepachangelog.com/).
     ```
2. Read `requirements.md` to extract feature summary (first 1-2 sentences of project description)
3. Prepend new entry under latest version or "Unreleased" section:
   ```markdown
   ## [Unreleased]

   ### Added
   - **{feature-name}**: {one-line summary from requirements} ({N} components, coverage {X}%)
   ```
4. If components include APIs/endpoints, add under relevant subsection (Changed, Fixed, etc.)

### Step 7: Post-Completion Actions

Suggest next steps:
- `/blast:security {feature}` — security audit before deployment (recommended)
- `/blast:steering` — sync project memory with new patterns from implementation
- Review if any active specs depend on components just shipped
- If coverage < 80%: suggest creating a new spec for test improvements

</instructions>

## Tool Guidance
- **Read**: spec.json, tasks.md, design.md
- **Glob**: Check for INVENTORY.md existence
- **Write/Edit**: Update spec.json and INVENTORY.md
- **Bash**: Generate timestamp with `date -u +"%Y-%m-%dT%H:%M:%SZ"`

## Output Description

Provide output in the language specified in spec.json:

1. **Shipped Feature**: Name and brief summary
2. **Coverage**: Test coverage % (with warning if < 80%)
3. **Delivered Components**: List of components added to inventory
4. **Inventory Updated**: Confirm INVENTORY.md changes
5. **Next Steps**: Recommend `/blast:security` + `/blast:steering` sync

**Format**: Concise (under 200 words)

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
