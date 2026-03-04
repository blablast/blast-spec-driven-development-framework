# blast — Spec-Driven Development by Błażej Strus

> Mój system, moje zasady, mój flow.
> Każda ficzerka przechodzi jasne fazy: od pomysłu, przez specyfikację, aż po kod.

## Co to jest blast?

blast to framework do programowania z AI, który wymusza porządek: **najpierw wiesz CO, potem JAK, a dopiero wtedy piszesz kod**. Działa jako zestaw agentów i komend dla Claude Code — generuje specyfikacje, designy i taski, a potem implementuje je w TDD.

### Filozofia kodowania

blast wymusza zestaw zasad na każdym etapie (pełna lista w `.blast/settings/rules/code-principles.md`):

- **Clean Code** — czytelność ponad spryt, małe funkcje, znaczące nazwy
- **SOLID** — każdy moduł ma jedną odpowiedzialność, zależności przez abstrakcje
- **KISS** — najprostsze rozwiązanie, które spełnia wymagania
- **DRY** — jedna reprezentacja wiedzy, ale bez przedwczesnej abstrakcji
- **YAGNI** — nie budujemy "na zapas"
- **Wzorce projektowe** — stosowane gdy rozwiązują realny problem, nie dla samego stosowania
- **No overengineering** — konkretne rozwiązania zamiast frameworków na jedną ficzkę
- **SOTA** — nowoczesne narzędzia i idiomy, ale krytycznie oceniane

## Struktura katalogów

```
.blast/
├── README.md              ← ten plik
├── settings/
│   ├── rules/             ← reguły procesu (EARS, design, taski, code principles...)
│   └── templates/
│       ├── specs/         ← szablony specyfikacji (init.json, requirements.md, design.md...)
│       ├── steering/      ← szablony core steering (product, tech, structure)
│       └── steering-custom/ ← szablony rozszerzonych steering (API, DB, security...)
├── knowledge/
│   ├── decisions/         ← decyzje architektoniczne (ADR)
│   ├── references/        ← dokumentacja API, snippety, artykuły
│   └── research/          ← wyniki researchów (auto-generowane)
├── steering/              ← pamięć projektu (generowana przez /blast:steering)
└── specs/                 ← specyfikacje ficzerów (generowane przez /blast:init)

.claude/
├── agents/blast/          ← 13 agentów (steering, requirements, research, design, tasks, impl, complete, review, walidacje)
├── commands/blast/        ← 20 slash commands (interfejs użytkownika)
└── settings.local.json    ← uprawnienia bash (git-ignored)

CLAUDE.md                  ← instrukcje dla AI (ładowane automatycznie)
```

## Szybki start

### Wymagania

- **Claude Code** (terminal) — blast działa przez slash commands
- Projekt z kodem źródłowym (lub pusty projekt do zainicjalizowania)

### Krok 0: Inicjalizacja pamięci projektu (raz na projekt)

```
/blast:steering
```

Analizuje codebase i generuje `.blast/steering/` z trzema plikami:
- `product.md` — co to za projekt, dla kogo, po co
- `tech.md` — stack technologiczny, konwencje, decyzje
- `structure.md` — organizacja kodu, nazewnictwo, importy

Opcjonalnie rozszerzony steering:
```
/blast:steering-custom
```
Tworzy dodatkowe pliki (API standards, testing, security, database...).

### Krok 1–4: Specyfikacja ficzera

```bash
# Inicjalizacja — opis tekstowy
/blast:init "System logowania z OAuth2"

# Inicjalizacja z pliku źródłowego (PDF, MD, TXT)
/blast:init "System logowania" --source docs/login-brief.pdf

# Inicjalizacja tylko z pliku (opis wyciągnie z treści)
/blast:init --source specs/feature-description.md

# Wymagania w formacie EARS
/blast:requirements system-logowania-oauth2

# Research / spike (opcjonalnie — gdy nie wiesz JAK)
/blast:research system-logowania-oauth2
/blast:research system-logowania-oauth2 --deep  # dogłębny z benchmarkami

# Design techniczny (architektura, komponenty, interfejsy)
/blast:design system-logowania-oauth2

# Plan implementacji (taski z mapowaniem na wymagania)
/blast:tasks system-logowania-oauth2
```

Każdy etap wymaga review — idziesz dalej dopiero po aprovacie.

### Krok 5: Implementacja (TDD)

```bash
# Konkretny task
/blast:impl system-logowania-oauth2 1.1

# Wszystkie taski
/blast:impl system-logowania-oauth2
```

### Krok 6: Zamknięcie ficzera

```bash
# Oznacza ficzer jako shipped, aktualizuje inventory
/blast:complete system-logowania-oauth2

# Sync pamięci projektu (rekomendowane po complete)
/blast:steering

# Audyt bezpieczeństwa (rekomendowane przed deployment)
/blast:security system-logowania-oauth2
/blast:security system-logowania-oauth2 --fix   # auto-fix bezpiecznych poprawek
/blast:security --all                           # cały codebase
```

### Tryb szybki — tylko specyfikacja (prototyp / CRUD)

```bash
# Z review na każdym etapie
/blast:quick "Formularz kontaktowy z walidacją"

# Pełny automat — bez pytań
/blast:quick "Formularz kontaktowy z walidacją" --auto

# Z pliku źródłowego
/blast:quick --source docs/brief.pdf --auto

# Z fazą research (gdy nie wiesz JAK)
/blast:quick "OAuth2 login" --auto --research
```

### Pełny pipeline — od opisu do shipped kodu

```bash
# Interaktywny — zatrzymuje się po każdej fazie, pytasz "dalej?"
/blast:full "Formularz kontaktowy z walidacją"

# Pełny automat — spec, implementacja TDD, security, ship, sync pamięci
/blast:full "Formularz kontaktowy z walidacją" --auto

# Z pliku źródłowego, automat
/blast:full --source docs/brief.pdf --auto

# Pełny automat + push na repo
/blast:full "Formularz kontaktowy" --auto --push
```

`/blast:full` wykonuje 8 faz: init → req → [research] → design → tasks → impl → complete → security → steering [→ push]. Security jest zawsze — blokuje pipeline przy krytycznych lukach. Research opcjonalny z `--research`.

### Git push — wrzucanie na repo

```bash
# Push ficzera (smart staging, English commit title)
/blast:push zoo-garden

# Push wszystkich zmian (auto-detect)
/blast:push
```

### Code review — jakość kodu

```bash
# Review ficzera — Clean Code, SOLID, DRY, YAGNI, ruff, docstrings
/blast:review system-logowania-oauth2

# Review + automatyczne poprawki (ruff fix, formatowanie, docstrings)
/blast:review system-logowania-oauth2 --fix

# Review całego codebase
/blast:review
```

`/blast:review` sprawdza kod pod kątem WSZYSTKICH zasad z `code-principles.md` — punkt po punkcie. Odpala ruff (Python) / ESLint (JS/TS), waliduje Google-style docstrings, szuka code smells, i generuje raport ze scorecard. Z flagą `--fix` automatycznie naprawia co się da.

### Walidacje specyfikacji (opcjonalne, ale polecane)

```bash
# Gap analysis — co jest, czego brakuje
/blast:validate-gap system-logowania-oauth2

# Review designu — architektura OK?
/blast:validate-design system-logowania-oauth2

# Walidacja implementacji vs spec
/blast:validate-impl system-logowania-oauth2
```

### Podgląd statusu i pomoc

```bash
/blast:status system-logowania-oauth2

# Pomoc — lista wszystkich komend
/blast:help

# Pomoc dla konkretnej komendy
/blast:help init
/blast:help design
```

## Import opisu z pliku

Masz gotowy brief w PDF, specyfikację w Markdown, albo opis z Jiry w TXT? Nie przepisuj ręcznie — wskaż plik:

```bash
# PDF od klienta z opisem wymagań
/blast:init "Panel administracyjny" --source docs/admin-panel-brief.pdf

# Markdown z opisem ficzera
/blast:init --source features/user-dashboard.md

# Eksport z Jiry / Confluence
/blast:init "Integracja płatności" --source exports/payment-integration.txt
```

**Co się dzieje**: treść pliku trafia do `requirements.md` jako "Source Material". Agent `/blast:requirements` czyta ją jako pełny kontekst i generuje wymagania EARS na jej podstawie — nie musisz przepisywać ani streszczać.

**Obsługiwane formaty**: PDF, Markdown (.md), tekst (.txt), HTML (.html). Pliki >500 linii są przycinane z referencją do pełnej ścieżki.

## Przykład: od zera do kodu

Załóżmy, że masz apkę do zarządzania zadaniami i chcesz dodać ficzer drag & drop na tablicy Kanban.

### 1. Inicjalizacja pamięci (jeśli jeszcze nie zrobiona)

```
/blast:steering
```

Blast analizuje Twój codebase i generuje pamięć projektu — wie jaki masz stack, jakie konwencje, jak zorganizowany jest kod.

### 2. Inicjalizacja ficzera

```
/blast:init "Drag and drop na tablicy Kanban"
```

Tworzy `.blast/specs/drag-drop-kanban/` z `spec.json` i szkieletem `requirements.md`.

### 3. Wymagania

```
/blast:requirements drag-drop-kanban
```

Generuje wymagania w formacie EARS, np.:
- *"When a user drags a task card, the system shall display a visual placeholder at the target position"*
- *"When a task is dropped in a new column, the system shall update the task status and persist the change"*

Reviewujesz, zatwierdzasz (albo poprawiasz).

### 4. Design

```
/blast:design drag-drop-kanban
```

Generuje design techniczny: komponenty (`DragProvider`, `KanbanColumn`, `TaskCard`), interfejsy, flow diagramy w Mermaid, strategię testowania. Wszystko z traceability do wymagań.

Zasady code principles wchodzą tu automatycznie — design musi być KISS, komponenty SRP, brak overengineeringu.

### 5. Taski

```
/blast:tasks drag-drop-kanban
```

Generuje plan implementacji z mapowaniem na wymagania:
```
- [ ] 1. Implement drag and drop infrastructure
- [ ] 1.1 (P) Set up DragProvider with context and state management
- [ ] 1.2 (P) Implement draggable TaskCard behavior
- [ ] 1.3 Implement droppable KanbanColumn with visual feedback
- [ ] 2. Implement persistence and state sync
- [ ] 2.1 Update task status on drop with optimistic UI
- [ ] 2.2 Handle error recovery and rollback
```

### 6. Implementacja

```
/blast:impl drag-drop-kanban 1.1
```

Blast implementuje task 1.1 w TDD: najpierw test, potem kod, potem refactor. Powtarzasz dla kolejnych tasków.

### 7. Walidacja (opcjonalnie)

```
/blast:validate-impl drag-drop-kanban
```

Sprawdza: czy wszystkie wymagania pokryte, testy przechodzą, design jest zgodny z implementacją.

### 8. Zamknięcie i pamięć

```
/blast:complete drag-drop-kanban
```

Co się dzieje:
- `spec.json` → `status: "shipped"`, `provides: ["DragProvider", "KanbanColumn", "TaskCard"]`
- `INVENTORY.md` w steering → nowe wpisy w rejestrze komponentów
- Następnym razem jak odpalisz `/blast:requirements nowy-ficzer`, agent sprawdzi inventory i ostrzeże jeśli próbujesz budować coś co już istnieje

**Teraz wyobraź sobie, że za tydzień robisz nowy ficzer "Sortowanie zadań na tablicy".** Agent requirements widzi w inventory że `DragProvider` i `TaskCard` już istnieją — zamiast budować od zera, projektuje rozszerzenie istniejących komponentów. **To jest DRY na poziomie cross-spec.**

## Pamięć projektu i DRY cross-spec

blast pilnuje żebyś nie pisał tego samego dwa razy:

**INVENTORY.md** (`.blast/steering/`) — rejestr shipped komponentów. Aktualizowany automatycznie przez `/blast:complete`. Każdy ficzer deklaruje co dostarcza (`provides`) i od czego zależy (`dependencies`).

**Cross-spec awareness** — agenci requirements, design i validate-gap przed generowaniem sprawdzają inne spece. Jeśli próbujesz budować coś co już istnieje, dostaniesz ostrzeżenie z propozycją reuse.

**Status lifecycle** — `planning` → `active` → `shipped` → ew. `deprecated`. Dzięki temu wiesz co jest w produkcji, co jest w trakcie, a co porzucone.

**Workflow pamięci**:
```
/blast:impl {feature}      # implementujesz
/blast:complete {feature}   # zamykasz → inventory się aktualizuje
/blast:steering             # sync pamięci z nowym kodem
```

## Użycie jako szablon (rekomendowane)

blast jest zaprojektowany jako **reusable template** — 70% plików jest generycznych. Rekomendowane podejście:

### Struktura template repo

```
blast-template/
├── .blast/
│   ├── settings/          ← 100% reusable (rules + templates)
│   ├── steering/          ← pusty (.gitkeep) — generuje się per-projekt
│   └── specs/             ← pusty (.gitkeep) — generuje się per-projekt
├── .claude/
│   ├── agents/blast/      ← 100% reusable
│   └── commands/blast/    ← 100% reusable
├── CLAUDE.md              ← generyczna wersja (bez project-specific treści)
├── .gitignore
└── README.md              ← ten plik (albo skrócona wersja)
```

### Workflow nowego projektu

```bash
# Klonujesz szablon
git clone git@github.com:twoj-user/blast-template.git moj-nowy-projekt
cd moj-nowy-projekt

# Reinicjalizujesz git (opcjonalnie)
rm -rf .git && git init

# Inicjalizujesz pamięć projektu
# (w Claude Code)
/blast:steering

# I lecisz z ficzerami
/blast:init "pierwsza ficzerka"
```

### .gitignore (rekomendowany)

```gitignore
# Pliki lokalne Claude Code
.claude/settings.local.json

# Pliki specyficzne per-maszynę
*.pyc
__pycache__/
node_modules/
.env
```

## Kiedy blast, kiedy nie?

| Scenariusz | Rekomendacja |
|---|---|
| Nowy ficzer z logiką biznesową | `/blast:init` → pełny workflow krok po kroku |
| Ficzer opisany w dokumencie (PDF/MD) | `/blast:full --source plik.pdf` → pełny automat |
| CRUD / prototyp — tylko spec | `/blast:quick --auto` |
| CRUD / prototyp — od razu do kodu | `/blast:full --auto` |
| Bugfix (1-2 pliki) | Bez blasta — napraw bezpośrednio |
| Refactoring | `/blast:init` z opisem refactoringu, potem design + tasks |
| Hotfix produkcyjny | Bez blasta — czas jest kluczowy |
| Spike / research | `/blast:research {f}` lub `--research` w quick/full |
| Przegląd jakości kodu | `/blast:review` lub `/blast:review {f}` |
| Audyt bezpieczeństwa | `/blast:security {f}` (w full jest automatycznie) |

## Komendy — ściąga

| Komenda | Co robi | Kiedy używać |
|---|---|---|
| `/blast:steering` | Tworzy/synchronizuje pamięć projektu | Raz na projekt / po dużych zmianach |
| `/blast:steering-custom` | Dodaje custom steering | Gdy potrzebujesz API/DB/security guidelines |
| `/blast:init "opis" [--source]` | Tworzy nowy spec (opcjonalnie z pliku) | Start nowej ficzerki |
| `/blast:requirements {f}` | Generuje EARS requirements | Po init |
| `/blast:research {f} [--deep]` | Spike/research — opcje, porównania | Po requirements (opcjonalnie) |
| `/blast:design {f} [-y]` | Generuje design | Po requirements / research |
| `/blast:tasks {f} [-y]` | Generuje taski | Po design |
| `/blast:impl {f} [taski]` | Implementuje w TDD + ruff + docstrings | Po tasks |
| `/blast:review {f} [--fix]` | Code review vs zasady + linting | Po impl / w dowolnym momencie |
| `/blast:security {f} [--fix] [--all]` | Audyt bezpieczeństwa (OWASP, secrets) | Po complete / przed deployment |
| `/blast:complete {f}` | Zamyka spec, aktualizuje inventory | Po implementacji |
| `/blast:push [feature]` | Git commit + push (smart staging, English title) | Po complete / standalone |
| `/blast:deprecate {f}` | Wycofuje ficzer z migration guide | Gdy ficzer do wymiany |
| `/blast:quick "opis" [--auto] [--source] [--research]` | Spec w jednym (+ opcjonalny research) | Prototyp / CRUD — spec |
| `/blast:full "opis" [--auto] [--source] [--research] [--push]` | Pełny pipeline + security (+ push) | Prototyp / CRUD — od razu do kodu |
| `/blast:status {f}` | Sprawdza postęp | W dowolnym momencie |
| `/blast:validate-gap {f}` | Analiza luki | Przed design (opcjonalne) |
| `/blast:validate-design {f}` | Review designu | Po design (opcjonalne) |
| `/blast:validate-impl {f}` | Walidacja impl | Po implementacji (opcjonalne) |
| `/blast:help [komenda]` | Pomoc i ściąga | Zawsze |

---

*blast by Błażej Strus — bo programowanie powinno mieć flow, nie chaos.*
