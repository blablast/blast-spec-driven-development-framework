# blast — Spec-Driven Development by Błażej Strus

> Mój system, moje zasady, mój flow.
> Każda ficzerka przechodzi jasne fazy: od pomysłu, przez specyfikację, aż po kod.

## Co to jest blast?

blast to framework do programowania z AI, który wymusza porządek: **najpierw wiesz CO, potem JAK, a dopiero wtedy piszesz kod**. Działa jako zestaw agentów i komend dla Claude Code — generuje specyfikacje, designy i taski, a potem implementuje je w TDD.

Filozofia kodowania (Clean Code, SOLID, KISS, DRY, YAGNI, wzorce projektowe, brak overengineeringu, SOTA) jest wymuszana na każdym etapie. Pełne zasady: `.blast/settings/rules/code-principles.md`.

## Struktura katalogów

```
.blast/
├── settings/
│   ├── rules/             ← reguły procesu (EARS, design, taski, code principles...)
│   └── templates/         ← szablony specs / steering / steering-custom
├── knowledge/             ← decyzje (ADR), referencje, wyniki researchów
├── steering/              ← pamięć projektu (generowana przez /blast:steering)
└── specs/                 ← specyfikacje ficzerów (generowane przez /blast:init)

.claude/
├── agents/blast/          ← 17 agentów + 4 debate sub-agents
├── commands/blast/        ← 29 slash commands
└── settings.local.json    ← uprawnienia bash (git-ignored)

CLAUDE.md                  ← instrukcje dla AI (ładowane automatycznie)
```

## Szybki start

### Wymagania

- **Claude Code** (terminal) — blast działa przez slash commands
- Projekt z kodem źródłowym (lub pusty do zainicjalizowania)

### Krok 0: Inicjalizacja pamięci projektu (raz na projekt)

```
/blast:steering
```

Analizuje codebase i generuje `.blast/steering/` z trzema plikami: `product.md`, `tech.md`, `structure.md`.

Opcjonalnie rozszerzony steering (API standards, testing, security, database...):
```
/blast:steering-custom
```

### Krok 1–4: Specyfikacja ficzera

```bash
# Inicjalizacja
/blast:init "System logowania z OAuth2"
/blast:init "System logowania" --source docs/login-brief.pdf   # z pliku
/blast:init --source specs/feature-description.md              # tylko z pliku

# Wymagania (EARS)
/blast:requirements system-logowania-oauth2

# Research / spike (opcjonalnie)
/blast:research system-logowania-oauth2 [--deep]

# Design techniczny
/blast:design system-logowania-oauth2

# Plan implementacji
/blast:tasks system-logowania-oauth2
```

Każdy etap wymaga review — idziesz dalej dopiero po aprovacie.

### Krok 5: Implementacja (TDD)

```bash
/blast:impl system-logowania-oauth2 1.1    # konkretny task
/blast:impl system-logowania-oauth2        # wszystkie
```

### Krok 6: Zamknięcie ficzera

```bash
/blast:complete system-logowania-oauth2              # ship + update inventory + retrospekcja
/blast:steering                                       # sync pamięci (rekomendowane po complete)
/blast:security system-logowania-oauth2 [--fix]      # audyt bezpieczeństwa
/blast:security --all                                # cały codebase
```

### Tryb szybki — tylko specyfikacja (prototyp / CRUD)

```bash
/blast:quick "Formularz kontaktowy z walidacją"                 # z review
/blast:quick "Formularz kontaktowy z walidacją" --auto          # pełny automat
/blast:quick --source docs/brief.pdf --auto                     # z pliku
/blast:quick "OAuth2 login" --auto --research                   # z fazą research
```

### Pełny pipeline — od opisu do shipped kodu

```bash
/blast:full "Formularz kontaktowy z walidacją"                  # interaktywny
/blast:full "Formularz kontaktowy z walidacją" --auto           # pełny automat
/blast:full --source docs/brief.pdf --auto                      # z pliku
/blast:full "Formularz kontaktowy" --auto --push                # + push
```

`/blast:full` wykonuje: init → req → [research] → design → tasks → impl → complete → security → steering [→ push]. Security zawsze — blokuje pipeline przy krytycznych lukach.

### Git push

```bash
/blast:push zoo-garden    # smart staging, English commit title
/blast:push               # auto-detect wszystkich zmian
```

### Code review

```bash
/blast:review system-logowania-oauth2            # Clean Code, SOLID, DRY, YAGNI, ruff, docstrings
/blast:review system-logowania-oauth2 --fix      # + automatyczne poprawki
/blast:review                                     # cały codebase
```

### Walidacje specyfikacji (opcjonalne)

```bash
/blast:validate-gap      {f}             # co jest, czego brakuje
/blast:validate-design   {f}             # review designu
/blast:validate-impl     {f} [--prove]   # walidacja impl vs spec; --prove odpala Verification Strategy
```

### Podgląd i pomoc

```bash
/blast:status {f}
/blast:help              # lista komend
/blast:help init         # szczegóły konkretnej komendy
```

## Import opisu z pliku

Gotowy brief w PDF/MD/TXT? Wskaż plik zamiast przepisywać:

```bash
/blast:init "Panel administracyjny" --source docs/admin-panel-brief.pdf
/blast:init --source features/user-dashboard.md
/blast:init "Integracja płatności" --source exports/payment-integration.txt
```

Treść pliku trafia do `requirements.md` jako "Source Material". Agent `/blast:requirements` generuje wymagania EARS na jej podstawie. Obsługiwane formaty: PDF, MD, TXT, HTML. Pliki >500 linii są przycinane z referencją do pełnej ścieżki.

## Przykład: od zera do kodu

Apka do zarządzania zadaniami, chcesz dodać drag & drop na tablicy Kanban.

```bash
/blast:steering                                    # 1. Pamięć projektu (jeśli jeszcze nie ma)
/blast:init "Drag and drop na tablicy Kanban"       # 2. Spec
/blast:requirements drag-drop-kanban               # 3. Wymagania EARS
/blast:design drag-drop-kanban                      # 4. Design techniczny (KISS, SRP automatycznie)
/blast:tasks drag-drop-kanban                       # 5. Plan implementacji z (P) markerami
/blast:impl drag-drop-kanban 1.1                    # 6. TDD task po tasku
/blast:validate-impl drag-drop-kanban [--prove]     # 7. Walidacja (opcjonalnie)
/blast:complete drag-drop-kanban                    # 8. Ship + inventory + retrospekcja
```

Po `/blast:complete`:
- `spec.json` → `status: "shipped"`, `provides: ["DragProvider", "KanbanColumn", "TaskCard"]`
- `INVENTORY.md` → nowe wpisy w rejestrze komponentów
- Następnym razem gdy odpalisz `/blast:requirements nowy-ficzer`, agent sprawdzi inventory i ostrzeże jeśli próbujesz zbudować coś co już istnieje. **To jest DRY na poziomie cross-spec.**

## Multi-LLM (opcjonalne)

blast obsługuje multi-LLM compositions:
- **HYBRID** dla `validate-impl --thorough` (Sonnet + qwen3.6 → Haiku)
- **JURY_3_FLASH3** dla `security` + high-stakes (Opus + qwen3.6 + Gemini-3-Flash → Haiku)
- **Privacy mode** (`spec.json.privacy: local-only`) blokuje external calls

Setup: `cp .env.example .env`, fill keys, see `MANIFEST.md` + `.blast/steering/llm-routing.md`.

## Pamięć projektu i DRY cross-spec

blast pilnuje żebyś nie pisał tego samego dwa razy:

- **INVENTORY.md** (`.blast/steering/`) — rejestr shipped komponentów, aktualizowany przez `/blast:complete`. Każdy spec deklaruje `provides` (co dostarcza) i `dependencies` (od czego zależy).
- **Cross-spec awareness** — agenci requirements/design/validate-gap sprawdzają inne spece przed generowaniem. Ostrzegają jeśli próbujesz budować coś co już istnieje.
- **Status lifecycle** — `planning` → `active` → `shipped` → ew. `deprecated`.

Workflow pamięci: `/blast:impl` → `/blast:complete` (aktualizuje inventory) → `/blast:steering` (sync).

## Użycie jako szablon

blast jest reusable template. Pełna klasyfikacja FRAMEWORK / HYBRID / R&D w `MANIFEST.md` na repo root.

- **FRAMEWORK (universal)**: `.blast/settings/`, `.claude/agents/blast/`, `.claude/commands/blast/`, `.claude/scripts/`, `.claude/hooks/`, `.claude/mcp/` — 100% reusable
- **HYBRID** (project-specific content w framework path): `.blast/steering/{cost-policy,llm-routing}.md` — replace z `.blast/settings/templates/steering/*.template` na nowy projekt
- **Per-project**: `.blast/{specs,knowledge,steering}/` — puste/.gitkeep, generuje się per-projekt
- **R&D (NIE ship)**: `r_and_d/` — personal content tego repo, exclude przy distribution

Workflow nowego projektu:

```bash
git clone git@github.com:twoj-user/blast-template.git moj-nowy-projekt
cd moj-nowy-projekt
rm -rf .git && git init                            # opcjonalne
# w Claude Code:
/blast:steering
/blast:init "pierwsza ficzerka"
```

`.gitignore` powinien wykluczać: `.claude/settings.local.json`, standardowe artefakty (`*.pyc`, `__pycache__/`, `node_modules/`, `.env`).

## Kiedy blast, kiedy nie?

| Scenariusz | Rekomendacja |
|---|---|
| Nowy ficzer z logiką biznesową | `/blast:init` → pełny workflow |
| Ficzer opisany w PDF/MD | `/blast:full --source plik.pdf` |
| CRUD / prototyp — tylko spec | `/blast:quick --auto` |
| CRUD / prototyp — do kodu | `/blast:full --auto` |
| Bugfix (1–2 pliki) | Bez blasta |
| Refactoring | `/blast:init` z opisem refactoringu |
| Hotfix produkcyjny | Bez blasta — czas kluczowy |
| Spike / research | `/blast:research {f}` lub `--research` |
| Przegląd jakości kodu | `/blast:review [{f}]` |
| Audyt bezpieczeństwa | `/blast:security [{f}]` |

Pełną ściągę komend i flag → `/blast:help [komenda]`.

---

*blast by Błażej Strus — bo programowanie powinno mieć flow, nie chaos.*
