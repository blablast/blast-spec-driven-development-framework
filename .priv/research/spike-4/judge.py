#!/usr/bin/env python3
"""
spike-4 judge — Claude Opus rates each (task, arm) output on quality rubric.

Subjective quality dimensions (1-5 scale):
  - idiomatic: Pythonic conventions, naming, structure
  - security: input validation, error handling, no obvious holes
  - performance: appropriate algorithms, no O(n^2) where O(n) works
  - readability: comments where needed, clear flow
  - completeness: handles edge cases beyond just the test cases

Plus binary check: does code "look correct" or has obvious bugs (orthogonal to pytest).

Required env: ANTHROPIC_API_KEY (or claude CLI in PATH for fallback)

Usage:
  python judge.py --results results/results.json --output results/judge_scores.json
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
TASKS_DIR = ROOT_DIR / "tasks"

CLAUDE_CLI = shutil.which("claude")
JUDGE_MODEL = "claude-opus-4-6"

RUBRIC_PROMPT = """You are an expert code reviewer. Rate the implementation below on a 1-5 scale across 5 dimensions.

# Task spec the implementation should fulfill

{task_md}

# Implementation under review

```python
{impl_code}
```

# Rubric (rate each 1-5)

- **idiomatic**: Pythonic conventions, naming, no anti-patterns. 1=non-idiomatic, 5=production-quality
- **security**: input validation, error handling, no obvious holes (injection, race, leak). 1=multiple holes, 5=hardened
- **performance**: appropriate algorithms/data structures, no O(n^2) where O(n) works. 1=clearly inefficient, 5=optimal for spec
- **readability**: clear flow, comments where non-obvious, sensible function decomposition. 1=opaque, 5=self-documenting
- **completeness**: handles edge cases (empty input, None, type errors, concurrency) beyond just test cases. 1=happy path only, 5=defensive

Plus binary judgment:
- **looks_correct**: TRUE/FALSE — does the logic appear to match the spec? (orthogonal to test results)

# Output format (strict JSON, no prose)

```json
{{
  "idiomatic": <1-5>,
  "security": <1-5>,
  "performance": <1-5>,
  "readability": <1-5>,
  "completeness": <1-5>,
  "looks_correct": true or false,
  "notable_issues": ["short bullet 1", "short bullet 2"],
  "notable_strengths": ["short bullet 1", "short bullet 2"]
}}
```

End with the literal closing brace. No prose before or after.
"""


def call_judge(prompt: str, timeout: int = 240):
    """Use claude CLI to invoke Opus. Returns (text, cost_usd, latency_s)."""
    if not CLAUDE_CLI:
        raise RuntimeError("claude CLI not in PATH")
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="spike4-judge-") as tmpdir:
        cmd = [CLAUDE_CLI, "-p", prompt, "--model", JUDGE_MODEL, "--output-format", "json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=tmpdir, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI exit {proc.returncode}: {proc.stderr[:300]}")

    text = proc.stdout
    cost_usd = 0.0
    try:
        events = json.loads(proc.stdout)
        if isinstance(events, list):
            for ev in events:
                if isinstance(ev, dict) and ev.get("type") == "result":
                    text = ev.get("result", text)
                    cost_usd = float(ev.get("total_cost_usd", 0.0) or 0.0)
                    break
    except (json.JSONDecodeError, ValueError):
        pass

    return text, cost_usd, time.time() - t0


def parse_judge_response(text: str):
    """Extract JSON object from text (strict)."""
    # Find first { and last }
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0 or end <= start:
        return None
    candidate = text[start:end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # Try removing markdown fence
        candidate2 = candidate.replace("```json", "").replace("```", "")
        try:
            return json.loads(candidate2)
        except json.JSONDecodeError:
            return None


def find_impl_file(arm_dir: Path):
    """The impl file is whichever .py is NOT tests.py / conftest.py."""
    for f in arm_dir.glob("*.py"):
        if f.name not in ("tests.py", "conftest.py"):
            return f
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results", default=str(ROOT_DIR / "results" / "results.json"))
    p.add_argument("--output", default=str(ROOT_DIR / "results" / "judge_scores.json"))
    p.add_argument("--skip-failed", action="store_true",
                   help="Skip arms that failed to extract code")
    args = p.parse_args()

    runs = json.loads(Path(args.results).read_text(encoding="utf-8"))
    judge_results = []

    for run in runs:
        arm = run["arm"]
        task = run["task"]
        if args.skip_failed and not run.get("code_extracted"):
            continue

        task_dir = TASKS_DIR / task
        arm_dir = task_dir / arm
        impl_file = find_impl_file(arm_dir)
        if not impl_file or not impl_file.exists():
            judge_results.append({"arm": arm, "task": task, "error": "no impl file found"})
            continue

        task_md = (task_dir / "task.md").read_text(encoding="utf-8")
        impl_code = impl_file.read_text(encoding="utf-8")

        prompt = RUBRIC_PROMPT.format(task_md=task_md, impl_code=impl_code)

        print(f"  Judging [{arm}] {task}...", file=sys.stderr, flush=True)
        try:
            text, cost, latency = call_judge(prompt)
        except Exception as e:
            judge_results.append({"arm": arm, "task": task, "error": f"{type(e).__name__}: {e}"})
            continue

        scores = parse_judge_response(text)
        if not scores:
            judge_results.append({"arm": arm, "task": task, "error": "could not parse judge JSON",
                                  "raw_tail": text[-500:]})
            continue

        scores["arm"] = arm
        scores["task"] = task
        scores["judge_cost_usd"] = cost
        scores["judge_latency_s"] = latency
        scores["composite"] = (
            scores.get("idiomatic", 0) + scores.get("security", 0) +
            scores.get("performance", 0) + scores.get("readability", 0) +
            scores.get("completeness", 0)
        ) / 5.0
        judge_results.append(scores)

        print(f"    composite {scores['composite']:.2f} (idiom={scores.get('idiomatic')}, "
              f"sec={scores.get('security')}, perf={scores.get('performance')}, "
              f"read={scores.get('readability')}, comp={scores.get('completeness')}) "
              f"${cost:.4f}",
              file=sys.stderr, flush=True)

    Path(args.output).write_text(
        json.dumps(judge_results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nJudge scores: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
