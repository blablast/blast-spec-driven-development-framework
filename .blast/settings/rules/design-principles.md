# Design Document Rules

> blast-specific conventions for `design.md`. Generic design advice (SRP, loose coupling, fail-fast, declarative language) is assumed — this file only captures the **formats, thresholds, and document structures unique to blast**.
> Code-level principles live in `code-principles.md`.

## Document Scope

- **WHAT, not HOW**: interfaces and contracts, not code.
- **Self-contained for reviewers**: `design.md` must stand alone. Reference `research.md` for background, but restate conclusions here.
- **Match detail to complexity**: extra sections only when they prevent implementation errors.
- **No `any` in TypeScript** interfaces. Explicit types, generic constraints, discriminated unions for errors.

## Section Ordering & Structure

Default flow: **Overview → Goals/Non-Goals → Requirements Traceability → Architecture → Technology Stack → System Flows → Components & Interfaces → Data Models → Optional**.

Within each section: **Summary → Scope → Decisions → Impacts/Risks**.

Reordering is allowed when it improves clarity (e.g. Traceability earlier). Keep the headings intact.

## Requirement IDs (MANDATORY FORMAT)

- Reference requirements as `2.1, 2.3` — **no prefixes** ("Requirement 2.1" is wrong).
- All requirements MUST have numeric IDs. If any requirement lacks one, stop and fix `requirements.md` before continuing.
- Format: `N.M` where `N` is the top-level requirement number from `requirements.md` (Requirement 1 → 1.1, 1.2; Requirement 2 → 2.1, 2.2).
- Every component, task, and traceability row must use the same canonical numeric ID.

## Technology Stack section

- Include ONLY layers impacted by this feature (frontend, backend, data, messaging, infra).
- Per layer: tool/library + version + role. Push rationale, comparisons, benchmarks to `research.md`.
- When extending an existing system, highlight deviations from the current stack and list new dependencies.

## Components & Interfaces

- Start with a summary table: **Component | Domain | Intent | Req coverage | Key deps (P0/P1) | Contracts**.
- Dependencies table marks each entry Inbound/Outbound/External and assigns Criticality: `P0` blocking, `P1` high-risk, `P2` informational.
- **Contracts checkbox**: Service [ ] / API [ ] / Event [ ] / Batch [ ] / State [ ]. Only the ticked types should appear in the per-component block.
- Service interfaces must declare method signatures, inputs/outputs, and error envelopes. API/Event/Batch need schema tables covering trigger, payload, delivery, idempotency.

### Detail density rules

- **Full block** — components introducing new boundaries (logic hooks, shared services, external integrations, data layers).
- **Summary-only** — presentational/UI components with no new boundaries (summary row + short Implementation Note if needed).
- Implementation Notes combine Integration / Validation / Risks into one bulleted subsection.
- Prefer lists/inline descriptors for short data. Use tables only when comparing multiple items.

### Shared interfaces

- Define a base interface (e.g. `BaseUIPanelProps`) for recurring UI components. Per-component blocks extend with deltas only.
- When reusing a base contract, reference it ("Extends `BaseUIPanelProps` with `onSubmitAnswer` callback") instead of duplicating the code block.
- Hooks, utilities, and integration adapters with new contracts still need full signatures.

## Requirements Traceability

- Use the table **Requirement | Summary | Components | Interfaces | Flows** for complex/compliance-sensitive features.
- Collapse to bullets when a requirement maps 1:1 to a component.
- Re-run the mapping whenever requirements or components change.

## Data Models

- Domain Model: aggregates, entities, value objects, domain events, invariants. Mermaid diagram only when relationships are non-trivial.
- Logical Model: structure, indexing, sharding, storage-specific considerations relevant to the change.
- Data Contracts: API payloads, event schemas, cross-service sync — only when the feature crosses boundaries.
- Lengthy type definitions or vendor option matrices → **Supporting References** section within `design.md` (linked from the relevant place). Investigation notes stay in `research.md`.

## Mermaid diagrams — strict mode

Pure Mermaid only. No styling.

- **Node IDs**: alphanumeric + underscore only. Do not use `@`, `/`, or leading `-`.
- **Labels**: simple words. Forbidden in labels: `()`, `[]`, `""`, `/`.
  - ❌ `DnD[@dnd-kit/core]` — invalid ID (`@`).
  - ❌ `UI[KanbanBoard(React)]` — invalid label (`()`).
  - ✅ `DndKit[dnd-kit core]` — technology detail in accompanying prose.
- Mermaid strict-mode otherwise fails with `Expecting 'SQE' ... got 'PS'`. Remove punctuation from labels before rendering.
- Subgraphs OK for clustering, use sparingly.

## When to include a diagram

- **Architecture**: 3+ components or external systems interact.
- **Sequence**: multi-step handshakes between parties.
- **State / Flow**: complex state machines or business flows.
- **ER**: non-trivial data models.
- Skip for single-component changes.

## Deduplication

- Do not restate diagram content verbatim in prose. Text should highlight decisions, trade-offs, or impacts not obvious from the diagram.
- Avoid repeating information across Overview, Architecture, and Components — reference earlier sections.
- If a requirement/component relationship is in the summary table, do not rewrite it elsewhere unless new nuance is added.
- **Error/Testing/Security/Performance sections** record only feature-specific decisions or deviations. Link steering for baseline practices instead of restating them.

## Design Completeness Checklist

- [ ] All requirements addressed (numeric IDs match requirements.md)
- [ ] No implementation details leaked
- [ ] Clear component boundaries with Criticality labels
- [ ] Error scenarios explicit
- [ ] Testing strategy present
- [ ] Security considered (for auth / PII / integrations)
- [ ] Performance targets defined (if applicable)
- [ ] Migration path clear (if applicable)
- [ ] Verification Strategy present (see `design.md` template)

## Code Principles Integration

Designs must align with `code-principles.md`. Specifically:

- Component boundaries reflect SRP; interfaces follow ISP; dependencies flow per DIP.
- Every abstraction layer must be justified — KISS/YAGNI.
- Patterns only when they solve a recognized problem and reduce complexity.
- Technology choices favor current ecosystem standards; document rationale in `research.md`.
