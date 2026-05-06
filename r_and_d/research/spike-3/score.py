#!/usr/bin/env python3
"""
spike-3 score — match arm findings against ground_truth, compute recall/precision/cost per arm.

Matching rule:
  A finding "matches" a planted bug if any keyword (case-insensitive) from the
  bug's keyword list appears in the finding's TITLE+DESCRIPTION text. Each
  finding can match at most one bug (highest keyword-overlap wins).

Outputs:
  report.md — markdown report with:
    - Per-arm aggregate table (recall/precision/F1/cost/latency)
    - Per-snippet × per-arm breakdown
    - Unmatched findings (potential false positives)
    - Missed bugs (false negatives)

Usage:
  python3 score.py [--results results.json] [--ground-truth ground_truth.json] [--output report.md]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

# ─── MATCHING ─────────────────────────────────────────────────────────────

def text_contains_any_keyword(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    """Return (count_of_matched_keywords, list_of_matched_kw_strings)."""
    text_lc = text.lower()
    matched = [kw for kw in keywords if kw.lower() in text_lc]
    return len(matched), matched

def match_findings_to_bugs(findings: list[dict], bugs: list[dict]) -> dict:
    """
    Returns:
      {
        'tp': int,  # planted bugs caught
        'fp': int,  # findings not matching any bug
        'fn': int,  # planted bugs not caught
        'matched_bug_ids': list[str],
        'unmatched_findings': list[dict],   # FP candidates
        'missed_bugs': list[dict],
        'matches': list[{finding_idx, bug_id, kw_count, kw_matched}],
      }
    """
    matches: list[dict] = []
    matched_bug_set: set[str] = set()
    finding_match_status: list[bool] = [False] * len(findings)

    # Greedy: for each finding, find best-matching bug (highest keyword count)
    for fi, finding in enumerate(findings):
        finding_text = " ".join([
            finding.get("title", ""),
            finding.get("description", ""),
            finding.get("suggested_fix", ""),
        ])
        best_bug = None
        best_count = 0
        best_kw: list[str] = []
        for bug in bugs:
            count, kw_list = text_contains_any_keyword(finding_text, bug["keywords"])
            if count > best_count:
                best_bug = bug
                best_count = count
                best_kw = kw_list
        if best_bug:
            matches.append({
                "finding_idx": fi,
                "bug_id": best_bug["id"],
                "kw_count": best_count,
                "kw_matched": best_kw,
                "finding_title": finding.get("title", "")[:80],
            })
            matched_bug_set.add(best_bug["id"])
            finding_match_status[fi] = True

    tp = len(matched_bug_set)
    fn = len(bugs) - tp
    fp = sum(1 for matched in finding_match_status if not matched)

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "matched_bug_ids": sorted(matched_bug_set),
        "unmatched_findings": [
            {"idx": fi, "title": f.get("title", "")[:80],
             "description": f.get("description", "")[:200]}
            for fi, f in enumerate(findings) if not finding_match_status[fi]
        ],
        "missed_bugs": [b for b in bugs if b["id"] not in matched_bug_set],
        "matches": matches,
    }

# ─── AGGREGATION ──────────────────────────────────────────────────────────

def safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0

def f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

# ─── REPORT ───────────────────────────────────────────────────────────────

def render_report(results: list[dict], gt: dict) -> str:
    """Score every (arm, snippet) pair against ground truth and render markdown."""
    out: list[str] = []
    out.append("# spike-3 — scoring report")
    out.append("")
    out.append(f"- Snippets: {len(gt['snippets'])}")
    out.append(f"- Total planted bugs: {sum(len(s['bugs']) for s in gt['snippets'].values())}")
    out.append(f"- Result rows: {len(results)}")
    out.append("")

    # Per-(arm, snippet) scoring
    per_arm: dict[str, dict] = defaultdict(lambda: {
        "tp": 0, "fp": 0, "fn": 0,
        "cost_usd": 0.0, "latency_s": 0.0, "n_runs": 0,
        "n_errors": 0,
        "snippet_breakdown": {},
        "all_unmatched_findings": [],
        "all_missed_bugs": [],
    })

    for r in results:
        arm = r["arm"]
        snippet = r["snippet"]
        if r.get("error"):
            per_arm[arm]["n_errors"] += 1
            continue

        bugs = gt["snippets"].get(snippet, {}).get("bugs", [])
        if not bugs:
            continue
        m = match_findings_to_bugs(r["findings"], bugs)
        per_arm[arm]["tp"] += m["tp"]
        per_arm[arm]["fp"] += m["fp"]
        per_arm[arm]["fn"] += m["fn"]
        per_arm[arm]["cost_usd"] += r.get("cost_usd", 0.0)
        per_arm[arm]["latency_s"] += r.get("latency_s", 0.0)
        per_arm[arm]["n_runs"] += 1
        per_arm[arm]["snippet_breakdown"][snippet] = {
            "tp": m["tp"], "fp": m["fp"], "fn": m["fn"],
            "n_findings": len(r["findings"]),
            "n_bugs_planted": len(bugs),
            "missed": [b["id"] for b in m["missed_bugs"]],
            "matched": m["matched_bug_ids"],
        }
        per_arm[arm]["all_unmatched_findings"].extend(
            (snippet, u) for u in m["unmatched_findings"]
        )
        per_arm[arm]["all_missed_bugs"].extend(
            (snippet, b["id"], b["severity"], b["description"][:120])
            for b in m["missed_bugs"]
        )

    # ── Aggregate table ──
    out.append("## Aggregate per-arm scores")
    out.append("")
    out.append("| Arm | TP | FP | FN | Recall | Precision | F1 | Cost ($) | Avg latency (s) | Runs | Errors |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    arm_rankings: list[tuple[str, float, float, float, float, float]] = []
    for arm in sorted(per_arm.keys()):
        s = per_arm[arm]
        recall = safe_div(s["tp"], s["tp"] + s["fn"])
        precision = safe_div(s["tp"], s["tp"] + s["fp"])
        f1_score = f1(precision, recall)
        avg_lat = safe_div(s["latency_s"], max(s["n_runs"], 1))
        arm_rankings.append((arm, recall, precision, f1_score, s["cost_usd"], avg_lat))
        out.append(
            f"| **{arm}** | {s['tp']} | {s['fp']} | {s['fn']} | "
            f"{recall:.2f} | {precision:.2f} | {f1_score:.2f} | "
            f"${s['cost_usd']:.4f} | {avg_lat:.1f} | {s['n_runs']} | {s['n_errors']} |"
        )

    out.append("")
    out.append("## Decision matrix")
    out.append("")
    if arm_rankings:
        ranked = sorted(arm_rankings, key=lambda x: -x[3])  # by F1 desc
        winner_arm, winner_recall, winner_prec, winner_f1, winner_cost, _ = ranked[0]
        out.append(f"- Highest F1: **{winner_arm}** ({winner_f1:.2f})")
        if "HYBRID" in dict((a[0], a) for a in arm_rankings):
            hyb = dict((a[0], a) for a in arm_rankings)["HYBRID"]
            sonnet = dict((a[0], a) for a in arm_rankings).get("SOLO_claude-sonnet-4-6") \
                  or dict((a[0], a) for a in arm_rankings).get("SONNET_SOLO")
            if sonnet:
                gain = hyb[1] - sonnet[1]
                cost_ratio = hyb[4] / sonnet[4] if sonnet[4] else float("inf")
                out.append(f"- HYBRID vs SONNET_SOLO recall delta: **{gain:+.2f}** (cost ratio {cost_ratio:.2f}×)")
        if "JURY_3" in dict((a[0], a) for a in arm_rankings):
            jury = dict((a[0], a) for a in arm_rankings)["JURY_3"]
            ctrl = dict((a[0], a) for a in arm_rankings).get("CONTROL") \
                or dict((a[0], a) for a in arm_rankings).get("SOLO_claude-opus-4-6")
            if ctrl:
                gain = jury[1] - ctrl[1]
                cost_ratio = jury[4] / ctrl[4] if ctrl[4] else float("inf")
                out.append(f"- JURY_3 vs CONTROL recall delta: **{gain:+.2f}** (cost ratio {cost_ratio:.2f}×)")

    # ── Per-snippet breakdown ──
    out.append("")
    out.append("## Per-snippet breakdown")
    out.append("")
    snippets_sorted = sorted({r["snippet"] for r in results})
    arms_sorted = sorted(per_arm.keys())
    header = "| Arm | " + " | ".join(snippets_sorted) + " |"
    sep = "|---|" + "|".join(["---:"] * len(snippets_sorted)) + "|"
    out.append(header)
    out.append(sep)
    for arm in arms_sorted:
        cells = []
        for snip in snippets_sorted:
            sb = per_arm[arm]["snippet_breakdown"].get(snip)
            if not sb:
                cells.append("—")
            else:
                cells.append(f"{sb['tp']}/{sb['n_bugs_planted']} (FP {sb['fp']})")
        out.append(f"| **{arm}** | " + " | ".join(cells) + " |")

    # ── Missed bugs (FN) per arm ──
    out.append("")
    out.append("## Missed bugs (false negatives) per arm")
    out.append("")
    for arm in arms_sorted:
        missed = per_arm[arm]["all_missed_bugs"]
        if not missed:
            out.append(f"### {arm} — caught all bugs ✓")
            out.append("")
            continue
        out.append(f"### {arm} — missed {len(missed)} bugs")
        for snippet, bug_id, sev, desc in missed:
            out.append(f"- `{snippet}` :: `{bug_id}` ({sev}) — {desc}")
        out.append("")

    # ── Unmatched findings (potential FPs) per arm ──
    out.append("")
    out.append("## Unmatched findings per arm (potential false positives)")
    out.append("")
    out.append("These are findings reported by the arm that did NOT match any planted bug. They may be:")
    out.append("- Real issues we didn't plant (bonus signal — not necessarily noise)")
    out.append("- Noise / over-report")
    out.append("- Bugs whose keywords need updating in ground_truth.json")
    out.append("")
    for arm in arms_sorted:
        unm = per_arm[arm]["all_unmatched_findings"]
        if not unm:
            out.append(f"### {arm} — no unmatched findings")
            out.append("")
            continue
        out.append(f"### {arm} — {len(unm)} unmatched findings")
        for snippet, u in unm:
            out.append(f"- `{snippet}`: **{u['title']}** — {u['description']}")
        out.append("")

    return "\n".join(out)

# ─── MAIN ─────────────────────────────────────────────────────────────────

def main():
    here = Path(__file__).parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(here / "results.json"))
    ap.add_argument("--ground-truth", default=str(here / "ground_truth.json"))
    ap.add_argument("--output", default=str(here / "report.md"))
    args = ap.parse_args()

    results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    gt = json.loads(Path(args.ground_truth).read_text(encoding="utf-8"))

    report = render_report(results, gt)
    Path(args.output).write_text(report, encoding="utf-8")
    print(f"Report written to {args.output}")
    print("\n" + report)

if __name__ == "__main__":
    main()
