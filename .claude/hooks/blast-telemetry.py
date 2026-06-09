#!/usr/bin/env python3
"""
blast telemetry hook - PostToolUse event sink for Agent/Task calls.

Appends one JSONL line per Agent/Task invocation to:
    .blast/logs/agent-runs.jsonl

Recorded data is META ONLY:
    - timestamp (UTC, ISO-8601)
    - tool_name (Agent | Task)
    - subagent_type
    - feature (extracted from prompt header if possible)
    - prompt_chars / result_chars (lengths only, not content)
    - verdict / blocking (parsed from verdict envelope in result if present)
    - gate_blocked (true when prior PreToolUse hook returned exit 2)

NEVER recorded:
    - prompt body
    - result body
    - any user PII

Defensive posture:
    - All errors -> stderr log, exit 0 (never block user workflow)
    - Missing fields -> graceful skip
    - Disk-full / permission errors -> log only

Usage (registered in .claude/settings.json):
    {
      "hooks": {
        "PostToolUse": [{
          "matcher": "^(Agent|Task)$",
          "hooks": [{"type": "command", "command": "python3 .claude/hooks/blast-telemetry.py"}]
        }]
      }
    }
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

LOG_DIR_NAME = ".blast/logs"
LOG_FILE_NAME = "agent-runs.jsonl"

VERDICT_RE = re.compile(
    r"---VERDICT---\s*\n"
    r"VERDICT:\s*(?P<verdict>PASS|WARN|FAIL)\s*\n"
    r"BLOCKING:\s*(?P<blocking>true|false)",
    re.IGNORECASE | re.MULTILINE,
)
FINDINGS_RE = re.compile(r"^FINDINGS:\s*(\d+)", re.IGNORECASE | re.MULTILINE)
# Escalation accounting block emitted by spec-tdd-impl-agent (Forge)
ESCALATION_RE = re.compile(
    r"Qwen delegated successfully:\s*(?P<local_ok>\d+).*?"
    r"Sonnet escalation:\s*(?P<escalated>\d+)",
    re.IGNORECASE | re.DOTALL,
)
FEATURE_RE = re.compile(r"^Feature:\s*([A-Za-z0-9._-]+)\s*$", re.MULTILINE)


def safe_get(d, *path, default=None):
    cur = d
    for k in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def extract_verdict(result_text: str):
    if not result_text:
        return None, None
    m = VERDICT_RE.search(result_text)
    if not m:
        return None, None
    return m.group("verdict").upper(), m.group("blocking").lower() == "true"


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        event = json.loads(raw)
    except Exception as e:
        print(f"[blast-telemetry] WARN: bad event JSON ({e})", file=sys.stderr)
        return 0

    tool_name = event.get("tool_name", "")
    if tool_name not in ("Agent", "Task"):
        return 0

    cwd = event.get("cwd") or "."
    log_dir = Path(cwd) / LOG_DIR_NAME

    # Fallback: derive project root from this script's location if cwd-relative
    # path doesn't make sense (Claude Code event variations, Windows OneDrive
    # quirks). Same robustness fix as approval-gate and privacy-gate hooks.
    if not log_dir.parent.exists():
        script_root = Path(__file__).resolve().parent.parent.parent
        if (script_root / ".blast").exists():
            log_dir = script_root / LOG_DIR_NAME
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[blast-telemetry] WARN: cannot create log dir ({e})", file=sys.stderr)
        return 0

    log_path = log_dir / LOG_FILE_NAME

    tool_input = event.get("tool_input") or {}
    tool_response = event.get("tool_response") or {}

    subagent = safe_get(tool_input, "subagent_type", default="") or ""
    prompt = safe_get(tool_input, "prompt", default="") or ""
    description = safe_get(tool_input, "description", default="") or ""

    feature = ""
    fm = FEATURE_RE.search(prompt) if prompt else None
    if fm:
        feature = fm.group(1)

    # Result body shape varies between Claude Code versions; try common keys
    result_text = ""
    for key in ("result", "output", "response", "content", "text"):
        v = safe_get(tool_response, key)
        if isinstance(v, str) and v:
            result_text = v
            break
    if not result_text and isinstance(tool_response, dict):
        # Try nested content blocks
        content = tool_response.get("content")
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    t = block.get("text")
                    if isinstance(t, str):
                        parts.append(t)
            result_text = "\n".join(parts)

    verdict, blocking = extract_verdict(result_text)

    findings = None
    fm2 = FINDINGS_RE.search(result_text) if result_text else None
    if fm2:
        try:
            findings = int(fm2.group(1))
        except ValueError:
            findings = None

    # Local->cloud escalation accounting (impl phase only; None elsewhere)
    local_ok = escalated = None
    em = ESCALATION_RE.search(result_text) if result_text else None
    if em:
        try:
            local_ok = int(em.group("local_ok"))
            escalated = int(em.group("escalated"))
        except ValueError:
            local_ok = escalated = None

    # Tool-call duration when the event carries it (varies by Claude Code version)
    duration_ms = None
    for k in ("duration_ms", "durationMs", "elapsed_ms"):
        v = event.get(k)
        if isinstance(v, (int, float)):
            duration_ms = int(v)
            break

    # Detect gate-blocked: tool_response often has "is_error": true OR
    # text starts with "[blast-gate] HARD BLOCK"
    is_error = bool(tool_response.get("is_error")) if isinstance(tool_response, dict) else False
    gate_blocked = is_error and "blast-gate" in result_text.lower()

    record = {
        "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool": tool_name,
        "subagent": subagent,
        "feature": feature,
        "description": description[:120],
        "prompt_chars": len(prompt),
        "result_chars": len(result_text),
        "verdict": verdict,
        "blocking": blocking,
        "findings": findings,
        "local_ok": local_ok,
        "escalated": escalated,
        "duration_ms": duration_ms,
        "is_error": is_error,
        "gate_blocked": gate_blocked,
    }

    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[blast-telemetry] WARN: cannot append to log ({e})", file=sys.stderr)
        return 0

    return 0


def self_test():
    """Write a probe record so the user can verify hook wiring end-to-end.

    Run manually: python .claude/hooks/blast-telemetry.py --self-test
    Then check .blast/logs/agent-runs.jsonl for a {"subagent": "self-test"} line.
    If pipeline runs produce no records while self-test does, the hook command
    in .claude/settings.json is not firing (check `python` vs `python3` on PATH).
    """
    fake = {
        "tool_name": "Task",
        "cwd": str(Path(__file__).resolve().parent.parent.parent),
        "tool_input": {"subagent_type": "self-test", "prompt": "Feature: self-test\n", "description": "telemetry self-test"},
        "tool_response": {"result": "---VERDICT---\nVERDICT: PASS\nBLOCKING: false\nFINDINGS: 0\n---END---"},
    }
    import io
    sys.stdin = io.StringIO(json.dumps(fake))
    rc = main()
    print(f"[blast-telemetry] self-test wrote probe record (rc={rc}) — check .blast/logs/agent-runs.jsonl")
    return rc


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[blast-telemetry] ERROR: unhandled ({e}); allowing", file=sys.stderr)
        sys.exit(0)
