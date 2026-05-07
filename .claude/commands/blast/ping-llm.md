---
description: "Test bridge — wywołaj 2 lokalne modele Ubuntu z UNIQUE prompts (bypass Ollama cache)"
allowed-tools: mcp__blast-llm-bridge__ask_ubuntu_qwen36, mcp__blast-llm-bridge__ask_ubuntu_qwen3_coder
argument-hint: (no args)
---

# blast:ping-llm — Test Spike #2 Bridge

Wywołaj dwa lokalne modele równolegle, KAŻDY z UNIQUE prompt'em. Per-model prompts są niezbędne żeby ominąć Ollama prefix cache (jeśli wszystkie modele dostaną ten sam prompt, drugi+ wywołanie na tym samym hoście może zwrócić cached completion z pierwszego modelu).

## Per-model prompts (UNIQUE)

Wywołaj oba narzędzia **równolegle** (parallel), każde z dedykowanym prompt'em:

### 1. ask_ubuntu_qwen36
prompt: `Reply with EXACTLY one sentence: "Hello, I am qwen3.6 (35B-A3B MoE), serving as a general critic from Ubuntu 5090."`

### 2. ask_ubuntu_qwen3_coder
prompt: `Reply with EXACTLY one sentence: "Hello, I am qwen3-coder 30B, serving as a code critic from Ubuntu 5090."`

Każdy prompt jest **unikatowy** — żaden cache prefix w Ollamie nie zadziała.

## Output

Pokaż user'owi tabelę:

| Tool | Model (header) | Maszyna | Latency | Tokens/s | Identity match |
|---|---|---|---|---|---|
| ask_ubuntu_qwen36 | _____ | Ubuntu (5090) | _____ | _____ | ☐ |
| ask_ubuntu_qwen3_coder | _____ | Ubuntu (5090) | _____ | _____ | ☐ |

Kolumny:
- **Model (header)**: tag z `[model @ machine | ...]` headera bridge'a — confirm że bridge faktycznie route'uje do tego co myślisz (np. że `ask_ubuntu_qwen36` używa `qwen3.6:latest`, nie starego `qwen3.6:27b`)
- **Identity match**: czy treść responsa zgadza się z prompt'em (model wymienił **swoją** nazwę)
- ✓ jeśli model match'uje, ✗ jeśli np. qwen3-coder powiedział "I am qwen3.6" (cache miss/hit issue)

## Verdict

- ✅ **PASS**: 2/2 tools odpowiada, headers correct (model match request), identity match dla każdego, latency <2 min
- ⚠️ **WARN**: 2/2 transport OK ale ≥1 identity mismatch — możliwe nadal cache issue (skontroluj prompts unique)
- ❌ **FAIL**: ≥1 connection error — bridge / network problem

Jeśli PASS — Spike #2 closure, ruszamy do Fali 7 lub Fali 10.
