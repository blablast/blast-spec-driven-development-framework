# Gap Analysis Process

> Used by `/blast:validate-gap` to produce a Requirement-to-Asset map, implementation options, and effort/risk estimates before the design phase.

## Objective

Analyze the gap between `requirements.md` and the existing codebase. Output is **information + options**, not final decisions.

## Analysis Steps

### 1. Current State Investigation

- Key files/modules and directory layout relevant to the feature domain.
- Reusable components / services / utilities.
- Dominant architecture patterns and constraints.
- Conventions: naming, layering, dependency direction, import/export patterns, test placement.
- Integration surfaces: data models/schemas, API clients, auth mechanisms.

### 2. Requirements Feasibility

From EARS requirements, list technical needs:
- Data models, APIs/services, UI/components.
- Business rules / validation.
- Non-functionals: security, performance, scalability, reliability.

Identify and **tag**:
- **Missing** — capability absent from current codebase.
- **Unknown** — needs research later (mark "Research Needed", defer to design phase).
- **Constraint** — limitation from existing architecture.

Note complexity signal: simple CRUD / algorithmic / workflow / external integration.

### 3. Implementation Approach Options

Present ALL viable options with short rationale and trade-offs. Do NOT pick the final approach — that's design phase.

#### Option A — Extend Existing Components

- **When**: feature fits naturally into existing structure.
- **Assess**: which files/modules to modify, backward compatibility, test coverage impact, single responsibility maintained.
- **Trade-offs**: ✅ fewer new files, leverages existing patterns; ❌ risk of bloating existing components, may complicate existing logic.

#### Option B — Create New Components

- **When**: feature has distinct responsibility or existing components are already complex.
- **Assess**: rationale for new boundary, integration points, responsibility boundaries.
- **Trade-offs**: ✅ clean separation, easier to test, reduces complexity in existing components; ❌ more files, needs careful interface design.

#### Option C — Hybrid

- **When**: complex features requiring both extension and new creation.
- **Assess**: which parts extend vs which warrant new, phased implementation, risk mitigation (feature flags, rollback).
- **Trade-offs**: ✅ balanced, iterative; ❌ more planning, potential inconsistency.

### 4. Effort & Risk

- **Effort**:
  - **S** (1–3 days) — existing patterns, minimal deps, straightforward integration.
  - **M** (3–7 days) — some new patterns, moderate complexity.
  - **L** (1–2 weeks) — significant functionality, multiple integrations.
  - **XL** (2+ weeks) — architectural changes, unfamiliar tech, broad impact.
- **Risk**:
  - **High** — unknown tech, complex integrations, architectural shifts, unclear perf/security path.
  - **Medium** — new patterns with guidance, manageable integrations.
  - **Low** — extend established patterns, familiar tech, clear scope.

Justify each label in one line.

### 5. Out of scope for this phase

- Deep research activities (defer to design / `/blast:research`).
- Final technology selection.
- Architecture pattern decisions.

Record unknowns as concise "Research Needed" items.

## Output Checklist

- [ ] Requirement-to-Asset map with gaps tagged (Missing / Unknown / Constraint).
- [ ] Options A/B/C with rationale and trade-offs.
- [ ] Effort (S/M/L/XL) and Risk (High/Medium/Low) with one-line justification each.
- [ ] Recommendations for design phase: preferred approach + research items to carry forward.
