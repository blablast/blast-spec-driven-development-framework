#!/usr/bin/env python3
"""
blast lint gate — PreToolUse hook for Claude Code.

Runs the deterministic spec linter (blast-lint.py) before spawning gated blast
subagents. Zero-token, <1s. Blocks (exit 2) ONLY on lint ERROR-level findings
(lint exit code 2). WARN-level findings are echoed but never block.

Rationale (SOTA proposal 1.3 + 4.4): only deterministic checks may block the
pipeline. This gate removes the need for an LLM to re-verify EARS format,
numeric IDs, and req<->task traceability on every phase transition.

Gated agents (same set as blast-approval-gate.py):
  spec-design-agent, spec-tasks-agent, spec-tdd-impl-agent

Bypasses:
  - subagent not in gated list
  - prompt contains "Lint-bypass: true" (escape hatch for intentional WIP runs)
  - spec-tiny-agent / spec.json.tiny == true (tiny specs are exempt)
  - linter script missing or crashes -> allow by default, but LOUDLY (the gate's
    guardian is absent; a silent allow-all reads like a passing gate). Set
    BLAST_LINT_STRICT=1 (CI / autonomous runs) to turn a missing/broken linter
    into a hard block instead — fail closed where correctness matters.

Exit codes: 0 = allow, 2 = block.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

GATED_AGENTS = {"spec-design-agent", "spec-tasks-agent", "spec-tdd-impl-agent"}
BYPASS_MARKER = "Lint-bypass: true"
TINY_AGENT = "spec-tiny-agent"
# Fail-closed switch: in CI / autonomous pipelines a missing linter is a
# misconfiguration, not a normal condition — block rather than wave the run through.
STRICT = os.environ.get("BLAST_LINT_STRICT", "").strip().lower() in ("1", "true", "yes")


def log_missing_guardian(what: str, detail: str) -> int:
    """Report an absent/broken linter. Block in strict mode, else loud-allow."""
    if STRICT:
        print(
            f"\n[blast-lint-gate] HARD BLOCK (BLAST_LINT_STRICT)\n"
            f"Deterministic lint guardian unavailable: {what}\n  {detail}\n"
            f"  In strict mode the gate fails CLOSED. Install/repair blast-lint.py "
            f"or unset BLAST_LINT_STRICT for interactive work.\n",
            file=sys.stderr,
        )
        return 2
    print(
        f"\n[blast-lint-gate] ⚠ LINT GATE INACTIVE — {what}\n"
        f"  {detail}\n"
        f"  Spawning subagent WITHOUT deterministic lint. This is NOT a pass.\n"
        f"  Set BLAST_LINT_STRICT=1 to fail closed in CI/autonomous runs.\n",
        file=sys.stderr,
    )
    return 0


def log_warn(msg):
    print(f"[blast-lint-gate] WARN: {msg}", file=sys.stderr)


def find_project_root(cwd: str) -> Path:
    root = Path(cwd or ".")
    if (root / ".blast" / "specs").exists():
        return root
    # Hook lives in .claude/hooks/ — project root is 3 parents up
    return Path(__file__).resolve().parent.parent.parent


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        event = json.loads(raw)
    except Exception as e:
        log_warn(f"could not parse hook event ({e}); allowing")
        return 0

    if event.get("tool_name", "") not in ("Agent", "Task"):
        return 0

    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0

    subagent_type = tool_input.get("subagent_type") or ""
    prompt = tool_input.get("prompt") or ""

    if subagent_type == TINY_AGENT or subagent_type not in GATED_AGENTS:
        return 0
    if BYPASS_MARKER in prompt:
        return 0

    m = re.search(r"^Feature:\s*([A-Za-z0-9._-]+)\s*$", prompt, re.MULTILINE)
    if not m:
        return 0  # approval gate already enforces the prompt header contract

    feature = m.group(1)
    root = find_project_root(event.get("cwd") or ".")

    spec_path = root / ".blast" / "specs" / feature / "spec.json"
    try:
        if spec_path.exists():
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            if spec.get("tiny") is True:
                return 0
    except Exception:
        pass  # malformed spec.json is the linter's job to report

    linter = root / ".claude" / "scripts" / "blast-lint.py"
    if not linter.exists():
        return log_missing_guardian("blast-lint.py not found", f"expected at {linter}")

    try:
        result = subprocess.run(
            [sys.executable, str(linter), feature],
            capture_output=True, text=True, timeout=30, cwd=str(root),
        )
    except Exception as e:
        return log_missing_guardian("linter failed to run", str(e))

    if result.returncode == 2:
        errors = [
            line for line in result.stdout.splitlines()
            if line.strip().startswith("[X]")
        ]
        details = "\n".join(f"  {e.strip()}" for e in errors[:10]) or "  (see /blast:lint output)"
        print(
            f"\n[blast-lint-gate] HARD BLOCK\n"
            f"Deterministic lint FAIL for feature '{feature}' — {subagent_type} not spawned.\n"
            f"{details}\n\n"
            f"  Fix:    resolve ERROR findings, see `/blast:lint {feature}`\n"
            f"  Bypass: add 'Lint-bypass: true' to the agent prompt (intentional WIP only)\n",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[blast-lint-gate] ERROR: unhandled exception ({e}); allowing", file=sys.stderr)
        sys.exit(0)
