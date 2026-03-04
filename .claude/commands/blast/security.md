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

<background_information>
- **Mission**: Security audit — scan code for common vulnerabilities (OWASP Top 10, CWE Top 25), hardcoded secrets, unsafe patterns, and produce actionable report
- **Success Criteria**:
  - All source files scanned for security issues
  - Findings categorized by severity (Critical / High / Medium / Low)
  - Each finding includes location, description, and remediation
  - In fix mode: auto-fix what's safe to fix automatically
  - Security report saved to spec directory (or project root for --all)
</background_information>

<instructions>
## Core Task
Execute security audit on feature code (or entire codebase with `--all`). Scan for vulnerabilities, secrets, and unsafe patterns. Produce structured security report.

## Execution Steps

### Step 1: Determine Scope

**Feature-scoped** (default):
1. Read `.blast/specs/{feature}/design.md` — identify implementation files
2. Glob for feature source files and test files
3. Read `.blast/steering/structure.md` — understand project layout

**Codebase-scoped** (`--all`):
1. Read `.blast/steering/structure.md`
2. Glob for all source files (exclude node_modules, __pycache__, .venv, .git)

### Step 2: Load Security Rules

Read `.blast/settings/templates/steering-custom/security.md` for project security standards (if exists).

Use built-in security checklist (always applied):

**OWASP/CWE Categories**:
1. **Injection** (SQL, NoSQL, OS command, LDAP, XSS)
2. **Broken Authentication** (weak passwords, session management, token handling)
3. **Sensitive Data Exposure** (hardcoded secrets, unencrypted data, excessive logging)
4. **Broken Access Control** (missing authz checks, IDOR, privilege escalation)
5. **Security Misconfiguration** (debug mode, default credentials, verbose errors)
6. **Insecure Deserialization** (pickle, yaml.load, eval, exec)
7. **Dependency Vulnerabilities** (known CVEs in requirements.txt/package.json)
8. **Path Traversal** (unsanitized file paths, directory traversal)
9. **Cryptographic Issues** (weak algorithms, hardcoded keys, predictable randomness)
10. **Logging & Monitoring** (PII in logs, missing audit trail, excessive data)

### Step 3: Static Analysis — Automated Scans

Run available tools:

**Python**:
```bash
# Check for hardcoded secrets
grep -rn "password\s*=\s*['\"]" --include="*.py" || true
grep -rn "secret\s*=\s*['\"]" --include="*.py" || true
grep -rn "api_key\s*=\s*['\"]" --include="*.py" || true
grep -rn "token\s*=\s*['\"]" --include="*.py" || true

# Check for dangerous functions
grep -rn "eval(" --include="*.py" || true
grep -rn "exec(" --include="*.py" || true
grep -rn "pickle\.load" --include="*.py" || true
grep -rn "yaml\.load(" --include="*.py" || true
grep -rn "subprocess\.\(call\|run\|Popen\)" --include="*.py" || true
grep -rn "os\.system(" --include="*.py" || true
grep -rn "__import__(" --include="*.py" || true

# Check for SQL injection vectors
grep -rn "f\".*SELECT\|f\".*INSERT\|f\".*UPDATE\|f\".*DELETE" --include="*.py" || true
grep -rn "\.format.*SELECT\|\.format.*INSERT" --include="*.py" || true

# Check for path traversal
grep -rn "open(.*\+" --include="*.py" || true

# Dependency audit (if pip-audit available)
pip-audit 2>/dev/null || true
```

**JavaScript/TypeScript**:
```bash
# Hardcoded secrets
grep -rn "password\s*[:=]\s*['\"]" --include="*.{js,ts,jsx,tsx}" || true
grep -rn "apiKey\s*[:=]\s*['\"]" --include="*.{js,ts,jsx,tsx}" || true

# Dangerous patterns
grep -rn "eval(" --include="*.{js,ts,jsx,tsx}" || true
grep -rn "innerHTML\s*=" --include="*.{js,ts,jsx,tsx}" || true
grep -rn "dangerouslySetInnerHTML" --include="*.{js,ts,jsx,tsx}" || true
grep -rn "document\.write" --include="*.{js,ts,jsx,tsx}" || true

# SQL injection
grep -rn "query.*\`.*\$\{" --include="*.{js,ts,jsx,tsx}" || true

# Dependency audit
npm audit 2>/dev/null || true
```

### Step 4: Manual Code Review

Read each source file and check for:

1. **Input validation**: Are all inputs validated at boundaries?
2. **Output encoding**: Is output properly escaped for context (HTML, SQL, shell)?
3. **Authentication**: Are auth checks present before sensitive operations?
4. **Authorization**: Are permissions verified (not just authentication)?
5. **Error handling**: Do errors leak sensitive info? (stack traces, DB details)
6. **Secrets management**: Are secrets from env/config, not hardcoded?
7. **Cryptography**: Are algorithms current? (no MD5/SHA1 for security, no ECB mode)
8. **File operations**: Are paths validated? Open with minimal permissions?
9. **Dependencies**: Are imports from trusted sources? Pinned versions?
10. **Logging**: Is PII/secret data excluded from logs?

### Step 5: Generate Security Report

Create security report at:
- Feature-scoped: `.blast/specs/{feature}/security-report.md`
- Codebase-scoped: `.blast/steering/security-report.md`

Report format:
```markdown
# Security Audit Report

**Scope**: {feature-name} / Full Codebase
**Date**: {timestamp}
**Files Scanned**: {count}
**Findings**: {critical} Critical, {high} High, {medium} Medium, {low} Low

## Critical Findings
### [CRIT-001] {Title}
- **Category**: {OWASP category}
- **File**: `{path}:{line}`
- **Description**: What the vulnerability is
- **Impact**: What an attacker could do
- **Remediation**: How to fix it
- **Fixed**: Yes/No (in --fix mode)

## High Findings
...

## Medium Findings
...

## Low Findings
...

## Summary
- **Security Score**: {score}/10
- **Top Risks**: {list}
- **Recommendation**: {pass/fix-required/block-deployment}
```

### Step 6: Fix Mode (--fix)

If `--fix` flag:
1. Auto-fix safe issues:
   - Replace `yaml.load()` → `yaml.safe_load()`
   - Replace `pickle.load()` with warning comment
   - Add input validation stubs
   - Replace f-string SQL with parameterized queries (where pattern is clear)
   - Remove hardcoded secrets → replace with `os.environ.get("KEY")`
2. For issues requiring manual intervention: add `# SECURITY: TODO` comment with description
3. Re-run automated scans after fixes to verify

### Step 7: Verdict

Based on findings, output one of:
- **PASS** (0 Critical, 0 High): Safe to proceed
- **FIX REQUIRED** (0 Critical, >0 High): Fix high-severity issues before deployment
- **BLOCK** (>0 Critical): Critical vulnerabilities — must fix before proceeding. Recommend rolling back to impl phase.

</instructions>

## Tool Guidance
- **Grep**: Pattern matching for secrets, dangerous functions, injection vectors
- **Glob**: Find all source files in scope
- **Read**: Code review of individual files
- **Bash**: Run automated security tools (pip-audit, npm audit, grep patterns)
- **Edit**: Apply auto-fixes in --fix mode
- **Write**: Create security report
- **Task**: Parallel scanning of independent file groups (large codebases)

## Output Description

Provide output in the language specified in `spec.json` (or Polish for --all):

1. **Scope**: Feature name or "Full Codebase", files scanned count
2. **Findings Summary**: Critical/High/Medium/Low counts
3. **Top Issues**: Top 3 most severe findings (one line each)
4. **Verdict**: PASS / FIX REQUIRED / BLOCK
5. **Report Location**: Path to full security report
6. **Next Step**: Based on verdict — proceed or fix

**Format**: Concise (under 200 words)

## Safety & Fallback

### Error Scenarios

**Feature Not Found**:
- "Spec `{feature}` nie istnieje. Użyj `--all` dla całego codebase."

**No Source Files**:
- "Brak plików źródłowych do skanowania. Najpierw `/blast:impl {feature}`"

**Security Tools Not Available**:
- Fall back to grep-based scanning + manual review
- Note in report which automated tools were unavailable
