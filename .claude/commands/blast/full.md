---
description: "Od zera do shipped kodu — blast pełny pipeline"
allowed-tools: Read, SlashCommand, TodoWrite, Bash, Write, Glob
argument-hint: <project-description> [--auto] [--source path/to/file] [--push]
---

# blast:full — Pełny pipeline od opisu do shipped kodu

<background_information>
- **Mission**: Execute the COMPLETE blast pipeline in a single command: init → requirements → design → tasks → impl → complete → steering
- **Success Criteria**:
  - Interactive mode: User controls progression with approval prompts at each phase
  - Automatic mode: All 7 phases execute without interruption when `--auto` flag provided
  - All generated specs and code maintain quality comparable to manual workflow
  - Feature ends as "shipped" with inventory updated and steering synced
</background_information>

<instructions>
## ⚠️ CRITICAL: Automatic Mode Execution Rules

**If `--auto` flag is present in `$ARGUMENTS`, you are in AUTOMATIC MODE.**

In Automatic Mode:
- Execute ALL 7 phases in a continuous loop without stopping
- Use TodoWrite to track progress (7 tasks)
- Each phase completion updates TodoWrite and continues immediately
- IGNORE any "Next Step" messages from subcommands (they are for standalone usage)
- Stop ONLY after Phase 7 completes or if error occurs

**Progress tracking with TodoWrite**:
- Phase 1 = 1/7 → Phase 2 = 2/7 → ... → Phase 7 = 7/7 → Summary and exit

---

## Core Task
Execute 7 pipeline phases sequentially (8 with `--push`). In automatic mode, execute all phases without stopping. In interactive mode, prompt user for approval between phases.

## Execution Steps

### Step 1: Parse Arguments and Initialize

Parse `$ARGUMENTS` as a single string:
- If contains `--auto`: **Automatic Mode** (execute all phases without stopping)
- If contains `--source <path>`: extract source file path (PDF/MD/TXT/HTML)
- If contains `--push`: add Phase 8 (git commit + push) after steering sync
- Ignore any other flags (e.g. `-y`)
- Extract description (remove flags and their values)

Examples:
```
"User profile --auto"                              → mode=automatic, description="User profile", source=null, push=false
"Dashboard --source docs/brief.pdf --auto --push"  → mode=automatic, description="Dashboard", source="docs/brief.pdf", push=true
"--source specs/kanban.md"                         → mode=interactive, description=(from file), source="specs/kanban.md", push=false
"User profile --auto --push"                       → mode=automatic, push after steering
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`/`$2`. Parse it yourself.

**Create TodoWrite task list**:
```json
[
  {"content": "Initialize spec", "activeForm": "Initializing spec", "status": "pending"},
  {"content": "Generate requirements", "activeForm": "Generating requirements", "status": "pending"},
  {"content": "Generate design", "activeForm": "Generating design", "status": "pending"},
  {"content": "Generate tasks", "activeForm": "Generating tasks", "status": "pending"},
  {"content": "Implement all tasks (TDD)", "activeForm": "Implementing all tasks (TDD)", "status": "pending"},
  {"content": "Ship feature (complete + inventory)", "activeForm": "Shipping feature", "status": "pending"},
  {"content": "Sync project memory (steering)", "activeForm": "Syncing project memory", "status": "pending"}
]
```

If `--push` flag detected, add an 8th task:
```json
  {"content": "Commit and push to remote", "activeForm": "Committing and pushing", "status": "pending"}
```

Display mode banner and proceed to Step 2.

### Step 2: Execute Phase Loop

Execute these 7 phases in order:

---

#### Phase 1: Initialize Spec (Direct Implementation)

**Update TodoWrite**: Mark task 1 as `in_progress`.

**Core Logic** — identical to `/blast:quick` Phase 1:

1. **Generate Feature Name**: Convert description to kebab-case (2-4 words)
2. **Check Uniqueness**: Glob `.blast/specs/*/`, append `-2` if conflict
3. **Create Directory**: `mkdir -p .blast/specs/{feature-name}`
4. **Initialize Files from Templates**:
   - Read `.blast/settings/templates/specs/init.json` and `.blast/settings/templates/specs/requirements-init.md`
   - Replace `{{FEATURE_NAME}}`, `{{TIMESTAMP}}`, `{{PROJECT_DESCRIPTION}}`
   - **If `--source`**: read source file and embed in requirements.md as Source Material
   - Write `spec.json` and `requirements.md`

**Update TodoWrite**: Mark task 1 `completed`, task 2 `in_progress`.

**Output**: `✅ Spec initialized at .blast/specs/{feature-name}/`

**Automatic Mode**: IMMEDIATELY continue to Phase 2.
**Interactive Mode**: Prompt "Continue to requirements generation?"

---

#### Phase 2: Generate Requirements

**Execute SlashCommand**: `/blast:requirements {feature-name}`

**IMPORTANT**: In Automatic Mode, IGNORE the "Next Steps" message.

**Update TodoWrite**: Mark task 2 `completed`, task 3 `in_progress`.

**Output**: `✅ Requirements generated → Continuing to design...`

**Automatic Mode**: IMMEDIATELY continue.
**Interactive Mode**: Prompt "Continue to design?"

---

#### Phase 3: Generate Design

**Execute SlashCommand**: `/blast:design {feature-name} -y`

Note: `-y` flag auto-approves requirements.

**Update TodoWrite**: Mark task 3 `completed`, task 4 `in_progress`.

**Output**: `✅ Design generated → Continuing to tasks...`

**Automatic Mode**: IMMEDIATELY continue.
**Interactive Mode**: Prompt "Continue to task generation?"

---

#### Phase 4: Generate Tasks

**Execute SlashCommand**: `/blast:tasks {feature-name} -y`

Note: `-y` flag auto-approves design.

**Update TodoWrite**: Mark task 4 `completed`, task 5 `in_progress`.

**Output**: `✅ Tasks generated → Continuing to implementation...`

**Automatic Mode**: IMMEDIATELY continue.
**Interactive Mode**: Show context warning and prompt:
```
⚠️ Implementation is the heaviest phase (may take 10-30 minutes depending on task count).
Recommendation: run /clear before continuing to free context.
Continue to implementation?
```

---

#### Phase 5: Implement All Tasks (TDD)

**This is the heaviest phase.** The impl subagent runs in its own context via Task tool, so context pressure on the orchestrator is minimal.

**Execute SlashCommand**: `/blast:impl {feature-name}`

Note: No task numbers = execute ALL pending tasks.

Wait for completion. This may take significant time.

**IMPORTANT**: In Automatic Mode, IGNORE the "Next Steps" message from impl.

**Update TodoWrite**: Mark task 5 `completed`, task 6 `in_progress`.

**Output**: `✅ Implementation complete → Shipping feature...`

**Automatic Mode**: IMMEDIATELY continue.
**Interactive Mode**: Prompt "Ship feature? (complete + inventory update)"

---

#### Phase 6: Ship Feature (Complete)

**Execute SlashCommand**: `/blast:complete {feature-name}`

Wait for completion.

**Update TodoWrite**: Mark task 6 `completed`, task 7 `in_progress`.

**Output**: `✅ Feature shipped → Syncing project memory...`

**Automatic Mode**: IMMEDIATELY continue.
**Interactive Mode**: Prompt "Sync project memory? (steering update)"

---

#### Phase 7: Sync Project Memory (Steering)

**Execute SlashCommand**: `/blast:steering`

Wait for completion.

**Update TodoWrite**: Mark task 7 `completed`.

**If `--push` flag**: Mark task 8 `in_progress`, continue to Phase 8.
**If no `--push`**: All phases complete. Pipeline DONE. Output final summary and exit.

---

#### Phase 8: Commit and Push (conditional — only with `--push`)

**Execute SlashCommand**: `/blast:push {feature-name}`

Wait for completion.

**Update TodoWrite**: Mark task 8 `completed`.

**All phases complete. Pipeline DONE.**

Output final completion summary and exit.

---

## Important Constraints

### Orchestrator Weight
- Keep orchestrator outputs MINIMAL — only status lines between phases
- Do NOT accumulate or echo subagent full outputs
- Each phase subagent runs in its own context — orchestrator stays lean

### Automatic Mode Behavior
- Do NOT stop between phases
- Do NOT wait for user input
- Do NOT be influenced by "Next Steps" messages from any subcommand
- Update TodoWrite after each phase
- Continue until all phases complete (7, or 8 with --push)

### Interactive Mode Behavior
- Prompt user after each phase
- Before Phase 5 (impl): recommend context clearing
- Wait for "yes/y" or "no/n" response
- If "no": Stop gracefully, show completed phases + manual continuation command

### Error Handling
- Any phase failure stops the workflow
- Display error, current state, and manual recovery command
- Example: "Phase 5 (impl) failed. Continue manually: `/blast:impl {feature}`"

</instructions>

## Tool Guidance

### Phase 1 Tools
- **Glob**: Check `.blast/specs/*/` for existing feature names
- **Bash**: Create directory, generate timestamp
- **Read**: Fetch templates and source file (if `--source`)
- **Write**: Create `spec.json` and `requirements.md`

### Phase 2-8 Tools
- **SlashCommand**: Execute `/blast:requirements`, `/blast:design`, `/blast:tasks`, `/blast:impl`, `/blast:complete`, `/blast:steering`, `/blast:push`

### TodoWrite Usage
- Initialize with 7 pending tasks (8 with --push)
- Update after each phase: current `completed`, next `in_progress`
- Provides visual progress tracking in UI

## Output Description

### Mode Banners

**Interactive Mode**:
```
🚀 Full Pipeline (Interactive Mode)

7 phases: init → requirements → design → tasks → impl → complete → steering
(+push with --push flag)
You will be prompted at each phase.
```

**Automatic Mode**:
```
🚀 Full Pipeline (Automatic Mode)

7 phases execute automatically without prompts (8 with --push).
⚠️ Skips all validations and reviews. Implementation may take 10-30 min.
```

### Intermediate Output

After each phase, show brief progress:
```
✅ 1/7 Spec initialized at .blast/specs/{feature}/
✅ 2/7 Requirements generated
✅ 3/7 Design generated
✅ 4/7 Tasks generated ({N} tasks)
✅ 5/7 Implementation complete ({X} tests passing)
✅ 6/7 Feature shipped → inventory updated
✅ 7/7 Steering synced
✅ 8/8 Pushed to origin/{branch} (only with --push)
```

### Final Completion Summary

Provide output in the language specified in `spec.json`:

```
🎉 Full Pipeline Complete!

Feature: {feature-name}
Status: shipped

## Pipeline Results:
- Spec: {X} requirements → {Y} components → {Z} tasks
- Code: {N} files created, {M} tests passing
- Inventory: {K} components registered
- Steering: project memory synced

## Generated Files:
- .blast/specs/{feature}/ (spec.json, requirements.md, design.md, tasks.md)
- src/... (implementation files)
- tests/... (test files)
- .blast/steering/ (updated memory)

⚠️ Full pipeline skipped optional validations:
- /blast:validate-gap — gap analysis
- /blast:validate-design — architecture review
- /blast:validate-impl — implementation validation

For production-critical features, consider running validations manually.
```

## Safety & Fallback

### Argument Parsing
- Use `$ARGUMENTS` to parse (NOT `$1`, `$2`)
- Handle spaces in descriptions correctly
- Handle combination of `--auto`, `--source`, and `--push` in any order

### Error Scenarios

**Template Missing**:
- Report specific missing file, exit with error

**Phase Execution Failed**:
- Stop workflow, show completed phases
- Suggest: "Continue manually from `/blast:{failed-phase} {feature}`"

**User Cancellation** (Interactive Mode):
- Stop gracefully, show completed phases
- Suggest manual continuation with specific next command

### Usage Guidance

**Use `/blast:full --auto`** when:
- Simple feature (CRUD, basic UI, PoC)
- Well-known pattern, low risk
- You trust the pipeline and want hands-off execution

**Use `/blast:full`** (interactive) when:
- Want to review spec before implementation starts
- Moderate complexity, want checkpoints
- First time using blast on a project

**Use `/blast:quick` + manual steps** when:
- Want to review design before committing to impl
- Need gap analysis or design validation
- Complex integrations or security-critical features

**Use standard workflow** (manual step-by-step) when:
- High-stakes production feature
- Need full validation at every gate
- Brownfield project with complex dependencies
