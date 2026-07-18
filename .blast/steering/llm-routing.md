# LLM Routing Policy

Centralna konfiguracja: która faza używa którego modelu, gdzie debate jest enabled, które ścieżki muszą iść tylko do lokalnego LLM (privacy).

Plik czytany przez:
- Wszystkie blast agents przed wyborem modelu (override domyślnego frontmatter)
- `/blast:debate` przy doborze protokołu i jurorów
- `blast-llm-bridge` MCP przy routing'u i privacy enforcement
- `blast-privacy-gate.py` hook przed zewnętrznymi LLM calls

---

## Default routing per agent

Model aliases w frontmatterze (`haiku` / `sonnet` / `opus`) rozwiązują się do **aktualnej
generacji**: Opus 4.8 ($5/$25), Sonnet 5 (intro **$2/$10 do 2026-08-31**, potem $3/$15),
Haiku 4.5 ($1/$5). Trzymamy aliasy — same wskoczą na kolejną generację. `effort` (kolumna
niżej) to drugi wymiar: przy tym samym modelu steruje budżetem tokenów wyjściowych
(thinking+tekst). Domyślny effort silnika = `high`; obniżenie do `medium` na fazach
Sonnet to główna dźwignia kosztu tej fali (Sonnet 5 `medium` ≈ jakość Sonnet 4.6 `high`).

> ⚠ Po migracji na Sonnet 5 / Opus 4.7+ tokenizer emituje ~30% więcej tokenów za ten sam
> tekst — przelicz ceilingi w `cost-policy.md` na nowo (nie zmienia ceny za token, ale koszt
> requestu rośnie). Rekalibracja dopiero po zebraniu telemetrii kosztów (§3).

| Agent | Persona | Default model | Effort |
|---|---|---|---|
| spec-design-agent | Atlas | claude-opus | high |
| spec-tdd-impl-agent | Forge | claude-sonnet | medium |
| spec-tasks-agent | Loom | claude-haiku | — (haiku bez effort) |
| spec-requirements-agent | Scribe | claude-haiku | — |
| spec-tiny-agent | Sprint | claude-haiku | — |
| spec-research-agent | Oracle | claude-sonnet | medium |
| spec-complete-agent | Ledger | claude-haiku | — |
| spec-evolve-agent | Delta | claude-haiku | — |
| spec-deprecate-agent | Curator | claude-haiku | — |
| validate-gap-agent | Bridge | claude-sonnet | medium |
| validate-design-agent | Crucible | claude-sonnet | medium |
| validate-impl-agent | Auditor | claude-sonnet | medium |
| validate-tasks-agent | Pragmatist | claude-sonnet | medium |
| simplify-agent | Occam | claude-sonnet | medium |
| security-audit-agent | Sentinel | claude-sonnet † | high |
| code-review-agent | Compass | claude-sonnet | medium |
| spec-drift-agent | Tracker | claude-haiku | — |
| steering-agent | Cartographer | claude-sonnet | medium |
| steering-custom-agent | Specialist | claude-haiku | — |

† **Sentinel** orkiestruje: sam jest `sonnet` (dispatch/merge/dedup/kalibracja severity — `effort: high`,
bo to security), ale Phase 1A to deterministyczny skrypt `blast-secscan.py` (0 tokenów), a głęboka
semantyka zostaje w spawnowanym Sub-agencie B (`opus`). Demote opus→sonnet dotyczy orkiestratora, nie
deep-review. Jury (JURY_3_FLASH3) tylko przy `high_stakes` (patrz `debate_config.security`).

Zmiana defaults: edytuj frontmatter `model:` (i `effort:`) w `.claude/agents/blast/{agent}.md`. Ten plik jest **referencyjny**, nie autoritative dla single-agent path.

## Effort policy (budżet rozumowania per tier)

`effort ∈ {low, medium, high, xhigh, max}` — dostępny na Opus 4.5+/Sonnet 4.6+/Fable 5
(Haiku 4.5 go nie honoruje → agenci haiku nie mają tego pola). Ustawiany w frontmatterze
subagenta (Claude Code czyta `effort:` per subagent). Zasada:

- **Mechaniczne fazy (haiku)** — bez effort; model już jest najtańszy.
- **Walidacja / transformacja / orkiestracja (sonnet)** → `medium`. Down z domyślnego `high`;
  Sonnet 5 `medium` ≈ Sonnet 4.6 `high`. Główna oszczędność bez utraty jakości.
- **Design / security (opus)** → `high` (default). Fazy jakościowo krytyczne — nie schodzimy.
- **Eskalacja architektoniczna w impl** → podnieś ad hoc do `xhigh` na konkretne wywołanie,
  nie na stałe we frontmatterze.

Chcesz konkretnego agenta ostrzej (np. `spec-research-agent` na `high`) — zmień jego
`effort:` we frontmatterze; ten plik jest opisem polityki, nie egzekwuje jej.

## Steering digest (§5 — czytaj skrót, nie cały katalog)

`.blast/steering/steering-digest.md` to **generowany** skrót całego `.blast/steering/`
(sekcje + verbatim gotchas/invariants/canonical-commands/component-registry + pointery
do pełnych plików). Generator: `python3 .claude/scripts/blast-steering-digest.py`
(Cartographer odpala go na sync; `--check` wykrywa staleness do CI). Cel: fazy, które dziś
czytają „**entire** `.blast/steering/`", mogą czytać **najpierw digest** i sięgać po pełny
plik tylko przy drill-downie — steering przestaje być re-tokenizowany 7–8× na pipeline.
Opt-in: przełączanie konkretnych agentów na digest-first to zmiana behawioralna — rób ją
świadomie, agent po agencie (design może dalej czytać całość). Digest jest generowany —
nigdy nie edytuj go ręcznie.

---


## Tiered impl routing (local-first)

`spec-tdd-impl-agent` (Forge) generates code **locally by default**. The code primary is
`qwen3-coder` (17.3G, ~160 tok/s on the 5090). Rationale vs `qwen3.6` (243 tok/s raw): the
coder profile produces almost no thinking chain, so its EFFECTIVE code throughput is higher —
thinking tokens are pure waste in a TDD loop. Cloud escalation is the exception, not a
keyword reflex.

**VRAM residency (RTX 5090, 32G)**: `qwen3-coder` (17.3G) + `lfm2.5` (4.8G) = 22.1G — both
pinned resident (`keep_alive=-1` in the bridge) with headroom for KV cache. `qwen3.6` (22.3G)
does NOT co-fit with a second model; it stays a debate juror, never the impl primary. Never
load a third local model mid-impl — it evicts the resident pair and costs a reload per call.

```yaml
spec-tdd-impl-agent:
  default_model: qwen3-coder          # via mcp__blast-llm-bridge__ask_ubuntu_qwen3_coder
  draft_model: lfm2.5                 # via mcp__blast-llm-bridge__ask_ubuntu_lfm25 (draft-then-verify, never final code)
  escalate_local: qwen3-coder-next    # tier 2 — via ask_ubuntu_qwen3_coder_next ($0, slow, deliberate swap)
  escalate_to: claude-sonnet-5        # tier 3 — cloud, last resort (effort: medium; xhigh only on architectural)
  escalation_triggers:                # ONLY these — async/complexity keywords removed
    - spec_json:
        security_critical: true       # correctness non-negotiable → straight to tier 3 (Sonnet)
    - spec_json:
        complexity_hint: "high"       # AND task has subtle correctness (state cycles, txns, consistency)
    - local_failed_this_task: true    # red tests on this task → next tier up (coder-next first, then Sonnet)
    - task_domain: ["parser", "observability"]   # Spike-3 empirical blind spot — see below
```

> **Qwen blind spot (Spike-3, empirical)**: Qwen critics/coders consistently miss issues in
> **parser code** and **observability/instrumentation code**. Tasks touching grammars,
> tokenizers, AST/lexers, log/metric/trace instrumentation → escalate straight to Sonnet
> (tier 3), skipping the local ladder. This is an evidence-based exception consistent with
> the no-keyword-reflex policy — the evidence already exists, no fresh spike needed.

**Three-tier ladder** (non-security tasks):
```
qwen3-coder (160 tok/s, resident, default)
  → 2 failed attempts (red tests) → qwen3-coder-next (50 tok/s, $0, CPU offload — deliberate swap)
    → still red / architectural issue → claude-sonnet (cloud, ~$0.04/task)
```
Rationale: coder-next catches a chunk of tasks that previously went straight to cloud.
The swap costs a model reload (resident pair evicted) — batch tier-2 escalations at the
END of a wave when possible, never interleave. Target from telemetry: cloud escalation
rate <10% (was <20% with the two-tier ladder).

### lfm2.5 — mechanical lane (580 tok/s)

`lfm2.5` is a weaker model: **never final code**. Route to it (via `ask_ubuntu_lfm25`):
- draft-then-verify scaffolding: test boilerplate, fixtures, dataclasses, signatures from
  design.md — qwen3-coder verifies/corrects the draft (verification is faster than generation)
- verdict-envelope parsing, debate scratchpad digests, stalemate-similarity checks
- telemetry summaries for `/blast:learn`, commit-message drafts
- judge + aggregator in privacy mode (`local-only`), where Haiku is blocked

> ⚠ Spike-4 (2026-05-07) baselines are STALE — they measured the OLD `qwen3-coder:30b`, whose
> async weakness (composite 2.6/5) drove the now-removed `async`/`asyncio` escalation triggers.
> The dense `qwen3.6:27b` is a different model; it handles ordinary async fine. Do not re-add
> keyword triggers without a fresh Spike-4 on the current model.

Cost trade-off per impl phase:
- Default (local qwen3-coder): $0, fully on-GPU, no async carve-out needed
- Escalated (sonnet): ~$0.04 per task — reserved for security-critical / demonstrated failure only

Re-validate the new baseline via `/blast:learn --routing` once a few specs have shipped on it.
Target: local→Sonnet escalation < ~20% on non-security specs.

## Privacy patterns

Format: `glob_pattern llm=<policy>`

Domyślne (apply do every project):

```
.env* llm=local-only
*.pem llm=local-only
*.key llm=local-only
secrets/** llm=local-only
config/production.yml llm=local-only
*.proprietary llm=local-only
**/credentials.json llm=local-only
**/private/** llm=local-only
```

Per-project additions:

```
# (twoje patterns tutaj — np. compliance-flagged code)
src/billing/legal/** llm=local-only
docs/customer-pii/** llm=local-only
```

Polityki:
- `local-only` — file content nie może iść do żadnego cloud LLM (Anthropic, OpenAI, OpenRouter). Tylko Ollama (lokalny cluster).
- `cloud-ok` — domyślnie, brak ograniczeń
- (przyszłe: `redact-only` — automatyczne maskowanie PII przed cloud send)

Privacy hook (`blast-privacy-gate.py`) skanuje paths przed call'ami `ask_anthropic_*` / `ask_openrouter_*` i blokuje gdy match.

---

## debate_config — declarative composition for `/blast:debate`

Read by `validate-{impl,design}-agent`, `security-audit-agent`, `code-review-agent` via Debate Mode hook. Used by `/blast:debate` for juror selection.

### Trigger semantics

**Debate is OPT-IN, not default.** Rationale: blast's own spike-3 verdict found multi-LLM debate
buys only ~+5% recall vs solo Opus — not worth ~130–141s + cost on every validation pass. Solo
(Sonnet/Opus per Model routing) is the default; the user opts INTO debate with `--debate`, or it
fires automatically only where cross-model diversity genuinely matters (security).

| Trigger | Fires when |
|---|---|
| `always` | every invocation of that phase (debate non-negotiable — currently no phase uses it; security moved to `high_stakes`) |
| `debate_flag` | ONLY when the user passes `--debate` (default OFF — solo composition otherwise) |
| `high_stakes` | `risk_level: high` OR `security_critical: true` OR PR touches sensitive paths (always debate, no opt-out) |

Per-spec override: `spec.json.debate.{phase}` wins.

### Compositions

Each juror entry has TWO parts: logical model name (for documentation) and the
**actual invocation** (subagent name OR MCP tool name) that `debate.md` Protocol B
must call. If `mcp_tool` is missing or its API key is unset, the juror falls back
to the named subagent (which runs as Sonnet by default unless its own frontmatter
overrides `model:`).

```yaml
HYBRID:
  protocol: B   # parallel jury, N=2 — single message, parallel tool calls
  jurors:
    - name: claude-sonnet-5
      subagent: debate-critic           # spawned via Task tool (real Sonnet, effort per frontmatter)
    - name: qwen3.6:latest
      mcp_tool: ask_ubuntu_qwen36       # real local Ollama via blast-llm-bridge
  aggregator:
    name: claude-haiku-4-5-20251001
    subagent: debate-aggregator          # spawned via Task tool (uses haiku model)

HYBRID_LOCAL:                            # dual-GPU local jury — privacy mode / $0 validation
  protocol: B   # parallel jury, N=2 — single message, parallel tool calls
  jurors:
    - name: qwen3.6 @ 5090
      mcp_tool: ask_ubuntu_qwen36       # Ubuntu/5090
    - name: qwen3-coder @ 4090
      mcp_tool: ask_win11_qwen3_coder   # Win11/4090 — runs in PARALLEL with the 5090 juror
  aggregator:
    name: lfm2.5
    mcp_tool: ask_ubuntu_lfm25          # mechanical tally, 580 tok/s

JURY_3_FLASH3:
  protocol: B   # parallel jury, N=3 — single message, parallel tool calls
  jurors:
    - name: claude-opus-4-8
      subagent: debate-critic-opus      # spawned via Task tool (model: opus in frontmatter)
    - name: qwen3.6:latest
      mcp_tool: ask_ubuntu_qwen36       # real local Ollama via blast-llm-bridge
    - name: gemini-3-flash-preview
      mcp_tool: ask_gemini_3_flash_preview   # real Gemini API via blast-llm-bridge
                                              # requires GEMINI_API_KEY in .env or os.environ
                                              # if missing → juror skipped, jury degrades to N=2
  aggregator:
    name: claude-haiku-4-5-20251001
    subagent: debate-aggregator          # spawned via Task tool (uses haiku model)
```

**Truth-in-advertising note**: prior runs of `/blast:debate` with JURY_3_FLASH3
produced "stand-in" jurors (Sonnet pretending to be Opus / Gemini) when the
underlying subagents/MCP tools weren't wired. The schema above makes the wiring
explicit so debate.md MUST call the named subagent or MCP tool — not roleplay it
in its own context. If a tool is unavailable, the debate output must say so.

### Per-phase config

Validate-{impl,design}-agent's Debate Mode hook reads these YAML blocks. The hook
spawns the debate flow only when `enabled: true` AND the trigger condition is met.

```yaml
debate_config:
  validate-impl:
    enabled: true
    trigger: debate_flag          # opt-in: solo Sonnet unless user passes --debate
    composition: HYBRID
    cost_ceiling_usd: 0.50

  validate-tasks:
    enabled: true
    trigger: debate_flag          # opt-in: solo Sonnet unless user passes --debate
    composition: HYBRID
    cost_ceiling_usd: 0.40

  validate-design:
    enabled: true
    trigger: debate_flag          # opt-in: solo Opus unless user passes --debate
    composition: JURY_3_FLASH3
    cost_ceiling_usd: 1.00

  security:
    enabled: true
    trigger: high_stakes          # jury (cross-corpus diversity) only where it pays: security_critical
                                  # / risk_level=high / sensitive paths. Normal specs run SOLO Sentinel
                                  # (sonnet orchestrator + deterministic Phase-1A scan + opus deep-review
                                  # Sub-agent B + threat-model Sub-agent C) — still thorough, no jury tax.
                                  # Spike-3: jury buys only +0.05 recall for +$0.57 and +96s vs solo.
    composition: JURY_3_FLASH3    # used ONLY when high_stakes fires
    cost_ceiling_usd: 1.50

  review:
    enabled: true
    trigger: debate_flag          # opt-in: solo Sonnet unless user passes --debate
    composition: JURY_3_FLASH3
    cost_ceiling_usd: 1.00

  simplify:
    enabled: true
    trigger: high_stakes          # solo Sonnet by default; debate only on auth/payments/schema or explicit --debate
    composition: HYBRID
    cost_ceiling_usd: 0.40
```

Compositions (HYBRID, HYBRID_LOCAL, JURY_3_FLASH3) defined above. **Trigger semantics**:
- `debate_flag` — opt-in: fire debate ONLY when the calling slash command injected `Debate: true` into the agent prompt (user passed `--debate`). Otherwise run the solo composition from Model routing.
- `always` — fire debate unconditionally (no phase uses it today; security is `high_stakes`).
- `high_stakes` — fire only when risk_level=high or security_critical=true.

To **disable** debate for a phase without removing config: set `enabled: false`. To **force always-on**: set `trigger: always`.

### Privacy mode override (`spec.json.privacy: local-only`)

All compositions fall back to local-only via `blast-privacy-gate.py` → composition `HYBRID_LOCAL`:
- jurors → `[qwen3.6 @5090 (ask_ubuntu_qwen36), qwen3-coder @4090 (ask_win11_qwen3_coder)]`
  — **dual-GPU parallel jury**: both jurors run simultaneously, no model swap. If the
  Win11 host is offline, fall back to `ask_ubuntu_qwen3_coder` (serialized on the 5090).
  Security adds `gemma4` @5090 as third juror — different corpus for diversity; 16 tok/s
  is slow but acceptable for a security audit, and ONLY there.
- aggregator → `lfm2.5` via `ask_ubuntu_lfm25` (Haiku blocked; tallying votes is mechanical)
- cost_ceiling_usd → 0.00
