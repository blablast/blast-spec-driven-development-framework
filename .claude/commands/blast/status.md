---
description: "Gdzie jesteśmy? blast pokazuje status i postęp"
allowed-tools: Bash, Read, Glob, Write, Edit, MultiEdit, Update
argument-hint: <feature-name>
---

# blast:status — Raport sytuacyjny

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Strip any flags (tokens starting with `-`) — this command has no flags
- Extract feature name from remaining tokens (kebab-case identifier)
- If empty after stripping → list all specs

Examples:
```
"zoo-garden"     → feature=zoo-garden
""               → feature=null (list all specs)
"zoo-garden -y"  → feature=zoo-garden (flag ignored)
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`. Parse it yourself.

<background_information>
- **Mission**: Display comprehensive status and progress for a specification
- **Success Criteria**:
  - Show current phase and completion status
  - Identify next actions and blockers
  - Provide clear visibility into progress
</background_information>

<instructions>
## Core Task
Generate status report for the parsed feature showing progress across all phases.

## Execution Steps

### Step 1: Load Spec Context
- Read `.blast/specs/{feature}/spec.json` for metadata and phase status
- Read existing files: `requirements.md`, `design.md`, `tasks.md` (if they exist)
- Check `.blast/specs/{feature}/` directory for available files

### Step 2: Analyze Status

**Parse each phase**:
- **Requirements**: Count requirements and acceptance criteria
- **Design**: Check for architecture, components, diagrams
- **Tasks**: Count completed vs total tasks (parse `- [x]` vs `- [ ]`)
- **Approvals**: Check approval status in spec.json

### Step 3: Generate Report

Create report in the language specified in spec.json covering:
1. **Current Phase & Progress**: Where the spec is in the workflow
2. **Completion Status**: Percentage complete for each phase
3. **Task Breakdown**: If tasks exist, show completed/remaining counts
4. **Next Actions**: What needs to be done next
5. **Blockers**: Any issues preventing progress

## Critical Constraints
- Use language from spec.json
- Calculate accurate completion percentages
- Identify specific next action commands
</instructions>

## Tool Guidance
- **Read**: Load spec.json first, then other spec files as needed
- **Parse carefully**: Extract completion data from tasks.md checkboxes
- Use **Glob** to check which spec files exist

## Output Description

Provide status report in the language specified in spec.json:

**Report Structure**:
1. **Feature Overview**: Name, phase, last updated
2. **Phase Status**: Requirements, Design, Tasks with completion %
3. **Task Progress**: If tasks exist, show X/Y completed
4. **Next Action**: Specific command to run next
5. **Issues**: Any blockers or missing elements

**Format**: Clear, scannable format with emojis for status

## Safety & Fallback

### Error Scenarios

**Spec Not Found**:
- **Message**: "No spec found for `{feature}`. Check available specs in `.blast/specs/`"
- **Action**: List available spec directories

**Incomplete Spec**:
- **Warning**: Identify which files are missing
- **Suggested Action**: Point to next phase command

### List All Specs

To see all available specs:
- Run with no argument or use wildcard
- Shows all specs in `.blast/specs/` with their status
