#!/usr/bin/env python3
"""
blast-llm-bridge — MCP server exposing local Ollama models as Claude Code tools.

Spike #2 MVP scope:
- Eksponuje 2 lokalne modele (Ubuntu 5090) jako MCP tools
- Read-only, sync inference via Ollama HTTP API
- Foundation for blast multi-LLM routing

Usage:
  python3 blast-llm-bridge.py     # Run as MCP stdio server (Claude Code starts it)

Environment variables (override config):
  BLAST_OLLAMA_UBUNTU=http://192.168.5.60:11434
  BLAST_LLM_TIMEOUT_S=120


Tools exposed:
  ask_ubuntu_qwen36          — qwen3.6 @ Ubuntu/5090 (general critic, ~243 tok/s raw, thinking-heavy)
  ask_ubuntu_qwen3_coder     — qwen3-coder @ Ubuntu/5090 (code primary, 17.3G, ~160 tok/s,
                               coder profile = minimal thinking → highest EFFECTIVE code throughput;
                               co-resident with lfm2.5: 17.3G + 4.8G = 22.1G fits 32G VRAM together)
  ask_ubuntu_lfm25           — lfm2.5 @ Ubuntu/5090 (mechanical workhorse, 4.8G, ~580 tok/s:
                               drafts/scaffolding, envelope parsing, digests, privacy-mode aggregator)
  ask_ubuntu_qwen3_coder_next — qwen3-coder-next @ Ubuntu/5090 (tier-2 local escalation, 48.2G,
                               ~50 tok/s w/ CPU offload; deliberate swap, never resident)
  ask_win11_qwen3_coder      — qwen3-coder @ Win11/4090 (parallel debate juror — dual-GPU jury)
  ask_gemini_3_flash_preview — Gemini 3 Flash Preview via Google AI API (cloud juror, multilingual, fast)

VRAM residency policy (RTX 5090, 32G): qwen3-coder + lfm2.5 are pinned (keep_alive=-1) and
must BOTH stay resident during impl — never load a third local model mid-impl (forces swap).

Dual-GPU jury: ask_win11_qwen3_coder runs on the 4090 (192.168.5.70) in parallel
with 5090 jurors — local debates no longer serialize on one card. qwen3-coder
(17.3G) fits the 4090's 24G; larger models still don't.

API keys:
  GEMINI_API_KEY — required for ask_gemini_3_flash_preview. Read from os.environ
  first; if missing, attempt to read from `.env` in current working directory
  (KEY=VALUE format). If still missing, the Gemini tool is skipped gracefully
  and JURY_3_FLASH3 falls back to JURY_2 (Sonnet + qwen).

Dependencies:
  pip install mcp httpx
"""

import asyncio
import json
import os
import sys
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent



# === .env loader (no python-dotenv dependency) ===

def _load_dotenv_into_environ() -> None:
    """Load KEY=VALUE pairs from blast's .env into os.environ if not already set.

    Bridge is started by Claude Code which doesn't auto-load .env. This lets
    GEMINI_API_KEY (and similar) live in blast's own env file (gitignored)
    without forcing the user to export it system-wide or duplicate it in .mcp.json.
    Looks in `.blast/.env` first (namespaced), then legacy root `.env`.
    """
    # Lookup order (first hit wins): `.blast/.env` (namespaced — keeps blast's
    # env out of the host project's root) then legacy root `.env` (back-compat).
    cwd = os.getcwd()
    candidates = [os.path.join(cwd, ".blast", ".env"), os.path.join(cwd, ".env")]
    env_path = next((c for c in candidates if os.path.exists(c)), None)
    if env_path is None:
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        # Silent — env loading is best-effort; missing keys produce graceful
        # tool-skip downstream
        pass


_load_dotenv_into_environ()


# === CONFIGURATION ===

CONFIG = {
    "endpoints": {
        "ubuntu": os.environ.get("BLAST_OLLAMA_UBUNTU", "http://192.168.5.60:11434"),
        # win11/4090 (24G): hosts qwen3-coder (17.3G — fits with KV headroom) as a
        # PARALLEL debate juror. Dual-GPU jury: qwen3.6 on the 5090 + qwen3-coder on
        # the 4090 run simultaneously instead of swapping models on one card.
        "win11": os.environ.get("BLAST_OLLAMA_WIN11", "http://192.168.5.70:11434"),
        "gemini_openai_compat": "https://generativelanguage.googleapis.com/v1beta/openai",
    },
    "models": {
        # tool_name → dict with provider + provider-specific config
        "ask_ubuntu_qwen36": {
            "provider": "ollama",
            "endpoint": "ubuntu",
            "model": "qwen3.6:latest",
            "think": True,          # reasoning juror — its VALUE is the reasoning chain;
                                    # forcing think:False (the global default) strips exactly
                                    # what llm-routing.md routes this model FOR.
            "description": "General critic — qwen3.6 (22.3G, ~243 tok/s raw, thinking-heavy: effective output slower than raw). Juror/critic for debates and validate-design. NOT the impl code primary (that is qwen3-coder) — loading it during impl evicts the resident pair.",
        },
        "ask_ubuntu_qwen3_coder": {
            "provider": "ollama",
            "endpoint": "ubuntu",
            "model": "qwen3-coder",
            "keep_alive": -1,       # pinned resident — impl code primary
            "num_ctx": 32768,
            "description": (
                "Code primary — qwen3-coder (17.3G, ~160 tok/s on the 5090). Coder profile: "
                "minimal thinking overhead → highest EFFECTIVE code throughput (qwen3.6 has higher "
                "raw tok/s but burns it on reasoning chains — pure waste in a TDD loop). "
                "Default code generator for spec-tdd-impl-agent (Forge) and code critic for "
                "validate-impl/review. Co-resident with lfm2.5 (22.1G total < 32G VRAM). "
                "Tool name kept for backward compat."
            ),
        },
        "ask_ubuntu_lfm25": {
            "provider": "ollama",
            "endpoint": "ubuntu",
            "model": "lfm2.5",
            "keep_alive": -1,       # pinned resident — mechanical workhorse
            "num_ctx": 8192,        # small KV cache: leaves VRAM headroom for qwen3-coder ctx
            "default_max_tokens": 8192,
            "description": (
                "Mechanical workhorse — lfm2.5 (4.8G, ~580 tok/s). WEAKER model: never use for "
                "final code. Roles: draft-then-verify scaffolding (test boilerplate, fixtures, "
                "dataclasses, signatures — verified by qwen3-coder), verdict-envelope parsing, "
                "debate scratchpad digests, telemetry summaries, commit-message drafts, and "
                "judge/aggregator in privacy mode (local-only) where Haiku is blocked."
            ),
        },
        "ask_ubuntu_qwen3_coder_next": {
            "provider": "ollama",
            "endpoint": "ubuntu",
            "model": "qwen3-coder-next",
            "keep_alive": "5m",     # escalation tier — transient by design, never pinned
            "num_ctx": 32768,
            "description": (
                "Local escalation tier — qwen3-coder-next (48.2G, ~50 tok/s; exceeds 32G VRAM "
                "so it partially offloads to CPU AND evicts the resident pair when loaded). "
                "Use ONLY as tier-2 escalation when qwen3-coder produced red tests twice on a "
                "task — a deliberate swap that buys a stronger local attempt before paying for "
                "cloud Sonnet. Never use as the default primary; never during parallel waves."
            ),
        },
        "ask_win11_qwen3_coder": {
            "provider": "ollama",
            "endpoint": "win11",
            "model": "qwen3-coder",
            "keep_alive": "30m",    # warm across a jury cycle
            "num_ctx": 16384,
            "description": (
                "Parallel debate juror — qwen3-coder @ Win11/4090 (17.3G fits 24G VRAM). "
                "Runs SIMULTANEOUSLY with qwen3.6 on the 5090 in local jury compositions: "
                "two jurors, two GPUs, zero model swapping. Code-profile critic for "
                "validate-impl/review debates and privacy-mode juries. If the Win11 host "
                "is offline the juror is skipped and the jury degrades transparently."
            ),
        },
        "ask_gemini_3_flash_preview": {
            "provider": "gemini",
            "endpoint": "gemini_openai_compat",
            "model": "gemini-3-flash-preview",
            "api_key_env": "GEMINI_API_KEY",
            "description": "Cloud juror — Gemini 3 Flash Preview via Google AI API (multilingual, fast, ~5s typical). Use as JURY_3_FLASH3 third juror alongside Sonnet/Opus + qwen.",
        },
    },
    "timeout_s": int(os.environ.get("BLAST_LLM_TIMEOUT_S", "120")),
    # Split the single wall-clock timeout into phases: a short connect timeout
    # surfaces a dead host in seconds (was: up to timeout_s of silence), while
    # generation still gets the full read budget. Streaming (below) makes the
    # read budget an INTER-CHUNK timeout, so a stalled generation aborts fast
    # instead of freezing the caller for the whole window.
    "connect_timeout_s": float(os.environ.get("BLAST_LLM_CONNECT_TIMEOUT_S", "5")),
    "max_retries": int(os.environ.get("BLAST_LLM_MAX_RETRIES", "2")),
}


# === SHARED HTTP CLIENT + RETRY ===

_CLIENT: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Lazily create one pooled AsyncClient for the server's lifetime.

    A new client per call reopened a TCP/TLS connection every time; a single
    pooled client reuses keep-alive connections to the Ollama hosts and Gemini.
    The read timeout applies per-chunk once we stream, so a long-but-progressing
    generation is fine while a truly stalled one trips the read timeout.
    """
    global _CLIENT
    if _CLIENT is None:
        timeout = httpx.Timeout(
            CONFIG["timeout_s"],
            connect=CONFIG["connect_timeout_s"],
        )
        _CLIENT = httpx.AsyncClient(timeout=timeout)
    return _CLIENT


def _is_retryable(exc: Exception) -> bool:
    """Transient faults worth one more shot: connection refused/reset, timeouts,
    and 5xx from the host. 4xx (bad request, auth) are NOT retried."""
    if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout,
                        httpx.RemoteProtocolError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return 500 <= exc.response.status_code < 600
    return False


async def _sleep_backoff(attempt: int) -> None:
    # 0.5s, 1.5s — bounded, cheap; jurors that would have silently dropped now
    # get a second chance before the composition degrades.
    await asyncio.sleep(0.5 + attempt)


# === MCP SERVER ===

server = Server("blast-llm-bridge")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Announce all available tools to Claude Code.

    Tools whose required API key is missing from the environment are skipped
    gracefully — callers fall back to alternative compositions automatically.
    """
    tools = []
    for tool_name, entry in CONFIG["models"].items():
        provider = entry["provider"]
        description = entry["description"]
        api_key_env = entry.get("api_key_env")

        # Skip tools whose API key isn't available
        if api_key_env and not os.environ.get(api_key_env):
            print(
                f"[blast-llm-bridge] Skipping {tool_name}: {api_key_env} not set "
                f"(check .env in cwd or system env)",
                file=sys.stderr,
            )
            continue

        tools.append(
            Tool(
                name=tool_name,
                description=description,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Prompt to send to the model.",
                        },
                        "system": {
                            "type": "string",
                            "description": "Optional system prompt prefix.",
                        },
                        "max_tokens": {
                            "type": "integer",
                            "description": "Max output tokens (default 32768 for ollama, 8192 for gemini).",
                        },
                    },
                    "required": ["prompt"],
                },
            )
        )
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Dispatch tool call to the appropriate provider (ollama / gemini)."""
    if name not in CONFIG["models"]:
        return [TextContent(type="text", text=f"[blast-llm-bridge] Unknown tool: {name}")]

    entry = CONFIG["models"][name]
    provider = entry["provider"]

    if provider == "gemini":
        return await _call_gemini(name, entry, arguments)
    elif provider == "ollama":
        return await _call_ollama(name, entry, arguments)
    else:
        return [TextContent(type="text", text=f"[blast-llm-bridge] Unknown provider: {provider}")]


async def _call_ollama(name: str, entry: dict, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a tool call against an Ollama endpoint."""
    endpoint = CONFIG["endpoints"][entry["endpoint"]]
    model = entry["model"]
    machine = entry["endpoint"]
    prompt = arguments.get("prompt", "")
    system = arguments.get("system", "").strip()
    # qwen3.6:latest is a thinking model — reasoning chain consumes the budget before output.
    # Default is 32k to give 8x headroom over the spike-3 fix (16k). Local model = zero token cost,
    # latency only on actually generated tokens (model stops at natural completion).
    max_tokens = arguments.get("max_tokens", entry.get("default_max_tokens", 32768))

    # Build Ollama API payload. keep_alive: pinned residents (qwen3-coder, lfm2.5) use -1,
    # transient jurors default to 30m (warm across a jury cycle). think is PER-ROLE:
    # reasoning jurors (qwen3.6) keep it on, coders/mechanical models keep it off.
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,   # stream NDJSON: inter-chunk read timeout catches stalls fast
        "keep_alive": entry.get("keep_alive", "30m"),
        "options": {
            "num_predict": max_tokens,
            "think": entry.get("think", False),
        },
    }
    if entry.get("num_ctx"):
        payload["options"]["num_ctx"] = entry["num_ctx"]
    if system:
        payload["system"] = system

    url = f"{endpoint}/api/generate"

    async def _generate(pl: dict) -> tuple[str, int, float]:
        """Stream one generation. Returns (text, eval_count, eval_duration_s).
        Raises httpx transport/status errors for the retry wrapper to handle."""
        chunks: list[str] = []
        eval_count = 0
        eval_duration_ns = 0
        client = _get_client()
        async with client.stream("POST", url, json=pl) as resp:
            if resp.status_code >= 400:
                await resp.aread()          # must read body before raise on a stream
                resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                obj = json.loads(line)
                piece = obj.get("response", "")
                if piece:
                    chunks.append(piece)
                if obj.get("done"):
                    eval_count = obj.get("eval_count", 0)
                    eval_duration_ns = obj.get("eval_duration", 0)
        eval_duration_s = eval_duration_ns / 1_000_000_000 if eval_duration_ns else 0
        return "".join(chunks), eval_count, eval_duration_s

    async def _generate_with_retry(pl: dict) -> tuple[str, int, float]:
        last_exc: Exception | None = None
        for attempt in range(CONFIG["max_retries"] + 1):
            try:
                return await _generate(pl)
            except Exception as e:  # noqa: BLE001 — classify below
                last_exc = e
                if _is_retryable(e) and attempt < CONFIG["max_retries"]:
                    print(
                        f"[blast-llm-bridge] {type(e).__name__} on {model} @ {machine}, "
                        f"retry {attempt + 1}/{CONFIG['max_retries']}",
                        file=sys.stderr,
                    )
                    await _sleep_backoff(attempt)
                    continue
                raise
        assert last_exc is not None
        raise last_exc

    try:
        generated, eval_count, eval_duration_s = await _generate_with_retry(payload)
        retry_note = ""

        # Empty-response retry: reasoning burned the whole budget and emitted nothing →
        # one more shot at double the budget.
        if not generated.strip() and eval_count >= max_tokens * 0.9:
            payload["options"]["num_predict"] = max_tokens * 2
            generated, eval_count, eval_duration_s = await _generate_with_retry(payload)
            retry_note = " | retried@2x"

        tokens_per_sec = eval_count / eval_duration_s if eval_duration_s > 0 else 0
        metadata = (
            f"[{model} @ {machine} | {eval_count} tokens | "
            f"{eval_duration_s:.1f}s | {tokens_per_sec:.1f} tok/s{retry_note}]"
        )
        return [TextContent(type="text", text=f"{metadata}\n\n{generated}")]

    except httpx.TimeoutException:
        return [TextContent(
            type="text",
            text=f"[blast-llm-bridge] Timeout on {model} @ {machine} after "
                 f"{CONFIG['max_retries'] + 1} attempt(s) "
                 f"(connect {CONFIG['connect_timeout_s']}s / read {CONFIG['timeout_s']}s). "
                 "Model may be cold-loading or stalled; retry, or check OLLAMA_KEEP_ALIVE.",
        )]
    except httpx.ConnectError as e:
        return [TextContent(
            type="text",
            text=f"[blast-llm-bridge] Cannot connect to {endpoint} after "
                 f"{CONFIG['max_retries'] + 1} attempt(s). Is Ollama running on {machine}? Error: {e}",
        )]
    except httpx.HTTPStatusError as e:
        return [TextContent(
            type="text",
            text=f"[blast-llm-bridge] Ollama HTTP {e.response.status_code} on {machine}: {e.response.text[:200]}",
        )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"[blast-llm-bridge] {type(e).__name__}: {e}",
        )]




async def _call_gemini(name: str, entry: dict, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a tool call against Google's Gemini API (OpenAI-compat endpoint)."""
    api_key = os.environ.get(entry["api_key_env"])
    if not api_key:
        return [TextContent(
            type="text",
            text=f"[blast-llm-bridge] {entry['api_key_env']} not set — Gemini call skipped. "
                 f"Add to .env in project cwd or export in shell.",
        )]

    base_url = CONFIG["endpoints"][entry["endpoint"]]
    model = entry["model"]
    prompt = arguments.get("prompt", "")
    system = arguments.get("system", "").strip()
    max_tokens = arguments.get("max_tokens", 8192)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async def _post() -> dict:
        client = _get_client()
        response = await client.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()

    try:
        data = None
        last_exc: Exception | None = None
        for attempt in range(CONFIG["max_retries"] + 1):
            try:
                data = await _post()
                break
            except Exception as e:  # noqa: BLE001
                last_exc = e
                if _is_retryable(e) and attempt < CONFIG["max_retries"]:
                    await _sleep_backoff(attempt)
                    continue
                raise
        if data is not None:
            generated = ""
            try:
                generated = data["choices"][0]["message"]["content"] or ""
            except (KeyError, IndexError):
                generated = ""

            usage = data.get("usage", {})
            in_tokens = usage.get("prompt_tokens", 0)
            out_tokens = usage.get("completion_tokens", 0)

            metadata = (
                f"[{model} @ gemini-api | in={in_tokens} out={out_tokens}]"
            )
            return [TextContent(type="text", text=f"{metadata}\n\n{generated}")]

    except httpx.TimeoutException:
        return [TextContent(
            type="text",
            text=f"[blast-llm-bridge] Gemini timeout after {CONFIG['timeout_s']}s on {model}.",
        )]
    except httpx.HTTPStatusError as e:
        return [TextContent(
            type="text",
            text=f"[blast-llm-bridge] Gemini HTTP {e.response.status_code}: {e.response.text[:300]}",
        )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"[blast-llm-bridge] Gemini {type(e).__name__}: {e}",
        )]

async def main():
    """Run MCP server over stdio (Claude Code spawns this process)."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        # Last-ditch error logging (can't print to stdout — that's MCP comms channel)
        print(f"[blast-llm-bridge] FATAL: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
