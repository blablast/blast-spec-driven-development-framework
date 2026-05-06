#!/usr/bin/env python3
"""
blast privacy gate - PreToolUse hook enforcing privacy patterns from llm-routing.md.

Blocks tool calls that would send privacy-flagged file content to non-local LLMs.

Specifically:
    - Reads `.blast/steering/llm-routing.md` for `local-only` glob patterns
    - When a Read/Glob/Grep tool call references a privacy-flagged path,
      records the path in a session-scoped state file
    - When a subsequent Agent/Task call invokes a known external-LLM tool
      (ask_openrouter_*, ask_anthropic_* — currently external = cloud),
      checks if recent privacy-flagged files were read; blocks if so
    - Local Ollama tools (ask_ubuntu_*, ask_win11_*, ask_local_*) are always allowed

This is a best-effort defense. It is NOT a substitute for keeping secrets out
of the working tree (use `.gitignore`), but it catches accidental cloud LLM
invocations after reading a flagged file.

Exit codes:
    0 = allow tool call
    2 = block tool call (Claude Code shows stderr)

Defensive posture:
    - Cannot read llm-routing.md → exit 0 (don't break workflow)
    - State file unwritable → log warning, exit 0
    - Pattern parse error → log, skip that pattern
"""

from __future__ import annotations

import fnmatch
import json
import re
import sys
import time
from pathlib import Path

ROUTING_PATH = ".blast/steering/llm-routing.md"
STATE_DIR = ".blast/.session-state"
STATE_FILE = "privacy-touched.json"
TOUCH_WINDOW_S = 1800  # 30 minutes

# Cloud-side tool patterns (treated as "external" — privacy-flagged files cannot reach them)
EXTERNAL_TOOL_PATTERNS = [
    r"^ask_openrouter_",
    r"^ask_anthropic_",
    r"^ask_cloud_",
]
EXTERNAL_RES = [re.compile(p) for p in EXTERNAL_TOOL_PATTERNS]

# Local-side tool patterns (always allowed regardless of privacy state)
LOCAL_TOOL_PATTERNS = [
    r"^ask_local_",
    r"^ask_ubuntu_",
    r"^ask_win11_",
]
LOCAL_RES = [re.compile(p) for p in LOCAL_TOOL_PATTERNS]


def log_warn(msg):
    print(f"[blast-privacy] WARN: {msg}", file=sys.stderr)


def log_block(msg):
    print(f"\n[blast-privacy] HARD BLOCK\n{msg}\n", file=sys.stderr)


def parse_local_only_patterns(routing_path: Path) -> list[str]:
    """Extract `local-only` glob patterns from llm-routing.md."""
    if not routing_path.exists():
        return []
    try:
        text = routing_path.read_text(encoding="utf-8")
    except Exception as e:
        log_warn(f"cannot read {routing_path}: {e}")
        return []

    patterns: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # Format: <glob>   llm=local-only
        m = re.match(r"^(\S+)\s+llm=local-only\b", s)
        if m:
            patterns.append(m.group(1))
    return patterns


def matches_any(path: str, patterns: list[str]) -> bool:
    norm = path.replace("\\", "/")
    for pat in patterns:
        if fnmatch.fnmatch(norm, pat):
            return True
        # Also try pattern with **/ prefix for sub-path matching
        if not pat.startswith("**/") and fnmatch.fnmatch(norm, "**/" + pat):
            return True
    return False


def load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {"touched": []}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {"touched": []}


def save_state(state_path: Path, state: dict) -> None:
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state), encoding="utf-8")
    except Exception as e:
        log_warn(f"cannot save state: {e}")


def prune_touched(state: dict) -> dict:
    now = time.time()
    state["touched"] = [
        t for t in state.get("touched", [])
        if isinstance(t, dict) and (now - t.get("ts", 0)) <= TOUCH_WINDOW_S
    ]
    return state


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        event = json.loads(raw)
    except Exception as e:
        log_warn(f"bad event JSON ({e})")
        return 0

    cwd = event.get("cwd") or "."
    cwd_path = Path(cwd)
    state_path = cwd_path / STATE_DIR / STATE_FILE
    routing_path = cwd_path / ROUTING_PATH

    # Fallback: if cwd-relative paths don't resolve, derive project root from
    # this script's location. Same robustness fix as approval-gate hook —
    # handles Claude Code event variations and edge cases on Windows
    # (OneDrive folders, em-dash paths, copied directories).
    if not routing_path.exists():
        script_root = Path(__file__).resolve().parent.parent.parent
        fallback_routing = script_root / ROUTING_PATH
        if fallback_routing.exists():
            routing_path = fallback_routing
            state_path = script_root / STATE_DIR / STATE_FILE

    patterns = parse_local_only_patterns(routing_path)
    if not patterns:
        return 0  # No privacy patterns configured → allow everything

    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0

    state = prune_touched(load_state(state_path))

    # Track Read/Glob/Grep accesses to privacy-flagged paths
    touched_path = None
    if tool_name == "Read":
        touched_path = tool_input.get("file_path")
    elif tool_name == "Edit" or tool_name == "Write":
        touched_path = tool_input.get("file_path")
    elif tool_name == "Grep":
        touched_path = tool_input.get("path")
    elif tool_name == "Glob":
        touched_path = tool_input.get("pattern")

    if touched_path and matches_any(touched_path, patterns):
        state["touched"].append({"ts": time.time(), "path": touched_path})
        save_state(state_path, state)
        # Don't block the read itself — we just remember it for later cloud-tool checks

    # Check Agent/Task calls that may invoke external LLM tools
    # Heuristic: scan prompt for invocation of external tool names
    # (we can't know for sure until the agent actually calls the tool, but
    # a hint exists in the prompt — and bridge tool names are visible)
    if tool_name in ("Agent", "Task"):
        prompt = tool_input.get("prompt") or ""
        # Find any explicit external tool reference in prompt
        external_hits = []
        for re_p in EXTERNAL_RES:
            for m in re.finditer(r"(ask_\w+)", prompt):
                tn = m.group(1)
                if re_p.match(tn):
                    external_hits.append(tn)
        if external_hits and state["touched"]:
            recent_paths = [t["path"] for t in state["touched"]]
            log_block(
                f"Privacy violation: agent prompt references external LLM tool(s) "
                f"{external_hits} but recent privacy-flagged paths were touched.\n"
                f"  Touched: {recent_paths[:5]}\n"
                f"  Allowed: only local-* tools (ask_local_*, ask_ubuntu_*, ask_win11_*).\n"
                f"  Fix: re-run agent without external LLM, or remove privacy flag from "
                f"those paths in .blast/steering/llm-routing.md if intentional."
            )
            return 2

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[blast-privacy] ERROR: unhandled ({e}); allowing", file=sys.stderr)
        sys.exit(0)
