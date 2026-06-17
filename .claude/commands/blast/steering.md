---
description: "Pamięć projektu — blast ładuje lub odświeża steering"
allowed-tools: Read, Task, Glob
---

# Blast Steering Management

## Mode Detection

**Perform detection before invoking Subagent (deterministic, in this order)**:

### Step 1: Stub marker check (highest priority)

Use Grep to check if ANY of `product.md`, `tech.md`, `structure.md` contains the stub marker `<!-- BLAST_STUB: fresh scaffold from \`blast init\` -->`. If yes → **Bootstrap Mode (fresh scaffold)**.

This catches the post-`blast init` state where files exist (so the legacy "files exist → sync" rule misfires) but content is still placeholder. Steward MUST ask the user about purpose/stack/structure rather than infer from `.blast/MANIFEST.md` / `.blast/CONSTITUTION.md` / `.blast/CLAUDE.snippet.md` — those are framework reference, not project signals. Root `CLAUDE.md` (if present) is purely the user's project file — blast's own instructions live in `.claude/CLAUDE.md`, so any root `CLAUDE.md` content CAN inform steering.

### Step 2: Empty/missing core files

If no stub marker but `product.md` / `tech.md` / `structure.md` is missing OR has zero non-comment content → **Bootstrap Mode (greenfield)**.

### Step 3: Files exist with real content

→ **Sync Mode** (refresh existing content, detect drift, preserve user edits)

### Step 4: Fresh-scaffold safety check (Bootstrap Mode only)

If Bootstrap Mode triggered AND the project has `.blast/CONSTITUTION.md` AND no `src/` AND `.blast/specs/` is empty → flag `BOOTSTRAP_REASON=fresh-scaffold` in subagent prompt. Steward will switch to ASK mode (5–7 user questions) and explicitly ignore framework metadata files.

## Invoke Subagent

Delegate steering management to steering-agent:

Use the Task tool to invoke the Subagent with file path patterns:

```
Task(
  subagent_type="steering-agent",
  description="Steward — Manage steering files",
  prompt="""
Mode: {bootstrap | sync}
Bootstrap reason: {fresh-scaffold | greenfield | none}   # only set when mode=bootstrap

File patterns to read:
- .blast/steering/*.md
- .blast/settings/templates/steering/*.md
- .blast/settings/rules/steering-principles.md

If Bootstrap reason = fresh-scaffold:
  - Files exist with BLAST_STUB markers — content is placeholder, NOT user data
  - DO NOT infer project description from .claude/CLAUDE.md, .blast/CLAUDE.snippet.md, .blast/CONSTITUTION.md, or any other framework file
  - DO ask the user 5–7 short questions (purpose, target audience, stack, key dependencies, conventions, deployment, integrations)
  - Stack Fingerprint: still try filesystem detection first (.python-version, package.json, etc.) but fall back to ASK rather than guess from framework allow-lists

JIT Strategy: Fetch codebase files when needed, not upfront
"""
)
```

## Display Result

Show Subagent summary to user:

### Bootstrap:
- Generated steering files: product.md, tech.md, structure.md
- Review and approve as Source of Truth

### Sync:
- Updated steering files
- Code drift warnings
- Recommendations for custom steering

## Notes

- All `.blast/steering/*.md` loaded as project memory
- Templates and principles are external for customization
- Focus on patterns, not catalogs
- "Golden Rule": New code following patterns shouldn't require steering updates
- Avoid documenting agent-specific tooling directories (e.g. `.cursor/`, `.gemini/`, `.claude/`)
- `.blast/settings/` content should NOT be documented in steering files (settings are metadata, not project knowledge)
- Light references to `.blast/specs/` and `.blast/steering/` are acceptable; avoid other `.blast/` directories


## --learn flag (post-feature lessons aggregation)

When invoked with `--learn`, before running standard steering:

1. Run `python .claude/scripts/blast-learn.py --lessons --apply`
2. Read `.blast/steering/lessons.md` (just generated)
3. Review recurring themes (bigram frequency ≥ 2)
4. Promote relevant lessons to `tech.md::Gotchas` section (concise bullets)
5. Continue with normal steering refresh

This closes the spec → project feedback loop: per-spec retrospections aggregated
→ recurring patterns identified → project-wide guidance updated.
