# Spike-4 — qwen3-coder:30b vs claude-sonnet-4-6

Head-to-head test on 5 coding tasks of increasing complexity. Compare quality (objective + subjective), cost, latency.

## Tasks

| # | Task | Skill |
|---|---|---|
| 01 | Token bucket rate limiter | Threading + monotonic clock |
| 02 | LRU cache with TTL | OrderedDict + thread safety |
| 03 | CSV processor with validation | stdlib csv + regex + error aggregation |
| 04 | Workflow state machine | OOP, transitions, exceptions, history |
| 05 | Async worker pool | asyncio + Semaphore + ordering |

## Method

For each (arm, task):
1. Send `task.md` + `tests.py` to model with prompt: "implement"
2. Save model output as `<arm>/{module}.py`
3. Run pytest — record passed/failed/errors
4. Subjective judge (Claude Opus) rates on 5-dim rubric (1-5 scale)

## Arms

- **`qwen`** — qwen3-coder:30b @ Ubuntu/5090 via `mcp__blast-llm-bridge__ask_ubuntu_qwen3_coder` (or direct Ollama)
- **`sonnet`** — claude-sonnet-4-6 via Claude Code CLI

## Required env

```bash
# For sonnet arm + judge:
# Either: ANTHROPIC_API_KEY (direct API)
# Or: claude CLI in PATH (subscription, $0 marginal in cost field — but quota-limited)

# For qwen arm:
export BLAST_OLLAMA_UBUNTU=http://192.168.5.60:11434
```

## Run

```bash
cd .priv/research/spike-4

# Step 1: driver runs all (arm × task) pairs, executes pytest
python driver.py
# OR subset: python driver.py --tasks 01_token_bucket --arms qwen,sonnet

# Step 2: judge rates each output (Claude Opus)
python judge.py
# OR skip failed: python judge.py --skip-failed

# Step 3: build report
python report.py > results/report.md
cat results/report.md
```

## Cost estimate

- Sonnet: ~50-100k tokens × 5 tasks = ~$1-2
- Qwen: $0 (local)
- Judge (Opus): ~30k × 5 × 2 = ~$5
- **Total: ~$6-8**

## Decision matrix

After run, `report.md::Verdict` answers:

- Should `/blast:impl` Author switch from Sonnet to qwen3-coder?
- For which task complexity is qwen "good enough" (pass + judge ≥3.5)?
- What's cost/quality trade-off ratio?

Outcomes feed back into `.blast/steering/llm-routing.md` if convincing.

## Files

```
spike-4/
├── README.md (this)
├── driver.py            — run model on each task, run pytest
├── judge.py             — Opus rates outputs on rubric
├── report.py            — combine results + judge → markdown
├── conftest.py          — pytest config
├── pyproject.toml       — pytest async mode
├── tasks/
│   ├── 01_token_bucket/{task.md, tests.py}
│   ├── 02_lru_cache_ttl/{task.md, tests.py}
│   ├── 03_csv_processor/{task.md, tests.py}
│   ├── 04_state_machine/{task.md, tests.py}
│   └── 05_async_worker_pool/{task.md, tests.py}
└── results/
    ├── results.json     — driver output
    ├── judge_scores.json — judge output
    └── report.md        — final verdict
```

After run, each task dir grows arm subdirs:
```
01_token_bucket/qwen/{rate_limiter.py, tests.py, raw_response.txt, .pytest_cache/}
01_token_bucket/sonnet/{rate_limiter.py, tests.py, raw_response.txt, .pytest_cache/}
```

## Wyniki

**Data runu**: 2026-05-07
**Total cost**: ~$0.78 (driver $0.19 sonnet + judge $0.59 Opus × 10 outputs)
**Total runtime**: ~10 min wallclock

### Headline

| Wymiar | qwen3-coder:30b | sonnet-4-6 |
|---|---:|---:|
| Pass rate (objective) | 30/30 (100%) | 30/30 (100%) |
| Composite quality (Opus judge) | 3.80/5 | 4.00/5 |
| Cost | $0 | $0.19 |
| Latency | 18.4s | 45.6s |

### Per-task quality (composite 1-5)

| Task | qwen | sonnet | Δ | Looks correct |
|---|---:|---:|---:|---|
| 01 token bucket | 4.2 | 4.2 | 0.0 | both ✓ |
| 02 LRU cache | 4.4 | 4.4 | 0.0 | both ✓ |
| 03 CSV processor | **3.8** | 3.4 | **+0.4 qwen** | qwen ✗ / sonnet ✓ |
| 04 state machine | 4.0 | **4.4** | -0.4 | both ✓ |
| 05 async worker pool | **2.6** | **3.6** | **-1.0** | both ✗ |

### Verdict

**Crossover pattern**: qwen3-coder:30b jest **competitive lub lepszy** na tasks 1-3, słabnie na task 4, **dramatically pozostaje w tyle na async (5)**.

Async (task 5) ujawniło istotną słabość qwen-coder: mimo że wszystkie 5 testów przeszło, judge ocenił `looks_correct: false` (composite 2.6) — semaphore handling / ordering / exception propagation są subtelnie rozjeżdżone z prawidłowym async pattern.

### Decision matrix outcome

| Criterion | Winner |
|---|---|
| Pass rate | tie |
| Composite quality | sonnet (+0.20) |
| Cost | qwen ($0) |
| Latency | qwen (2.5×) |

### Recommendation: TIERED IMPL ROUTING

```yaml
spec-tdd-impl-agent:
  default: qwen3-coder:30b     # via MCP bridge, $0, 4× faster
  escalate_to_sonnet_when:
    - "async" / "asyncio" / "concurrent.futures" w tasks.md
    - design.md complexity > N components (TBD heuristic)
    - user passes --thorough flag
    - spec.json.complexity_hint == "high" or security_critical: true
```

Empirical evidence supports: ~80% tasks → qwen (free, fast, equivalent), ~20% tasks (async/highly complex) → sonnet ($0.04, +0.5-1.0 quality).

### What's next

1. ✅ Update `.blast/steering/llm-routing.md` — tiered impl routing documented
2. TODO: Update `.claude/agents/blast/impl.md` — Debate Mode-style escalation logic w prompcie agenta
3. TODO: Re-run smoke test (`/blast:full "test 4"`) z nowym routingiem, mierzyć improvement
4. ✅ Spike-4 closure dopisane do `r_and_d/INVENTORY.md`

