---
description: "Cross-spec dependency graph + status dashboard — wszystkie specy w jednym widoku"
allowed-tools: Read, Glob, Bash
argument-hint: [feature-name]  (no arg = all specs; with arg = focused on that feature + neighbors)
---

# blast:graph — Status klastra specy

Pokazuje ASCII graph + tabelę wszystkich specy w `.blast/specs/`. Bez wywoływania subagenta — czysta analiza JSON. Szybkie (<1s).

## Parse Arguments

Parse `$ARGUMENTS`:
- Empty → mode = `all` (pokaż wszystkie specy)
- Single token (kebab-case) → mode = `focused`, target = ten feature + jego dependencies + dependents

## Execution

Use Bash tool to run the standalone graph script:

```bash
# Run the standalone graph script (reads .blast/specs/, renders status + graph).
# Optional argument: feature name for focused view.
python .claude/scripts/blast-graph.py {ARGUMENT}
```

## Safety & Fallback

- **Brak `.blast/specs/`**: graceful "no specs yet" message
- **Malformed spec.json**: skip + warn that one (don't crash whole report)
- **Empty argument**: show all
- **Invalid argument**: list available + exit
