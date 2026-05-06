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

#### Protocol B — Multi-Jury Vote (N=3 default, up to N=4)

1. Dispatch same question to N jurors **in parallel** (Agent calls)
   - Juror 1: `debate-critic` (model=sonnet)
   - Juror 2: `debate-critic` (model=opus, override)
   - Juror 3: external via `blast-llm-bridge` MCP (e.g. ask_local_qwen)
   - Juror 4 (optional): another external (e.g. ask_local_deepseek)
2. Each juror writes own verdict block to scratchpad
3. Spawn `debate-aggregator` agent → tally → final verdict

Total: 4-5 sub-agent calls. Cost: ~40-80k tokens. Latency: dominated by slowest juror.

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

`/blast:debate` is **manual trigger**. For automatic debate during validation phases, configure in `.blast/steering/llm-routing.md`:

```yaml
debate_config:
  validate-design:
    enabled: true
    protocol: A
  validate-impl:
    enabled: false  # default off
  security:
    enabled: true
    protocol: B
    jury_size: 3
```

When config is present, the relevant validation agent (Crucible / Auditor / Sentinel) auto-spawns the debate flow before producing its verdict envelope. Without config, validation runs standard single-agent path (backward compatible).

## Safety & Fallback

- **Spec missing**: STOP with usage example
- **Cost ceiling exceeded mid-protocol**: stop after current round, emit WARN verdict + note
- **Sub-agent failure**: log to scratchpad, continue with reduced jury (Protocol B) or fall back to Judge (Protocols A, C)
- **Round 5 user_call timeout**: leave scratchpad as-is, exit with note "user decision pending"
