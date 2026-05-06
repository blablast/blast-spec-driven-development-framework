#!/usr/bin/env python3
"""
blast telemetry report generator.

Reads .blast/logs/agent-runs.jsonl (and rotated archives) and produces
a markdown summary: counts per agent, verdict trends, gate failure rate,
top features by activity.

Usage:
    python .claude/scripts/blast-telemetry.py
    python .claude/scripts/blast-telemetry.py --since 2026-04-01
    python .claude/scripts/blast-telemetry.py --feature auth-basic

Output: stdout markdown report.
Exit codes: 0 always (read-only operation).
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = REPO_ROOT / ".blast" / "logs"
ACTIVE_LOG = LOG_DIR / "agent-runs.jsonl"
ARCHIVE_DIR = LOG_DIR / "archive"


def parse_iso(s):
    if not s:
        return None
    try:
        if s.endswith("Z"):
            return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.datetime.fromisoformat(s)
    except Exception:
        return None


def read_log_lines(since=None):
    """Yield records from active log + archived logs (gz)."""
    files = []
    if ACTIVE_LOG.exists():
        files.append(("active", ACTIVE_LOG))
    if ARCHIVE_DIR.exists():
        for p in sorted(ARCHIVE_DIR.glob("*.jsonl.gz")):
            files.append(("archive", p))
        for p in sorted(ARCHIVE_DIR.glob("*.jsonl")):
            files.append(("archive", p))

    since_dt = parse_iso(since) if since else None

    for kind, path in files:
        try:
            opener = gzip.open if path.suffix == ".gz" else open
            with opener(path, "rt", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if since_dt:
                        rec_dt = parse_iso(rec.get("ts"))
                        if rec_dt and rec_dt < since_dt:
                            continue
                    yield rec
        except Exception as e:
            print(f"[telemetry] warn: cannot read {path}: {e}", file=sys.stderr)


def render_report(records, args):
    if not records:
        return ("# blast Telemetry Report\n\n"
                "No data yet. The PostToolUse hook writes to "
                "`.blast/logs/agent-runs.jsonl` after Agent/Task calls.\n")

    out = []
    out.append("# blast Telemetry Report")
    out.append("")
    out.append(f"**Generated**: {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    if args.since:
        out.append(f"**Since**: {args.since}")
    if args.feature:
        out.append(f"**Feature filter**: `{args.feature}`")
    out.append(f"**Records**: {len(records)}")
    out.append("")

    # Per-agent summary
    by_agent = Counter()
    by_verdict = Counter()
    by_feature = Counter()
    gate_blocked = 0
    is_error = 0
    total_prompt = 0
    total_result = 0
    blocking_fails = 0

    for r in records:
        sub = r.get("subagent") or "(no-subagent)"
        by_agent[sub] += 1
        v = r.get("verdict")
        if v:
            by_verdict[v] += 1
        f = r.get("feature")
        if f:
            by_feature[f] += 1
        if r.get("gate_blocked"):
            gate_blocked += 1
        if r.get("is_error"):
            is_error += 1
        total_prompt += int(r.get("prompt_chars") or 0)
        total_result += int(r.get("result_chars") or 0)
        if r.get("verdict") == "FAIL" and r.get("blocking"):
            blocking_fails += 1

    out.append("## Summary")
    out.append("")
    out.append(f"- Total Agent/Task invocations: **{len(records)}**")
    out.append(f"- Errors (is_error=true): **{is_error}**")
    out.append(f"- Approval gate blocks: **{gate_blocked}**")
    out.append(f"- Blocking FAIL verdicts: **{blocking_fails}**")
    out.append(f"- Total prompt chars: {total_prompt:,}")
    out.append(f"- Total result chars: {total_result:,}")
    out.append("")

    out.append("## By Subagent")
    out.append("")
    out.append("| Subagent | Calls |")
    out.append("|---|---:|")
    for name, cnt in by_agent.most_common():
        out.append(f"| `{name}` | {cnt} |")
    out.append("")

    if by_verdict:
        out.append("## Verdict Distribution")
        out.append("")
        out.append("| Verdict | Count |")
        out.append("|---|---:|")
        for v in ("PASS", "WARN", "FAIL"):
            if v in by_verdict:
                out.append(f"| {v} | {by_verdict[v]} |")
        out.append("")

    if by_feature:
        out.append("## Top Features by Activity")
        out.append("")
        out.append("| Feature | Calls |")
        out.append("|---|---:|")
        for name, cnt in by_feature.most_common(10):
            out.append(f"| `{name}` | {cnt} |")
        out.append("")

    out.append("## Notes")
    out.append("")
    out.append("- Records are **meta-only** — no prompt/result bodies are stored.")
    out.append("- Active log: `.blast/logs/agent-runs.jsonl`")
    out.append("- Archives: `.blast/logs/archive/*.jsonl.gz` (rotated quarterly).")
    out.append("- To rotate manually: "
               "`mv .blast/logs/agent-runs.jsonl .blast/logs/archive/$(date +%Y-Q%q).jsonl && "
               "gzip .blast/logs/archive/*.jsonl`")
    return "\n".join(out)


def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--since", help="ISO date or datetime (UTC)")
    p.add_argument("--feature", help="filter by feature name")
    args = p.parse_args(argv)

    records = []
    for r in read_log_lines(since=args.since):
        if args.feature and r.get("feature") != args.feature:
            continue
        records.append(r)

    print(render_report(records, args))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
