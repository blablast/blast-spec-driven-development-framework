---
description: "Manual debate trigger — odpal Author/Critic/Judge debate na konkretnym topicu"
allowed-tools: Read, Write, Edit, Bash, Agent, Task, Glob, Grep
argument-hint: <feature> <topic> [--protocol A|B|C|D] [--max-rounds N] [--cost-ceiling N]
---

# blast:debate — Multi-agent debate on a specific topic

Spawn a structured debate (4 protokoły dostępne) na konkretnym topicu w ramach feature. Wynik: scratchpad + verdict envelope.

## Parse Arguments

Parse `$ARGUMENTS`:
- Position 1: `<feature>` (kebab-case, must exist in `.blast/specs/`)
- Position 2: `<topic>` (kebab-case, e.g. `design-soundness`, `security-posture`, `verification-strategy`)
- `--protocol A|B|C|D` (default: A — Critique-Revise-Judge)
- `--max-rounds N` (Protocol C only; default 4)
- `--cost-ceiling N` (token budget cap; default 100000)

Validate:
- Spec dir exists. If not: STOP with usage.
- Spec status is one of `active`, `shipped` (debate na deprecated specs nie ma sensu).
- Topic name passes kebab-case regex.

## Execution

### Step 1: Setup scratchpad

```bash
FEATURE="<feature>"
TOPIC="<topic>"
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DEBATE_DIR=".blast/specs/${FEATURE}/debates"
SCRATCHPAD="${DEBATE_DIR}/${TOPIC}.md"
mkdir -p "${DEBATE_DIR}"

if [ -f "${SCRATCHPAD}" ]; then
  echo "⚠ Scratchpad ${SCRATCHPAD} exists. Append to existing debate? (yes/no)"
  # User input expected here
fi
```

If new debate: load template from `.blast/settings/templates/debates/scratchpad.md`, fill placeholders ({{FEATURE}}, {{TOPIC}}, {{PROTOCOL}}, {{TIMESTAMP}}, ...), write to scratchpad path.

### Step 2: Run protocol

#### Protocol A — Critique-Revise-Judge (default)

1. Spawn `debate-author` agent → write Round 1 entry
2. Spawn `debate-critic` agent → write Round 1 entry
3. Spawn `debate-author` agent → write Round 2 entry (revision)
4. Spawn `debate-critic` agent → write Round 2 entry (response)
5. Spawn `debate-judge` agent → verdict envelope

Total: 5 sub-agent calls. Cost: ~30-60k tokens.

#### Protocol B — Multi-Jury Vote (composition-driven)

**Composition lookup**: read `.blast/steering/llm-routing.md` `### Compositions`
section. The caller (slash command) names the composition (HYBRID, JURY_3_FLASH3,
etc.). Each composition lists `jurors:` entries with one of two wirings:

- `subagent: <name>` → spawn via `Task` tool with `subagent_type: <name>`
- `mcp_tool: <name>` → call MCP tool directly (e.g. `mcp__blast-llm-bridge__<name>`)

**Dispatch rule (CRITICAL — non-negotiable)**: issue ALL juror calls in ONE
message so they execute in parallel. Sequential dispatch defeats the purpose of
Protocol B. Example for JURY_3_FLASH3:

```
[single message contains 3 parallel tool calls]
Task(subagent_type="debate-critic-opus", description="Juror 1 (Opus)", prompt=<topic>)
mcp__blast-llm-bridge__ask_ubuntu_qwen36(prompt=<topic>, system=<juror system>)
mcp__blast-llm-bridge__ask_gemini_3_flash_preview(prompt=<topic>, system=<juror system>)
```

**If a juror's tool is unavailable** (subagent missing, MCP key not set):
- Skip that juror, log to scratchpad: `Juror N (<name>) — UNAVAILABLE: <reason>`
- Composition degrades (e.g. JURY_3_FLASH3 → de-facto JURY_2 if Gemini key missing)
- Aggregator notes the degradation in verdict envelope

**No stand-ins**. If a juror is unavailable, do NOT have your own context
roleplay it as a different model. Either real call or skipped + noted.

**After all jurors return**: aggregator (per composition) consolidates verdicts
and produces final envelope. The aggregator is also a real subagent call (not
roleplay).

Each juror writes its own verdict block to the scratchpad
`.blast/specs/{feature}/debates/{topic}.md` before returning. Aggregator reads
the scratchpad and produces the final tail-block envelope.

Total: N+1 real tool calls (N jurors + 1 aggregator). Latency: dominated by
slowest juror (parallel). Cost depends on composition: HYBRID ≈ 30-60k tokens,
JURY_3_FLASH3 ≈ 60-120k tokens.

#### Protocol C — Round-Robin (max 4 rounds, opt-in only)

Loop:
- Round N=1: Author opening → Critic critique
- Round N=2..4: Author revision → Critic response
- After each round, **stalemate detection** (haiku similarity on last 2 entries each agent)
- Termination on: `## I CONCEDE` from Critic | `## ESCALATE` | round 4 reached | cost ceiling
- If terminated by round 4 + no convergence → trigger Round 5 Synthesis (`debate-aggregator` mode R5)
- If terminated by I CONCEDE: spawn Judge for verdict envelope

Total: 8-10 sub-agent calls. Cost: ~80-150k tokens. Latency: 4-8 min.

#### Protocol D — Devil's Advocate (asymmetric)

1. Spawn `debate-author` (normal mode)
2. Spawn `debate-critic` with `protocol=D` flag (HARD RULE — must find ≥3 weaknesses)
3. Spawn `debate-judge` → verdict (downweighting Critic's reflexive findings)

Total: 3 sub-agent calls. Cost: ~20-40k tokens.

### Step 3: Output

After protocol completes:

```
✓ Debate complete: {feature}/{topic} (Protocol {P})

Scratchpad: .blast/specs/{feature}/debates/{topic}.md
Verdict: PASS | WARN | FAIL | ESCALATE_TO_ROUND_5
Blocking: true | false

Findings resolved: {N}/{M}
Cost: {tokens_used} tokens

Next steps:
  - Review scratchpad
  - If FAIL: address findings, optionally re-run with /blast:debate {f} {topic}
  - If ESCALATE_TO_ROUND_5: orchestrator runs Synthesis & Addenda; user decides
```

## Cost Awareness

| Protocol | Calls | ~tokens | ~time |
|---|---|---|---|
| A | 5 | 30-60k | 1-2 min |
| B (N=3) | 4 | 40-80k | 1-2 min (parallel) |
| C (max 4) | 8-10 | 80-150k | 4-8 min |
| D | 3 | 20-40k | 1 min |

Use `--cost-ceiling N` to cap. Protokoł C respektuje cost ceiling (stop early jeśli przekroczone).

## Examples

```bash
# Quick critique of design (default Protocol A)
/blast:debate auth-basic design-soundness

# Multi-jury for security-critical feature
/blast:debate payment-flow security-posture --protocol B

# Heavy round-robin for contentious architecture decision
/blast:debate billing-engine event-sourcing --protocol C --max-rounds 4

# Devil's advocate for over-confident requirements
/blast:debate user-onboarding requirements-completeness --protocol D
```

## Integration with Validation Phases

`/blast:debate` is **manual trigger**. For automatic debate during validation phases,
the ONLY authoritative config is `.blast/steering/llm-routing.md::debate_config` —
do not duplicate its values here (past copies of that YAML in this file drifted from
the source and caused contradictory semantics).

Current semantics (summary; llm-routing.md wins on any conflict):
- **Debate is opt-in** — solo composition per Model routing unless the user passes
  `--debate` (`trigger: debate_flag`).
- **`security` and `simplify` use `trigger: high_stakes`** — jury fires only on
  `security_critical` / `risk_level: high` / sensitive paths; normal specs run solo.
- Compositions (HYBRID / HYBRID_LOCAL / JURY_3_FLASH3), cost ceilings, and privacy-mode
  fallbacks are all defined in llm-routing.md.

When the trigger condition is met, the relevant validation agent (Crucible / Auditor /
Sentinel) auto-spawns the debate flow before producing its verdict envelope. Otherwise
validation runs the standard single-agent path.

## Safety & Fallback

- **Spec missing**: STOP with usage example
- **Cost ceiling exceeded mid-protocol**: stop after current round, emit WARN verdict + note
- **Sub-agent failure**: log to scratchpad, continue with reduced jury (Protocol B) or fall back to Judge (Protocols A, C)
- **Round 5 user_call timeout**: leave scratchpad as-is, exit with note "user decision pending"
