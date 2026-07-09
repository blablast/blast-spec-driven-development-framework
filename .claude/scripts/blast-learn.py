#!/usr/bin/env python3
"""
blast-learn — multi-purpose self-improvement aggregator.

Modes:
  --lessons       Aggregate retrospections from shipped specs → lessons.md
  --calibrate     Read agent-runs.jsonl, compute p25/p50/p75/p95 per (subagent,phase)
                  → suggest cost-policy.md updates
  --routing       Correlate composition (jury/hybrid/solo) → verdict outcomes
                  → routing observability report
  --all           Run all three sequentially

Read-only by default; --apply writes changes.

Usage:
  python .claude/scripts/blast-learn.py --lessons
  python .claude/scripts/blast-learn.py --calibrate --apply
  python .claude/scripts/blast-learn.py --routing
  python .claude/scripts/blast-learn.py --all --apply
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import statistics
import datetime as dt
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPECS_DIR = REPO_ROOT / ".blast" / "specs"
LOG_PATH = REPO_ROOT / ".blast" / "logs" / "agent-runs.jsonl"
STEERING_DIR = REPO_ROOT / ".blast" / "steering"


# ──────────────────────────────────────────────────────────────────────────
# 1) LESSONS AGGREGATOR
# ──────────────────────────────────────────────────────────────────────────

def collect_lessons(since: str | None = None) -> list[dict]:
    """Walk shipped specs, harvest retrospection.md + spec.json.lessons[]."""
    out = []
    if not SPECS_DIR.exists():
        return out
    cutoff = None
    if since:
        cutoff = dt.datetime.fromisoformat(since.replace("Z", "+00:00"))
    for spec_dir in SPECS_DIR.iterdir():
        if not spec_dir.is_dir():
            continue
        spec_json_path = spec_dir / "spec.json"
        if not spec_json_path.exists():
            continue
        try:
            spec = json.loads(spec_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if spec.get("status") != "shipped":
            continue
        if cutoff and spec.get("completed_at"):
            try:
                completed = dt.datetime.fromisoformat(spec["completed_at"].replace("Z", "+00:00"))
                if completed < cutoff:
                    continue
            except (ValueError, TypeError):
                pass

        # Source 1: retrospection.md if exists
        retro_path = spec_dir / "retrospection.md"
        retro_text = ""
        if retro_path.exists():
            retro_text = retro_path.read_text(encoding="utf-8")

        # Source 2: spec.json.lessons[] (structured)
        json_lessons = spec.get("lessons", []) or []

        if retro_text or json_lessons:
            out.append({
                "feature": spec.get("feature_name", spec_dir.name),
                "completed_at": spec.get("completed_at"),
                "retrospection_md": retro_text,
                "lessons_structured": json_lessons,
            })
    return out


def render_lessons_digest(lessons: list[dict]) -> str:
    if not lessons:
        return "# Aggregated Lessons\n\n_No retrospections found in shipped specs._\n"

    out = ["# Aggregated Lessons", "",
           f"Source: retrospections from {len(lessons)} shipped spec(s).",
           "Use as input to /blast:steering for promoting recurring themes to tech.md::Gotchas.",
           ""]

    # Section per spec, plus simple frequency on extracted bullet lines
    out.append("## Per-spec lessons")
    out.append("")
    all_bullets = []
    for entry in sorted(lessons, key=lambda e: e.get("completed_at") or ""):
        out.append(f"### `{entry['feature']}` (shipped {entry.get('completed_at') or '?'})")
        out.append("")
        if entry["lessons_structured"]:
            for ln in entry["lessons_structured"]:
                out.append(f"- {ln}")
                all_bullets.append(ln.strip().lower())
        if entry["retrospection_md"]:
            for raw in entry["retrospection_md"].splitlines():
                m = re.match(r"^\s*[-*]\s+(.+?)\s*$", raw)
                if m:
                    bullet = m.group(1).strip()
                    out.append(f"- {bullet}")
                    all_bullets.append(bullet.lower())
        out.append("")

    # Naive recurring-theme detection: bigrams of significant words
    def significant_words(text: str) -> list[str]:
        return [w for w in re.findall(r"\b[a-z]{4,}\b", text)
                if w not in {"this", "that", "with", "from", "have", "were", "been", "they",
                             "their", "them", "these", "than", "into", "when", "what",
                             "which", "would", "should", "could", "while", "after", "before"}]
    bigram_counts = Counter()
    for b in all_bullets:
        words = significant_words(b)
        for i in range(len(words) - 1):
            bigram_counts[(words[i], words[i + 1])] += 1
    recurring = [(bg, n) for bg, n in bigram_counts.items() if n >= 2]
    recurring.sort(key=lambda x: -x[1])

    out.append("## Recurring themes (bigram frequency ≥ 2)")
    out.append("")
    if not recurring:
        out.append("_No bigrams repeating across specs yet (need more shipped specs)._")
    else:
        for (w1, w2), count in recurring[:15]:
            out.append(f"- `{w1} {w2}` appears in {count} bullets")
    out.append("")

    out.append("## Recommended action")
    out.append("")
    out.append("Run `/blast:steering --learn` and have Steward agent decide which themes")
    out.append("graduate to `tech.md::Gotchas` (recurring pitfalls, project-wide).")
    return "\n".join(out)


# ──────────────────────────────────────────────────────────────────────────
# 2) COST CALIBRATOR
# ──────────────────────────────────────────────────────────────────────────

def parse_telemetry() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    rows = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _pct(vals: list[float], q: float) -> float:
    """Percentile with a nearest-rank fallback for tiny samples."""
    s = sorted(vals)
    if len(s) == 1:
        return s[0]
    idx = min(len(s) - 1, int(round(q * (len(s) - 1))))
    return s[idx]


def calibrate_cost_caps(rows: list[dict]) -> dict:
    """Group real $ cost by subagent, compute percentiles + spend totals.

    Uses the telemetry `cost_usd` field (added §3). Falls back to a char proxy
    only for legacy rows written before cost accounting existed, so a mixed log
    still produces useful numbers.
    """
    if not rows:
        return {"_status": "empty log", "groups": {}}

    groups = defaultdict(lambda: {"cost": [], "chars": [], "esc_local": 0, "esc_cloud": 0,
                                  "expensive": 0, "estimated": 0})
    total_spend = 0.0
    have_cost = 0
    for r in rows:
        sub = r.get("subagent") or "unknown"
        g = groups[sub]
        cost = r.get("cost_usd")
        if isinstance(cost, (int, float)):
            g["cost"].append(float(cost))
            total_spend += float(cost)
            have_cost += 1
            if r.get("cost_estimated"):
                g["estimated"] += 1
        chars = (r.get("prompt_chars") or 0) + (r.get("result_chars") or 0)
        if chars > 0:
            g["chars"].append(chars)
        if r.get("expensive"):
            g["expensive"] += 1
        lo, es = r.get("local_ok"), r.get("escalated")
        if isinstance(lo, int):
            g["esc_local"] += lo
        if isinstance(es, int):
            g["esc_cloud"] += es

    out = {}
    for sub, g in groups.items():
        cost = g["cost"]
        entry = {"n": len(cost) or len(g["chars"]), "expensive_runs": g["expensive"]}
        if len(cost) >= 3:
            entry.update({
                "cost_p25": round(_pct(cost, 0.25), 4),
                "cost_p50": round(statistics.median(cost), 4),
                "cost_p75": round(_pct(cost, 0.75), 4),
                "cost_p95": round(_pct(cost, 0.95), 4),
                "cost_total": round(sum(cost), 4),
                "cost_estimated_frac": round(g["estimated"] / len(cost), 2),
                "warning_at": round(_pct(cost, 0.75), 2),   # cost-policy suggestion
                "block_at": round(_pct(cost, 0.95), 2),
            })
        elif cost:
            entry["_note"] = f"{len(cost)} cost sample(s) — need ≥3 for percentiles"
            entry["cost_total"] = round(sum(cost), 4)
        else:
            entry["_note"] = "no cost_usd yet (legacy rows); char proxy only"
            if g["chars"]:
                entry["p50_chars"] = int(statistics.median(g["chars"]))
        tot_esc = g["esc_local"] + g["esc_cloud"]
        if tot_esc:
            entry["cloud_escalation_rate"] = round(g["esc_cloud"] / tot_esc, 3)
        out[sub] = entry
    return {"groups": out, "total_runs": len(rows),
            "rows_with_cost": have_cost, "total_spend_usd": round(total_spend, 4)}


def render_calibration_report(cal: dict) -> str:
    out = ["# Cost calibration report", ""]
    out.append(f"Source: `{LOG_PATH.relative_to(REPO_ROOT)}` "
               f"({cal.get('total_runs', 0)} runs, {cal.get('rows_with_cost', 0)} with cost_usd)")
    out.append(f"**Total observed spend: ${cal.get('total_spend_usd', 0):.2f}** "
               f"(cloud estimated from chars÷4 until real usage lands; local = $0).")
    out.append("")
    if not cal.get("groups"):
        out.append("_No telemetry data yet. Run blast specs to accumulate samples._")
        return "\n".join(out)

    out.append("## Cost per subagent (USD)")
    out.append("")
    out.append("| Subagent | N | p50 $ | p75 $ | p95 $ | total $ | expensive | cloud-esc | est-frac |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    ready = []
    for sub, s in sorted(cal["groups"].items()):
        if "cost_p50" in s:
            esc = f"{s['cloud_escalation_rate']:.0%}" if "cloud_escalation_rate" in s else "—"
            out.append(f"| {sub} | {s['n']} | {s['cost_p50']:.4f} | {s['cost_p75']:.4f} | "
                       f"{s['cost_p95']:.4f} | {s['cost_total']:.3f} | {s['expensive_runs']} | "
                       f"{esc} | {s.get('cost_estimated_frac', 0):.0%} |")
            ready.append((sub, s))
        else:
            out.append(f"| {sub} | {s.get('n', 0)} | {s.get('_note', 'n/a')} | | | "
                       f"{s.get('cost_total', 0):.3f} | {s['expensive_runs']} | | |")
    out.append("")
    out.append("## Recommended `cost-policy.md` caps (warning_at = p75, block_at = p95)")
    out.append("")
    if not ready:
        out.append("_Not enough samples yet — need ≥3 cost-bearing runs per subagent._")
    else:
        out.append("Paste into `.blast/steering/cost-policy.md` once samples are representative")
        out.append("(the roadmap target: warning_at = historical p75, block_at = p95):")
        out.append("")
        out.append("```")
        for sub, s in ready:
            out.append(f"{sub:28s} warning_at: ${s['warning_at']:<6} block_at: ${s['block_at']}")
        out.append("```")
        out.append("")
        out.append("> ⚠ `est-frac` = share of runs whose cloud cost is ESTIMATED (chars÷4), not")
        out.append("> billed. Treat caps as provisional until real token usage reaches the hook,")
        out.append("> and re-baseline after the Sonnet-5/Opus-4.7 tokenizer change (~+30% tokens).")
    return "\n".join(out)


# ──────────────────────────────────────────────────────────────────────────
# 3) ROUTING OBSERVABILITY
# ──────────────────────────────────────────────────────────────────────────

def routing_correlations(rows: list[dict]) -> dict:
    """Group verdict outcomes by subagent_type — surface which agents WARN/FAIL most."""
    by_sub = defaultdict(lambda: {"PASS": 0, "WARN": 0, "FAIL": 0, "blocked": 0, "errors": 0, "total": 0})
    for r in rows:
        sub = r.get("subagent") or "unknown"
        verdict = r.get("verdict")
        by_sub[sub]["total"] += 1
        if r.get("gate_blocked"):
            by_sub[sub]["blocked"] += 1
        if r.get("is_error"):
            by_sub[sub]["errors"] += 1
        if verdict in {"PASS", "WARN", "FAIL"}:
            by_sub[sub][verdict] += 1
    return dict(by_sub)


def render_routing_report(corr: dict) -> str:
    out = ["# Routing observability report", ""]
    if not corr:
        out.append("_No telemetry data yet._")
        return "\n".join(out)
    out.append("## Verdict distribution per subagent")
    out.append("")
    out.append("| Subagent | Total | PASS | WARN | FAIL | Blocked | Errors | PASS% |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for sub, stats in sorted(corr.items()):
        total = stats["total"] or 1
        pass_pct = stats["PASS"] / total * 100
        out.append(f"| {sub} | {stats['total']} | {stats['PASS']} | {stats['WARN']} | {stats['FAIL']} | {stats['blocked']} | {stats['errors']} | {pass_pct:.0f}% |")
    out.append("")
    out.append("## Insights")
    out.append("")
    # Surface anomalies
    insights = []
    for sub, s in corr.items():
        if s["total"] < 3:
            continue
        fail_rate = s["FAIL"] / s["total"]
        block_rate = s["blocked"] / s["total"]
        err_rate = s["errors"] / s["total"]
        if fail_rate > 0.3:
            insights.append(f"- **{sub}**: FAIL rate {fail_rate:.0%} (n={s['total']}) — review prompt or routing")
        if block_rate > 0.2:
            insights.append(f"- **{sub}**: blocked {block_rate:.0%} (n={s['total']}) — approval flow friction")
        if err_rate > 0.1:
            insights.append(f"- **{sub}**: error rate {err_rate:.0%} (n={s['total']}) — debug agent")
    if not insights:
        out.append("_No anomalies (need more samples or all subagents performing well)._")
    else:
        out.extend(insights)
    return "\n".join(out)




# ──────────────────────────────────────────────────────────────────────────
# 4) SOTA REFRESH (audit only — manual refresh recommended)
# ──────────────────────────────────────────────────────────────────────────

import re as _re_sota
import datetime as _dt_sota

def audit_sota_freshness() -> dict:
    """List sota/*.md files with refresh date, flag stale (>6mo)."""
    sota_dir = REPO_ROOT / ".blast" / "knowledge" / "sota"
    if not sota_dir.exists():
        return {"_status": "no sota/ dir; create with /blast:knowledge --seed-sota (TODO)"}
    out = []
    today = _dt_sota.date.today()
    for md in sota_dir.glob("*.md"):
        if md.name == "README.md":
            continue
        text = md.read_text(encoding="utf-8")
        m = _re_sota.search(r"\*\*Last refreshed\*\*:\s*(\d{4}-\d{2}-\d{2})", text)
        if not m:
            out.append({"file": md.name, "status": "no refresh date", "stale": True})
            continue
        try:
            refreshed = _dt_sota.date.fromisoformat(m.group(1))
            age_days = (today - refreshed).days
            stale = age_days > 180
            out.append({
                "file": md.name,
                "last_refreshed": m.group(1),
                "age_days": age_days,
                "stale": stale,
                "recommend": "refresh now (>6mo)" if age_days > 180 else
                             "due soon (>3mo)" if age_days > 90 else "fresh",
            })
        except ValueError:
            out.append({"file": md.name, "status": "invalid date format"})
    return {"sota_files": out, "total": len(out)}


def render_sota_audit(audit: dict) -> str:
    out = ["# SOTA freshness audit", ""]
    if "_status" in audit:
        out.append(f"_{audit['_status']}_")
        return "\n".join(out)
    if not audit.get("sota_files"):
        out.append("_No sota/ files found._")
        return "\n".join(out)
    out.append("| File | Last refreshed | Age | Status |")
    out.append("|---|---|---:|---|")
    for f in audit["sota_files"]:
        if "last_refreshed" in f:
            out.append(f"| {f['file']} | {f['last_refreshed']} | {f['age_days']}d | {f['recommend']} |")
        else:
            out.append(f"| {f['file']} | — | — | {f.get('status', 'unknown')} |")
    out.append("")
    out.append("## Refresh action")
    out.append("")
    stale = [f for f in audit["sota_files"] if f.get("stale")]
    if stale:
        out.append(f"**{len(stale)} file(s) stale** — recommend WebSearch refresh:")
        for f in stale:
            out.append(f"- `{f['file']}` (last {f.get('last_refreshed', 'unknown')}, {f.get('age_days', '?')}d ago)")
        out.append("")
        out.append("Manual refresh: edit each file with current SOTA recommendations + bump `**Last refreshed**` date.")
    else:
        out.append("All files fresh (<6mo). No action needed.")
    return "\n".join(out)


# ──────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lessons", action="store_true")
    p.add_argument("--calibrate", action="store_true")
    p.add_argument("--routing", action="store_true")
    p.add_argument("--all", action="store_true")
    p.add_argument("--refresh-sota", action="store_true",
                   help="Audit sota/ knowledge files for staleness (>6mo)")
    p.add_argument("--apply", action="store_true",
                   help="Write changes to disk (without: dry-run, print to stdout)")
    p.add_argument("--since", help="ISO date — only specs/rows from this date onward")
    p.add_argument("--output", help="Output file (default stdout)")
    args = p.parse_args()

    if not (args.lessons or args.calibrate or args.routing or args.all or args.refresh_sota):
        p.print_help()
        return 1

    out_chunks = []

    if args.lessons or args.all:
        lessons = collect_lessons(args.since)
        out_chunks.append(render_lessons_digest(lessons))
        if args.apply:
            target = Path(args.output) if args.output else STEERING_DIR / "lessons.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(out_chunks[-1], encoding="utf-8")
            print(f"Wrote {target}", file=sys.stderr)

    if args.calibrate or args.all:
        rows = parse_telemetry()
        cal = calibrate_cost_caps(rows)
        out_chunks.append(render_calibration_report(cal))

    if args.routing or args.all:
        rows = parse_telemetry()
        corr = routing_correlations(rows)
        out_chunks.append(render_routing_report(corr))

    if args.refresh_sota or args.all:
        audit = audit_sota_freshness()
        out_chunks.append(render_sota_audit(audit))

    output = "\n\n---\n\n".join(out_chunks)
    if args.output and not args.apply:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
