---
description: "Od zera do shipped kodu — blast pełny pipeline"
allowed-tools: Read, SlashCommand, TodoWrite, Bash, Write, Glob
argument-hint: <project-description> [--auto] [--source path/to/file] [--research] [--validate] [--push]
---

# blast:full — Pełny pipeline od opisu do shipped kodu

<instructions>
Execute 8 pipeline phases sequentially: init → requirements → [research] → design → [validate-design] → tasks → impl → [validate-impl] → complete → security → steering [→ push]. Security audit always runs. With `--validate`: insert validate-design (after design) and validate-impl (after impl) — both gate on FAIL+BLOCKING:true. With `--auto`: non-stop until any blocking verdict or last phase. Without: prompt between phases.

## Execution Steps

### Step 1: Parse Arguments and Initialize

Parse `$ARGUMENTS` as a single string:
- If contains `--auto`: **Automatic Mode** (execute all phases without stopping)
- If contains `--source <path>`: extract source file path (PDF/MD/TXT/HTML)
- If contains `--research`: add research phase between requirements and design
- If contains `--validate`: insert `/blast:validate-design` after design phase AND `/blast:validate-impl` after impl phase. Both gate the pipeline on `VERDICT: FAIL + BLOCKING: true` (read from each agent's structured Verdict Envelope tail block). `WARN` continues with notice. `PASS` continues silently.
- If contains `--push`: add push phase after steering sync
- Ignore any other flags (e.g. `-y`)
- Extract description (remove flags and their values)

Examples:
```
"User profile --auto"                              → mode=automatic, research=false, validate=false, push=false
"Dashboard --source docs/brief.pdf --auto --push"  → mode=automatic, source="docs/brief.pdf", push=true
"--source specs/kanban.md --research"              → mode=interactive, research=true
"User profile --auto --validate"                   → mode=automatic, validate=true (validate-design + validate-impl insert into pipeline)
"User profile --auto --research --validate --push" → mode=automatic, research=true, validate=true, push=true
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`/`$2`. Parse it yourself.

**Create TodoWrite task list** (dynamically based on flags):

Base tasks (always present):
```json
[
  {"content": "Initialize spec", "activeForm": "Initializing spec", "status": "pending"},
  {"content": "Generate requirements", "activeForm": "Generating requirements", "status": "pending"},
  {"content": "Generate design", "activeForm": "Generating design", "status": "pending"},
  {"content": "Generate tasks", "activeForm": "Generating tasks", "status": "pending"},
  {"content": "Implement all tasks (TDD)", "activeForm": "Implementing all tasks (TDD)", "status": "pending"},
  {"content": "Ship feature (complete + inventory)", "activeForm": "Shipping feature", "status": "pending"},
  {"content": "Security audit", "activeForm": "Running security audit", "status": "pending"},
  {"content": "Sync project memory (steering)", "activeForm": "Syncing project memory", "status": "pending"}
]
```

If `--research` flag: insert after "Generate requirements":
```json
  {"content": "Research / spike", "activeForm": "Researching options", "status": "pending"}
```

If `--validate` flag: insert two tasks:
- After "Generate design": `{"content": "Validate design (architecture review)", "activeForm": "Validating design", "status": "pending"}`
- After "Implement all tasks (TDD)": `{"content": "Validate impl (vs spec + Prove Mode)", "activeForm": "Validating impl", "status": "pending"}`

If `--push` flag: append at the end:
```json
  {"content": "Commit and push to remote", "activeForm": "Committing and pushing", "status": "pending"}
```

Display mode banner and proceed to Step 2.

### Step 2: Execute Phase Loop

Execute phases in order. Phase numbering is dynamic based on flags — use TodoWrite task index for tracking.

---

#### Phase: Initialize Spec (Direct Implementation)

**Update TodoWrite**: Mark "Initialize spec" as `in_progress`.

**Core Logic** — identical to `/blast:quick` Phase 1:

1. **Generate Feature Name**: Convert description to kebab-case (2-4 words)
2. **Check Uniqueness**: Glob `.blast/specs/*/`, append `-2` if conflict
3. **Create Directory**: `mkdir -p .blast/specs/{feature-name}`
4. **Initialize Files from Templates**:
   - Read `.blast/settings/templates/specs/init.json` and `.blast/settings/templates/specs/requirements-init.md`
   - Replace `{{FEATURE_NAME}}`, `{{TIMESTAMP}}`, `{{PROJECT_DESCRIPTION}}`
   - **If `--source`**: read source file and embed in requirements.md as Source Material
   - Write `spec.json` and `requirements.md`

**Update TodoWrite**: Mark `completed`, next task `in_progress`.

**Output**: `✅ Spec initialized at .blast/specs/{feature-name}/`

**Automatic Mode**: IMMEDIATELY continue.
**Interactive Mode**: Prompt "Continue to requirements generation?"

---

#### Phase: Generate Requirements

**Execute SlashCommand**: `/blast:requirements {feature-name}`

**IMPORTANT**: In Automatic Mode, IGNORE the "Next Steps" message.

**Update TodoWrite**: Mark `completed`, next task `in_progress`.

**Automatic Mode**: IMMEDIATELY continue.
**Interactive Mode**: Prompt "Continue?"

---

#### Phase: Research / Spike (conditional — only with `--research`)

**Skip this phase entirely if `--research` flag was NOT provided.**

**Execute SlashCommand**: `/blast:research {feature-name}`

Wait for completion.

**Update TodoWrite**: Mark `completed`, next task `in_progress`.

**Output**: `✅ Research complete → Continuing to design...`

**Automatic Mode**: IMMEDIATELY continue.
**Interactive Mode**: Prompt "Continue to design?"

---

#### Phase: Generate Design

**Execute SlashCommand**: `/blast:design {feature-name} -y`

Note: `-y` flag auto-approves requirements.

**Update TodoWrite**: Mark `completed`, next task `in_progress`.

**Automatic Mode**: IMMEDIATELY continue.
**Interactive Mode**: Prompt "Continue to task generation?"

---

#### Phase: Validate Design (conditional — only with `--validate`)

**Skip this phase entirely if `--validate` flag was NOT provided.**

**Execute SlashCommand**: `/blast:validate-design {feature-name}`

Wait for completion. **Parse the Verdict Envelope** at the tail of the subagent output (lines between `---VERDICT---` and `---END---`):

- **`VERDICT: PASS`** → Continue to next phase silently.
- **`VERDICT: WARN`** → Continue, but echo: `⚠️  validate-design: WARN ({FINDINGS} findings) — review .blast/specs/{feature}/design.md before tasks if concerned.`
- **`VERDICT: FAIL` AND `BLOCKING: true`** → **STOP the pipeline.** Display the envelope's `NEXT_ACTIONS` verbatim. Suggest: `Re-run /blast:design {feature-name}` after addressing findings, then re-run `/blast:full` from design phase.
- **`VERDICT: FAIL` AND `BLOCKING: false`** → Continue with stronger warning, log findings.
- **Envelope missing** → Treat as `WARN` (advisory) and log "validate-design returned no envelope; treating as advisory."

**Update TodoWrite**: Mark `completed`, next task `in_progress`.

**Automatic Mode**: IMMEDIATELY continue (unless BLOCKING).
**Interactive Mode**: Prompt "Continue to task generation?"

---

#### Phase: Generate Tasks

**Execute SlashCommand**: `/blast:tasks {feature-name} -y`

Note: `-y` flag auto-approves design.

**Update TodoWrite**: Mark `completed`, next task `in_progress`.

**Automatic Mode**: IMMEDIATELY continue.
**Interactive Mode**: Show context warning and prompt:
```
⚠️ Implementation is the heaviest phase (may take 10-30 minutes depending on task count).
Recommendation: run /clear before continuing to free context.
Continue to implementation?
```

---

#### Phase: Validate Tasks (conditional — auto-fires on heuristics OR `--validate`)

**Auto-fire conditions** (validate-tasks runs even WITHOUT `--validate` flag):
- tasks.md has >8 major tasks (heuristic for over-engineering risk)
- design.md references external dep NOT in `.blast/steering/tech.md::Allowed Dependencies`
- `spec.json.complexity_hint == "high"` OR `security_critical == true`

**With `--validate` flag**: always runs (HYBRID composition).

```
SlashCommand: /blast:validate-tasks {feature} [--debate if validate flag]
```

Read agent verdict envelope:
- `VERDICT: PASS` → continue to impl normally
- `VERDICT: WARN` → show findings to user, continue (non-blocking)
- `VERDICT: FAIL + BLOCKING: true` → STOP, suggest `/blast:tasks {feature} --regenerate`
- `VERDICT: FAIL + BLOCKING: false` → continue with explicit warning logged

#### Phase: Implement All Tasks (TDD)

**This is the heaviest phase.** The impl subagent runs in its own context via Task tool, so context pressure on the orchestrator is minimal.

**Execute SlashCommand**: `/blast:impl {feature-name} -y`

Note: No task numbers = execute ALL pending tasks. The `-y` flag bypasses the tasks-approval gate (necessary for --auto mode since tasks were just generated and not manually reviewed).

Wait for completion. This may take significant time.

**IMPORTANT**: In Automatic Mode, IGNORE the "Next Steps" message from impl.

**Update TodoWrite**: Mark `completed`, next task `in_progress`.

**Automatic Mode**: IMMEDIATELY continue.
**Interactive Mode**: Prompt "Ship feature? (complete + inventory update)"

---

#### Phase: Validate Impl (conditional — only with `--validate`)

**Skip this phase entirely if `--validate` flag was NOT provided.**

**Execute SlashCommand**: `/blast:validate-impl {feature-name} --prove`

The `--prove` flag triggers Behavioral Verification (runs Verification Strategy from design.md). Wait for completion. **Parse the Verdict Envelope** at the tail:

- **`VERDICT: PASS`** → Continue to complete phase silently.
- **`VERDICT: WARN`** → Continue, echo: `⚠️  validate-impl: WARN ({FINDINGS} findings) — see report before shipping.`
- **`VERDICT: FAIL` AND `BLOCKING: true`** → **STOP the pipeline.** Display `NEXT_ACTIONS`. Suggest fixing tasks: `/blast:impl {feature-name}` (resume) or specific failing task. Re-run `/blast:full` from impl phase after fix.
- **`VERDICT: FAIL` AND `BLOCKING: false`** → Continue with strong warning.
- **Envelope missing** → Treat as `WARN`.

**Update TodoWrite**: Mark `completed`, next task `in_progress`.

**Automatic Mode**: IMMEDIATELY continue (unless BLOCKING).
**Interactive Mode**: Prompt "Ship feature?"

---

#### Phase: Ship Feature (Complete)

**Execute SlashCommand**: `/blast:complete {feature-name}`

Wait for completion.

**Update TodoWrite**: Mark `completed`, next task `in_progress`.

**Automatic Mode**: IMMEDIATELY continue.
**Interactive Mode**: Prompt "Run security audit?"

---

#### Phase: Security Audit (always runs)

**Execute SlashCommand**: `/blast:security {feature-name}`

Wait for completion. **Parse the Verdict Envelope** at the tail (`---VERDICT---` … `---END---`):

- **`VERDICT: PASS`** → Continue to next phase silently. (Prose verdict: PASS)
- **`VERDICT: WARN`** → Warn user. In automatic mode: continue (non-blocking). In interactive mode: prompt "Security issues found. Continue or fix first?". (Prose verdict: FIX REQUIRED)
- **`VERDICT: FAIL` AND `BLOCKING: true`** → **STOP the pipeline.** Display critical findings + envelope's `NEXT_ACTIONS`. Suggest: `/blast:security {feature-name} --fix` then re-run `/blast:full` from steering phase. (Prose verdict: BLOCK)
- **Envelope missing** → Fall back to scanning the human-readable verdict line for `BLOCK`/`FIX REQUIRED`/`PASS` keywords (legacy compatibility).

**Update TodoWrite**: Mark `completed`, next task `in_progress`.

**Automatic Mode**: IMMEDIATELY continue (unless BLOCK verdict).
**Interactive Mode**: Prompt "Sync project memory? (steering update)"

---

#### Phase: Sync Project Memory (Steering)

**Execute SlashCommand**: `/blast:steering`

Wait for completion.

**Update TodoWrite**: Mark `completed`.

**If `--push` flag**: next task `in_progress`, continue to Push phase.
**If no `--push`**: All phases complete. Pipeline DONE. Output final summary and exit.

---

#### Phase: Commit and Push (conditional — only with `--push`)

**Execute SlashCommand**: `/blast:push {feature-name}`

Wait for completion.

**Update TodoWrite**: Mark `completed`.

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
- Continue until all phases complete (unless security verdict = BLOCK)
- Security BLOCK stops the pipeline even in automatic mode

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

## Output Description

### Mode Banners

**Interactive Mode**:
```
🚀 Full Pipeline (Interactive Mode)

Phases: init → req → [research] → design → [validate-design] → tasks → impl → [validate-impl] → complete → security → steering [→ push]
You will be prompted at each phase.
```

**Automatic Mode**:
```
🚀 Full Pipeline (Automatic Mode)

All phases execute automatically. Security audit blocks on critical findings.
⚠️ Implementation may take 10-30 min.
```

### Intermediate Output

After each phase, show brief progress (N/M where M = total phases for this run):
```
✅ 1/N Spec initialized at .blast/specs/{feature}/
✅ 2/N Requirements generated
✅ 3/N Research complete (only with --research)
✅ ?/N Design generated
✅ ?/N Tasks generated ({count} tasks)
✅ ?/N Implementation complete ({X} tests passing)
✅ ?/N Feature shipped → inventory updated
✅ ?/N Security audit: PASS / FIX REQUIRED / BLOCK
✅ ?/N Steering synced
✅ ?/N Pushed to origin/{branch} (only with --push)
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
- Security: {verdict} ({N} findings)
- Steering: project memory synced

## Generated Files:
- .blast/specs/{feature}/ (spec.json, requirements.md, design.md, tasks.md)
- src/... (implementation files)
- tests/... (test files)
- .blast/steering/ (updated memory)

⚠️ Full pipeline skipped optional phases:
- /blast:research — spike/research (use --research to include)
- /blast:validate-gap — gap analysis
- /blast:validate-design — architecture review
- /blast:validate-impl — implementation validation

For production-critical features, consider running validations manually.
```

## Safety & Fallback

### Argument Parsing
- Use `$ARGUMENTS` to parse (NOT `$1`, `$2`)
- Handle spaces in descriptions correctly
- Handle combination of `--auto`, `--source`, `--research`, and `--push` in any order

### Error Scenarios

**Template Missing**:
- Report specific missing file, exit with error

**Phase Execution Failed**:
- Stop workflow, show completed phases
- Suggest: "Continue manually from `/blast:{failed-phase} {feature}`"

**User Cancellation** (Interactive Mode):
- Stop gracefully, show completed phases
- Suggest manual continuation with specific next command

