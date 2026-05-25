# Requirements Document — `/blast:simplify`

## Introduction

`/blast:simplify` to nowa, opcjonalna faza pipeline'u: jedyny krok który złożoność **odejmuje**, a nie dokłada. Działa po implementacji, na zaimplementowanym specu. Usuwa złożoność narosłą w trakcie impl (drift) oraz nieuzasadnione abstrakcje — z **gwarancją zachowania zachowania** (Verification Strategy zielona przed i po cięciu).

Komenda jest egzekucyjnym ramieniem zasady Rule 2 (Simplicity first) z `ai-collaboration.md`, działającym pod twardym rygorem Rule 3 (Surgical changes — ochrona komentarzy, granica zastanego dead-code). Differentiator vs GitHub Spec Kit i Amazon Kiro — żaden z nich nie ma kroku „odejmij złożoność".

Zakres: jeden slash-command (`/blast:simplify`) + jeden agent (`simplify-agent`, persona Occam) + wpięcie w pipeline po `validate-impl`, przed `complete`. Bez zmian w istniejących fazach.

## Requirements

### Requirement 1: Tryb raportu (domyślny, nieniszczący)

**Objective:** Jako Błażej, chcę domyślnie dostać listę kandydatów do usunięcia bez dotykania kodu, aby móc ocenić cięcia zanim cokolwiek zniknie.

#### Acceptance Criteria
1. When `/blast:simplify {feature}` jest wywołane bez flagi `--apply`, the system shall przeskanować kod feature'a i wypisać findingi (REMOVE candidates), NIE modyfikując żadnego pliku.
2. While tryb raportu jest aktywny, the system shall pozostawić `git status` czysty (zero zmian w drzewie roboczym).
3. The system shall przypisać każdemu findingowi: ścieżkę+linię, oś (1-6), szacowaną deltę LOC (ujemną) i severity (CRITICAL/WARNING/INFO).
4. If skan nie znajdzie żadnych kandydatów, then the system shall zwrócić VERDICT PASS z komunikatem „code already lean".

### Requirement 2: Sześć osi redukcyjnych

**Objective:** Jako Błażej, chcę żeby simplify szukał złożoności na sześciu osiach, a nie tylko KISS/YAGNI, aby łapał też drift i over-engineering niewidoczny na poziomie planu.

#### Acceptance Criteria
1. The system shall sprawdzić oś **spec-traceability/drift**: każdy nietrywialny symbol (funkcja, klasa, gałąź, eksport) który nie odnosi się do żadnego wymagania w `requirements.md` ani taska w `tasks.md` shall być oznaczony jako kandydat do usunięcia.
2. The system shall sprawdzić osie: **YAGNI** (flexibility bez wymagania), **KISS/przedwczesna abstrakcja** (interfejs/generic/factory/ABC dla single-use), **dead code** (nieosiągalne, nieużywane importy/eksporty), **defensive overkill** (obsługa niemożliwych stanów), **config/flag sprawl** (opcje których nikt nie zamówił).
3. Where finding wymagałby **dodania** kodu lub abstrakcji, the system shall go odrzucić i (opcjonalnie) eskalować do `review` — simplify jest wyłącznie redukcyjny.
4. The system shall przed zaraportowaniem zweryfikować dla każdego findingu, że jego usunięcie zachowuje zachowanie; findingi zmieniające zachowanie shall być wycofane z jawnym labelem „⚠ Occam-bias".

### Requirement 3: Tryb `--apply` bramkowany Verification Strategy

**Objective:** Jako Błażej, chcę móc zastosować cięcia jednym poleceniem, ale tylko jeśli testy są zielone przed i po, aby nigdy nie zostać z zepsutym albo połowicznie pociętym drzewem.

#### Acceptance Criteria
1. When `--apply` jest podane, the system shall najpierw odpalić komendy z `design.md :: Verification Strategy` (baseline) i shall przerwać z VERDICT FAIL, jeśli baseline nie jest zielony („cannot simplify failing code").
2. If `design.md` feature'a nie zawiera sekcji `## Verification Strategy`, then the system shall odmówić wejścia w `--apply` i zwrócić FAIL z instrukcją uzupełnienia designu.
3. When baseline jest zielony, the system shall zastosować cięcia (od najbezpieczniejszych: dead code → defensive → config → drift → YAGNI → abstrakcje), a następnie ponownie odpalić Verification Strategy.
4. If re-run jest zielony, then the system shall zachować zmiany i zaraportować LOC before/after oraz `APPLIED: true`.
5. If re-run jest czerwony, then the system shall zrewertować dotknięte pliki (`git checkout -- <files>`), zaraportować które cięcia zepsuły build i ustawić `APPLIED: false`.
6. The system shall używać komend Verification Strategy **dosłownie** — nie wolno ich przepisywać ani osłabiać, żeby przeszły (integrity rule jak w validate-impl Prove Mode).
7. Where drzewo robocze ma już niezacommitowane zmiany w plikach docelowych, the system shall odmówić `--apply` (nie da się czysto zrewertować) i poprosić o commit/stash.

### Requirement 4: Hamulec Karpathy Rule 3 — ochrona komentarzy i granica dead-code

**Objective:** Jako Błażej, chcę żeby simplify nigdy nie usunął komentarza ani kodu, którego intencji nie rozumie, aby uniknąć top-pułapki LLM (ciche kasowanie niezrozumianego kontekstu).

#### Acceptance Criteria
1. The system shall NIGDY nie usuwać ani nie modyfikować komentarza, ani linii kodu, której intencji nie rozumie w pełni — nawet jeśli wygląda na osieroconą lub ortogonalną do zadania.
2. If kandydat do usunięcia niesie komentarz, którego agent nie potrafi w pełni wyjaśnić, then the system shall zdegradować go do findingu report-only i NIE wycinać w `--apply`.
3. The system shall traktować `/blast:simplify` jako jawne „polecenie" usuwania zastanego dead-code (wyjątek od Rule 3 „don't delete pre-existing"), ale licencja shall być wąska: usunąć wolno tylko kod spełniający JEDNOCZEŚNIE (a) brak odniesienia do wymagania/taska, (b) zielona Verification Strategy po usunięciu, (c) brak niezrozumianego komentarza.
4. The system shall NIE modyfikować plików testowych — testy są siecią bezpieczeństwa, nie celem redukcji.

### Requirement 5: Wpięcie w pipeline i routing

**Objective:** Jako Błażej, chcę żeby simplify był opcjonalnym krokiem po validate-impl a przed complete i nigdy nie blokował pipeline'u, aby był narzędziem higieny, nie kolejną twardą bramką.

#### Acceptance Criteria
1. The system shall plasować simplify w pipeline jako `impl → [validate-impl] → [simplify] → complete` (opcjonalny).
2. The system shall zawsze zwracać `BLOCKING: false` — simplify nigdy nie zatrzymuje przejścia do `complete`.
3. The system shall obsłużyć flagi `--apply`, `--debate`, `--no-debate`; routing FIRE/SKIP shall działać jak w `validate-impl` (czyta `debate_config.simplify` z `llm-routing.md`), a brak konfiguracji shall być traktowany jako solo Sonnet (`high_stakes` default).
4. The system shall emitować linię `Routing: <FIRE|SKIP> — <reason>` przed wywołaniem jakiegokolwiek subagenta.
5. The system shall kończyć verdict envelope zawierającym pola: `VERDICT`, `BLOCKING`, `FINDINGS`, `LOC_DELTA`, `APPLIED`, `NEXT_ACTIONS`.

### Requirement 6: Auto-fire na drifcie (opcjonalne, w `--full`)

**Objective:** Jako Błażej, chcę żeby pełny pipeline sam zaproponował simplify gdy impl dorzucił dużo kodu spoza tasks, aby drift nie wchodził cicho do INVENTORY.

#### Acceptance Criteria
1. Where `/blast:full` wykryje, że impl dodał istotnie więcej kodu niż przewidywały taski (sygnał driftu) lub LOC feature'a przekracza próg, the system shall zasugerować uruchomienie `/blast:simplify {feature}` przed `complete`.
2. The system shall pozostawić decyzję o uruchomieniu użytkownikowi (sugestia, nie przymus) — zgodnie z `BLOCKING: false`.
