---
description: "Delta-spec dla shipped feature — opisz tylko zmianę, nie cały nowy spec"
allowed-tools: Read, Edit, Task
argument-hint: <parent-feature> "<change-description>"
---

# blast:evolve — Iteracja na shipped feature

Tworzy **delta-spec** (evolution) — focused diff opisujący ZMIANY względem shipped parent specu, nie cały nowy spec. Use case: dodanie pola, zmiana algorytmu, breaking refactor — w istniejącej, shipped feature.

> **Use this when**: shipped feature wymaga modyfikacji (nowy req, breaking change, refactor).
> **Use NIE when**: nowy ficzer (use `/blast:init` lub `/blast:tiny`); cosmetic fix (use `/blast:tiny`); spec jeszcze nie shipped (just continue normal pipeline).

## Parse Arguments

Parse `$ARGUMENTS`:
- First non-flag token = parent feature name (kebab-case identifier)
- Remaining (in quotes lub do końca) = change description

Examples:
```
"auth-oauth \"add MFA support via TOTP\""
  → parent=auth-oauth, change="add MFA support via TOTP"

"user-profile \"breaking: rename email field to primary_email\""
  → parent=user-profile, change="breaking: rename email field to primary_email"

"api-rate-limiting \"refactor: switch from Redis to in-memory cache\""
  → parent=api-rate-limiting, change="refactor: switch from Redis to in-memory cache"
```

**IMPORTANT**: `$ARGUMENTS` is a single string. Parse it yourself.

## Validate

Check that parent exists and is shipped:

1. Verify `.blast/specs/{parent_feature}/` exists. If not:
   ```
   ❌ Parent feature '{parent_feature}' nie istnieje.
   Available specs:
   $(ls .blast/specs/ | head -10)
   ```
   STOP.

2. Verify `.blast/specs/{parent_feature}/spec.json` exists.

3. **Read** spec.json. Check `status` field.

## Gate (parent must be shipped)

```
Read .blast/specs/{parent_feature}/spec.json
Check `status` field:

- status == "shipped" → gate PASS, continue
- status == "active" or "planning" → gate STOP:
  ```
  ❌ Parent feature '{parent_feature}' is status: {actual}.
  Evolution requires shipped parent.
  
  Options:
  - Continue normal pipeline first: /blast:impl {parent} → /blast:complete {parent}
  - For small additions to active spec, use: /blast:tiny "{change}"
  ```
- status == "deprecated" → gate STOP:
  ```
  ❌ Parent feature '{parent_feature}' is deprecated.
  Cannot evolve deprecated feature. Start fresh: /blast:init "<description>"
  ```
```

## Invoke Subagent

Delegate evolution generation to spec-evolve-agent:

```
Task(
  subagent_type="spec-evolve-agent",
  description="Generate delta-spec for shipped feature",
  prompt="""
Parent feature: {parent_feature}
Change description: {change_description}

File patterns to read:
- .blast/specs/{parent_feature}/spec.json
- .blast/specs/{parent_feature}/requirements.md
- .blast/specs/{parent_feature}/design.md
- .blast/specs/{parent_feature}/tasks.md
- .blast/specs/{parent_feature}/evolutions/*/spec.json (existing evolutions for numbering)
- .blast/steering/*.md
- .blast/settings/templates/specs/evolution.md

Mode: generate delta-spec
Output location: .blast/specs/{parent_feature}/evolutions/{NN}-{slug}/
"""
)
```

## Display Result

Show subagent summary, then provide next-step guidance:

### After evolution generated

```
✅ Evolution {NN}-{slug} generated at .blast/specs/{parent}/evolutions/{NN}-{slug}/

Review:
  cat .blast/specs/{parent}/evolutions/{NN}-{slug}/evolution.md

Approve & implement:
  /blast:approve {parent}-evo-{NN} evolution
  /blast:impl {parent}-evo-{NN}

After implementation, merge delta into parent:
  /blast:complete {parent}-evo-{NN}
```

### Note about evolution-specific approval

Evolutions use **simplified approval gate** — single approval (`evolution`) zamiast trzech (requirements/design/tasks). Bo delta jest unifikowany dokument, nie phased pipeline.

`/blast:approve {feature_name} evolution` ustawia `approvals.evolution.approved = true`.

`/blast:impl` na evolution sprawdza `approvals.evolution.approved` zamiast `approvals.tasks.approved`.

## Safety & Fallback

### Spec-evolve-agent returned escalation

Jeśli agent stwierdzi że change description jest za duża/niejasny — wyświetl jego komunikat verbatim, exit. Nie generuj.

### Evolution conflict z istniejącą active evolution

Jeśli już istnieje evolution X dla tego samego parent z status=active która modyfikuje overlapping zakres — agent zwróci WARN. Display warn + recommendation (review tamtej first lub coordinate).

### Schema mismatch

Jeśli evolution spec.json ma inną strukturę niż init.json (różne approvals shape) — to design intencjonalny. Inne komendy (impl, complete) wykrywają evolution przez `parent_feature` field i obsługują appropriately.
