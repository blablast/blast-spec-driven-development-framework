# Technology Stack

## Stack Fingerprint (MANDATORY — keep current)

Hard fields that drive agent behavior (commands, hooks, permissions). When empty, `/blast:steering` detects/asks before proceeding.

| Field | Value | Notes |
|---|---|---|
| Language | | e.g. Python 3.12, TypeScript 5.3, Go 1.22 |
| Runtime | | e.g. CPython, Node.js 20, Bun, Deno |
| Package manager | | `pip` \| `uv` \| `poetry` \| `conda` \| `npm` \| `pnpm` \| `yarn` \| `bun` |
| Environment | | `venv` \| `uv` \| `docker` \| `conda` \| `devcontainer` \| `bare` |
| Test runner | | `pytest` \| `unittest` \| `jest` \| `vitest` \| `go test` \| other |
| Linter | | `ruff` \| `flake8` \| `pylint` \| `eslint` \| `biome` \| other |
| Formatter | | `ruff format` \| `black` \| `prettier` \| `biome` \| other |
| Type checker | | `mypy` \| `pyright` \| `tsc` \| `none` |
| Framework | | e.g. FastAPI, Django, Next.js, None |

### Canonical Commands

Commands agents use directly. Must reflect the stack above.

| Action | Command |
|---|---|
| Install deps | e.g. `uv sync` \| `pip install -e ".[dev]"` \| `npm ci` |
| Run single test | e.g. `pytest tests/<path>::<test> -v` \| `npx jest <path> -t "<name>"` |
| Run all tests | e.g. `pytest` \| `npm test` |
| Lint | e.g. `ruff check .` \| `npx eslint .` |
| Format | e.g. `ruff format .` \| `npx prettier --write .` |
| Type check | e.g. `mypy src/` \| `npx tsc --noEmit` |
| Dev server | e.g. `uvicorn src.app.main:app --reload` \| `npm run dev` |
| Smoke check | e.g. `python -c "import src.app"` \| `curl -fs localhost:8000/health` |

> Defaults recommended when bootstrapping from scratch on Python projects: **pip + venv + pytest + ruff**. Override in `/blast:steering` if the project uses something else.

---

## Architecture

[High-level system design approach]

## Core Technologies

- **Language**: [see fingerprint above]
- **Framework**: [see fingerprint above]
- **Runtime**: [see fingerprint above]

## Key Libraries

[Only major libraries that influence development patterns]

## Development Standards

### Type Safety
[e.g., TypeScript strict mode, Python mypy strict, no `any`]

### Code Quality
[Linter/formatter rules beyond defaults]

### Testing
[Coverage targets, integration vs unit split, test DB strategy]

## Key Technical Decisions

[Important architectural choices and rationale]

---

## Gotchas

<!--
Tech-specific pitfalls learned in THIS project. Added via `/blast:complete` retrospection (with near-neighbor check — refine existing entries instead of duplicating).
Format: one bullet per gotcha, lead with the rule, follow with one-line reason.
-->

_none yet_

## Incidents

<!--
Scar tissue — things that broke in prod/staging/dev and cost us time. Added manually or via `/blast:complete` retrospection.
Format: date + one-line description + one-line mitigation.
-->

_none yet_

## AI Guidance (this project)

<!--
Project-specific rules for AI collaboration that are NOT universal (those live in .blast/settings/rules/ai-collaboration.md).
Examples: "don't mock the DB in integration tests — we rely on testcontainers", "never regenerate migration files, use alembic revision --autogenerate".
-->

_none yet_

---
_Document patterns and principles, not every dependency_
