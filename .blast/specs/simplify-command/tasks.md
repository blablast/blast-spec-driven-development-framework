# Implementation Plan — `/blast:simplify`

> Większość pracy to pliki promptów (agent + slash-command) i wpięcia w dokumentację frameworka. „Testy" tu = smoke na strukturze plików (frontmatter, sekcje) + ręczna próba na realnym specu, bo to artefakty Claude Code, nie kod wykonywalny.

- [x] 1. Agent `simplify-agent` (Occam)
  - Plik `.claude/agents/blast/simplify.md`: frontmatter (name, description, tools, model=sonnet, color), persona Occam, 6 osi redukcji, tryb raportu + `--apply`, verdict envelope
  - _Requirements: 1, 2, 3, 5_

- [x] 1.1 Guardrail Karpathy Rule 3 w agencie
  - Constraints: ochrona komentarzy (downgrade do report-only przy niezrozumianym komentarzu), wąska licencja na zastany dead-code (a+b+c), zakaz tykania testów
  - _Requirements: 4_

- [x] 2. Slash-command `/blast:simplify`
  - Plik `.claude/commands/blast/simplify.md`: parse args (`--apply`/`--debate`/`--no-debate`), auto-detect feature, routing FIRE/SKIP (brak configu → solo Sonnet), linia `Routing:`, spawn agenta, display result
  - _Requirements: 5_

- [x] 3. Wpięcie w pipeline (CLAUDE.md)
  - Pipeline diagram `[simplify]` po `[validate-impl]`; skróty; Smart Routing (wiersz „wszystkie taski [x]"); Model routing (sonnet)
  - _Requirements: 5_

- [x] 3.1 Wpięcie w README.md
  - Pipeline line, tabela komend (+wiersz simplify), liczniki (30 komend / 22 agentów), sekcja Karpathy-aligned
  - _Requirements: 5_

- [x] 4. Wzmocnienie reguł rdzenia (Karpathy emphasis)
  - `ai-collaboration.md` Rule 2: ilościowy gut-check (200→50, 1000→100); Rule 3: ochrona komentarzy + orphans-vs-preexisting
  - `code-principles.md` Review Checklist: 2 nowe pozycje (komentarze, your-orphans-only)
  - _Requirements: 4_

- [x] 5. Konfiguracja debate routing dla simplify
  - Dodany blok `debate_config.simplify` (enabled: true, trigger: high_stakes, composition: HYBRID) do `.blast/steering/llm-routing.md` + persona Occam w tabeli routingu
  - Default = solo Sonnet (hygiene step); debate tylko na auth/payments/schema lub `--debate`
  - _Requirements: 5_

- [x] 6. Smoke verification (Verification Strategy z design.md)
  - [x] 6.1 Frontmatter agenta parsuje się (`yaml.safe_load`) — PASS
    - _Requirements: 5_
  - [x] 6.2 Sekcje obecne: `grep` na 'verdict envelope' + 'Verification Strategy' w agencie — PASS
    - _Requirements: 3, 5_
  - [ ] 6.3 E2E na realnym shipped-specu — DEFERRED: brak zaimplementowanego blast-specu z kodem w `specs/` (tylko meta-spec simplify-command). Uruchomić przy pierwszym realnym użyciu `/blast:simplify` na shipped feature.
    - _Requirements: 1, 3_

- [x] 7. Backfill: decision write-back (ADR)
  - Zapisana decyzja „standalone vs review --simplify" → `.blast/knowledge/decisions/2026-05-25-simplify-standalone-vs-review-mode.md`
  - Kill-switch lesson udokumentowany: jeśli po 5 użyciach pokrycie z review > 70% → scal do `review --simplify`
  - _Requirements: 2_
