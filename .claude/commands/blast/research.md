---
description: "Spike / research — zbadaj opcje, porównaj, zapisz wnioski"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch, Task
argument-hint: <feature-name> [--deep]
---

# blast:research — Badanie terenu przed designem

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Split by spaces
- Extract flags: `--deep` (thorough multi-source research with benchmarks)
- Ignore unknown flags (tokens starting with `-` that aren't `--deep`)
- Extract feature name (first non-flag token — kebab-case identifier)

Examples:
```
"zoo-garden"         → feature=zoo-garden, deep=false
"zoo-garden --deep"  → feature=zoo-garden, deep=true
"--deep zoo-garden"  → feature=zoo-garden, deep=true
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`. Parse it yourself.

<background_information>
- **Mission**: Research/spike phase — investigate options, compare approaches, record findings and decisions before design begins
- **Success Criteria**:
  - `research.md` created in spec directory with structured findings
  - Options compared with trade-offs
  - Clear recommendation for design phase
  - spec.json updated with `phase: "research-completed"`
</background_information>

<instructions>
## Core Task
Execute research/spike for the given feature — investigate technical options, compare approaches, consult docs and community, produce structured `research.md` with findings and recommendation.

## Execution Steps

### Step 1: Load Context

1. Read `.blast/specs/{feature}/spec.json` — verify feature exists
2. Read `.blast/specs/{feature}/requirements.md` — understand what needs to be built
3. Read `.blast/steering/*.md` — project context, stack, conventions
4. Check if `research.md` already exists (update vs create)

**Phase check**: Research is most useful after requirements, before design. Warn if design already exists (findings may override it).

### Step 2: Identify Research Questions

From requirements, extract key questions:
- What technical approaches solve this?
- What libraries/tools are available?
- What are the performance/scalability implications?
- What patterns does the existing codebase use? (check steering)
- Are there security considerations?
- What are the integration points?

Output research plan (3-7 questions) to console.

### Step 3: Execute Research

For each question:

**Standard mode** (default):
- Check project steering and existing code first (Grep, Glob)
- Search local knowledge base (`.blast/knowledge/`) — decisions, references, previous research
- If knowledge base answers the question — skip web search
- WebSearch for current best practices and comparisons (only if needed)
- Consult official docs (WebFetch)
- Summarize findings concisely
- Save reusable findings back to knowledge base

**Deep mode** (`--deep`):
- Everything in standard mode, plus:
- Search for benchmarks and performance comparisons
- Look for community discussion (GitHub issues, forums)
- Check for known pitfalls and migration stories
- Consider 3+ alternatives for each major decision
- Use Task tool with subagents for parallel research on independent questions

### Step 4: Compare Options

For each major decision point, build comparison:
- Minimum 2 options (3+ for `--deep`)
- Strengths and risks for each
- Fit with existing stack (from steering)
- Recommendation with rationale

### Step 5: Write research.md

Create/update `.blast/specs/{feature}/research.md` using template from `.blast/settings/templates/specs/research.md`:

Fill in:
- **Summary**: Feature name, scope, key findings
- **Research Log**: Question → sources → findings → implications
- **Architecture Pattern Evaluation**: Options table
- **Design Decisions**: Selected approaches with rationale
- **Risks & Mitigations**: Identified risks
- **References**: Links to docs, articles, benchmarks

### Step 6: Update spec.json

Update `spec.json`:
- `phase`: `"research-completed"` (if was `"requirements-generated"`)
- `updated_at`: current timestamp
- Add `research_scope`: `"standard"` or `"deep"`

</instructions>

## Tool Guidance
- **Read**: Load spec files, steering, existing code
- **Grep/Glob**: Search codebase for existing patterns and implementations
- **WebSearch**: Find current best practices, library comparisons, benchmarks
- **WebFetch**: Read official documentation, API references
- **Task**: Parallel research subagents (deep mode only)
- **Write/Edit**: Create/update research.md and spec.json

## Output Description

Provide output in the language specified in `spec.json`:

1. **Research Scope**: Standard or Deep, N questions investigated
2. **Key Findings**: Top 3-5 findings (one line each)
3. **Recommendation**: Recommended approach with one-sentence rationale
4. **Next Step**: `/blast:design {feature}` (research informs design decisions)

**Format**: Concise (under 200 words)

## Safety & Fallback

### Error Scenarios

**Feature Not Found**:
- "Spec `{feature}` nie istnieje. Sprawdź `/blast:status`"

**No Requirements Yet**:
- "Brak requirements — research potrzebuje kontekstu. Najpierw `/blast:requirements {feature}`"

**Design Already Exists**:
- **Warning**: "Design already exists — research findings may require design update"
- **Action**: Proceed, but note conflicts with existing design in research.md

**WebSearch Unavailable**:
- Fall back to codebase analysis and steering context only
- Note limitation in research.md
