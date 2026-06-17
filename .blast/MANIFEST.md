# blast Distribution Manifest

Klasyfikacja każdego pliku w repo: **FRAMEWORK** (universal blast, dystrybuowany w template) vs **R&D** (mój personal R&D content) vs **HYBRID** (framework path, project-specific content).

Cel: jasność co commituję, co dystrybuuję jako template, a co zostaje moje.

## Canonical sources (OSOT)

When updating shared information, edit the canonical source — never duplicate. Catalog:

- **Top-level governance (Articles)** → `.blast/CONSTITUTION.md` — eleven Articles binding every spec/agent
- **Agent routing + debate compositions** → `.blast/steering/llm-routing.md`
- **File classification (FRAMEWORK / HYBRID / R&D)** → this file (`.blast/MANIFEST.md`)
- **Spec schema (`spec.json` fields, `phase`/`status` enums)** → `.blast/settings/templates/specs/init.json`
- **Approval / privacy / telemetry gate logic** → `.claude/hooks/blast-*.py`
- **Persona names + agent contracts** → `.claude/agents/blast/*.md` frontmatter + body
- **Pipeline phases (canonical order)** → `.blast/CLAUDE.snippet.md::Pipeline` (auto-loaded via `.claude/CLAUDE.md`; replicated to README, help; sync manually if changed)

## Drop-in guarantee (root stays clean)

blast requires **zero** required files at the repo root. Everything lives inside the `.blast/` and `.claude/` namespaces, so integrating with an existing project is literally: copy `.blast/` and `.claude/`, done.

- **AI instructions** auto-load from `.claude/CLAUDE.md` (Claude Code loads both `./CLAUDE.md` and `./.claude/CLAUDE.md` additively — your root `CLAUDE.md`, if any, is untouched).
- **Secrets** live in `.blast/.env` (the bridge reads it; legacy root `.env` still works as fallback).
- **gitignore** is nested (`.blast/.gitignore` + `.claude/.gitignore`) — git applies them additively, no root edit.
- **MCP bridge** is the only thing Claude Code can read *only* from root `.mcp.json` — and it is **optional** (local Ollama). Merge `.blast/.mcp.json.snippet` or `claude mcp add` if you want it; without it blast runs cloud-only.
- **Code search (semble)** — optional local code-search MCP (`semble`), registered the same way (`claude mcp add semble -s user -- uvx --from "semble[mcp]" semble`, or via `.blast/.mcp.json.snippet`). Agents prefer `mcp__semble__search` over grep+read (~98% fewer tokens) and fall back to grep when it is absent. Setup: `.blast/knowledge/references/semble-setup.md`.
- Anything at the repo root (e.g. `README.md`) is **informational only**.

## FRAMEWORK — universal blast (ship as-is)

Te pliki SĄ częścią blast'a. Każdy klonujący repo dostaje je 1:1.

```
.claude/commands/blast/*.md                  29 plików — slash commands
.claude/agents/blast/**/*.md                 22 plików — agents (incl. debate sub-agents: critic, critic-opus, author, judge, aggregator)
.claude/scripts/blast-*.py                   ~10 plików — init, lint, bench, telemetry, learn, graph, knowledge-index, autotune, eval, shipped-counter
.claude/hooks/blast-*.py                      3 pliki  — approval-gate, privacy-gate, telemetry
.claude/mcp/blast-llm-bridge.py               1 plik   — Ollama + Gemini providers
.claude/settings.json                                  — hooks registry, bash allowlist

.blast/CONSTITUTION.md                                 — top-level governance, 11 Articles (FRAMEWORK; ship as-is to give new projects clear governance entry-point)
.blast/settings/rules/*.md                   12 plików — EARS, design, code principles, ai-collaboration
.blast/settings/templates/specs/             6 plików  — requirements/design/tasks/research/evolution
.blast/settings/templates/steering/          5 plików  — product, tech, structure, inventory, research
.blast/settings/templates/steering/*.template 2 pliki  — cost-policy + llm-routing skeletons
.blast/settings/templates/steering-custom/   7 plików  — auth, db, deploy, etc.
.blast/settings/templates/debates/scratchpad.md       — debate scaffold

.blast/README.md                                       — explains blast structure
.blast/knowledge/README.md                             — explains knowledge base
.blast/knowledge/sota/                                 — curated SOTA recommendations per domain (FRAMEWORK; refreshed via /blast:learn --refresh-sota)
.blast/{specs,steering}/.gitkeep                       — empty dir markers (populated per project)

README.md                                              — top-level readme (informational only — no wiring needed)
.claude/CLAUDE.md                                      — auto-loaded include stub → @../.blast/CLAUDE.snippet.md
.blast/CLAUDE.snippet.md                               — framework AI instructions (single source of truth)
.blast/.env.example                                    — env vars template (incl. GEMINI_API_KEY for JURY_3_FLASH3)
.blast/.gitignore + .claude/.gitignore                 — nested, additive (no root .gitignore edit needed)
.blast/.mcp.json.snippet                               — OPTIONAL bridge entry (merge into root .mcp.json, or `claude mcp add`)
.blast/MANIFEST.md                                     — this file (framework manifest)
```

**Total**: ~100 plików.

**New project entry-points**:
- `python .claude/scripts/blast-init.py <name>` — local scaffolder (clone + cleanup + fresh git)
- `curl -sSL https://raw.githubusercontent.com/blablast/blast-spec-driven-development-framework/main/.claude/scripts/blast-init.py | python3 - <name>` — one-liner

## HYBRID — framework path, project-specific content

Te pliki LIVE w framework path bo framework je czyta, ale ich CONTENT jest moim project-specific config'iem. Przy distribution: replace z template'ami.

```
.blast/steering/llm-routing.md          — routing config (per-phase model + debate compositions)
.blast/steering/cost-policy.md          — cost caps (per-phase ceilings, calibratable)
.blast/specs/{f}/spec.json              — per-feature spec metadata (NIE istnieje w template, generuje się per project)
.blast/specs/{f}/{requirements,design,tasks,research}.md — per-feature artifacts (generuje się per project)
.blast/steering/{product,tech,structure,INVENTORY}.md   — generuje się przez /blast:steering / /blast:complete per project
```

**Distribution rule**: replace HYBRID files z template'ami z `.blast/settings/templates/steering/*.template` przed clone publication.

## R&D — moje personal content (NIE ship)

Wszystko w `.priv/` — pure project-specific content. Nigdy nie powinno trafiać do public template clone.

```
.priv/README.md                                      — explains .priv structure
.priv/INVENTORY.md                                   — snapshot stanu projektu
.priv/decisions/2026-05-05-sdd-number-one-roadmap.md — strategic plan
.priv/research/spike-1/{README,results-*.json}       — local cluster benchmark
.priv/research/spike-2/README.md                     — bridge MVP spike
.priv/research/spike-3/{snippets,driver,score,results,report}.* — multi-LLM validation
.priv/steering-snapshot/{cost-policy,llm-routing}.md — backup of my .blast/steering/
```

**Total**: ~25 files, ~3,000 lines.

## Distribution flow

Future `tools/package-blast.sh`:

1. Copy FRAMEWORK files do `dist/`
2. Replace HYBRID `.blast/steering/{cost-policy,llm-routing}.md` z templates
3. Reset `.blast/{specs,knowledge,steering}/` do `.gitkeep` only
4. Skip `.priv/` całkowicie
5. Skip `.blast/logs/`, `.blast/.session-state/`
6. Tarball `dist/` lub push do `blast-spec-driven-development-framework` public repo

Bez tego script'u — clone'owanie tego repa daje TEŻ R&D content. To znana luka, fix przez packaging script.

## How to verify (manual audit)

```bash
# Lista FRAMEWORK files (should be ~95)
find .claude/commands/blast .claude/agents/blast .claude/scripts .claude/hooks .claude/mcp \
     .blast/settings -type f \
     ! -path "*__pycache__*" | wc -l

# Lista R&D files (should be ~25)
find .priv -type f ! -path "*__pycache__*" | wc -l

# HYBRID files
ls .blast/steering/*.md
```
