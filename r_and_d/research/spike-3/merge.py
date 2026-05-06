#!/usr/bin/env python3
"""
Merge multiple spike-3 results.json files.

Later files override earlier ones on (arm, snippet) collision. This is the
typical re-run flow: run full pipeline → identify failed arms → re-run only
those arms → merge.

Usage:
    # results-qwen.json overrides results.json on shared keys
    python3 merge.py results.json results-qwen.json --output results-final.json
    python3 score.py --results results-final.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+",
                    help="results JSON files in priority order; later overrides earlier")
    ap.add_argument("--output", default="results-merged.json")
    args = ap.parse_args()

    merged: dict[tuple[str, str], dict] = {}
    sources: dict[tuple[str, str], str] = {}
    for path in args.inputs:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        n_added = n_replaced = 0
        for entry in data:
            key = (entry["arm"], entry["snippet"])
            if key in merged:
                n_replaced += 1
            else:
                n_added += 1
            merged[key] = entry
            sources[key] = path
        print(f"  {path}: +{n_added} new, ~{n_replaced} replaced")

    out = list(merged.values())
    out.sort(key=lambda e: (e["snippet"], e["arm"]))
    Path(args.output).write_text(
        json.dumps(out, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Summary breakdown by arm
    by_arm: dict[str, dict] = {}
    for entry in out:
        a = entry["arm"]
        by_arm.setdefault(a, {"n": 0, "errors": 0, "findings": 0})
        by_arm[a]["n"] += 1
        if entry.get("error"):
            by_arm[a]["errors"] += 1
        by_arm[a]["findings"] += len(entry.get("findings", []))

    print(f"\nMerged {len(out)} entries into {args.output}")
    print(f"\nPer-arm summary:")
    for arm, s in sorted(by_arm.items()):
        print(f"  {arm:14} {s['n']:>2} runs, {s['errors']} errors, {s['findings']:>3} total findings")


if __name__ == "__main__":
    main()
