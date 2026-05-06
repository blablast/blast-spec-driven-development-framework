---
description: "Spec linter — deterministyczny check EARS / IDs / traceability / V.S. quality"
allowed-tools: Bash, Read
argument-hint: [feature-name | --all]
---

# blast:lint — Deterministyczny linter speców

Pure-Python check: `spec.json` schema, EARS format wymagań, numeric IDs, traceability req↔task, design completeness (`## Components`, `## Verification Strategy` z Local/Smoke/E2E), DRY vs INVENTORY. Bez subagenta. Szybkie (<1s).

## Parse Arguments

Parse `$ARGUMENTS`:
- Empty → ERROR: brakuje argumentu. Pokaż usage.
- `--all` → lintuj wszystkie spece w `.blast/specs/`
- Single token (kebab-case) → lintuj ten feature

## Execution

Use Bash tool to run the linter script:

```bash
python3 .claude/scripts/blast-lint.py {ARGUMENT}
```

Skrypt sam:
- Wypisuje human-readable raport (per-feature findings z severity)
- Kończy verdict envelope (`---VERDICT--- ... ---END---`)
- Zwraca exit code: `0` PASS, `1` WARN, `2` FAIL

## Output Interpretation

Raport ma 3 poziomy:
- `[X]` ERROR — twardy problem, blokujący (FAIL)
- `[!]` WARN — soft issue, do review (WARN jeśli jedyne; nie blokuje)
- `[i]` INFO — wskazówka (placeholders, TODOs)

Lint codes (stable, dla automatyzacji / CI):

| Kod | Co znaczy |
|---|---|
| `SPEC_MISSING` | brak `spec.json` |
| `SPEC_MALFORMED` | `spec.json` to nie jest valid JSON |
| `SPEC_FIELD_MISSING` | brakuje wymaganego pola (feature_name/language/phase/status/approvals) |
| `SPEC_PHASE_UNKNOWN` / `SPEC_STATUS_UNKNOWN` | wartość poza znanym setem |
| `REQ_FILE_MISSING` | brak `requirements.md` dla phase >= requirements-generated |
| `REQ_NO_HEADERS` | brak `### Requirement N:` headerów |
| `REQ_DUP_ID` | duplikat ID wymagania |
| `REQ_NO_OBJECTIVE` | brak/zniekształcony `**Objective:** As a X, I want Y, so that Z` |
| `REQ_NO_AC_SECTION` | brak `#### Acceptance Criteria` |
| `REQ_NO_AC_ITEMS` | sekcja jest, ale pusta |
| `REQ_EARS_VIOLATION` | AC item nie pasuje do żadnego EARS pattern |
| `REQ_PLACEHOLDERS` | nieuzupełnione `{{...}}` |
| `REQ_NO_TASK` | wymaganie nie ma żadnego pokrywającego taska |
| `DESIGN_FILE_MISSING` | brak `design.md` dla phase >= design-generated |
| `DESIGN_NO_COMPONENTS` | brak `## Components` |
| `DESIGN_NO_VS_SECTION` | brak `## Verification Strategy` |
| `DESIGN_VS_INCOMPLETE` | V.S. nie ma Local/Smoke/E2E |
| `DESIGN_VS_NO_SIGNAL` | V.S. nie ma `Expected Signal` |
| `TASKS_FILE_MISSING` | brak `tasks.md` dla phase >= tasks-generated |
| `TASKS_NO_LINES` | brak rozpoznawalnych task lines |
| `TASK_DUP_ID` | duplikat ID taska |
| `TASK_NO_REF` | task bez `[Req: N]` |
| `TASK_REF_BAD` | reference niemożliwy do parsowania |
| `TASK_REF_UNKNOWN` | task referuje requirement którego nie ma |
| `DRY_DUPLICATE` | `provides[]` duplikuje komponent z innej feature (per INVENTORY.md) |

## Verdict Envelope

Po raporcie skrypt drukuje:

```
---VERDICT---
VERDICT: PASS|WARN|FAIL
BLOCKING: true|false
FINDINGS: <count>
NEXT_ACTIONS:
- ...
---END---
```

Format zgodny z Falą 4 verdict envelope — można pipe'ować do innych narzędzi.

## Examples

```bash
# Pojedynczy feature
/blast:lint auth-basic

# Wszystkie spece
/blast:lint --all
```

## Integration

Lint NIE jest automatycznie wpięty w pipeline (na razie). Możesz dodać manualnie:
- jako gate przed `/blast:design` — sprawdź że requirements są clean
- po `/blast:tasks` — sprawdź traceability przed implementacją
- w CI — `python3 .claude/scripts/blast-lint.py --all` przed merge

## Limitacje (świadome)

- Nie wykrywa **semantycznej** poprawności (czy AC ma sens) — tylko strukturalnej
- EARS pattern matching jest rygorystyczny: jeśli wymagasz custom format, edytuj `EARS_PATTERNS` w skrypcie
- DRY check jest naiwny — porównuje pierwsze identifiery z `provides[]` z `Component Registry` w INVENTORY.md
- Nie czyta evolution.md (delta-specy mają swoją strukturę — patrz `/blast:graph` dla audytu evolutions)

## Następny krok

Po PASS → dalej w pipeline (`/blast:design`, `/blast:tasks`, `/blast:impl`).
Po FAIL → fixuj ERROR findings → re-run.
Po WARN → review, fixuj manual lub akceptuj (`/blast:lint` jest informacyjny, nie blokuje pipeline'u).
