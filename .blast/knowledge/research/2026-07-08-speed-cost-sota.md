# blast → szybciej i taniej: audyt + SOTA (2026-07-08)

Kontynuacja `2026-06-09-sota-proposals.md`. Metoda: pełny audyt implementacji czerwcowych propozycji (co weszło, co nie) + research aktualnego stanu API Anthropic / Claude Code / lokalnej inferencji (lipiec 2026). Wnioski posortowane wg impact/effort.

**Bilans czerwcowych propozycji:** 14/17 wdrożone lub prawie wdrożone (parallel impl, trzystopniowa eskalacja, lfm2.5 mechanical lane, mutation testing, EARS→stuby, risk-tiered autonomy, auto-remediation, verdict persistence, knowledge-index — działa). Dwa czyste braki: **1.4 odchudzenie promptów (regres: impl.md 467→508 linii, full.md 436→481)** i **4.6 drift-as-CI**. Częściowe: telemetria (parsuje dużo, ale **nie loguje tokenów ani kosztu**), pipelining (tylko validate-design∥tasks), Ollama hygiene (brak KV quant, brak stabilnych prefixów).

---

## 0. TL;DR — dziesięć ruchów, kolejność wdrożenia

| # | Zmiana | Effort | Zysk |
|---|---|---|---|
| 1 | Routing na **Sonnet 5 intro pricing** ($2/$10 do 31.08) + `effort` per agent | edycja frontmatter + llm-routing | koszt ↓ ~30–50% na fazach Sonnet |
| 2 | **Security: `always` → `high_stakes`** + Phase 1 jako skrypt + Sentinel na Sonnet | edycja llm-routing + security.md | ~$0.6–1.0 i ~1,5–2 min z KAŻDEGO fulla |
| 3 | **Telemetria kosztów**: zbieraj `eval_count` z bridge'a + usage z cloud | godziny | odblokowuje cost-policy (dziś martwa) |
| 4 | **Prefix-cache dyscyplina** (obie strony: Anthropic i Ollama) | przestawienie kolejności bloków | prefill ↓ 20–40% na najgorętszej pętli |
| 5 | **Steering digest** zamiast 7–8× czytania całego katalogu | 1 dzień | tokeny wejściowe ↓ na każdej fazie |
| 6 | Odchudzenie promptów (1.4, wciąż otwarte) + CLAUDE.snippet <200 linii, playbooki → skills | 1–2 dni | stały podatek od każdego spawnu ↓ |
| 7 | Bugfixy: privacy-gate nie łapie `ask_gemini_*`; `think:False` kastruje jurora qwen3.6; lint-gate „silently allow" | godziny | poprawność + jakość debat |
| 8 | Bridge: streaming + retry na ConnectError + reuse klienta; `OLLAMA_KV_CACHE_TYPE=q8_0`, `FLASH_ATTENTION=1`, jawny `OLLAMA_NUM_PARALLEL=3` | godziny | latencja ↓, parallel impl realnie równoległy lokalnie |
| 9 | Walidacja solo: **Haiku k=3 z rubryką** zamiast pojedynczego Sonneta | edycja validate-* | taniej i (wg badań) celniej |
| 10 | **Batch API (−50%)** dla faz nieinteraktywnych + `task_budget` na pętle TDD | średni | koszt ↓ na sweepach, kaput runaway loops |

Szacunek łączny: mediana `/blast:full` ~$2 (spike‑3) → realnie **$0.6–1.0** i o kilka minut krócej, bez utraty jakości (security jury zostaje tam, gdzie daje zwrot).

---

## 1. Nowe dźwignie API (stan: lipiec 2026)

### 1.1 Cennik i lineup — routing table jest przestarzały
`llm-routing.md` operuje na claude-opus-4-6 / sonnet-4-6 / haiku-4.5. Aktualnie:

| Model | Input | Output | Uwagi |
|---|---|---|---|
| Opus 4.8 | $5 | $25 | rekomendowany do complex agentic coding |
| **Sonnet 5** | **$2 / $10 do 31.08.2026**, potem $3/$15 | | intro pricing — okno na przełączenie |
| Sonnet 4.6 | $3 | $15 | |
| Haiku 4.5 | $1 | $5 | bez zmian |

Ruchy: (a) wszystkie role `claude-sonnet` → `claude-sonnet-5` przed końcem intro; (b) design/security zostają na Opus 4.8 ($5/$25 — dużo taniej niż stary Opus 4.1). **Uwaga rekalibracyjna:** tokenizer Opus 4.7+/Sonnet 5 emituje ~30% więcej tokenów za ten sam tekst — po migracji przelicz ceilingi w `cost-policy.md` na nowo (p75/p95 z nowej telemetrii, patrz §3).

### 1.2 Parametr `effort` — brakujący wymiar Waszego tieringu
Routing tieruje MODEL per faza, ale nie tieruje WYSIŁKU. Od Opus 4.5+/Sonnet 4.6+ jest `effort: low|medium|high|xhigh` (kontroluje wszystkie tokeny wyjściowe, w tym thinking; default `high`). W Claude Code ustawiane per subagent we frontmatter. Mapowanie dla blast:

- Scribe/Loom/Ledger/Delta (mechaniczne): Haiku bez zmian, albo Sonnet 5 `effort: low` (często lepszy niż Haiku z retry, porównywalny koszt),
- Auditor/Pragmatist/Crucible (walidacja): Sonnet 5 `effort: medium` (wg docs ≈ jakość Sonnet 4.6 `high`, taniej),
- Atlas/Sentinel: Opus 4.8 `high` (default) — bez zmian,
- Forge (cloud-eskalacja): Sonnet 5 `medium`, `xhigh` tylko przy eskalacji architektonicznej.

Dodatkowo beta `task_budget` (Opus 4.7+): advisory limit tokenów, który model widzi i sam się tempuje — idealne na runaway pętle TDD w impl (dziś ogranicza je tylko licznik prób).

### 1.3 Batch API — 50% zniżki na fazy, które nie muszą być „teraz"
Sumuje się z cachingiem. Kandydaci w blast: nocne security sweepy po wielu specach, `/blast:drift --all`, masowa re-walidacja po zmianie steering, benchmarki `blast-bench`. Wynik ≤24 h (zwykle szybciej).

### 1.4 Drobne
- Token-efficient tool use jest już wbudowany (beta header to no-op — usunąć, jeśli gdzieś został).
- Structured outputs GA: verdict envelope jako `json_schema strict` zamiast „MANDATORY tail block" w prozie — zero re-asków, tańszy parsing (i można skasować zduplikowane 25-liniowe bloki z 3 agentów).
- Explore agent w Claude Code od v2.1.198 **dziedziczy model główny** (już nie Haiku) — jeśli gdzieś liczycie na tanią eksplorację, zdefiniować własnego agenta z `model: haiku`.
- Fast mode (Opus 4.8, 2× cena za ≤2,5× tok/s) — dźwignia latencji na deadline'y, nie kosztu.

---

## 2. Security — największy pojedynczy przeciek kredytów

Stan: `security.trigger: always` + JURY_3_FLASH3 na **każdym** przebiegu, a orkiestrator Sentinel to Opus, który spawnuje opus(B — pełne źródła w prompcie) + opus(C) + haiku(A). Własne dane spike‑3 mówią: jury vs solo = **+0.05 recall za +$0.57 i +96 s** (przy tej samej precision 0.57).

Zmiany (spójne z filozofią „debata tam, gdzie dywersyfikacja korpusu ma zwrot"):
1. `trigger: always` → `high_stakes` (risk_level=high / security_critical / sensitive paths). CRUD-owy spec nie płaci jury.
2. Phase 1 (mechaniczny skan grep/secret/deps) → **skrypt** (semgrep + trufflehog/gitleaks + pip-audit), 0 tokenów, <10 s. To jest dokładnie logika propozycji 1.3, nigdy niezastosowana do security.
3. Sentinel (dispatch/merge/dedup JSON-ów) → Sonnet; Opus zostaje tylko w sub-agencie B (deep review) i tylko high_stakes.
4. Sub-agent B nie wkleja pełnych źródeł do prompta — zakres z `git diff` speca + semble.

## 3. Telemetria kosztów — bez tego cost-policy nigdy nie wystartuje

Schemat rekordu ma tylko `prompt_chars`/`result_chars`. Bridge **już zwraca** `eval_count`/tok/s w nagłówku metadanych, Gemini zwraca `usage` — nic tego nie zbiera. Efekt: `blast-learn --calibrate` i cały plan „warning_at=p75, block_at=p95" z cost-policy.md są trwale zablokowane, a ceilingi z 2026-05-06 nie mają pętli zwrotnej (i po zmianie tokenizera będą błędne).

Zmiana: telemetry hook parsuje nagłówek bridge'a + szacuje tokeny cloud (chars/4 do czasu, aż hook dostanie realne usage), dolicza cennik z §1.1, pisze `cost_usd` per run. Po 2 tygodniach danych: rekalibracja ceilingów i włączenie hard limits na dobre.

## 4. Prompt-cache dyscyplina (obie strony)

**Anthropic:**
- Hierarchia cache: tools → system → messages; treść stabilna na początku, zmienna na końcu. Tymczasem `blast-approval-gate.py` (L135) **wymusza dynamiczną linię `Feature: <name>` na początku** każdego gated prompta — to unieważnia cache całego statycznego ogona między feature'ami. Zmiana: hook czyta feature z końca prompta albo ze spec.json; szablony promptów: stały preamble → dynamiczny tail.
- `ENABLE_PROMPT_CACHING_1H=1` na kluczach API — fazy z ludzkimi przerwami >5 min przestają płacić pełny re-read.
- Haiku cache'uje dopiero od 4096 tokenów — krótkie prompty mechanicznych faz poniżej progu po prostu się nie cache'ują (świadomie zaakceptować albo współdzielić prefix powyżej progu).
- Nie przełączać modeli w ramach jednej sesji (każdy model = osobny cache) — per-fazowe subagenty już to załatwiają, nie psuć tego „ręcznym" `/model` w środku pipeline'u.

**Ollama:** szablon delegacji w impl.md układa prompt: nagłówek → dynamiczny task → dynamiczny design → dynamiczne testy → **statyczny code-principles.md na końcu**. Prefix-cache Ollamy reużywa tylko wspólny PREFIX, więc każdy task re-prefilluje cały statyczny blok. Zmiana: code-principles + stałe instrukcje do parametru `system` bridge'a (wspiera go, szablon go nie używa) — statyka trafia na początek i cache'uje się między wszystkimi taskami fali. Do tego: `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_FLASH_ATTENTION=1`, jawnie `OLLAMA_NUM_PARALLEL=3` w konfigu hosta (dziś tylko komentarz w impl.md — jeśli nieustawione, „równoległe" waves serializują się na GPU).

## 5. Steering digest — koniec z 7–8× re-readem

„Read the entire `.blast/steering/`" występuje dosłownie w 6 agentach (plus research/security de facto). W dojrzałym projekcie to 1–2k linii tokenizowanych 7–8× na pipeline. Zmiana: Cartographer utrzymuje wygenerowany `steering-digest.md` (~150 linii: decyzje, konwencje, wskaźniki do plików źródłowych); fazy czytają digest, pełne pliki tylko na żądanie (drill-down przez semble/knowledge-index). Wyjątek: design może dalej czytać całość.

## 6. Odchudzenie promptów — propozycja 1.4, wciąż otwarta (i regres)

Liczby dziś: impl.md **508**, full.md **481**, complete.md **405**, quick.md **345**; 7 komend = 1 771 linii, 14 agentów = 3 071 linii. Zduplikowane verbatim: blok semble (6 agentów), Verdict Envelope (~25 linii × 3), Verdict persistence (~20 × 2), persony (~15–20 × 14 ≈ 250 linii), logika init (3 kopie w full/quick/tiny). Zmiany:
- ekstrakcja duplikatów do `settings/rules/` (envelope → structured outputs z §1.4 i znika w ogóle),
- persony do 3–4 linii (rola + blind spot; „PEERS WHO CORRECT YOU" to flavor płacony przy każdym spawnie),
- `CLAUDE.snippet.md` (245 linii, jedzie w KAŻDYM kontekście, także subagentów) → <200 linii; playbooki per-workflow do **skills** (ładują się na żądanie, nie zawsze),
- cel bez zmian: żaden prompt >250 linii; egzekwować w blast-lint.

## 7. Bugfixy znalezione przy audycie (tanie, zrobić od razu)

1. **Privacy-gate dziura**: `EXTERNAL_TOOL_PATTERNS = [ask_openrouter_, ask_anthropic_, ask_cloud_]` — realny cloud tool bridge'a to `ask_gemini_3_flash_preview`, nie łapie się w żaden wzorzec → juror Gemini **omija bramkę prywatności**. Dodać `^ask_gemini_`.
2. **`think: False` globalnie w bridge'u** — także dla `ask_ubuntu_qwen36`, którego udokumentowana rola to „reasoning juror". Bridge odcina dokładnie to, za co routing go ceni. Per-tool flaga.
3. **Lint-gate „silently allow"**, gdy `blast-lint.py` nieobecny/nieodnaleziony — bramka, która przy braku strażnika przepuszcza wszystko, powinna głośno FAIL-ować (albo minimum WARN do telemetrii).
4. **Retrospekcja w complete pyta y/n per lesson** — zawiesza `--auto` na przedostatniej fazie; w trybie auto: zapisz kandydatów do pliku, zatwierdzanie batchowe później.
5. **Privacy-gate per tool call**: spawn Pythona + re-parsing 12,6 KB llm-routing.md + read/write JSON przy każdym Read/Edit/Grep — najgorętszy podatek latencji w sesji. Cache sparsowanych patterns (mtime-based) albo rejestracja tylko na Agent/Task + MCP.
6. **Bridge**: brak retry na ConnectError/5xx (jurorzy cicho znikają), `stream: False` przy timeoucie 240 s (do 4 min zamrożenia bez feedbacku), nowy AsyncClient per call. Jeden bounded retry + streaming + wspólny klient.

## 8. Walidacja solo: rubryka + małe modele k=3

Badania 2026 (LLM-as-judge): dopisanie **rubryki per faza** do prompta sędziego = +3 pp accuracy za darmo; ensemble małych sędziów (k=3, self-consistency) bije pojedynczego dużego przy ~1,2× kosztu MAŁEGO modelu. Dla blast: solo-ścieżka validate-* (dziś 1× Sonnet) → **3× Haiku 4.5 z rubryką i głosowaniem** (agregacja mechaniczna — lfm2.5/skrypt). Taniej niż Sonnet, wyżej recall, a spike'owa filozofia „debata opt-in" nietknięta — to nie debata, to tani ensemble. Rubryki per faza wyprowadzić z findings w `verdicts/*.json` (telemetria już je zbiera).

## 9. Lokalna inferencja — co się zmieniło od czerwca

- **Speculative decoding: nie dla Was.** Ollama dalej go nie ma, a benchmark na Qwen3.6-A3B pokazał zero zysku na 19 konfiguracjach — sparse-MoE z ~3B aktywnych parametrów jest za szybki, draft overhead dominuje. Nie inwestować.
- **vLLM tylko dla debat/fan-outu.** Przy batch=1 vLLM ≈ Ollama (~2% różnicy); przy concurrency 32+ vLLM ma 8–9× throughput + automatyczny cross-request prefix caching. Jeśli parallel impl + jury mają realnie fan-outować lokalnie, postawić vLLM obok Ollamy dla qwen3-coder; dla pojedynczej pętli TDD — zostać przy Ollamie.
- **Kandydaci do trialu na 5090** (benchmarki vendor/3rd-party — zweryfikować przez blast-bench na własnych taskach): Qwen3.6-35B-A3B (73.4% SWE-bench Verified, mieści się na 5090, 262k ctx) i Qwen3-Coder-Next-30B „Flash" (~18 GB). Uwaga na trade-off rezydencji: 35B-A3B może nie ko-fitować z lfm2.5 tak wygodnie jak obecny coder (17.3G) — decyzja po benchu, nie po tabelce.
- Higiena (§4): q8_0 KV, flash attention, num_parallel — to jest ta część propozycji 3.5, która nigdy nie weszła.

## 10. Pipelining — dokończyć to, co zaczęte

Wdrożone: validate-design ∥ tasks-draft. Brakuje:
- **security Phase 1 (po zeskryptowaniu — §2) startuje po pierwszej fali impl**, nie po complete,
- validate-impl `--prove` (testy+mutmut, ≤5 min ściany) ∥ przygotowanie complete (diff, checklisty),
- steering sync (Cartographer) → **background subagent** (Claude Code: subagenty w tle są default od v2.1.198) — nie blokuje zakończenia fulla,
- merge fal w impl: testy pełnej suity raz PO fali (per-merge tylko affected tests) — dziś N pełnych przebiegów suity na falę.

---

## Czego NIE robić

- Nie wracać do debat jako default — spike‑3 się nie zestarzał (+5% recall za 2× koszt), a §8 daje tańszą drogę do wyższego recall.
- Nie dodawać keyword-triggerów eskalacji bez świeżego spike'a (polityka „evidence-based" działa).
- Nie przenosić pojedynczej pętli TDD na vLLM ani nie włączać spec-dec dla modeli A3B.
- Nie kupować fast mode jako oszczędności — to 2× cena za latencję.

## Kolejność wdrożenia

Tydzień 1 (bezryzykowne, odwracalne): §7 bugfixy → §1.1+1.2 routing na Sonnet 5 + effort (okno intro do 31.08!) → §2 security demotion → §3 telemetria kosztów.
Tydzień 2: §4 cache-dyscyplina → §5 steering digest → §6 odchudzanie promptów.
Tydzień 3+: §8 ensemble walidacji → §10 pipelining → §9 trial modeli / vLLM dla debat → Batch API dla sweepów.

Po 2 tygodniach telemetrii z kosztami: rekalibracja `cost-policy.md` (nowy tokenizer!) i dopiero wtedy twarde limity.
