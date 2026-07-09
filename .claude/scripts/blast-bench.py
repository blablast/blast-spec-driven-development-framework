#!/usr/bin/env python3
"""
blast-bench - LLM throughput benchmark for the cluster.

Two non-trivial tasks, run against N local Ollama models, 2x per model
(cold + warm), measures wall time, tokens/sec, output sanity.

Tasks:
  - analytical: validate-design audit on a realistic OAuth design
  - coding:     TDD impl of a non-trivial function (rate limiter)

Usage:
  python3 .claude/scripts/blast-bench.py                      # all models, both tasks
  python3 .claude/scripts/blast-bench.py --task coding        # coders only
  python3 .claude/scripts/blast-bench.py --task analytical    # critics only
  python3 .claude/scripts/blast-bench.py --models qwen3.6:latest,glm-4.6:cloud
  python3 .claude/scripts/blast-bench.py --runs 1             # single-run only (skip warm)
  # vLLM batch engine (start blast-vllm-batch.sh first — it opens the GPU window):
  python3 .claude/scripts/blast-bench.py --engine vllm --task coding
  python3 .claude/scripts/blast-bench.py --engine vllm --base-url http://localhost:8001

Output:
  - Markdown table per task to stdout
  - Optional --output <path> writes full transcript JSON

Dependencies:
  pip install httpx
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx", file=sys.stderr)
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

ENDPOINTS = {
    "ubuntu": "http://192.168.5.60:11434",
    # win11 (4090) absent — 32B models hit VRAM ceiling on 24 GB card
    # (CPU offload ~5 tok/s). Re-add when smaller models or Q3 quants tested.
}

# (machine, model_tag, roles, thinking)
# thinking=True  → reasoning model (qwen3.6 family). On `coding` task we disable
#                  thinking (`/no_think` + `think: false`) so num_predict is not
#                  burned on reasoning before the code block is emitted.
# thinking=False → coder/instruct model, emits output directly.
MODELS = [
    ("ubuntu", "qwen3.6:latest",         ["analytical", "coding"], True),
    ("ubuntu", "qwen3.6:27b",            ["analytical", "coding"], True),
    ("ubuntu", "qwen3-coder:30b",        ["coding"],               False),
    ("ubuntu", "qwen3-coder-next",       ["coding"],               False),
]

TIMEOUT_S = 360  # cold loads (qwen3-coder-next ~48GB) can be slow

# ─────────────────────────────────────────────────────────────────────────────
# TASKS — non-trivial, realistic for blast use cases
# ─────────────────────────────────────────────────────────────────────────────

TASK_ANALYTICAL = """You are a senior reviewer. Audit this technical design for User Authentication via OAuth2. Find weaknesses in security, concurrency, error handling, observability.

# Design: User Authentication via OAuth2

## Requirements
- Users log in with Google / GitHub OAuth2
- Sessions persist across page reloads
- Logout revokes session locally and at provider
- API calls use access token from session

## Architecture (layered)
- AuthController: /login (redirect to provider), /callback (exchange code), /logout
- TokenService: encrypt/decrypt, refresh logic, expiry tracking
- ProviderAdapter: OAuth2 specifics per provider (Google, GitHub)
- SessionStorage: Redis-backed active sessions

## Flow
1. User hits /login -> AuthController redirects to provider's authorize URL
2. Provider redirects back to /callback with auth code
3. AuthController calls TokenService.exchange_code(code) -> {access_token, refresh_token}
4. TokenService stores encrypted tokens in HttpOnly cookie (web) or Keychain (mobile)
5. Subsequent API calls include Bearer token
6. On token expiry, TokenService.refresh() kicks in transparently
7. /logout: TokenService.revoke() at provider + clear local session

## Verification Strategy
- Unit tests on TokenService encryption
- Smoke check: AuthController instantiation
- E2E probe: curl /login expects 302 redirect

Find at least 3 weaknesses. For each:
- Severity (CRITICAL / WARNING / INFO)
- What's wrong (1-2 sentences)
- Why it matters
- Suggested fix or question

End with verdict envelope:
---VERDICT---
VERDICT: PASS|WARN|FAIL
BLOCKING: true|false
FINDINGS: <count>
NEXT_ACTIONS:
- ...
---END---
"""

TASK_CODING = """Implement a Python token-bucket rate limiter that passes the failing test below. Use only stdlib (no external deps). Code must be thread-safe. Include the implementation as a single ```python code block at the end.

# Failing test (must pass)
```python
import threading, time
from rate_limiter import RateLimiter

def test_basic_acquire():
    rl = RateLimiter(rate=2.0, burst=4)        # 2 tokens/sec, capacity 4
    # Bucket starts full -> 4 acquires should succeed immediately
    for _ in range(4):
        assert rl.try_acquire() is True
    # 5th immediately should fail (bucket empty)
    assert rl.try_acquire() is False

def test_refill():
    rl = RateLimiter(rate=10.0, burst=2)        # 10 tokens/sec
    assert rl.try_acquire(2) is True            # drain
    assert rl.try_acquire() is False
    time.sleep(0.25)                             # 0.25s * 10 = 2.5 tokens refilled
    assert rl.try_acquire(2) is True
    assert rl.try_acquire() is False

def test_thread_safety():
    rl = RateLimiter(rate=1000.0, burst=100)
    successes = []
    def worker():
        for _ in range(50):
            if rl.try_acquire():
                successes.append(1)
    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    # Total tries = 500; bucket can give max 100 + small refill during execution
    assert 100 <= len(successes) <= 200
```

# Spec
- Class `RateLimiter`
- Constructor `(rate: float, burst: int)`: rate = tokens/sec, burst = bucket capacity
- Method `try_acquire(tokens: int = 1) -> bool`: non-blocking attempt
- Use monotonic clock, lazy refill (compute on each call), threading.Lock
- File path: `rate_limiter.py`

Provide ONLY the implementation in a ```python ... ``` block. No prose, no explanation, no preamble.
"""

TASKS = {
    "analytical": TASK_ANALYTICAL,
    "coding": TASK_CODING,
}


# ─────────────────────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RunResult:
    machine: str
    model: str
    task: str
    run_idx: int                    # 1 = cold, 2 = warm
    elapsed_s: float
    tokens_in: int
    tokens_out: int
    tokens_per_sec: float
    ollama_total_s: float
    ollama_eval_s: float
    response_chars: int
    response_preview: str = ""
    error: str = ""


def run_one(machine: str, model: str, task: str, prompt: str, run_idx: int,
            thinking: bool = False) -> RunResult:
    endpoint = ENDPOINTS[machine]
    url = f"{endpoint}/api/generate"
    # Belt-and-suspenders thinking gate for coding task on reasoning models:
    #   - top-level `think: false` (Ollama 0.5+)
    #   - `/no_think` suffix (Qwen3 control token, works on older Ollama too)
    final_prompt = prompt
    extra: dict = {}
    if thinking and task == "coding":
        final_prompt = prompt + "\n\n/no_think"
        extra["think"] = False
    payload = {
        "model": model,
        "prompt": final_prompt,
        "stream": False,
        "options": {
            "num_predict": 4096,
            "num_ctx": 8192,         # cap context to keep KV cache small
            "temperature": 0.2,
        },
        **extra,
    }
    t0 = time.time()
    try:
        with httpx.Client(timeout=TIMEOUT_S) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        return RunResult(machine, model, task, run_idx,
                         elapsed_s=time.time() - t0, tokens_in=0, tokens_out=0,
                         tokens_per_sec=0.0, ollama_total_s=0.0, ollama_eval_s=0.0,
                         response_chars=0, error=f"TIMEOUT after {TIMEOUT_S}s")
    except httpx.ConnectError as e:
        return RunResult(machine, model, task, run_idx,
                         elapsed_s=time.time() - t0, tokens_in=0, tokens_out=0,
                         tokens_per_sec=0.0, ollama_total_s=0.0, ollama_eval_s=0.0,
                         response_chars=0, error=f"CONNECT_ERROR: {e}")
    except httpx.HTTPStatusError as e:
        return RunResult(machine, model, task, run_idx,
                         elapsed_s=time.time() - t0, tokens_in=0, tokens_out=0,
                         tokens_per_sec=0.0, ollama_total_s=0.0, ollama_eval_s=0.0,
                         response_chars=0,
                         error=f"HTTP_{e.response.status_code}: {e.response.text[:160]}")
    except Exception as e:
        return RunResult(machine, model, task, run_idx,
                         elapsed_s=time.time() - t0, tokens_in=0, tokens_out=0,
                         tokens_per_sec=0.0, ollama_total_s=0.0, ollama_eval_s=0.0,
                         response_chars=0, error=f"{type(e).__name__}: {e}")

    elapsed = time.time() - t0
    response = data.get("response", "")
    tokens_in = data.get("prompt_eval_count", 0)
    tokens_out = data.get("eval_count", 0)
    eval_dur_ns = data.get("eval_duration", 0)
    total_dur_ns = data.get("total_duration", 0)
    eval_s = eval_dur_ns / 1_000_000_000
    total_s = total_dur_ns / 1_000_000_000
    tps = tokens_out / eval_s if eval_s > 0 else 0.0

    # Sanity preview: first 80 chars of response, single line
    preview = " ".join(response[:160].split())[:80]

    return RunResult(
        machine=machine, model=model, task=task, run_idx=run_idx,
        elapsed_s=elapsed, tokens_in=tokens_in, tokens_out=tokens_out,
        tokens_per_sec=tps, ollama_total_s=total_s, ollama_eval_s=eval_s,
        response_chars=len(response), response_preview=preview, error="",
    )


def run_one_vllm(base_url: str, model: str, task: str, prompt: str, run_idx: int) -> RunResult:
    """Run a task against a vLLM OpenAI-compatible server (/v1/completions).

    vLLM is the BATCH engine (decision 2026-07-09) — use via `blast-vllm-batch.sh`,
    which opens a GPU window and serves this endpoint. tok/s is wall-clock based
    (no server-side eval_duration like Ollama exposes)."""
    url = f"{base_url}/v1/completions"
    payload = {
        "model": model,
        "prompt": prompt,
        "max_tokens": 4096,
        "temperature": 0.2,
    }

    def _err(msg: str) -> RunResult:
        return RunResult("vllm", model, task, run_idx, elapsed_s=time.time() - t0,
                         tokens_in=0, tokens_out=0, tokens_per_sec=0.0,
                         ollama_total_s=0.0, ollama_eval_s=0.0, response_chars=0, error=msg)

    t0 = time.time()
    try:
        with httpx.Client(timeout=TIMEOUT_S) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        return _err(f"TIMEOUT after {TIMEOUT_S}s")
    except httpx.ConnectError as e:
        return _err(f"CONNECT_ERROR: {e} (is blast-vllm-batch running on {base_url}?)")
    except httpx.HTTPStatusError as e:
        return _err(f"HTTP_{e.response.status_code}: {e.response.text[:160]}")
    except Exception as e:
        return _err(f"{type(e).__name__}: {e}")

    elapsed = time.time() - t0
    choices = data.get("choices") or [{}]
    text = choices[0].get("text", "") or ""
    usage = data.get("usage", {}) or {}
    tokens_in = usage.get("prompt_tokens", 0)
    tokens_out = usage.get("completion_tokens", 0)
    tps = tokens_out / elapsed if elapsed > 0 else 0.0
    preview = " ".join(text[:160].split())[:80]
    return RunResult(
        machine="vllm", model=model, task=task, run_idx=run_idx,
        elapsed_s=elapsed, tokens_in=tokens_in, tokens_out=tokens_out,
        tokens_per_sec=tps, ollama_total_s=elapsed, ollama_eval_s=elapsed,
        response_chars=len(text), response_preview=preview, error="",
    )


def render_table(results: list[RunResult], task: str) -> str:
    out = []
    out.append(f"\n## Task: `{task}`")
    out.append("")
    out.append("| Machine | Model | Run | Wall (s) | Ollama eval (s) | Tokens out | Tok/s | Response chars | Status |")
    out.append("|---|---|---:|---:|---:|---:|---:|---:|---|")
    for r in [x for x in results if x.task == task]:
        status = "OK" if not r.error else r.error[:60]
        out.append(
            f"| {r.machine} | `{r.model}` | {r.run_idx} | "
            f"{r.elapsed_s:.1f} | {r.ollama_eval_s:.1f} | "
            f"{r.tokens_out} | {r.tokens_per_sec:.1f} | {r.response_chars} | {status} |"
        )
    out.append("")
    # Cold vs warm summary
    out.append("**Cold vs warm delta** (run 2 / run 1, lower is better — model warmed up):")
    out.append("")
    out.append("| Machine | Model | Cold (s) | Warm (s) | Speedup |")
    out.append("|---|---|---:|---:|---:|")
    grouped: dict[tuple[str, str], list[RunResult]] = {}
    for r in results:
        if r.task != task or r.error:
            continue
        grouped.setdefault((r.machine, r.model), []).append(r)
    for (m, mod), runs in grouped.items():
        runs.sort(key=lambda x: x.run_idx)
        if len(runs) >= 2:
            cold, warm = runs[0].elapsed_s, runs[1].elapsed_s
            speedup = cold / warm if warm > 0 else 0
            out.append(f"| {m} | `{mod}` | {cold:.1f} | {warm:.1f} | {speedup:.2f}x |")
    out.append("")
    return "\n".join(out)


def render_preview(results: list[RunResult], task: str) -> str:
    out = []
    out.append(f"\n## Response previews — `{task}` (first 80 chars, warm run)")
    out.append("")
    grouped: dict[tuple[str, str], list[RunResult]] = {}
    for r in results:
        if r.task != task or r.error:
            continue
        grouped.setdefault((r.machine, r.model), []).append(r)
    for (m, mod), runs in grouped.items():
        runs.sort(key=lambda x: x.run_idx)
        if len(runs) >= 2:
            warm = runs[1]
            out.append(f"- **{m}/{mod}** — `{warm.response_preview}`")
    out.append("")
    return "\n".join(out)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["analytical", "coding", "both"], default="both")
    parser.add_argument("--models", help="comma-separated model tags filter (e.g., 'qwen3.6:latest,glm-4.6:cloud')")
    parser.add_argument("--runs", type=int, default=2, help="how many runs per (model,task), default 2 (cold+warm)")
    parser.add_argument("--output", help="optional path to write full JSON transcript")
    parser.add_argument("--sleep", type=float, default=2.0, help="seconds between runs (default 2)")
    parser.add_argument("--engine", choices=["ollama", "vllm"], default="ollama",
                        help="ollama (default, /api/generate) or vllm (OpenAI /v1/completions — batch window)")
    parser.add_argument("--base-url", help="override endpoint (vllm default http://localhost:8001)")
    parser.add_argument("--vllm-model", default="QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ",
                        help="served model id when --engine vllm (used if --models not given)")
    args = parser.parse_args(argv)

    tasks = ["analytical", "coding"] if args.task == "both" else [args.task]
    model_filter = set(m.strip() for m in args.models.split(",")) if args.models else None

    # vLLM path: single OpenAI-compatible endpoint, one served model (the coder).
    # Decision 2026-07-09 — vLLM is the BATCH engine; start it with blast-vllm-batch.sh first.
    if args.engine == "vllm":
        base_url = args.base_url or "http://localhost:8001"
        vmodels = sorted(model_filter) if model_filter else [args.vllm_model]
        print(f"# blast-bench (vLLM) — {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        print(f"\n**Engine**: vLLM @ {base_url}\n**Models**: {vmodels}\n**Tasks**: {tasks}\n"
              f"**Runs**: {args.runs}\n**Timeout**: {TIMEOUT_S}s\n")
        results: list[RunResult] = []
        plan_v = [(m, t) for m in vmodels for t in tasks]
        print(f"**Planned runs**: {len(plan_v) * args.runs}\n")
        for i, (model, task) in enumerate(plan_v, 1):
            print(f"[{i}/{len(plan_v)}] vllm/{model} — task={task}", file=sys.stderr, flush=True)
            for run_idx in range(1, args.runs + 1):
                print(f"   run {run_idx}/{args.runs}...", end="", file=sys.stderr, flush=True)
                r = run_one_vllm(base_url, model, task, TASKS[task], run_idx)
                results.append(r)
                if r.error:
                    print(f" {r.error}", file=sys.stderr)
                    break
                print(f" {r.elapsed_s:.1f}s ({r.tokens_per_sec:.1f} tok/s)", file=sys.stderr)
                time.sleep(args.sleep)
        for t in tasks:
            print(render_table(results, t))
            print(render_preview(results, t))
        if args.output:
            payload_json = json.dumps([asdict(r) for r in results], indent=2, ensure_ascii=False)
            try:
                Path(args.output).write_text(payload_json, encoding="utf-8")
                print(f"\nFull transcript written to {args.output}", file=sys.stderr)
            except (PermissionError, OSError) as e:
                fb = Path(f"/tmp/{Path(args.output).name}")
                fb.write_text(payload_json, encoding="utf-8")
                print(f"\nWARNING: {e}; fallback {fb}", file=sys.stderr)
        return 1 if any(r.error for r in results) else 0

    print(f"# blast-bench results — {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"\n**Endpoints**: {ENDPOINTS}")
    print(f"**Tasks**: {tasks}")
    print(f"**Runs per (model,task)**: {args.runs}")
    print(f"**Timeout**: {TIMEOUT_S}s\n")

    results: list[RunResult] = []

    plan = []
    for machine, model, roles, thinking in MODELS:
        if model_filter and model not in model_filter:
            continue
        for t in tasks:
            if t in roles:
                plan.append((machine, model, t, thinking))

    print(f"**Planned runs**: {len(plan) * args.runs}")
    print(f"**Models in plan**: {sorted(set(m for _, m, _, _ in plan))}")
    print()

    for i, (machine, model, task, thinking) in enumerate(plan, 1):
        print(f"[{i}/{len(plan)}] {machine}/{model} — task={task}", file=sys.stderr, flush=True)
        prompt = TASKS[task]
        for run_idx in range(1, args.runs + 1):
            print(f"   run {run_idx}/{args.runs}...", end="", file=sys.stderr, flush=True)
            r = run_one(machine, model, task, prompt, run_idx, thinking)
            results.append(r)
            if r.error:
                print(f" {r.error}", file=sys.stderr)
                break
            print(f" {r.elapsed_s:.1f}s ({r.tokens_per_sec:.1f} tok/s)", file=sys.stderr)
            time.sleep(args.sleep)

    # Render all tables
    for t in tasks:
        print(render_table(results, t))
        print(render_preview(results, t))

    # Optional JSON dump — fall back to /tmp/ on permission errors
    # (OneDrive sync conflicts, root-owned dirs, etc.)
    if args.output:
        payload_json = json.dumps([asdict(r) for r in results], indent=2, ensure_ascii=False)
        path = Path(args.output)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload_json, encoding="utf-8")
            print(f"\nFull transcript written to {path}", file=sys.stderr)
        except (PermissionError, OSError) as e:
            fallback = Path(f"/tmp/{path.name}")
            fallback.write_text(payload_json, encoding="utf-8")
            print(f"\nWARNING: could not write {path} ({type(e).__name__}: {e})", file=sys.stderr)
            print(f"Fallback transcript written to {fallback}", file=sys.stderr)

    # Exit code: 0 if all OK, 1 if any errors
    has_errors = any(r.error for r in results)
    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
