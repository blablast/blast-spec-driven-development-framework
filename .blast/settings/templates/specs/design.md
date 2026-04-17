# Design Document Template

> Approaching 1000 lines indicates excessive feature complexity — simplify. Sections may be reordered when it improves clarity; keep the flow **Summary → Scope → Decisions → Impacts/Risks** within each. Match detail to feature complexity; omit optional sections unless critical.

## Overview

2–3 paragraphs max.

- **Purpose**: this feature delivers [specific value] to [target users].
- **Users**: [target user groups] use this for [specific workflows].
- **Impact** (if applicable): changes current [system state] by [specific modifications].

### Goals
- Primary objective 1
- Primary objective 2
- Success criteria

### Non-Goals
- Explicitly excluded functionality
- Integration points deferred

## Architecture

> Keep `design.md` self-contained for reviewers. Reference `research.md` for background only; restate decisions here. Capture key decisions in prose; let diagrams carry structure — no verbatim restatement.

### Existing Architecture Analysis (if modifying)
- Current patterns and constraints to respect
- Existing domain boundaries
- Integration points to maintain
- Technical debt addressed or worked around

### Architecture Pattern & Boundary Map

Include a Mermaid diagram for complex features (optional for simple additions).

- Selected pattern + brief rationale
- Domain/feature boundaries (how responsibilities separate to avoid conflicts)
- Existing patterns preserved
- New components rationale
- Steering compliance

### Technology Stack

Include ONLY layers impacted by this feature.

| Layer | Choice / Version | Role in Feature | Notes |
|-------|------------------|-----------------|-------|
| Frontend / CLI | | | |
| Backend / Services | | | |
| Data / Storage | | | |
| Messaging / Events | | | |
| Infrastructure / Runtime | | | |

> Keep rationale concise; push trade-offs/benchmarks to `research.md` with a one-line pointer here.

## System Flows

Diagrams only when they clarify behavior:
- **Sequence** — multi-step interactions
- **Process/State** — branching rules or lifecycle
- **Data/Event** — pipelines or async patterns

Pure Mermaid, strict-mode compatible (no `@`/`/` in IDs, no `()`/`[]`/`""`/`/` in labels — see `design-principles.md`). Omit this section entirely for simple CRUD.

## Requirements Traceability

Use for complex or compliance-sensitive features. For 1:1 requirement-to-component mappings, rely on the Components summary table instead.

Reference requirement IDs as `2.1, 2.3` (no prefix).

| Requirement | Summary | Components | Interfaces | Flows |
|-------------|---------|------------|------------|-------|
| 1.1 | | | | |
| 1.2 | | | | |

## Components and Interfaces

Start with a quick-reference summary. Full detail blocks only for components introducing new boundaries (logic hooks, shared services, external integrations, data layers). Presentation/UI components with no new boundaries use summary row + short Implementation Note.

| Component | Domain/Layer | Intent | Req Coverage | Key Dependencies (P0/P1) | Contracts |
|-----------|--------------|--------|--------------|--------------------------|-----------|
| ExampleComponent | UI | Displays XYZ | 1.1, 1.2 | GameProvider (P0), MapPanel (P1) | Service, State |

Group detailed blocks by domain or layer. When multiple UI components share a contract, define a base interface (e.g. `BaseUIPanelProps`) and reference deltas per component.

### [Domain / Layer]

#### [Component Name]

| Field | Detail |
|-------|--------|
| Intent | 1-line description of the responsibility |
| Requirements | 2.1, 2.3 |
| Owner / Reviewers | (optional) |

**Responsibilities & Constraints**
- Primary responsibility
- Domain boundary and transaction scope
- Data ownership / invariants

**Dependencies**
- Inbound: name — purpose (P0/P1/P2)
- Outbound: name — purpose (P0/P1/P2)
- External: service/library — purpose (P0/P1/P2)

Summarize external dependency findings here; deeper investigation (API signatures, rate limits, migration notes) lives in `research.md`.

**Contracts**: Service [ ] / API [ ] / Event [ ] / Batch [ ] / State [ ]  ← tick only those that apply.

##### Service Interface
```typescript
interface [ComponentName]Service {
  methodName(input: InputType): Result<OutputType, ErrorType>;
}
```
- Preconditions:
- Postconditions:
- Invariants:

##### API Contract
| Method | Endpoint | Request | Response | Errors |
|--------|----------|---------|----------|--------|
| POST | /api/resource | CreateRequest | Resource | 400, 409, 500 |

##### Event Contract
- Published events:
- Subscribed events:
- Ordering / delivery guarantees:

##### Batch / Job Contract
- Trigger:
- Input / validation:
- Output / destination:
- Idempotency & recovery:

##### State Management
- State model:
- Persistence & consistency:
- Concurrency strategy:

**Implementation Notes** (combine Integration / Validation / Risks)
- Integration:
- Validation:
- Risks:

## Data Models

Focus on what changes with this feature.

### Domain Model
- Aggregates and transactional boundaries
- Entities, value objects, domain events
- Business rules & invariants
- Mermaid diagram only when relationships are non-trivial

### Logical Data Model
- Entity relationships and cardinality
- Attributes and types
- Natural keys / identifiers
- Referential integrity rules
- Consistency, transaction boundaries, cascading rules, temporal aspects

### Physical Data Model (when implementation requires storage-specific decisions)

Pick the storage tech relevant to this feature and document the specifics that matter:

- **Relational**: table definitions + types, PK/FK, indexes, partitioning strategy.
- **Document**: collection structures, embedding vs referencing, sharding key, indexes.
- **Event store**: event schemas, stream aggregation, snapshot policy, projections.
- **KV / Wide-column**: key design, column families, TTL and compaction.

### Data Contracts & Integration
- API request/response schemas + validation + serialization format (JSON, Protobuf…)
- Event schemas + versioning + backward/forward compatibility
- Cross-service: distributed transaction patterns (Saga, 2PC), sync strategies, eventual consistency handling

Skip subsections that don't apply.

## Error Handling

### Error Strategy

Concrete error handling patterns and recovery for each category relevant to this feature.

- **User errors (4xx)** — validation, auth, not-found. Field-level feedback, auth guidance, navigation help.
- **System errors (5xx)** — infra failures, timeouts, exhaustion. Graceful degradation, circuit breakers, rate limiting.
- **Business logic (422)** — rule violations, state conflicts. Condition explanations, transition guidance.

Include a Mermaid flowchart ONLY for complex error scenarios with business workflows.

### Monitoring
Error tracking, logging, health monitoring relevant to this feature.

## Testing Strategy

Adapt section names to fit the domain:
- Unit tests: 3–5 items from core functions/modules.
- Integration tests: 3–5 cross-component flows.
- E2E/UI (if applicable): 3–5 critical user paths.
- Performance/Load (if applicable): 3–4 concurrency or high-volume items.

## Verification Strategy

**MANDATORY.** How AI and humans verify this feature works locally — WITHOUT waiting for CI. Commands must match the stack in `.blast/steering/tech.md`. If no local verification loop is possible, flag as architectural red flag.

### Local Test Command
Single-file / single-test command exercising THIS feature's tests.

```bash
# Example (Python/pytest): pytest tests/test_<feature>.py -v
# Example (JS/Jest):       npx jest tests/<feature>.test.ts
<command>
```

### Smoke Check
Fastest signal that the feature imports/mounts correctly (≤5s).

```bash
# Example: python -c "from src.<pkg>.<module> import <symbol>"
# Example: curl -fs http://localhost:8000/health
<command>
```

### End-to-End Probe
One concrete scenario through the actual entry point.

```bash
# Example: curl -X POST http://localhost:8000/api/login -d '{"email":"a@b.com","password":"x"}'
# Example: python scripts/smoke_<feature>.py
<command>
```

### Expected Signal
- Test command → `exit 0`, all green
- Smoke → <observable>
- E2E → <expected response / side effect>

## Optional Sections

### Security Considerations
_Use for features handling auth, sensitive data, external integrations, user permissions. Capture only decisions unique to this feature; defer baseline controls to steering._
- Threat modeling, security controls, compliance
- AuthN/AuthZ patterns
- Data protection and privacy

### Performance & Scalability
_Use when performance targets, high load, or scaling concerns exist. Record only feature-specific targets/trade-offs; rely on steering for general practices._
- Target metrics + measurement strategy
- Scaling approach (horizontal/vertical)
- Caching and optimization

### Migration Strategy
Include a Mermaid flowchart showing migration phases when schema/data movement is required.
- Phase breakdown, rollback triggers, validation checkpoints

## Supporting References (optional)

Create ONLY when keeping content in the main body hurts readability (long TypeScript definitions, vendor option matrices, exhaustive schema tables). Decision-making context stays in the main sections so `design.md` stands alone. Link from the main text instead of inlining large snippets. Background research lives in `research.md`, but conclusions must appear here.
