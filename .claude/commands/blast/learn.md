---
description: "Self-improvement aggregator — lessons / cost calibration / routing observability"
allowed-tools: Bash, Read, Write, Edit
argument-hint: [--lessons | --calibrate | --routing | --all] [--apply]
---

# blast:learn — Self-improvement aggregator

Three feedback-loop tools in one command:

- **`--lessons`** — collect retrospections from shipped specs → digest → input for `/blast:steering`
- **`--calibrate`** — compute p25/p50/p75/p95 from `agent-runs.jsonl` → suggest `cost-policy.md` updates
- **`--routing`** — verdict distribution per subagent → flag anomalies (high FAIL rate, error rate)
- **`--all`** — run all three

Read-only by default. Pass `--apply` to write `lessons.md` to `.blast/steering/`.

## Execution

```bash
python .claude/scripts/blast-learn.py {ARGUMENTS}
```

## When to run

- After every 5+ shipped specs (lessons aggregator value rises with sample size)
- After 1-2 months of usage (calibrator needs telemetry samples)
- Routing observability: anytime — surfaces issues even from few samples

Auto-trigger: `/blast:complete` invokes `--all` every 5 shipped specs (counter in `.blast/.session-state/learn-counter.json`).
