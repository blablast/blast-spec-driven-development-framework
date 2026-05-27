# Cost Policy

**Status**: szkielet (Fala 8.2). Hard limits **DISABLED** dopóki nie zbierzemy 1-2 miesięcy historycznych danych z `/blast:telemetry`.

Filozofia: *tani default, drogie świadomie*. Patrz roadmap `r_and_d/decisions/2026-05-05-sdd-number-one-roadmap.md` sekcja 9.

## Hard limits (DISABLED — placeholder)

```
# Pojedynczy spec full pipeline:
#   warning_at: $5
#   block_at:   $10
#
# /blast:full --auto:
#   block_at:   $20
#
# Single Agent call:
#   warning_at: $1
#
# Jury N>3 (Pattern B):
#   require_flag: --jury-large
```

Po zebraniu danych (1-2 miesiące): ustaw `warning_at` na p75 historycznych, `block_at` na p95.

## Soft warnings (active from day 1)

- Każde użycie `model: opus` → log entry w telemetry z `expensive: true`
- Jury z N≥3 → wymaga explicit flag `--jury-large` (Fala 9)
- Cost ceiling debate: `debate_max_tokens` w `spec.json` (default 100000, Fala 9)

## What counts as "expensive"

| Operacja | Tier | Default policy |
|---|---|---|
| haiku call | cheap | always allowed |
| sonnet call | normal | always allowed |
| opus call | expensive | log + telemetry mark |
| jury N=3 | expensive | log + warn |
| jury N=4+ | very-expensive | require `--jury-large` |
| Round-robin debate (Protocol C, max 4 rounds) | very-expensive | require `--debate` flag |
| Round 5 Synthesis & Addenda | very-expensive | only when stalemate detected |

## Local LLM impact

- Local calls (Ollama via `blast-llm-bridge` MCP) → cost = $0 w telemetry
- Hardware koszt jest IGNORED (decyzja Runda 1 #5)
- W praktyce: validate-* z lokalnym critic → darmowe, debate cross-provider (Claude vs Qwen) → tylko Claude side liczy się w $

## Privacy mode i koszt

- Privacy-flagged paths (patrz `.blast/steering/llm-routing.md`, Fala 10) → wymuszają local-only
- Privacy mode = również cost control: nie ma jak skierować do drogich cloud modeli

## Calibration roadmap

- **Tydzień 1-4**: telemetry collection only, brak hard limits
- **Tydzień 5-8**: review p25/p50/p75/p95 dla single feature spec, single Agent call, debate session
- **Tydzień 9+**: enable hard limits w tym pliku, edytuj sekcję "Hard limits" z konkretnymi liczbami
- **Co miesiąc po enable**: revisit limits, tighten/relax na bazie observed pattern

## Manual override

Każdy hard limit (gdy aktywny) może być pominięty przez:
- `--cost-override` flag w slash command
- Edytowanie tego pliku (commit z uzasadnieniem)
- `spec.json.cost_override: true` (per-spec exemption)

## Historia decyzji

- 2026-05-05: skeleton placeholder, decyzja Runda 3 #13 (hard limits aktywne post-baseline)
- (przyszłe): updates po review telemetry


---

## Recalibrated caps (post Spike-3, 2026-05-06)

Spike-3 dał real numbers per call. Caps poniżej oparte na empirycznych medianach + bufor.

### Per-phase ceilings (warning_at / block_at)

| Phase / Composition | warning_at | block_at | Empirical median (spike-3) |
|---|---:|---:|---:|
| Solo Haiku (requirements/tasks/complete) | $0.02 | $0.05 | ~$0.005 |
| Solo Sonnet (validate-*, review) | $0.10 | $0.25 | ~$0.06 |
| Solo Opus (design, control reviews) | $0.30 | $0.75 | ~$0.10 |
| HYBRID validate-impl | $0.20 | $0.50 | ~$0.12 |
| JURY_3_FLASH3 (security, high-stakes) | $0.40 | $1.00 | ~$0.17 |
| `/blast:full` standard spec | $5 | $10 | ~$2 |
| `/blast:full --thorough` | $10 | $20 | ~$4 |
| `/blast:full` z security-critical | $15 | $30 | ~$5 |

### Soft warnings (still active)

- Każde użycie `claude-opus-4-6` → telemetry log entry z `expensive: true`
- JURY composition z N≥4 (jeśli kiedyś rozszerzymy) → wymagana flaga `--jury-large`
- Single Agent call >$1 → log + alert
- `/blast:full --auto` >$20 → block z user override

### Hard limits aktywowane od 2026-05-06

Po Spike-3 mamy wystarczające dane historyczne żeby ustawić warning_at na p75 i block_at na p95. Limits powyżej zaktualizowane do tych poziomów.

### Free local-only mode (`spec.json.privacy: local-only`)

Wszystkie external LLM calls blocked. Cost = $0 niezależnie od liczby calli. `cost-policy` nie ma zastosowania w tym trybie.
