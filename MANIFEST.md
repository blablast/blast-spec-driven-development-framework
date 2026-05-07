# blast Distribution Manifest

Klasyfikacja każdego pliku w repo: **FRAMEWORK** (universal blast, dystrybuowany w template) vs **R&D** (mój personal R&D content) vs **HYBRID** (framework path, project-specific content).

Cel: jasność co commituję, co dystrybuuję jako template, a co zostaje moje.

## Canonical sources (OSOT)

When updating shared information, edit the canonical source — never duplicate. Catalog:

- **Agent routing + debate compositions** → `.blast/steering/llm-routing.md`
- **File classification (FRAMEWORK / HYBRID / R&D)** → this file (`MANIFEST.md`)
- **Spec schema (`spec.json` fields, `phase`/`status` enums)** → `.blast/settings/templates/specs/init.json`
- **Approval / privacy / telemetry gate logic** → `.claude/hooks/blast-*.py`
- **Persona names + agent contracts** → `.claude/agents/blast/*.md` frontmatter + body
- **Pipeline phases (canonical order)** → `CLAUDE.md::Pipeline` (replicated to README, help; sync manually if changed)

## FRAMEWORK — universal blast (ship as-is)

Te pliki SĄ częścią blast'a. Każdy klonujący repo dostaje je 1:1.

```
.claude/commands/blast/*.md                  29 plików — slash commands
.claude/agents/blast/**/*.md                 21 plików — agents (incl. debate sub-agents)
.claude/scripts/blast-*.py                    3 pliki  — lint, bench, telemetry
.claude/hooks/blast-*.py                      3 pliki  — approval-gate, privacy-gate, telemetry
.claude/mcp/blast-llm-bridge.py               1 plik
.claude/settings.json                                  — hooks registry, bash allowlist

.blast/settings/rules/*.md                   12 plików — EARS, design, code principles
.blast/settings/templates/specs/             6 plików  — requirements/design/tasks/research/evolution
.blast/settings/templates/steering/          5 plików  — product, tech, structure, inventory, research
.blast/settings/templates/steering/*.template 2 pliki  — cost-policy + llm-routing skeletons
.blast/settings/templates/steering-custom/   7 plików  — auth, db, deploy, etc.
.blast/settings/templates/debates/scratchpad.md       — debate scaffold

.blast/README.md                                       — explains blast structure
.blast/knowledge/README.md                             — explains knowledge base
.blast/{knowledge,specs,steering}/.gitkeep             — empty dir markers (recreated per project)

README.md                                              — top-level readme + Setup
CLAUDE.md                                              — AI instructions (template version)
.env.example                                           — env vars template
.gitignore
.mcp.json                                              — MCP bridge registration
MANIFEST.md                                            — this file
```

**Total**: ~95 plików, ~13,000 linii.

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

Wszystko w `r_and_d/` — pure project-specific content. Nigdy nie powinno trafiać do public template clone.

```
r_and_d/README.md                                      — explains r_and_d structure
r_and_d/INVENTORY.md                                   — snapshot stanu projektu
r_and_d/decisions/2026-05-05-sdd-number-one-roadmap.md — strategic plan
r_and_d/research/spike-1/{README,results-*.json}       — local cluster benchmark
r_and_d/research/spike-2/README.md                     — bridge MVP spike
r_and_d/research/spike-3/{snippets,driver,score,results,report}.* — multi-LLM validation
r_and_d/steering-snapshot/{cost-policy,llm-routing}.md — backup of my .blast/steering/
```

**Total**: ~25 files, ~3,000 lines.

## Distribution flow

Future `tools/package-blast.sh`:

1. Copy FRAMEWORK files do `dist/`
2. Replace HYBRID `.blast/steering/{cost-policy,llm-routing}.md` z templates
3. Reset `.blast/{specs,knowledge,steering}/` do `.gitkeep` only
4. Skip `r_and_d/` całkowicie
5. Skip `.blast/logs/`, `.blast/.session-state/`
6. Tarball `dist/` lub push do `claude_code-template` public repo

Bez tego script'u — clone'owanie tego repa daje TEŻ R&D content. To znana luka, fix przez packaging script.

## How to verify (manual audit)

```bash
# Lista FRAMEWORK files (should be ~95)
find .claude/commands/blast .claude/agents/blast .claude/scripts .claude/hooks .claude/mcp \
     .blast/settings -type f \
     ! -path "*__pycache__*" | wc -l

# Lista R&D files (should be ~25)
find r_and_d -type f ! -path "*__pycache__*" | wc -l

# HYBRID files
ls .blast/steering/*.md
```
