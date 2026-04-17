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
`steering`, `steering-custom`, `init`, `requirements`, `research`, `design`, `tasks`, `impl`, `complete`, `deprecate`, `quick`, `full`, `review`, `security`, `push`, `status`, `validate-gap`, `validate-design`, `validate-impl`, `help`

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
  /blast:impl {f} [taski]          Implementacja TDD
  /blast:complete {f}              Ship! → inventory + retrospekcja + steering sync

SKRÓTY:
  /blast:quick "opis"              Spec w jednym (init→req→design→tasks)
  /blast:quick "opis" --auto       Spec pełny automat
  /blast:quick --research          Spec z research phase
  /blast:full "opis"               Pełny pipeline (spec + impl + ship + security)
  /blast:full "opis" --auto        Pipeline pełny automat
  /blast:full --research --push    Pipeline z research i pushem
  /blast:full --source file --auto   Pipeline z pliku, automat

JAKOŚĆ KODU:
  /blast:review {f}                Code review vs zasady (Clean Code, SOLID, DRY...)
  /blast:review {f} --fix          Code review + automatyczne poprawki
  /blast:review                    Review całego codebase
  /blast:security {f}              Audyt bezpieczeństwa (OWASP, secrets, injection)
  /blast:security {f} --fix        Audyt + auto-fix bezpiecznych poprawek
  /blast:security --all            Skan całego codebase

WALIDACJE (opcjonalne):
  /blast:validate-gap {f}          Analiza luki (przed design)
  /blast:validate-design {f}       Review architektury (po design)
  /blast:validate-impl {f}         Walidacja impl vs spec (po impl)
  /blast:validate-impl {f} --prove Walidacja + odpalenie Verification Strategy z design.md

GIT:
  /blast:push [feature]            Commit + push (smart staging, English title)
  /blast:full "opis" --push        Pipeline + push na koniec

ZARZĄDZANIE:
  /blast:status {f}                Status i postęp specyfikacji
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
  /blast:full  = init → req → [research] → design → tasks → impl → complete → security → steering [→ push]

FLAGI:
  -y                               Auto-approve (design, tasks)
  --auto                           Pełny automat (quick, full)
  --source path/to/file            Importuj opis z pliku (init, quick, full)
  --fix                            Auto-fix (review)
  --push                           Git push po pipeline (full)
  --research                       Research phase (quick, full)
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

QUALITY GATES:
  Automatyczne kontrole jakości przed każdą fazą.
  Reguły: .blast/settings/rules/quality-gates.md

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

## Tool Guidance
- **Read**: Load command file from `.claude/commands/blast/{name}.md` for detailed help
- **Glob**: List available commands if name not found

## Output Description
- Full help: reference card format (monospace block)
- Detailed help: structured command info (under 200 words)
- Always end with: "Pełna dokumentacja: `.blast/README.md`"

## Safety & Fallback
- **Unknown command**: "Komenda `{name}` nie istnieje. Dostępne komendy:" → show full help
- **Typo detection**: If close match found (e.g., "req" → "requirements"), suggest correction
