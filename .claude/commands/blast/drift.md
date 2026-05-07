---
description: "Wykryj drift między shipped spec a aktualnym kodem — raportuj rozjazd"
allowed-tools: Read, Task
argument-hint: <feature-name>
---

# blast:drift — Spec ↔ kod drift detection

Sprawdza czy `design.md::Components` zgadza się z aktualnym kodem. Po jakimś czasie po shipped — refaktor, drobne zmiany, removed components → drift. Tracker (haiku agent) raportuje co znalazł, klasyfikuje severity, sugeruje remediation (zwykle `/blast:evolve` jeśli drift legit).

> **Use when**: shipped feature po jakimś czasie, chcesz audyt czy spec wciąż aktualny.
> **Use NIE when**: spec jeszcze nie shipped (pipeline normalny zrobi swoje); małe ad-hoc zmiany (wyjaśnij user'owi że spec jest source of truth).

## Parse Arguments

Parse `$ARGUMENTS`:
- First non-flag token = feature name (kebab-case identifier)

Examples:
```
"auth-oauth"        → feature=auth-oauth
"user-profile"      → feature=user-profile
```

**IMPORTANT**: `$ARGUMENTS` is single string, parse it yourself.

## Validate

Check spec exists:

1. Verify `.blast/specs/{feature}/` exists. If not:
   ```
   ❌ Feature '{feature}' nie istnieje. Use /blast:status żeby zobaczyć dostępne specy.
   ```
   STOP.

2. Verify `.blast/specs/{feature}/design.md` exists. If not:
   ```
   ❌ design.md missing for '{feature}'. Drift check requires Components section.
   Run /blast:design {feature} pierw.
   ```
   STOP.

3. Verify `design.md` contains `## Components` section (Bash grep). If not:
   ```
   ❌ design.md does not have `## Components` section.
   Drift check requires component inventory. Update design.md.
   ```
   STOP.

## Soft warning (non-blocking)

Read spec.json, check `status`:
- `shipped` → no warning, proceed normally
- `active` / `planning` → WARN: "Drift check most useful for shipped features. This spec is {status} — drift may reflect work-in-progress, not real drift. Continuing anyway."
- `deprecated` → WARN: "Spec is deprecated. Drift check skipped — use /blast:status to verify retirement plan."

Continue regardless (warning is informational).

## Invoke Subagent

Delegate drift detection to spec-drift-agent:

```
Task(
  subagent_type="spec-drift-agent",
  description="Tracker — Detect drift between spec and codebase",
  prompt="""
Feature: {feature}
Spec directory: .blast/specs/{feature}/

File patterns to read:
- .blast/specs/{feature}/spec.json
- .blast/specs/{feature}/design.md
- .blast/specs/{feature}/tasks.md
- .blast/specs/{feature}/evolutions/*/evolution.md (if exist)
- .blast/steering/structure.md

Code patterns to search (defaults — agent may expand):
- src/**, lib/**, app/**, tests/**

Algorithm: hybrid static + LLM semantic
- Static pre-check first (file existence, signature grep)
- LLM semantic only on suspicious components
- Severity: NONE | INFO | WARNING | CRITICAL

Output: drift report markdown + verdict envelope (---VERDICT---...---END---)
"""
)
```

## Display Result

Show subagent's report verbatim, plus add:

### Quick interpretation guide

After report:
```
Severity legend:
  CRITICAL — Component completely missing. Spec lies. Action required.
  WARNING  — Functional drift (signature/behavior changed). Likely needs evolution.
  INFO     — Cosmetic drift (file moved, internal refactor). Update spec at convenience.
  NONE     — Clean. Spec matches reality.

Common remediations:
  - Drift is intentional → /blast:evolve {feature} "<change description>"
  - Drift is accidental → revert code to match spec
  - Component truly removed → /blast:evolve {feature} "remove <component>"
```

### After verdict

If `VERDICT: FAIL` (CRITICAL findings):
```
⚠️ Drift report shows CRITICAL findings. Spec no longer matches code.
Recommended next step: /blast:evolve {feature} "<consolidated change description>"
```

If `VERDICT: WARN` (WARNING findings):
```
⚠️ Drift detected (WARNING level). Review findings — likely legit refactors not yet specified.
Suggested: /blast:evolve {feature} "<change description>" if changes are intentional.
```

If `VERDICT: PASS`:
```
✅ Spec matches reality. No action needed.
```

## Safety & Fallback

- **Code dirs not standard**: jeśli projekt nie używa `src/lib/app/` — agent może próbować innych standardowych (sprawdzi `tech.md`'s `Stack Fingerprint`). Jeśli wciąż nie znajdzie — WARN i continue.
- **LLM tokens budżet**: dla feature'u z 50+ components, LLM check może być drogi. Agent ma limit (max 10 LLM checks per run); pozostałe oznacza "INDETERMINATE — sample only".
- **False positives wysokie**: gdy projekt używa nietypowych conventions. User może whitelistować kompoenenty (future Fala).
