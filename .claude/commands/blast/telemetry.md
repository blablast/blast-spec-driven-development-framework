---
description: "Telemetry — agreguj logi agent runs, pokaż trends i top features"
allowed-tools: Bash, Read
argument-hint: [--since YYYY-MM-DD] [--feature <name>]
---

# blast:telemetry — Raport z logów agent runs

Agreguje `.blast/logs/agent-runs.jsonl` (i archived) → markdown summary: liczba calls per agent, verdict distribution, gate failure rate, top features, total chars.

**Logi są meta-only** — żadnych promptów, żadnego output content. Tylko shape danych.

## Parse Arguments

Parse `$ARGUMENTS`:
- Empty → all-time report
- `--since YYYY-MM-DD` → tylko wpisy od tej daty
- `--feature <name>` → tylko wpisy dotyczące tego feature

## Execution

Use Bash tool:

```bash
python3 .claude/scripts/blast-telemetry.py {ARGUMENTS}
```

Skrypt:
- Czyta active log + archived `.gz` files
- Filtruje (`--since`, `--feature`)
- Renderuje markdown report do stdout

## Output

Sekcje raportu:

1. **Summary** — total calls, errors, gate blocks, blocking FAILs, prompt/result chars
2. **By Subagent** — tabela: subagent → call count
3. **Verdict Distribution** — PASS / WARN / FAIL counts (jeśli verdict envelope w response)
4. **Top Features by Activity** — feature → call count (top 10)
5. **Notes** — przypomnienie o rotacji i meta-only policy

## Examples

```bash
# All-time
/blast:telemetry

# Last week
/blast:telemetry --since 2026-04-29

# Per feature
/blast:telemetry --feature auth-basic

# Combined
/blast:telemetry --since 2026-04-01 --feature payment-flow
```

## Log Lifecycle

| Stage | Path | Format |
|---|---|---|
| Active | `.blast/logs/agent-runs.jsonl` | JSONL (one record per Agent/Task call) |
| Archived | `.blast/logs/archive/YYYY-Qn.jsonl.gz` | Gzipped JSONL, kwartalnie |

**Rotacja manualna** (gdy active > ~10MB):

```bash
mkdir -p .blast/logs/archive
QUARTER=$(date +%Y-Q$(( ($(date +%-m)-1)/3+1 )))
mv .blast/logs/agent-runs.jsonl ".blast/logs/archive/${QUARTER}.jsonl"
gzip ".blast/logs/archive/${QUARTER}.jsonl"
```

Telemetry script czyta zarówno active jak i archive.

## What's Logged

Per Agent/Task call:

```json
{
  "ts": "2026-05-06T12:34:56Z",
  "tool": "Agent",
  "subagent": "spec-design-agent",
  "feature": "auth-basic",
  "description": "Generate design.md for auth-basic",
  "prompt_chars": 4123,
  "result_chars": 8742,
  "verdict": "PASS",
  "blocking": false,
  "is_error": false,
  "gate_blocked": false
}
```

**Nigdy nie logujemy**:
- Treści promptu / responsa
- User PII
- Sekretów / credentials

## Privacy & Cost

- Plik jest tracked w git (decyzja Runda 1 #4) — cross-machine continuity
- Jeśli sensitive feature names wyciekają → użyj `--feature` filter w lokalnych raportach
- Cost analysis: skoro to meta-only, dolary nie są tu obliczane. Patrz `.blast/steering/cost-policy.md` dla polityki kosztów (placeholder Fala 8.2 — hard limits aktywne post-baseline)

## Następny krok

- Przeglądaj raport regularnie (`/blast:telemetry --since 2026-04-01`)
- Identyfikuj outliers: top features w call count, blocking FAIL trends, gate block rate
- Po 1-2 miesiącach: ustal hard limits w `cost-policy.md` na bazie p95
