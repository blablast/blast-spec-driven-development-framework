# Light Discovery Process (for simple extensions)

> Used for feature extensions that fit existing patterns. Escalate to `design-discovery-full.md` if any trigger below fires.

## Steps

### 1. Extension Point Analysis

- Locate existing extension points / interfaces.
- Determine modification scope (files, components).
- Identify patterns to follow.
- Backward compatibility requirements.

### 2. Dependency Check

- Version compatibility of new dependencies.
- API contracts haven't changed.
- No breaking changes in pipeline.

### 3. Quick Technology Verification (new libraries only)

- WebSearch for official documentation.
- Basic usage patterns.
- Known compatibility issues.
- Licensing compatibility.
- Record key findings in `research.md`.

### 4. Integration Risk

- Impact on existing functionality.
- Performance implications.
- Security considerations.
- Testing requirements.

## Escalate to Full Discovery when

- Significant architectural changes needed.
- Complex external service integrations.
- Security-sensitive implementations.
- Performance-critical components.
- Unknown or poorly documented dependencies.

## Output

- Clear integration approach (note boundary impacts in `research.md`).
- List of files/components to modify.
- New dependencies with versions.
- Integration risks + mitigations.
- Testing focus areas.
