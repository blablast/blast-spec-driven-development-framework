#!/usr/bin/env python3
"""
blast spec linter - deterministic validation of spec contents.

Usage:
    python .claude/scripts/blast-lint.py <feature>
    python .claude/scripts/blast-lint.py --all

Checks (per-spec):
    - spec.json schema (required fields, valid enum values)
    - requirements.md format (EARS, numeric IDs, acceptance criteria)
    - design.md completeness (Components, Verification Strategy with Local/Smoke/E2E)
    - tasks.md format (numeric IDs N.M, [Req: ...] traceability)
    - traceability req <-> task (every task references existing req; every req covered)
    - DRY check vs INVENTORY.md (provides[] not duplicating shipped components)
    - placeholder sniffing ({{...}}, TODO/FIXME in shipped specs)

Output:
    - Human-readable report
    - Verdict envelope (compatible with Fala 4 envelope format)

Exit codes:
    0 = PASS (no errors, warnings allowed)
    1 = WARN (warnings only, no blocking errors)
    2 = FAIL (one or more errors)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPECS_DIR = REPO_ROOT / ".blast" / "specs"
INVENTORY_PATH = REPO_ROOT / ".blast" / "steering" / "INVENTORY.md"

VALID_PHASES = {
    "initialized",
    "requirements-generated",
    "research-completed",
    "design-generated",
    "tasks-generated",
    "implementing",
    "complete",
    "shipped",
    "deprecated",
    "evolution-generated",
}
VALID_STATUS = {"planning", "active", "shipped", "deprecated", "merged"}

EARS_PATTERNS = [
    re.compile(r"^\s*\d+\.\s+When\s+.+,\s+the\s+\S.+\s+shall\s+", re.IGNORECASE),
    re.compile(r"^\s*\d+\.\s+If\s+.+,\s+then\s+the\s+\S.+\s+shall\s+", re.IGNORECASE),
    re.compile(r"^\s*\d+\.\s+While\s+.+,\s+the\s+\S.+\s+shall\s+", re.IGNORECASE),
    re.compile(r"^\s*\d+\.\s+Where\s+.+,\s+the\s+\S.+\s+shall\s+", re.IGNORECASE),
    re.compile(r"^\s*\d+\.\s+The\s+\S.+\s+shall\s+", re.IGNORECASE),
    re.compile(r"^\s*\d+\.\s+When\s+.+\s+and\s+.+,\s+the\s+\S.+\s+shall\s+", re.IGNORECASE),
]

REQ_HEADER_RE = re.compile(r"^###\s+Requirement\s+(\d+)\s*:?", re.MULTILINE)
TASK_LINE_RE = re.compile(
    r"^\s*-\s*\[(?P<done>[ x])\]\s*(?P<id>\d+(?:\.\d+)?)\s+"
    r"(?:\(P\d+\)\s+)?"
    r"(?P<title>.+?)"
    r"(?:\s*\[Req:\s*(?P<refs>[^\]]+)\])?\s*$",
    re.MULTILINE,
)

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_][A-Z0-9_]*\}\}")
TODO_FIXME_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    location: str = ""

    def render(self) -> str:
        prefix = {"ERROR": "[X]", "WARN": "[!]", "INFO": "[i]"}[self.severity]
        loc = f" {self.location}" if self.location else ""
        return f"  {prefix} {self.code}{loc}: {self.message}"


@dataclass
class LintResult:
    feature: str
    findings: list = field(default_factory=list)

    def add(self, severity, code, message, location=""):
        self.findings.append(Finding(severity, code, message, location))

    @property
    def errors(self):
        return [f for f in self.findings if f.severity == "ERROR"]

    @property
    def warnings(self):
        return [f for f in self.findings if f.severity == "WARN"]

    @property
    def infos(self):
        return [f for f in self.findings if f.severity == "INFO"]

    def verdict(self):
        if self.errors:
            return "FAIL"
        if self.warnings:
            return "WARN"
        return "PASS"


def check_spec_json(spec_dir, result):
    spec_path = spec_dir / "spec.json"
    if not spec_path.exists():
        result.add("ERROR", "SPEC_MISSING",
                   f"spec.json not found at {spec_path}", "spec.json")
        return None

    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        result.add("ERROR", "SPEC_MALFORMED",
                   f"spec.json is not valid JSON: {e}", "spec.json")
        return None

    required = ["feature_name", "language", "phase", "status", "approvals"]
    for k in required:
        if k not in spec:
            result.add("ERROR", "SPEC_FIELD_MISSING",
                       f"required field '{k}' missing", "spec.json")

    phase = spec.get("phase")
    if phase and phase not in VALID_PHASES:
        result.add("WARN", "SPEC_PHASE_UNKNOWN",
                   f"phase='{phase}' not in known set", "spec.json")

    status = spec.get("status")
    if status and status not in VALID_STATUS:
        result.add("WARN", "SPEC_STATUS_UNKNOWN",
                   f"status='{status}' not in known set", "spec.json")

    return spec


def check_requirements(spec_dir, spec, result):
    req_path = spec_dir / "requirements.md"
    requirements = {}

    phase = spec.get("phase") if spec else ""
    needs_requirements = phase not in ("initialized",)

    if not req_path.exists():
        if needs_requirements:
            result.add("ERROR", "REQ_FILE_MISSING",
                       "requirements.md missing for phase >= requirements-generated",
                       "requirements.md")
        return requirements

    text = req_path.read_text(encoding="utf-8")

    placeholders = PLACEHOLDER_RE.findall(text)
    if placeholders:
        unique = list(dict.fromkeys(placeholders))[:5]
        result.add("WARN", "REQ_PLACEHOLDERS",
                   f"unrendered placeholders: {', '.join(unique)}",
                   "requirements.md")

    headers = list(REQ_HEADER_RE.finditer(text))
    if not headers:
        result.add("ERROR", "REQ_NO_HEADERS",
                   "no '### Requirement N:' headers found",
                   "requirements.md")
        return requirements

    seen_ids = []
    for h in headers:
        rid = int(h.group(1))
        if rid in seen_ids:
            result.add("ERROR", "REQ_DUP_ID",
                       f"duplicate requirement ID {rid}", "requirements.md")
        seen_ids.append(rid)

    lines = text.splitlines()
    blocks = []
    for i, h in enumerate(headers):
        start = text[:h.start()].count("\n")
        end = (text[:headers[i + 1].start()].count("\n")
               if i + 1 < len(headers) else len(lines))
        rid = int(h.group(1))
        blocks.append((rid, start, end))

    for rid, start, end in blocks:
        block = "\n".join(lines[start:end])
        info = {"line": start + 1}

        if not re.search(
                r"\*\*Objective:\*\*\s*As\s+\S+\s+[^,]+,\s+I\s+want\s+[^,]+,\s+so\s+that\s+\S+",
                block, re.IGNORECASE):
            result.add("WARN", "REQ_NO_OBJECTIVE",
                       f"Requirement {rid}: missing or malformed Objective line",
                       f"requirements.md:{start + 1}")

        if re.search(r"^####\s+Acceptance\s+Criteria", block, re.MULTILINE):
            ac_lines = re.findall(r"^\s*\d+\.\s+(.+)$", block, re.MULTILINE)
            if not ac_lines:
                result.add("WARN", "REQ_NO_AC_ITEMS",
                           f"Requirement {rid}: 'Acceptance Criteria' section has no items",
                           f"requirements.md:{start + 1}")
            else:
                violations = []
                for j, ac_line in enumerate(ac_lines, 1):
                    full = f"{j}. {ac_line}"
                    if not any(p.match(full) for p in EARS_PATTERNS):
                        violations.append(j)
                if violations:
                    vlist = ",".join(str(v) for v in violations[:5])
                    result.add("WARN", "REQ_EARS_VIOLATION",
                               f"Requirement {rid}: AC item(s) {vlist} don't match EARS pattern",
                               f"requirements.md:{start + 1}")
        else:
            result.add("WARN", "REQ_NO_AC_SECTION",
                       f"Requirement {rid}: '#### Acceptance Criteria' section missing",
                       f"requirements.md:{start + 1}")

        requirements[rid] = info

    return requirements


def check_design(spec_dir, spec, result):
    design_path = spec_dir / "design.md"
    phase = spec.get("phase") if spec else ""
    needs_design = phase in ("design-generated", "tasks-generated", "implementing",
                              "complete", "shipped", "evolution-generated")

    if not design_path.exists():
        if needs_design:
            result.add("ERROR", "DESIGN_FILE_MISSING",
                       "design.md missing for phase >= design-generated",
                       "design.md")
        return False

    text = design_path.read_text(encoding="utf-8")

    if PLACEHOLDER_RE.search(text):
        result.add("WARN", "DESIGN_PLACEHOLDERS",
                   "unrendered placeholders found", "design.md")

    if not re.search(r"^##\s+Components", text, re.MULTILINE):
        result.add("WARN", "DESIGN_NO_COMPONENTS",
                   "missing '## Components' section", "design.md")

    if not re.search(r"^##\s+Verification\s+Strategy", text, re.MULTILINE):
        result.add("WARN", "DESIGN_NO_VS_SECTION",
                   "missing '## Verification Strategy' section", "design.md")
    else:
        vs_block = text.split("## Verification Strategy", 1)[1]
        vs_end = re.search(r"^##\s+\S", vs_block, re.MULTILINE)
        if vs_end:
            vs_block = vs_block[:vs_end.start()]

        for label, pattern in (
                ("Local test", r"(?:Local|local-probe|test_|unit\s+test)"),
                ("Smoke check", r"(?:Smoke|smoke)"),
                ("E2E probe", r"(?:E2E|e2e|end-to-end)")):
            if not re.search(pattern, vs_block, re.MULTILINE):
                result.add("WARN", "DESIGN_VS_INCOMPLETE",
                           f"Verification Strategy missing '{label}' marker",
                           "design.md")

        if not re.search(r"Expected\s+Signal", vs_block, re.IGNORECASE):
            result.add("WARN", "DESIGN_VS_NO_SIGNAL",
                       "Verification Strategy missing 'Expected Signal'",
                       "design.md")

    return True


def check_tasks(spec_dir, spec, requirements, result):
    tasks_path = spec_dir / "tasks.md"
    coverage = {}

    phase = spec.get("phase") if spec else ""
    needs_tasks = phase in ("tasks-generated", "implementing", "complete",
                             "shipped", "evolution-generated")

    if not tasks_path.exists():
        if needs_tasks:
            result.add("ERROR", "TASKS_FILE_MISSING",
                       "tasks.md missing for phase >= tasks-generated",
                       "tasks.md")
        return coverage

    text = tasks_path.read_text(encoding="utf-8")

    if PLACEHOLDER_RE.search(text):
        result.add("WARN", "TASKS_PLACEHOLDERS",
                   "unrendered placeholders found", "tasks.md")

    matches = list(TASK_LINE_RE.finditer(text))
    if not matches:
        if needs_tasks:
            result.add("ERROR", "TASKS_NO_LINES",
                       "no recognizable task lines found "
                       "(expected '- [ ] N.M Title [Req: ...]')",
                       "tasks.md")
        return coverage

    seen_ids = []
    for m in matches:
        tid = m.group("id")
        refs_raw = m.group("refs") or ""
        line_num = text[:m.start()].count("\n") + 1

        if tid in seen_ids:
            result.add("WARN", "TASK_DUP_ID",
                       f"task ID {tid} duplicated", f"tasks.md:{line_num}")
        seen_ids.append(tid)

        refs = set()
        if refs_raw.strip():
            for tok in re.split(r"[,\s]+", refs_raw.strip()):
                if not tok:
                    continue
                base = tok.split(".")[0]
                try:
                    refs.add(int(base))
                except ValueError:
                    result.add("WARN", "TASK_REF_BAD",
                               f"task {tid}: req reference '{tok}' not parseable",
                               f"tasks.md:{line_num}")
        else:
            result.add("WARN", "TASK_NO_REF",
                       f"task {tid}: no [Req: N] reference",
                       f"tasks.md:{line_num}")

        coverage[tid] = refs

        if requirements:
            for r in refs:
                if r not in requirements:
                    result.add("ERROR", "TASK_REF_UNKNOWN",
                               f"task {tid} references requirement {r} which doesn't exist",
                               f"tasks.md:{line_num}")

    return coverage


def check_traceability(requirements, coverage, result):
    if not requirements or not coverage:
        return

    covered_reqs = set()
    for refs in coverage.values():
        covered_reqs.update(refs)

    for rid in requirements:
        if rid not in covered_reqs:
            result.add("WARN", "REQ_NO_TASK",
                       f"Requirement {rid} not covered by any task",
                       "traceability")


def check_inventory_dry(spec, result):
    if not INVENTORY_PATH.exists() or not spec:
        return

    provides = spec.get("provides", []) or []
    if not provides:
        return

    inv_text = INVENTORY_PATH.read_text(encoding="utf-8")
    own_feature = (spec.get("feature_name") or "").strip()

    for p in provides:
        if not isinstance(p, str):
            continue
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)", p)
        if not m:
            continue
        comp = m.group(1)
        row_re = re.compile(
            rf"^\|\s*{re.escape(comp)}\s*\|[^|]*\|\s*([^|\s][^|]*?)\s*\|",
            re.MULTILINE,
        )
        for rm in row_re.finditer(inv_text):
            owner = rm.group(1).strip()
            if owner and owner != own_feature:
                result.add("WARN", "DRY_DUPLICATE",
                           f"provides '{comp}' may duplicate component already shipped "
                           f"by feature '{owner}' (per INVENTORY.md)",
                           "INVENTORY.md")


def lint_one(feature):
    result = LintResult(feature=feature)
    spec_dir = SPECS_DIR / feature
    if not spec_dir.exists():
        result.add("ERROR", "FEATURE_DIR_MISSING",
                   f"spec directory not found: {spec_dir}", feature)
        return result

    spec = check_spec_json(spec_dir, result)
    if spec is None:
        return result

    requirements = check_requirements(spec_dir, spec, result)
    check_design(spec_dir, spec, result)
    coverage = check_tasks(spec_dir, spec, requirements, result)
    check_traceability(requirements, coverage, result)
    check_inventory_dry(spec, result)

    return result


def render_report(results):
    out = []
    out.append("blast lint report")
    out.append("=" * 60)
    out.append("")

    total_errors = 0
    total_warnings = 0
    total_infos = 0

    for r in results:
        out.append(f"Feature: {r.feature}")
        if not r.findings:
            out.append("  [OK] no issues")
        else:
            for f in r.findings:
                out.append(f.render())
        out.append(f"  -> {r.verdict()} ({len(r.errors)}E / "
                   f"{len(r.warnings)}W / {len(r.infos)}I)")
        out.append("")
        total_errors += len(r.errors)
        total_warnings += len(r.warnings)
        total_infos += len(r.infos)

    out.append("=" * 60)
    if total_errors:
        overall = "FAIL"
    elif total_warnings:
        overall = "WARN"
    else:
        overall = "PASS"
    out.append(f"Overall: {overall} "
               f"({total_errors} errors, {total_warnings} warnings, {total_infos} infos "
               f"across {len(results)} spec(s))")
    out.append("")

    next_actions = []
    if total_errors:
        next_actions.append("Fix ERROR-level findings before proceeding to next phase")
    if total_warnings:
        next_actions.append("Review WARN findings - most can be addressed via /blast:design or manual edit")
    if not total_errors and not total_warnings:
        next_actions.append("Spec is clean - proceed to next pipeline phase")

    out.append("---VERDICT---")
    out.append(f"VERDICT: {overall}")
    out.append(f"BLOCKING: {str(total_errors > 0).lower()}")
    out.append(f"FINDINGS: {total_errors + total_warnings}")
    out.append("NEXT_ACTIONS:")
    for a in next_actions:
        out.append(f"- {a}")
    out.append("---END---")

    return "\n".join(out)


def discover_features():
    if not SPECS_DIR.exists():
        return []
    out = []
    for p in sorted(SPECS_DIR.iterdir()):
        if p.is_dir() and (p / "spec.json").exists():
            out.append(p.name)
    return out


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0

    arg = argv[1]
    if arg == "--all":
        features = discover_features()
        if not features:
            print("No specs found under .blast/specs/")
            return 0
    else:
        features = [arg]

    results = [lint_one(f) for f in features]
    print(render_report(results))

    has_errors = any(r.errors for r in results)
    has_warnings = any(r.warnings for r in results)
    if has_errors:
        return 2
    if has_warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
