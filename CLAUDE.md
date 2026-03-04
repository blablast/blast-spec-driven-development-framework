# blast — Spec-Driven Development by Błażej Strus

> **blast** = Błażej Strus' AI Development Life Cycle.
> Mój system, moje zasady, mój flow.

## Filozofia

blast to moje podejście do programowania z AI — uporządkowane, ale bez kija w dupie.
Każda ficzerka przechodzi przez jasne fazy: od pomysłu, przez specyfikację, aż po kod.
Nie piszemy kodu w ciemno. Najpierw wiemy CO, potem JAK, a dopiero wtedy lecimy z implementacją.

## Struktura projektu

- **Steering** (`.blast/steering/`) — pamięć projektu: kontekst, stack, konwencje
- **Specs** (`.blast/specs/`) — specyfikacje poszczególnych ficzerów
- **Settings** (`.blast/settings/`) — reguły, szablony, konfiguracja systemu

Pełna dokumentacja: `.blast/README.md`

## Komendy blast

### Faza 0: Kontekst projektu (opcjonalna)

| Komenda | Co robi |
|---|---|
| `/blast:steering` | Tworzy lub synchronizuje pamięć projektu |
| `/blast:steering-custom` | Tworzy dodatkowe pliki steering (API, DB, security...) |

### Faza 1: Specyfikacja

| Komenda | Co robi |
|---|---|
| `/blast:init "opis" [--source path]` | Inicjalizuje nowy spec — tworzy folder i metadane. `--source` importuje treść z pliku |
| `/blast:requirements {feature}` | Generuje wymagania w formacie EARS |
| `/blast:validate-gap {feature}` | *(opcjonalne)* Analiza luki między wymaganiami a istniejącym kodem |
| `/blast:design {feature} [-y]` | Generuje design techniczny |
| `/blast:validate-design {feature}` | *(opcjonalne)* Review jakości designu |
| `/blast:tasks {feature} [-y]` | Generuje plan implementacji (taski) |

### Faza 2: Implementacja

| Komenda | Co robi |
|---|---|
| `/blast:impl {feature} [tasks]` | Implementuje taski (TDD) z lintingiem (ruff/eslint) i docstrings |
| `/blast:review {feature} [--fix]` | Code review vs zasady (Clean Code, SOLID, DRY, PEP8, ruff...) |
| `/blast:validate-impl {feature}` | *(opcjonalne)* Walidacja implementacji vs spec |
| `/blast:complete {feature}` | Zamyka spec, aktualizuje inventory — ficzer shipped! |
| `/blast:push [feature]` | Git commit + push (smart staging, English title) |
| `/blast:deprecate {feature}` | Wycofuje ficzer z migration guide |

### Skróty i status

| Komenda | Co robi |
|---|---|
| `/blast:quick "opis" [--auto] [--source]` | Specyfikacja w jednym strzale (init→req→design→tasks) |
| `/blast:full "opis" [--auto] [--source] [--push]` | Pełny pipeline od opisu do shipped kodu (spec + impl + ship + steering + push) |
| `/blast:status {feature}` | Status i postęp specyfikacji |
| `/blast:help [komenda]` | Pomoc — lista komend, flagi, przykłady |

## Workflow — od zera do kodu

```
/blast:steering                    # raz na projekt
/blast:init "nowa ficzerka"
/blast:requirements {feature}
/blast:design {feature}
/blast:tasks {feature}
/blast:impl {feature} 1.1
/blast:complete {feature}          # zamyka spec, aktualizuje inventory
```

Szybki tryb — tylko spec (prototyp / CRUD):
```
/blast:quick "opis ficzera" --auto
```

Pełny pipeline — od opisu do shipped kodu:
```
/blast:full "opis ficzera" --auto
/blast:full "opis" --source docs/brief.pdf --auto
```

## Zasady gry

1. **3 fazy, 3 zgody** — Requirements → Design → Tasks → dopiero wtedy kod
2. **Human review** na każdym etapie (chyba że `-y` na szybko)
3. **Steering = pamięć** — trzymaj aktualny, to Twój kontekst dla AI
4. **Sprawdzaj status** — `/blast:status` powie Ci gdzie jesteś
5. **Język specyfikacji** — domyślnie polski (konfigurowalny w `spec.json`)
6. **Autonomia w ramach instrukcji** — AI zbiera kontekst i dowozi, pyta tylko gdy brakuje krytycznych info

## Zasady kodowania

blast wymusza zasady Clean Code, SOLID, KISS, DRY, YAGNI, odpowiednie wzorce projektowe, brak overengineeringu i SOTA rozwiązania. Pełna lista: `.blast/settings/rules/code-principles.md`

## Wytyczne dla AI

- Myśl po angielsku, odpowiadaj po angielsku. Cała treść Markdown zapisywana do plików projektowych (np. requirements.md, design.md, tasks.md, research.md, raporty walidacyjne) MUSI być napisana w języku docelowym skonfigurowanym dla danej specyfikacji (patrz spec.json.language).
- Postępuj zgodnie z instrukcjami użytkownika i w ich zakresie działaj autonomicznie: zbieraj potrzebny kontekst i realizuj zadanie od A do Z, pytając tylko wtedy gdy brakuje krytycznych informacji.
- Stosuj zasady z `.blast/settings/rules/code-principles.md` na etapie designu i implementacji.

## Smart Routing — automatyczna nawigacja

Kiedy użytkownik pyta "co dalej?" lub wydaje komendę blast, AI MUSI sprawdzić aktualny stan projektu i zasugerować właściwą ścieżkę:

**Detekcja stanu** — przeczytaj `.blast/specs/*/spec.json` i sprawdź `phase` + `status`:

| Stan projektu | Sugerowana akcja |
|---|---|
| Brak steering (`steering/` pusty) | → `/blast:steering` |
| Brak speców (`specs/` pusty) | → `/blast:init "opis"` |
| `phase: "initialized"` | → `/blast:requirements {feature}` |
| `phase: "requirements-generated"`, requirements approved | → `/blast:design {feature}` (lub `/blast:validate-gap` dla złożonych) |
| `phase: "requirements-generated"`, requirements NOT approved | → Poproś o review requirements |
| `phase: "design-generated"`, design approved | → `/blast:tasks {feature}` |
| `phase: "design-generated"`, design NOT approved | → Poproś o review designu (lub `/blast:validate-design`) |
| `phase: "tasks-generated"`, tasks approved | → `/blast:impl {feature}` |
| `phase: "tasks-generated"`, tasks NOT approved | → Poproś o review tasków |
| Wszystkie taski `[x]` w tasks.md | → `/blast:complete {feature}` |
| `status: "shipped"` | → Ficzer gotowy. `/blast:steering` do sync lub nowy `/blast:init` |

**Phase guards** — jeśli użytkownik próbuje przeskoczyć fazę (np. `/blast:impl` bez approved tasks), AI ostrzega i sugeruje brakujący krok. Nie blokuje, ale jasno komunikuje ryzyko.

**Auto-detect feature** — jeśli jest tylko jeden aktywny spec, AI domyśla się o który ficzer chodzi (nie trzeba podawać nazwy).

## Pamięć projektu i DRY

blast pilnuje DRY na poziomie cross-spec:

- **INVENTORY.md** (`.blast/steering/`) — rejestr shipped komponentów, aktualizowany przez `/blast:complete`
- **spec.json → `provides`** — każdy spec deklaruje co dostarcza (komponenty, serwisy, typy)
- **spec.json → `dependencies`** — każdy spec deklaruje od czego zależy
- **Cross-spec check** — agenci requirements, design i validate-gap sprawdzają inne spece przed generowaniem, żeby nie duplikować
- **Status lifecycle** — `planning` → `active` → `shipped` → ew. `deprecated`

Workflow pamięci: `/blast:impl` → `/blast:complete` (aktualizuje inventory) → `/blast:steering` (synchronizuje pamięć)

## Konfiguracja Steering

- Ładuj cały `.blast/steering/` jako pamięć projektu
- Domyślne pliki: `product.md`, `tech.md`, `structure.md`, `INVENTORY.md`
- Pliki niestandardowe obsługiwane przez `/blast:steering-custom`

## Aktywne specyfikacje

Sprawdź `.blast/specs/` lub użyj `/blast:status [feature]`.

---

*blast by Błażej Strus — bo programowanie powinno mieć flow, nie chaos.*
