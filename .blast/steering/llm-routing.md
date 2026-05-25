# LLM Routing Policy

Centralna konfiguracja: która faza używa którego modelu, gdzie debate jest enabled, które ścieżki muszą iść tylko do lokalnego LLM (privacy).

Plik czytany przez:
- Wszystkie blast agents przed wyborem modelu (override domyślnego frontmatter)
- `/blast:debate` przy doborze protokołu i jurorów
- `blast-llm-bridge` MCP przy routing'u i privacy enforcement
- `blast-privacy-gate.py` hook przed zewnętrznymi LLM calls

---

## Default routing per agent

| Agent | Persona | Default model |
|---|---|---|
| spec-design-agent | Atlas | claude-opus |
| spec-tdd-impl-agent | Forge | claude-sonnet |
| spec-tasks-agent | Loom | claude-haiku |
| spec-requirements-agent | Scribe | claude-haiku |
| spec-tiny-agent | Sprint | claude-haiku |
| spec-research-agent | Oracle | claude-sonnet |
| spec-complete-agent | Ledger | claude-haiku |
| spec-evolve-agent | Delta | claude-haiku |
| spec-deprecate-agent | Curator | claude-haiku |
| validate-gap-agent | Bridge | claude-sonnet |
| validate-design-agent | Crucible | claude-sonnet |
| validate-impl-agent | Auditor | claude-sonnet |
| validate-tasks-agent | Pragmatist | claude-sonnet |
| simplify-agent | Occam | claude-sonnet |
| security-audit-agent | Sentinel | claude-opus |
| code-review-agent | Compass | claude-sonnet |
| spec-drift-agent | Tracker | claude-haiku |
| steering-agent | Cartographer | claude-sonnet |
| steering-custom-agent | Specialist | claude-haiku |

Zmiana defaults: edytuj frontmatter `model:` w `.claude/agents/blast/{agent}.md`. Ten plik jest **referencyjny**, nie autoritative dla single-agent path.

---


## Tiered impl routing (Spike-4 verdict)

`spec-tdd-impl-agent` (Forge) uses tiered model selection — empirical evidence (Spike-4, 2026-05-07) shows qwen3-coder:30b is competitive with claude-sonnet on most tasks, but pozostaje w tyle on async-heavy code.

```yaml
spec-tdd-impl-agent:
  default_model: qwen3-coder:30b      # via mcp__blast-llm-bridge__ask_ubuntu_qwen3_coder
  escalate_to: claude-sonnet-4-6
  escalation_triggers:
    - tasks_md_contains:
        - "async"
        - "asyncio"
        - "concurrent.futures"
        - "trio"
        - "anyio"
    - design_complexity_high:
        # design.md has >8 components OR >3 classes with state
    - flag_passed: "--debate"
    - spec_json:
        complexity_hint: "high"
        security_critical: true
```

Empirical baselines (Spike-4):
- qwen pass rate: 30/30 (100%) across 5 tasks
- qwen composite quality: 3.80/5
- qwen async-task quality: 2.6/5 (significant drop, looks_correct: false)
- sonnet composite quality: 4.00/5
- sonnet async-task quality: 3.6/5 (still has correctness concerns)

Cost trade-off per impl phase:
- Default (qwen): $0, ~4× faster than sonnet
- Escalated (sonnet): ~$0.04 per task, +0.5-1.0 composite quality

If pattern repeats across more specs, validate via `/blast:learn --routing` periodically.

## Privacy patterns

Format: `glob_pattern llm=<policy>`

Domyślne (apply do every project):

```
.env* llm=local-only
*.pem llm=local-only
*.key llm=local-only
secrets/** llm=local-only
config/production.yml llm=local-only
*.proprietary llm=local-only
**/credentials.json llm=local-only
**/private/** llm=local-only
```

Per-project additions:

```
# (twoje patterns tutaj — np. compliance-flagged code)
src/billing/legal/** llm=local-only
docs/customer-pii/** llm=local-only
```

Polityki:
- `local-only` — file content nie może iść do żadnego cloud LLM (Anthropic, OpenAI, OpenRouter). Tylko Ollama (lokalny cluster).
- `cloud-ok` — domyślnie, brak ograniczeń
- (przyszłe: `redact-only` — automatyczne maskowanie PII przed cloud send)

Privacy hook (`blast-privacy-gate.py`) skanuje paths przed call'ami `ask_anthropic_*` / `ask_openrouter_*` i blokuje gdy match.

---

## debate_config — declarative composition for `/blast:debate`

Read by `validate-{impl,design}-agent`, `security-audit-agent`, `code-review-agent` via Debate Mode hook. Used by `/blast:debate` for juror selection.

### Trigger semantics

**Debate is the DEFAULT for validation phases (SOTA #1 stance).** User passes `--no-debate` to use solo composition instead.

| Trigger | Fires when |
|---|---|
| `always` | every invocation of that phase (debate non-negotiable, e.g., security) |
| `validate_flag_unless_no_debate` | when `--validate` triggers the phase AND user did NOT pass `--no-debate` |
| `auto_or_validate_unless_no_debate` | auto-fire heuristic OR `--validate` flag, debate unless `--no-debate` |
| `research_flag_unless_no_debate` | when `--research` flag passed, debate unless `--no-debate` |
| `high_stakes` | `risk_level: high` OR `security_critical: true` OR PR touches sensitive paths (always debate, no opt-out) |

Per-spec override: `spec.json.debate.{phase}` wins.

### Compositions

Each juror entry has TWO parts: logical model name (for documentation) and the
**actual invocation** (subagent name OR MCP tool name) that `debate.md` Protocol B
must call. If `mcp_tool` is missing or its API key is unset, the juror falls back
to the named subagent (which runs as Sonnet by default unless its own frontmatter
overrides `model:`).

```yaml
HYBRID:
  protocol: B   # parallel jury, N=2 — single message, parallel tool calls
  jurors:
    - name: claude-sonnet-4-6
      subagent: debate-critic           # spawned via Task tool (real Sonnet)
    - name: qwen3.6:latest
      mcp_tool: ask_ubuntu_qwen36       # real local Ollama via blast-llm-bridge
  aggregator:
    name: claude-haiku-4-5-20251001
    subagent: debate-aggregator          # spawned via Task tool (uses haiku model)

JURY_3_FLASH3:
  protocol: B   # parallel jury, N=3 — single message, parallel tool calls
  jurors:
    - name: claude-opus-4-6
      subagent: debate-critic-opus      # spawned via Task tool (model: opus in frontmatter)
    - name: qwen3.6:latest
      mcp_tool: ask_ubuntu_qwen36       # real local Ollama via blast-llm-bridge
    - name: gemini-3-flash-preview
      mcp_tool: ask_gemini_3_flash_preview   # real Gemini API via blast-llm-bridge
                                              # requires GEMINI_API_KEY in .env or os.environ
                                              # if missing → juror skipped, jury degrades to N=2
  aggregator:
    name: claude-haiku-4-5-20251001
    subagent: debate-aggregator          # spawned via Task tool (uses haiku model)
```

**Truth-in-advertising note**: prior runs of `/blast:debate` with JURY_3_FLASH3
produced "stand-in" jurors (Sonnet pretending to be Opus / Gemini) when the
underlying subagents/MCP tools weren't wired. The schema above makes the wiring
explicit so debate.md MUST call the named subagent or MCP tool — not roleplay it
in its own context. If a tool is unavailable, the debate output must say so.

### Per-phase config

Validate-{impl,design}-agent's Debate Mode hook reads these YAML blocks. The hook
spawns the debate flow only when `enabled: true` AND the trigger condition is met.

```yaml
debate_config:
  validate-impl:
    enabled: true
    trigger: debate_default       # SOTA #1: debate ON by default; downgrade only if --no-debate flag passed
    composition: HYBRID
    cost_ceiling_usd: 0.50

  validate-tasks:
    enabled: true
    trigger: debate_default       # SOTA #1: debate ON by default; downgrade only if --no-debate flag passed
    composition: HYBRID
    cost_ceiling_usd: 0.40

  validate-design:
    enabled: true
    trigger: debate_default       # SOTA #1: debate ON by default; downgrade only if --no-debate flag passed
    composition: JURY_3_FLASH3
    cost_ceiling_usd: 1.00

  security:
    enabled: true
    trigger: always               # security always uses jury (cross-corpus diversity matters most here)
    composition: JURY_3_FLASH3
    cost_ceiling_usd: 1.50

  review:
    enabled: true
    trigger: debate_default       # SOTA #1: debate ON by default; downgrade only if --no-debate flag passed
    composition: JURY_3_FLASH3
    cost_ceiling_usd: 1.00

  simplify:
    enabled: true
    trigger: high_stakes          # solo Sonnet by default (hygiene step, not a gate); debate only on auth/payments/schema or explicit --debate
    composition: HYBRID
    cost_ceiling_usd: 0.40
```

Compositions (HYBRID, JURY_3_FLASH3) defined above. **Trigger semantics**:
- `debate_default` — SOTA #1 default: fire debate UNLESS the calling slash command injected `No-debate: true` into the agent prompt (user passed `--no-debate`).
- `always` — fire debate unconditionally (e.g. security; ignores --no-debate).
- `high_stakes` — fire only when risk_level=high or security_critical=true (legacy; prefer `debate_default`).

To **disable** debate for a phase without removing config: set `enabled: false`. To **force always-on** (ignore --no-debate): set `trigger: always`.

### Privacy mode override (`spec.json.privacy: local-only`)

All compositions fall back to local-only via `blast-privacy-gate.py`:
- jurors → `[qwen3.6:latest, qwen3-coder:30b]` (or `[qwen3.6:latest, qwen3-coder:30b, gpt-oss:latest]` for security)
- aggregator → `qwen3.6:latest` (Haiku blocked)
- cost_ceiling_usd → 0.00

