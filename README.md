# blast — Spec-Driven Development for Claude Code

> **blast** = Błażej Strus' AI Development Life Cycle.
> Spec-first. Quality-enforced. No chaos.

![License](https://img.shields.io/badge/license-MIT-green)
![Built for Claude Code](https://img.shields.io/badge/built%20for-Claude%20Code-7C3AED)
![Commands](https://img.shields.io/badge/commands-30-blue)
![Agents](https://img.shields.io/badge/agents-22-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)
![Pipeline](https://img.shields.io/badge/pipeline-spec--driven-1A1D23)
[![Paper](https://img.shields.io/badge/%F0%9F%93%84-Read%20the%20paper-B31B1B)](blast_opracowanie.pdf)

## The problem

AI coding agents are fast, but raw speed without discipline is a liability. They make wrong assumptions and run with them, overcomplicate code and bloat abstractions ("1000 lines where 100 would do"), drift outside the task, and silently change code and comments they don't fully understand. The fix isn't a better model — it's a framework that communicates intent and **enforces** it.

**blast is that framework.** It forces order onto AI-assisted development: **first you know WHAT, then HOW, and only then you write code.** It ships as a set of agents and slash commands for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — generating specs, designs, and tasks, then implementing them with TDD, code review, security audit, and a behavior-preserving simplify pass.

## The pipeline

```mermaid
flowchart LR
    steering --> init --> req[requirements] --> design --> tasks --> impl --> complete --> security
    security --> steering
    req -. opt .-> research
    design -. opt .-> vd[validate-design]
    tasks -. opt .-> vt[validate-tasks]
    impl -. opt .-> vi[validate-impl]
    vi -. opt .-> simplify
    security -. opt .-> push

    classDef mand fill:#1A1D23,color:#fff,stroke:#1A1D23;
    classDef opt fill:#fff,color:#1A1D23,stroke:#7A7A7A,stroke-dasharray:4 3;
    classDef term fill:#2F8F4D,color:#fff,stroke:#2F8F4D;
    class steering,init,req,design,tasks,impl,complete mand;
    class security term;
    class research,vd,vt,vi,simplify,push opt;
```

Solid spine = mandatory phases. Dashed = optional (research, three validations, simplify, push). Each gate requires human approval unless you bypass with `-y`. `simplify` is the only step that *subtracts* complexity instead of adding it.

## Why blast?

A fair comparison against the current state of the art (May 2026):

| Capability | raw Claude Code | GitHub Spec Kit | Amazon Kiro | **blast** |
|---|:---:|:---:|:---:|:---:|
| Spec → design → tasks gates | ✗ | ✓ | ✓ | ✓ |
| Project memory (steering) | partial | ✗ | ✓ | ✓ |
| Cross-artifact validation | ✗ | ✓ `/analyze` | partial | ✓ (4 validators) |
| Cross-spec DRY (inventory) | ✗ | ✗ | ✗ | ✓ |
| Constitution / governance | ✗ | ✓ | ✗ | ✓ (11 Articles) |
| Multi-LLM debate | ✗ | ✗ | ✗ | ✓ |
| Privacy / local-only LLM | ✗ | ✗ | ✗ | ✓ |
| Event-driven hooks (on-save) | ✗ | ✗ | ✓ | ✗ |
| Behavior-preserving **simplify** | ✗ | ✗ | ✗ | ✓ |
| Hard SDK-level approval gate | ✗ | ✗ | partial (IDE) | ✓ |
| Enforcement model | — | prompt templates | IDE-integrated | agents + hooks + gates |

Honest read: Spec Kit's `/analyze` and Kiro's on-save hooks are genuinely good ideas (Kiro's event-driven hooks are something blast doesn't do — it's prompt-driven, not IDE-embedded). Where blast pulls ahead is **enforcement depth** (deterministic SDK-level gates, not just templates), **cross-spec DRY**, **multi-LLM debate + privacy mode**, and **`/blast:simplify`** — a behavior-preserving complexity-reduction step neither competitor has.

## Karpathy-aligned, and then some

blast's four core AI rules — **Think Before Coding · Simplicity First · Surgical Changes · Goal-Driven Execution** — are the same four principles the community distilled from [Andrej Karpathy's notes on LLM coding pitfalls](https://github.com/multica-ai/andrej-karpathy-skills). The difference: those ship as a single passive `CLAUDE.md` you *hope* the model follows. blast **actively enforces** them:

- **Simplicity First** → `validate-tasks` (pre-impl KISS) + `/blast:simplify` (post-impl behavior-preserving reduction)
- **Surgical Changes** → `validate-impl` + `review`, including the comment guardrail ("never delete a comment you don't understand") and the "remove only your own orphans" rule
- **Goal-Driven Execution** → TDD by default + `validate-impl --prove` (runtime proof against the design's Verification Strategy)

Full rules: [`.blast/settings/rules/ai-collaboration.md`](.blast/settings/rules/ai-collaboration.md) and [`.blast/settings/rules/code-principles.md`](.blast/settings/rules/code-principles.md).

## Key features

- Spec-driven pipeline with **hard phase guards** (requirements → design → tasks → code) enforced at the SDK level, not just prompt-level
- TDD implementation with ruff/ESLint **in the cycle**, not post-hoc
- Security audit (OWASP/CWE) built into the pipeline
- Code review with a 9-point scorecard (Clean Code, SOLID, KISS, DRY, YAGNI, patterns, SOTA, lint, docstrings)
- Behavior-preserving **`/blast:simplify`** — removes drift and over-abstraction, gated by the feature's Verification Strategy (reverts on red)
- Research/spike phase for unknown-territory features, backed by a local knowledge base
- Cross-spec DRY via a project inventory
- **Multi-LLM compositions** (opt-in): HYBRID validate-impl (Sonnet ‖ qwen3.6 → Haiku judge) and JURY_3_FLASH3 for security/high-stakes review (Opus ‖ qwen3.6 ‖ Gemini-3-Flash → Haiku aggregator)
- **Privacy mode** (`spec.json.privacy: local-only`) — all external LLM calls blocked by hook, falls back to local-only routing
- **MCP bridge for local Ollama** — qwen3.6, qwen3-coder for free local critic/coder roles

## Quick start

### 1. Scaffold a new project

**Option A — `blast init` CLI** (recommended; clones template, wipes author's specs/code, resets steering, fresh git):

```bash
curl -sSL https://raw.githubusercontent.com/blablast/claude_code-template/main/.claude/scripts/blast-init.py | python3 - my-project
cd my-project
```

**Option B — manual clone** (inherit author's R&D as reference):

```bash
gh repo clone blablast/claude_code-template my-project
cd my-project && rm -rf .git && git init
```

### 2. Initialize project memory

```bash
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
```

### 4. Shortcuts

```bash
/blast:quick "Contact form with validation" --auto          # spec only, no code
/blast:full "Payment gateway" --auto --research --push      # full pipeline + research + push
/blast:review user-auth-oauth2 --fix                        # code review
/blast:simplify user-auth-oauth2 --apply                    # cut complexity, re-verify
/blast:security --all                                       # audit entire codebase
```

### Zero-config

blast works out-of-the-box on a Claude Code subscription — **no API keys** for the basic pipeline. Multi-LLM debate, jury review, and privacy mode are opt-in via `.env` (see `.env.example`).

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
| `/blast:simplify {f} [--apply]` | Behavior-preserving code reduction after impl (report-first; `--apply` cuts + re-verifies) |
| `/blast:security {f} [--fix] [--all]` | Security audit (OWASP/CWE) |
| `/blast:complete {f}` | Ship feature → inventory + changelog |
| `/blast:push [f]` | Git commit + push (smart staging) |
| `/blast:quick "desc" [--auto] [--research]` | Spec pipeline (init → tasks) |
| `/blast:full "desc" [--auto] [--research] [--push]` | Full pipeline (init → push) |
| `/blast:status {f}` | Check progress |
| `/blast:validate-tasks {f}` | KISS + SOTA review of tasks before impl |
| `/blast:learn` | Self-improvement: aggregate lessons / cost calibrate / routing |
| `/blast:help [cmd]` | Help and reference |

**30 commands, 22 agents (18 top-level + 4 debate).** Full reference: `/blast:help` or [`.blast/README.md`](.blast/README.md).

## Governance — the Constitution

The project's binding principles live in [`.blast/CONSTITUTION.md`](.blast/CONSTITUTION.md) — eleven Articles covering spec-driven discipline, multi-LLM debate as default, tiered cost routing, privacy mode, TDD enforcement, cross-spec DRY, lifecycle, determinism boundaries, and conscious-duplicate policy. Steering files (`product.md`, `tech.md`, `structure.md`, `INVENTORY.md`) are the operational expansion of those Articles. If anything conflicts with steering, the Constitution wins for governance intent.

## Knowledge base

`.blast/knowledge/` — local knowledge the research agent searches **before** the internet:

- **`decisions/`** — architectural decisions (ADR); research respects existing decisions
- **`references/`** — API docs, library gotchas, saved articles
- **`research/`** — auto-generated summaries from previous `/blast:research` runs
- **`sota/`** — curated state-of-the-art recommendations per technology area, read by `validate-tasks` before suggesting library alternatives

## Using as a template

blast is a **reusable template** — the `.blast/` and `.claude/` directories are 100% portable. See `MANIFEST.md` for which files are FRAMEWORK (ship as-is), HYBRID (framework path, project-specific content), and R&D (personal, not for distribution).

```bash
gh repo clone blablast/claude_code-template my-new-project
cd my-new-project
rm -rf .git .blast/specs/ r_and_d/      # drop R&D content
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
