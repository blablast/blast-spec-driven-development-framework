# Design Review Process

## Objective

Quality review of `design.md` to decide GO/NO-GO before implementation. Limit to 3 critical concerns. Do not perform implementation-level design or finalize technology choices — defer to design iteration.

## Core Review Criteria

### 1. Existing Architecture Alignment (Critical)
- Integration with existing system boundaries and layers
- Consistency with established architectural patterns
- Proper dependency direction and coupling management
- Alignment with current module organization

### 2. Design Consistency & Standards
- Adherence to project naming conventions and code standards
- Consistent error handling and logging strategies
- Uniform configuration and dependency management
- Alignment with established data modeling patterns

### 3. Extensibility & Maintainability
- Design flexibility for future requirements
- Clear separation of concerns and single responsibility
- Testability and debugging considerations
- Appropriate complexity for requirements

### 4. Type Safety & Interface Design
- Proper type definitions and interface contracts
- Avoidance of unsafe patterns (e.g., `any` in TypeScript)
- Clear API boundaries and data structures
- Input validation and error handling coverage

## Review Process

### Step 1: Analyze
Analyze design against all review criteria, focusing on critical issues impacting integration, maintainability, complexity, and requirements fulfillment.

### Step 2: Identify Critical Issues (≤3)
For each issue:
```
🔴 **Critical Issue [1-3]**: [Brief title]
**Concern**: [Specific problem]
**Impact**: [Why it matters]
**Suggestion**: [Concrete improvement]
**Traceability**: [Requirement ID/section from requirements.md]
**Evidence**: [Design doc section/heading]
```

### Step 3: Recognize Strengths
Acknowledge 1-2 strong aspects to maintain balanced feedback.

### Step 4: Decide GO/NO-GO
- **GO**: No critical architectural misalignment, requirements addressed, clear implementation path, acceptable risks
- **NO-GO**: Fundamental conflicts, critical gaps, high failure risk, disproportionate complexity

## Traceability & Evidence

- Link each critical issue to the relevant requirement(s) from `requirements.md` (ID or section).
- Cite evidence locations in the design document (section/heading, diagram, or artifact) to support the assessment.
- When applicable, reference constraints from steering context to justify the issue.

## Output Format

### Design Review Summary
2-3 sentences on overall quality and readiness.

### Critical Issues (≤3)
For each: Issue, Impact, Recommendation, Traceability (e.g., 1.1, 1.2), Evidence (design.md section).

### Design Strengths
1-2 positive aspects.

### Final Assessment
Decision (GO/NO-GO), Rationale (1-2 sentences), Next Steps.

### Interactive Discussion
Engage on designer's perspective, alternatives, clarifications, and necessary changes.

## Length

- Summary: 2–3 sentences
- Each critical issue: 5–7 lines (Issue/Impact/Recommendation/Traceability/Evidence)
- Overall: ~400 words

## Final Checklist

- **Critical Issues ≤ 3** and each includes Impact and Recommendation
- **Traceability**: Each issue references requirement ID/section
- **Evidence**: Each issue cites design doc location
- **Decision**: GO/NO-GO with clear rationale and next steps
