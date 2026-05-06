---
description: "Approve faza specu — odblokuj kolejny etap pipeline'u"
allowed-tools: Read, Edit, Bash
argument-hint: <feature-name> <phase>
---

# blast:approve — Klepnięcie fazy

Ustawia `approvals.{phase}.approved = true` w `.blast/specs/{feature}/spec.json` i zapisuje znacznik czasu zatwierdzenia. To jest user-facing odpowiednik `-y` — używaj kiedy chcesz świadomie zaakceptować artefakt po review (zamiast bypassu).

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Split by spaces
- First non-flag token = feature name (kebab-case)
- Second non-flag token = phase name (one of: `requirements`, `design`, `tasks`)

Examples:
```
"zoo-garden requirements"  → feature=zoo-garden, phase=requirements
"zoo-garden design"        → feature=zoo-garden, phase=design
"zoo-garden tasks"         → feature=zoo-garden, phase=tasks
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`/`$2`. Parse it yourself.

## Validate

1. Verify `.blast/specs/{feature}/spec.json` exists. If not: STOP with:
   ```
   Spec not found: .blast/specs/{feature}/

   Run /blast:init "<opis>" to create a new spec, or /blast:status to see existing specs.
   ```

2. Verify phase is one of `requirements`, `design`, `tasks`. If not: STOP with:
   ```
   Unknown phase: '{phase}'. Allowed: requirements | design | tasks
   ```

3. Verify the artifact for that phase exists:
   - `requirements` → `.blast/specs/{feature}/requirements.md`
   - `design` → `.blast/specs/{feature}/design.md`
   - `tasks` → `.blast/specs/{feature}/tasks.md`
   If missing: STOP with `{phase}.md not generated yet — run the corresponding /blast command first.`

4. Verify `approvals.{phase}.generated === true`. If false: WARN (not stop) — "Phase {phase} marked as not yet generated; approving anyway." and continue.

## Apply

Generate current ISO-8601 UTC timestamp (use Bash: `date -u +%Y-%m-%dT%H:%M:%SZ`).

Use the Edit tool on `.blast/specs/{feature}/spec.json`:
1. Set `approvals.{phase}.approved` to `true`.
2. Add or update `approvals.{phase}.approvedAt` to the timestamp.
3. Update top-level `updated_at` to the same timestamp.

Preserve all other JSON fields and key order. The file MUST remain valid JSON.

## Display Result

Print exactly (substituting values):
```
✓ Approved: {feature} / {phase}   ({timestamp})

Next:
  - requirements approved → /blast:design {feature}
  - design approved       → /blast:tasks {feature}
  - tasks approved        → /blast:impl {feature}
```
Show only the line that matches the approved phase as the "Next" suggestion.

## Safety & Fallback

- **Already approved**: if `approvals.{phase}.approved` is already `true`, refresh `approvedAt` and `updated_at`, print `Already approved (refreshed timestamp): {feature} / {phase}`. Do NOT error.
- **JSON parse error**: STOP with `spec.json malformed — fix manually.` Do not attempt automatic repair.
