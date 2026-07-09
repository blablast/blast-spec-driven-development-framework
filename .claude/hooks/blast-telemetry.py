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
    - model_tier + cost_usd (§3): cloud cost ESTIMATED from char counts × tier price
      (cost_estimated=true) until Claude Code passes real token usage to hooks;
      local Ollama tokens scraped from bridge headers and booked at $0; Gemini
      juror cost added from its real usage. Unblocks cost-policy.md calibration.

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

# === COST ACCOUNTING (§3) ===
# Bridge metadata headers the local/cloud tools prepend to their output. We scrape
# them out of the subagent's result text to book real local token counts ($0) and,
# when a cloud juror ran, its real usage.
#   local:  "[qwen3-coder @ ubuntu | 42 tokens | 2.0s | 21.0 tok/s]"
#   gemini: "[gemini-3-flash-preview @ gemini-api | in=1200 out=340]"
BRIDGE_LOCAL_RE = re.compile(r"\[[\w.\-:]+ @ (?:ubuntu|win11) \| (\d+) tokens \|")
BRIDGE_GEMINI_RE = re.compile(r"\[[\w.\-:]+ @ gemini-api \| in=(\d+) out=(\d+)\]")

# subagent_type → cloud model tier. Aliases resolve to current gen; keep in sync
# with .blast/steering/llm-routing.md. Agents that generate code locally (Forge)
# still incur cloud cost only on escalation — their tier is the escalation target.
SUBAGENT_TIER = {
    "spec-design-agent": "opus",
    "security-audit-agent": "sonnet",   # orchestrator demoted to sonnet (§2); opus lives in sub-agent B
    "spec-tdd-impl-agent": "sonnet",    # local-first; sonnet only on escalation
    "spec-research-agent": "sonnet",
    "validate-gap-agent": "sonnet",
    "validate-design-agent": "sonnet",
    "validate-impl-agent": "sonnet",
    "validate-tasks-agent": "sonnet",
    "simplify-agent": "sonnet",
    "code-review-agent": "sonnet",
    "steering-agent": "sonnet",
    "debate-critic": "sonnet",
    "debate-author": "sonnet",
    "debate-critic-opus": "opus",
    "spec-tasks-agent": "haiku",
    "spec-requirements-agent": "haiku",
    "spec-tiny-agent": "haiku",
    "spec-complete-agent": "haiku",
    "spec-evolve-agent": "haiku",
    "spec-deprecate-agent": "haiku",
    "spec-drift-agent": "haiku",
    "steering-custom-agent": "haiku",
    "debate-judge": "haiku",
    "debate-aggregator": "haiku",
}

# $/MTok (input, output). Snapshot: 2026-07-08. Sonnet 5 intro pricing ($2/$10)
# runs through 2026-08-31, then $3/$15 — bump the sonnet row after that date.
# UPDATE THIS when models/prices change; cost-policy.md calibration reads these.
PRICING = {
    "opus":   (5.0, 25.0),
    "sonnet": (2.0, 10.0),
    "haiku":  (1.0, 5.0),
    "gemini": (0.30, 2.50),   # Gemini 3 Flash Preview (approx; refine when billed)
}
PRICING_ASOF = "2026-07-08"
CHARS_PER_TOKEN = 4  # crude estimate until Claude Code passes real usage to hooks


def scrape_local_tokens(result_text: str) -> int:
    return sum(int(m) for m in BRIDGE_LOCAL_RE.findall(result_text or ""))


def scrape_gemini_cost(result_text: str):
    """Return (tokens_in, tokens_out, usd) summed over any Gemini juror headers."""
    tin = tout = 0
    for a, b in BRIDGE_GEMINI_RE.findall(result_text or ""):
        tin += int(a); tout += int(b)
    ip, op = PRICING["gemini"]
    usd = tin / 1e6 * ip + tout / 1e6 * op
    return tin, tout, usd


def estimate_cost(subagent: str, prompt_chars: int, result_chars: int, result_text: str):
    """Best-effort cost of this Agent call.

    Cloud side is ESTIMATED from char counts (÷4) × the subagent's tier price —
    Claude Code doesn't hand token usage to hooks yet, so this bootstraps
    cost-policy calibration; swap in real usage the moment the event carries it.
    Local (Ollama) tokens are booked at $0 but recorded for throughput stats.
    Gemini juror cost, when present in the result, is added from its real usage.
    """
    tier = SUBAGENT_TIER.get(subagent)
    est_in = prompt_chars // CHARS_PER_TOKEN
    est_out = result_chars // CHARS_PER_TOKEN
    cloud_usd = 0.0
    if tier and tier in PRICING:
        ip, op = PRICING[tier]
        cloud_usd = est_in / 1e6 * ip + est_out / 1e6 * op
    _, _, gemini_usd = scrape_gemini_cost(result_text)
    local_tokens = scrape_local_tokens(result_text)
    total = round(cloud_usd + gemini_usd, 6)
    return {
        "model_tier": tier,
        "est_input_tokens": est_in,
        "est_output_tokens": est_out,
        "local_tokens": local_tokens,
        "cost_usd": total,
        "cost_estimated": True,   # cloud side is chars÷4, not billed usage
        "pricing_asof": PRICING_ASOF,
        "expensive": bool(tier == "opus" or total >= 0.50),
    }


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

    cost = estimate_cost(subagent, len(prompt), len(result_text), result_text)

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
        # §3 cost accounting (cloud side estimated from chars÷4 until real usage lands)
        **cost,
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
