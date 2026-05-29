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
  ask_ubuntu_qwen36          — qwen3.6:latest @ Ubuntu/5090 (general critic, ~24s warm @ 177 tok/s)
  ask_ubuntu_qwen3_coder     — qwen3.6:27b @ Ubuntu/5090 (code primary, dense 27B GGUF Q4_K_M,
                               SWE-bench Verified 77.2 ≈ Sonnet 4.6; 17GB fully on-GPU, fast)
  ask_gemini_3_flash_preview — Gemini 3 Flash Preview via Google AI API (cloud juror, multilingual, fast)

Win11 wrappers absent — RTX 4090 24 GB cannot host 32B Q4 + KV cache without
CPU offload. Re-add to CONFIG when hardware permits (>32 GB VRAM or Q3 quants).

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
    """Load KEY=VALUE pairs from .env in cwd into os.environ if not already set.

    Bridge is started by Claude Code which doesn't auto-load .env. This lets
    GEMINI_API_KEY (and similar) live in the project's .env file (gitignored)
    without forcing the user to export it system-wide or duplicate it in .mcp.json.
    """
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
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
        # win11 endpoint absent — re-add when 4090 hardware swap or Q3 quants
        # make 32B models viable (currently CPU offload, ~5 tok/s).
        "gemini_openai_compat": "https://generativelanguage.googleapis.com/v1beta/openai",
    },
    "models": {
        # tool_name → dict with provider + provider-specific config
        "ask_ubuntu_qwen36": {
            "provider": "ollama",
            "endpoint": "ubuntu",
            "model": "qwen3.6:latest",
            "description": "General critic — Qwen3.6 35B-A3B MoE (Claude-class quality, ~20s warm). Use for validate-design role. Default primary critic.",
        },
        "ask_ubuntu_qwen3_coder": {
            "provider": "ollama",
            "endpoint": "ubuntu",
            "model": "qwen3.6:27b",
            "description": (
                "Code primary — Qwen3.6-27B dense (GGUF Q4_K_M, 17GB, fully on-GPU on the 5090). "
                "SWE-bench Verified 77.2 (≈ Sonnet 4.6 on agentic coding). "
                "Default code generator for spec-tdd-impl-agent (Forge) and code critic for validate-impl/review. "
                "Already installed (digest a50eda8ed977). NVFP4/MXFP8 variants are MLX-only (macOS) — "
                "do NOT use on Linux. Tool name kept for backward compat."
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
}


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
    max_tokens = arguments.get("max_tokens", 32768)

    # Build Ollama API payload
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "30m",  # keep model warm across jury cycle (validate-* calls bridge ~3x in a row)
        "options": {
            "num_predict": max_tokens,
            "think": False,   # disable Qwen3 reasoning chain — we want the answer, not the working
        },
    }
    if system:
        payload["system"] = system

    # Execute the call
    try:
        async with httpx.AsyncClient(timeout=CONFIG["timeout_s"]) as client:
            response = await client.post(f"{endpoint}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract relevant fields
            generated = data.get("response", "")
            eval_count = data.get("eval_count", 0)
            eval_duration_ns = data.get("eval_duration", 0)
            eval_duration_s = eval_duration_ns / 1_000_000_000 if eval_duration_ns else 0
            tokens_per_sec = eval_count / eval_duration_s if eval_duration_s > 0 else 0

            # Empty-response retry: if Ollama burned the budget on reasoning and returned nothing,
            # retry once with double budget. Belt and suspenders since think:False should already prevent this.
            if not generated.strip() and eval_count >= max_tokens * 0.9:
                payload["options"]["num_predict"] = max_tokens * 2
                response = await client.post(f"{endpoint}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                generated = data.get("response", "")
                eval_count = data.get("eval_count", 0)
                eval_duration_ns = data.get("eval_duration", 0)
                eval_duration_s = eval_duration_ns / 1_000_000_000 if eval_duration_ns else 0
                tokens_per_sec = eval_count / eval_duration_s if eval_duration_s > 0 else 0
                retry_note = " | retried@2x"
            else:
                retry_note = ""

            # Format response with metadata header
            metadata = (
                f"[{model} @ {machine} | {eval_count} tokens | "
                f"{eval_duration_s:.1f}s | {tokens_per_sec:.1f} tok/s{retry_note}]"
            )
            return [TextContent(type="text", text=f"{metadata}\n\n{generated}")]

    except httpx.TimeoutException:
        return [TextContent(
            type="text",
            text=f"[blast-llm-bridge] Timeout after {CONFIG['timeout_s']}s on {model} @ {machine}. "
                 "Model may be cold-loading (first call is slow). Retry, or check OLLAMA_KEEP_ALIVE.",
        )]
    except httpx.ConnectError as e:
        return [TextContent(
            type="text",
            text=f"[blast-llm-bridge] Cannot connect to {endpoint}. "
                 f"Is Ollama running on {machine}? Error: {e}",
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

    try:
        async with httpx.AsyncClient(timeout=CONFIG["timeout_s"]) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

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
