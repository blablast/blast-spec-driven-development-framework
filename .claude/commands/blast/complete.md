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

### Step 6: Retrospection — capture lessons

Reflect on what was missing at the start of this feature and route lessons to their natural homes. **Keep files short**: prefer refining an existing rule over adding a new one.

**Inputs**:
- `requirements.md`, `design.md`, `tasks.md`
- Git diff of the feature branch: `git diff $(git merge-base HEAD main)..HEAD 2>/dev/null || git log --all --oneline -n 20`
- Any validation reports in `.blast/specs/{feature}/` (e.g. `validate-impl-report.md`)

**Ask silently, answer honestly** — then produce 0–5 candidates:
- What surprised us during implementation?
- What required a course correction vs the design?
- What would have saved time if known at the start?
- Did a library/tool behave unexpectedly? Did anything break in dev/staging?
- Did a domain rule become explicit that wasn't written down?

**Classify each candidate** into exactly one target:

| Category | Target |
|---|---|
| Tech gotcha (framework/library quirk, build/runtime pitfall) | `.blast/steering/tech.md` → `## Gotchas` |
| Incident (something broke, cost us time) | `.blast/steering/tech.md` → `## Incidents` |
| Project AI rule, tech-facing | `.blast/steering/tech.md` → `## AI Guidance (this project)` |
| Domain invariant (business rule always true) | `.blast/steering/product.md` → `## Invariants` |
| Project AI rule, domain-facing | `.blast/steering/product.md` → `## AI Guidance (domain-facing)` |

**Universal filter**: if the lesson would apply to any blast project, do NOT write it to project files — flag in the output as "consider updating `.blast/settings/rules/ai-collaboration.md` or `code-principles.md` manually." Skip writing.

**Near-neighbor check** (MANDATORY before adding a new line):
1. Read the target section.
2. Search for semantically close existing rules (keyword overlap, same subsystem, same library).
3. Choose exactly one action:
   - **Refine** — existing rule is close; edit in place to subsume the new insight.
   - **Supersede** — new rule strictly covers the old; replace the old line.
   - **New** — no close neighbor; add a single line.
4. Never duplicate. If Refine fits, Refine wins.

**User confirmation per candidate**: present classification, target section, action (refine/supersede/new), exact diff. Accept `y` / `n` / `edit`. Apply only confirmed edits.

**Formatting** (enforces brevity):
- One line per entry. Imperative rule — short "— reason" fragment.
- Incidents: `YYYY-MM-DD — what broke — mitigation`.
- If something needs >1 line, route to `.blast/knowledge/references/` instead.

**Skip silently** if nothing surfaces. Output "No retrospection candidates."

**Record** the tally (e.g. `lessons: 2 (tech.md: 1, product.md: 1)`) in the INVENTORY.md entry added in Step 5.

### Step 7: Update CHANGELOG.md

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

### Step 8: Post-Completion Actions

Suggest next steps:
- `/blast:security {feature}` — security audit before deployment (recommended)
- `/blast:steering` — sync project memory with new patterns from implementation
- Review if any active specs depend on components just shipped
- If coverage < 80%: suggest creating a new spec for test improvements

</instructions>

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
