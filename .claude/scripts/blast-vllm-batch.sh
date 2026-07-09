#!/usr/bin/env bash
# blast-vllm-batch — open a GPU BATCH WINDOW for vLLM, then restore Ollama on exit.
#
# Decision 2026-07-09 (.priv/decisions/2026-07-09-vllm-vs-ollama-trial.md):
# vLLM is NO-GO as a persistent service, GO as a batch tool. This script is that
# tool — it is NOT a daemon. It:
#   1. unloads Ollama's resident models to free VRAM (the ollama SERVICE stays up
#      so the MCP bridge keeps working; models reload on the next request),
#   2. starts `vllm serve` (OpenAI-compatible) with the coder model,
#   3. waits until it is ready and prints the blast-bench command to use,
#   4. holds the window open until you Ctrl-C, then stops vLLM and frees the GPU.
#
# Nothing is enabled/persisted. Ctrl-C ends the window.
#
# Config via env (all optional):
#   BLAST_VLLM_VENV     path to the vLLM venv         (default: $HOME/vllm-venv)
#   BLAST_VLLM_MODEL    served model id               (default: QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ)
#   BLAST_VLLM_PORT     port                          (default: 8001)
#   BLAST_VLLM_GPU_UTIL gpu-memory-utilization        (default: 0.90)
#   BLAST_VLLM_MAXLEN   max-model-len                 (default: 32768)
#   BLAST_OLLAMA_UBUNTU ollama base url               (default: http://localhost:11434)

set -uo pipefail

VENV="${BLAST_VLLM_VENV:-$HOME/vllm-venv}"
MODEL="${BLAST_VLLM_MODEL:-QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ}"
PORT="${BLAST_VLLM_PORT:-8001}"
GPU_UTIL="${BLAST_VLLM_GPU_UTIL:-0.90}"
MAXLEN="${BLAST_VLLM_MAXLEN:-32768}"
OLLAMA_URL="${BLAST_OLLAMA_UBUNTU:-http://localhost:11434}"

log() { printf '\n[blast-vllm-batch] %s\n' "$*"; }

VLLM_PID=""
cleanup() {
  if [ -n "$VLLM_PID" ]; then
    log "Stopping vLLM (pid $VLLM_PID) and freeing the GPU…"
    kill "$VLLM_PID" 2>/dev/null || true
    wait "$VLLM_PID" 2>/dev/null || true
  fi
  log "Batch window closed. Ollama models reload on the next request — nothing to restore."
}
trap cleanup EXIT INT TERM

# ── 1. free Ollama VRAM (keep the service running for the bridge) ──────────────
log "Unloading Ollama resident models to free VRAM (service stays up)…"
if command -v ollama >/dev/null 2>&1; then
  # `ollama ps` lists loaded models; column 1 is the name. `ollama stop` unloads.
  ollama ps 2>/dev/null | awk 'NR>1 && $1!="" {print $1}' | while read -r m; do
    ollama stop "$m" 2>/dev/null && echo "  unloaded $m"
  done
else
  log "ollama CLI not found — set keep_alive=0 via API instead"
  curl -s "$OLLAMA_URL/api/ps" 2>/dev/null \
    | grep -o '"model":"[^"]*"' | cut -d'"' -f4 | while read -r m; do
        curl -s "$OLLAMA_URL/api/generate" \
          -d "{\"model\":\"$m\",\"keep_alive\":0}" >/dev/null 2>&1 && echo "  unloaded $m"
      done
fi

# ── 2. locate + start vLLM ─────────────────────────────────────────────────────
VLLM_BIN="$VENV/bin/vllm"
if [ ! -x "$VLLM_BIN" ]; then
  if command -v vllm >/dev/null 2>&1; then
    VLLM_BIN="$(command -v vllm)"
    log "Using vllm from PATH ($VLLM_BIN); set BLAST_VLLM_VENV to pin a venv."
  else
    log "ERROR: vLLM not found at $VLLM_BIN nor on PATH. Set BLAST_VLLM_VENV."
    exit 1
  fi
fi

log "Starting vLLM: $MODEL on :$PORT (gpu-util=$GPU_UTIL, max-len=$MAXLEN)…"
# VLLM_USE_FLASHINFER_SAMPLER=0 works around the sm_120 (Blackwell) JIT sampler landmine.
VLLM_USE_FLASHINFER_SAMPLER=0 "$VLLM_BIN" serve "$MODEL" \
  --port "$PORT" \
  --gpu-memory-utilization "$GPU_UTIL" \
  --max-model-len "$MAXLEN" \
  --enable-prefix-caching &
VLLM_PID=$!

# ── 3. wait for readiness ──────────────────────────────────────────────────────
log "Waiting for vLLM to become ready on :$PORT (up to ~4 min for cold load)…"
ready=0
for _ in $(seq 1 120); do
  if ! kill -0 "$VLLM_PID" 2>/dev/null; then
    log "ERROR: vLLM process exited during startup. Check its logs above."
    exit 1
  fi
  if curl -s "http://localhost:$PORT/v1/models" >/dev/null 2>&1; then
    ready=1; break
  fi
  sleep 2
done
if [ "$ready" -ne 1 ]; then
  log "ERROR: vLLM did not become ready in time."
  exit 1
fi

log "vLLM READY on http://localhost:$PORT — run your batch, e.g.:"
echo "    python3 .claude/scripts/blast-bench.py --engine vllm --base-url http://localhost:$PORT --task coding --output /tmp/vllm-bench.json"
echo
log "Batch window OPEN. Press Ctrl-C when done to stop vLLM and free the GPU."

# ── 4. hold open until the user ends the window ────────────────────────────────
wait "$VLLM_PID"
