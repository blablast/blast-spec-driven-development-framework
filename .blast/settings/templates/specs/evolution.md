# Evolution Document

> **Delta-spec format**. Opisuje TYLKO zmiany względem parent specu — nie powtarza całej zawartości parenta. Read parent first przy review.

## Parent Reference

- **Parent feature**: `{{PARENT_FEATURE}}`
- **Parent status at evolution start**: shipped (validated by `/blast:evolve` gate)
- **Evolution number**: {{EVOLUTION_N}} of {{PARENT_FEATURE}}
- **Evolution type**: {{EVOLUTION_TYPE}} — one of: `additive` / `breaking` / `refactor` / `bugfix`
- **Reason for evolution**: {{EVOLUTION_REASON}}

## Summary

2-4 zdania: co dokładnie się zmienia i dlaczego. Reviewer powinien rozumieć **zakres** bez czytania reszty.

---

## Requirements Changes

### ADDED
<!-- Nowe requirements — które nie były w parent. Numeracja kontynuuje parent's IDs. -->
<!-- Format: numeric ID > parent's max ID -->

#### Requirement {{NEXT_ID}}: {{NEW_REQUIREMENT_AREA}}
**Objective:** As a {{ROLE}}, I want {{CAPABILITY}}, so that {{BENEFIT}}

##### Acceptance Criteria
1. When [event], the [system] shall [response/action]

<!-- Repeat for each new requirement -->

### MODIFIED
<!-- Existing requirements które są zmieniane. Cytuj parent's ID + co się zmienia. -->

#### Requirement {{PARENT_REQ_ID}}: {{REQUIREMENT_AREA}} — MODIFIED
**Original** (parent):
> {{ORIGINAL_TEXT}}

**Updated**:
{{UPDATED_TEXT}}

**Rationale**: {{WHY_CHANGED}}

### REMOVED
<!-- Existing requirements które są usuwane. Wymień ID + uzasadnienie. -->

- Requirement {{PARENT_REQ_ID}}: {{TITLE}} — **REMOVED**
  - **Rationale**: {{WHY_REMOVED}}
  - **Migration**: {{HOW_USERS_HANDLE_REMOVAL}}

---

## Design Changes

### ADDED
<!-- Nowe komponenty / interfaces / flows. -->

#### Component: {{NEW_COMPONENT_NAME}} ({{path}})
- **Intent**: {{purpose}}
- **Req Coverage**: {{req_id}}
- **Dependencies**: {{deps}}
- **Contracts**: {{interfaces}}

### MODIFIED
<!-- Existing components z parent design.md które się zmieniają. -->

#### Component: {{EXISTING_COMPONENT}} — MODIFIED
**Original signature/contract**:
```
{{ORIGINAL_INTERFACE}}
```

**New signature/contract**:
```
{{NEW_INTERFACE}}
```

**Backward compat**: ☐ breaking / ☐ deprecation path provided / ☐ fully compatible
**Migration steps**: {{IF_BREAKING}}

### REMOVED

- Component: {{COMPONENT_NAME}} — **REMOVED**
  - **Replacement**: {{NEW_COMPONENT_OR_REASON}}
  - **Files to delete**: {{file paths}}

### Verification Strategy Update

(Tylko jeśli zmiana wymaga update'u verification commands z parent design.md.)

- **Local test command**: {{NEW_OR_UNCHANGED}}
- **Smoke check**: {{NEW_OR_UNCHANGED}}
- **E2E probe**: {{NEW_OR_UNCHANGED}}
- **Expected signal**: {{NEW_OR_UNCHANGED}}

---

## Tasks Changes

### ADDED
<!-- Nowe taski — kontynuują numerację parent'a. Apply (P) markers per tasks-generation rules. -->

- [ ] {{NEXT_TASK_ID}} {{TASK_TITLE}}  [Req: {{req_ids}}]
- [ ] {{NEXT_TASK_ID}} (P) {{TASK_TITLE}}  [Req: {{req_ids}}]

### MODIFIED
<!-- Existing tasks które trzeba przerobić — np. logic change. Cytuj parent ID. -->

- {{PARENT_TASK_ID}} — **MODIFIED**: {{WHAT_CHANGES}}

### REMOVED

- {{PARENT_TASK_ID}} — **REMOVED**: {{REASON}}

---

## Migration Notes

(Wymagane dla `breaking` evolution_type. Opcjonalne dla `additive` / `refactor` / `bugfix`.)

### Data migration

- Schema changes: {{IF_ANY}}
- Backfill strategy: {{IF_NEEDED}}
- Rollback plan: {{IF_REQUIRED}}

### Deployment sequence

1. {{STEP_1}}
2. {{STEP_2}}

### User-facing changes

- API consumers: {{COMMUNICATION_STRATEGY}}
- Documentation updates: {{LIST}}

---

## Cross-spec impact

(Czy ta evolution wpływa na inne shipped specy?)

| Affected spec | Impact | Required action |
|---|---|---|
| {{spec_name}} | {{description}} | {{action}} |

---

## Approval

- [ ] Parent spec status verified `shipped` (by `/blast:evolve` gate)
- [ ] Reviewer reviewed delta against parent context
- [ ] Migration plan reviewed (if breaking)
