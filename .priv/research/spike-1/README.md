# Spike #1 — Local Cluster Validation (Runbook + Report Template)

**Źródło**: Phase 0 z `../../decisions/2026-05-05-sdd-number-one-roadmap.md`
**Data**: 2026-05-05 (start)
**Tagi**: spike, local-cluster, ollama, qwen, deepseek, performance, quality
**Status**: IN PROGRESS

---

## Cel

Zweryfikować czy klaster lokalny (Ubuntu+RTX 4090, Win 11+RTX 5090, 10 Gbps LAN) z Qwen3.6 + DeepSeek V4 Flash daje sensowną performance dla blast'owego workload — czyli czy lokalne LLM mogą realnie pełnić role Critic / Juror / Devil's Advocate w debate framework (Fala 9), zamiast tylko być fallbackiem privacy.

## Decision criteria po spike'u

Po wypełnieniu sekcji "Wyniki" poniżej, podejmujemy decyzję:

| Wynik | Interpretacja | Skutek dla planu |
|---|---|---|
| Qwen jest **comparable** do Claude opus na validate-design | Local ma silną pozycję | Pattern A z Qwen jako Critic; agresywne użycie local |
| Qwen jest **noticeably worse** ale wciąż useful | Local OK na drugą rolę | Pattern B (jury) z Claude+Qwen — diversity > raw quality |
| Qwen jest **much worse** | Local nie nadaje się do critic role | Local TYLKO dla privacy mode + jako 1 z N w jury |
| Throughput drastycznie spada przy 2+ concurrent | Wąska gardło = Ollama default config | Migrate do vLLM (post-MVP) lub Pattern Y (pool z 2 maszyn) |
| Cross-machine latency >500ms | LAN to bottleneck | Pin tasks → bliskiej maszyny, unikaj cross-machine routing |

---

## Część 1 — Setup (~30-60 min)

### 1.1 Ubuntu — sprawdź obecny stan

```bash
# Verify Ollama running
systemctl status ollama
# Should show: active (running)

# Verify it's listening on 0.0.0.0 (not just localhost)
sudo ss -tlnp | grep 11434
# CRITICAL: jeśli pokazuje 127.0.0.1:11434 zamiast 0.0.0.0:11434
# to Ollama nie przyjmuje connections z LAN — fix poniżej.

# Find local IP on LAN
ip addr show | grep "inet " | grep -v "127.0.0.1"
# Note the IP, np. 192.168.1.10 — będziemy nazywać UBUNTU_IP
```

**Jeśli Ollama tylko na localhost** — zmień:

```bash
# Ubuntu: edit systemd service
sudo systemctl edit ollama.service
# Add:
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"

# Reload + restart
sudo systemctl daemon-reload
sudo systemctl restart ollama
sudo ss -tlnp | grep 11434  # Verify now 0.0.0.0:11434
```

### 1.2 Ubuntu — pull models

```bash
# Qwen3.6-35B-A3B (general/design role)
ollama pull qwen3.6:35b-a3b
# (jeśli tag nie istnieje, sprawdź `ollama search qwen` lub odwiedź ollama.com/library/qwen3.6)

# Qwen3-Coder-30B (code-specialized critic)
ollama pull qwen3-coder:30b

# Verify
ollama list
# Should show both models with sizes ~17-20GB each
```

### 1.3 Win 11 — install Ollama

```powershell
# Pobierz instalator z https://ollama.com/download/windows
# Run installer, default options OK

# Po instalacji — verify
ollama --version

# CRITICAL: Windows Ollama domyślnie też tylko na localhost.
# Set environment variable PERMANENTLY:
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "Machine")
# Restart Ollama (Task Manager → kill → relaunch from Start Menu)
# Or restart Windows.

# Verify
netstat -ano | findstr 11434
# Should show 0.0.0.0:11434 LISTENING

# Find LAN IP
ipconfig | findstr IPv4
# Note IP — WIN_IP, np. 192.168.1.11
```

### 1.4 Win 11 — pull models

```powershell
# DeepSeek V4 Flash (reasoning/security role)
ollama pull deepseek-v4:flash
# Jeśli tag nie istnieje, check ollama.com/library/deepseek-v4

# Qwen3-32B-Instruct (general fallback)
ollama pull qwen3:32b-instruct

# Verify
ollama list
```

### 1.5 Firewall — open port 11434 between machines

**Ubuntu**:
```bash
# Find Win 11 IP first, then:
sudo ufw allow from <WIN_IP> to any port 11434
# Or for whole subnet:
sudo ufw allow from 192.168.1.0/24 to any port 11434
sudo ufw status verbose
```

**Win 11** (run PowerShell as Admin):
```powershell
New-NetFirewallRule -DisplayName "Ollama LAN" `
  -Direction Inbound -LocalPort 11434 -Protocol TCP `
  -Action Allow -RemoteAddress 192.168.1.0/24

# Verify
Get-NetFirewallRule -DisplayName "Ollama LAN" | Format-List
```

### 1.6 Verify connectivity (cross-machine)

**From Win 11**, test Ubuntu:
```powershell
# Replace UBUNTU_IP
curl http://<UBUNTU_IP>:11434/api/tags
# Expected: JSON with list of models (qwen3.6, qwen3-coder)
```

**From Ubuntu**, test Win 11:
```bash
curl http://<WIN_IP>:11434/api/tags
# Expected: JSON with deepseek-v4:flash, qwen3:32b-instruct
```

Jeśli timeout / connection refused — wróć do 1.1, 1.3 lub 1.5.

---

## Część 2 — Test material (test prompt)

Użyjemy realistycznego validate-design prompt'u. **Skopiuj ten cały blok jako test prompt:**

```
You are a senior software architect reviewing a technical design document.

# Feature: User Authentication via OAuth2

## Requirements
1. WHEN a user clicks "Login", THE SYSTEM SHALL redirect to OAuth provider authorization URL.
2. WHEN OAuth provider returns authorization code, THE SYSTEM SHALL exchange it for access token.
3. WHILE access token is valid, THE SYSTEM SHALL include it in all API requests.
4. IF refresh token expires, THEN THE SYSTEM SHALL force re-authentication.
5. WHEN user clicks "Logout", THE SYSTEM SHALL revoke tokens with provider AND clear local session.

## Design

### Architecture Pattern
Layered: Auth Controller → Token Service → Provider Adapter → Storage.
Token storage: encrypted in HttpOnly cookies (web) + Keychain (mobile).

### Components
- AuthController (src/auth/controller.py) — handles /login, /callback, /logout endpoints.
- TokenService (src/auth/tokens.py) — encrypt/decrypt, refresh logic, expiry tracking.
- ProviderAdapter (src/auth/providers/{google,github}.py) — OAuth2 specific quirks per provider.
- SessionStorage (src/auth/session.py) — stores active session metadata in Redis.

### Verification Strategy
- Local test: pytest tests/test_auth_flow.py::test_oauth_full_cycle -v
- Smoke check: python -c "from src.auth.controller import AuthController; AuthController()"
- E2E probe: curl http://localhost:8000/login -L → expect redirect to provider
- Expected signal: HTTP 302 with Location: header containing provider domain

## Your task
Review this design as Crucible (validate-design persona). Find weaknesses. Output exactly this format at the end:

---VERDICT---
VERDICT: <PASS|WARN|FAIL>
BLOCKING: <true|false>
FINDINGS: <integer count of issues>
NEXT_ACTIONS:
- <imperative command>
---END---

Look for: missing edge cases, security holes, scalability concerns, design completeness, peer-reviewable gaps. Limit to 3 most critical issues. Be specific.
```

**Zapisz powyższy prompt** do pliku `prompt.txt` na każdej maszynie — będziesz go używać 3-4 razy.

---

## Część 3 — Wykonanie testów

### 3.1 Test 1: Quality Comparison (cold start)

Wywołaj prompt na każdym modelu **z cold start** (Ollama dopiero co wstartowane lub model nie był używany >1h).

**Ubuntu (Qwen3.6)**:
```bash
time ollama run qwen3.6:35b-a3b "$(cat prompt.txt)" > qwen3.6_response.txt
# Note: time, tokens/s (sprawdź `ollama ps`), VRAM use (`nvidia-smi`)
```

**Ubuntu (Qwen3-Coder)**:
```bash
time ollama run qwen3-coder:30b "$(cat prompt.txt)" > qwen3-coder_response.txt
```

**Win 11 (DeepSeek)**:
```powershell
Measure-Command { ollama run deepseek-v4:flash "$(Get-Content prompt.txt -Raw)" } | Tee-Object -FilePath deepseek_timing.txt
ollama run deepseek-v4:flash "$(Get-Content prompt.txt -Raw)" > deepseek_response.txt
```

**Win 11 (Qwen3-32B)**:
```powershell
ollama run qwen3:32b-instruct "$(Get-Content prompt.txt -Raw)" > qwen3-32b_response.txt
```

**Claude opus** (manualnie w Claude Code lub claude.ai):
- Wklej prompt
- Skopiuj odpowiedź → `claude-opus_response.txt`
- Note total time od submission do completion

### 3.2 Test 2: Warm response (drugi raz)

Po cold start, odpal **ten sam prompt** drugi raz na każdym modelu. Mierz czas.

```bash
time ollama run qwen3.6:35b-a3b "$(cat prompt.txt)" > /dev/null
# 2nd run: model is hot in VRAM, no load overhead
```

### 3.3 Test 3: Concurrent throughput

**Ubuntu** (test concurrent na Qwen3.6):
```bash
# Two parallel calls — przez nawiasy w bash
( ollama run qwen3.6:35b-a3b "$(cat prompt.txt)" > parallel_1.txt ) &
( ollama run qwen3.6:35b-a3b "$(cat prompt.txt)" > parallel_2.txt ) &
time wait
# Note: total time vs serial 2× single. Default Ollama queue'uje requests per model.
```

### 3.4 Test 4: Cross-machine latency

**Z Ubuntu, query Win 11 model**:
```bash
time curl http://<WIN_IP>:11434/api/generate \
  -d '{"model": "deepseek-v4:flash", "prompt": "test", "stream": false}' \
  > /dev/null
# Note: time differs from local call by network overhead
```

**Z Win 11, query Ubuntu model**:
```powershell
Measure-Command {
  Invoke-RestMethod -Uri "http://<UBUNTU_IP>:11434/api/generate" `
    -Method POST -Body '{"model":"qwen3.6:35b-a3b","prompt":"test","stream":false}'
}
```

---

## Część 4 — Wyniki (FILL IN AFTER TESTS)

### 4.1 Quality scoring (subjective, 1-10)

Compare each model's response to the same OAuth design prompt against Claude opus's response. Score each:

| Model | Quality 1-10 | Format compliance | Critical findings count | Notes |
|---|---|---|---|---|
| Claude opus (baseline) | 10 | ✓ | _____ | _____ |
| Qwen3.6-35B-A3B | _____ | _____ | _____ | _____ |
| Qwen3-Coder-30B | _____ | _____ | _____ | _____ |
| DeepSeek V4 Flash | _____ | _____ | _____ | _____ |
| Qwen3-32B-Instruct | _____ | _____ | _____ | _____ |

**Quality scoring guide**:
- 10: catches everything Claude catches, equal depth
- 7-9: catches most things, occasional misses or weaker reasoning
- 4-6: superficial, misses real issues, but format mostly OK
- 1-3: bad output, misses obvious issues, format broken

**Format compliance**: did model emit the `---VERDICT---` … `---END---` envelope verbatim? ✓ / ✗

### 4.2 Latency (seconds)

| Model | Cold start | Warm response | Tokens/sec |
|---|---|---|---|
| Qwen3.6-35B-A3B | _____ s | _____ s | _____ |
| Qwen3-Coder-30B | _____ s | _____ s | _____ |
| DeepSeek V4 Flash | _____ s | _____ s | _____ |
| Qwen3-32B-Instruct | _____ s | _____ s | _____ |
| Claude opus (reference) | _____ s | _____ s | (n/a — API) |

### 4.3 Concurrent (Qwen3.6, 2 parallel)

- Serial 2× single response time: _____ s
- Concurrent (parallel) response time: _____ s
- Speedup ratio: _____ (1.0 = no benefit, 2.0 = perfect parallel)
- VRAM use during concurrent: _____ GB / 24 GB

**Interpretacja**: jeśli ratio bliska 1.0 → Ollama queue'uje, jeden GPU = sequential. Jeśli >1.5 → kontekstowo równoległe (rzadkie).

### 4.4 Cross-machine

| Direction | Latency overhead vs local |
|---|---|
| Ubuntu → Win 11 (Ollama API call) | +_____ ms |
| Win 11 → Ubuntu (Ollama API call) | +_____ ms |

**Interpretacja**:
- <50 ms = LAN żywa, można freely route
- 50-200 ms = noticeable but acceptable
- >500 ms = something wrong (check switch, cable, or driver)

### 4.5 VRAM utilization

| Model | VRAM (idle) | VRAM (during inference) |
|---|---|---|
| Qwen3.6-35B-A3B (Ubuntu) | _____ | _____ |
| Qwen3-Coder-30B (Ubuntu) | _____ | _____ |
| DeepSeek V4 Flash (Win 11) | _____ | _____ |
| Qwen3-32B-Instruct (Win 11) | _____ | _____ |

**Concern threshold**: >22 GB na 4090 (24 GB) lub >30 GB na 5090 (32 GB) → margins are tight, problem if 2+ models loaded simultaneously.

---

## Część 5 — Decision (FILL AFTER ANALYSIS)

Bazując na wynikach:

**Quality verdict**: ☐ comparable / ☐ noticeably worse / ☐ much worse

**Per-protocol fitness**:
- Pattern A (Critique-Revise-Judge with local critic): ☐ recommended / ☐ acceptable / ☐ avoid
- Pattern B (Multi-Jury cross-provider): ☐ recommended / ☐ acceptable / ☐ avoid
- Pattern D (Devil's Advocate with local): ☐ recommended / ☐ acceptable / ☐ avoid

**Routing strategy decision**:
- ☐ Pattern Z (Pinned + Failover) — confirmed
- ☐ Pattern Y (Pool) — needed because concurrent kills throughput

**Update to llm-routing.md** (write below what should be the actual default):

```markdown
## Default debate config (after Spike #1)

| Faza | Protokół | Modele |
|---|---|---|
| validate-design | _____ | _____ |
| validate-impl | _____ | _____ |
| security | _____ | _____ |
```

**Concerns to track**:
- _____ (anything surprising or worth watching)
- _____

---

## Część 6 — Notes / surprises

(Free-form — wpisuj wszystko co nie pasowało do oczekiwań, edge cases, gotchas które inni mogą napotkać.)

---

## Kompletne next steps po spike #1

Gdy ten dokument jest wypełniony:

1. Commit do git (`../spike-1/README.md`)
2. Wróć do dyskusji z Claude — przeczytamy wyniki, zaktualizujemy plan jeśli trzeba
3. Decyzja: ruszamy ze Spike #2 (Bridge MVP), czy potrzebujemy adjustments w plan na podstawie tego co zobaczyliśmy

---

## SPIKE #1 — FINAL RESULTS (post-swap)

**Closed**: 2026-05-06 00:30 UTC
**Status**: ✅ **PASS** — local cluster production-viable

### Hardware swap performed

5090 moved from Win 11 → Ubuntu. 4090 moved Ubuntu → Win 11.

### Pre/post swap comparison (Ubuntu — qwen3.6:27b)

| Test | Pre-swap (4090, x16, driver 580) | Post-swap (5090, x16, driver 595) | Δ |
|---|---|---|---|
| Cold start | 5m 20s | 1m 29s | **3.6×** |
| Warm | 3m 42s | 45s | **4.9×** |
| VRAM use | 22.7/24 GB (CPU offload!) | comfortable na 32 GB | full GPU |
| Output quality | 9/10 (Claude-class) | 9/10 | preserved |

### Win 11 (4090) performance

- qwen3-coder:30b warm: 26s — code workload fast, no CPU offload (model 18GB on 24GB card)
- 3 monitors detected po DDU + clean driver install
- PCIe link: gen 4 x8 (ASRock M.2 lane sharing, OK, identical to before)

### PCIe surprise — 5090 zyskał na Ubuntu

ASRock Z790 Nova WiFi: gen 5 **x8** (M.2 contention)
MSI PRO Z790-A MAX WIFI: gen 5 **x16** (clean lanes)

5090 na Ubuntu dostaje 2× theoretical bandwidth → ~20% szybsza warm inference (45s vs 56s).

### Lessons learned

1. **BIOS update mandatory pre-Blackwell** — vM2 (2024-01) → vMA (2026-03) brought Intel 0x12B microcode + 5090 support
2. **Secure Boot reset** by major BIOS updates — must disable post-flash
3. **Driver Blackwell support** — 580 series unstable; 595+ from graphics-drivers PPA stable for 5090
4. **Open Kernel Modules vs Proprietary** — 580.x Open had issue; 595 standard worked
5. **PCIe lane allocation** depends heavily on motherboard — MSI Z790-A MAX better for GPU than ASRock Z790 Nova
6. **DDU + clean driver reinstall** for Windows side after GPU swap (avoids ghost 5090 driver entries)
7. **PPA strategy** — `add-apt-repository ppa:graphics-drivers/ppa` gives latest stable nvidia drivers for cutting-edge cards

### Final routing decision

Production cluster:
- **Ubuntu (5090)**: primary AI inference server, all premium models
- **Win 11 (4090)**: user's daily-driver, lekkie blast inference jeśli potrzeba (4090 + 24GB nadal top tier)

### Status klastra

- ✅ Cross-machine connectivity verified (Win 11 ↔ Ubuntu via curl /api/tags)
- ✅ Both Ollama instances running with auto-start
- ✅ Drivers latest on both sides
- ✅ Quality benchmarks meet Claude-class standard for local critic role
- ✅ Latency budget acceptable for blast Pattern A debate (~2 min total)

**Ready for Spike #2 — Bridge MVP.**


---

## Wyniki

**Data runu**: 2026-05-06
**Konfiguracja runu**: `--num_predict 4096 --num_ctx 8192 --keep_alive 30m`, dla qwen3.6 family `/no_think + think:false` na coding task
**Total runtime**: ~10 min Ubuntu only (win11 wycofane — 32B na 4090 24 GB → CPU offload, 5 tok/s)

### Performance per model (Ubuntu / RTX 5090, warm runs)

| Model | Coding tok/s | Analytical tok/s | Latency warm | Output quality |
|---|---:|---:|---:|---|
| qwen3.6:latest | 178 | 177 | 1.16s / 24s | OAuth audit findings sensible (PKCE, state) |
| qwen3.6:27b | 67 | 66 | 2.94s / 48s | Comparable do :latest, ~3× wolniej |
| **qwen3-coder:30b** | **246** | (skip) | **0.87s** | clean RateLimiter, mechanically correct |
| qwen3-coder-next | 18 | (skip) | 10.5s | clean ale 14× wolniejszy = not for hot path |

### Verdict per decision criteria (z runbooka)

> "Qwen comparable do Claude opus na validate-design"

✅ **TAK**. qwen3.6:latest 177 tok/s, 24s warm na pełen audit z złapaniem PKCE + state validation. Claude opus na to samo zadanie ~10-15s. Local jest ~2× wolniejszy ale jakościowo comparable, koszt $0.

> "qwen3-coder na coding"

✅ **DOMINUJE**. qwen3-coder:30b 246 tok/s, 0.87s warm, 871 chars czystego kodu. **Szybsze od Claude haiku przez API**. 

### Skutek dla planu (zaktualizowane vs original runbook)

- **Pattern Z (Pinned + Failover)** zatwierdzony dla Ubuntu/5090. Win11/4090 wymaga pre-tuning (Q3 quant, mniejszy num_ctx, lub mniejsze modele) zanim zostanie dodany do pool — TODO na później.
- **Pattern A (asymmetric)** enabled: qwen3-coder:30b jako Author w impl, qwen3.6:latest jako parallel critic w validate-impl HYBRID (potwierdzone w spike-3).
- **Pattern B (jury)** enabled tylko dla high-stakes (security, validate-design) z JURY_3_FLASH3 (potwierdzone w spike-3).
- `qwen3-coder-next` (79.7B) — DROP z default MODELS w bench. On-demand only dla rare deep-code-review.

### Hardware notes

- **VRAM gotcha**: domyślne `keep_alive` było ustawione na 24h dla qwen3-coder-next (poprzedni eksperyment), blokowało 30 GB VRAM. Standard 5min jest właściwy dla normalnego użycia. Dla bench/spike użyj jawnego `keep_alive: "30m"`.
- **5090 32 GB**: qwen3.6:latest (24 GB Q4) + 8k KV cache wchodzi czysto. qwen3-coder:30b (18.5 GB Q4) zostawia headroom na cross-machine pool. qwen3-coder-next (30 GB) blokuje wszystko inne.
- **win11 4090 24 GB**: 32B Q4 modele spillują KV cache → CPU offload → 5 tok/s. Wymaga albo Q3 quant albo mniejszych modeli.
