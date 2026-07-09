#!/usr/bin/env python3
"""
blast-secscan — deterministic Phase-1 security scanner (0 tokens, <2s).

Replaces the LLM "Sub-agent A: Static Pattern Scanner" in the security-audit
agent. Pure regex + dependency audit; emits the SAME findings JSON the agent's
sub-agent A used to produce, so downstream merge/threat-model steps are unchanged.

Two consumers:
  1. security-audit-agent Step 2 Phase 1 — runs this instead of spawning a Haiku
     sub-agent, then feeds the JSON into Sub-agent B/C context.
  2. /blast:complete Step 1b.5 gate — exit code gates the ship (CRITICAL = block).

Usage:
  blast-secscan.py --feature <name>     # scan feature's impl files (from design.md globs)
  blast-secscan.py --changed            # scan files changed vs merge-base (git)
  blast-secscan.py --all                # scan whole tree (excludes vendor/build dirs)
  blast-secscan.py <file> [<file> ...]  # scan explicit files
  blast-secscan.py --changed --json     # machine output only (default prints summary too)

Exit codes:
  0 = no CRITICAL findings
  2 = at least one CRITICAL finding (hardcoded secret, etc.) — gate should block
  1 = usage / internal error (fail-open for the agent path, fail-closed is the gate's call)

Findings JSON (stdout, always): array of
  {id, severity, category, file, line, description, impact, remediation}
Severities: CRITICAL | HIGH | MEDIUM | LOW
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# --- scope helpers -----------------------------------------------------------

CODE_EXT = {".py", ".js", ".ts", ".jsx", ".tsx"}
EXCLUDE_DIRS = {"node_modules", "__pycache__", ".venv", "venv", ".git", ".blast",
                "dist", "build", ".next", "coverage", "_to_delete"}
TESTY = re.compile(r"(^|/)(tests?|__tests__|spec|fixtures?|examples?|templates?)(/|$)|"
                   r"(test_|_test|\.test\.|\.spec\.)", re.IGNORECASE)


def is_test_or_template(path: str) -> bool:
    return bool(TESTY.search(path.replace("\\", "/")))


def iter_lines(path: Path):
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                yield i, line.rstrip("\n")
    except (OSError, UnicodeError):
        return


# --- pattern rules -----------------------------------------------------------
# Each rule: (compiled_regex, severity, category, description, impact, remediation, lang)
# lang: "py" | "js" | "any". Secret rules downgrade CRITICAL→LOW on test/template files.

PY_RULES = [
    (re.compile(r"""(password|passwd|secret|api_?key|token|access_?key)\s*=\s*['"][^'"]{3,}['"]""", re.I),
     "CRITICAL", "secrets", "Hardcoded credential literal",
     "Leaked secret grants attacker direct access", "Move to env/secret store: os.environ.get(...)", "py"),
    (re.compile(r"\beval\s*\("), "HIGH", "code-injection", "eval() on possibly untrusted input",
     "Arbitrary code execution", "Remove eval; parse explicitly or use ast.literal_eval", "py"),
    (re.compile(r"\bexec\s*\("), "HIGH", "code-injection", "exec() call",
     "Arbitrary code execution", "Avoid exec; redesign to explicit dispatch", "py"),
    (re.compile(r"\bpickle\.load[s]?\s*\("), "HIGH", "deserialization", "pickle.load on external data",
     "RCE via crafted pickle", "Use json or a safe schema; never unpickle untrusted bytes", "py"),
    (re.compile(r"\byaml\.load\s*\((?!.*Loader\s*=\s*yaml\.SafeLoader)"), "HIGH", "deserialization",
     "yaml.load without SafeLoader", "Object injection / RCE", "Use yaml.safe_load()", "py"),
    (re.compile(r"shell\s*=\s*True"), "HIGH", "command-injection", "subprocess with shell=True",
     "Shell/command injection", "Pass an argv list, shell=False; validate inputs", "py"),
    (re.compile(r"\bos\.system\s*\("), "HIGH", "command-injection", "os.system() call",
     "Command injection", "Use subprocess with an argv list", "py"),
    (re.compile(r"""f['"][^'"]*\b(SELECT|INSERT|UPDATE|DELETE)\b""", re.I), "HIGH", "sql-injection",
     "f-string SQL", "SQL injection", "Use parameterized queries / bound params", "py"),
    (re.compile(r"""\.format\s*\([^)]*\)\s*|['"][^'"]*\{[^}]*\}[^'"]*\b(SELECT|INSERT|UPDATE|DELETE)\b""", re.I),
     "MEDIUM", "sql-injection", "String-formatted SQL (possible)",
     "SQL injection if input untrusted", "Use parameterized queries", "py"),
]

JS_RULES = [
    (re.compile(r"""(password|api_?key|secret|token)\s*[:=]\s*['"][^'"]{3,}['"]""", re.I),
     "CRITICAL", "secrets", "Hardcoded credential literal",
     "Leaked secret grants attacker access", "Move to env/secret store", "js"),
    (re.compile(r"\beval\s*\("), "HIGH", "code-injection", "eval() call",
     "Arbitrary code execution", "Remove eval; use JSON.parse or explicit logic", "js"),
    (re.compile(r"\.innerHTML\s*="), "HIGH", "xss", "innerHTML assignment",
     "DOM XSS", "Use textContent or a sanitizer (DOMPurify)", "js"),
    (re.compile(r"dangerouslySetInnerHTML"), "HIGH", "xss", "dangerouslySetInnerHTML",
     "React XSS", "Sanitize HTML or avoid raw injection", "js"),
    (re.compile(r"document\.write\s*\("), "MEDIUM", "xss", "document.write()",
     "DOM XSS / injection", "Build DOM nodes explicitly", "js"),
    (re.compile(r"`[^`]*\$\{[^}]*\}[^`]*`.*\b(query|execute)\b|\b(query|execute)\b.*`[^`]*\$\{", re.I),
     "HIGH", "sql-injection", "Template-literal SQL", "SQL injection",
     "Use parameterized queries", "js"),
]


def lang_of(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".py":
        return "py"
    if ext in (".js", ".ts", ".jsx", ".tsx"):
        return "js"
    return "any"


def scan_file(path: Path, findings: list, counter: list):
    lang = lang_of(str(path))
    rules = PY_RULES if lang == "py" else JS_RULES if lang == "js" else []
    if not rules:
        return
    is_test = is_test_or_template(str(path))
    for lineno, line in iter_lines(path):
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("//"):
            continue
        for rx, sev, cat, desc, impact, remediation, _lang in rules:
            if rx.search(line):
                eff_sev = sev
                # secrets in tests/templates are almost always fixtures → downgrade, never block
                if cat == "secrets" and is_test:
                    eff_sev = "LOW"
                counter[0] += 1
                findings.append({
                    "id": f"SCAN-{counter[0]:03d}",
                    "severity": eff_sev,
                    "category": cat,
                    "file": str(path).replace("\\", "/"),
                    "line": lineno,
                    "description": desc,
                    "impact": impact,
                    "remediation": remediation,
                })
                break  # one finding per line is enough


# --- dependency audit --------------------------------------------------------

def which(cmd: str) -> bool:
    from shutil import which as _w
    return _w(cmd) is not None


def dep_audit(root: Path, findings: list, counter: list, notes: list):
    # Python
    if (root / "requirements.txt").exists() or (root / "pyproject.toml").exists():
        if which("pip-audit"):
            try:
                r = subprocess.run(["pip-audit", "-f", "json"], capture_output=True,
                                   text=True, timeout=120, cwd=str(root))
                data = json.loads(r.stdout or "{}")
                deps = data.get("dependencies", data) if isinstance(data, dict) else data
                for d in (deps or []):
                    for v in d.get("vulns", []) or []:
                        counter[0] += 1
                        findings.append({
                            "id": f"SCAN-{counter[0]:03d}", "severity": "HIGH",
                            "category": "dependency", "file": "requirements",
                            "line": 0,
                            "description": f"{d.get('name')} {d.get('version')}: {v.get('id')}",
                            "impact": "Known CVE in dependency",
                            "remediation": f"Upgrade to {', '.join(v.get('fix_versions', []) or ['a patched version'])}",
                        })
            except Exception as e:
                notes.append(f"pip-audit failed: {e}")
        else:
            notes.append("pip-audit not installed — Python dependency CVEs not checked")
    # JS
    if (root / "package.json").exists():
        if which("npm"):
            try:
                r = subprocess.run(["npm", "audit", "--json"], capture_output=True,
                                   text=True, timeout=120, cwd=str(root))
                data = json.loads(r.stdout or "{}")
                meta = (data.get("metadata", {}) or {}).get("vulnerabilities", {})
                crit = meta.get("critical", 0); high = meta.get("high", 0)
                if crit or high:
                    counter[0] += 1
                    findings.append({
                        "id": f"SCAN-{counter[0]:03d}",
                        "severity": "CRITICAL" if crit else "HIGH",
                        "category": "dependency", "file": "package.json", "line": 0,
                        "description": f"npm audit: {crit} critical, {high} high",
                        "impact": "Known CVEs in npm dependencies",
                        "remediation": "Run `npm audit fix` / upgrade affected packages",
                    })
            except Exception as e:
                notes.append(f"npm audit failed: {e}")
        else:
            notes.append("npm not installed — JS dependency CVEs not checked")


# --- scope resolution --------------------------------------------------------

def project_root() -> Path:
    p = Path.cwd()
    if (p / ".blast").exists():
        return p
    return Path(__file__).resolve().parent.parent.parent


def files_for_feature(root: Path, feature: str) -> list[Path]:
    """Best-effort: scan common source dirs; the agent narrows via design.md.
    We can't parse design.md deterministically, so scan the source tree and let
    the agent's deep-review sub-agent focus. Kept broad but vendor-excluded."""
    return files_all(root)


def files_changed(root: Path) -> list[Path]:
    """Union of everything 'in flight': committed vs the push base (upstream, else
    main), PLUS staged (--cached) PLUS unstaged. Missing any of these lets a secret
    slip through — e.g. a staged-but-uncommitted key at pre-push time."""
    def _git(*args) -> str:
        try:
            return subprocess.run(["git", *args], capture_output=True, text=True,
                                  cwd=str(root)).stdout
        except Exception:
            return ""
    try:
        # Prefer the upstream range (what a push would send); fall back to main; then HEAD~1.
        base = _git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}").strip()
        if not base:
            base = _git("merge-base", "HEAD", "main").strip() or "HEAD~1"
        ranged = _git("diff", "--name-only", f"{base}..HEAD")
        staged = _git("diff", "--cached", "--name-only")
        unstaged = _git("diff", "--name-only")
        names = set(filter(None, "\n".join([ranged, staged, unstaged]).splitlines()))
        return [root / n for n in names if os.path.splitext(n)[1].lower() in CODE_EXT
                and (root / n).exists()]
    except Exception:
        return files_all(root)


def files_all(root: Path) -> list[Path]:
    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in CODE_EXT:
                result.append(Path(dirpath) / fn)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--feature")
    ap.add_argument("--changed", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", action="store_true", help="suppress the human summary on stderr")
    args = ap.parse_args()

    root = project_root()
    if args.files:
        targets = [Path(f) for f in args.files]
    elif args.changed:
        targets = files_changed(root)
    elif args.feature:
        targets = files_for_feature(root, args.feature)
    elif args.all:
        targets = files_all(root)
    else:
        targets = files_changed(root)

    findings: list = []
    counter = [0]
    notes: list = []
    for t in targets:
        if t.exists() and t.is_file():
            scan_file(t, findings, counter)
    dep_audit(root, findings, counter, notes)

    # stdout: always the machine JSON (what the agent ingests)
    print(json.dumps(findings, indent=2))

    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in sev_order}
    if not args.json:
        print(
            f"[blast-secscan] {len(targets)} file(s) | "
            f"CRITICAL={counts['CRITICAL']} HIGH={counts['HIGH']} "
            f"MEDIUM={counts['MEDIUM']} LOW={counts['LOW']}",
            file=sys.stderr,
        )
        for n in notes:
            print(f"[blast-secscan] note: {n}", file=sys.stderr)

    return 2 if counts["CRITICAL"] > 0 else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print("[]")
        print(f"[blast-secscan] ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
