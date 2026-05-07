# SOTA Knowledge Base

Curated state-of-the-art recommendations per technology area. Read by `validate-tasks-agent` (Pragmatist) before suggesting library / pattern alternatives.

## Files

- `http-clients.md` — Python HTTP libraries (httpx, requests, aiohttp)
- `async-patterns.md` — asyncio idioms, TaskGroup, Semaphore, backpressure
- (add more as needed: orm.md, testing.md, web-frameworks.md, ...)

## Lookup discipline (for validate-tasks agent)

1. Read all `.md` files in this dir on validate-tasks invocation
2. Trust if `**Last refreshed**` < 6 months ago
3. If 6-12 months old: use as starting point, WebSearch to verify
4. If > 12 months: stale, prefer WebSearch + flag refresh as TODO

## Refresh cadence

Manual refresh via `/blast:learn --refresh-sota` (when implemented) OR edit per-file as new info arrives.

Recommended: review entire `sota/` quarterly. Library landscape moves fast — what was best 6 months ago may already be deprecated.

## Adding new files

When `validate-tasks` agent encounters a tech area NOT covered:
1. Performs WebSearch
2. Logs finding as INFO with "consider adding sota/{topic}.md"
3. User adds curated file based on research

Format: see existing files. Required headers: `**Last refreshed**`, recommendation tables, anti-patterns, references.
