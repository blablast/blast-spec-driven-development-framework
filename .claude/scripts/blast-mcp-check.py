#!/usr/bin/env python3
"""blast SessionStart check — verifies optional local tooling is installed.

Registered as a Claude Code `SessionStart` hook (see .claude/settings.json).
Fires once per session BEFORE MCP servers finish connecting, so it cannot probe
live tools — it inspects config + Python deps / PATH statically instead.

Checks the OPTIONAL integrations below and, for whatever is missing, prints the
exact install commands. For SessionStart, stdout is added to the session
context, so the agent sees the commands and surfaces them. Always exits 0.

  - blast-llm-bridge : local Ollama bridge (qwen3-coder / qwen3.6 / lfm2.5)
  - semble           : fast local code search for agents (~98% fewer tokens)

Both are opt-in: blast runs cloud-only and falls back to grep without them.
Silence it: `touch .blast/.mcp-check-skip` or set BLAST_SKIP_MCP_CHECK=1.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

BRIDGE = "blast-llm-bridge"
BRIDGE_DEPS = ["mcp", "httpx"]          # `pip install mcp httpx`
BRIDGE_SCRIPT = ".claude/mcp/blast-llm-bridge.py"
SEMBLE = "semble"


def _root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def _mcp_servers(obj: object) -> dict:
    return (obj.get("mcpServers") or {}) if isinstance(obj, dict) else {}


def _registered(root: Path, name: str) -> bool:
    """True if MCP server `name` is declared in project .mcp.json or user scope."""
    proj = root / ".mcp.json"
    if proj.exists():
        try:
            if name in _mcp_servers(json.loads(proj.read_text(encoding="utf-8"))):
                return True
        except Exception:
            pass
    user = Path.home() / ".claude.json"
    if user.exists():
        try:
            data = json.loads(user.read_text(encoding="utf-8"))
            if name in _mcp_servers(data):
                return True
            for block in (data.get("projects") or {}).values():
                if name in _mcp_servers(block):
                    return True
        except Exception:
            pass
    return False


def _missing_deps(deps: list[str]) -> list[str]:
    out = []
    for dep in deps:
        try:
            if importlib.util.find_spec(dep) is None:
                out.append(dep)
        except Exception:
            out.append(dep)
    return out


def main() -> int:
    try:
        root = _root()
        if os.environ.get("BLAST_SKIP_MCP_CHECK") or (root / ".blast" / ".mcp-check-skip").exists():
            return 0

        py = os.path.basename(sys.executable) or "python"
        blocks: list[str] = []

        # --- blast-llm-bridge (local Ollama models) ---
        bridge_missing = _missing_deps(BRIDGE_DEPS)
        if not _registered(root, BRIDGE) or bridge_missing:
            b = ["* blast-llm-bridge (lokalne modele qwen/lfm — opcjonalne):"]
            if bridge_missing:
                b.append(f"    {py} -m pip install {' '.join(bridge_missing)}")
            if not _registered(root, BRIDGE):
                b.append(f"    claude mcp add {BRIDGE} -- {py} {BRIDGE_SCRIPT}")
                b.append("    # lub: merge wpisu z .blast/.mcp.json.snippet do root .mcp.json")
            blocks.append("\n".join(b))

        # --- semble (fast local code search) ---
        if not _registered(root, SEMBLE) and not (shutil.which("semble") or shutil.which("uvx")):
            blocks.append("\n".join([
                "* semble (szybkie wyszukiwanie kodu, ~98% mniej tokenow — opcjonalne):",
                "    uv tool install semble        # albo: pip install semble",
                '    claude mcp add semble -s user -- uvx --from "semble[mcp]" semble',
                "    # indeks (opcjonalnie): semble index -o .blast/.session-state/semble-index",
            ]))

        if not blocks:
            return 0  # wszystko OK — cisza

        header = [
            "[blast] Opcjonalne lokalne narzedzia nie sa w pelni zainstalowane.",
            "        Bez nich blast dziala cloud-only (fallback na grep). Aby wlaczyc:",
            "",
        ]
        footer = [
            "",
            "    Po instalacji zrestartuj Claude Code (MCP czytane przy starcie).",
            "    Wyciszenie: `touch .blast/.mcp-check-skip` lub BLAST_SKIP_MCP_CHECK=1.",
        ]
        print("\n".join(header + blocks + footer))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
