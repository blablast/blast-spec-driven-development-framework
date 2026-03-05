# Quality Gates — Automated Pre-Flight Checks

Quality gates run automatically before phase transitions. They don't block (user can override), but they clearly flag issues.

## Gate 1: Requirements → Design

**Trigger**: Before `/blast:design` generates design.md

**Checks**:
1. **Numeric IDs**: All requirements have numeric IDs (no "Requirement A")
2. **EARS format**: Each acceptance criterion uses EARS syntax (When/While/Where/If/shall)
3. **Completeness**: At least 3 requirements defined (warning if fewer)
4. **No implementation details**: Requirements describe WHAT, not HOW (flag technical terms like "use React", "implement with SQL")
5. **Testability**: Each requirement has at least one measurable acceptance criterion

**Output**: Pass/Warn/Fail per check. Fail blocks only if numeric IDs missing.

## Gate 2: Design → Tasks

**Trigger**: Before `/blast:tasks` generates tasks.md

**Checks**:
1. **Requirements traceability**: Every requirement ID from requirements.md appears in design.md
2. **Component interfaces defined**: Each component has input/output types documented
3. **No orphan components**: Every component traces back to at least one requirement
4. **Error handling**: Design addresses error scenarios (at least one error flow documented)
5. **Code principles alignment**: Design doesn't violate SOLID/KISS/YAGNI (flag god-components with >5 responsibilities, over-abstracted layers, speculative features)

**Output**: Pass/Warn per check. No hard blocks — warnings only.

## Gate 3: Tasks → Implementation

**Trigger**: Before `/blast:impl` starts coding

**Checks**:
1. **Task-requirement mapping**: Every task references at least one requirement ID
2. **Test tasks present**: At least one task explicitly mentions testing
3. **Task sizing**: Flag tasks with descriptions suggesting >4 hours of work
4. **No orphan tasks**: Every major task has at least one sub-task
5. **Dependency order**: Tasks with dependencies listed after their prerequisites

**Output**: Pass/Warn per check.

## Gate 4: Implementation → Complete

**Trigger**: Before `/blast:complete` marks feature as shipped

**Checks**:
1. **All tasks done**: Every task in tasks.md is `[x]` (fail if any `[ ]`)
2. **Design→code match**: Components from design.md exist in codebase (Grep for class/function names)
3. **Test existence**: Test files exist for components listed in design.md
4. **No TODO/FIXME**: Grep codebase for TODO/FIXME/HACK in files modified by this feature
5. **`provides` accuracy**: Components in `provides` array actually exist in codebase
6. **Requirements→deliverables match**: Every file, document, and artifact explicitly named in requirements.md exists on disk. Grep for named files (README.md, etc.), verify quantitative thresholds (≥N tests, ≥N items), confirm documentation artifacts are non-trivial (>20 lines)
7. **Smoke test**: Entry point runs without import/startup errors (see impl.md Step 4a for tech-specific commands)

**Output**: Pass/Warn/Fail. Fail on #1 (incomplete tasks), #6 (missing deliverables), #7 (app doesn't start). Rest are warnings.

## Reporting Format

```
## Quality Gate: {gate-name}
| Check | Status | Details |
|-------|--------|---------|
| Numeric IDs | ✅ Pass | All 8 requirements have numeric IDs |
| EARS format | ⚠️ Warn | Req 3.2 missing EARS keyword |
| Completeness | ✅ Pass | 8 requirements defined |

**Result**: PASS (1 warning)
→ Proceeding to next phase.
```

## Override Protocol

User can override any warning with explicit confirmation. Fails require either:
- Fixing the issue, or
- Explicit "skip gate" confirmation with documented reason
