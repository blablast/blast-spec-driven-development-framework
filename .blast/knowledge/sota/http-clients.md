# SOTA: Python HTTP clients (2026)

**Last refreshed**: 2026-05-07
**Refresh source**: web research + project experience
**Refresh cadence**: every 6 months OR when library deprecation announced

## Recommendation by use case

| Use case | SOTA choice (2026) | Alternative | Avoid |
|---|---|---|---|
| Sync HTTP client | `httpx` | `requests` (mature, stable, widely used) | `urllib3` (low-level), `urllib.request` (only for stdlib-only constraint) |
| Async HTTP client | `httpx` (async API) | `aiohttp` (mature, but split sync/async API less ergonomic) | `httplib2` (deprecated), `urllib3 async` (limited) |
| Streaming downloads | `httpx.stream()` | `requests` with `stream=True` | — |
| HTTP/2 support | `httpx` (built-in) | `hyper` (legacy) | — |
| Retry logic | `tenacity` (decorator-based) | `httpx` with `transport.HTTPTransport(retries=N)` (basic only) | manual exponential backoff for new code |

## Why httpx > aiohttp for new async projects (2026)

- Single API for sync + async (same `Client` / `AsyncClient` shape)
- Built-in HTTP/2 support
- More idiomatic with modern Python (typing, context managers)
- Active maintenance (encode org, used by FastAPI ecosystem)
- aiohttp still solid choice for legacy/existing codebases

## When aiohttp is OK to choose

- Existing codebase already uses aiohttp (consistency > swap)
- Need WebSocket + HTTP in single library (aiohttp has both)
- Specific feature parity already proven for the use case

## Anti-patterns to flag

- `requests` in async code (blocks event loop) → use `httpx.AsyncClient`
- Manual retry loops with `time.sleep` → use `tenacity` or `httpx.Transport(retries=N)`
- Custom connection pooling → use library's built-in (httpx.AsyncClient handles it)
- Hardcoded timeouts → use `httpx.Timeout` per-call configuration

## References

- httpx docs: https://www.python-httpx.org/
- httpx vs aiohttp comparison: https://github.com/encode/httpx/discussions
- tenacity: https://tenacity.readthedocs.io/
