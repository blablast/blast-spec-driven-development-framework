---
description: "Pomoc blast — lista komend, workflow, przykłady"
allowed-tools: Read, Glob
argument-hint: [command-name]
---

# blast:help — Przewodnik po systemie

<instructions>
## Core Task
Display help information about blast commands. If a specific command name is provided, show detailed help for that command. Otherwise, show overview of all commands.

## Execution Steps

### Step 1: Parse Arguments

- If `$ARGUMENTS` is empty → show **full help** (overview + all commands)
- If `$ARGUMENTS` contains a command name → show **detailed help** for that command

Valid command names (with or without `blast:` prefix):
`steering`, `steering-custom`, `init`, `requirements`, `research`, `design`, `tasks`, `impl`, `complete`, `approve`, `evolve`, `graph`, `drift`, `lint`, `telemetry`, `debate`, `deprecate`, `quick`, `full`, `tiny`, `review`, `security`, `push`, `status`, `validate-gap`, `validate-design`, `validate-impl`, `help`

### Step 2: Generate Help Output

#### Full Help (no arguments)

Output this reference card:

```
🚀 blast — Spec-Driven Development by Błażej Strus

WORKFLOW (od zera do kodu):
  /blast:steering                  Inicjalizacja pamięci projektu (raz)
  /blast:init "opis"               Nowy ficzer → folder + metadane
  /blast:requirements {f}          Wymagania w formacie EARS
  /blast:research {f} [--deep]     Spike/research — opcje, porównania, wnioski
  /blast:design {f}                Design techniczny
  /blast:tasks {f}                 Plan implementacji
  /blast:impl {f} [taski] [-y]     Implementacja TDD + post-impl audyt (smoke→requirements→verification→test cleanup→final lint)
  /blast:approve {f} <phase>       Klepnięcie fazy (requirements|design|tasks)
  /blast:complete {f}              Ship! → inventory + retrospekcja + steering sync
  /blast:evolve {f} "<change>"     Delta-spec dla shipped feature (iteracja, breaking change, refactor)

SKRÓTY:
  /blast:tiny "opis"               Fast path dla małych ficzerów (spec + impl, 1 strzał)
  /blast:tiny "opis" --auto        Tiny bez confirm gate przed impl
  /blast:quick "opis"              Spec w jednym (init→req→design→tasks)
  /blast:quick "opis" --auto       Spec pełny automat
  /blast:quick --research          Spec z research phase
  /blast:full "opis"               Pełny pipeline (spec + impl + ship + security)
  /blast:full "opis" --auto        Pipeline pełny automat
  /blast:full --auto --validate    Pipeline + validate-design + validate-impl (verdict-gated)
  /blast:full --research --push    Pipeline z research i pushem
  /blast:full --source file --auto Pipeline z pliku, automat

JAKOŚĆ KODU:
  /blast:review {f}                Code review vs zasady (Clean Code, SOLID, DRY...)
  /blast:review {f} --fix          Code review + automatyczne poprawki
  /blast:review                    Review całego codebase
  /blast:security {f}              Audyt bezpieczeństwa (OWASP, secrets, injection)
  /blast:drift {f}                 Wykryj drift między shipped spec a kodem (severity NONE/INFO/WARN/CRITICAL)
  /blast:lint {f|--all}            Deterministyczny linter speców (EARS, IDs, traceability, V.S.)
  /blast:debate {f} {topic}        Multi-agent debate (4 protokoły A/B/C/D, scratchpad-based)
  /blast:security {f} --fix        Audyt + auto-fix bezpiecznych poprawek
  /blast:security --all            Skan całego codebase

WALIDACJE (opcjonalne):
  /blast:validate-gap {f}          Analiza luki (przed design)
  /blast:validate-design {f}       Review architektury (po design)
  /blast:validate-tasks {f}        KISS + SOTA review tasks.md (po tasks, przed impl)
  /blast:validate-impl {f}         Walidacja impl vs spec (po impl)
  /blast:validate-impl {f} --prove Walidacja + odpalenie Verification Strategy z design.md

GIT:
  /blast:push [feature]            Commit + push (smart staging, English title)
  /blast:full "opis" --push        Pipeline + push na koniec

ZARZĄDZANIE:
  /blast:status {f}                Status i postęp specyfikacji
  /blast:graph [f]                 Cross-spec dependency graph + status dashboard
  /blast:telemetry [--since|--feature]  Raport agent runs (calls/verdicts/top features, meta-only)
  /blast:learn [--lessons|--calibrate|--routing|--refresh-sota|--all]
                                   Self-improvement: aggregate lessons / cost cal / routing obs / SOTA staleness
                                   Auto co 5 shipped specs via /blast:complete Step 7
  /blast:deprecate {f}             Wycofanie ficzera z migration guide
  /blast:steering-custom           Dodatkowe pliki steering (API, DB...)
  /blast:help [komenda]            Ta pomoc

GRAF PRZEJŚĆ:

  ┌──────────────┐
  │  steering    │  (raz na projekt)
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐    --source
  │    init      │◄── PDF/MD/TXT
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │ requirements │
  └──────┬───────┘
         │
         ├──────────────┐ (opcjonalnie)
         ▼              ▼
  ┌─────────────┐ ┌──────────────┐
  │  research   │ │ validate-gap │
  └──────┬──────┘ └──────────────┘
         │
         ▼
  ┌─────────────┐
  │   design    │
  └──────┬──────┘
         │
         ├──────────────┐ (opcjonalnie)
         ▼              ▼
  ┌─────────────┐ ┌─────────────────┐
  │    tasks    │ │ validate-design │
  └──────┬──────┘ └─────────────────┘
         │
         ▼
  ┌─────────────┐
  │    impl     │◄─┐ (iteruj po taskach)
  └──────┬──────┘  │
         │         │
         ├─────────┘
         │
         ├──────────────┐ (opcjonalnie)
         ▼              ▼
  ┌─────────────┐ ┌────────────────┐
  │  complete   │ │ validate-impl  │
  └──────┬──────┘ └────────────────┘
         │
         ▼
  ┌─────────────┐
  │  steering   │  (sync pamięci)
  └──────┬──────┘
         │
         ▼ (opcjonalnie)
  ┌─────────────┐
  │  security   │  (audyt bezpieczeństwa)
  └─────────────┘

  /blast:quick = init → req → [research] → design → tasks
  /blast:full  = init → req → [research] → design → [validate-design] → tasks → impl → [validate-impl] → complete → security → steering [→ push]
  /blast:tiny  = init → tiny-agent (compressed spec, self-approve) → impl

FLAGI:
  -y                               Auto-approve / bypass approval gate (design, tasks, impl)
  --sequential                     Wymuś sekwencyjne wykonanie tasków, ignoruj `(P)` markery (impl)
  --max-parallel N                 Cap concurrency dla wav `(P)`, default 4, range 1..8 (impl)
  --auto                           Pełny automat (quick, full)
  --source path/to/file            Importuj opis z pliku (init, quick, full)
  --fix                            Auto-fix (review)
  --push                           Git push po pipeline (full)
  --research                       Research phase (quick, full)
  --validate                       Insert validate-design + validate-impl --prove (full); blokuje na FAIL+BLOCKING:true
  --deep                           Dogłębny research (research)
  --all                            Skan całego codebase (security)
  --prove                          Behavioral verification — odpal Verification Strategy z design.md (validate-impl)

PAMIĘĆ:
  steering/     → pamięć projektu (product, tech, structure, inventory, research)
  tech.md       → Stack Fingerprint + Canonical Commands + Gotchas/Incidents/AI Guidance
  product.md    → purpose + Invariants + AI Guidance (domain-facing)
  specs/        → specyfikacje ficzerów (requirements, design, tasks)
  spec.json     → metadane: phase, status, provides, dependencies
  /blast:complete → retrospekcja: lekcje trafiają do tech.md/product.md (near-neighbor check, refine/supersede/new)

QUALITY GATES (przed fazą):
  Automatyczne kontrole jakości przed każdą fazą.
  Reguły: .blast/settings/rules/quality-gates.md

APPROVAL GATES (defense in depth):
  Markdown gate — slash command czyta spec.json, fail-fast z czytelnym błędem:
    /blast:design feat       → STOP jeśli requirements.approved=false (bez -y)
    /blast:tasks  feat       → STOP jeśli design.approved=false
    /blast:impl   feat       → STOP jeśli tasks.approved=false
  Bypass: -y (auto-approves prior phase) lub /blast:approve {f} <phase>
  Hard gate — PreToolUse hook .claude/hooks/blast-approval-gate.py
    Egzekwuje to samo na poziomie SDK (exit 2). Działa nawet gdy markdown gate ominięty.
    Bypass paths: prompt z "Auto-approve: true", spec.tiny=true, non-blast subagent.
    Disable awaryjnie: usuń sekcję `hooks` z .claude/settings.json.

POST-IMPL CHECKS (auto po /blast:impl gdy wszystkie taski [x]):
  4a Smoke Test           — design.md::Verification Strategy → tech.md::smoke_command → generic
  4b Requirements check   — sub-agent (opus) sprawdza czy każdy req ma pokrycie w plikach/kodzie
  4c Verification probe   — test + e2e probe z design.md::Verification Strategy
  4d Test Relevance Audit — sub-agent (haiku) audytuje testy: KEEP/DELETE/REFACTOR vs requirements
  4e Final Lint Pass      — ruff/eslint na zmodyfikowanych plikach (cross-task sweep)
  Dowolny step ❌ → impl nie marka feature jako done; user widzi konkretny błąd.

Szczegóły komendy: /blast:help <nazwa-komendy>
Pełna dokumentacja: .blast/README.md
```

#### Detailed Help (specific command)

Read the command file from `.claude/commands/blast/{command}.md` and extract:

1. **Komenda**: Full command syntax with arguments
2. **Opis**: From `description` in frontmatter
3. **Argumenty**: From `argument-hint` + parse instructions section
4. **Co robi**: 3-5 bullet summary of execution steps
5. **Przykłady**: 2-3 usage examples
6. **Powiązane komendy**: What comes before/after in workflow
7. **Flagi**: Available flags (if any)

Format as concise reference (under 200 words).

Example for `/blast:help init`:
```
📋 /blast:init <opis> [--source path/to/file]

Inicjalizuje nowy spec — tworzy folder i metadane.

ARGUMENTY:
  <opis>              Opis ficzera (wymagany, chyba że --source)
  --source <path>     Import opisu z pliku PDF/MD/TXT

CO ROBI:
  • Generuje nazwę ficzera z opisu (kebab-case)
  • Tworzy .blast/specs/{nazwa}/
  • Inicjalizuje spec.json + requirements.md z szablonów
  • Jeśli --source: embeduje treść pliku w requirements.md

PRZYKŁADY:
  /blast:init "System logowania z OAuth2"
  /blast:init "Dashboard" --source docs/brief.pdf
  /blast:init --source specs/feature-description.md

NASTĘPNY KROK:
  /blast:requirements {nazwa-ficzera}

POWIĄZANE:
  ← (start)
  → /blast:requirements
```

## Important Constraints
- Output in Polish (blast UI language)
- Keep output scannable — use monospace blocks for command reference
- For detailed help: read the actual command file, don't hardcode descriptions
- If command not found: suggest closest match or show full help

</instructions>

## Safety & Fallback
- **Unknown command**: "Komenda `{name}` nie istnieje. Dostępne komendy:" → show full help
- **Typo detection**: If close match found (e.g., "req" → "requirements"), suggest correction


---

## Setup before first run

### Zero-config (default)
Działa od razu — Claude Code subscription wystarczy. Pipeline (init→complete), review/security solo: zero env vars.

### Multi-LLM (HYBRID, JURY_3_FLASH3, privacy mode)

```bash
cp .env.example .env             # wypełnij klucze które chcesz
set -a; source .env; set +a
# Restart Claude Code (MCP bridge re-reads env)
/blast:ping-llm                  # smoke test
```

### Required env vars per use case

| Use case | Vars |
|---|---|
| Plain pipeline | NONE |
| `validate-impl --debate` (HYBRID) | `BLAST_OLLAMA_UBUNTU` |
| `security` + `validate-design --debate` (jury) | `BLAST_OLLAMA_UBUNTU` + `GEMINI_API_KEY` |
| Privacy mode | `BLAST_OLLAMA_UBUNTU` (cloud blocked) |
| Spike reproduction | `ANTHROPIC_API_KEY` + `GEMINI_API_KEY` + `BLAST_OLLAMA_UBUNTU` |

Pełen detail: `.env.example`. Lokalny Ollama setup: `.blast/knowledge/references/multi-llm-setup.md`.

**NIE** ustawiaj `OLLAMA_KEEP_ALIVE` system-wide na >5min — używaj per-call `keep_alive: "30m"`. 24h+ blokuje VRAM.
