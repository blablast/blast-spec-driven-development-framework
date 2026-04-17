---
description: "Odpalamy nowy spec — blast inicjalizuje strukturę i metadane"
allowed-tools: Bash, Read, Write, Glob
argument-hint: <project-description> [--source path/to/file.pdf|md|txt]
---

# blast:init — Nowy spec wchodzi do gry

<background_information>
- **Mission**: Initialize the first phase of spec-driven development by creating directory structure and metadata for a new specification
- **Success Criteria**:
  - Generate appropriate feature name from project description
  - Create unique spec structure without conflicts
  - If source file provided: extract and embed its content into requirements.md
  - Provide clear path to next phase (requirements generation)
</background_information>

<instructions>
## Core Task
Generate a unique feature name from the project description ($ARGUMENTS) and initialize the specification structure. If a source file is provided, extract its content and embed it as input for the requirements phase.

## Execution Steps

### Step 1: Parse Arguments

Parse `$ARGUMENTS` for:
- `--source <path>` flag — path to a source file (PDF, MD, TXT, HTML, DOCX)
- Remaining text — project description

Examples:
```
"System logowania z OAuth2" → description only
"System logowania z OAuth2 --source docs/brief.pdf" → description + source file
"--source specs/kanban-feature.md" → source file only (extract description from content)
```

If `--source` provided:
- Read the file using Read tool (supports: .pdf, .md, .txt, .html)
- For other formats: attempt Read, warn if unsupported
- Extract key content for embedding in requirements.md

If no description AND no source: ask user for at least a one-line description.

### Step 2: Check Uniqueness

Verify `.blast/specs/` for naming conflicts (append number suffix if needed).

### Step 3: Create Directory

`mkdir -p .blast/specs/[feature-name]/`

### Step 4: Initialize Files Using Templates

1. Read templates:
   - `.blast/settings/templates/specs/init.json`
   - `.blast/settings/templates/specs/requirements-init.md`

2. Replace placeholders:
   - `{{FEATURE_NAME}}` → generated feature name
   - `{{TIMESTAMP}}` → current ISO 8601 timestamp (use `date -u +"%Y-%m-%dT%H:%M:%SZ"`)
   - `{{PROJECT_DESCRIPTION}}` → project description

3. **If source file was provided**, enhance requirements.md:
   - After the `## Project Description` section, add:
   ```markdown
   ## Source Material
   > Imported from: `{source-path}`

   {extracted content from source file}
   ```
   - Default: keep source content verbatim (requirements agent needs full context)
   - **If content ≥500 tokens**: invoke `blastboom` skill to compress BEFORE embedding. Add note after path: `> Compressed via blastboom (original: {N} lines, {M} tokens)`. Preserves all facts/code/identifiers per skill contract.
   - **If content still >500 lines after compression**: embed first 500 lines, add note: "Source material truncated. Full document at: `{path}`"

4. Write files:
   - `.blast/specs/{feature-name}/spec.json`
   - `.blast/specs/{feature-name}/requirements.md`

### Step 5: Output

Provide output with:
1. Generated feature name with rationale
2. Project summary (1 sentence)
3. Created files list
4. **If source file used**: note what was imported and line count
5. Next step: `/blast:requirements {feature-name}`

## Important Constraints
- DO NOT generate requirements/design/tasks at this stage
- Follow stage-by-stage development principles
- Maintain strict phase separation
- Only initialization is performed in this phase
- Source file content is embedded as RAW INPUT — requirements agent will process it
</instructions>

## Tool Guidance
- Use **Glob** to check existing spec directories for name uniqueness
- Use **Read** to fetch templates AND source file (if `--source` provided)
- Use **Write** to create spec.json and requirements.md after placeholder replacement
- Use **Bash** for `mkdir -p` and timestamp generation
- Perform validation before any file write operation

## Output Description
Provide output in the language specified in `spec.json` with the following structure:

1. **Generated Feature Name**: `feature-name` format with 1-2 sentence rationale
2. **Project Summary**: Brief summary (1 sentence)
3. **Source Material**: *(only if --source used)* What was imported, line count, truncation note
4. **Created Files**: Bullet list with full paths
5. **Next Step**: Command block showing `/blast:requirements <feature-name>`
6. **Notes**: Explain why only initialization was performed (1-2 sentences)

**Format Requirements**:
- Use Markdown headings (##, ###)
- Wrap commands in code blocks
- Keep total output concise (under 300 words)
- Use clear, professional language per `spec.json.language`

## Safety & Fallback

**Ambiguous Feature Name**: Propose 2-3 options and ask user to select.

**Template Missing**: Report error with specific missing file path.

**Directory Conflict**: Append numeric suffix (e.g., `feature-name-2`) and notify user.

**Source File Not Found**: Warn and continue without source material. Suggest checking path.

**Source File Unreadable**: Warn about format, continue with description only. Suggest converting to .md or .txt.

**Source File Too Large** (≥500 tokens): Invoke `blastboom` skill to compress before embedding. If still >500 lines after compression, embed first 500 and add reference to full path.

**No Description AND No Source**: Ask user for at least a one-line description before proceeding.
