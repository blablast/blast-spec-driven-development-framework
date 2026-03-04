# blast — Spec-Driven Development for Claude Code

> **blast** = Błażej Strus' AI Development Life Cycle.
> Spec-first. Quality-enforced. No chaos.

## What is blast?

blast is a framework for AI-assisted development that enforces order: **first you know WHAT, then HOW, and only then you write code**. It works as a set of agents and slash commands for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — generating specs, designs, and tasks, then implementing them with TDD.

**Key features:**
- Spec-driven pipeline with phase guards (requirements → design → tasks → code)
- TDD implementation with ruff/ESLint in the cycle, not post-hoc
- Security audit (OWASP/CWE) built into the pipeline
- Code review with 9-point scorecard (Clean Code, SOLID, KISS, DRY, YAGNI...)
- Test coverage tracking (≥80% target) as a soft gate
- Research/spike phase for unknown-territory features
- Cross-spec DRY via project inventory
- Auto-changelog on feature completion
- Git push with smart staging and descriptive English commits

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
| `/blast:help [cmd]` | Help and reference |

**20 commands, 14 agents.** Full docs: `.blast/README.md`

## Pipeline

```
steering ──► init ──► requirements ──► [research] ──► design ──► tasks
                                                                   │
push ◄── steering ◄── security ◄── complete ◄── impl ◄────────────┘
                        (OWASP)      (changelog    (TDD + ruff
                                      + coverage)   + coverage)
```

**`/blast:full`** runs all phases automatically. Security blocks on critical findings.

## Knowledge Base

`.blast/knowledge/` — local knowledge that research agent searches BEFORE the internet.

- **`decisions/`** — architectural decisions (ADR). Research respects existing decisions.
- **`references/`** — API docs, library gotchas, saved articles. Drop anything useful here.
- **`research/`** — auto-generated summaries from previous `/blast:research` runs.

Research agent reads knowledge base first, skips web search when local sources answer the question, and writes back reusable findings after each research.

## Code Principles

blast enforces on every phase: Clean Code, SOLID, KISS, DRY, YAGNI, appropriate design patterns, no overengineering, SOTA solutions, PEP 8 / ruff (Python), ESLint / Prettier (JS/TS), Google-style docstrings.

Full rules: `.blast/settings/rules/code-principles.md`

## Using as Template

blast is designed as a **reusable template** — the `.blast/` and `.claude/` directories are 100% portable. Clone, delete `.git`, init your own repo, and start building.

```bash
gh repo clone blablast/claude_code-template my-new-project
cd my-new-project
rm -rf .git .blast/steering/ .blast/specs/ .blast/knowledge/research/ .blast/knowledge/decisions/
git init && git add -A && git commit -m "Initial commit from blast template"
```

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (CLI)
- Python 3.10+ or Node.js 18+ (depending on your project)

## License

MIT

---

*blast by Błażej Strus — bo programowanie powinno mieć flow, nie chaos.*
