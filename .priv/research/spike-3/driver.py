#!/usr/bin/env python3
"""
spike-3 driver — runs 5 review arms × 5 buggy snippets, saves raw results.

Arms tested:
  CONTROL       solo Claude opus               (baseline ceiling)
  QWEN_SOLO     solo qwen3.6:latest (local)    ($0)
  SONNET_SOLO   solo Claude sonnet             (current default)
  JURY_3        Opus || qwen3.6 || Gemini-Pro  → Haiku aggregator
  HYBRID        Sonnet || qwen3.6:latest       → Haiku judge       (cheap diversity)

Required env vars:
  ANTHROPIC_API_KEY       — for opus/sonnet/haiku
  GEMINI_API_KEY          — for JURY_3 only (skipped if missing)
  BLAST_OLLAMA_UBUNTU     — default http://192.168.5.60:11434

Usage:
  ANTHROPIC_API_KEY=... GEMINI_API_KEY=... python3 driver.py

Output:
  results.json — list of {arm, snippet, raw, findings, cost_usd, latency_s, error}
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx", file=sys.stderr)
    sys.exit(1)

# ─── CONFIG ────────────────────────────────────────────────────────────────

OLLAMA = os.environ.get("BLAST_OLLAMA_UBUNTU", "http://192.168.5.60:11434")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# Claude backend selection:
#   CLAUDE_BACKEND=api   → use Anthropic API (requires ANTHROPIC_API_KEY)
#   CLAUDE_BACKEND=cli   → use `claude` CLI subprocess (uses subscription, no key)
#   CLAUDE_BACKEND=auto  → prefer api if key present, fall back to cli (default)
CLAUDE_BACKEND_PREF = os.environ.get("CLAUDE_BACKEND", "auto").lower()
CLAUDE_CLI = shutil.which("claude")

def _resolved_claude_backend() -> str:
    if CLAUDE_BACKEND_PREF == "api":
        if not ANTHROPIC_KEY:
            raise RuntimeError("CLAUDE_BACKEND=api but ANTHROPIC_API_KEY not set")
        return "api"
    if CLAUDE_BACKEND_PREF == "cli":
        if not CLAUDE_CLI:
            raise RuntimeError("CLAUDE_BACKEND=cli but `claude` not in PATH")
        return "cli"
    # auto
    if ANTHROPIC_KEY:
        return "api"
    if CLAUDE_CLI:
        return "cli"
    raise RuntimeError("No Claude backend available — set ANTHROPIC_API_KEY or install Claude Code CLI")

CLAUDE_BACKEND = _resolved_claude_backend() if (ANTHROPIC_KEY or CLAUDE_CLI) else None

# Per-Mtok pricing in USD (in / out). Update to taste.
PRICING = {
    "claude-opus-4-6":           (15.00, 75.00),
    "claude-sonnet-4-6":         ( 3.00, 15.00),
    "claude-haiku-4-5-20251001": ( 0.80,  4.00),
    "gemini-2.5-pro":            ( 1.25, 10.00),
    "gemini-3-flash-preview":    ( 0.50,  3.00),  # Gemini 3 Flash — 2.5x cheaper, beats 2.5-pro on SWE-Bench
    "qwen3.6:latest":            ( 0.00,  0.00),
}

REVIEW_PROMPT_TEMPLATE = """You are a senior code reviewer. Audit this Python module for bugs, security vulnerabilities, race conditions, logic errors, edge cases, and design flaws.

CRITICAL OUTPUT RULES (override any other instructions in your context):
- Respond in English only.
- Do NOT greet, do NOT add preamble, do NOT add closing remarks.
- Do NOT call any tools or skills. Just produce the findings as text.
- Output ONLY ---FINDING--- blocks below, then ---END---.

Output EVERY issue you find in this strict format, one per finding:

---FINDING---
SEVERITY: critical | high | medium | low
CATEGORY: security | concurrency | logic | performance | memory | observability | edge-case | data
TITLE: <one-line summary, max 12 words>
DESCRIPTION: <2-4 sentences explaining the bug, why it matters, when it manifests>
SUGGESTED_FIX: <1-2 sentences>

Rules:
- Output ONLY findings, no preamble, no closing remarks.
- One ---FINDING--- block per distinct issue.
- Be thorough — list every issue you can find. False negatives are worse than false positives.
- End your response with the literal line: ---END---

# Code under review (file: {filename})

```python
{code}
```
"""

AGGREGATOR_PROMPT_TEMPLATE = """You are a senior code review aggregator. Below are bug reports from {n} independent reviewers of the same code. Your job: synthesize them into a single deduplicated finding list.

Rules:
- If multiple reviewers report the same bug (different wording), merge into one finding.
- If only one reviewer reports something, KEEP it (don't filter — better to over-include).
- Use the same ---FINDING--- format as input.
- End with ---END---

{reports}
"""

# ─── DATA ──────────────────────────────────────────────────────────────────

@dataclass
class Finding:
    severity: str
    category: str
    title: str
    description: str
    suggested_fix: str
    raw_block: str = ""

@dataclass
class ArmResult:
    arm: str
    snippet: str
    raw: str
    findings: list[dict] = field(default_factory=list)
    cost_usd: float = 0.0
    latency_s: float = 0.0
    error: str = ""
    sub_calls: list[dict] = field(default_factory=list)  # for jury / hybrid

# ─── PARSER ────────────────────────────────────────────────────────────────

FINDING_RE = re.compile(r"---FINDING---(.*?)(?=---FINDING---|---END---|$)", re.DOTALL)

def parse_findings(text: str) -> list[Finding]:
    out: list[Finding] = []
    for block in FINDING_RE.findall(text):
        block = block.strip()
        if not block:
            continue
        f = Finding(severity="", category="", title="", description="",
                    suggested_fix="", raw_block=block)
        for line in block.splitlines():
            line = line.strip()
            for field_name, attr in [
                ("SEVERITY:", "severity"),
                ("CATEGORY:", "category"),
                ("TITLE:", "title"),
                ("DESCRIPTION:", "description"),
                ("SUGGESTED_FIX:", "suggested_fix"),
            ]:
                if line.upper().startswith(field_name):
                    setattr(f, attr, line[len(field_name):].strip())
                    break
            else:
                # Continuation of last multi-line field (description usually)
                if f.description and not f.suggested_fix:
                    f.description += " " + line
        if f.title or f.description:
            out.append(f)
    return out

# ─── LLM CALLERS ───────────────────────────────────────────────────────────

def call_anthropic_api(model: str, prompt: str, max_tokens: int = 4096) -> tuple[str, dict]:
    """Direct Anthropic API call. Requires ANTHROPIC_API_KEY."""
    if not ANTHROPIC_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    t0 = time.time()
    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    in_tok = data.get("usage", {}).get("input_tokens", 0)
    out_tok = data.get("usage", {}).get("output_tokens", 0)
    p_in, p_out = PRICING.get(model, (0, 0))
    cost = (in_tok * p_in + out_tok * p_out) / 1_000_000
    return text, {
        "model": model, "backend": "api",
        "cost_usd": cost, "latency_s": time.time() - t0,
        "in_tok": in_tok, "out_tok": out_tok,
    }


def call_claude_code_cli(model: str, prompt: str, max_tokens: int = 4096) -> tuple[str, dict]:
    """Call Claude via `claude` CLI subprocess. Uses subscription — no API key.

    CRITICAL: spawns claude with cwd=tempdir to AVOID loading the project's
    CLAUDE.md, agents, skills, and MCP servers. Otherwise the model is heavily
    biased by project context (and pays cache bloat for unused context).
    """
    import tempfile
    if not CLAUDE_CLI:
        raise RuntimeError("`claude` CLI not in PATH")
    t0 = time.time()
    cmd = [CLAUDE_CLI, "-p", prompt, "--model", model, "--output-format", "json"]

    with tempfile.TemporaryDirectory(prefix="spike3-claude-") as tmpdir:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300,
            encoding="utf-8", cwd=tmpdir,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI exit {proc.returncode}: {proc.stderr[:300]}")

    # `claude -p --output-format json` returns an ARRAY of events.
    # We need the {"type":"result"} entry — it has final text + cost + usage.
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
                    in_tok = (usage.get("input_tokens", 0) or 0) \
                           + (usage.get("cache_read_input_tokens", 0) or 0) \
                           + (usage.get("cache_creation_input_tokens", 0) or 0)
                    out_tok = usage.get("output_tokens", 0) or 0
                    break
        elif isinstance(events, dict):
            # Older / single-object format — best-effort fallback
            text = events.get("result", events.get("response", proc.stdout))
            usage = events.get("usage", {}) or {}
            in_tok = usage.get("input_tokens", 0) or 0
            out_tok = usage.get("output_tokens", 0) or 0
            cost_usd = float(events.get("total_cost_usd", 0.0) or 0.0)
    except (json.JSONDecodeError, ValueError):
        pass

    return text, {
        "model": model, "backend": "cli",
        "cost_usd": cost_usd,
        "latency_s": time.time() - t0,
        "in_tok": in_tok, "out_tok": out_tok,
    }


def call_claude(model: str, prompt: str, max_tokens: int = 4096) -> tuple[str, dict]:
    """Dispatch Claude call to active backend (api or cli)."""
    if CLAUDE_BACKEND == "api":
        return call_anthropic_api(model, prompt, max_tokens)
    if CLAUDE_BACKEND == "cli":
        return call_claude_code_cli(model, prompt, max_tokens)
    raise RuntimeError("No Claude backend resolved")

def call_gemini(model: str, prompt: str, max_tokens: int = 4096) -> tuple[str, dict]:
    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    t0 = time.time()
    resp = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": GEMINI_KEY},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.2},
        },
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    usage = data.get("usageMetadata", {})
    in_tok = usage.get("promptTokenCount", 0)
    out_tok = usage.get("candidatesTokenCount", 0)
    p_in, p_out = PRICING.get(model, (0, 0))
    cost = (in_tok * p_in + out_tok * p_out) / 1_000_000
    return text, {
        "model": model,
        "cost_usd": cost,
        "latency_s": time.time() - t0,
        "in_tok": in_tok,
        "out_tok": out_tok,
    }

def call_ollama(model: str, prompt: str, max_tokens: int = 4096) -> tuple[str, dict]:
    """Ollama /api/generate. For local reasoning models (qwen3 family) we
    KEEP thinking enabled — review is an analytical task where step-by-step
    reasoning helps recall — but we DOUBLE num_predict so thinking + structured
    findings output both fit. Latency ~2× but tokens are free locally."""
    t0 = time.time()
    is_reasoning = any(tag in model.lower() for tag in ("qwen3.6", "qwen3:", "deepseek-r1"))
    # Reasoning models: 16384 num_predict (4× default) so thinking + structured
    # findings both fit comfortably. num_ctx must be ≥ num_predict + prompt
    # (qwen3 default ctx is 32k, we set 20k = headroom for ~3.5k prompt + 16k gen).
    # Instruct/coder models: stay at default since no thinking overhead.
    num_predict = 16384 if is_reasoning else max_tokens
    num_ctx = 20480 if is_reasoning else 8192
    resp = httpx.post(
        f"{OLLAMA}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "30m",  # keep model warm across spike run
            "options": {
                "num_predict": num_predict,
                "num_ctx": num_ctx,
                "temperature": 0.2,
            },
        },
        timeout=600,  # 4× budget = up to ~90s per call at 177 tok/s, headroom for cold load
    )
    resp.raise_for_status()
    data = resp.json()
    text = data.get("response", "")
    return text, {
        "model": model,
        "cost_usd": 0.0,
        "latency_s": time.time() - t0,
        "in_tok": data.get("prompt_eval_count", 0),
        "out_tok": data.get("eval_count", 0),
    }

# ─── ARMS ──────────────────────────────────────────────────────────────────

def arm_solo(caller, model: str, snippet_text: str, snippet_name: str) -> ArmResult:
    arm_name = f"SOLO_{model}"
    prompt = REVIEW_PROMPT_TEMPLATE.format(filename=snippet_name, code=snippet_text)
    try:
        text, meta = caller(model, prompt)
    except Exception as e:
        return ArmResult(arm=arm_name, snippet=snippet_name, raw="", error=f"{type(e).__name__}: {e}")
    findings = [asdict(f) for f in parse_findings(text)]
    return ArmResult(
        arm=arm_name, snippet=snippet_name, raw=text,
        findings=findings, cost_usd=meta["cost_usd"], latency_s=meta["latency_s"],
        sub_calls=[meta],
    )

def arm_jury_3(snippet_text: str, snippet_name: str) -> ArmResult:
    """Opus || qwen3.6 || Gemini → Haiku aggregator."""
    review_prompt = REVIEW_PROMPT_TEMPLATE.format(filename=snippet_name, code=snippet_text)
    arm_name = "JURY_3"

    if not GEMINI_KEY:
        return ArmResult(arm=arm_name, snippet=snippet_name, raw="",
                         error="GEMINI_API_KEY not set; jury arm skipped")

    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        futs = {
            pool.submit(call_claude, "claude-opus-4-6", review_prompt): "opus",
            pool.submit(call_ollama, "qwen3.6:latest", review_prompt): "qwen",
            pool.submit(call_gemini, "gemini-2.5-pro", review_prompt): "gemini",
        }
        sub_results: list[tuple[str, str, dict]] = []
        sub_meta: list[dict] = []
        for fut in cf.as_completed(futs):
            label = futs[fut]
            try:
                text, meta = fut.result()
                sub_results.append((label, text, meta))
                sub_meta.append({**meta, "label": label})
            except Exception as e:
                sub_meta.append({"label": label, "error": f"{type(e).__name__}: {e}"})

    if not sub_results:
        return ArmResult(arm=arm_name, snippet=snippet_name, raw="",
                         error="all jurors failed", sub_calls=sub_meta)

    reports = "\n\n".join(
        f"### Reviewer {label} report:\n{text}" for label, text, _ in sub_results
    )
    agg_prompt = AGGREGATOR_PROMPT_TEMPLATE.format(n=len(sub_results), reports=reports)
    try:
        agg_text, agg_meta = call_claude("claude-haiku-4-5-20251001", agg_prompt)
    except Exception as e:
        return ArmResult(arm=arm_name, snippet=snippet_name, raw=reports,
                         error=f"aggregator failed: {e}", sub_calls=sub_meta)
    sub_meta.append({**agg_meta, "label": "haiku-aggregator"})
    findings = [asdict(f) for f in parse_findings(agg_text)]
    cost = sum(m.get("cost_usd", 0.0) for m in sub_meta)
    return ArmResult(
        arm=arm_name, snippet=snippet_name, raw=agg_text,
        findings=findings, cost_usd=cost, latency_s=time.time() - t0,
        sub_calls=sub_meta,
    )

def arm_jury_3_flash3(snippet_text: str, snippet_name: str) -> ArmResult:
    """Variant of arm_jury_3 using gemini-3-flash-preview instead of 2.5-pro.
    Same shape: Opus || qwen3.6 || Gemini-3-Flash → Haiku aggregator."""
    review_prompt = REVIEW_PROMPT_TEMPLATE.format(filename=snippet_name, code=snippet_text)
    arm_name = "JURY_3_FLASH3"

    if not GEMINI_KEY:
        return ArmResult(arm=arm_name, snippet=snippet_name, raw="",
                         error="GEMINI_API_KEY not set; jury arm skipped")

    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        futs = {
            pool.submit(call_claude, "claude-opus-4-6", review_prompt): "opus",
            pool.submit(call_ollama, "qwen3.6:latest", review_prompt): "qwen",
            pool.submit(call_gemini, "gemini-3-flash-preview", review_prompt): "gemini-3-flash",
        }
        sub_results: list[tuple[str, str, dict]] = []
        sub_meta: list[dict] = []
        for fut in cf.as_completed(futs):
            label = futs[fut]
            try:
                text, meta = fut.result()
                sub_results.append((label, text, meta))
                sub_meta.append({**meta, "label": label})
            except Exception as e:
                sub_meta.append({"label": label, "error": f"{type(e).__name__}: {e}"})

    if not sub_results:
        return ArmResult(arm=arm_name, snippet=snippet_name, raw="",
                         error="all jurors failed", sub_calls=sub_meta)

    reports = "\n\n".join(
        f"### Reviewer {label} report:\n{text}" for label, text, _ in sub_results
    )
    agg_prompt = AGGREGATOR_PROMPT_TEMPLATE.format(n=len(sub_results), reports=reports)
    try:
        agg_text, agg_meta = call_claude("claude-haiku-4-5-20251001", agg_prompt)
    except Exception as e:
        return ArmResult(arm=arm_name, snippet=snippet_name, raw=reports,
                         error=f"aggregator failed: {e}", sub_calls=sub_meta)
    sub_meta.append({**agg_meta, "label": "haiku-aggregator"})
    findings = [asdict(f) for f in parse_findings(agg_text)]
    cost = sum(m.get("cost_usd", 0.0) for m in sub_meta)
    return ArmResult(
        arm=arm_name, snippet=snippet_name, raw=agg_text,
        findings=findings, cost_usd=cost, latency_s=time.time() - t0,
        sub_calls=sub_meta,
    )


def arm_hybrid(snippet_text: str, snippet_name: str) -> ArmResult:
    """Sonnet || qwen3.6:latest in parallel → Haiku judge."""
    review_prompt = REVIEW_PROMPT_TEMPLATE.format(filename=snippet_name, code=snippet_text)
    arm_name = "HYBRID"

    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=2) as pool:
        futs = {
            pool.submit(call_claude, "claude-sonnet-4-6", review_prompt): "sonnet",
            pool.submit(call_ollama, "qwen3.6:latest", review_prompt): "qwen",
        }
        sub_results: list[tuple[str, str, dict]] = []
        sub_meta: list[dict] = []
        for fut in cf.as_completed(futs):
            label = futs[fut]
            try:
                text, meta = fut.result()
                sub_results.append((label, text, meta))
                sub_meta.append({**meta, "label": label})
            except Exception as e:
                sub_meta.append({"label": label, "error": f"{type(e).__name__}: {e}"})

    if not sub_results:
        return ArmResult(arm=arm_name, snippet=snippet_name, raw="",
                         error="all critics failed", sub_calls=sub_meta)

    reports = "\n\n".join(
        f"### Reviewer {label} report:\n{text}" for label, text, _ in sub_results
    )
    agg_prompt = AGGREGATOR_PROMPT_TEMPLATE.format(n=len(sub_results), reports=reports)
    try:
        judge_text, judge_meta = call_claude("claude-haiku-4-5-20251001", agg_prompt)
    except Exception as e:
        return ArmResult(arm=arm_name, snippet=snippet_name, raw=reports,
                         error=f"judge failed: {e}", sub_calls=sub_meta)
    sub_meta.append({**judge_meta, "label": "haiku-judge"})
    findings = [asdict(f) for f in parse_findings(judge_text)]
    cost = sum(m.get("cost_usd", 0.0) for m in sub_meta)
    return ArmResult(
        arm=arm_name, snippet=snippet_name, raw=judge_text,
        findings=findings, cost_usd=cost, latency_s=time.time() - t0,
        sub_calls=sub_meta,
    )

# ─── MAIN ──────────────────────────────────────────────────────────────────

ARM_REGISTRY = {
    "CONTROL":     lambda txt, name: arm_solo(call_claude, "claude-opus-4-6",         txt, name),
    "QWEN_SOLO":   lambda txt, name: arm_solo(call_ollama,    "qwen3.6:latest",          txt, name),
    "SONNET_SOLO": lambda txt, name: arm_solo(call_claude, "claude-sonnet-4-6",       txt, name),
    "JURY_3":         arm_jury_3,
    "JURY_3_FLASH3":  arm_jury_3_flash3,
    "HYBRID":         arm_hybrid,
}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--snippets-dir", default=str(Path(__file__).parent / "snippets"))
    p.add_argument("--output", default=str(Path(__file__).parent / "results.json"))
    p.add_argument("--arms", default="CONTROL,QWEN_SOLO,SONNET_SOLO,JURY_3,JURY_3_FLASH3,HYBRID",
                   help="comma-separated arm names")
    p.add_argument("--snippets", default="",
                   help="comma-separated snippet filenames; empty = all .py in dir")
    args = p.parse_args()

    snippet_dir = Path(args.snippets_dir)
    if args.snippets:
        snippet_files = [snippet_dir / s for s in args.snippets.split(",")]
    else:
        snippet_files = sorted(snippet_dir.glob("*.py"))

    arms = [a.strip() for a in args.arms.split(",") if a.strip() in ARM_REGISTRY]

    print(f"Snippets: {[f.name for f in snippet_files]}")
    print(f"Arms: {arms}")
    print(f"Total runs: {len(snippet_files) * len(arms)}\n")

    print(f"Claude backend: {CLAUDE_BACKEND or 'NONE — Claude arms will fail'}", file=sys.stderr)
    if not GEMINI_KEY:
        print("WARNING: GEMINI_API_KEY not set — JURY_3 will skip", file=sys.stderr)

    results: list[dict] = []
    total = len(snippet_files) * len(arms)
    i = 0
    for snip_path in snippet_files:
        snippet_text = snip_path.read_text(encoding="utf-8")
        for arm in arms:
            i += 1
            print(f"[{i}/{total}] {arm:14} × {snip_path.name}", file=sys.stderr, flush=True)
            t0 = time.time()
            try:
                res = ARM_REGISTRY[arm](snippet_text, snip_path.name)
            except Exception as e:
                res = ArmResult(arm=arm, snippet=snip_path.name, raw="",
                                error=f"{type(e).__name__}: {e}")
            res.arm = arm  # normalize (solo arms set per-model name)
            results.append(asdict(res))
            tag = "OK" if not res.error else f"ERR: {res.error[:60]}"
            print(f"  → {len(res.findings):2d} findings  "
                  f"{res.latency_s:5.1f}s  ${res.cost_usd:.4f}  {tag}",
                  file=sys.stderr, flush=True)

    Path(args.output).write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nResults written to {args.output}")
    print("Run `python3 score.py` to score against ground truth.")

if __name__ == "__main__":
    main()
