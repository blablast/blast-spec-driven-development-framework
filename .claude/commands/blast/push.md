---
description: "Git push — blast commituje i pushuje ficzer"
allowed-tools: Bash, Read, Glob, Grep
argument-hint: [feature-name]
---

# blast:push — Wrzucamy na repo

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Strip any flags (tokens starting with `-`) — this command has no flags
- Extract feature name from remaining tokens (kebab-case identifier, optional)
- If empty: auto-detect from recent spec or git changes

Examples:
```
"zoo-garden"     → feature=zoo-garden
""               → feature=auto-detect
"zoo-garden -y"  → feature=zoo-garden (flag ignored)
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`. Parse it yourself.

<background_information>
- **Mission**: Stage changes, create a descriptive commit, and push to remote. Commit message in English, descriptive title, concise summary.
- **Success Criteria**:
  - All relevant files staged (no secrets, no junk)
  - Commit message: descriptive English title + concise summary (meat only, no fluff)
  - Default branch auto-detected, push executed
  - PR created if on feature branch (optional, suggest only)
</background_information>

<instructions>
## Core Task
Stage, commit, and push changes related to a feature (or all uncommitted changes if no feature specified).

## Execution Steps

### Step 1: Assess State

1. Run `git status` — see what's changed (staged, unstaged, untracked)
2. Run `git diff --stat` — understand scope of changes
3. Run `git log --oneline -5` — see recent commit style for consistency
4. If feature provided: read `.blast/specs/{feature}/spec.json` for context (feature name, description, status)
5. If no feature: infer scope from changed files

### Step 2: Stage Files

**Smart staging** — stage relevant files, skip dangerous ones:

**Always skip** (never stage):
- `.env`, `.env.*` — secrets
- `*.local.json` — local config
- `credentials.*`, `*secret*`, `*token*` — sensitive data
- `__pycache__/`, `node_modules/`, `.pyc` files — artifacts
- `.DS_Store`, `Thumbs.db` — OS junk

**Feature-scoped** (if feature provided):
- Stage files in `src/` (or project source) matching feature's components
- Stage test files for the feature
- Stage `.blast/specs/{feature}/` — spec files
- Stage `.blast/steering/` — if updated by `/blast:complete` or `/blast:steering`
- Stage `CLAUDE.md` if modified

**Full scope** (no feature):
- Stage all modified/new files except skipped patterns
- Use `git add` with specific paths, NOT `git add -A`

If any potentially sensitive files are detected, **list them and ask user before staging**.

### Step 3: Generate Commit Message

**Format**:
```
<descriptive title in English, max 72 chars>

<concise summary — only the meat, 2-5 lines>
```

**Author rules** (strict):
- Author = user only. Do NOT append `Co-Authored-By: Claude ...` trailer.
- Do NOT add "Generated with Claude Code" footer or any AI-attribution line.
- No emoji.

**Title rules**:
- English, imperative mood ("Add zoo management system", not "Added" or "Adding")
- Descriptive — say WHAT was done, not just "update files"
- Max 72 characters
- No period at end
- Scope prefix (`feat(zoo): ...`) ONLY if `git log --oneline -5` shows the repo already uses conventional/scoped format. Otherwise skip.

**Summary rules**:
- English, concise — every word must earn its place
- What was built/changed and why — no filler, no "this commit does...", no marketing language
- Prefer one paragraph. Bullets only for genuinely multi-part changes (big feature rollup with distinct components)
- Include key stats if useful: "90 tests passing, 6 modules"
- If feature-scoped: reference spec name
- Skip the summary entirely if the title alone suffices (trivial change)

**Examples**:
```
Add zoo garden simulation with TDD implementation

- Animal hierarchy: 10 species with polymorphic behavior
- Enclosure management with capacity constraints
- Employee system: zookeepers, vets, guides
- 90 tests passing across 6 test modules
```

```
Fix argument parsing in blast slash commands

Replace $1/$2 positional args with $ARGUMENTS string parsing
across all 11 commands. Add unknown flag tolerance.
```

### Step 4: Commit

Run `git commit` with the generated message using HEREDOC format:
```bash
git commit -m "$(cat <<'EOF'
<title>

<summary>
EOF
)"
```

### Step 5: Push

1. Detect current branch: `git branch --show-current`
2. Check if remote tracking exists: `git rev-parse --abbrev-ref @{upstream} 2>/dev/null`
3. If no upstream: `git push -u origin {branch}`
4. If upstream exists: `git push`

### Step 6: Output Summary

Report:
- Branch pushed
- Commit hash and title
- Files changed count
- If on feature branch (not main/master): suggest `gh pr create` with title

</instructions>

## Tool Guidance
- **Bash**: git commands (status, diff, add, commit, push, log)
- **Read**: spec.json for feature context
- **Glob**: find files to stage
- **Grep**: check for sensitive patterns in files before staging

## Output Description

Provide concise output:

```
✅ Pushed to origin/{branch}

Commit: {hash} {title}
Files: {count} changed ({insertions}+, {deletions}-)

{If feature branch, suggest PR}
```

**Format**: Under 100 words.

## Safety & Fallback

### Error Scenarios

**No Changes to Commit**:
- "Nothing to commit — working tree clean"

**Sensitive Files Detected**:
- List files and ask: "These files may contain secrets. Stage them? (list specific files)"
- Do NOT stage without confirmation

**No Remote Configured**:
- "No remote configured. Add one with: `git remote add origin <url>`"

**Push Rejected**:
- If behind remote: suggest `git pull --rebase` first
- If protected branch: warn and suggest feature branch

**Not a Git Repository**:
- "Not a git repository. Initialize with: `git init`"
