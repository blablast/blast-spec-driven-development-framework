#!/usr/bin/env python3
"""
spike-4 driver — head-to-head qwen3-coder:30b vs claude-sonnet-4-6 on coding tasks.

For each (arm, task):
  1. Send prompt: task.md + tests.py + "implement"
  2. Save model output as <task>/<arm>/impl.py + copy tests.py
  3. Run pytest, capture pass/fail per test + total time
  4. Record latency, tokens, cost

Required env:
  ANTHROPIC_API_KEY (optional — uses claude CLI if absent)
  BLAST_OLLAMA_UBUNTU (default http://192.168.5.60:11434)

Usage:
  python driver.py
  python driver.py --tasks 01_token_bucket,02_lru_cache_ttl
  python driver.py --arms qwen,sonnet
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx", file=sys.stderr)
    sys.exit(1)

ROOT_DIR = Path(__file__).resolve().parent
TASKS_DIR = ROOT_DIR / "tasks"
RESULTS_DIR = ROOT_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

OLLAMA = os.environ.get("BLAST_OLLAMA_UBUNTU", "http://192.168.5.60:11434")
CLAUDE_CLI = shutil.which("claude")

PROMPT_TEMPLATE = """You are an expert Python engineer. Implement the spec below.

# Task spec

{task_md}

# Tests that must pass

```python
{tests_py}
```

# Instructions

- Output ONE Python file as ```python ... ``` block. NO prose, NO preamble.
- Pure stdlib only.
- Match exact module name expected by tests (e.g. `from rate_limiter import ...` -> file `rate_limiter.py`).
"""

CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


@dataclass
class RunResult:
    arm: str
    task: str
    latency_s: float = 0.0
    cost_usd: float = 0.0
    in_tok: int = 0
    out_tok: int = 0
    output_chars: int = 0
    code_extracted: bool = False
    pytest_passed: int = 0
    pytest_failed: int = 0
    pytest_errors: int = 0
    pytest_total: int = 0
    pytest_pass_rate: float = 0.0
    pytest_log: str = ""
    error: str = ""


def call_claude_cli(prompt: str, model: str = "claude-sonnet-4-6", timeout: int = 300):
    if not CLAUDE_CLI:
        raise RuntimeError("claude CLI not available")
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="spike4-") as tmpdir:
        cmd = [CLAUDE_CLI, "-p", prompt, "--model", model, "--output-format", "json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=tmpdir, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI exit {proc.returncode}: {proc.stderr[:200]}")
    text = proc.stdout
    in_tok = out_tok = 0
    cost_usd = 0.0
    try:
        events = json.loads(proc.stdout)
        if isinstance(events, list):
            for ev in events:
                if isinstance(ev, dict) and ev.get("type") == "result":
                    text = ev.get("result", text)
                    cost_usd = float(ev.get("total_cost_usd", 0.0) or 0.0)
                    usage = ev.get("usage", {}) or {}
                    in_tok = (usage.get("input_tokens", 0) or 0) + \
                             (usage.get("cache_read_input_tokens", 0) or 0) + \
                             (usage.get("cache_creation_input_tokens", 0) or 0)
                    out_tok = usage.get("output_tokens", 0) or 0
                    break
    except (json.JSONDecodeError, ValueError):
        pass
    return text, {"latency_s": time.time() - t0, "cost_usd": cost_usd, "in_tok": in_tok, "out_tok": out_tok}


def call_qwen_coder(prompt: str, model: str = "qwen3-coder:30b", timeout: int = 300):
    t0 = time.time()
    resp = httpx.post(
        f"{OLLAMA}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "30m",
            "options": {"num_predict": 8192, "num_ctx": 16384, "temperature": 0.2},
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", ""), {
        "latency_s": time.time() - t0,
        "cost_usd": 0.0,
        "in_tok": data.get("prompt_eval_count", 0),
        "out_tok": data.get("eval_count", 0),
    }


def extract_code(response_text: str):
    m = CODE_BLOCK_RE.search(response_text)
    if m:
        return m.group(1).strip()
    if "import" in response_text or "def " in response_text or "class " in response_text:
        return response_text.strip()
    return None


def run_task(arm: str, task_dir: Path) -> RunResult:
    task_name = task_dir.name
    result = RunResult(arm=arm, task=task_name)

    task_md = (task_dir / "task.md").read_text(encoding="utf-8")
    tests_py = (task_dir / "tests.py").read_text(encoding="utf-8")
    prompt = PROMPT_TEMPLATE.format(task_md=task_md, tests_py=tests_py)

    print(f"  [{arm}] {task_name} -- calling model...", file=sys.stderr, flush=True)
    try:
        if arm == "qwen":
            text, meta = call_qwen_coder(prompt)
        elif arm == "sonnet":
            text, meta = call_claude_cli(prompt, model="claude-sonnet-4-6")
        else:
            raise ValueError(f"Unknown arm: {arm}")
    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"
        return result

    result.latency_s = meta["latency_s"]
    result.cost_usd = meta["cost_usd"]
    result.in_tok = meta["in_tok"]
    result.out_tok = meta["out_tok"]
    result.output_chars = len(text)

    code = extract_code(text)
    if not code:
        result.error = "no code block in response"
        return result
    result.code_extracted = True

    arm_dir = task_dir / arm
    arm_dir.mkdir(exist_ok=True)
    (arm_dir / "raw_response.txt").write_text(text, encoding="utf-8")

    m_imp = re.search(r"^from\s+(\w+)\s+import", tests_py, re.MULTILINE)
    module_name = m_imp.group(1) if m_imp else "impl"
    (arm_dir / f"{module_name}.py").write_text(code, encoding="utf-8")
    shutil.copy(task_dir / "tests.py", arm_dir / "tests.py")

    # Copy conftest + pyproject for async test support
    for cfg in ["conftest.py", "pyproject.toml"]:
        src = ROOT_DIR / cfg
        if src.exists():
            shutil.copy(src, arm_dir / cfg)

    print(f"  [{arm}] {task_name} -- running pytest...", file=sys.stderr, flush=True)
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests.py", "-v", "--tb=short"],
            capture_output=True, text=True, timeout=120, cwd=arm_dir,
        )
    except subprocess.TimeoutExpired:
        result.error = "pytest timeout"
        result.pytest_log = "TIMEOUT after 120s"
        return result

    log = proc.stdout + "\n" + proc.stderr
    result.pytest_log = log[-3000:]

    result.pytest_passed = log.count(" PASSED")
    result.pytest_failed = log.count(" FAILED")
    result.pytest_errors = log.count(" ERROR")
    result.pytest_total = result.pytest_passed + result.pytest_failed + result.pytest_errors
    if result.pytest_total:
        result.pytest_pass_rate = result.pytest_passed / result.pytest_total

    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tasks", help="Comma-separated task dir names")
    p.add_argument("--arms", default="qwen,sonnet")
    p.add_argument("--output", default=str(RESULTS_DIR / "results.json"))
    args = p.parse_args()

    if args.tasks:
        tasks = [TASKS_DIR / t.strip() for t in args.tasks.split(",")]
    else:
        tasks = sorted([d for d in TASKS_DIR.iterdir() if d.is_dir()])
    arms = [a.strip() for a in args.arms.split(",")]

    print(f"Spike-4: {len(tasks)} tasks x {len(arms)} arms = {len(tasks) * len(arms)} runs", file=sys.stderr)
    print(f"Tasks: {[t.name for t in tasks]}", file=sys.stderr)
    print(f"Arms: {arms}", file=sys.stderr)

    results = []
    for task_dir in tasks:
        for arm in arms:
            r = run_task(arm, task_dir)
            results.append(r)
            tag = "OK" if not r.error else f"ERR: {r.error[:60]}"
            print(f"  -> {r.pytest_passed}/{r.pytest_total} pass  {r.latency_s:5.1f}s  ${r.cost_usd:.4f}  {tag}",
                  file=sys.stderr, flush=True)

    Path(args.output).write_text(
        json.dumps([asdict(r) for r in results], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nResults: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
