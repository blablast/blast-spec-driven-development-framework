# Full Discovery Process (for `/blast:design`)

> Used when the feature is non-trivial (new components, architectural shifts, external integrations, security-sensitive). Produces `research.md` as the investigation log.

## Discovery Steps

### 1. Requirements → Technical needs

- Extract all functional requirements from EARS; identify non-functionals (perf, security, scalability).
- Determine technical constraints and dependencies.
- List core technical challenges.

### 2. Existing Implementation Analysis (if extending)

- Codebase structure and architecture patterns.
- Reusable components, services, utilities.
- Domain boundaries and data flows.
- Integration points and dependencies.
- Approach: extend vs refactor vs wrap.

### 3. Technology Research

Use WebSearch for:
- Latest architectural patterns for similar problems.
- Industry best practices for the stack.
- Recent changes in relevant technologies.
- Common pitfalls.

Use WebFetch for:
- Official framework/library docs.
- API references.
- Migration guides / breaking changes.
- Performance benchmarks.

### 4. External Dependencies

Per external service/library:
- Verify API signatures and auth methods.
- Version compatibility with existing stack.
- Rate limits and usage constraints.
- Known issues / community resources.
- Security considerations.
- Gaps requiring implementation investigation.

### 5. Architecture Pattern & Boundary Analysis

- Compare relevant patterns (MVC, Clean, Hexagonal, Event-driven).
- Assess fit with existing architecture and steering principles.
- Identify domain boundaries and ownership seams (to avoid team conflicts).
- Consider scalability, operations, maintainability, team expertise.
- Document preferred pattern + rejected alternatives in `research.md`.

### 6. Risk Assessment

- Performance bottlenecks and scaling limits.
- Security vulnerabilities and attack vectors.
- Integration complexity and coupling.
- Technical debt created vs resolved.
- Knowledge gaps.

## Output → `research.md`

Capture:
- Key insights affecting architecture, technology alignment, contracts.
- Constraints discovered.
- Recommended approaches and selected architecture pattern with rationale.
- Rejected alternatives and trade-offs (Design Decisions section).
- Updated domain boundaries for Components & Interface Contracts.
- Risks and mitigations.
- Gaps requiring further investigation during implementation.
