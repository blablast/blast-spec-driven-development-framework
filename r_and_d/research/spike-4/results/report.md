# Spike-4 — qwen3-coder vs claude-sonnet-4-6 (head-to-head)

## Aggregate per arm

| Arm | Tasks | Pass rate | Composite quality (judge) | Total cost | Total latency |
|---|---:|---:|---:|---:|---:|
| **qwen** | 5 | 30/30 (100%) | 3.80/5 | $0.0000 | 18.4s |
| **sonnet** | 5 | 30/30 (100%) | 4.00/5 | $0.1884 | 45.6s |

## Per-task breakdown

| Task | Arm | Tests pass | Latency | Cost | Idiom | Sec | Perf | Read | Comp | Composite | Looks correct |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| 01_token_bucket | qwen | 5/5 | 3.9s | $0.0000 | 5 | 3 | 5 | 5 | 3 | 4.2 | ✓ |
| 01_token_bucket | sonnet | 5/5 | 6.6s | $0.0330 | 5 | 3 | 5 | 5 | 3 | 4.2 | ✓ |
| 02_lru_cache_ttl | qwen | 6/6 | 3.7s | $0.0000 | 5 | 4 | 4 | 5 | 4 | 4.4 | ✓ |
| 02_lru_cache_ttl | sonnet | 6/6 | 8.0s | $0.0383 | 5 | 4 | 4 | 5 | 4 | 4.4 | ✓ |
| 03_csv_processor | qwen | 6/6 | 5.9s | $0.0000 | 4 | 4 | 4 | 4 | 3 | 3.8 | ✗ |
| 03_csv_processor | sonnet | 6/6 | 16.5s | $0.0454 | 3 | 4 | 3 | 3 | 4 | 3.4 | ✓ |
| 04_state_machine | qwen | 8/8 | 1.9s | $0.0000 | 4 | 3 | 5 | 5 | 3 | 4.0 | ✓ |
| 04_state_machine | sonnet | 8/8 | 6.4s | $0.0351 | 5 | 4 | 5 | 5 | 3 | 4.4 | ✓ |
| 05_async_worker_pool | qwen | 5/5 | 3.0s | $0.0000 | 3 | 2 | 3 | 3 | 2 | 2.6 | ✗ |
| 05_async_worker_pool | sonnet | 5/5 | 8.2s | $0.0367 | 4 | 3 | 4 | 4 | 3 | 3.6 | ✗ |

## Verdict

### Pass rate: qwen 100% vs sonnet 100%
Tied.

### Composite quality (judge): qwen 3.80/5 vs sonnet 4.00/5
**sonnet** wygrywa o 0.20 pkt.

### Cost premium: qwen $0.0000 vs sonnet $0.1884
Free arm: qwen

### Latency: qwen 18.4s vs sonnet 45.6s
**qwen** szybszy o 27.2s.

### Decision matrix

| Criterion | Winner |
|---|---|
| Pass rate | tie |
| Composite quality | sonnet |
| Cost ($) | qwen |
| Latency | qwen |