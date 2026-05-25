# blast — Spec-Driven Development by Błażej Strus

> **blast** = Błażej Strus' AI Development Life Cycle.
> Mój system, moje zasady, mój flow.

## Filozofia

blast to moje podejście do programowania z AI — uporządkowane, ale bez kija w dupie.
Każda ficzerka przechodzi przez jasne fazy: od pomysłu, przez specyfikację, aż po kod.
Nie piszemy kodu w ciemno. Najpierw wiemy CO, potem JAK, a dopiero wtedy lecimy z implementacją.

## Struktura projektu

- **Constitution** (`.blast/CONSTITUTION.md`) — top-level governance, eleven Articles binding every spec/agent. Read first.
- **Steering** (`.blast/steering/`) — pamięć projektu: kontekst, stack, konwencje (operational expansion of Articles)
- **Specs** (`.blast/specs/`) — specyfikacje poszczególnych ficzerów
- **Knowledge** (`.blast/knowledge/`) — baza wiedzy: decyzje, referencje, wyniki researchów
- **Settings** (`.blast/settings/`) — reguły, szablony, konfiguracja systemu

Pełna dokumentacja: `.blast/README.md`. Governance intent: `.blast/CONSTITUTION.md`.

## Komendy blast

Pełen wykaz komend, flag i przykładów → `/blast:help [komenda]`.

### Pipeline

```
steering → init → requirements → [research] → design → [validate-design] → tasks → [validate-tasks] → impl → [validate-impl] → [simplify] → complete → security → steering [→ push]
```

`[optional]` = fazy opcjonalne. Walidacje (`validate-gap`, `validate-design`, `validate-impl`) i `simplify` też opcjonalne — wchodzą po właściwej fazie. `simplify` = jedyny krok który złożoność *odejmuje* (behavior-preserving, bramkowany Verification Strategy); po `validate-impl`, przed `complete`.

### Skróty

- `/blast:quick "opis" [--auto] [--research]` — tylko spec (init→req→[research]→design→tasks)
- `/blast:full "opis" [--auto] [--research] [--validate] [--no-debate] [--push]` — pełny pipeline. Debate = default gdy validation fires; `--no-debate` downgrade'uje na solo Sonnet (cost/speed).
- `/blast:status [f]` — status i postęp specu
- `/blast:validate-tasks {f}` — KISS + SOTA review tasks.md przed impl (auto-fires na complex specs)
- `/blast:simplify {f} [--apply]` — behavior-preserving odchudzanie kodu PO impl; raport domyślnie, `--apply` tnie i re-runuje Verification Strategy (revert na czerwonych)
- `/blast:learn [--lessons|--calibrate|--routing|--refresh-sota|--all]` — self-improvement aggregator (auto co 5 shipped specs)
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
| `phase: "requirements-generated"`, requirements NOT approved | → Review `requirements.md`, potem `/blast:approve {f} requirements` (lub `/blast:design {f} -y` żeby ominąć) |
| `phase: "design-generated"`, design approved | → `/blast:tasks {feature}` |
| `phase: "design-generated"`, design NOT approved | → Review `design.md`, potem `/blast:approve {f} design` (lub `/blast:tasks {f} -y` żeby ominąć). Opcjonalnie: `/blast:validate-design` |
| `phase: "tasks-generated"`, tasks approved | → `/blast:validate-tasks {feature}` (if complex/--debate) lub `/blast:impl {feature}` |
| `phase: "tasks-generated"`, tasks NOT approved | → Review `tasks.md`, potem `/blast:approve {f} tasks` (lub `/blast:impl {f} -y` żeby ominąć) |
| Wszystkie taski `[x]` w tasks.md | → opcjonalnie `/blast:simplify {feature}` (odchudź drift przed inventory), potem `/blast:complete {feature}` |
| `status: "shipped"` | → `/blast:security {feature}` (rekomendowane); ewolucja: `/blast:evolve {feature} "<change>"`; nowy ficzer: `/blast:init` |
| `phase: "evolution-generated"`, evolution NOT approved | → Review `evolutions/{N}-{slug}/evolution.md`, potem `/blast:approve {f}-evo-{N} evolution` |
| `phase: "evolution-generated"`, evolution approved | → `/blast:impl {f}-evo-{N}` (delta jest unifikowany — single approval gate) |

**Phase guards** — komendy `/blast:design`, `/blast:tasks`, `/blast:impl` egzekwują approval gate na poziomie slash command (read spec.json -> sprawdź `approvals.{prev}.approved`). Bez approve i bez `-y` komenda STOP'uje przed odpaleniem subagenta i pokazuje konkretny next step (`/blast:approve {f} {phase}` lub `-y` jako bypass). To realny gate, nie ostrzeżenie.

**Auto-detect feature** — jeśli jest tylko jeden aktywny spec, AI domyśla się o który ficzer chodzi (nie trzeba podawać nazwy).

## Pamięć projektu i DRY

blast pilnuje DRY na poziomie cross-spec:

- **INVENTORY.md** (`.blast/steering/INVENTORY.md`) — rejestr shipped komponentów, aktualizowany przez `/blast:complete`. Framework writes here. Jeśli plik nie istnieje, `/blast:complete` go stworzy. Historical snapshots tego repo siedzą w `r_and_d/INVENTORY.md` (patrz `MANIFEST.md`).
- **spec.json → `provides`** — każdy spec deklaruje co dostarcza (komponenty, serwisy, typy)
- **spec.json → `dependencies`** — każdy spec deklaruje od czego zależy
- **Cross-spec check** — agenci requirements, design i validate-gap sprawdzają inne spece przed generowaniem, żeby nie duplikować
- **Status lifecycle** — `planning` → `active` → `shipped` → ew. `deprecated`

Workflow pamięci: `/blast:impl` → `/blast:complete` (aktualizuje inventory) → `/blast:steering` (synchronizuje pamięć)

## Konfiguracja Steering

- Ładuj cały `.blast/steering/` jako pamięć projektu
- Domyślne pliki: `product.md`, `tech.md`, `structure.md`, `INVENTORY.md`
- Pliki niestandardowe obsługiwane przez `/blast:steering-custom`

### Knowledge SOTA (Pragmatist agent reference)

`.blast/knowledge/sota/*.md` — curated SOTA recommendations per technology area. Read by `validate-tasks-agent` (Pragmatist) before suggesting library alternatives. Refresh audit via `/blast:learn --refresh-sota` (flags files >6mo old).

### Steering loading discipline (cache w sesji)

- Steering w obrębie jednej sesji jest stabilny — **nie czytaj `.blast/steering/*.md` ponownie** jeśli załadowałeś go już w bieżącej rozmowie. Treść zacachowana w kontekście jest źródłem prawdy do końca sesji (chyba że user explicit modyfikuje steering komendą `/blast:steering` lub `/blast:steering-custom`).
- Subagenci uruchamiani przez Task tool startują w świeżym kontekście — tam re-read jest konieczny, ale ogranicz go do plików których agent rzeczywiście potrzebuje (patrz tabela poniżej).
- Po `/blast:steering` lub `/blast:steering-custom` — invalidate cache i przeczytaj zmienione pliki ponownie.

### Per-agent steering scope (rekomendacje)

| Agent | Wymagane pliki steering |
|---|---|
| requirements | `product.md` (purpose, invariants), `tech.md` (constraints, gotchas) |
| research | `tech.md`, `RESEARCH.md` (jeśli istnieje) |
| design | `product.md`, `tech.md`, `structure.md`, `INVENTORY.md` (DRY check) |
| tasks | `tech.md`, `structure.md` |
| impl | `tech.md` (Canonical Commands), `structure.md`, `product.md` (Invariants) |
| validate-* | wszystko (cross-validate vs steering) |
| complete | wszystko (aktualizuje INVENTORY, dorzuca lessons do tech.md/product.md) |
| review, security | `product.md` (Invariants), `tech.md` (gotchas) |

Te zakresy są wskazówką, nie egzekwowanym kontraktem — agent może doczytać więcej jeśli zadanie tego wymaga.

## Model routing

Każdy agent w `.claude/agents/blast/` ma jawnie ustawiony `model:` zamiast `inherit`. Mapping (na 2026-05):

| Model | Agenci | Rationale |
|---|---|---|
| `haiku` | requirements, tasks, complete, deprecate, steering-custom, tiny | Templating + structured output, niska złożoność reasoning |
| `sonnet` | impl, research, review, steering, validate-gap, validate-design, validate-impl, simplify | Code reasoning, multi-file analysis, balanced cost/quality |
| `opus` | design, security | Architecture decisions + high-stakes audits |

Override per-call: zmień `model:` w odpowiednim pliku agenta. Jeśli nie wiesz — zostaw routing default'owy.

## Hard approval gate via Claude Code hooks

blast ma teraz **deterministyczny gate** na poziomie SDK, nie tylko prompt-level. Konfiguracja w `.claude/settings.json` rejestruje hook PreToolUse na matcherze `^(Agent|Task)$`, który odpala `.claude/hooks/blast-approval-gate.py` przed każdym wywołaniem subagenta.

Skrypt egzekwuje:
- `spec-design-agent` wymaga `approvals.requirements.approved == true`
- `spec-tasks-agent` wymaga `approvals.design.approved == true`
- `spec-tdd-impl-agent` wymaga `approvals.tasks.approved == true`

Bypass paths (skrypt przepuszcza bez czytania spec.json):
- `subagent_type` nie jest jednym z trzech powyższych (np. `general-purpose`, `validate-*`, `security`, `Explore`)
- prompt zawiera `Auto-approve: true` (slash command z flagą `-y`)
- `subagent_type == spec-tiny-agent` (zawsze przepuszczany)
- `spec.json.tiny == true` (defensywne — tiny spec już self-approved)

Reakcja na FAIL:
- Hook zwraca `exit 2`
- Claude Code przekazuje stderr jako error message do agenta
- Agent **nie zostaje uruchomiony** — to jest twardy gate, nie ostrzeżenie

Performance: ~15ms per invocation (Python startup + I/O). Niewidoczny dla użytkownika nawet przy częstych wywołaniach.

Współistnienie z markdown-level gate: markdown gate w slash commands daje fast-fail z czytelnym komunikatem zanim Claude w ogóle spróbuje wywołać Agent. Hook to last line of defense — zatrzyma wywołanie nawet jeśli markdown gate zostanie ominięty (zmodyfikowany slash command, bezpośrednie wywołanie Task).

**Defense in depth**: command-level prompt gate → hook-level SDK gate.

**Jeśli hook false-positive blokuje legitne wywołanie**: poprawka jednego z dwóch:
1. slash command nie emituje standardowego nagłówka `Feature: <name>` w prompcie subagenta — popraw slash command
2. flow wymaga bypass'u który nie pasuje do żadnej z bypass paths — dodaj bypass path do skryptu

**Tymczasowy disable**: usuń sekcję `hooks` z `.claude/settings.json`, hook nie odpali.

## Multi-LLM compositions (opt-in)

blast obsługuje wieloprovider'owy code review przez `debate_config:` w `.blast/steering/llm-routing.md`. Source of truth dla routingu i kompozycji.

### Compositions

- **HYBRID** — `validate-impl --debate`. Sonnet ‖ qwen3.6:latest (parallel critic) → Haiku judge. ~$0.12/spec, ~130s.
- **JURY_3_FLASH3** — `security` (always), `validate-design --debate`, `review --debate` dla auth/payments/schema. Opus ‖ qwen3.6:latest ‖ Gemini-3-Flash (3-juror) → Haiku aggregator. ~$0.17/spec, ~141s.
- **Solo Sonnet/Opus/Haiku** — default dla większości faz (patrz Model routing wyżej).

### Privacy mode

`spec.json.privacy: local-only` → `blast-privacy-gate.py` hook (registered w `settings.json::PreToolUse`) blokuje wszystkie external LLM calls. Routing fallback na lokalne Qwen via `mcp__blast-llm-bridge__ask_ubuntu_qwen36`. Zero cost, zero data leak.

### MCP bridge

`.claude/mcp/blast-llm-bridge.py` exposes lokalne Ollama models jako MCP tools (`ask_ubuntu_qwen36`, `ask_ubuntu_qwen3_coder`). Bridge registered w `.mcp.json`. Tylko Ubuntu/5090 wrappers (Win11/4090 wrapper'y nie istnieją — VRAM constraint na 32B Q4).

## R&D vs Framework separation

To repo zawiera 3 kategorie plików — patrz `MANIFEST.md` na repo root:

- **FRAMEWORK** — `.claude/`, `.blast/settings/`, top-level READMEs/CLAUDE.md/.env.example. Universal blast, dystrybuowane jako template.
- **HYBRID** — `.blast/steering/llm-routing.md` + `cost-policy.md`. Framework-required path, project-specific content. Templates dla nowego clone'a w `.blast/settings/templates/steering/*.template`.
- **R&D** — `r_and_d/` (roadmap, spikes, INVENTORY snapshot, steering snapshots). Personal content, NIE jest częścią dystrybuowanego template'a.

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
