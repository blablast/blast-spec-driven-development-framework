# Multi-LLM Setup

## Architektura

```
                    Claude Code (Anthropic) [orchestrator]
                              │
                              │ Task() spawn
                              ▼
                   Agent: spec-design-agent (sonnet)
                              │
                              │ uses tools:
                              ├─→ Read, Write, Edit (Claude Code native)
                              ├─→ ask_anthropic_*    (DIRECT — Claude Code native)
                              └─→ MCP: blast-llm-bridge
                                  ├─→ ask_openrouter_<model>   (cloud, opcjonalne)
                                  ├─→ ask_local_ubuntu_<model> (local Ollama, RTX 5090)
                                  └─→ ask_local_win11_<model>  (local Ollama, RTX 4090)
```

## Quickstart — Local Ollama Setup

### Ubuntu (RTX 5090, primary AI server)

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Configure systemd service to bind 0.0.0.0:11434 (LAN access)
sudo systemctl edit ollama.service
# Add:
# [Service]
# Environment="OLLAMA_HOST=0.0.0.0:11434"
# Environment="OLLAMA_KEEP_ALIVE=5m"
# Default 5m is correct for normal use. For bench/spike runs use 30m via per-call
# `keep_alive` field in /api/generate payload, NOT system-wide. 24h+ powoduje
# VRAM hog (qwen3-coder-next 30 GB
# zostało w VRAM przez >24h, blokując inne modele).
sudo systemctl daemon-reload
sudo systemctl restart ollama
sudo systemctl enable ollama

# Pull primary model + code critic
ollama pull qwen3.6:latest          # 35B-A3B MoE, 23GB Q4
ollama pull qwen3-coder:30b         # specialized code model

# Optional fallback
ollama pull qwen3:32b               # 32B Dense
```

### Windows 11 (RTX 4090, secondary)

```powershell
# Install Ollama Windows installer (one-click from ollama.ai)
# Set environment variable for LAN binding (System Properties → Environment Variables)
OLLAMA_HOST = 0.0.0.0:11434
OLLAMA_KEEP_ALIVE = 24h
# Restart Ollama service

# Pull
ollama pull qwen3:32b
ollama pull deepseek-r1:32b
```

### LAN connectivity check

```bash
# From any machine on LAN
curl http://192.168.5.60:11434/api/tags    # Ubuntu
curl http://192.168.5.70:11434/api/tags    # Win 11
```

### Firewall

```bash
# Ubuntu
sudo ufw allow from 192.168.5.0/24 to any port 11434

# Windows 11 (PowerShell as Admin)
New-NetFirewallRule -DisplayName "Ollama LAN" -Direction Inbound -Protocol TCP -LocalPort 11434 -Action Allow
```

## MCP Bridge — `.mcp.json`

Project-level config (Claude Code Cowork reads from here):

```json
{
  "mcpServers": {
    "blast-llm-bridge": {
      "command": "python",
      "args": [".claude/mcp/blast-llm-bridge.py"],
      "env": {
        "BLAST_OLLAMA_UBUNTU": "http://192.168.5.60:11434",
        "BLAST_OLLAMA_WIN11":  "http://192.168.5.70:11434",
        "BLAST_LLM_TIMEOUT_S": "240"
      }
    }
  }
}
```

After editing: restart Claude Code (Cowork desktop). Verify via `/mcp` command.

### Tools exposed (after `.mcp.json` reload)

| Tool name | Machine | Model | Use case |
|---|---|---|---|
| `ask_ubuntu_qwen36` | Ubuntu | qwen3.6:latest | General critic (validate-design) |
| `ask_ubuntu_qwen3_coder` | Ubuntu | qwen3-coder:30b | Code critic (validate-impl, review) |
| `ask_win11_qwen3_32b` | Win 11 | qwen3:32b | Fallback general |
| `ask_win11_deepseek_r1` | Win 11 | deepseek-r1:32b | Reasoning specialist (security jury) |

## Privacy Mode

**Konfiguracja**: `.blast/steering/llm-routing.md` ma sekcję privacy patterns w gitattributes-style:

```
.env*                  llm=local-only
*.pem                  llm=local-only
*.key                  llm=local-only
secrets/**             llm=local-only
*.proprietary          llm=local-only
```

Per-project additions: edytuj sekcję `## Privacy patterns` w `llm-routing.md`.

**Hook enforcement** (`.claude/hooks/blast-privacy-gate.py`):

- PreToolUse hook obserwuje Read/Edit/Glob/Grep dla privacy-flagged paths
- Tracks "touched" paths w `.blast/.session-state/privacy-touched.json` (window 30 min)
- Gdy Agent/Task call zawiera referencę do `ask_anthropic_*` lub `ask_openrouter_*` w prompcie ORAZ recent privacy-flagged paths istnieją → BLOCK (exit 2)
- Local tools (`ask_local_*`, `ask_ubuntu_*`, `ask_win11_*`) zawsze przechodzą

**Aktywacja**: dodaj do `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "^(Agent|Task|Read|Edit|Write|Grep|Glob)$",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/blast-privacy-gate.py"
          }
        ]
      }
    ]
  }
}
```

(Hook nie jest aktywowany domyślnie — opt-in. Aktywuj tylko gdy faktycznie pracujesz z privacy-flagged kodem.)

## Cost Strategy

Patrz `.blast/steering/cost-policy.md`. Skrót:

- **Anthropic native** (claude-haiku/sonnet/opus): płatne via Claude API
- **OpenRouter**: opcjonalny, jeden klucz dla 100+ modeli (po dodaniu wrapper'a do bridge)
- **Local Ollama**: $0 po hardware (4090 + 5090), 24/7 ready (KEEP_ALIVE=24h)

Zalecenia:
- Validate-* z lokalnym critic = darmowe → włącz dla każdego spec'u
- Security z jury (Pattern B) = mix: 1× Claude opus + 2× lokalne (qwen3.6 + deepseek-r1)
- Privacy mode = wymusza local → zero cost overhead

## Performance — Spike #1 results

| Model | Cold start | Warm | Tokens/sec |
|---|---|---|---|
| qwen3.6:latest (5090) | 33.3s | 20.6s | ~50 t/s |
| qwen3-coder:30b (5090) | ~25s | 12s | ~80 t/s |
| qwen3:32b (4090) | ~60s | 30s | ~30 t/s |
| deepseek-r1:32b (4090) | DISABLED — VRAM constraint, ~5 t/s with CPU offload |

Po `OLLAMA_KEEP_ALIVE=24h` modele zostają w VRAM → cold start tylko po reboot.

## vLLM — tryb wsadowy (batch), NIE drugi stały serwis

Decyzja (trial 2026-07-09, RTX 5090 32G / Blackwell): **NO-GO jako stały drugi serwis obok Ollamy;
GO jako narzędzie wsadowe.** Pełna notatka: `.priv/decisions/2026-07-09-vllm-vs-ollama-trial.md`.

Zmierzone (identyczny skrypt asyncio, wspólny system-prefix, 24 żądania/poziom, `max_tokens=256`, `temp=0`):

| Współbieżność | vLLM tok/s | Ollama tok/s | Przewaga | vLLM p95 | Ollama p95 |
|---|---:|---:|---:|---:|---:|
| 1 | 236.9 | 240.3 | remis (–1.4%) | 1.08 s | 1.05 s |
| 3 | 487.9 | 381.8 | +27.8% | 1.55 s | 2.01 s |
| 8 | 1018.1 | 400.8 | 2.5× | 1.87 s | 5.10 s |

- **Interaktywnie (bridge, pętle agentowe, conc 1–3) → Ollama.** Punkt pracy to conc=1 (remis);
  +28% przy conc=3 spłaca drugi serwis dopiero przy ≥3 równoległych sesjach na modelu coder.
  Ollama trzyma współrezydentną trójkę (qwen3-coder + lfm2.5 + juror, `keep_alive=-1`) — zero cold-startów.
- **Wsadowo (blast-bench: setki żądań, jeden model, okno na wyłączność karty, conc 8+) → vLLM.**
  Przewaga 2.5× i rosnąca; utrata współrezydencji nic nie kosztuje, bo to okno na wyłączność.

Receptura wsadowa (trzymana jako narzędzie, NIE demon — odpalana na czas eksperymentu):

```bash
# izolowany venv: torch 2.11+cu130, vLLM 0.24.0
VLLM_USE_FLASHINFER_SAMPLER=0 \      # obejście landminy JIT samplera na sm_120 (Blackwell)
vllm serve QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ \
  --port 8001 --gpu-memory-utilization 0.90 --max-model-len 32768 --enable-prefix-caching
# serwer OpenAI-compatible na :8001 — bench/bridge celują minimalną zmianą base_url
```

> ⚠ NIE uruchamiać równolegle z rezydentną parą Ollamy na jednej 32G karcie (15.7G wag + ~11G KV) —
> to okno time-sharingu GPU, zwolnij modele Ollamy na czas przebiegu. Spec-decoding pomijać
> (qwen3.6 / A3B-MoE = zero zysku). **Próg re-ewaluacji:** interaktyw regularnie ≥3 sesje równoległe
> na coderze → wróć do tabeli.

## Failure modes

| Scenario | Detection | Fallback |
|---|---|---|
| Local machine offline | TCP refuse / 60s timeout | Bridge retries 1×, then errors out |
| Ollama crash | Service restart loop | Auto-recovery via systemd |
| LAN partition | curl /api/tags fails | Switch to Anthropic native |
| Bridge crash | MCP disconnect | Claude Code restarts MCP, fall back to native if persistent |
| Privacy violation | Hook BLOCK exit 2 | User retries with local tool |

## Diagnostics

```bash
# Bridge logs
tail -f /var/log/blast-llm-bridge.log

# MCP visibility check (in Claude Code)
/mcp

# Test ping (po skonfigurowaniu)
/blast:ping-llm
```

## Environment variables — what goes where

Source: `.blast/.env.example` na repo root. Skopiuj do `.env`, wypełnij, source przed użyciem.

### Required for cloud features (jury, spike reproduction)

| Var | Required by | Where to get |
|---|---|---|
| `GEMINI_API_KEY` | JURY_3_FLASH3 (security, validate-design --debate, review --debate), spike-3 driver | https://aistudio.google.com/app/apikey |
| `ANTHROPIC_API_KEY` | spike-3 driver standalone (CLI mode = NOT needed for normal blast) | https://console.anthropic.com/settings/keys |
| `OPENROUTER_API_KEY` | OPTIONAL — reserved for future unified cloud LLM dispatcher (~100 models) | https://openrouter.ai/keys |
| `DEEPSEEK_API_KEY` | OPTIONAL — reserved for future N=4 jury (4 cloud providers) | https://platform.deepseek.com/api_keys |

### Required for local Ollama (HYBRID, privacy mode)

| Var | Default | Used by |
|---|---|---|
| `BLAST_OLLAMA_UBUNTU` | `http://192.168.5.60:11434` | blast-llm-bridge MCP server, spike-1/3 drivers |
| `BLAST_OLLAMA_WIN11` | `http://192.168.5.70:11434` | bridge (currently DISABLED — VRAM constraint) |
| `BLAST_LLM_TIMEOUT_S` | `240` | bridge per-call timeout (covers cold loads) |

### Activation flow

```bash
cp .blast/.env.example .blast/.env
# Edit .blast/.env: fill in the keys you actually need
set -a; source .blast/.env; set +a
# Restart Claude Code so MCP bridge picks up env vars on stdio reconnect
```

### Privacy gate enforcement

When `spec.json.privacy: local-only` is set, the `blast-privacy-gate.py` PreToolUse hook BLOCKS calls to:
- `mcp__*` external tools (cloud LLMs)
- Any agent matcher pattern in EXTERNAL_TOOL_PATTERNS

Cloud keys (GEMINI_API_KEY, etc.) are loaded but UNUSED in privacy mode. Local-only routing falls back to qwen3.6:latest + qwen3-coder:30b via bridge.
