# blast → SDD #1: Strategiczny plan implementacji

**Źródło**: własne notatki + research SOTA SDD frameworków (Spec Kit, Kiro, BMAD, OpenSpec, Tessl, Intent, Agent OS) + dyskusja Błażej x Claude 2026-05-05
**Data**: 2026-05-05 (v2 — z finalnymi decyzjami)
**Tagi**: roadmap, agent-debate, mcp, multi-llm, sdd, architektura, fala-7, fala-8, fala-9, fala-10, spike

---

## 0. TL;DR

blast po Falach 1–6 jest **już silniejszy mechanicznie** niż większość SOTA (hard hook gates, verdict envelope, test relevance audit, model routing, verification strategy enforcement). Ten plan domyka pozostałe luki funkcjonalne i dodaje dwie unikatowe strategiczne osie: **debata agentów** (multi-perspective enforcement jakości) i **multi-LLM via MCP** (wybór modelu per faza, w tym lokalne LLM dla privacy/cost).

**Strategia wdrożenia**: 3 spike'i (~2.5 wieczoru) → pełna implementacja Fal 7-10 (~10-13 wieczorów). Spike'i weryfikują kluczowe assumptions zanim zacznie się główna inwestycja kodu.

**Hardware base**: lokalna klastra 2 maszyn (Ubuntu+RTX 5090 i Win 11+RTX 4090, 10 Gbps LAN, NAS QNAP), Pattern Z (Pinned + Failover). 4 modele live: Qwen3.6-35B-A3B, Qwen3-Coder-30B, DeepSeek V4 Flash, Qwen3-32B-Instruct.

**Hybrid LLM**: Anthropic direct (Claude Code native) + OpenRouter dla cloud (jeden klucz, ~100 modeli) + lokalne Ollama. Privacy mode → tylko local. Cost transparency → tokens primary, $ secondary.

Cel: po wdrożeniu Fali 7–10 blast będzie obiektywnie najmocniejszym frameworkiem SDD na rynku w wymiarze egzekutywności i jakości. Osobno wymaga inwestycji w dystrybucję (Fala 11) jeśli celujemy w popularność.

---

## 1. Cel — co to znaczy "SDD #1"

Dwa osobne wymiary:

**Jakościowy #1** (wykonalne w 4 falach):
- Najmocniejsza egzekucja jakości w market (hard gates, verdict, debate, drift detection)
- Pełna parytet z liderami w obszarach gdzie obecnie tracimy (delta specs, cross-spec graph, living spec)
- Unikatowe ficzery których nikt jeszcze nie ma (debate framework, multi-LLM via MCP, spec linter)

**Popularnościowy #1** (osobny lift):
- Publiczny GitHub repo z dobrym README
- npm/pip installable
- Documentation site
- Video walkthrough
- Społeczność (Discord/blog/Twitter)
- To głównie marketing, nie technologia. Pomijam w tym dokumencie.

**Definition of Done dla Jakościowego #1**:

| Wymiar | Aktualnie blast | Po planu | Lider obecnie |
|---|---|---|---|
| Approval enforcement | ✓ unikatowy (markdown + hook) | ✓ utrzymany | blast |
| Verdict envelope | ✓ unikatowy | ✓ rozszerzony o debate | blast |
| Test relevance | ✓ unikatowy | ✓ utrzymany | blast |
| Model routing | ✓ częściowy | ✓ pełny + multi-LLM via MCP | blast (po MCP) |
| Verification strategy | ✓ unikatowy | ✓ utrzymany | blast |
| Delta specs | ✗ | ✓ (Fala 7) | OpenSpec |
| Drift detection | ✗ | ✓ (Fala 7) | Intent |
| Cross-spec graph | ✗ | ✓ (Fala 7) | OpenSpec, Kiro |
| Spec linter | ✗ | ✓ (Fala 8) | nikt — UNIKAT po Fali 8 |
| Agent debate | ✗ | ✓ (Fala 9) | BMAD ma częściowy (Party Mode) — blast będzie miał głębszy |
| Multi-LLM (incl. lokalne) | ✗ | ✓ (Fala 10) | nikt — UNIKAT po Fali 10 |
| Telemetry | ✗ | ✓ (Fala 8) | Intent, Tessl |

---

## 2. Filary planu — 4 fale + Phase 0 spike

**Phase 0 — Spike validation** (~2.5 wieczoru, BEFORE pełna implementacja)
- Spike #1: Local cluster validation (Ollama + LAN + jakość Qwen vs Claude)
- Spike #2: Bridge MVP (~100 linii Pythona, weryfikuje czy MCP w Claude Code działa jak myślimy)
- Spike #3: Manual debate simulation (czy multi-model debate daje lepsze wyniki niż solo)

**Fala 7 — Domknięcie luk SOTA** (pragmatyczny catch-up)
- Delta specs (`/blast:evolve`)
- Cross-spec dependency graph (`/blast:graph`)
- Drift detection (`/blast:drift`)

**Fala 8 — Differentiation** (unikalne ficzery których nikt nie ma)
- Spec linter (`/blast:lint`)
- Telemetry dashboard (`/blast:telemetry`)
- Persona naming (cosmetic but UX-positive)
- Cost-policy.md skeleton (hard limits aktywne post-baseline)

**Fala 9 — Agent Debate Framework** (główny diferencjator)
- 4 protokoły debate (Critique-Revise-Judge, Multi-jury vote, Round-robin, Devil's Advocate)
- Shared scratchpad convention
- Round 5 Synthesis & Addenda Loop (handling stalemates)
- Termination criteria + cost ceilings
- Integracja w `validate-design`, `validate-impl`, `security`, opcjonalnie `design`

**Fala 10 — Multi-LLM via MCP** (drugi główny diferencjator)
- MCP server `blast-llm-bridge` wrappujący OpenRouter + Ollama (Anthropic direct, NIE przez bridge)
- Konwencja tool naming (`ask_<provider>_<model>`)
- Per-phase config w `llm-routing.md`
- Lokalne LLM dla privacy-sensitive code (Pattern Z na 2 maszynach)

Fale 9 i 10 są **wzajemnie wzmacniające się**. Debate między modelami z różnych providerów (Claude vs Qwen vs DeepSeek) to znacznie silniejszy adversarial check niż debate między haiku i opus (które dzielą training distribution).

---

## 3. Deep dive — Agent Debate Framework (Fala 9)

### 3.1 Dlaczego debate ma znaczenie

Pojedynczy agent ma blind spots. Te blind spots są **systematyczne**, nie losowe:

- haiku trochę za bardzo upraszcza
- sonnet bywa zachowawczy
- opus czasem over-engineeruje
- każdy provider ma własny corpus → własne biases

Multi-agent debate nie eliminuje błędów, ale **eksponuje je przez konflikt**. Gdy dwa agenci się zgadzają, sygnał jest mocniejszy. Gdy się nie zgadzają — to dokładnie ta klasa błędów które solo-agent przepuści cicho.

Społeczność SDD już to dostrzega:
- BMAD ma "Party Mode" (adversarial review jest jednym z najmocniej chwalonych ficzerów BMADa)
- Anthropic Constitutional AI ma self-critique loop
- Multi-agent benchmarks (AutoGen, CrewAI) konsekwentnie pokazują że debate > solo dla jakości decyzji

### 3.2 Cztery protokoły debate

#### Protokół A: Critique-Revise-Judge (3 agenty, 3 role)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Author     │ ──→ │   Critic     │ ──→ │    Judge     │
│ (proposes)   │     │ (challenges) │     │ (verdict)    │
└──────────────┘     └──────────────┘     └──────────────┘
```

Jeden round, trzy różne modele/role. Author proponuje, Critic atakuje, Judge wydaje verdict envelope.

**Use case**: lekka debate dla decyzji o średnim ryzyku. Default dla `validate-design`.

#### Protokół B: Multi-Jury Vote (N agentów, jedna rola)

```
   Question
       │
       ├──→ Juror_1 (Sonnet)    → vote: PASS
       ├──→ Juror_2 (Opus)      → vote: WARN
       ├──→ Juror_3 (GPT-5)     → vote: PASS  (via MCP)
       ├──→ Juror_4 (Llama-3.3) → vote: PASS  (via MCP, local)
       │
       ▼
   Aggregator (Haiku)
   ─→ majority: PASS, dissent: 1 WARN noted
```

Każdy juror niezależnie. Aggregator zlicza głosy + konsoliduje uzasadnienia. Statystyczna pewność rośnie z N.

**Use case**: high-stakes decisions. Default dla `security` (jury z 3-4 modeli — różne providery wyłapią różne CVE patterns).

**Cost awareness**: N pełnych przebiegów. Cap na N=3 default, override do N=5 dla critical phases.

#### Protokół C: Round-Robin Debate (2 agenty, N rund)

Sekwencyjna wymiana, agenci widzą historię.

```
Round 1: Advocate proposes → Critic responds
Round 2: Advocate revises → Critic re-evaluates
Round 3: Advocate finalizes → Critic judges
...
Termination: agreement | max rounds | escalation to user
```

Shared scratchpad: `.blast/specs/{f}/debates/{topic}.md` — każdy agent appenduje swój wpis.

**Termination criteria**:
- **Agreement** — Critic ostatnia wpisuje `## I CONCEDE` lub `## VERDICT: PASS`
- **Max rounds** — domyślnie 4 (8 wpisów). Po max rounds → **Round 5 Synthesis & Addenda Loop** (patrz F4 w sekcji 10)
- **No movement** — ostatnie 2 wpisy obu agentów są semantycznie identyczne (haiku similarity check)
- **Cost ceiling** — przekroczony budżet tokenów (np. 50k łącznie)
- **Explicit escalation** — agent wpisuje `## ESCALATE: human input needed`

**Use case**: design decisions where there's no obviously right answer. Optional dla `validate-design --debate`. Heaviest protocol; explicit-opt-in.

#### Protokół D: Devil's Advocate (1 + 1, asymetryczna)

```
┌────────────────┐     ┌────────────────┐
│   Author       │     │  Devil's Adv.  │
│  (full freedom)│ ←── │  (only attacks)│
└────────────────┘     └────────────────┘
                       Hard rule: NEVER agree
                       Always find weakness
```

Asymetria: Author pisze normalnie, Devil ma w prompcie systemową zasadę "twoja jedyna funkcja to znajdować słabości — nie wolno ci się zgodzić, znajdź minimum 3 problemy nawet w doskonałym dokumencie".

**Use case**: gdy Author łatwo wpada w confirmation bias. Default dla `requirements` na high-risk projektach.

### 3.3 Architektura techniczna

**Shared scratchpad** (Protokół C):

`.blast/specs/{feature}/debates/{topic}.md` z konwencją:

```markdown
# Debate: {topic}
**Protocol**: C (Round-robin)
**Started**: 2026-05-05T10:00:00Z
**Models**: Advocate=opus, Critic=qwen3.6-35b

---

## Round 1 — Advocate (opus, 2026-05-05T10:01:23Z)
{argument}

## Round 1 — Critic (qwen3.6-35b via MCP, 2026-05-05T10:02:11Z)
{counter-argument}

## Round 2 — Advocate (opus)
...

## Closing Position — Advocate
**Final stance**: ...

## Verdict — Judge (haiku, 2026-05-05T10:08:34Z)
---VERDICT---
VERDICT: PASS
BLOCKING: false
FINDINGS: 2 (resolved through debate)
NEXT_ACTIONS:
- /blast:tasks {feature} -y
---END---
```

Format jest read-only po zakończeniu debate — staje się audit trailem decyzji.

### 3.4 Cost & latency awareness

| Protokół | Calls | ~ tokens | ~ czas | Override gdy |
|---|---|---|---|---|
| A (Critique-Revise-Judge) | 3 | 30-60k | 1-2 min | default dla validate-* |
| B (Multi-Jury, N=3) | 4 (3+aggregator) | 40-80k | 1-2 min równolegle | default dla security |
| C (Round-robin, max 4) | 8-9 | 80-150k | 4-8 min | manual `--debate` flag |
| D (Devil's Advocate) | 2 | 20-40k | 1 min | high-risk requirements |

`/blast:status {feature}` pokaże debate cost w summary. Cap budgetu w spec.json: `"debate_max_tokens": 100000`.

---

## 4. Deep dive — Multi-LLM via MCP (Fala 10)

### 4.1 Dlaczego MCP

Claude Code natywnie obsługuje haiku/sonnet/opus. To rozwiązuje cost optimization. Nie rozwiązuje:

- **Adversarial diversity** — debate między modelami z tej samej rodziny ma ograniczoną wartość
- **Privacy** — kod proprietary nie powinien iść do żadnego API. Lokalne LLM (Ollama) załatwiają to natywnie
- **Specialization** — niektóre modele są lepsze w niszowych zadaniach (Codestral dla kodu, Claude dla designu, GPT-5 dla math, DeepSeek dla reasoning)
- **Cost extreme** — lokalna 35B model jest darmowa po one-time inwestycji w hardware
- **Resilience** — provider down → fallback do innego

### 4.2 Architektura — Hybrid

```
                    Claude Code (Anthropic) [orchestrator]
                              │
                              │ Task() spawn
                              ▼
                   Agent: spec-design-agent (sonnet)
                              │
                              │ uses tools:
                              ├─→ Read, Write, Edit (Claude Code native)
                              ├─→ ask_anthropic_*    (DIRECT, nie przez bridge)
                              └─→ MCP: blast-llm-bridge
                                  ├─→ ask_openrouter_<model>   (cloud, 100+ models)
                                  ├─→ ask_local_ubuntu_<model> (RTX 4090)
                                  └─→ ask_local_win11_<model>  (RTX 5090)
```

**Trzy kanały**:
1. **Anthropic native** — Claude Code już ma, nie wrappujemy
2. **OpenRouter** — jeden klucz dla wszystkich cloud non-Anthropic (OpenAI, Google, Together, etc.)
3. **Local Ollama** — bezpośrednio do dwóch maszyn klastra

### 4.3 MCP server design — `blast-llm-bridge`

Mały Python MCP server (~300 linii).

**Konfiguracja** (`.blast/settings/llm-bridge.json`):

```json
{
  "anthropic": {
    "via": "claude-code-native"
  },
  "openrouter": {
    "api_key_env": "OPENROUTER_API_KEY",
    "base_url": "https://openrouter.ai/api/v1",
    "auto_pricing": true,
    "auto_discover_models": true
  },
  "local": {
    "machines": {
      "ubuntu": {"url": "http://10.0.0.10:11434"},
      "win11":  {"url": "http://10.0.0.11:11434"}
    },
    "models": {
      "qwen3.6-35b-a3b": {"primary": "ubuntu",  "failover": "win11"},
      "qwen3-coder-30b": {"primary": "ubuntu",  "failover": null},
      "deepseek-v4-flash": {"primary": "win11", "failover": null},
      "qwen3-32b-instruct": {"primary": "win11", "failover": "ubuntu"}
    },
    "timeout_ms": 60000,
    "health_check_interval_s": 60
  }
}
```

**Tool naming convention**:
- `ask_openrouter_<openai-gpt5|google-gemini-pro|...>` — OpenRouter cloud
- `ask_local_<qwen3.6-35b|deepseek-v4-flash|qwen3-coder-30b|qwen3-32b-instruct>` — lokalne
- (brak `ask_anthropic_*` — Claude Code natywnie)

**Bezpieczeństwo**:
- API keys NIGDY w `llm-bridge.json` — tylko env var names
- Output sanitization, log usage do `.blast/logs/llm-bridge.log`
- Rate limiting per provider
- Retry z exponential backoff

### 4.4 Lokalne LLM — quickstart

**Ollama na obu maszynach**:

```bash
# Ubuntu (4090)
curl https://ollama.ai/install.sh | sh
sudo systemctl enable ollama
ollama pull qwen3.6:35b-a3b
ollama pull qwen3-coder:30b

# Win 11 (5090)
# Ollama Windows installer (one-click)
ollama pull deepseek-v4:flash
ollama pull qwen3:32b-instruct

# Verify (z każdej maszyny do drugiej)
curl http://other-machine:11434/api/tags
```

### 4.5 Per-phase routing

W `.blast/steering/llm-routing.md` (jeden plik, wszystkie polityki LLM):

```markdown
## Default routing per agent

| Agent | Default model |
|---|---|
| spec-design-agent (Atlas) | claude-opus |
| spec-tdd-impl-agent (Forge) | claude-sonnet |
| spec-tasks-agent (Loom) | claude-haiku |
| validate-design-agent (Crucible) | claude-sonnet |
| security-audit-agent (Sentinel) | claude-opus |

## Debate config (Fala 9 — opt-in)

(Pusta na start. Wpisz fazę gdzie chcesz włączyć debate.)

## Privacy patterns (gitattributes-style)

src/secrets/**            llm=local-only
*.pem                     llm=local-only
*.key                     llm=local-only
.env*                     llm=local-only
config/production.yml     llm=local-only
secrets/**                llm=local-only
*.proprietary             llm=local-only
```

---

## 5. Pełna roadmapa — Fale 7-10

### Fala 7 — Domknięcie luk SOTA (~2 wieczory)

**Cel**: parytet z Intent (drift), OpenSpec (delta), Kiro (graph).

#### 7.1 Delta Specs — `/blast:evolve`

- Komenda: `/blast:evolve <feature> "<opis zmiany>"`
- Tworzy `.blast/specs/{feature}/evolutions/{N}-{slug}/`
- Sub-spec dziedziczy parent → zawiera tylko **diff** (ADDED/MODIFIED/REMOVED requirements, design components, tasks)
- Implementacja: nowy agent `spec-evolve-agent` (haiku) **— persona Delta**, nowy template `templates/specs/evolution.md`
- Merge przy `/blast:complete` — orchestrator scala delta z parent specem
- Effort: 1 wieczór

#### 7.2 Cross-spec graph — `/blast:graph`

- Komenda: `/blast:graph` (bez argumentów)
- Czyta wszystkie `spec.json` w `.blast/specs/*/`
- Buduje graf zależności (`provides` ↔ `dependencies`)
- Output: ASCII graph + tabela ze stanem faz wszystkich specy
- Implementacja: pure script (Python), bez agenta
- Effort: 0.5 wieczoru

#### 7.3 Drift Detection — `/blast:drift`

- Komenda: `/blast:drift <feature>`
- Spawnuje haiku sub-agenta
- Czyta design.md `## Components` + tasks.md, grep'uje aktualny kod
- Raport: które komponenty z designu istnieją w kodzie, które nie istnieją, które różnią się od designu
- NIE auto-fixuje — tylko raportuje + sugeruje `/blast:evolve` jeśli drift jest legit
- Verdict envelope: PASS / WARN / FAIL
- Effort: 1 wieczór

### Fala 8 — Differentiation (~2 wieczory)

#### 8.1 Spec Linter — `/blast:lint`

- Komenda: `/blast:lint [<feature>]`
- Pure Python skrypt (deterministyczna walidacja, bez agenta)
- Sprawdza: EARS format, numeric IDs, traceability req↔task, design completeness, Verification Strategy quality, DRY vs INVENTORY, spec.json schema
- Output: `PASS / N issues / N warnings`
- Verdict envelope kompatibilne z Fala 4
- Hook integration: opcjonalnie wpięty jako gate przed `/blast:design`
- Effort: 1.5 wieczoru

#### 8.2 Telemetry — `/blast:telemetry`

- Komenda: `/blast:telemetry [--since <date>]`
- Czyta `.blast/logs/agent-runs.jsonl` (PostToolUse hook na Agent)
- Generuje markdown raport: cost per phase/spec/agent, time-to-shipped, gate failure rate, validate verdict trends
- Treść logów: TYLKO meta (timestamp, agent, model, tokens, duration, verdict, gate_blocked) — bez treści promptów
- Rotacja kwartalna: active → `archive/2026-Q1.jsonl.gz`
- Effort: 1 wieczór + 0.5 na log infrastructure

**Dodatkowo w Fali 8.2**: szkielet `.blast/steering/cost-policy.md` (placeholder, hard limits aktywne post-baseline 1-2 miesiące).

#### 8.3 Persona Naming — full personalities (decyzja Runda 3)

Każdy z 14 agentów dostaje:
- **Evocative angielskie imię**
- **Rolę** (1 linia)
- **Styl** (signature behavior)
- **Świadomą słabość** (self-monitoring) — explicit w prompcie
- **Peerów** (kogo zna w "zespole", kto go koryguje)

Tabela:

| Agent | Imię | Rola |
|---|---|---|
| spec-design-agent | **Atlas** | System architect — invariant-first, trade-off mapper |
| spec-tdd-impl-agent | **Forge** | TDD developer — czerwone-zielone-refaktor |
| spec-tasks-agent | **Loom** | Task weaver — atomowe taski w sekwencję |
| spec-requirements-agent | **Scribe** | EARS analyst — strukturyzacja wymagań |
| spec-tiny-agent | **Sprint** | Fast-path — "ship it now" |
| validate-design-agent | **Crucible** | Design reviewer — testy pod ogniem |
| validate-impl-agent | **Auditor** | QA — sceptyczny, corner cases |
| validate-gap-agent | **Bridge** | Integrator — codebase + plan |
| security-audit-agent | **Sentinel** | Red team — paranoiczny, exploity |
| spec-research-agent | **Oracle** | Research — fakty, prognozy |
| spec-review-agent | **Compass** | Senior code reviewer — clean code |
| spec-complete-agent | **Ledger** | Archivist — pamięć projektu |
| spec-evolve-agent (Fala 7) | **Delta** | Iterator — drobne zmiany |
| spec-deprecate-agent | **Curator** | Porządkujący — co zostaje, co odchodzi |

Przykład system prompt persony (Atlas):

```markdown
## You are Atlas

ROLE: System architect — invariant-first, trade-off mapper, design.md author.
STYLE: ASCII diagrams. Always asks "what's the invariant?" then "what if it changes?".

WEAKNESS YOU MUST WATCH FOR:
You over-design for "future-proofing" — adding flexibility for hypothetical 
needs. This is a known failure mode. When you catch yourself adding abstraction 
"just in case," LABEL IT EXPLICITLY in your output:
"⚠ Atlas-bias: I'm adding X for hypothetical future need Y. Consider stripping."

PEERS WHO CORRECT YOU:
- Crucible (validate-design) — calls out over-engineering
- Forge (impl) — pushes back when design is too abstract to code
- Sprint (tiny) — when called for small change, defer to him

In debates, address peers by name. Heed corrections. You're not always right.
```

Effort: 30 min (frontmatter rename) + ~1h (system prompts dla wszystkich 14)

### Fala 9 — Agent Debate Framework (~3-4 wieczory)

#### 9.1 Protocol library

- Nowy katalog `.claude/agents/blast/debate/`
- Cztery sub-agenty: `debate-author`, `debate-critic`, `debate-judge`, `debate-aggregator`
- Effort: 1 wieczór

#### 9.2 Orchestrator integration

- Modyfikacja `validate-design-agent`, `validate-impl-agent`, `security-audit-agent`:
  - Czytają `debate-config` z `.blast/steering/llm-routing.md` (lub `spec.json.debate.{phase}` override)
  - Brak config → standard single-agent path (zgodność wsteczna)
  - Z config → spawn debate sub-agentów per protokół
- Effort: 1.5 wieczoru

#### 9.3 Shared scratchpad

- Konwencja: `.blast/specs/{feature}/debates/{topic}.md`
- Append-only — staje się audit trailem
- Effort: 0.5 wieczoru

#### 9.4 Termination logic + Round 5 Synthesis & Addenda

- Stalemate detection (haiku similarity check)
- Cost ceiling enforcement
- Explicit escalation handling
- **Round 5 Synthesis & Addenda Loop** (po 4 rundach bez konsensusu):
  1. Claude (opus) syntezuje całą debatę
  2. Każdy non-Anthropic juror dostaje syntezę → addenda (max 3 po <30 słów)
  3. Claude integruje addenda → final summary
  4. User decyduje PASS/FAIL/REVISE → zapisane w `spec.json.debate.{phase}.user_call`
- Effort: 1 wieczór

#### 9.5 Tests + docs

- Synthetic events dla każdego protokołu
- Update CLAUDE.md sekcja "Agent Debate"
- Effort: 0.5 wieczoru

### Fala 10 — Multi-LLM via MCP (~3 wieczory)

#### 10.1 MCP server `blast-llm-bridge`

- Mały Python MCP server (~300 linii)
- Wrapper na: OpenRouter (cloud) + Ollama (oba lokalne machines)
- Anthropic NIE w bridge (Claude Code native)
- Konfig w `.blast/settings/llm-bridge.json`
- Effort: 1.5 wieczoru

#### 10.2 Tool naming convention + integration

- `ask_openrouter_<model>` — cloud
- `ask_local_<model>` — local (bridge sam routuje do ubuntu lub win11 per Pattern Z)
- Auto-discovery z provider APIs
- Update `.claude/settings.json` żeby register MCP server
- Effort: 0.5 wieczoru

#### 10.3 Per-phase config

- Zintegrowane w `.blast/steering/llm-routing.md` (decyzja Runda 1 #6 — opcja C)
- Mapping faza → preferred models, debate config, privacy patterns
- Effort: 0.5 wieczoru

#### 10.4 Privacy mode (extension Fali 5 hooks)

- Pattern matching na ścieżkach plików
- PreToolUse blocks `ask_<external>_*` calls dla matched paths
- Defaults out-of-the-box (.env, *.pem, *.key, secrets/**, *.proprietary)
- Effort: 0.5 wieczoru

#### 10.5 Docs + quickstart

- Setup guide: Ollama install, model recommendations, hardware setup
- Per-use-case configs (jury, debate, privacy)
- Cost calculator (auto z OpenRouter API)
- Effort: 0.5 wieczoru

---

## 6. Dependency graph faz

```
Phase 0 (spike, ~2.5 wieczoru)   ────────────┐
   ├─ Spike #1 cluster validation             │
   ├─ Spike #2 bridge MVP                     │
   └─ Spike #3 debate manual sim              │
                                              │ (decyzje informują pełną implementację)
Fala 7 (catch-up)            ────────────┐   │
   ├─ 7.1 evolve / Delta     ─┐          │   │
   ├─ 7.2 graph              ─┤          │   │
   └─ 7.3 drift              ─┘          │   │
                                          │   │
Fala 8 (differentiation)     ────────────┤   │
   ├─ 8.1 lint               ─┐          │   │       ┌──→ Fala 9 (debate)
   ├─ 8.2 telemetry          ─┼──┴───────┴──→│       │
   └─ 8.3 personas           ─┘                      │
                                                      │
                                                      └──→ Fala 10 (multi-LLM via MCP)
                                                              enables Fala 9 cross-provider

Fala 9 + Fala 10 → wzajemnie wzmacniające się
```

**Kolejność wdrożenia**:
1. Phase 0 spike (cluster + bridge MVP + debate sim)
2. Fala 7 (catch-up, niskie ryzyko)
3. Fala 8.1 (lint)
4. Fala 8.2 (telemetry + log infrastructure + cost-policy skeleton)
5. Fala 8.3 (personas — quick win)
6. Fala 9 (debate — core diferencjator)
7. Fala 10 (multi-LLM — wzmocnienie 9)

Łączny effort z spike'ami: ~13-16 wieczorów (~50-65 godzin) sequencyjnej pracy.

---

## 7. Rejestr decyzji (po dyskusji 2026-05-05)

Wszystkie pytania zamknięte. Audit trail dla decyzji architektonicznych.

### Runda 1 — pytania bazowe

1. **Debate config — gdzie?**
   - **DECYZJA: C, ale start z B** — `.blast/steering/llm-routing.md` jako global default (sekcja Debate config), ewolucja do override per-spec gdy potrzeba
   - **Default mode: opt-in** — config startuje pusty + komentarz "wpisz fazy które mają używać debaty"

2. **MCP server — własny czy istniejący?**
   - **DECYZJA: Hybrid architecture**:
     - **Cloud**: OpenRouter wrapper (jeden klucz, ~100 modeli, auto-pricing API)
     - **Lokalne**: bezpośredni Ollama wrapper na 2 maszynach
     - **Anthropic**: bezpośrednio przez Claude Code (NIE przez bridge)
   - Bridge: ~300 linii własnego Pythona (OpenRouter wrapper + Ollama wrapper + routing logic)

3. **Jak daleko z personami?**
   - **DECYZJA: B (pełne osobowości)** — evocative angielskie imiona + 5-7 linii system prompt
   - Imiona: Atlas, Forge, Loom, Scribe, Sprint, Crucible, Auditor, Bridge, Sentinel, Oracle, Compass, Ledger, Delta, Curator
   - Cross-persona awareness: tak, w debacie zwracają się po imieniu
   - Świadomość własnych słabości: tak, explicit w każdym prompcie

4. **Telemetry storage — gdzie?**
   - **DECYZJA: A (jsonl files)** — `.blast/logs/agent-runs.jsonl`
   - Logs shared (tracked w git) — cross-machine continuity
   - Rotacja kwartalna: `archive/2026-Q1.jsonl.gz`
   - Treść: TYLKO meta — bez promptów ani output

5. **Cost dashboard — pokazywać $ czy tylko tokens?**
   - **DECYZJA: tokens primary, $ secondary** — pricing.json z aktualnymi cenami, auto-update z OpenRouter API
   - Hardware costs IGNORED (local = $0 w telemetry)

6. **Privacy mode — jak deklarować pliki sensitive?**
   - **DECYZJA: zintegrowany z `llm-routing.md`** — jeden plik dla Default routing + Debate config + Privacy patterns
   - Format: gitattributes-style (`src/secrets/** llm=local-only`)
   - Wbudowane defaults: `.env*`, `*.pem`, `*.key`, `secrets/**`, `*.proprietary`

### Runda 2 — pytania architektury klastra

7. **Hardware** — finalny:
   - **Maszyna A (Ubuntu)**: RTX 4090 (24GB), 192GB RAM, i9 — *karty zostają jak są*
   - **Maszyna B (Win 11)**: RTX 5090 (32GB), 128GB RAM, i9
   - **LAN**: 10 Gbps ethernet
   - **NAS**: QNAP — dla logs/specs/backup, **NIE** dla weights (lokalne dla performance)

8. **Routing pattern**: **Z (Pinned + Failover)**

9. **Cluster availability**: **Private cluster (always-available)** — Ollama jako service, autostart, health checks. Graceful degradation tylko przy awarii

10. **Modele do hostowania**:
    - **Ubuntu (4090)**: Qwen3.6-35B-A3B (primary) + Qwen3-Coder-30B (secondary, code critic)
    - **Win 11 (5090)**: DeepSeek V4 Flash (primary) + Qwen3-32B-Instruct (secondary, fallback)
    - 4 modele "hot" preloaded, dostępne dla jury Pattern B (do N=4)

11. **Software stack**: Ollama na obu maszynach (uniform), autostart przez systemd / Win Service

12. **Storage strategy**: lokalne weights (per maszyna na SSD), NAS dla logs/specs/backup

### Runda 3 — pytania operacyjne

13. **Cost limits**: **DECYZJA: szkielet w Fali 8.2 + telemetry, hard limits aktywne dopiero po zebraniu historycznych danych**
    - `.blast/steering/cost-policy.md` jako placeholder
    - Hard limits konfigurowane po 1-2 miesiącach realnego użycia (p95 historical)

14. **Imiona persony** — zatwierdzone, peery zwracają się po imieniu w debacie

15. **Cross-persona awareness w prompcie** — tak

16. **Logi**: rotacja kwartalna, content meta-only, tracked

17. **Local LLM timeout**: 60s default, configurable

18. **Auto-repair spec.json**: NIE w MVP — git checkout jako standardowa droga rollbacku

### Runda 4 — strategia wdrożenia

19. **Spike pipeline before full implementation**: **DECYZJA: TAK — 3 spike'i** (sekcja 11)

20. **F4 — debate stalemate handling** (zaproponowane przez Błażeja, integrated jako Round 5 Synthesis & Addenda Loop, sekcja 10 / F4)

---

## 8. Hardware & Local Cluster Setup

### 8.1 Maszyny

| Slot | OS | GPU | VRAM | RAM | CPU | Hostuje |
|---|---|---|---|---|---|---|
| A | Ubuntu | RTX 4090 | 24 GB | 192 GB | i9 | Qwen3.6-35B-A3B (primary), Qwen3-Coder-30B |
| B | Win 11 | RTX 5090 | 32 GB | 128 GB | i9 | DeepSeek V4 Flash (primary), Qwen3-32B-Instruct |

LAN: 10 Gbps ethernet między maszynami. NAS QNAP dla logs/specs/backup.

### 8.2 Software stack

- **Ollama** na obu maszynach (port 11434)
- **Ubuntu**: systemd service (`ollama.service`), autostart at boot
- **Win 11**: Windows Service registration, autostart at boot
- **Health endpoint**: `GET /api/tags` jako liveness check
- **Concurrent**: Ollama domyślnie 1 request per model. Dla Pattern B (N=4) — albo queue, albo migrate to vLLM (post-MVP)

### 8.3 Routing — Pattern Z

Konfig w `.blast/settings/llm-bridge.json` (przykład w sekcji 4.3).

### 8.4 Privacy patterns

W `.blast/steering/llm-routing.md` (przykład w sekcji 4.5).

Hook (extension Fali 5) sprawdza patterns przed `ask_<external>_*` calls; blok przy violation.

---

## 9. Cost / Quality Strategy

Pięć zasad projektowych dla całego blast (filozofia "tani default, drogie świadomie"):

### 9.1 Default = tani. Quality = opt-in

- Single agent default. Debate gdy explicit włączony w `llm-routing.md`
- Haiku/sonnet/opus mapping (Fala 3) trzyma per-phase domyślne
- `--auto` w pipeline'ach nigdy nie eskaluje do opus/debate bez explicit zgody

### 9.2 Drogie ruchy są jawne

- Każde użycie opus, jury (Pattern B), Devil's Advocate (D) jest logowane
- Pre-action warning gdy przewidywany koszt > próg
- `/blast:telemetry` raportuje top-10 najdroższych calls miesięcznie

### 9.3 Lokalne first dla repeatable tasks

- Validate-* z lokalnym critic = darmowe (po hardware)
- Tylko high-stakes (security) używa cross-provider jury
- Privacy mode wymusza local — dual purpose: bezpieczeństwo + cost control

### 9.4 Quality nie jest negocjowalna na hard gates

- Hook gate (Fala 5) — zawsze działa, koszt 15ms
- Verification Strategy (Fala 2) — zawsze probowane po impl
- Test Relevance Audit (Fala 6) — zawsze odpalony, ~$0.05 (haiku)
- Final Lint Sweep (Fala 6) — zawsze, $0

### 9.5 Quality jest opt-in na soft gates

- Debate, Devil's Advocate, multi-jury — drogie, włączasz gdy stakes wysokie
- "Stakes wysokie" = security, payments, schema migrations, public API, regulatory

### 9.6 cost-policy.md — szkielet

W `.blast/steering/cost-policy.md` (placeholder od Fali 8.2):

```markdown
# Cost Policy

## Hard limits (DISABLED until baselines collected, 1-2 miesięcy)
# Single feature spec: max $5 (warn), max $10 (block)
# /blast:full --auto: max $20 (block)

## Soft warnings (active from day 1)
- Single Agent call > $1: log warning to telemetry
- Jury N>3: require explicit --jury-large flag

## Calibration
- After 1 month: review telemetry, set hard limits at p95 of historical
- After 3 months: tighten or relax based on observed pattern
```

---

## 10. Fallback Catalog

Każdy realistyczny failure mode + fallback strategia.

### F1. OpenRouter down
- **Detection**: bridge widzi non-2xx response
- **Fallback chain**: retry 2× (1s, 4s) → direct provider API → local equivalent → degrade to single-agent

### F2. Local machine offline
- **Detection**: TCP refused, timeout (60s)
- **Fallback**: Pattern Z failover → cloud (jeśli !privacy) → STOP (jeśli privacy)

### F3. Anthropic down
- **Fallback**: pause z czytelnym błędem, stan zachowany w spec.json. Nie próbujemy obejść — Claude Code to runtime

### F4. Debate stalls — Round 5 Synthesis & Addenda Loop (rozwiązanie Błażeja)
1. **Round 5a**: Claude (opus) syntezuje pełną debatę
2. **Round 5b**: każdy non-Anthropic juror dostaje syntezę → max 3 addenda po <30 słów
3. **Round 5c**: Claude integruje addenda → final summary
4. **Output**: full summary + linki do scratchpadu → user, z pytaniem `[PASS] [FAIL] [REVISE]?`
5. User decyzja zapisana w `spec.json.debate.{phase}.user_call`

### F5. MCP server crash
- Auto-restart bridge → 3× fails → degrade to "no external LLM" mode

### F6. Hook script crash
- Top-level try/except → exit 0 (allow) z log do stderr (już zaimplementowane Fala 5)

### F7. Privacy violation attempted
- Hook BLOK (exit 2) + komunikat
- Agent retryuje z lokalnym tool

### F8. spec.json corrupted
- STOP + `git checkout` jako rollback (no auto-repair w MVP)

### F9. Conflicting verdicts in jury (split)
- Majority (≥2) → ten verdict, dissent w `dissent_notes`
- Tie 1+1+1 → WARN z notatką "jury split", BLOCKING:false

### F10. Local LLM zwraca śmieci
- Bridge re-queries z explicit format prompt
- Fails 2× → fallback do cloud, log
- Telemetry: `local_format_failure_count` per model — >5% = model niesuited

### Tabela podsumowująca

| Failure | Detected by | Fallback | User-visible? |
|---|---|---|---|
| F1 OpenRouter down | bridge | retry → direct → local → degrade | tylko jeśli all fall through |
| F2 Local offline | bridge health | failover → cloud (!privacy) | tylko jeśli privacy + all down |
| F3 Anthropic down | Claude Code | pause, czytelny błąd | zawsze |
| F4 Debate stalls | termination logic | Round 5 Synthesis + escalate | zawsze (oczekiwane) |
| F5 MCP crash | Claude Code | auto-restart, degrade | tylko po 3 restartach |
| F6 Hook crash | hook itself | top-level try/except | log only |
| F7 Privacy violation | privacy hook | block + retry with local | zawsze |
| F8 spec.json corrupt | command/agent | STOP + git rollback | zawsze |
| F9 Jury split | aggregator | WARN + dissent notes | zawsze |
| F10 Local malformed | bridge regex | retry → cloud fallback | tylko per-call |

---

## 11. Spike Plan (Phase 0)

### 11.1 Filozofia

Zamiast 10 wieczorów kodu w ciemno, **2.5 wieczora spike testów** weryfikuje krytyczne assumptions. Po każdym spike'u podejmujemy konkretne decyzje architektoniczne na bazie danych.

### 11.2 Spike #1 — Local cluster validation (1 wieczór)

**Cel**: czy 4090 + 5090 + Ollama + LAN dają sensowną performance?

**Setup**:
1. Install Ollama na Win 11 (jeśli jeszcze nie)
2. Pull modeli: Qwen3.6-35B-A3B + Qwen3-Coder-30B na Ubuntu, DeepSeek V4 Flash + Qwen3-32B na Win 11
3. Skonfiguruj firewall (port 11434 open w LAN)
4. Test connectivity: `curl http://other-machine:11434/api/tags`

**Test**:
1. **Quality**: ten sam prompt validate-design → Qwen3.6, DeepSeek, Claude opus. Manualne porównanie
2. **Latency**: cold start, warm response, tokens/sec
3. **Concurrent**: 2 równoległe calls do Qwen3.6 — performance impact?
4. **Cross-machine**: Ubuntu wysyła do Win 11 — overhead?

**Decyzja po**:
- Jeśli local "much worse than Claude" → tylko privacy mode + jury diversity
- Jeśli "comparable" → agresywniej local jako critic
- Jeśli "concurrent kills throughput" → Pattern Y (pool) zamiast Z

**Effort**: 1 wieczór. Bez kodu w blast.

### 11.3 Spike #2 — Bridge MVP (1 wieczór)

**Cel**: minimum viable MCP bridge — działa? Claude Code go widzi?

**Scope**:
- Python skrypt `blast-llm-bridge.py` (~100 linii MVP)
- 2 toole: `ask_local_ubuntu_qwen` i `ask_local_win11_deepseek`
- Konfiguracja w `.claude/settings.json` jako MCP server
- Testowa komenda `/blast:ping-llm`

**Test**:
1. Claude widzi tools po `/mcp` w Claude Code?
2. `/blast:ping-llm` zwraca odpowiedzi z obu maszyn?
3. End-to-end latency?
4. Co gdy Win 11 off? (test fallback path)

**Decyzja po**: MVP works → green light dla pełnej Fali 10. Issues → debugujemy

**Effort**: 1 wieczór.

### 11.4 Spike #3 — Manual debate simulation (0.5 wieczoru)

**Cel**: czy multi-model debate na realnym przykładzie daje lepsze wyniki niż solo?

**Test**:
1. Weź jeden istniejący spec / design.md
2. **Solo baseline**: validate-design solo (Claude opus) → output
3. **Pattern A simulation**:
   - Author: Claude opus
   - Critic: Qwen3.6 ("find 3 weaknesses, NEVER agree on first pass")
   - Judge: Claude haiku
4. Porównaj outputy

**Decyzja po**:
- Debate konsekwentnie znajduje issue solo nie znalazł → wartość udowodniona, full Fala 9
- Debate głównie powtarza → przemyśl Pattern D (taniej) zamiast A
- Specyficzne pattern działa lepiej → priorytetyzuj

**Effort**: 0.5 wieczoru. Bez kodu.

### 11.5 Spike outputs

Po każdym spike'u nowy plik w `.blast/knowledge/research/`:
- `spike-1-local-cluster-2026-05-XX.md`
- `spike-2-bridge-mvp-2026-05-XX.md`
- `spike-3-debate-sim-2026-05-XX.md`

Te są trwałe — gdy Fala 10 będzie pisana, agenty research/design będą mieć dostęp.

---

## 12. Success metrics

**Mechaniczne (deterministyczne)**:
- ☐ Wszystkie luki SOTA z sekcji 1 oznaczone ✓
- ☐ `/blast:lint` raportuje ≤5 issues per typowy spec
- ☐ Debate latency: A <2 min, B <2 min, C <8 min, D <1 min
- ☐ Cost overhead debate dla validate-design <2x single-agent
- ☐ Lokalny LLM (Qwen3.6 lub DeepSeek) działa z `validate-design` w privacy mode
- ☐ Round 5 Synthesis & Addenda Loop testowany na realnym stalemate

**Adopcja (jakościowe)**:
- ☐ Co najmniej 3 inne osoby próbują blast bez Twojego coachingu
- ☐ Pojawia się GitHub issue / PR od kogoś innego
- ☐ Komentarz w ekosystem comparison ("blast" wspomniany przez kogoś z zewnątrz)

**Reputacja**:
- ☐ Podpisałeś się pod blogiem porównującym blast do innych SDD frameworków
- ☐ Co najmniej jeden spec dogfooded przez >5 iteracji evolutions

---

## 13. Co dalej

### Phase 0 — Spike (~2.5 wieczoru, BEFORE commitment)

1. **Sesja A**: Spike #1 — Local cluster validation (1 wieczór)
2. **Sesja B**: Spike #2 — Bridge MVP (1 wieczór)
3. **Sesja C**: Spike #3 — Debate manual simulation (0.5 wieczoru)

Każdy spike kończy się dokumentem decyzyjnym w `.blast/knowledge/research/`.

### Phase 1 — Catch-up SOTA (Fala 7, ~2 wieczory)

4. **Sesja 1**: Fala 7.1 (delta specs / `/blast:evolve`)
5. **Sesja 2**: Fala 7.2 + 7.3 (graph + drift)

### Phase 2 — Differentiation (Fala 8, ~2.5 wieczory)

6. **Sesja 3**: Fala 8.1 (lint)
7. **Sesja 4**: Fala 8.2 (telemetry + log infrastructure + cost-policy.md skeleton)
8. **Sesja 5**: Fala 8.3 (personas — full system prompts dla 14 agentów)

### Phase 3 — Debate (Fala 9, ~3-4 wieczory)

9. **Sesja 6**: Fala 9.1 + 9.2 (protocol library + orchestrator integration)
10. **Sesja 7**: Fala 9.3 + 9.4 (shared scratchpad + termination logic + Round 5 Synthesis)
11. **Sesja 8**: Fala 9.5 (tests + docs)

### Phase 4 — Multi-LLM (Fala 10, ~3 wieczory)

12. **Sesja 9**: Fala 10.1 + 10.2 (MCP server + tool naming) — w dużej mierze już zaspike'owane
13. **Sesja 10**: Fala 10.3 + 10.4 + 10.5 (per-phase config + privacy mode + docs)

### Checkpoint po Fali 10

Verifikacja z 11 success-metrykami z sekcji 12. Jeśli osiągnięte — opcjonalna Fala 11 (dystrybucja).

Łączny effort: ~13-16 wieczorów (~50-65 godzin).

### Strategia commit / branch

- Każda Fala = osobna gałąź `fala/N-{name}`
- Spike'i: gałąź `phase-0-spike` z 3 commitami
- Merge do `main` po zakończeniu Fali (po self-review + manual smoke test)
- Tag `v0.{wave-number}` po każdym mergu

### Dogfooding

Po Fali 8 — używamy blast'a do specyfikacji **samego blast'a**. Każda kolejna Fala (9, 10) jest specyfikowana przez `/blast:full --validate`. Finalna walidacja: jeśli blast nie poradzi sobie ze swoim własnym specyfikowaniem, jest problem.

---

## 14. Notatka końcowa

### Stan po dyskusji (2026-05-05)

Wszystkie pytania architektury zamknięte. Plan gotowy do execution.

### Strategiczne pozycjonowanie

Po pełnej implementacji blast będzie unikatowy w trzech wymiarach których SOTA NIE pokrywa:

1. **Hard SDK-level enforcement** (Fala 5 zrobiona) — jedyny SDD framework z PreToolUse hook gates
2. **Multi-protocol agent debate** (Fala 9) — 4 protokoły z explicit cost/quality tradeoffami; F4 Synthesis & Addenda Loop dla nierozwiązywalnych konfliktów
3. **Hybrid LLM cluster** (Fala 10) — Anthropic-native + lokalne (4090+5090, 4 modele live) + OpenRouter cloud bez vendor lock-in. Privacy-first, cost-conscious, quality-uncompromising.

Plus wszystko co już blast ma (verdict envelope, test relevance audit, verification strategy enforcement, model routing, .gitattributes hygiene) — żaden inny framework nie ma kombinacji tych ficzerów.

### Filozofia projektowa

Filozofia blast — *egzekucyjność > popularność, jakość > marketing* — jest zgodna z tym co społeczność SDD najbardziej krytykuje u konkurencji ("markdown monster", "vibe coding debt", "spec rot"). Plan podwaja stawkę na tej filozofii.

### Co to znaczy w praktyce

- **Day 1 po Fali 10**: blast obiektywnie najmocniejszy SDD framework w wymiarze egzekucyjności i jakości decyzji
- **Day 1 po Fali 11 (jeśli)**: blast może być najpopularniejszym, jeśli marketing dorówna technologii
- **Day 365**: jeśli dystrybucja jest, blast definiuje SDD w ekosystemie Claude Code


---

## Spike-3 verdict — Fala 9 scope cuts (dopisane 2026-05-06)

**Spike #3 (multi-LLM code review validation)** zakończony 2026-05-06. Pełen raport: `r_and_d/research/spike-3/README.md` + `report.md`.

### TL;DR

Multi-LLM debate daje **marginal recall gain (+0.05, czyli 1 bug z 18)** vs solo Claude opus. Pre-committed thresholds (+0.10 dla HYBRID, +0.15 dla JURY) **nie zostały spełnione**. Pełna Fala 9 z 4 protokołami debate jako default = drogi teatr.

### Najważniejsze findings z liczb

1. **JURY_3_FLASH3** (Opus ‖ qwen3.6 ‖ Gemini-3-Flash → Haiku agg) wygrywa F1 (0.71), ale solo Opus tylko 0.01 punkt niżej (0.70) przy 1.8× tańszym i 3× szybszym.
2. **HYBRID** (Sonnet ‖ qwen3.6 → Haiku judge) F1 ~tied z SONNET_SOLO (0.61 vs 0.62). Qwen jako parallel critic dorzuca recall (+0.05) ale i FP. Wartościowy TYLKO gdy recall priority > precision.
3. **Gemini 3 Flash beats Gemini 2.5 Pro** dla review: precision 0.57 vs 0.41 przy same recall. Same cost. **Drop 2.5-pro całkiem**.
4. **QWEN_SOLO recall 0.72** — wystarczająco dobry żeby być solo reviewer w privacy mode. Catastrophic blind spot na observability/parser code (0/3 na `05_parser.py`).
5. Wszystkie arms przegapiły `wp-unbounded-queue` — multi-arm nie jest cudem, niektóre bugi po prostu wymagają eksplicytnych prompt directives.

### Modified Fala 9 scope (vs original)

**KEEP**:
- ✅ Asymmetric Pattern A (HYBRID-style) jako `validate-impl --thorough` opt-in
- ✅ Pattern B (JURY_3_FLASH3) jako default dla `security` i high-stakes `validate-design`/`review`
- ✅ Verdict envelope rozszerzony o multi-source findings (już mamy infra)

**DROP**:
- ❌ Pełna implementacja 4 protokołów debate (Critique-Revise-Judge, Multi-Jury Vote, Round-Robin, Devil's Advocate). Spike data nie supportuje — pojedynczy "Pattern A asymmetric + Pattern B for high-stakes" pokrywa 90% wartości.
- ❌ Round-Robin Debate z scratchpad (`debates/{topic}.md`). Złożone, mało dowodów na value.
- ❌ Devil's Advocate jako osobny protokół. Można zrealizować przez prompt do critica.
- ❌ `--debate` flag uniwersalny dla każdej fazy. Zostaje tylko `--thorough` na validate-impl.

**Effort saved**: ~2-3 wieczory. Realokować na Falę 7 (delta specs / drift / graph) i Falę 10 (production multi-LLM bridge).

### Routing (do `.blast/steering/llm-routing.md`, źródło prawdy)

| Faza | Default | High-stakes / `--thorough` |
|---|---|---|
| `requirements`, `tasks`, `complete`, `deprecate`, `tiny` | Haiku | — |
| `research` | Sonnet | — |
| `design` | Opus | — |
| `impl` Author | **qwen3-coder:30b** (5090) | — |
| `validate-gap` | Haiku | — |
| `validate-design` | Sonnet | **JURY_3_FLASH3** |
| `validate-impl` | Sonnet | **HYBRID** (Sonnet ‖ qwen3.6 → Haiku) |
| `security` | **JURY_3_FLASH3** | — |
| `review` | Sonnet | **JURY_3_FLASH3** dla auth/payments/schema |
| Privacy mode (override) | qwen3.6:latest local | — |

### Cost impact

- Default review per spec: ~$0.10-0.30 (Sonnet-dominated)
- High-stakes review per spec: ~$0.50-1.00 (JURY_3_FLASH3-dominated)
- Pełny `/blast:full` standard spec: ~$1-2 (był ~$3-8 estimate)
- Pełny `/blast:full` --thorough spec: ~$2-4
- Pełny `/blast:full` security-tagged spec: ~$3-5
