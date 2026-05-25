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

## 5. Testing alignment

- TDD is the default (see agent `impl`)
- Every principle above must be testable — if you can't test it, you've overcomplicated it
- Tests are documentation: they show intended behavior

## Review Checklist

Used by agent `review` to score principles. Answer yes/no per question:

- [ ] Does it do one thing well? (SRP, KISS)
- [ ] Is there duplication that should be extracted? (DRY — with Rule of Three)
- [ ] Is there abstraction that isn't needed yet? (YAGNI)
- [ ] Can I understand it without the author explaining? (Clean Code)
- [ ] Are dependencies injected, not hardcoded? (DIP)
- [ ] Is the pattern justified by a real problem? (No overengineering)
- [ ] Are we using current best practices? (SOTA)
- [ ] Does linter pass with zero violations? (Linting)
- [ ] Is formatting consistent and automated? (Formatting)
- [ ] Do all public symbols have Google-style docstrings? (Documentation)
- [ ] Are comments and code that weren't fully understood left untouched? (Surgical Changes — no silent deletion of comments/logic whose intent is unclear)
- [ ] Were only *your* orphans removed, with pre-existing dead code merely flagged, not deleted? (Surgical Changes)
