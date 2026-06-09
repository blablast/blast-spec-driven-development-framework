# blast → SOTA: propozycje zmian (2026-06-09)

Analiza całego `.blast` + `.claude/{commands,agents,hooks}`. Cztery osie: szybkość, jakość, Ollama/RTX 5090, walidacja bez human-in-the-loop. Posortowane wg impact/effort wewnątrz każdej sekcji.

---

## 1. Szybkość

### 1.1 Równoległy impl dla tasków `(P)` — największy zysk
Impl jest najcięższą fazą (10–30 min) i wykonuje taski **seryjnie** (impl.md, pętla "for each delegated task"), mimo że tasks.md ma markery równoległości i istnieje `tasks-parallel-analysis.md`. Zmiana:
- taski oznaczone `(P)` bez wspólnych plików → spawn równoległych Task calls (osobne konteksty, git index nie koliduje jeśli pliki rozłączne),
- limit współbieżności 2–3 (jeden strumień na qwen3-coder lokalnie + 1–2 cloud przy eskalacji),
- merge wyników: testy całości po zakończeniu fali, dopiero potem fala kolejna.
Szacunek: 2–3× szybszy impl przy typowym rozkładzie zależności.

### 1.2 Walidacja nakładkowa (pipelining faz)
`validate-design` jest read-only — nie musi blokować startu `tasks`. Wzorzec: odpal validate-design i tasks **równolegle**; jeśli verdict FAIL+BLOCKING, wyrzuć draft tasks (tani, Haiku) i wróć do design. Koszt odrzuconego draftu ~1–3k tokenów Haiku vs ~1–2 min zaoszczędzone w każdym przebiegu. To samo: security Phase 1 (skan mechaniczny) może ruszyć po pierwszej fali impl, nie po całym.

### 1.3 Deterministyczny lint zamiast LLM — 0 tokenów, <1 s
`lint.md` (112 linii) opisuje czysto mechaniczne checki: EARS regex, numeryczne ID, traceability req→task, sekcje w design.md. To powinno być skryptem `.blast/bin/blast-lint.py` (bez LLM), wołanym:
- jako PreToolUse hook przed spawnem spec-design/tasks/impl agenta (obok approval-gate),
- w CI / pre-push.
Analogicznie Gate 1–3 z quality-gates.md: ~70% kryteriów jest regex-owalnych. LLM zostaje tylko do checków subiektywnych (god-component, over-abstraction).

### 1.4 Odchudzenie najgrubszych promptów
`impl.md` agent 467 linii, `full.md` 436, `complete.md` 383, `quick.md` 340. Każde wywołanie płaci ten koszt w tokenach i TTFT. Wyciągnąć:
- tiering/eskalację z impl.md → `.blast/settings/rules/impl-routing.md` (ładowane raz, nie inline),
- retrospekcję z complete.md → template,
- wspólny approval-check z full/quick/tasks/impl → jedna rule (DRY, już zidentyfikowana duplikacja).
Cel: żaden prompt >250 linii. Bonus: stabilny, niezmienny preamble (steering + rules w stałej kolejności) → lepszy hit rate prefix cache po obu stronach (Anthropic i Ollama).

### 1.5 Tanie modele do mechaniki orkiestracji
debate-judge i aggregator już są na Haiku — dobrze. Dodatkowo: parsing verdict envelope, stalemate-similarity (Protocol C), digest telemetrii, update INVENTORY — to roboty dla lfm2.5 lokalnie (sekcja 3) albo zwykłego kodu.

---

## 2. Jakość

### 2.1 Uruchomić pętlę telemetrii — infrastruktura stoi pusta
`agent-runs.jsonl` ma 0 linii; `/blast:learn --calibrate|--routing` nie ma na czym pracować. Konstytucja Art. VIII obiecuje samodoskonalenie co 5 speców — martwy zapis bez danych. Zmiany:
- zweryfikować, czemu PostToolUse hook nie loguje (rejestracja w settings.json vs realne eventy),
- dodać do telemetrii: escalation_rate per task (qwen→Sonnet), czas fazy, verdict + liczba findings per walidator,
- `/blast:complete` co 5. spec automatycznie odpala `/blast:learn --all` (nie czeka na ręczne wywołanie).

### 2.2 Mutation testing jako obiektywny sygnał jakości testów
TDD (Art. VI) gwarantuje, że testy istnieją — nie że coś sprawdzają. qwen potrafi pisać testy-tautologie. W `validate-impl --prove` dodać krok: `mutmut run --paths-to-mutate {changed_files}` (Python) z progiem np. mutation score ≥70%. To jest **deterministyczny** miernik jakości testów — dokładnie to, czego potrzeba do odpięcia człowieka (sekcja 4). Tanio: mutacje tylko na plikach zmienionych w tym specu.

### 2.3 Wykonywalne Verification Strategy
design.md ma sekcję Verification Strategy (komendy + Expected Signal), ale to proza. Zmiana formatu na blok YAML:
```yaml
verify:
  - run: pytest tests/test_auth.py -k reset
    expect_exit: 0
  - run: curl -s localhost:8000/health
    expect_contains: '"ok"'
```
`validate-impl --prove` wykonuje je mechanicznie i porównuje — PASS/FAIL bez sędziego LLM. Wymusić obecność ≥1 wpisu per komponent w Gate 2.

### 2.4 Podpiąć knowledge-index.sqlite (dziś 0 bajtów)
Pusty plik = `/blast:research` i design nie mają retrieval. Minimalna wersja: indeks embeddingowy nad INVENTORY.md + decisions/ + sota/ (lokalny model embeddingowy na Ollamie, np. nomic/qwen-embedding). Design agent przed projektowaniem robi query "czy coś takiego już mamy" → twardsze egzekwowanie Art. VII (DRY cross-spec) niż dzisiejsze "przeczytaj INVENTORY".

### 2.5 Debata: mniej, ale ostrzej
Spike-3: multi-LLM debate daje tylko +5% recall vs solo Opus — słusznie zdegradowane do opt-in. Konsekwentnie:
- budżet przesunąć z debat na deterministykę (2.2, 2.3) — wyższy zwrot,
- w protokołach: każdy critic musi dostarczyć ≥1 **falsyfikowalne** twierdzenie z komendą weryfikującą ("ten endpoint nie waliduje X — sprawdź: curl ..."), inaczej finding nie liczy się do verdict. Tnie waterowane findings, które dziś zawyżają WARN.
- Anti-plateau guard zostaje (dobry mechanizm).

### 2.6 Pamiętaj o blind spocie Qwena
Spike-3: Qwen słaby w observability/parser code. Dodać do llm-routing.md regułę eskalacji: task dotykający parserów/instrumentacji → od razu Sonnet (to wyjątek empiryczny, zgodny z filozofią "eskalacja na dowodach" — dowód już jest).

---

## 3. Ollama / RTX 5090 — routing pod realne modele

Stan: impl woła `qwen3.6:27b`; jurorzy `qwen3.6` + `qwen3-coder`. Dostępne modele i sensowne role:

| Model | VRAM | tok/s | Rola docelowa |
|---|---|---|---|
| **qwen3-coder** | 17.3G | ~160 | **Domyślny impl codegen** |
| **lfm2.5** | 4.8G | ~580 | Mechanika: parsing, draft, digest, judge w privacy mode |
| **qwen3-coder-next** | 48.2G | ~50 | Lokalna eskalacja (tier 2) przed cloudem |
| **qwen3.6** | 22.3G | ~243 | Juror/krytyk w debatach (reasoning), NIE impl |
| **gemma4** | 18.5G | ~16 | Tylko juror security w privacy mode (dywersyfikacja korpusu); poza tym drop |

### 3.1 Zamiana domyślnego modelu impl: qwen3.6 → qwen3-coder
qwen3.6 ma wyższe surowe tok/s (243 vs 160), ale produkuje dużo thinkingu — **efektywna** przepustowość kodu jest niższa, a thinking w pętli TDD to czysty koszt. qwen3-coder: mniej thinkingu, profil coder, mniejszy footprint. Dodatkowo:

**Kluczowy argument VRAM:** qwen3-coder (17.3G) + lfm2.5 (4.8G) = 22.1G → **oba rezydentne naraz na 5090 (32G)** z zapasem na KV cache. Z qwen3.6 (22.3G) drugi model już się nie mieści wygodnie → swapowanie modeli (sekundy za każdym razem). Ustawić `keep_alive=-1` dla obu i nigdy nie ładować trzeciego w trakcie impl.

### 3.2 Trzystopniowa eskalacja impl (zamiast dwustopniowej)
```
qwen3-coder (160 tok/s, default)
  → red testy / 2 nieudane próby → qwen3-coder-next (50 tok/s, lokalnie, $0)
    → nadal red / problem architektoniczny → Sonnet (cloud)
```
qwen3-coder-next jako bufor wyłapie sporo tasków, które dziś idą do Sonneta. Uwaga: 48.2G > 32G VRAM → częściowy offload na CPU (stąd 50 tok/s) i wymusza zrzucenie pozostałych modeli; używać go **tylko** w trybie eskalacji, jako świadomy swap. Cel z telemetrii: cloud-escalation rate <10% (dziś próg 20% dla jednego stopnia).

### 3.3 lfm2.5 — wycisnąć 580 tok/s do roboty mechanicznej
- **Draft-then-verify:** lfm2.5 generuje scaffolding (boilerplate testów, fixtures, dataclassy, sygnatury z design.md), qwen3-coder weryfikuje/poprawia. Wzorzec speculative-decoding na poziomie tasków: drafty kosztują grosze czasu, weryfikacja jest szybsza niż generacja od zera.
- Parsing verdict envelopes, podsumowania scratchpadów debat, stalemate-similarity, digest telemetrii do `/blast:learn`, draft commit messages.
- W **privacy mode (local-only):** judge + aggregator przechodzą z Haiku na lfm2.5 (dziś privacy mode wrzuca wszystko na qwen3.6 — marnotrawstwo na role mechaniczne).

### 3.4 Drugi węzeł (RTX 4090, 192.168.5.70) do debat
Jury 3-osobowe w privacy mode dziś musi serializować modele na jednym GPU (swap za swapem). Wystawić Ollamę na Win11/4090 i wpisać do llm-routing.md jako drugi endpoint: juror A na 5090, juror B na 4090 **równolegle**. Czas jury lokalnego spada ~2×, zero zmian w protokole.

### 3.5 Higiena Ollamy
- `num_ctx` per rola: impl 16–32k; lfm2.5 do mechaniki 4–8k (mniejszy KV = więcej miejsca i szybciej).
- Stałe prefiksy promptów per agent → Ollama prefix cache działa (ping-llm już testuje bypass — wykorzystać świadomie w drugą stronę: **chcemy** cache hit na preamble).
- Quantized KV cache (`OLLAMA_KV_CACHE_TYPE=q8_0`) jeśli kontekst impl rośnie.

---

## 4. Walidacja → odpięcie human-from-the-loop

Filozofia: człowieka można odpiąć tam, gdzie werdykt jest **deterministyczny lub probabilistycznie tani do zweryfikowania**; zostaje tam, gdzie błąd jest drogi i nieodwracalny. Konkretnie:

### 4.1 Risk-tiered auto-approve (zamiast binarnego `-y`)
Dziś: ręczny `/blast:approve` albo globalny bypass `-y` — oba złe na autonomię. Zmiana — pole `autonomy` w spec.json wyliczane z obiektywnych cech:
```
LOW    → auto-approve wszystkich faz      (tiny, brak nowych zależności, brak migracji,
                                           security_critical=false, pliki tylko w module X)
MEDIUM → auto-approve gdy lint PASS + validator PASS + mutation score ≥ próg
HIGH   → human approve (security_critical, public API, migracje danych, auth, płatności)
```
Hook `blast-approval-gate.py` już jest SDK-level (Art. X) — rozszerzyć go o czytanie `autonomy` zamiast tylko `approvals.*.approved`. Człowiek przestaje być bramką, staje się eskalacją.

### 4.2 Bounded auto-remediation loop
Dziś FAIL+BLOCKING = stop i czekanie na człowieka. Zmiana: orchestrator dostaje budżet napraw:
```
FAIL → feedback z findings wraca do agenta fazy → regeneracja → re-walidacja
     → max 2 cykle / max $X (cost-policy.md) → dopiero wtedy human
```
Findings z verdict envelope są już strukturalne — nadają się wprost jako wsad do regeneracji. Logować każdy cykl do telemetrii (czy auto-fix konwerguje — jeśli nie, to sygnał kalibracji promptów, nie zwiększania budżetu).

### 4.3 Acceptance tests z EARS — requirements stają się wykonywalne
Każde kryterium EARS ma strukturę When/shall → kompiluje się do szkieletu testu. Nowy krok w `/blast:tasks`: wygeneruj `tests/acceptance/test_{feature}.py` ze stubów (po jednym na kryterium, `@pytest.mark.req("3.2")`). Gate przed impl: stuby istnieją i są **red**. Gate completion: wszystkie **green**. To zamyka traceability req→test→kod mechanicznie — dziś traceability sprawdza LLM, czytając markdown.

### 4.4 Twarde minimum bramek na complete (bez człowieka)
`/blast:complete` przepuszcza tylko gdy wszystkie deterministyczne:
1. blast-lint exit 0,
2. acceptance testy green (4.3),
3. coverage na zmienionych plikach — **signal-only** (zgodnie z decyzją z 2026-05-29), ale logowany,
4. mutation score ≥ próg (2.2),
5. security Phase 1 (skan mechaniczny) bez findings CRITICAL,
6. `verify:` bloki z design.md wykonane z oczekiwanym sygnałem (2.3).
LLM-walidatory (Crucible/Auditor) zostają jako WARN-producers; **blokować mogą tylko checki deterministyczne** — to usuwa największe źródło niestabilności autonomii (flaky LLM-FAIL na granicy).

### 4.5 Audyt zamiast nadzoru
Skoro człowiek znika z pętli, musi mieć ślad po fakcie:
- verdict envelopes zapisywane jako `verdicts/{phase}.json` per spec (dziś żyją w transkrypcie),
- `/blast:status --digest` generowany po każdym `complete` (co się zbudowało, co auto-zaaprobowano, escalation rate, koszt) — lfm2.5, $0,
- nieusuwalny append-only log decyzji auto-approve w `.blast/logs/` (kto/co/dlaczego przeszło bez człowieka).

### 4.6 Drift jako CI, nie komenda
`/blast:drift` odpalany ręcznie nie złapie regresji. Pre-push hook: blast-lint --all + drift na zmienionych specach. Spec, który skłamał, nie wychodzi z repo.

---

## Kolejność wdrożenia (impact × effort)

| # | Zmiana | Effort | Impact |
|---|---|---|---|
| 1 | 3.1 qwen3-coder jako default impl + lfm2.5 rezydentny | edycja llm-routing.md + MCP bridge | szybkość ↑↑, $0 |
| 2 | 1.3 deterministyczny blast-lint.py | 1 dzień | szybkość ↑, fundament pod 4.x |
| 3 | 2.1 naprawa telemetrii | godziny | odblokowuje learn/kalibrację |
| 4 | 1.1 równoległy impl `(P)` | zmiana impl.md + full.md | szybkość ↑↑ |
| 5 | 4.1 + 4.2 risk-tiered autonomy + auto-remediation | rozszerzenie hooka + orchestratorów | autonomia ↑↑ |
| 6 | 2.2 + 4.3 mutation testing + EARS→testy | 2–3 dni | jakość ↑↑, warunek autonomii |
| 7 | 3.2 trójstopniowa eskalacja (coder-next) | edycja routing + bridge | jakość ↑, koszt ↓ |
| 8 | 3.4 jury na dwóch GPU | konfiguracja | szybkość debat ↑ |
| 9 | 2.4 knowledge-index | 1–2 dni | DRY, jakość design |

Pozycje 1–3 są bezryzykowne i odwracalne — od nich zacząć.
