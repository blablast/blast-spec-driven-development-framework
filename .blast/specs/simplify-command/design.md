# Design — `/blast:simplify`

> SZKIC. Napisany przed formalnym `init`/`requirements` (dogfooding). Decyzje tu są wstępne — do zatwierdzenia.

## Overview

`/blast:simplify` to **counter-pressure step**: jedyny krok w pipeline który złożoność *odejmuje*, a nie dokłada. Wszystkie pozostałe fazy (requirements → design → tasks → impl) narastają — dokładają artefakty, kod, abstrakcje. SDD jako metodologia złożoności nie usuwa, tylko ją *relokuje* (InfoQ 2026). simplify domyka tę lukę.

- **Purpose**: po implementacji znaleźć i (opcjonalnie) usunąć złożoność, której nie da się odnieść do żadnego wymagania/taska — z **gwarancją zachowania zachowania** (testy zielone po cięciu).
- **Users**: Błażej, na shipped/zaimplementowanym specu, gdy impl dorzucił rzeczy spoza tasks (drift) albo gdy kod „spuchł".
- **Impact**: nowa komenda + agent, opcjonalne wpięcie w pipeline po `validate-impl`, przed `complete`. Zero zmian w istniejących fazach.

### Goals

- Redukcja netto: mniej LOC / mniej abstrakcji robiących to samo.
- Behavior-preserving: po `--apply` re-run Verification Strategy z `design.md`; bez zielonych testów → revert.
- Traceability-driven: kod nieodnoszący się do żadnego wymagania/taska = kandydat do usunięcia (drift).
- Differentiator: krok, którego nie ma ani Spec Kit ani Kiro.

### Non-Goals

- **Nie jest drugim `review`.** review (Compass) = szeroki audyt jakości (SOLID, docstringi, nazewnictwo, lint, scorecard). simplify = wąski, redukcyjny, behavior-preserving. Jeśli jedyną poprawką jest *dodanie* abstrakcji — to robota review, nie simplify.
- **Nie jest `validate-tasks`.** validate-tasks (Pragmatist) = KISS+YAGNI *przed* impl, na poziomie planu. simplify = *po* impl, na poziomie kodu. Komplementarne, nie konkurencyjne.
- **Nie robi dedup (DRY-first).** Deduplikacja zwykle *dokłada* abstrakcję (double-edged — patrz Rule of Three). To bias review, nie simplify. simplify usuwa abstrakcje które kosztowały więcej niż duplikacja którą zniosły.
- Nie zmienia kontraktów publicznych ani zachowania widocznego z zewnątrz. Refactor czysto wewnętrzny.

## Kluczowa decyzja: standalone komenda vs tryb `review --simplify`

Rozważone dwie opcje:

| | Standalone `/blast:simplify` | Tryb `/blast:review --simplify` |
|---|---|---|
| Reużycie silnika „find" review | duplikuje część skanu | reużywa |
| Distinct kontrakt (find→remove→prove) | czysty, własny verdict | rozmywa się w review |
| Bramka Verification Strategy (apply gate) | naturalne | obce do review (review nie odpala testów behawioralnych) |
| Pipeline slot (osobny, opcjonalny) | tak | nie (review jest on-demand) |
| Koszt utrzymania | +1 komenda +1 agent | +1 flaga |

**Decyzja: standalone komenda + agent.** Powód: kontrakt simplify (usuń + udowodnij behawior przez Verification Strategy) jest jakościowo inny od „znajdź i zaraportuj" review. Bramka apply (re-run testów, revert przy czerwonych) to nie jest tryb przeglądu — to transformacja. Mieszanie tego z review zaciemnia oba. Koszt +1 komenda jest akceptowalny, bo agent jest cienki (deleguje „find" do podzbioru reguł, nie kopiuje całego scorecardu review).

**Ryzyko (uczciwie):** to jest moment gdzie sam framework może złamać Rule #2 (Simplicity first) — dodajemy komendę. Mitygacja: agent simplify NIE replikuje scorecardu review; importuje tylko 6 osi redukcyjnych (niżej) i dokłada warstwę verify+apply. Jeśli po 5 użyciach okaże się że pokrywa się z review w >70% → scalić do flagi (zapisać jako lesson w `/blast:learn`).

## Co simplify sprawdza (odpowiedź na „czy to tylko KISS i YAGNI?")

Nie tylko. Sześć osi, wszystkie **redukcyjne** (każde cięcie = mniej kodu):

1. **Spec-traceability / drift** *(oś natywna blast — tego nie ma nikt)* — czy każdy nietrywialny element kodu odnosi się do wymagania (`requirements.md`) lub taska (`tasks.md`)? Kod bez śladu = drift wprowadzony przez impl → kandydat do usunięcia. Wykorzystuje linkację spec↔kod, której Spec Kit/Kiro nie utrzymują tak ściśle.
2. **YAGNI** — flexibility/parametryzacja/hooki bez wymagania w bieżącym specu. „Might need someday" = wytnij.
3. **KISS / przedwczesna abstrakcja** — interfejs/generic/factory/ABC dla single-use; warstwy indirection przepuszczające wywołanie dalej; clever code.
4. **Dead code** — nieosiągalne gałęzie, nieużywane eksporty/importy, zakomentowane bloki (VCS pamięta).
5. **Defensive overkill** — obsługa błędów dla niemożliwych stanów, guardy na wartości gwarantowane przez typ/kontrakt wyżej.
6. **Config/flag sprawl** — opcje/flagi/ustawienia których nikt nie zamówił; dynamiczna konfiguracja dla wartości stałych.

Oś #1 to differentiator. Reszta pokrywa się z regułami `code-principles.md`, ale tu są stosowane **redukcyjnie i behavior-gated**, nie jako raport jakości.

### Karpathy alignment — mandat i hamulec

simplify domyka dwie zasady z `ai-collaboration.md` (= cztery zasady Karpathy'ego, 152k⭐ community canon):

- **Mandat — Rule 2 (Simplicity first).** Pitfall Karpathy'ego *„bloated construction over 1000 lines when 100 would do"* to dosłowne uzasadnienie istnienia simplify. simplify jest **ramieniem egzekucyjnym** Rule 2 — pasywna zasada staje się aktywną bramką z metryką `LOC_DELTA`.
- **Hamulec — Rule 3 (Surgical changes).** simplify usuwa kod, więc MUSI działać pod rygorem Rule 3:
  - **Ochrona komentarzy**: nigdy nie usuwaj komentarza/kodu którego intencji nie rozumiesz — nawet jeśli wygląda na osierocony. Kandydat z niezrozumiałym komentarzem → downgrade do report-only, człowiek decyduje.
  - **Granica zastanego dead-code**: Rule 3 mówi „nie usuwaj zastanego dead code bez polecenia". simplify **jest** tym poleceniem — ale licencja jest wąska: wolno usunąć tylko kod który (a) nie odnosi się do żadnego wymagania/taska, (b) po usunięciu Verification Strategy zostaje zielony, (c) nie niesie komentarza którego nie rozumiesz. Wszystkie trzy naraz albo zostaje.

## Architecture

```
/blast:simplify {feature} [--apply] [--debate] [--no-debate]
        │
        ├─ routing (jak validate-impl: czyta llm-routing.md → FIRE/SKIP)
        │
        └─ simplify-agent (Occam)
              1. Load: spec.json, requirements.md, tasks.md, design.md (Verification Strategy!), code-principles.md, steering/tech.md+structure.md
              2. Discover: pliki kodu feature'a (z design.md Components + glob)
              3. Scan 6 osi → lista findingów (REMOVE candidates), severity + LOC delta
              4. Tryb domyślny (raport): wypisz findingi, NIE dotykaj kodu
              5. Tryb --apply:
                   a. baseline: odpal Verification Strategy → musi być zielone NA STARCIE (inaczej STOP — nie tnij zepsutego)
                   b. zastosuj cięcia (Edit), zaczynając od najbezpieczniejszych (dead code → drift → abstrakcje)
                   c. re-run Verification Strategy
                   d. zielone → zostaw + raport (LOC before/after); czerwone → revert (git checkout dotkniętych plików) + raport co odpadło
              6. Verdict envelope
```

### Relacja do istniejących agentów

- **Pragmatist** (validate-tasks) — robi to samo myślenie KISS/YAGNI, ale na planie *przed* impl. simplify to jego post-impl odpowiednik.
- **Compass** (review) — szerszy audyt; simplify pożycza podzbiór jego reguł (osie 2-6) ale dokłada traceability (#1) i bramkę verify+apply.
- **Auditor** (validate-impl) — dostarcza wzorzec routingu i to on jest „przed" simplify w pipeline (najpierw udowodnij że działa, potem odchudzaj).

## Components and Interfaces

| Component | Layer | Intent | Key Dependencies |
|-----------|-------|--------|------------------|
| `simplify.md` (slash) | command | parse args, routing FIRE/SKIP, spawn agent | llm-routing.md, debate |
| `simplify-agent` (Occam) | agent | skan 6 osi, raport, --apply z verify-gate | code-principles.md, design.md::Verification Strategy |

### Kontrakt agenta (verdict envelope)

```
---VERDICT---
VERDICT: <PASS|WARN|FAIL>
BLOCKING: <true|false>      # false zawsze (simplify jest opcjonalny, nie blokuje pipeline)
FINDINGS: <int>            # liczba REMOVE candidates
LOC_DELTA: <-N|0>         # netto linii (tylko w --apply; ujemne = sukces)
APPLIED: <true|false>     # czy cięcia zastosowane i testy zielone
NEXT_ACTIONS:
- <komenda>
---END---
```

`BLOCKING: false` zawsze — simplify nigdy nie zatrzymuje `complete`. To narzędzie higieny, nie bramka jakości.

## Verification Strategy

**MANDATORY** (sam dla siebie, bo simplify operuje na cudzej Verification Strategy — musi mieć własną).

### Local Test Command
```bash
# Smoke na strukturze komendy/agenta (markdown well-formed, frontmatter valid):
python -c "import yaml,sys; yaml.safe_load(open('.claude/agents/blast/simplify.md').read().split('---')[1])"
```

### Smoke Check
```bash
# Agent file ma wymagane sekcje:
grep -q 'verdict envelope' -i .claude/agents/blast/simplify.md && grep -q 'Verification Strategy' .claude/agents/blast/simplify.md && echo OK
```

### End-to-End Probe
```bash
# Na realnym (zaimplementowanym) specu: tryb raportu nie dotyka kodu
/blast:simplify <jakiś-shipped-feature>
# Oczekiwanie: lista findingów, git status czysty (zero zmian w trybie bez --apply)
```

### Expected Signal
- Local test → `exit 0` (frontmatter parsuje się)
- Smoke → `OK`
- E2E → raport findingów + `git status` bez zmian (tryb domyślny); w `--apply` → LOC_DELTA ≤ 0 i testy feature'a zielone

## Pipeline placement

```
... → impl → [validate-impl] → [simplify] → complete → security → ...
```

Opcjonalny (nawias), jak walidacje. Po validate-impl (najpierw dowód że działa), przed complete (żeby INVENTORY zapisał odchudzony kształt). Auto-fire heurystyka (jak validate-tasks „auto-fires on complex specs"): gdy impl dodał istotnie więcej kodu niż przewidywały taski (sygnał driftu) lub LOC feature'a > próg.

## Routing & model

- Sonnet solo (code reasoning, nie architektura) — jak review/validate-impl.
- `--debate` → HYBRID dla auth/payments/schema (przez `debate_config.simplify` w llm-routing.md).
- `--no-debate` → downgrade na solo.

## Risks & Mitigations

| Ryzyko | Mitygacja |
|---|---|
| Nakładka z review (Compass) | Agent importuje tylko osie 2-6, nie scorecard; jeśli >70% pokrycia po 5 użyciach → scal do `review --simplify` (lesson w `/blast:learn`) |
| „Simplify" wycina coś co było potrzebne ale nieudokumentowane | Bias na raport; `--apply` tylko za zielonymi testami + revert przy czerwonych; finding #1 (drift) zawsze proponuje, człowiek decyduje |
| Framework łamie własne Rule #2 dodając komendę | Cienki agent, opcjonalny krok, zero zmian w istniejących fazach; explicit kill-switch (scal do flagi) jeśli się nie obroni |
| Verification Strategy feature'a niekompletna | STOP z findingiem „Verification Strategy incomplete" — nie tnij bez sieci bezpieczeństwa (wzorzec z validate-impl Prove Mode) |
