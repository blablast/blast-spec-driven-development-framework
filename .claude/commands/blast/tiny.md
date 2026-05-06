---
description: "Fast path dla małych ficzerów — spec + impl w jednym strzale"
allowed-tools: Read, SlashCommand, TodoWrite, Bash, Write, Glob, Task
argument-hint: <description> [--auto] [--source path/to/file]
---

# blast:tiny — Mały ficzer, jeden strzał

> Use when: jednowyrazowa zmiana, dodanie walidacji, drobny util, fix copy. Wszystko z 1–3 deliverables, brak architektury, brak external deps, ~30 min focused work.
>
> Use NIE: integracje, auth, schema changes, nowe API, cokolwiek z research. Wtedy `/blast:quick` lub `/blast:full`.

<instructions>
Pipeline: init (template) → spec-tiny-agent (compressed req+design+tasks, self-approve) → impl. **Bez approvals interaktywnych**, bez research, bez validate. Default: automatic mode (interactive prompt tylko po fazie tiny-agent jeśli bez `--auto`).

## Step 1: Parse Arguments

Parse `$ARGUMENTS` as a single string:
- If contains `--auto`: skip the post-tiny-agent confirmation prompt, run impl immediately
- If contains `--source <path>`: extract source file path (PDF/MD/TXT/HTML)
- Extract description (everything else)

Examples:
```
"add email validation to UserForm"            → desc="add email validation to UserForm", auto=false
"fix typo in welcome banner --auto"           → desc="fix typo in welcome banner", auto=true
"validate phone --source notes/req.md --auto" → source=notes/req.md, auto=true
```

**IMPORTANT**: `$ARGUMENTS` is a single string. Parse it yourself.

## Step 2: Init Spec (template fill, identical to /blast:full Phase 1)

1. **Generate Feature Name**: kebab-case from description (2-4 words).
2. **Check Uniqueness**: Glob `.blast/specs/*/`, append `-2` if conflict.
3. **Create Directory**: `mkdir -p .blast/specs/{feature-name}`.
4. **Initialize Files**:
   - Read `.blast/settings/templates/specs/init.json` and `.blast/settings/templates/specs/requirements-init.md`
   - Replace `{{FEATURE_NAME}}`, `{{TIMESTAMP}}`, `{{PROJECT_DESCRIPTION}}`
   - **If `--source`**: read source file, embed in requirements.md as `## Source Material`
   - Write `spec.json` and `requirements.md`

**Output**: `✅ Spec initialized at .blast/specs/{feature-name}/`

## Step 3: Run spec-tiny-agent (single Task call)

Use the Task tool to invoke the tiny agent:

```
Task(
  subagent_type="spec-tiny-agent",
  description="Generate compressed spec for tiny feature",
  prompt="""
Feature: {feature-name}
Spec directory: .blast/specs/{feature-name}/
Original description: {description}

File patterns to read:
- .blast/specs/{feature-name}/spec.json
- .blast/specs/{feature-name}/requirements.md
- .blast/steering/product.md
- .blast/steering/tech.md
- .blast/steering/structure.md
- .blast/steering/INVENTORY.md

Mode: tiny (single-batch generate of req+design+tasks; self-approve all phases)
"""
)
```

**Wait for completion**. The tiny-agent may ESCALATE (if it judges the work non-trivial) — in that case, it will output the standard escalation message. If escalation:
- Display the escalation verbatim to user
- Do NOT proceed to impl
- Exit cleanly

## Step 4: Confirmation Gate (skipped in --auto)

**If NOT `--auto`**: prompt user:
```
✅ Tiny spec generated:
   .blast/specs/{feature-name}/requirements.md   ({N} requirements)
   .blast/specs/{feature-name}/design.md         ({M} components)
   .blast/specs/{feature-name}/tasks.md          ({K} tasks)

Proceed to /blast:impl, or review/edit first?
  [y] yes, run impl now
  [r] let me review first (exit, run /blast:impl manually after)
```

If user picks `r` → exit with: `Review then run: /blast:impl {feature-name} -y`.

If user picks `y` (or `--auto` was set): proceed to Step 5.

## Step 5: Run Impl

**Execute SlashCommand**: `/blast:impl {feature-name} -y`

Note: `-y` is technically redundant (tiny-agent already self-approved tasks), but kept for explicit intent.

Wait for completion. This is the heaviest phase.

## Step 6: Final Summary

```
🎉 /blast:tiny complete!

Feature: {feature-name}
Status: active (tiny)

## Generated:
- Spec: {N} requirements, {M} components, {K} tasks (compressed)
- Code: {X} files created/modified, {Y} tests passing

## Next steps (optional, manual):
- /blast:complete {feature-name}   (mark shipped + update INVENTORY)
- /blast:security {feature-name}   (security audit)

For tiny work, complete + security are usually skipped — the work is too small to register
in INVENTORY. Run them only if this turned out non-trivial after all.
```
</instructions>

## Safety & Fallback

### Escalation (from tiny-agent Step 2)

If `spec-tiny-agent` returns the standard escalation message (work too complex), display it verbatim and exit. Suggested user action is in the message; do NOT auto-redirect.

### Spec Already Exists (non-tiny)

If `.blast/specs/{feature-name}/` exists and has non-tiny content (no `tiny: true` marker in spec.json), STOP with:
```
Spec '{feature-name}' already exists with standard pipeline content.
Use /blast:impl {feature-name} directly, or pick a different name.
```

### Verification Strategy Missing in Generated design.md

Tiny-agent SHOULD always produce a Verification Strategy section. If somehow missing, impl will warn (per Fala 2 wiring) but proceed. Not a hard error.

### When to NOT use /blast:tiny

If user description suggests architectural concerns (auth, persistence, API, integration, schema, "let's design", "research how to..."), suggest:
```
This sounds non-tiny. For better results:
  /blast:quick "<desc>"        — full spec generation, no impl
  /blast:full  "<desc>" --auto — full spec + impl (with optional --validate)
```

(This safety check is also done by tiny-agent itself in its Step 2.)
