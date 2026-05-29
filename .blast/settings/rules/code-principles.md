# Code Principles — blast Development Standards

> Project-specific coding rules enforced across blast phases. Generic CS knowledge (what SOLID/KISS/DRY mean) is assumed — this file only records the **blast-specific thresholds, formats, and tool choices**.
> Referenced by: `design-principles.md`, `tasks-generation.md`, agents `impl`, `review`, `complete`.

## 1. Clean Code — blast thresholds

- Functions >20 lines → warning, refactor target
- Nesting >3 levels → refactor to early returns or extract
- Magic numbers/strings → named constants
- Dead code → delete (VCS remembers)

## 2. Documentation — Google-style docstrings (MANDATORY)

Every public function, class, and method MUST have a docstring in **Google style** (not NumPy, not Sphinx):

```python
def calculate_fee(amount: float, rate: float = 0.05) -> float:
    """Calculate transaction fee based on amount and rate.

    Args:
        amount: Transaction amount in base currency.
        rate: Fee rate as decimal. Defaults to 0.05.

    Returns:
        Calculated fee rounded to 2 decimal places.

    Raises:
        ValueError: If amount is negative.
    """
```

- Sections: `Args`, `Returns`, `Raises`, `Yields`, `Examples`, `Note`, `Attributes`
- First line: imperative mood, one sentence
- Classes: include `Attributes` section for public attrs
- Private functions: docstring optional (recommended for complex logic)
- Enforced by ruff rule `D` (pydocstyle)

## 3. SOLID / KISS / DRY / YAGNI / Patterns / SOTA — apply standard definitions

Standard software engineering principles apply. Specific blast enforcements:

- **DRY**: Rule of Three — duplicate twice, abstract on the third occurrence. Premature abstraction is worse than duplication.
- **YAGNI**: Features must trace to a requirement in the current spec. "Might need this someday" = don't build.
- **Patterns**: Never add a pattern just because you know it. If the pattern adds more code than it removes complexity → red flag.
- **No overengineering**: Abstract base class with one implementation, config system for static values, Factory for a single type, Observer for a single listener → all red flags.
- **SOTA**: Stdlib/framework defaults first → established library (>2y, active) second → newer alternatives last, with documented risk in `research.md`.

## 4. Linting & Formatting — automated quality

### Python: ruff (default)

- `ruff` replaces flake8 / isort / black — fast, opinionated
- Run `ruff check .` after every impl step — **zero violations allowed**
- Run `ruff format .` before commit
- Enforced rule groups:
  - `E` / `W` — PEP 8
  - `F` — pyflakes (unused imports, undefined names)
  - `I` — isort
  - `N` — pep8-naming
  - `UP` — pyupgrade (modern Python idioms)
  - `B` — flake8-bugbear
  - `D` — pydocstyle (Google-style docstrings)
  - `SIM` — flake8-simplify
  - `C4` — flake8-comprehensions
- If project has `pyproject.toml` / `ruff.toml` → respect project config

### JavaScript / TypeScript: ESLint + Prettier

- Respect project `.eslintrc` and `.prettierrc`
- `npx eslint .` and `npx prettier --check .` after impl

### Universal rules

- **Zero-warnings policy**: treat warnings as errors during implementation
- **Auto-fix first**: `ruff check --fix .` / `eslint --fix .` before manual fixes
- **Don't disable rules inline** unless absolutely necessary — always explain why in a comment
- **CI parity**: local linting must match CI

## 5. Traceability lives in the spec, NEVER in code (MANDATORY)

- Code MUST NOT carry requirement-traceability tags. No `# Req: 2.1`, `# Requirement 3`,
  `# satisfies R4`, `// [Req N]`, or equivalent — in comments, docstrings, or test names.
- Traceability is the job of `tasks.md` (`_Requirements: N.M_`) and `spec.json`. The spec↔code
  link is reconstructed by `validate-impl` and `simplify` via the spec mapping, by Grepping for
  the *behavior/symbol*, not by reading Req tags planted in the source.
- Comments explain **why** a non-obvious decision was made — not which spec line mandated it.
- `validate-impl` traceability check: map requirement → file/symbol/test via design.md + tasks.md,
  do NOT instruct the model to grep code for `Req` markers (that incentivizes planting them).
- Rationale: Req tags are write-only noise that rot the moment requirements renumber; they make
  code read like a compliance form, not senior engineering.

## 6. Testing alignment

- TDD is the default (see agent `impl`), but the unit of testing is **observable behavior**, not
  every private function or line. One test that pins a real contract beats three that pin internals.
- **Coverage is a 