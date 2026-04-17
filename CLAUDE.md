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
- **Knowledge** (`.blast/knowledge/`) — baza wiedzy: decyzje, referencje, wyniki researchów
- **Settings** (`.blast/settings/`) — reguły, szablony, konfiguracja systemu

Pełna dokumentacja: `.blast/README.md`

## Komendy blast

Pełen wykaz komend, flag i przykładów → `/blast:help [komenda]`.

### Pipeline

```
steering → init → requirements → [research] → design → tasks → impl → [review] → [security] → complete → [push]
```

`[optional]` = fazy opcjonalne. Walidacje (`validate-gap`, `validate-design`, `validate-impl`) też opcjonalne — wchodzą po właściwej fazie.

### Skróty

- `/blast:quick "opis" [--auto] [--research]` — tylko spec (init→req→[research]→design→tasks)
- `/blast:full "opis" [--auto] [--research] [--push]` — pełny pipeline (spec + impl + complete + security + steering)
- `/blast:status [f]` — status i postęp specu
- `/blast:help [cmd]` — szczegóły, flagi, przykłady

## Zasady gry

1. **3 fazy, 3 zgody** — Requirements → Design → Tasks → dopiero wtedy kod
2. **Human review** na każdym etapie (chyba że `-y` na szybko)
3. **Steering = pamięć** — trzymaj aktualny, to Twój kontekst dla AI
4. **Sprawdzaj status** — `/blast:status` powie Ci gdzie jesteś
5. **Język specyfikacji** — domyślnie polski (konfigurowalny w `spec.json`)
6. **Autonomia w ramach instrukcji** — AI zbiera kontekst i dowozi, pyta tylko gdy brakuje krytycznych info

## Verification

Jak AI ma zweryfikować swoją pracę bez czekania na CI:

- **Canonical commands** (install/test/lint/typecheck/dev/smoke) → `.blast/steering/tech.md :: Canonical Commands` (generowane przez `/blast:steering`)
- **Per-feature probe** (single test + smoke + e2e) → `.blast/specs/{f}/design.md :: Verification Strategy`
- **Runtime proof** → `/blast:validate-impl {f} --prove` (odpala Verification Strategy i sprawdza Expected Signal)

## Zasady kodowania

blast wymusza zasady Clean Code, SOLID, KISS, DRY, YAGNI, odpowiednie wzorce projektowe, brak overengineeringu i SOTA rozwiązania. Pełna lista: `.blast/settings/rules/code-principles.md`

## Wytyczne dla AI

- Myśl po angielsku, odpowiadaj po angielsku. Cała treść Markdown zapisywana do plików projektowych (np. requirements.md, design.md, tasks.md, research.md, raporty walidacyjne) MUSI być napisana w języku docelowym skonfigurowanym dla danej specyfikacji (patrz spec.json.language).
- Postępuj zgodnie z instrukcjami użytkownika i w ich zakresie działaj autonomicznie: zbieraj potrzebny kontekst i realizuj zadanie od A do Z, pytając tylko wtedy gdy brakuje krytycznych informacji.
- Stosuj zasady z `.blast/settings/rules/code-principles.md` na etapie designu i implementacji.
- **Core AI Rules** (załadowane na końcu tego pliku via `@.blast/settings/rules/ai-collaboration.md`) mają pierwszeństwo przed domyślnym "helpful" zachowaniem modelu.

## Smart Routing — automatyczna nawigacja

Kiedy użytkownik pyta "co dalej?" lub wydaje komendę blast, AI MUSI sprawdzić aktualny stan projektu i zasugerować właściwą ścieżkę:

**Detekcja stanu** — przeczytaj `.blast/specs/*/spec.json` i sprawdź `phase` + `status`:

| Stan projektu | Sugerowana akcja |
|---|---|
| Brak steering (`steering/` pusty) | → `/blast:steering` |
| Brak speców (`specs/` pusty) | → `/blast:init "opis"` |
| `phase: "initialized"` | → `/blast:requirements {feature}` |
| `phase: "requirements-generated"`, requirements approved | → `/blast:research {feature}` (lub `/blast:design` jeśli research niepotrzebny) |
| `phase: "research-completed"` | → `/blast:design {feature}` (lub `/blast:validate-gap` dla złożonych) |
| `phase: "requirements-generated"`, requirements NOT approved | → Poproś o review requirements |
| `phase: "design-generated"`, design approved | → `/blast:tasks {feature}` |
| `phase: "design-generated"`, design NOT approved | → Poproś o review designu (lub `/blast:validate-design`) |
| `phase: "tasks-generated"`, tasks approved | → `/blast:impl {feature}` |
| `phase: "tasks-generated"`, tasks NOT approved | → Poproś o review tasków |
| Wszystkie taski `[x]` w tasks.md | → `/blast:complete {feature}` |
| `status: "shipped"` | → `/blast:security {feature}` (rekomendowane) lub nowy `/blast:init` |

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

## Compact Instructions

Przy `/compact` zachowaj:

- Nazwę aktywnego ficzera i `phase` z `.blast/specs/{f}/spec.json`
- Otwarte taski (`- [ ]` w `tasks.md`) i lessons candidates z retrospekcji (jeśli są)
- Ostatni run Verification Strategy (test / smoke / e2e + exit codes)
- Decyzje architektoniczne podjęte w tej sesji

Odrzuć: output `/blast:help`, duplikaty Read, stary kontekst innych feature'ów, pełne tool outputs po tym, jak konkluzja już jest w chacie.

---

@.blast/settings/rules/ai-collaboration.md

---

*blast by Błażej Strus — bo programowanie powinno mieć flow, nie chaos.*
