# Spike #2 — Bridge MVP (Runbook + Report Template)

**Źródło**: Phase 0 z `../../decisions/2026-05-05-sdd-number-one-roadmap.md`
**Data**: 2026-05-06 (start)
**Tagi**: spike, mcp, bridge, ollama, multi-llm, fala-10
**Status**: PASS — bridge MVP działa, używany przez Spike-3 i HYBRID/JURY config

---

## Cel

Zweryfikować że `blast-llm-bridge` MCP server:
1. **Loads w Claude Code** — `/mcp` widzi 4 nowe tools
2. **Cross-machine** — wywołania z Claude Code dochodzą do Ubuntu (5090) i Win 11 (4090) Ollama
3. **Latency acceptable** — full call (Claude → bridge → Ollama → response) <2 min na model
4. **Error handling** — timeout, connection refused, malformed → readable error w Claude Code

Po PASS — fundament Fala 10 (production multi-LLM bridge) jest sprawdzony.

## Decision criteria

| Wynik | Skutek |
|---|---|
| Wszystkie 4 tools działają, latency 30s-2min | ✅ PASS — go to Fala 10 implementation |
| Tools loadują się ale nie odpowiadają | ⚠️ Network/firewall issue — diagnose |
| MCP nie load'uje się w Claude Code | ⚠️ Settings issue lub Python deps missing — fix and retry |
| Latency >5min lub modele timeout'ują | ❌ FAIL — investigate Ollama config, OLLAMA_KEEP_ALIVE |

---

## Część 1 — Setup (~15 min)

### 1.1 Install Python deps na maszynie z Claude Code

Bridge runs jako stdio MCP server, spawned by Claude Code. Process musi mieć dostęp do `mcp` i `httpx`.

```bash
# Jeśli używasz pyenv lub system Python
pip install mcp httpx

# Lub jeśli wolisz uv (fast):
uv pip install mcp httpx

# Lub virtualenv:
python3 -m venv .blast-mcp-venv
source .blast-mcp-venv/bin/activate
pip install mcp httpx
```

Gdzie? Na maszynie z której odpalasz **Claude Code**. To zwykle Twoja main workstation — w tym setupie prawdopodobnie Win 11.

### 1.2 Sprawdź IP adresy obu maszyn

Bridge config domyślnie: `BLAST_OLLAMA_UBUNTU=http://192.168.5.60:11434`, `BLAST_OLLAMA_WIN11=http://192.168.5.70:11434`.

Z każdej maszyny zweryfikuj:
```bash
# Ubuntu
hostname -I
# Powinno pokazać 192.168.5.60 (lub Twój)

# Win 11 (PowerShell)
ipconfig | findstr IPv4
# Powinno pokazać 192.168.5.70 (lub Twój)
```

Jeśli IP są inne — zmień w config (sekcja 1.4).

### 1.3 Sprawdź że Ollama nasłuchuje na 0.0.0.0 (post-Spike #1 powinno być)

Z OBU maszyn:
```bash
# Ubuntu / Win 11 (PowerShell)
curl http://192.168.5.60:11434/api/tags  # Ubuntu z innej
curl http://192.168.5.70:11434/api/tags  # Win 11 z innej
```

Powinno zwrócić JSON z listą modeli. Jeśli timeout — wróć do Spike #1 sekcja 1.5 (firewall + OLLAMA_HOST).

### 1.4 Skonfiguruj IP w bridge'u (jeśli inne niż defaults)

**Opcja A** — environment variables (bez modyfikacji kodu):

Na Win 11 PowerShell:
```powershell
[Environment]::SetEnvironmentVariable("BLAST_OLLAMA_UBUNTU", "http://192.168.5.60:11434", "User")
[Environment]::SetEnvironmentVariable("BLAST_OLLAMA_WIN11",  "http://192.168.5.70:11434", "User")
[Environment]::SetEnvironmentVariable("BLAST_LLM_TIMEOUT_S", "120", "User")
```

Restart Claude Code app żeby env vars się załadowały.

**Opcja B** — edycja kodu:

Otwórz `.claude/mcp/blast-llm-bridge.py`, znajdź `CONFIG = {`, zmień `endpoints` URLs.

### 1.5 Smoke test bridge'a stand-alone

Bez Claude Code, sprawdź że Python skrypt w ogóle startuje:

```bash
# Z directorium projektu
cd /path/to/claude_code-template

# Spróbuj odpalić bridge — powinien czekać na stdin (cisza w konsoli to OK)
python3 .claude/mcp/blast-llm-bridge.py
# Ctrl+C żeby zamknąć
```

Jeśli widzisz exception (np. `ModuleNotFoundError: No module named 'mcp'`) — wróć do 1.1.

### 1.6 Register MCP server w Claude Code

Edytuj `.claude/settings.json`. Dodaj sekcję `mcpServers`:

```json
{
  "permissions": { ... istniejące ... },
  "hooks": { ... istniejące Fala 5 ... },
  "mcpServers": {
    "blast-llm-bridge": {
      "command": "python3",
      "args": [".claude/mcp/blast-llm-bridge.py"],
      "env": {
        "BLAST_OLLAMA_UBUNTU": "http://192.168.5.60:11434",
        "BLAST_OLLAMA_WIN11":  "http://192.168.5.70:11434"
      }
    }
  }
}
```

**Path note**: `python3` musi być w PATH. Na Win 11 zwykle to `python` (bez 3). Możliwe że trzeba pełną ścieżkę:
- Linux/Mac: `/usr/bin/python3`
- Win 11: `C:\\Python313\\python.exe` lub `C:\\Users\\Blazek\\AppData\\Local\\Programs\\Python\\Python313\\python.exe`

### 1.7 Restart Claude Code

Zamknij Claude Code app w pełni (Quit, nie tylko close window). Otwórz ponownie. Otwórz projekt.

---

## Część 2 — Verify MCP loaded

### 2.1 Sprawdź że tools widać

W Claude Code:
```
/mcp
```

Powinno pokazać listę MCP servers. Szukaj `blast-llm-bridge` ze statusem `connected`.

Plus:
```
/help
```

W liście dostępnych tools szukaj `mcp__blast-llm-bridge__ask_*` — powinny być 4.

### 2.2 Jeśli MCP nie load'uje się

Najczęstsze przyczyny:
1. **Python not in PATH** — użyj pełnej ścieżki w `command`
2. **`mcp` package not installed** — `pip install mcp httpx` w Pythonie którego używa Claude Code
3. **Permission errors** — chmod +x na `.py` file (Linux/Mac); na Win to nie problem
4. **JSON syntax error w settings.json** — sprawdź `python -m json.tool .claude/settings.json`
5. **Bridge crashes na start** — dodaj `print` debug do skryptu albo zaloguj do pliku

Debug:
```bash
# Spawn bridge ręcznie z terminalu, przeczytaj stderr
python3 .claude/mcp/blast-llm-bridge.py 2>bridge-stderr.log
# Ctrl+C, sprawdź log
```

---

## Część 3 — Test funkcjonalny

### 3.1 Run /blast:ping-llm

```
/blast:ping-llm
```

Claude wywoła wszystkie 4 modele równolegle. Spodziewany czas: 30s-2min total (zależy od cold/warm state modeli).

### 3.2 Wpisz wyniki w tabelę

| Model | Maszyna | Latency | Tokens/s | Status |
|---|---|---|---|---|
| qwen3.6:27b | Ubuntu (5090) | _____ s | _____ | ☐ |
| qwen3-coder:30b | Ubuntu (5090) | _____ s | _____ | ☐ |
| qwen3:32b | Win 11 (4090) | _____ s | _____ | ☐ |
| deepseek-r1:32b | Win 11 (4090) | _____ s | _____ | ☐ |

### 3.3 Sanity check

- Czy każdy model odpowiedział?
- Czy format `[model @ machine | N tokens | Xs | Y tok/s]` widać w odpowiedzi?
- Czy latency jest podobna do Spike #1 baseline?

### 3.4 Manualny stress test (opcjonalny)

Wyślij dłuższy prompt (np. validate-design z Spike #1) do qwen3.6:27b — sprawdź czy bridge handle'uje 1-2 min generation bez timeout'u.

---

## Część 4 — Wyniki (FILL IN)

### 4.1 MCP loading

- ☐ `/mcp` shows `blast-llm-bridge` as connected
- ☐ 4 tools visible: ask_ubuntu_qwen36, ask_ubuntu_qwen3_coder, ask_win11_qwen3_32b, ask_win11_deepseek_r1

### 4.2 Functional test

(z Część 3.2 wyżej)

### 4.3 Network behavior

- ☐ Cross-machine calls działają (Win 11 → Ubuntu, jeśli Claude Code odpalony na Win 11)
- ☐ No firewall blocks
- ☐ No timeout issues for typical 30s-2min generations

### 4.4 Error handling

Test edge cases:
- ☐ Wyłącz Ollama na jednej maszynie → bridge zwraca helpful error (nie hang)
- ☐ Wyślij invalid model name w args → bridge zwraca "Unknown tool"
- ☐ Bardzo długi prompt (>50k tokens) → behaves correctly

---

## Część 5 — Decision (FILL AFTER TESTS)

**Verdict**: ☐ PASS / ☐ WARN / ☐ FAIL

**Update do planu Fala 10** (na bazie wyników):

```markdown
## Update post-Spike #2

[Wpisz lessons learned i decision points]

### Co działało:
- ...

### Co wymaga uwagi w pełnej Fali 10:
- ...

### Architectural decisions confirmed:
- ...
```

---

## Część 6 — Notes / Surprises

(Free-form)

---

## Następny krok

Po PASS:
- Plan v3 update z Spike #2 results
- Decision: kiedy startować pełen Fala 10 (production bridge z OpenRouter, Gemini direct, DeepSeek direct)
- Czy zaczynamy od Fala 7 (catch-up SOTA) i wracamy do Fali 10 z nauczkami z #2

Po FAIL/WARN: diagnostyka, fix, retry. Spike #2 nie jest done dopóki nie ma 4/4 tools działających.

---

## SPIKE #2 — FINAL RESULTS

**Closed**: 2026-05-06 ~10:30 UTC
**Status**: ✅ **PASS** — bridge production-ready (MVP)

### Final test results (per-model unique prompts)

| Tool | Model (verified header) | Maszyna | Latency | Tokens/s | Identity |
|---|---|---|---|---|---|
| ask_ubuntu_qwen36 | qwen3.6:latest | Ubuntu (5090) | 1.7s warm | 177.4 | ✓ |
| ask_ubuntu_qwen3_coder | qwen3-coder:30b | Ubuntu (5090) | 0.1s warm | 236.5 | ✓ |
| ask_win11_qwen3_32b | qwen3:32b | Win 11 (4090) | 35.2s | 5.1 | ✓ |
| ask_win11_deepseek_r1 | deepseek-r1:32b | Win 11 (4090) | 63.0s | 4.2 | ✓ |

### Lessons learned

1. **MCP config location matter** — Claude Code Cowork czyta `.mcp.json` w project root, NIE `.claude/settings.json` (mcpServers tam są ignorowane przez Cowork). User-level config jest w `~/.claude.json`.

2. **Project trust required** — Claude Code może wymagać explicit approval dla MCP server z project-level config (security feature against malicious git pulls).

3. **Ollama prefix cache cross-pollution** — jeśli kilka modeli na tym samym hoście dostaje IDENTYCZNY prompt, drugi+ wywołanie może zwrócić cached completion z pierwszego modelu. Fix: per-model unique prompts.

4. **System service vs user-level conflict** — `ollama serve` jako user blokuje port 11434 dla system service (auto-restart loop, exit 1). Plus dwa różne stores (~/.ollama vs /usr/share/ollama/.ollama). Trzymać się jednego.

5. **OLLAMA_KEEP_ALIVE=24h** mandatory na obu maszynach — bez tego każde wywołanie po 5 min idle = cold start tax.

6. **MCP server reload** wymaga **full Claude Code restart**, nie tylko `/mcp` Reconnect. Reconnect tylko reset connection, nie reload Python kodu.

7. **OneDrive sync lag** — edycje plików `.py` w sandbox nie propagują natychmiast na Win 11. Wymuszanie sync przez "Always keep on this device" pomaga.

### Architecture confirmed

```
Win 11 (Claude Code host)              Ubuntu (server, 5090)
  ├─ Claude Code (Opus 4.7)               ├─ Ollama service (0.0.0.0:11434)
  └─ blast-llm-bridge.py (stdio)          │  ├─ qwen3.6:latest (35B-A3B MoE) ★ primary critic
       │                                  │  ├─ qwen3-coder:30b ★ code critic
       ├─→ http://localhost:11434         │  ├─ codestral:22b
       │   └─ qwen3:32b, deepseek-r1:32b  │  └─ deepseek-coder-v2:16b
       │                                  │
       └─→ http://192.168.5.60:11434 (LAN)
           └─ Ubuntu Ollama (4 modele)
```

### Performance baseline

- **Pattern A debate** (3 calls: Author + Critic + Judge): ~30-90s total dependning on warm/cold state
- **Pattern B jury N=4** parallel cross-machine: ~60s total (limited by slowest, deepseek-r1 cold)
- **Single qwen3.6:latest call** warm: 1-30s depending on response length

### Bridge MVP scope satisfied

- ✅ stdio MCP server runs as Claude Code child process
- ✅ Cross-machine HTTP calls to Ollama (localhost + LAN)
- ✅ 4 tools dynamically registered with proper schemas
- ✅ Error handling: timeout, connection refused, unknown tool
- ✅ Metadata header in response: `[model @ machine | tokens | duration | tok/s]`

### Out of scope (Fala 10 production)

- Cloud LLM APIs (Anthropic direct, Gemini, DeepSeek, OpenRouter)
- Privacy mode (local-only enforcement via patterns)
- Per-phase routing config (`.blast/steering/llm-routing.md`)
- Async/parallel execution within single tool call
- HTTP MCP server (vs stdio) for always-on daemon

**Spike #2 PASS — fundament dla Fala 10 udowodniony, można odłożyć Fala 10 implementację bo bridge MVP jest functional.**



---

## Verdict (uzupełnione 2026-05-06)

Bridge przeszedł `/blast:ping-llm` smoke test (4 modele, unique prompts, parallel call). Latencja 30s-2min per model w zakresie criterium. Cross-machine working.

**Realnie używany przez**:
- Spike-3 (qwen3.6 jako jury/critic — działało po naprawie VRAM hoga)
- `validate-impl --thorough` HYBRID composition (configured)
- `security` JURY_3_FLASH3 composition (configured)
- `/blast:drift` Step 4 semantic delegation (configured)

**Limitations confirmed for production**:
- Tylko 4 hardcoded model wrappers — dynamic registry needed
- Sync inference, no retry/backoff
- No rate limiting per model
- Win11 endpointy są zapisane w bridge ale fizycznie not viable (32B Q4 spillują VRAM)

→ Production-grade bridge = osobna inwestycja (Fala 10 v2)

→ Audit szczegółów: `../../INVENTORY.md` sekcja Fala 10
