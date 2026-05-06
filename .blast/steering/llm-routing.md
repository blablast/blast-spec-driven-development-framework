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
| security-audit-agent | Sentinel | claude-opus |
| code-review-agent | Compass | claude-sonnet |
| spec-drift-agent | Tracker | claude-haiku |
| steering-agent | Cartographer | claude-sonnet |
| steering-custom-agent | Specialist | claude-haiku |

Zmiana defaults: edytuj frontmatter `model:` w `.claude/agents/blast/{agent}.md`. Ten plik jest **referencyjny**, nie autoritative dla single-agent path.

---

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

| Trigger | Fires when |
|---|---|
| `always` | every invocation of that phase |
| `thorough_flag` | user passes `--thorough` |
| `high_stakes` | `risk_level: high` OR `security_critical: true` OR PR touches sensitive paths |

Per-spec override: `spec.json.debate.{phase}` wins.

### Compositions

```yaml
HYBRID:
 protocol: B # parallel jury, N=2
 jurors: [claude-sonnet-4-6, qwen3.6:latest]
 aggregator: claude-haiku-4-5-20251001

JURY_3_FLASH3:
 protocol: B # parallel jury, N=3
 jurors: [claude-opus-4-6, qwen3.6:latest, gemini-3-flash-preview]
 aggregator: claude-haiku-4-5-20251001
```

### Per-phase config

Validate-{impl,design}-agent's Debate Mode hook reads these YAML blocks. The hook
spawns the debate flow only when `enabled: true` AND the trigger condition is met.

```yaml
debate_config:
 validate-impl:
 enabled: true
 trigger: thorough_flag # fires when --thorough flag passed
 composition: HYBRID
 cost_ceiling_usd: 0.50

 validate-design:
 enabled: true
 trigger: high_stakes # fires when risk_level=high OR security_critical=true
 composition: JURY_3_FLASH3
 cost_ceiling_usd: 1.00

 security:
 enabled: true
 trigger: always # security always uses jury (cross-corpus diversity matters most here)
 composition: JURY_3_FLASH3
 cost_ceiling_usd: 1.50

 review:
 enabled: true
 trigger: high_stakes # PR touches auth/payments/schema/data-mutating
 composition: JURY_3_FLASH3
 cost_ceiling_usd: 1.00
```

Compositions (HYBRID, JURY_3_FLASH3) defined above. To **disable** debate for a phase
without removing config: set `enabled: false`. To **force always**: set `trigger: always`.

### Privacy mode override (`spec.json.privacy: local-only`)

All compositions fall back to local-only via `blast-privacy-gate.py`:
- jurors → `[qwen3.6:latest, qwen3-coder:30b]` (or `[qwen3.6:latest, qwen3-coder:30b, gpt-oss:latest]` for security)
- aggregator → `qwen3.6:latest` (Haiku blocked)
- cost_ceiling_usd → 0.00

