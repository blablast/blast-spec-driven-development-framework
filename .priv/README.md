# r_and_d — Project R&D content

**Co to jest**: ten katalog zawiera **content specyficzny dla mojego projektu** — research, decyzje, spike outputs, project state snapshots. **NIE jest częścią dystrybuowanego framework'a blast**.

Gdy ktoś klonuje `claude_code-template` jako template:
- DOSTAJE: framework (`.claude/`, `.blast/settings/`, `README.md`, `CLAUDE.md`, `.env.example`, etc.)
- NIE DOSTAJE: zawartości tego katalogu (po cleanupie przy clone)

Patrz `MANIFEST.md` na repo root dla pełnej klasyfikacji FRAMEWORK vs R&D.

## Struktura

```
r_and_d/
├── README.md                       ← ten plik
├── INVENTORY.md                    ← snapshot stanu projektu (post Spike-3)
├── decisions/                      ← strategiczne decyzje, roadmap, ADRs
│   └── 2026-05-05-sdd-number-one-roadmap.md
├── research/                       ← spike outputs (Phase 0 validation)
│   ├── spike-1/                    ← local cluster benchmark (qwen vs Claude)
│   ├── spike-2/                    ← MCP bridge MVP
│   └── spike-3/                    ← multi-LLM code review validation
└── steering-snapshot/              ← snapshot mojej project-specific steering config
    ├── cost-policy.md              ← (żywa kopia w .blast/steering/cost-policy.md)
    └── llm-routing.md              ← (żywa kopia w .blast/steering/llm-routing.md)
```

## Snapshots vs live config

`steering-snapshot/` zawiera ARCHIWALNĄ kopię mojego `.blast/steering/cost-policy.md` i `llm-routing.md` w stanie post Spike-3. **Live versions** używane przez framework siedzą w `.blast/steering/` — ten snapshot służy tylko do:
- Backup przed eksperymentami z routingiem
- Reference dla "co wiem o moim setup'ie na 2026-05-06"
- Diff comparison gdy zmienię steering w przyszłości

Jeśli zmienisz `.blast/steering/llm-routing.md` (np. dodasz nowy juror, swap'niesz model), zaktualizuj też snapshot, żeby zostawić ślad.

## Cross-references

INVENTORY.md, roadmap.md i spike READMEs używają względnych ścieżek wewnątrz `r_and_d/` oraz `.blast/` paths gdy odnoszą się do framework'a.

## Co nie jest tutaj

- **Aktywne specy**: `.blast/specs/` (per-project, nie R&D archive)
- **Live steering**: `.blast/steering/` (framework reads here)
- **Framework templates**: `.blast/settings/templates/` (część blast'a)
- **Logi telemetry**: `.blast/logs/agent-runs.jsonl` (per-session, gitignored)

## Distribution flow (gdy ship'uję blast jako template)

Future packaging script `tools/package-blast.sh` (nie istnieje jeszcze) zrobi:
1. Skopiuje wszystkie FRAMEWORK files do `dist/`
2. POMIJA `r_and_d/` całkowicie
3. Replace'uje `.blast/steering/{cost-policy,llm-routing}.md` z template versions z `.blast/settings/templates/steering/`
4. Restart .blast/{specs,knowledge,logs,steering}/ jako empty z .gitkeep
5. Tarball / commit do `claude_code-template` public repo

Bez packaging script'u — gdy teraz ktoś klonuje **bezpośrednio** to repo, dostaje też R&D. To bug, nie feature. Fix przyjdzie z packaging.
