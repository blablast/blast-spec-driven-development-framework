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
  ask_ubuntu_qwen3_coder     — qwen3-coder:30b @ Ubuntu/5090 (code critic, ~0.9s warm @ 246 tok/s)

Win11 wrappers absent — RTX 4090 24 GB cannot host 32B Q4 + KV cache without
CPU offload. Re-add to CONFIG when hardware permits (>32 GB VRAM or Q3 quants).

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


# === CONFIGURATION ===

CONFIG = {
    "endpoints": {
        "ubuntu": os.environ.get("BLAST_OLLAMA_UBUNTU", "http://192.168.5.60:11434"),
        # win11 endpoint absent — re-add when 4090 hardware swap or Q3 quants
        # make 32B models viable (currently CPU offload, ~5 tok/s).
    },
    "models": {
        # tool_name → (machine, ollama_model_tag, description)
        "ask_ubuntu_qwen36": (
            "ubuntu",
            "qwen3.6:latest",
            "General critic — Qwen3.6 35B-A3B MoE (Claude-class quality, ~20s warm). Use for validate-design role. Default primary critic.",
        ),
        "ask_ubuntu_qwen3_coder": (
            "ubuntu",
            "qwen3-coder:30b",
            "Code critic — Qwen3-Coder 30B (specialized, ~12s warm). Use for validate-impl, review.",
        ),
    },
    "timeout_s": int(os.environ.get("BLAST_LLM_TIMEOUT_S", "120")),
}


# === MCP SERVER ===

server = Server("blast-llm-bridge")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Announce all available tools to Claude Code."""
    tools = []
    for tool_name, entry in CONFIG["models"].items():
        # 3-tuple (legacy) or 4-tuple (with disabled_reason)
        if len(entry) == 4:
            machine, model, description, disabled_reason = entry
        else:
            machine, model, description = entry
            disabled_reason = None
        # Prefix description with [DISABLED] so Claude sees it in tool catalog
        # (still listed so /mcp shows it; calls return helpful error from call_tool)
        if disabled_reason:
            description = f"[DISABLED] {description}"
        tools.append(Tool(
            name=tool_name,
            description=description,
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to send to the model",
                    },
                    "system": {
                        "type": "string",
                        "description": "Optional system prompt for context/persona",
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens to generate (default 4096)",
                        "default": 4096,
                    },
                },
                "required": ["prompt"],
            },
        ))
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a tool call against the appropriate Ollama endpoint."""
    if name not in CONFIG["models"]:
        return [TextContent(type="text", text=f"[blast-llm-bridge] Unknown tool: {name}")]

    machine, model, _description = CONFIG["models"][name]
    endpoint = CONFIG["endpoints"][machine]
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
