# LLM Routing Policy

Centralna konfiguracja: która faza używa którego modelu, gdzie debate jest enabled, które ścieżki muszą iść tylko do lokalnego LLM (privacy).

Plik czytany przez:
- Wszystkie blast agents przed wyborem modelu (override domyślnego frontmatter)
- `/blast:debate` przy doborze protokołu i jurorów
- `blast-llm-bridge` MCP (Fala 10) przy routing'u i privacy enforcement
- `blast-privacy-gate.py` hook (Fala 10) przed zewnętrznymi LLM calls

---

## Default routing per agent

(Mapping z Fala 3, single-source-of-truth.)

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
| security-audit-agent | Sentinel | claude-opus |
| code-review-agent | Compass | claude-sonnet |
| spec-drift-agent | Tracker | claude-haiku |
| steering-agent | Cartographer | claude-sonnet |
| steering-custom-agent | Specialist | claude-haiku |

Zmiana defaults: edytuj frontmatter `model:` w `.claude/agents/blast/{agent}.md`. Ten plik jest **referencyjny**, nie autoritative dla single-agent path.

---

## Debate config (Fala 9 — opt-in)

**Default**: pusty. Agentom validate-* / security działa standardowy single-agent path. Aby włączyć debate dla danej fazy, dodaj wpis w sekcji poniżej.

```yaml
debate_config:
  # validate-design:
  #   enabled: true
  #   protocol: A          # A | B | C | D
  #   author_model: opus
  #   critic_model: sonnet
  #   judge_model: haiku
  #
  # validate-impl:
  #   enabled: false
  #
  # security:
  #   enabled: true
  #   protocol: B
  #   jury_size: 3
  #   jury_models:
  #     - claude-opus
  #     - claude-sonnet
  #     - local-qwen3.6:latest    # via blast-llm-bridge MCP (Fala 10)
  #
  # design:
  #   enabled: false        # design itself can be debated, but heavy — opt-in only
  #   protocol: C
  #   max_rounds: 4
```

Jak to działa:
- Agent czyta tę sekcję na starcie
- Jeśli `<phase>.enabled: true` → spawn debate sub-agents zamiast single-agent path
- Verdict envelope nadal jest wymagany (debate kończy się envelopem)
- Wszystko inne (caller, hooks, post-impl) jest niezmienione — backward compatible

Per-spec override: spec.json może mieć `"debate": {"validate-design": {"enabled": false}}` żeby wyłączyć dla konkretnego spec'u.

---

## Privacy patterns (Fala 10)

Format: `glob_pattern   llm=<policy>`

Domyślne (apply do every project):

```
.env*                       llm=local-only
*.pem                       llm=local-only
*.key                       llm=local-only
secrets/**                  llm=local-only
config/production.yml       llm=local-only
*.proprietary               llm=local-only
**/credentials.json         llm=local-only
**/private/**               llm=local-only
```

Per-project additions:

```
# (twoje patterns tutaj — np. compliance-flagged code)
src/billing/legal/**        llm=local-only
docs/customer-pii/**        llm=local-only
```

Polityki:
- `local-only` — file content nie może iść do żadnego cloud LLM (Anthropic, OpenAI, OpenRouter). Tylko Ollama (lokalny cluster).
- `cloud-ok` — domyślnie, brak ograniczeń
- (przyszłe: `redact-only` — automatyczne maskowanie PII przed cloud send)

Privacy hook (`blast-privacy-gate.py`, Fala 10) skanuje paths przed call'ami `ask_anthropic_*` / `ask_openrouter_*` i blokuje gdy match.

---

## Cost annotations (referencyjne)

Patrz `.blast/steering/cost-policy.md` dla pełnej polityki kosztów.

| Operacja | Koszt względny |
|---|---|
| haiku call | 1× |
| sonnet call | 5× |
| opus call | 25× |
| jury N=3 (Protocol B) | 3× single-agent |
| round-robin (Protocol C, full 4 rounds) | ~10× single-agent |
| Round 5 Synthesis & Addenda | +5× pojedynczego protokołu C |
| Local Ollama call | $0 (po hardware) |

---

## Historia zmian

- 2026-05-05: utworzony jako część Fala 9 (debate config) i Fala 10 (privacy patterns + multi-LLM routing)
- (przyszłe: per-Fala updates)


---

## Per-phase routing (post Spike-3, 2026-05-06)

Each blast agent reads this table at startup to override its `model:` frontmatter when needed. Source of truth for "who reviews what".

### Default routing

| Agent / Phase | Default model | Persona | Rationale |
|---|---|---|---|
| `spec-requirements-agent` | claude-haiku-4-5 | Scribe | Templating, structured output, low reasoning |
| `spec-research-agent` | claude-sonnet-4-6 | Oracle | Web search + multi-source synthesis |
| `spec-design-agent` | claude-opus-4-6 | Atlas | Architecture, trade-offs, deepest reasoning |
| `spec-tasks-agent` | claude-haiku-4-5 | Loom | Parsing design.md → ordered task list |
| `spec-tdd-impl-agent` Author | **qwen3-coder:30b** (Ubuntu/5090) | Forge | 246 tok/s, $0, comparable quality to Sonnet on code gen |
| `spec-tdd-impl-agent` Critic (escalation only) | claude-sonnet-4-6 | Forge-Critic | Run only if tests fail or smoke probe fails |
| `validate-gap-agent` | claude-haiku-4-5 | Bridge | Fast cross-check requirements vs research |
| `validate-design-agent` | claude-sonnet-4-6 | Crucible | Deep design audit |
| `validate-impl-agent` | claude-sonnet-4-6 | Auditor | Code review, finds subtle bugs |
| `spec-complete-agent` | claude-haiku-4-5 | Ledger | Update INVENTORY, log changelog |
| `spec-deprecate-agent` | claude-haiku-4-5 | Curator | Mark spec deprecated, log to memory |
| `spec-evolve-agent` | claude-haiku-4-5 | Delta | Generate evolution.md from change description |
| `spec-tiny-agent` | claude-haiku-4-5 | Sprint | One-shot lightweight specs |
| `steering-agent` | claude-sonnet-4-6 | Steward | Codebase scan + steering doc generation |
| `steering-custom-agent` | claude-haiku-4-5 | — | Apply steering template |
| `code-review-agent` | claude-sonnet-4-6 | Reviewer | Standard PR review |
| `security-audit-agent` | **JURY_3_FLASH3** | Jurors | Multi-LLM jury (Opus ‖ qwen3.6 ‖ Gemini-3-Flash → Haiku agg). Highest stakes phase. |

### High-stakes / opt-in escalation

| Trigger | Override |
|---|---|
| `validate-design --thorough` OR `spec.json.risk_level: high` | `validate-design-agent` → JURY_3_FLASH3 |
| `validate-impl --thorough` OR auth/payments/data-mutating in changed files | `validate-impl-agent` → HYBRID (Sonnet ‖ qwen3.6:latest → Haiku judge) |
| `code-review --thorough` OR PR touches sensitive paths | `code-review-agent` → JURY_3_FLASH3 |
| `spec.json.security_critical: true` | All validation phases → JURY_3_FLASH3 |

### Privacy mode (`spec.json.privacy: local-only`)

When privacy flag is set, ALL external LLM calls (Anthropic, Google) are blocked by `blast-privacy-gate.py` hook. Routing falls back to local Ollama:

| Phase | Privacy-mode model |
|---|---|
| Reasoning-heavy phases (design, validate-*) | qwen3.6:latest (5090) |
| Coding (impl) | qwen3-coder:30b (5090) |
| Templating (requirements, tasks, complete) | qwen3.6:latest (5090) |
| Aggregator/judge in HYBRID/JURY | falls back to qwen3.6:latest (no Haiku) |

### Multi-LLM compositions

**HYBRID** (validate-impl --thorough):
```
Author     = qwen3-coder:30b (impl output, frozen)
Critic1    = claude-sonnet-4-6     ┐
                                    ├ parallel
Critic2    = qwen3.6:latest        ┘
Judge      = claude-haiku-4-5 (synthesizes findings → verdict envelope)
```

**JURY_3_FLASH3** (security, high-stakes validate-design):
```
Juror1     = claude-opus-4-6              ┐
Juror2     = qwen3.6:latest               ├ parallel, independent
Juror3     = gemini-3-flash-preview       ┘
Aggregator = claude-haiku-4-5 (deduplicates, ranks, emits verdict envelope)
```

### Models DROPPED post-spike

- ❌ `gemini-2.5-pro` — replaced by `gemini-3-flash-preview` (precision 0.57 vs 0.41, same recall, ~2.5× tańsze)
- ❌ `qwen3-coder-next` (79.7B) — 17.7 tok/s = 14× wolniejsze niż :30b. Z default MODELS w bench. On-demand only.
- ❌ Pełne 4-protokoły debate framework — Spike-3 nie dostarczył dowodów. Asymmetric Pattern A + Pattern B dla high-stakes wystarczą.

### Sources

- Spike-1 verdict: `r_and_d/research/spike-1/README.md`
- Spike-3 verdict: `r_and_d/research/spike-3/README.md`
- Decision detail: `r_and_d/decisions/2026-05-05-sdd-number-one-roadmap.md` (Spike-3 verdict section)


---

## debate_config — declarative composition for `/blast:debate`

Read by `validate-{impl,design}-agent`, `security-audit-agent`, `code-review-agent` via Debate Mode hook. Used by `/blast:debate` for juror selection.

### Trigger semantics

| Trigger | Fires when |
|---|---|
| `always` | every invocation of that phase |
| `thorough_flag` | user passes `--thorough` |
| `high_stakes` | `risk_level: high` OR `security_critical: true` OR PR touches sensitive paths |

Per-spec override: `spec.json.debate.{phase}` wins.

### Compositions (post Spike-3)

```yaml
HYBRID:
  protocol: B   # parallel jury, N=2
  jurors: [claude-sonnet-4-6, qwen3.6:latest]
  aggregator: claude-haiku-4-5-20251001

JURY_3_FLASH3:
  protocol: B   # parallel jury, N=3
  jurors: [claude-opus-4-6, qwen3.6:latest, gemini-3-flash-preview]
  aggregator: claude-haiku-4-5-20251001
```

### Per-phase config

| Phase | Composition | Trigger | Cost ceiling |
|---|---|---|---:|
| `validate-impl` | HYBRID | thorough_flag | $0.50 |
| `validate-design` | JURY_3_FLASH3 | high_stakes | $1.00 |
| `security` | JURY_3_FLASH3 | always | $1.50 |
| `review` | JURY_3_FLASH3 | high_stakes | $1.00 |

### Privacy mode override (`spec.json.privacy: local-only`)

All compositions fall back to local-only via `blast-privacy-gate.py`:
- jurors → `[qwen3.6:latest, qwen3-coder:30b]` (or `[qwen3.6:latest, qwen3-coder:30b, gpt-oss:latest]` for security)
- aggregator → `qwen3.6:latest` (Haiku blocked)
- cost_ceiling_usd → 0.00

### Empirical baselines (Spike-3, 2026-05-06) — regression detection

| Composition | Recall | Precision | F1 | Cost/spec | Latency/spec |
|---|---:|---:|---:|---:|---:|
| HYBRID | 0.94 | 0.45 | 0.61 | $0.12 | 130s |
| JURY_3_FLASH3 | 0.94 | 0.57 | 0.71 | $0.17 | 141s |
| solo Sonnet (validate-impl default) | 0.89 | 0.47 | 0.62 | $0.06 | 42s |
| solo Opus (CONTROL) | 0.89 | 0.57 | 0.70 | $0.10 | 45s |

If recall drops >0.10 from baseline → investigate prompt regression, model swap, or context contamination.
