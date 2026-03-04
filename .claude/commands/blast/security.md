---
description: "Audyt bezpieczeństwa — skanuj kod pod kątem typowych luk i zagrożeń"
allowed-tools: Read, Bash, Glob, Grep, Edit, Write, Task
argument-hint: <feature-name | --all> [--fix]
---

# blast:security — Audyt bezpieczeństwa kodu

## Parse Arguments

Parse `$ARGUMENTS` as a single string:
- Split by spaces
- Extract flags: `--fix` (auto-fix what's possible), `--all` (scan entire codebase)
- Ignore unknown flags (tokens starting with `-` that aren't `--fix`/`--all`)
- Extract feature name (first non-flag token — kebab-case identifier)
- If no feature name and no `--all`: auto-detect (single active spec)

Examples:
```
"zoo-garden"           → feature=zoo-garden, fix=false
"zoo-garden --fix"     → feature=zoo-garden, fix=true
"--all"                → scope=all, fix=false
"--all --fix"          → scope=all, fix=true
```

**IMPORTANT**: `$ARGUMENTS` is a single string, NOT positional `$1`. Parse it yourself.

## Execution

Delegate the security audit to the **security-audit-agent** (`.claude/agents/blast/security.md`) using the Task tool.

**Construct agent prompt** with:
1. Feature name (or `--all` scope)
2. Fix mode flag
3. File path patterns to expand:
   - `.blast/steering/*.md`
   - `.blast/specs/{feature}/*.md` (if feature-scoped)
   - Source files based on steering/structure.md

**Launch agent**:
```
Task(security-audit-agent):
  Feature: {feature} | Scope: --all
  Fix mode: {yes/no}

  Execute full security audit following your protocol.
  File patterns to expand:
  - .blast/steering/*.md
  - .blast/specs/{feature}/*.md (if feature-scoped)
```

## Post-Agent

After agent returns:

1. **Display verdict** prominently: PASS / FIX REQUIRED / BLOCK
2. **Show report location**
3. **Suggest next step**:
   - PASS: "Kod jest bezpieczny. Kontynuuj pipeline."
   - FIX REQUIRED: "Popraw znalezione problemy lub uruchom `/blast:security {feature} --fix`"
   - BLOCK: "⛔ Krytyczne luki! Napraw PRZED wdrożeniem."

## Output

Provide concise summary (under 200 words) in the language from spec.json.
