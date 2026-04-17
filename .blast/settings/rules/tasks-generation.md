# Task Generation Rules

> blast-specific rules for generating `tasks.md`. Generic engineering principles are assumed — this file captures the **formats, hierarchy, and parallel-execution conventions unique to blast**.
> Code-level principles live in `code-principles.md`; design conventions in `design-principles.md`.

## 1. Natural language, not code structure

Tasks describe the functional work — NOT file paths, function signatures, class names, or type definitions. Implementation details belong in `design.md`.

**Describe**: what capability/behavior to achieve, business logic, domain concepts, data relationships.
**Avoid**: file paths, method signatures, type/class names, specific data structures.

## 2. Task hierarchy (MANDATORY)

- **Max 2 levels**: Level 1 = major tasks (1, 2, 3…), Level 2 = sub-tasks (1.1, 1.2, 2.1…). No 1.1.1.
- If a major task has only one actionable item, collapse it and promote the sub-task to the major level.
- Major task exists purely as container → keep its description concise; put specifics in sub-tasks.
- Sequential numbering: major tasks MUST increment. Sub-tasks reset per major (1.1, 1.2, then 2.1, 2.2).

### Checkbox format

```markdown
- [ ] 1. Major task description
- [ ] 1.1 Sub-task description
  - Detail item 1
  - Detail item 2
  - _Requirements: X.X_

- [ ] 2. Next major task
- [ ] 2.1 Sub-task...
```

## 3. Requirements mapping (MANDATORY FORMAT)

Each sub-task detail block ends with:

```
_Requirements: 2.1, 3.4_
```

- **Only numeric IDs, comma-separated.**
- **No descriptive suffixes, parentheses, translations, or free-form labels** after the IDs.
- For cross-cutting requirements, list every relevant ID.
- All requirements MUST have numeric IDs in `requirements.md`. If one is missing, stop and fix `requirements.md` before generating tasks.
- Format: `N.M` where `N` is the top-level requirement number from `requirements.md`.
- Components/interfaces from `design.md` may be referenced separately, e.g. `_Contracts: AuthService API_`.

## 4. Sizing

- Sub-tasks: 1–3 hours of work each, 3–10 detail bullets.
- Major tasks: as many sub-tasks as logical cohesion demands. Don't force arbitrary counts.
- Use major task summaries sparingly — omit detail bullets when child tasks cover the work fully.

## 5. Optional test-coverage marker `- [ ]*`

When the design already guarantees functional coverage and MVP speed is prioritized, mark purely-test follow-up work as optional:

```markdown
- [ ]* 4.2 Add baseline rendering tests for PanelHeader
```

- Apply ONLY when the sub-task references acceptance criteria from `requirements.md` in its detail bullets.
- Never mark implementation or integration-critical verification as optional.

## 6. Parallel analysis — `(P)` marker

Default is parallel-analysis enabled. Disabled via `--sequential` (then omit `(P)` markers entirely).

Mark `(P)` immediately after the task number only when **all** hold:

1. No data dependency on other pending tasks.
2. No shared file or resource contention.
3. No prerequisite review/approval from another task.
4. Environment/setup already satisfied or covered within the task.
5. Operates within boundaries defined in `design.md` § Architecture Pattern & Boundary Map.
6. No overlapping API/event contracts from `design.md`.

```markdown
- [ ] 2.1 (P) Build background worker for emails
```

- Apply to both major and sub-tasks when appropriate.
- Group parallel tasks under the same parent when theme matches.
- Call out dependencies that prevent `(P)` even when tasks look similar.
- Skip `(P)` on container-only major tasks — evaluate parallelism at the sub-task level.
- Keep `(P)` **outside** checkbox brackets.

## 7. Code-only focus

**Include**: coding, testing (unit/integration/E2E), technical setup (infra, config).
**Exclude**: deployment, documentation, user testing, marketing/business activities.

## 8. Requirements coverage (MANDATORY CHECK)

- Every requirement ID from `requirements.md` MUST appear in at least one task.
- If gaps found → return to requirements or design phase.
- Document any intentionally deferred requirements with rationale.
- Tasks must respect architecture boundaries defined in `design.md`.
- Tasks must honor interface contracts from `design.md`.
