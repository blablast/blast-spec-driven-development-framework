# Cost Policy

**Status**: caps poniżej są startem; calibruj na bazie `/blast:telemetry` po 1-2 miesiącach użytkowania.

Filozofia: *tani default, drogie świadomie*. Calibruj caps po 1-2 miesiącach telemetry.

## Soft warnings (active from day 1)

- Każde użycie `model: opus` → log entry w telemetry z `expensive: true`
- Jury z N≥3 → wymaga explicit flag `--jury-large`
- Cost ceiling debate: `debate_max_tokens` w `spec.json` (default 100000)

## Local LLM

Local Ollama calls via `blast-llm-bridge` MCP have cost = $0 w telemetry. Hardware capex ignored.

## Manual override

Każdy hard limit (gdy aktywny) może być pominięty przez:
- `--cost-override` flag w slash command
- Edytowanie tego pliku (commit z uzasadnieniem)
- `spec.json.cost_override: true` (per-spec exemption)

## Hard limits — per-phase ceilings (warning_at / block_at)

| Phase / Composition | warning_at | block_at | Empirical median (spike-3) |
|---|---:|---:|---:|
| Solo Haiku (requirements/tasks/complete) | $0.02 | $0.05 | ~$0.005 |
| Solo Sonnet (validate-*, review) | $0.10 | $0.25 | ~$0.06 |
| Solo Opus (design, control reviews) | $0.30 | $0.75 | ~$0.10 |
| HYBRID validate-impl | $0.20 | $0.50 | ~$0.12 |
| JURY_3_FLASH3 (security, high-stakes) | $0.40 | $1.00 | ~$0.17 |
| `/blast:full` standard spec | $5 | $10 | ~$2 |
| `/blast:full --debate` | $10 | $20 | ~$4 |
| `/blast:full` z security-critical | $15 | $30 | ~$5 |

### Soft warnings (still active)

- Każde użycie `claude-opus-4-6` → telemetry log entry z `expensive: true`
- JURY composition z N≥4 (jeśli kiedyś rozszerzymy) → wymagana flaga `--jury-large`
- Single Agent call >$1 → log + alert
- `/blast:full --auto` >$20 → block z user override

### Free local-only mode (`spec.json.privacy: local-only`)

Wszystkie external LLM calls blocked. Cost = $0 niezależnie od liczby calli. `cost-policy` nie ma zastosowania w tym trybie.
