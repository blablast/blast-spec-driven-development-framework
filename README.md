# blast — Spec-Driven Development for Claude Code

> **blast** = Błażej Strus' AI Development Life Cycle.
> Spec-first. Quality-enforced. No chaos.

## What is blast?

blast is a framework for AI-assisted development that enforces order: **first you know WHAT, then HOW, and only then you write code**. It works as a set of agents and slash commands for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — generating specs, designs, and tasks, then implementing them with TDD.

**Key features:**
- Spec-driven pipeline with phase guards (requirements → design → tasks → code)
- TDD implementation with ruff/ESLint in the cycle, not post-hoc
- Security audit (OWASP/CWE) built into the pipeline
- Code review with 9-point scorecard (Clean Code, SOLID, KISS, DRY, YAGNI, patterns, SOTA, lint, docstrings)
- Test coverage tracking (≥80% target) as a soft gate
- Research/spike phase for unknown-territory features
- Cross-spec DRY via project inventory
- Auto-changelog on feature completion
- Git push with smart staging and descriptive English commits
- **Multi-LLM compositions** (opt-in): HYBRID validate-impl (Sonnet ‖ qwen3.6 → Haiku judge) and JURY_3_FLASH3 for security/high-stakes review (Opus ‖ qwen3.6 ‖ Gemini-3-Flash → Haiku aggregator)
- **MCP bridge for local Ollama** (`.claude/mcp/blast-llm-bridge.py`) — qwen3.6, qwen3-coder for free local critic/coder roles
- **Privacy mode** (`spec.json.privacy: local-only`) — all external LLM calls blocked by hook, falls back to local-only routing
- **Hard approval gate** via Claude Code hooks — deterministic phase-by-phase enforcement

## Setup

### Zero-config (default)

blast works out-of-the-box via Claude Code subscription — **no API keys needed** for the basic pipeline (init → requirements → design → tasks → impl → review → security solo).

### Multi-LLM mode (optional)

To enable HYBRID validate-impl, JURY_3_FLASH3 for security/validate-design, or privacy mode:

```bash
cp .env.example .env
# Fill in keys you want (GEMINI_API_KEY for jury; BLAST_OLLAMA_UBUNTU for local Qwen)
set -a; source .env; set +a
```

Full quick reference in `.env.example`. Local Ollama setup: `.blast/knowledge/references/multi-llm-setup.md`.

### Verification after setup

```
/blast:ping-llm      # smoke test MCP bridge (local models)
/blast:help          # full command list + setup details
/blast:status        # status of existing specs
```

## Quick Start

### 1. Clone the template

```bash
gh repo clone blablast/claude_code-template my-project
cd my-project
rm -rf .git && git init
```

### 2. Initialize project memory

```bash
# In Claude Code terminal:
/blast:steering
```

### 3. Build a feature

```bash
# Full pipeline — from description to shipped code
/blast:full "User authentication with OAuth2" --auto

# Or step by step:
/blast:init "User authentication with OAuth2"
/blast:requirements user-auth-oauth2
/blast:design user-auth-oauth2
/blast:tasks user-auth-oauth2
/blast:impl user-auth-oauth2
/blast:complete user-auth-oauth2
/blast:security user-auth-oauth2
/blast:steering
```

### 4. Shortcuts

```bash
# Spec only (no implementation)
/blast:quick "Contact form with validation" --auto

# Full pipeline with research phase and git push
/blast:full "Payment gateway integration" --auto --research --push

# Code review
/blast:review user-auth-oauth2 --fix

# Security audit on entire codebase
/blast:security --all
```

## Commands

| Command | Description |
|---|---|
| `/blast:steering` | Initialize/sync project memory |
| `/blast:init "desc" [--source file]` | Create new feature spec |
| `/blast:requirements {f}` | Generate EARS requirements |
| `/blast:research {f} [--deep]` | Spike/research — compare options |
| `/blast:design {f} [-y]` | Generate technical design |
| `/blast:tasks {f} [-y]` | Generate implementation plan |
| `/blast:impl {f} [tasks]` | Implement with TDD + ruff + coverage |
| `/blast:review {f} [--fix]` | Code review vs principles |
| `/blast:security {f} [--fix] [--all]` | Security audit (OWASP/CWE) |
| `/blast:complete {f}` | Ship feature → inventory + changelog |
| `/blast:push [f]` | Git commit + push (smart staging) |
| `/blast:quick "desc" [--auto] [--research]` | Spec pipeline (init → tasks) |
| `/blast:full "desc" [--auto] [--research] [--push]` | Full pipeline (init → push) |
| `/blast:status {f}` | Check progress |
| `/blast:validate-tasks {f}` | KISS + SOTA review of tasks before impl phase |
| `/blast:learn` | Self-improvement: aggregate lessons / cost calibrate / routing observability |
| `/blast:help [cmd]` | Help and reference |

**29 commands, 21 agents (17 top-level + 4 debate).** Full docs: `.blast/README.md`

## Pipeline

```
steering → init → requirements → [research] → design → [validate-design] → tasks → [validate-tasks] → impl → [validate-impl] → complete → security → steering [→ push]
```

**`/blast:full`** runs all phases automatically. Security blocks on critical findings. Optional validations (`validate-gap`, `validate-design`, `validate-tasks`, `validate-impl`) opt-in via `--validate` flag.

Detailed phase-by-phase breakdown: `/blast:help` (quick reference) or `.blast/README.md` (Polish dev guide).

## Knowledge Base

`.blast/knowledge/` — local knowledge that research agent searches BEFORE the internet.

- **`decisions/`** — architectural decisions (ADR). Research respects existing decisions.
- **`references/`** — API docs, library gotchas, saved articles. Drop anything useful here.
- **`research/`** — auto-generated summaries from previous `/blast:research` runs.
- **`sota/`** — curated state-of-the-art recommendations per technology area (HTTP clients, async patterns, etc.). Read by `validate-tasks` agent before suggesting library alternatives. Refresh staleness audit: `python .claude/scripts/blast-learn.py --refresh-sota`.

Research agent reads knowledge base first, skips web search when local sources answer the question, and writes back reusable findings after each research.

## Code Principles

blast enforces on every phase: Clean Code, SOLID, KISS, DRY, YAGNI, appropriate design patterns, no overengineering, SOTA solutions, PEP 8 / ruff (Python), ESLint / Prettier (JS/TS), Google-style docstrings.

Full rules: `.blast/settings/rules/code-principles.md`

## Using as Template

blast is designed as a **reusable template** — the `.blast/` and `.claude/` directories are 100% portable. See `MANIFEST.md` for the full classification of which files are FRAMEWORK (universal blast, ship as-is), HYBRID (framework path, project-specific content), and R&D (personal content, NOT for distribution).

Clone, delete `.git`, remove R&D, init your own repo:

```bash
gh repo clone blablast/claude_code-template my-new-project
cd my-new-project
rm -rf .git .blast/specs/ r_and_d/      # remove R&D content (spikes/decisions/INVENTORY snapshot)
# Optional: replace HYBRID config with skeletons:
cp .blast/settings/templates/steering/llm-routing.md.template .blast/steering/llm-routing.md
cp .blast/settings/templates/steering/cost-policy.md.template .blast/steering/cost-policy.md
git init && git add -A && git commit -m "Initial commit from blast template"
```

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (CLI)
- Python 3.10+ or Node.js 18+ (depending on your project)

## License

MIT

---

*blast by Błażej Strus — bo programowanie powinno mieć flow, nie chaos.*
