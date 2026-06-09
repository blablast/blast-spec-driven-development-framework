---
description: "Gdzie jesteśmy? blast pokazuje status i postęp"
allowed-tools: Bash, Read, Glob, Write, Edit, MultiEdit, Update, mcp__blast-llm-bridge__ask_ubuntu_qwen36, mcp__blast-llm-bridge__ask_ubuntu_lfm25
argument-hint: <feature-name>
---

# blast:status — Raport sytuacyjny

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Detect `--digest` flag (boolean — autonomous-runs audit digest, see below)
- Strip remaining flags
- Extract feature name from remaining tokens (kebab-case identifier)
- If empty after stripping → list all specs

Examples:
```
"zoo-garden"     → feature=zoo-garden
""               → feature=null (list all specs)
"--digest"       → digest mode (all specs)
"zoo-garden -y"  → feature=zoo-garden (flag ignored)
```

## Digest mode (`--digest`) — audit instead of supervision

Compensating control for risk-tiered autonomy: the human reviews AFTER the fact what ran
WITHOUT them. Gather (Bash/Read):
1. `.blast/logs/auto-approvals.jsonl` — what auto-approved since last digest (count per feature/phase)
2. `.blast/specs/*/verdicts/*.json` — latest verdicts per phase (PASS/WARN/FAIL + findings)
3. `.blast/logs/agent-runs.jsonl` — escalation rates (local_ok vs escalated), error rate, debate compositions fired
4. shipped features since last digest (INVENTORY / spec.json.completed_at)

Then produce a compact digest via the mechanical lane (NOT your own model):
`mcp__blast-llm-bridge__ask_ubuntu_lfm25(prompt=<raw data + "summarize as 10-line audit digest:
shipped, auto-approved, verdicts, escalation rate, anomalies">)` — $0, ~580 tok/s.
If the bridge is down, summarize yourself (shorter). Flag anomalies LOUDLY:
auto-approved phase followed by FAIL verdict, cloud escalation >10%, security WARN+.

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


---

## Step 4 — Project Pulse (multi-spec mode, Qwen synthesis)

**ONLY runs when invoked WITHOUT feature argument** (i.e., listing all specs). Skip entirely for per-feature status.

Rationale: when listing 3+ specs, raw per-spec dashboards don't answer "what's the team focused on right now? what's stalled? what's next?". Qwen3.6:latest local synthesizes this in 5-10s for $0 — perfect for daily-check-in cadence.

### When to skip

- Single feature mode (user passed `<feature>` arg) → skip Step 4 entirely
- Specs count < 3 → skip (single project, narrative redundant with raw list)
- MCP bridge unreachable → skip with warning, return raw list only
- User passed `--no-pulse` flag → skip

### Synthesis prompt for Qwen

After rendering individual spec entries, gather summary data and call Qwen via MCP:

```python
# Pseudo
specs_summary = []
for spec_dir in glob('.blast/specs/*/'):
    sj = json.load(open(f'{spec_dir}/spec.json'))
    tasks_done, tasks_total = parse_task_progress(f'{spec_dir}/tasks.md')
    specs_summary.append({
        'name': sj['feature_name'],
        'phase': sj['phase'],
        'status': sj['status'],
        'tasks': f'{tasks_done}/{tasks_total}',
        'last_modified_days_ago': days_since_mtime(spec_dir),
        'approvals': sj.get('approvals', {}),
    })

prompt = f"""You are a project status synthesizer. Below is a structured list of all active specs in a blast project. Produce a SHORT (max 8 lines) project pulse covering:
1. What is the team's primary focus right now? (1 line)
2. What spec is closest to shipping? (1 line)
3. What spec is stalled — at the same phase for 5+ days, or unapproved for 3+ days? Suggest concrete next-action command. (1-3 lines)
4. Any anomalies — phase mismatch, status mismatch, tasks done but not completed? (1-2 lines)

Specs data:
{json.dumps(specs_summary, indent=2)}

OUTPUT RULES:
- Respond in {primary_language} (read from .blast/settings/spec.json or default 'pl')
- No greeting, no preamble, no closing remarks
- Use markdown bullet list
- Cite spec names and concrete commands (e.g. /blast:approve auth-oauth requirements)
- End with literal line: ---END---
"""

result = mcp__blast-llm-bridge__ask_ubuntu_qwen36(prompt=prompt, max_tokens=2048)
```

### Output format

After the raw spec list, append:

```
---
## 🔍 Project Pulse (Qwen synthesis, $0)

{Qwen narrative output, max 8 lines}

---
*Pulse generated by local LLM via `mcp__blast-llm-bridge__ask_ubuntu_qwen36`. Re-run with --no-pulse to skip. Model behind the tool is configured in `.claude/mcp/blast-llm-bridge.py`.*
```

### Privacy mode

`spec.json.privacy: local-only` already routes Qwen via MCP (local), so privacy mode works transparently. No external calls.

### Performance budget

| Specs count | Expected Qwen latency | Total `/blast:status` latency |
|---|---:|---:|
| 3-5 | ~5s | ~6s |
| 5-10 | ~8s | ~10s |
| 10+ | ~12s | ~15s |

Beyond 20 specs: skip Step 4, render raw list only (Qwen prompt becomes too long, narrative loses focus).
