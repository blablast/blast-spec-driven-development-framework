#!/usr/bin/env python3
"""
blast approval gate — PreToolUse hook for Claude Code.

Blocks Agent/Task tool calls to gated blast subagents (spec-design-agent,
spec-tasks-agent, spec-tdd-impl-agent) when the prior pipeline phase has
not been approved in spec.json AND no bypass marker is present in the prompt.

Bypasses (allow without checking spec.json):
  - subagent NOT in gated list (general-purpose, validate-*, security, etc.)
  - prompt contains "Auto-approve: true" (set by /blast:design -y, /blast:tasks -y)
  - spec-tiny-agent (self-approves all phases as part of its workflow)
  - spec.json has top-level "tiny": true (tiny-spec already self-approved)

Exit codes:
  0 = allow tool call
  2 = block tool call (Claude Code shows stderr to user as error message)

Defensive posture:
  - Hook system errors (bad JSON, missing fields) → exit 0 (don't break user's workflow)
  - Spec-related errors (missing/malformed spec.json for a gated agent) → exit 2 (force user attention)
  - Cannot extract feature name from prompt → exit 2 (something is wrong)
"""

import json
import re
import sys
from pathlib import Path

# Map subagent type → name of approval field that must be true=true to proceed
GATED_AGENTS = {
    "spec-design-agent":     "requirements",
    "spec-tasks-agent":      "design",
    "spec-tdd-impl-agent":   "tasks",
}

BYPASS_MARKER = "Auto-approve: true"
TINY_AGENT = "spec-tiny-agent"


def log_warn(msg):
    print(f"[blast-gate] WARN: {msg}", file=sys.stderr)


def log_block(msg):
    print(f"\n[blast-gate] HARD BLOCK\n{msg}\n", file=sys.stderr)


def main():
    # 1. Read hook event JSON from stdin
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            log_warn("empty stdin; allowing")
            return 0
        event = json.loads(raw)
    except json.JSONDecodeError as e:
        log_warn(f"could not parse hook event JSON ({e}); allowing")
        return 0
    except Exception as e:
        log_warn(f"unexpected error reading event ({e}); allowing")
        return 0

    # 2. Confirm this is the right event/tool. Matcher should already filter,
    #    but be defensive against config drift.
    tool_name = event.get("tool_name", "")
    if tool_name not in ("Agent", "Task"):
        # Not the tool we care about — let it through.
        return 0

    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        log_warn(f"tool_input is not a dict ({type(tool_input).__name__}); allowing")
        return 0

    subagent_type = tool_input.get("subagent_type") or ""
    prompt = tool_input.get("prompt") or ""

    # 3. Tiny agent — never gated (it self-approves as part of its workflow)
    if subagent_type == TINY_AGENT:
        return 0

    # 4. Not a gated blast agent (general-purpose, Explore, validate-*, security, etc.)
    if subagent_type not in GATED_AGENTS:
        return 0

    # 5. Bypass via -y flag — slash command writes "Auto-approve: true" into prompt
    if BYPASS_MARKER in prompt:
        return 0

    # 6. Extract feature name from prompt. Standard prompt format from blast slash
    #    commands starts with "Feature: <name>\n".
    m = re.search(r"^Feature:\s*([A-Za-z0-9._-]+)\s*$", prompt, re.MULTILINE)
    if not m:
        log_block(
            f"Cannot extract feature name from {subagent_type} prompt.\n"
            f"  Expected line:  'Feature: <kebab-case-name>'\n"
            f"  Prompt preview: {prompt[:180]!r}...\n"
            f"  Fix:            ensure your slash command emits the standard prompt header."
        )
        return 2

    feature = m.group(1)
    cwd = event.get("cwd") or "."
    spec_path = Path(cwd) / ".blast" / "specs" / feature / "spec.json"

    # 7. Spec must exist for gated agents — try cwd-relative first, fallback to
    #    project root derived from this script's location. Robust against
    #    Claude Code event format changes that may not pass cwd reliably,
    #    or against shells that spawn hook with unexpected cwd (Windows OneDrive
    #    folders with Unicode chars sometimes resolve cwd to user profile dir).
    if not spec_path.exists():
        # Hook lives in .claude/hooks/ — project root is 3 parents up
        script_root = Path(__file__).resolve().parent.parent.parent
        fallback_path = script_root / ".blast" / "specs" / feature / "spec.json"
        if fallback_path.exists():
            spec_path = fallback_path
        else:
            log_block(
                f"spec.json not found for {subagent_type}.\n"
                f"  feature:        {feature}\n"
                f"  tried (cwd):    {Path(cwd) / '.blast/specs' / feature / 'spec.json'}\n"
                f"  tried (script): {fallback_path}\n"
                f"  Fix:            run /blast:init first, or check feature name."
            )
            return 2

    # 8. Parse spec.json
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        log_block(
            f"spec.json malformed for feature '{feature}'.\n"
            f"  path:  {spec_path}\n"
            f"  error: {e}\n"
            f"  Fix:   repair JSON manually, then re-run."
        )
        return 2

    # 9. Tiny-spec bypass (defensive — tiny-agent should never reach here, but
    #    in case a tiny spec is somehow run through standard agents)
    if spec.get("tiny") is True:
        return 0

    # 10. Check approval flag for the prior phase
    prev_phase = GATED_AGENTS[subagent_type]
    approved = (
        spec.get("approvals", {}).get(prev_phase, {}).get("approved", False)
    )

    if approved is True:
        return 0

    # 11. BLOCK — emit clear remediation
    next_command = {
        "spec-design-agent":   ("design",  "/blast:design"),
        "spec-tasks-agent":    ("tasks",   "/blast:tasks"),
        "spec-tdd-impl-agent": ("impl",    "/blast:impl"),
    }[subagent_type]
    phase_label, slash_cmd = next_command

    log_block(
        f"{subagent_type} cannot run for feature '{feature}'.\n"
        f"  required:    approvals.{prev_phase}.approved == true\n"
        f"  current:     {approved}\n\n"
        f"  Fix (review then approve):\n"
        f"    1. Review .blast/specs/{feature}/{prev_phase}.md\n"
        f"    2. /blast:approve {feature} {prev_phase}\n"
        f"    3. {slash_cmd} {feature}\n\n"
        f"  Bypass (auto-approve prior phase):\n"
        f"    {slash_cmd} {feature} -y"
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        # Last-ditch: never let an unhandled exception break the user's workflow.
        # Log to stderr and allow.
        print(f"[blast-gate] ERROR: unhandled exception ({e}); allowing", file=sys.stderr)
        sys.exit(0)
