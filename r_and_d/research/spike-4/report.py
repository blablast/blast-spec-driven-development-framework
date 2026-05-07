#!/usr/bin/env python3
"""
spike-4 report — combine driver results + judge scores into final markdown.

Output: results/report.md with:
- Per-task pytest pass rates (objective)
- Per-task judge scores (subjective)
- Aggregate per-arm: avg pass rate, avg composite, total cost, total latency
- Verdict: which arm wins, by how much, at what cost premium

Usage:
  python report.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = ROOT_DIR / "results"


def main():
    runs = json.loads((RESULTS_DIR / "results.json").read_text(encoding="utf-8"))
    judge = []
    judge_path = RESULTS_DIR / "judge_scores.json"
    if judge_path.exists():
        judge = json.loads(judge_path.read_text(encoding="utf-8"))

    judge_by_key = {(j["arm"], j["task"]): j for j in judge if "error" not in j}

    by_arm = defaultdict(lambda: {
        "tasks": 0, "total_passed": 0, "total_tests": 0,
        "cost_usd": 0.0, "latency_s": 0.0,
        "judge_composite_sum": 0.0, "judge_count": 0,
        "errors": 0,
    })
    for r in runs:
        a = r["arm"]
        by_arm[a]["tasks"] += 1
        by_arm[a]["total_passed"] += r["pytest_passed"]
        by_arm[a]["total_tests"] += r["pytest_total"]
        by_arm[a]["cost_usd"] += r["cost_usd"]
        by_arm[a]["latency_s"] += r["latency_s"]
        if r.get("error"):
            by_arm[a]["errors"] += 1
        j = judge_by_key.get((r["arm"], r["task"]))
        if j and "composite" in j:
            by_arm[a]["judge_composite_sum"] += j["composite"]
            by_arm[a]["judge_count"] += 1

    out = []
    out.append("# Spike-4 — qwen3-coder vs claude-sonnet-4-6 (head-to-head)")
    out.append("")
    out.append("## Aggregate per arm")
    out.append("")
    out.append("| Arm | Tasks | Pass rate | Composite quality (judge) | Total cost | Total latency |")
    out.append("|---|---:|---:|---:|---:|---:|")
    for arm, s in sorted(by_arm.items()):
        pass_rate = s["total_passed"] / s["total_tests"] if s["total_tests"] else 0
        composite = s["judge_composite_sum"] / s["judge_count"] if s["judge_count"] else 0
        out.append(
            f"| **{arm}** | {s['tasks']} | "
            f"{s['total_passed']}/{s['total_tests']} ({pass_rate:.0%}) | "
            f"{composite:.2f}/5 | "
            f"${s['cost_usd']:.4f} | "
            f"{s['latency_s']:.1f}s |"
        )
    out.append("")

    out.append("## Per-task breakdown")
    out.append("")
    out.append("| Task | Arm | Tests pass | Latency | Cost | Idiom | Sec | Perf | Read | Comp | Composite | Looks correct |")
    out.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|")
    runs_sorted = sorted(runs, key=lambda r: (r["task"], r["arm"]))
    for r in runs_sorted:
        j = judge_by_key.get((r["arm"], r["task"]), {})
        if r.get("error"):
            out.append(f"| {r['task']} | {r['arm']} | — | — | — | — | — | — | — | — | — | ERR: {r['error'][:30]} |")
            continue
        looks = "✓" if j.get("looks_correct") else ("✗" if j.get("looks_correct") is False else "—")
        composite = f"{j.get('composite', 0):.1f}" if j else "—"
        out.append(
            f"| {r['task']} | {r['arm']} | "
            f"{r['pytest_passed']}/{r['pytest_total']} | "
            f"{r['latency_s']:.1f}s | "
            f"${r['cost_usd']:.4f} | "
            f"{j.get('idiomatic', '—')} | "
            f"{j.get('security', '—')} | "
            f"{j.get('performance', '—')} | "
            f"{j.get('readability', '—')} | "
            f"{j.get('completeness', '—')} | "
            f"{composite} | {looks} |"
        )
    out.append("")

    # Verdict section
    out.append("## Verdict")
    out.append("")
    arms = list(by_arm.keys())
    if len(arms) == 2:
        a1, a2 = sorted(arms)
        s1, s2 = by_arm[a1], by_arm[a2]
        pr1 = s1["total_passed"] / max(s1["total_tests"], 1)
        pr2 = s2["total_passed"] / max(s2["total_tests"], 1)
        c1 = s1["judge_composite_sum"] / max(s1["judge_count"], 1)
        c2 = s2["judge_composite_sum"] / max(s2["judge_count"], 1)
        cost1, cost2 = s1["cost_usd"], s2["cost_usd"]
        lat1, lat2 = s1["latency_s"], s2["latency_s"]

        out.append(f"### Pass rate: {a1} {pr1:.0%} vs {a2} {pr2:.0%}")
        if pr1 > pr2:
            out.append(f"**{a1}** wygrywa o {pr1 - pr2:.0%}.")
        elif pr2 > pr1:
            out.append(f"**{a2}** wygrywa o {pr2 - pr1:.0%}.")
        else:
            out.append(f"Tied.")
        out.append("")
        out.append(f"### Composite quality (judge): {a1} {c1:.2f}/5 vs {a2} {c2:.2f}/5")
        if c1 > c2:
            out.append(f"**{a1}** wygrywa o {c1 - c2:.2f} pkt.")
        elif c2 > c1:
            out.append(f"**{a2}** wygrywa o {c2 - c1:.2f} pkt.")
        else:
            out.append("Tied.")
        out.append("")
        out.append(f"### Cost premium: {a1} ${cost1:.4f} vs {a2} ${cost2:.4f}")
        if cost1 > 0.001 and cost2 > 0.001:
            ratio = max(cost1, cost2) / min(cost1, cost2)
            costlier = a1 if cost1 > cost2 else a2
            out.append(f"**{costlier}** kosztował {ratio:.1f}x więcej.")
        else:
            out.append(f"Free arm: {a1 if cost1 < cost2 else a2}")
        out.append("")
        out.append(f"### Latency: {a1} {lat1:.1f}s vs {a2} {lat2:.1f}s")
        if abs(lat1 - lat2) > 1:
            faster = a1 if lat1 < lat2 else a2
            out.append(f"**{faster}** szybszy o {abs(lat1 - lat2):.1f}s.")
        out.append("")

        out.append("### Decision matrix")
        out.append("")
        out.append("| Criterion | Winner |")
        out.append("|---|---|")
        out.append(f"| Pass rate | {a1 if pr1 > pr2 else (a2 if pr2 > pr1 else 'tie')} |")
        out.append(f"| Composite quality | {a1 if c1 > c2 else (a2 if c2 > c1 else 'tie')} |")
        out.append(f"| Cost ($) | {a1 if cost1 < cost2 else a2} |")
        out.append(f"| Latency | {a1 if lat1 < lat2 else a2} |")

    print("\n".join(out))
    Path(RESULTS_DIR / "report.md").write_text("\n".join(out), encoding="utf-8")
    print(f"\nReport: {RESULTS_DIR / 'report.md'}", file=sys.stderr)


if __name__ == "__main__":
    main()
