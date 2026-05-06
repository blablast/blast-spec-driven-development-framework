# blast INVENTORY — what's actually delivered

**Aktualizowane**: 2026-05-06 (audit po Spike-3)
**Źródło prawdy**: ten plik vs roadmap (`r_and_d/decisions/2026-05-05-sdd-number-one-roadmap.md`). Roadmap = plan. INVENTORY = stan rzeczywisty.

---

## Falsa 1-6 (już shipped — fundamentals)

Bez audytu — założone że shipped wcześniej. Smart routing, hard approval gate, verdict envelope, basic agents, settings.json hooks dla approval-gate. Status `shipped`.

---

## Fala 7 — Domknięcie SOTA luk

### ✅ Delivered (files exist, structurally complete)

| Komponent | Pliki | Lines | Smoke tested? |
|---|---|---:|---|
| `/blast:evolve` | `commands/blast/evolve.md` + `agents/blast/evolve.md` + `templates/specs/evolution.md` | 146+197+template | ❌ NIE |
| `/blast:graph` | `commands/blast/graph.md` (pure-bash, no agent) | 252 | ❌ NIE |
| `/blast:drift` | `commands/blast/drift.md` + `agents/blast/drift.md` (Step 4 z Qwen MCP delegation, 2026-05-06) | 140+250 | ❌ NIE |
| spec.json schema z `provides`/`dependencies`/`evolutions`/`completed_at` | `templates/specs/init.json` | — | partially (init używa) |
| `/blast:approve {f}-evo-{N} evolution` flow | `commands/blast/approve.md` | — | ❌ NIE |
| Smart routing dla `phase: evolution-generated` | `CLAUDE.md` decision matrix | — | ❌ NIE |

### ⚠️ Gaps

- **Zero end-to-end smoke tests** na realnym specu. Trzy ficzery (`graph`, `evolve`, `drift`) nigdy nie odpalone na żywo.
- `/blast:graph` nie ma osobnego agenta — pure bash. Można dorzucić Qwen synthesis (similar do `/blast:status` Project Pulse) jako enhancement, nie blocker.
- 25+ untracked plików nie zcommitowanych — git history not reflecting Fala 7.

### Status: **STRUCTURALLY DONE, FUNCTIONALLY UNTESTED**

---

## Fala 8 — Differentiation

### ✅ Delivered

| Komponent | Pliki | Lines | Status |
|---|---|---:|---|
| `/blast:lint` (deterministic linter) | `commands/blast/lint.md` + `scripts/blast-lint.py` | — | ✅ pure-Python, sub-second, działa |
| `/blast:telemetry` (raport z logów) | `commands/blast/telemetry.md` + `scripts/blast-telemetry.py` + `hooks/blast-telemetry.py` | — | ✅ structurally; ⚠️ hook registered ale `agent-runs.jsonl` ma 0 linii |
| Persona naming (Atlas, Forge, Tracker, Crucible, etc.) | `agents/blast/{*}.md` | — | partially — niektóre agenty mają explicit `## You are <Persona>`, niektóre nie (e.g. design.md, impl.md, security.md, validate-design.md) |
| `cost-policy.md` skeleton | `.blast/steering/cost-policy.md` | 80+ | ✅ z Spike-3 recalibration na p75/p95 |

### ⚠️ Gaps

- **Telemetry NIGDY nie zalogowała żadnego runu** — `agent-runs.jsonl` size=0 mimo że hook jest registered w `settings.json`. Możliwe powody: (a) żaden Agent/Task call nie odpalił się w trackowanych sesjach, (b) hook fails silently. **Diagnostyka needed**: odpal `python3 .claude/hooks/blast-telemetry.py < /dev/null` ręcznie żeby sprawdzić czy nie crash'uje.
- Persona naming inconsistent — co najmniej design/impl/security/validate-design nie mają explicit Persona linii. Drift, complete, evolve, deprecate, tasks, requirements, tiny — większość ma. Cosmetic gap.
- `/blast:lint --semantic` (Qwen-powered) — deferred, optional.

### Status: **FULLY DELIVERED** (telemetry working, personas complete — both confirmed 2026-05-06)

---

## Fala 9 — Agent Debate Framework

### Original scope (z roadmapa, pre-Spike-3): 4 protokoły debate, scratchpad, termination criteria, integracja z validate-design/validate-impl/security

### ✅ Delivered

| Komponent | Pliki | Lines | Status |
|---|---|---:|---|
| `/blast:debate` slash command | `commands/blast/debate.md` | — | ✅ czyta `debate_config:` z llm-routing.md (verified 2026-05-06) |
| 4 debate agenty | `agents/blast/debate/{aggregator,author,critic,judge}.md` | — | ✅ files present |
| Scratchpad template | `templates/debates/scratchpad.md` | — | ✅ |
| `debate_config:` per-faza w `llm-routing.md` | `.blast/steering/llm-routing.md` | 14.6 KB | ✅ added 2026-05-06 z empirical baselines |
| Debate Mode hook w `validate-impl-agent` | `agents/blast/validate-impl.md` | — | ✅ czyta config, spawnuje `/blast:debate` |

### Spike-3 verdict applied (modified scope)

- ✅ **Pattern A asymmetric** (HYBRID — Sonnet ‖ qwen3.6 → Haiku judge) configured w `validate-impl --thorough`
- ✅ **Pattern B (JURY_3_FLASH3)** configured dla `security` (always) + `validate-design` (high-stakes/--thorough) + `review` (high-stakes)
- ❌ **DROPPED**: pełna implementacja Round-Robin (Protokół C) jako default. Files są (`/blast:debate` supports protocol C), ale nie używamy tego flow w żadnym agencie.
- ❌ **DROPPED**: `--debate` universal flag dla każdej fazy. Zostało tylko `--thorough` na validate-impl.

### ⚠️ Gaps

- `/blast:debate` Pattern A/B/C/D — **nigdy nie odpalone end-to-end**. Tylko spike-3 driver odpalał Pattern B logic ad-hoc.
- Agent `validate-design-agent` Debate Mode hook — nie zweryfikowane czy faktycznie czyta nową `debate_config.validate-design`. Probably tak (same wzorzec jak validate-impl), ale untestowane.
- `security-audit-agent` Debate Mode hook — jw.

### Status: **DELIVERED PER MODIFIED SCOPE, UNTESTED END-TO-END**

---

## Fala 10 — Multi-LLM via MCP

### ✅ Delivered

| Komponent | Pliki | Status |
|---|---|---|
| `blast-llm-bridge.py` MCP server | `.claude/mcp/blast-llm-bridge.py` | ✅ spike-2 MVP grade — 4 hardcoded model tools (qwen3.6, qwen3-coder, qwen3:32b win11, deepseek-r1 win11) |
| MCP registered | `.mcp.json` | ✅ |
| `/blast:ping-llm` smoke test | `commands/blast/ping-llm.md` | ✅ |
| `blast-privacy-gate.py` hook | `.claude/hooks/blast-privacy-gate.py` | ⚠️ exists, ale **NIE registered w settings.json** — tylko approval-gate i telemetry zarejestrowane |
| `llm-routing.md` declarative routing | `.blast/steering/llm-routing.md` | ✅ pełna tabela per-faza + debate_config + privacy overrides + empirical baselines (14.6 KB) |
| `multi-llm-setup.md` instrukcje | `.blast/knowledge/references/multi-llm-setup.md` | ⚠️ ma `OLLAMA_KEEP_ALIVE=24h` recommendation — **to jest błędne** (powodowało VRAM hog z qwen3-coder-next w spike-3 debugging). Powinno być default 5min lub explicit 30m dla bench/spike. |

### ⚠️ Gaps

- **Privacy gate NIE active** — hook present ale settings.json nie ma matcher'a. Privacy mode overrides w `llm-routing.md` są dziś tylko deklaratywne, nie egzekwowane. **Quick fix**: dorzucić matcher w `settings.json::hooks.PreToolUse`.
- Bridge zostaje **spike MVP**: 4 hardcoded model wrappers, sync inference, no retry/backoff, no rate limiting, no dynamic registry. Production grade = osobna inwestycja (~2 wieczory).
- Bridge **nie obsługuje** Anthropic API direct (tylko Claude Code CLI subprocess), Gemini API (tylko bezpośrednio z driver.py), DeepSeek API. To są intencjonalne — Anthropic via Claude Code, others via direct API w driverach. Ale w `llm-routing.md` mamy `backend: gemini_api` — wymaga osobnego dispatchera lub agenta SDK calls.
- Bridge wrappuje `win11` endpointy (qwen3:32b, deepseek-r1:32b) ale **win11 4090 jest broken dla 32B** (CPU offload, 5 tok/s — confirmed w spike-3). Bridge powinien mieć health check przed call albo deprecation note.
- `OLLAMA_KEEP_ALIVE=24h` w setup docs — **bug w dokumentacji** (powodowało VRAM hog) — fix wymagany.

### Status: **SPIKE-MVP GRADE z safety patches** (privacy-gate registered, win11 wrappers disabled with deprecation message). NIE production-ready (still no retry/backoff/rate limiting/dynamic registry). Fala 10 v2 = osobna inwestycja.

---

## Cross-cutting infrastructure

### ✅ Delivered

- Hard approval gate via PreToolUse hook (`blast-approval-gate.py`) — registered, działa
- Telemetry hook (PostToolUse) — registered, **but log empty**
- Settings.json bash allowlist — comprehensive
- `.gitignore` — clean
- `.mcp.json` — bridge registered
- 22 modified + ~25 untracked files **na main branchu, niezcommitowane**

### Memory / steering

- `MEMORY.md` index z 5 wpisami (user role, commit style, hardware, spike-3 verdict, project overview)
- `cost-policy.md` z post-Spike-3 calibration
- `llm-routing.md` 14.6 KB pełna prawda
- INVENTORY.md (this file) — created 2026-05-06

---

## Quick fixes — RESOLVED 2026-05-06

1. ✅ **Privacy-gate hook registered** w `settings.json` (matcher `Read|Glob|Grep|Agent|Task|mcp__.*`). Privacy mode teraz faktycznie egzekwowany.
2. ✅ **`OLLAMA_KEEP_ALIVE` corrected** w `multi-llm-setup.md`: 24h → 5m default + comment o per-call override dla bench/spike.
3. ✅ **Telemetry hook diagnosed** — code OK, log pusty był bo brak qualifying Task calls w trackowanych sesjach. Manual smoke test napisał wpis. Hook works.
4. ✅ **Persona naming** — wszystkie 4 brakujące agenty miały już `## You are <Persona>` (Atlas, Forge, Sentinel, Crucible). Mój wcześniejszy grep miał zły regex. Persona suite kompletny: Atlas, Forge, Loom, Scribe, Sprint, Oracle, Ledger, Delta, Curator, Bridge, Crucible, Auditor, Tracker, Steward, Sentinel.
5. ✅ **Bridge win11 health check** — dodany `disabled_reason` field w `CONFIG["models"]`. `ask_win11_qwen3_32b` i `ask_win11_deepseek_r1` teraz return helpful deprecation message zamiast próbować call. Re-enable instructions w komunikacie. List_tools advertise [DISABLED] prefix w description.

## Co NIE zostało zrobione (świadome scope cuts post Spike-3)

- ❌ Pattern C (Round-Robin Debate z scratchpad iteration) jako default w validate-design — drop
- ❌ Pattern D (Devil's Advocate jako separate protocol) — drop
- ❌ `--debate` universal flag — drop, zostaje tylko `--thorough`
- ❌ Spike #3 alternatywne arms (np. JURY_5 z 5 jurorami, Pattern A z 3 critics) — nie testowane, drop
- ❌ Production-grade bridge (retry, backoff, rate limit, dynamic registry) — Fala 10 v2, future
- ❌ Anthropic dispatcher w bridge — intencjonalnie via Claude Code CLI
- ❌ Gemini/DeepSeek API w bridge — intencjonalnie direct API w driverach (jeśli kiedyś chcemy unified, dorzucamy)

---

## Następna inwestycja (post-audit)

Sugerowana kolejność:

1. **Quick fixes** (~10 min total): privacy-gate registration + multi-llm-setup keep_alive correction + telemetry diagnoza
2. **Smoke test Fala 7** (~1 wieczór): odpal `/blast:graph`, `/blast:evolve`, `/blast:drift` na realnym specu, naprawić bugi
3. **Logical commits paczki** (~1 wieczór): porozdzielić 47 pending plików na 5-6 commitów per fala
4. **Smoke test Fala 9 modified scope** (~half wieczoru): odpal `/blast:validate-impl --thorough` na shipped specu, sprawdź HYBRID
5. **Fala 10 v2 production bridge** (2-3 wieczory): retry, backoff, dispatcher dla wszystkich providerów, rate limit
