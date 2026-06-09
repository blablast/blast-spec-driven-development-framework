# Spike-4 baseline (2026-05-07) — qwen3-coder:30b [STALE]

Archived from `.claude/agents/blast/impl.md` (2026-06-09) — historical context only,
moved out of the agent prompt to stop paying its tokens on every impl invocation.

> ⚠ The numbers below were measured on `qwen3-coder:30b`, the OLD code primary. The current
> primary is `qwen3-coder` (current generation, 17.3G). The async
> weakness recorded here is a property of the old model, NOT the current one. **Do not use these
> numbers to justify async→Sonnet escalation.** Re-run Spike-4 on the new model via
> `/blast:learn --routing` before trusting any threshold.

- Simple tasks (rate limiter, LRU cache, CSV processor): qwen3-coder:30b 100% pass, composite 4.0/5
- Complex sync (state machine): qwen3-coder:30b 100% pass, composite 4.0/5
- Async (worker pool): qwen3-coder:30b 100% pass BUT composite 2.6/5, looks_correct: false

→ Old conclusion (superseded): "never delegate on async" applied to qwen3-coder:30b only.
→ Current stance: delegate async to the current qwen3-coder primary; escalate only on demonstrated red tests.
