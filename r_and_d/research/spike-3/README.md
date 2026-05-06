# Spike #3 — Multi-LLM Code Review Validation

**Źródło**: `../../decisions/2026-05-05-sdd-number-one-roadmap.md` Phase 0
**Data**: 2026-05-06
**Tagi**: spike, fala-9, debate, multi-llm, code-review, jury, hybrid
**Status**: PROVISIONED, READY TO RUN

---

## Cel

Empirycznie zwalidować premise Fal 9-10: czy multi-LLM review wnosi mierzalną wartość (recall) nad solo Claude opus, i przy jakim koszcie.

Kluczowe pytania:

1. Czy **HYBRID** (Sonnet ‖ qwen3.6:latest → Haiku judge) wygrywa z **SONNET_SOLO**? O ile? Za jaki koszt premium?
2. Czy **JURY_3** (Opus ‖ Qwen ‖ Gemini → aggregator) wygrywa z **CONTROL** (solo Opus)? O ile?
3. Czy **QWEN_SOLO** w ogóle łapie bugi na poziomie umożliwiającym użycie Qwena jako parallel critic, czy jest catastrophic miss?
4. False positive rate — czy multi-model arms produkują noise który zalewa real findings?

## Metoda

5 fragmentów Pythona (~30-50 linii każdy), w sumie **18 planted bugs** o znanej trudności i kategorii. Każdy fragment puszczany przez 5 arms, findings każdego arm matchowane keyword-fuzzy do ground truth.

### Snippets (`snippets/*.py`)

| File | Lines | Bugs planted | Severities |
|---|---:|---:|---|
| `01_cache.py` | 44 | 3 | 2 medium, 1 low |
| `02_auth_session.py` | 38 | 4 | 2 high, 1 medium, 1 low |
| `03_worker_pool.py` | 44 | 4 | 1 high, 3 medium |
| `04_migration.py` | 43 | 4 | 2 high, 1 medium, 1 low |
| `05_parser.py` | 48 | 3 | 3 medium |

Pełna definicja bugów: `ground_truth.json` (NIE pokazywać modelom — używane tylko przez `score.py`).

### Arms

| Arm | Skład | Co testujemy |
|---|---|---|
| `CONTROL` | solo Claude opus | baseline ceiling |
| `QWEN_SOLO` | solo qwen3.6:latest (Ollama) | czy lokalny Qwen w ogóle łapie? |
| `SONNET_SOLO` | solo Claude sonnet | aktualny default `validate-impl` |
| `JURY_3` | Opus ‖ qwen3.6 ‖ Gemini-2.5-Pro → Haiku aggregator | klasyczny Pattern B |
| `HYBRID` | Sonnet ‖ qwen3.6:latest → Haiku judge | tani 2-corpus reviewer (Twój pomysł) |

### Matching rule

A finding "łapie" planted bug jeśli **dowolny keyword** z `bug.keywords` (case-insensitive) pojawia się w `finding.title + finding.description + finding.suggested_fix`. Każdy finding może matchować maksymalnie jeden bug (greedy, max keyword overlap).

- TP = liczba unikalnych planted bugs zmatchowanych
- FP = findings które niczego nie zmatchowały (noise lub bonus signal)
- FN = planted bugs nie złapane przez nikogo
- Recall = TP / (TP + FN); Precision = TP / (TP + FP); F1 standard

## Decision matrix (PRE-COMMITTED — wypełniamy dopiero po runie)

| Wynik | Verdict |
|---|---|
| HYBRID recall ≥ SONNET_SOLO + 0.10 przy cost ≤ 1.5× | HYBRID jako default `validate-impl`. Sonnet-solo deprecated. |
| HYBRID recall ≈ SONNET_SOLO (delta < 0.05) | qwen3.6 jako critic nie wnosi sygnału. Default = SONNET_SOLO. |
| JURY_3 recall ≥ CONTROL + 0.15 przy cost ≤ 2× | JURY_3 default dla high-stakes faz (`security`, `validate-design`). |
| JURY_3 recall < CONTROL + 0.05 | Jury N=3 = drogi teatr. Pattern B tylko opt-in dla critical-only. |
| QWEN_SOLO recall < 0.30 (catastrophic miss) | Qwen NIE może być standalone reviewer. Tylko jako redundancy w hybrid/jury. |
| QWEN_SOLO recall > 0.60 | Qwen wystarczająco mocny żeby być solo critic w privacy mode (gdy Claude/Gemini niedostępne). |
| Wszystkie multi-arms ~ same recall jak CONTROL | Debate to drogi teatr na blast workload. Solo-LLM wygrywa, Fala 9 odpada. |

## Run

### Wymagane env vars

Claude backend — wybierz jeden:

```bash
# Opcja A: Claude Code CLI (subskrypcja, bez klucza API)
# Driver wykryje `claude` w PATH automatycznie. Działa z domyślną subskrypcją.
which claude   # zweryfikuj że CLI jest dostępne

# Opcja B: Anthropic API key (jeśli masz)
export ANTHROPIC_API_KEY=sk-ant-...

# Wymuszenie konkretnego backendu (default = "auto"):
export CLAUDE_BACKEND=cli   # albo "api" albo "auto"
```

Pozostałe:

```bash
export GEMINI_API_KEY=AI...                       # opcjonalnie — bez tego JURY_3 jest skipped
export BLAST_OLLAMA_UBUNTU=http://192.168.5.60:11434  # default OK
```

### Smoke test Claude Code CLI (przed pełnym driver runem)

```bash
# Czy CLI w ogóle działa?
claude -p "Reply with exactly one word: pong" --model claude-haiku-4-5-20251001

# Czy --output-format json zwraca strukturalny output?
claude -p "Say hi" --model claude-haiku-4-5-20251001 --output-format json
```

Jeśli któryś flag nie istnieje na Twojej wersji `claude`:
- `--model` nieobsługiwany → driver użyje default modelu (zwykle sonnet); zaktualizuj `ARM_REGISTRY` z konkretnymi nazwami które działają
- `--output-format json` nieobsługiwany → driver zrobi fallback do plain stdout (parser findings działa na surowym tekście)

### Komendy

```bash
cd r_and_d/research/spike-3

# Pełny run — 5 arms × 5 snippets = 25 calli, ~10-15 min, ~$3 budget
python3 driver.py

# Albo subset arm'ów (np. tylko hybrid vs sonnet)
python3 driver.py --arms SONNET_SOLO,HYBRID

# Albo subset snippets
python3 driver.py --snippets 01_cache.py,03_worker_pool.py

# Po runie — score
python3 score.py
# Wynik w report.md + na stdout
```

### Co produkuje

- `results.json` — raw findings z każdego (arm, snippet) calla, cost, latency, sub-call breakdown dla jury/hybrid
- `report.md` — tabela aggregate + per-snippet breakdown + missed bugs + unmatched findings per arm

## Założenia / limitations

- **Greedy keyword match** może być niedokładny: model który użył synonimu nieuwzględnionego w `ground_truth.keywords` nie dostanie credit. Mitygacja: keywords są dość obszerne (15-20 per bug). Po runie warto przeglądnąć `unmatched_findings` — jeśli widzimy real catches które nie zmatchowały, dorzucamy keywords i re-scorujemy.
- **N=1 per (arm, snippet)** — pojedynczy run, brak variance estimate. Akceptowalne dla spike (`temperature=0.2` redukuje variance), ale dla faktycznej Fali 9 release decyzji rozważyć N=3.
- **Snippets są syntetyczne** — bugi planted, nie z prod. Real-world bugs mogą mieć inną dystrybucję trudności. Spike #3 daje signal na *direction*, nie absolute numbers.
- **Cost numbers są estymowane** — ceny per Mtok mogą być nieaktualne; PRICING dict w `driver.py` do uaktualnienia.

## Po runie

1. Przegląd `report.md` — czy decision matrix daje czytelny verdict?
2. Update sekcji **Wyniki** w tym pliku (tu, na dole)
3. Update `../../decisions/2026-05-05-sdd-number-one-roadmap.md` — Fala 9 decisions według verdictu
4. Patch `.blast/steering/llm-routing.md` — zaktualizować default reviewer per faza zgodnie z verdict

---

## Wyniki

**Data runu**: 2026-05-06
**Total cost**: ~$3.20 (CONTROL $0.48 + SONNET_SOLO $0.30 + JURY_3 $0.91 + JURY_3_FLASH3 $0.87 + HYBRID $0.61 + QWEN_SOLO $0.00)
**Total runtime**: ~75 min (sequential, multiple iterations: pierwszy run, qwen-fix re-run, flash3 add)

### Aggregate scores (5 snippets × 18 planted bugs)

| Arm | Recall | Precision | F1 | Cost | Avg latency |
|---|---:|---:|---:|---:|---:|
| **JURY_3_FLASH3** (Opus ‖ qwen3.6 ‖ Gemini-3-Flash → Haiku agg) | **0.94** | **0.57** | **0.71** | $0.87 | 141s |
| **CONTROL** (solo Claude opus) | 0.89 | 0.57 | 0.70 | $0.48 | 45s |
| **SONNET_SOLO** (solo Claude sonnet) | 0.89 | 0.47 | 0.62 | $0.30 | 42s |
| **HYBRID** (Sonnet ‖ qwen3.6 → Haiku judge) | 0.94 | 0.45 | 0.61 | $0.61 | 130s |
| **QWEN_SOLO** (solo qwen3.6:latest local) | 0.72 | 0.50 | 0.59 | **$0.00** | 49s |
| **JURY_3** (Opus ‖ qwen3.6 ‖ Gemini-2.5-Pro → Haiku agg) | 0.94 | 0.41 | 0.58 | $0.91 | 156s |

### Decision matrix outcomes (vs pre-committed criteria)

| Criterion | Threshold | Actual | Result |
|---|---|---|---|
| HYBRID recall ≥ SONNET_SOLO + 0.10 @ cost ≤ 1.5× | +0.10 / 1.5× | +0.05 / 2.0× | ❌ NOT MET |
| JURY_3 recall ≥ CONTROL + 0.15 @ cost ≤ 2× | +0.15 / 2× | +0.05 / 1.9× | ❌ NOT MET |
| QWEN_SOLO recall < 0.30 (catastrophic) | <0.30 | 0.72 | ✅ Qwen viable |
| QWEN_SOLO recall > 0.60 (privacy mode capable) | >0.60 | 0.72 | ✅ |

### Key findings

1. **Multi-LLM debate gives marginal recall (+0.05, czyli 1 bug z 18), nie transformational**. Wszystkie multi-arms (HYBRID, JURY_3, JURY_3_FLASH3) złapały te same 17/18 bugów. Jeden bug (`wp-unbounded-queue`) przegapiły wszystkie arms.
2. **Gemini 3 Flash > Gemini 2.5 Pro** dla code review: precision 0.57 vs 0.41 przy tym samym recallu. Same cost. Drop 2.5-pro.
3. **HYBRID vs SONNET_SOLO**: recall +0.05, precision −0.02, F1 ~tied (0.61 vs 0.62). Qwen jako parallel critic dorzuca jeden bug ale i więcej noise. Wartościowe TYLKO gdy recall jest priorytetem nad precision.
4. **QWEN_SOLO blind spot**: catastrophic na `05_parser.py` (0/3 bugów). Przegapił `parser-broad-except`, `parser-silent-read-failure`, `parser-isdigit-negative` — wszystkie observability/silent-failure category. Inne snippety: comparable do Claude (3/3, 4/4, 3/4, 3/4).
5. **Solo Opus jest sweet spot dla większości faz** — F1 0.70, $0.48, 45s. Tylko 0.01 F1 punkt poniżej JURY_3_FLASH3 przy 1.8× tańszym i 3× szybszym.

### Verdict dla Fal 9-10

**Modified Fala 9 scope** (cuts vs original roadmap):

- ✅ **Asymmetric Pattern A (HYBRID-style)** — implement, opt-in dla `validate-impl --thorough`. ~2 wieczory roboty.
- ✅ **Pattern B jako JURY_3_FLASH3** — implement TYLKO dla high-stakes (`security`, `validate-design`). Drop Pattern B z 2.5-pro całkiem.
- ❌ **DROP**: pełna implementacja "4 protokołów debate" (Critique-Revise-Judge, Round-Robin, Devil's Advocate). Dane nie wspierają — recall gain za mały.
- ❌ **DROP**: `--debate` flag dla każdej fazy. Zostaje tylko `--thorough` (HYBRID) i implicit jury dla high-stakes.

**Saved**: ~2-3 wieczory implementacji vs original Fala 9 scope. Te wieczory → Fala 10 (multi-LLM bridge) i Fala 7 (delta specs).

### Recommended routing (do `.blast/steering/llm-routing.md`)

| Faza | Default | High-stakes / `--thorough` |
|---|---|---|
| `requirements`, `tasks`, `complete`, `deprecate`, `tiny` | Haiku | — |
| `research` | Sonnet | — |
| `design` | Opus | — |
| `impl` | qwen3-coder:30b (Author) | — |
| `validate-gap` | Haiku | — |
| `validate-design` | Sonnet | JURY_3_FLASH3 |
| `validate-impl` | Sonnet | HYBRID (Sonnet ‖ qwen3.6 → Haiku judge) |
| `security` | JURY_3_FLASH3 | — (already jury) |
| `review` | Sonnet | JURY_3_FLASH3 dla auth/payments/data-mutating |
| Privacy mode (any phase) | qwen3.6:latest local | — |

### Files updated post-spike

- `../spike-1/README.md` — Wyniki + Pattern A enabled
- `../../decisions/2026-05-05-sdd-number-one-roadmap.md` — Fala 9 modified scope appended
- `.blast/steering/llm-routing.md` — full routing table per phase
- `.blast/steering/cost-policy.md` — caps recalibrated

