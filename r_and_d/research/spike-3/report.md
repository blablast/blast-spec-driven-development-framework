# spike-3 — scoring report

- Snippets: 5
- Total planted bugs: 18
- Result rows: 30

## Aggregate per-arm scores

| Arm | TP | FP | FN | Recall | Precision | F1 | Cost ($) | Avg latency (s) | Runs | Errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **CONTROL** | 16 | 12 | 2 | 0.89 | 0.57 | 0.70 | $0.4767 | 44.6 | 5 | 0 |
| **HYBRID** | 17 | 21 | 1 | 0.94 | 0.45 | 0.61 | $0.6094 | 129.5 | 5 | 0 |
| **JURY_3** | 17 | 24 | 1 | 0.94 | 0.41 | 0.58 | $0.9062 | 156.2 | 5 | 0 |
| **JURY_3_FLASH3** | 17 | 13 | 1 | 0.94 | 0.57 | 0.71 | $0.8718 | 140.7 | 5 | 0 |
| **QWEN_SOLO** | 13 | 13 | 5 | 0.72 | 0.50 | 0.59 | $0.0000 | 48.5 | 5 | 0 |
| **SONNET_SOLO** | 16 | 18 | 2 | 0.89 | 0.47 | 0.62 | $0.3027 | 42.0 | 5 | 0 |

## Decision matrix

- Highest F1: **JURY_3_FLASH3** (0.71)
- HYBRID vs SONNET_SOLO recall delta: **+0.06** (cost ratio 2.01×)
- JURY_3 vs CONTROL recall delta: **+0.06** (cost ratio 1.90×)

## Per-snippet breakdown

| Arm | 01_cache.py | 02_auth_session.py | 03_worker_pool.py | 04_migration.py | 05_parser.py |
|---|---:|---:|---:|---:|---:|
| **CONTROL** | 2/3 (FP 3) | 4/4 (FP 3) | 3/4 (FP 1) | 4/4 (FP 4) | 3/3 (FP 1) |
| **HYBRID** | 3/3 (FP 9) | 4/4 (FP 5) | 3/4 (FP 2) | 4/4 (FP 3) | 3/3 (FP 2) |
| **JURY_3** | 3/3 (FP 4) | 4/4 (FP 2) | 3/4 (FP 4) | 4/4 (FP 4) | 3/3 (FP 10) |
| **JURY_3_FLASH3** | 3/3 (FP 2) | 4/4 (FP 4) | 3/4 (FP 1) | 4/4 (FP 2) | 3/3 (FP 4) |
| **QWEN_SOLO** | 3/3 (FP 5) | 4/4 (FP 3) | 3/4 (FP 1) | 3/4 (FP 4) | 0/3 (FP 0) |
| **SONNET_SOLO** | 2/3 (FP 7) | 4/4 (FP 7) | 3/4 (FP 2) | 4/4 (FP 2) | 3/3 (FP 0) |

## Missed bugs (false negatives) per arm

### CONTROL — missed 2 bugs
- `01_cache.py` :: `cache-wallclock-ttl` (low) — Uses time.time() (wall clock) for TTL, not time.monotonic(). NTP adjustments or manual clock changes can make entries ap
- `03_worker_pool.py` :: `wp-unbounded-queue` (medium) — queue.Queue() created with no maxsize. Producers can enqueue without backpressure -> OOM if workers can't keep up.

### HYBRID — missed 1 bugs
- `03_worker_pool.py` :: `wp-unbounded-queue` (medium) — queue.Queue() created with no maxsize. Producers can enqueue without backpressure -> OOM if workers can't keep up.

### JURY_3 — missed 1 bugs
- `03_worker_pool.py` :: `wp-unbounded-queue` (medium) — queue.Queue() created with no maxsize. Producers can enqueue without backpressure -> OOM if workers can't keep up.

### JURY_3_FLASH3 — missed 1 bugs
- `03_worker_pool.py` :: `wp-unbounded-queue` (medium) — queue.Queue() created with no maxsize. Producers can enqueue without backpressure -> OOM if workers can't keep up.

### QWEN_SOLO — missed 5 bugs
- `03_worker_pool.py` :: `wp-unbounded-queue` (medium) — queue.Queue() created with no maxsize. Producers can enqueue without backpressure -> OOM if workers can't keep up.
- `04_migration.py` :: `mig-n-plus-one` (medium) — backfill_tier executes one UPDATE per user. For N users that's N round-trips. Should batch with `UPDATE ... WHERE id IN 
- `05_parser.py` :: `parser-broad-except` (medium) — except Exception: pass on per-line parsing silently swallows all errors. Malformed config lines disappear without diagno
- `05_parser.py` :: `parser-silent-read-failure` (medium) — except Exception on Path(path).read_text() returns empty config silently if the file is missing, has bad permissions, or
- `05_parser.py` :: `parser-isdigit-negative` (medium) — value.isdigit() returns False for negative integers like '-5'. Negative ints fall through to the string branch and get s

### SONNET_SOLO — missed 2 bugs
- `01_cache.py` :: `cache-wallclock-ttl` (low) — Uses time.time() (wall clock) for TTL, not time.monotonic(). NTP adjustments or manual clock changes can make entries ap
- `03_worker_pool.py` :: `wp-unbounded-queue` (medium) — queue.Queue() created with no maxsize. Producers can enqueue without backpressure -> OOM if workers can't keep up.


## Unmatched findings per arm (potential false positives)

These are findings reported by the arm that did NOT match any planted bug. They may be:
- Real issues we didn't plant (bonus signal — not necessarily noise)
- Noise / over-report
- Bugs whose keywords need updating in ground_truth.json

### CONTROL — 12 unmatched findings
- `01_cache.py`: **No validation on `max_size` allows degenerate cache behavior** — If `max_size` is set to `0` or a negative value, the cache degrades silently. With `max_size=0`, every `put()` immediately evicts the entry just inserted (the `len > max_size` check is `1 > 0`). With 
- `01_cache.py`: **No validation on `ttl_seconds` allows instant expiration** — If `ttl_seconds` is set to `0` or a negative value, every `get()` will find `time.time() - ts > self._ttl` to be `True` and immediately delete the entry, making the cache useless. No error or warning 
- `01_cache.py`: **No metrics or logging for eviction, expiration, or cache hits/misses** — The cache provides no visibility into its behavior — no hit/miss counters, no eviction logging, no way to know the current size or expiration rate. For a component caching API responses, this makes it
- `02_auth_session.py`: **In-memory `SESSIONS` dict is not thread-safe** — The global `SESSIONS` dictionary is accessed from `create_session` and `verify_session` without synchronization. Under a multi-threaded WSGI server (e.g., gunicorn with thread workers), concurrent wri
- `02_auth_session.py`: **No input validation on `user_id` or `password`** — `create_session` and `hash_password` accept arbitrary strings without checking for empty, excessively long, or null-byte-containing values. An empty `user_id` would create a valid session for a meanin
- `02_auth_session.py`: **No logging of authentication events** — Neither successful logins nor failed attempts are logged. This makes it impossible to detect brute-force attacks, compromised accounts, or suspicious login patterns during incident response or forensi
- `03_worker_pool.py`: **`fn.__name__` may not exist or may be unhelpful** — The code accesses `fn.__name__` to tag results. Lambdas all share the name `<lambda>`, `functools.partial` objects have no `__name__` (raises `AttributeError`), and arbitrary callables (classes with `
- `04_migration.py`: **No logging or progress reporting for long-running migration** — For a large table, this migration could run for minutes or hours with no output. Operators have no way to know whether it is making progress, stuck, or has silently failed. The return value is only av
- `04_migration.py`: **Connection not closed if `sqlite3.connect()` succeeds but `get_unbackfilled_ids`** — While the `finally` block does close the connection, the generator `get_unbackfilled_ids` holds a reference to `conn` and may have an open cursor. If the generator is not fully consumed (e.g., due to 
- `04_migration.py`: **`backfill_tier` hardcodes `'free'` with no conditional logic** — Every backfilled user is assigned `tier = 'free'` regardless of any other data (e.g., payment history, account age). If some existing users should have a different tier, this migration will incorrectl
- `04_migration.py`: **`fetchall()` loads entire batch into memory before filtering** — `cur.fetchall()` materializes all matching rows for a window into a list, then builds a second list of IDs. For a window of 500, this is small, but if `BATCH_SIZE` were increased significantly, memory
- `05_parser.py`: **Bare `partition(":")` breaks values containing colons** — `str.partition(":")` splits on the first colon only, but the value portion is simply `value.strip()`. If a value itself contains colons (e.g., `url: http://example.com:8080`), only the text after the 

### HYBRID — 21 unmatched findings
- `01_cache.py`: **`put` evicts entries spuriously during concurrent overwrites** — When `put` is called with an existing key at max capacity, the assignment overwrites the value without growing the store size. However, with concurrent puts racing in, the combined effect can cause sp
- `01_cache.py`: **`get` does not update LRU order when deleting expired entries** — When `put` inserts a new entry exceeding `max_size`, `popitem(last=False)` correctly evicts the LRU item. However, `get` silently deletes expired entries without updating LRU ordering, potentially lea
- `01_cache.py`: **Zero or negative `max_size` causes perpetual cache emptiness** — If `max_size <= 0`, every `put` call will immediately evict the entry it just inserted (since `len > 0` is immediately true), leaving the cache permanently empty. There is no validation in `__init__`.
- `01_cache.py`: **Negative or zero `ttl_seconds` makes all entries immediately expired** — A `ttl_seconds` of `0` or negative means `time.time() - ts > self._ttl` is always true immediately after insertion, so every `get` will return `None` and delete the entry, wasting CPU cycles on consta
- `01_cache.py`: **Expired entries accumulate and bypass `max_size` capacity limit** — TTL validation only occurs lazily on `get`. If a key is never accessed again after expiry, the stale entry remains in `_store` indefinitely and counts against `max_size`, potentially evicting live ent
- `01_cache.py`: **No cache hit/miss/eviction metrics or logging** — For a cache serving API responses, there is no instrumentation for hit rate, miss rate, TTL evictions, LRU evictions, or current size. Without this, diagnosing cache effectiveness, capacity planning, 
- `01_cache.py`: **Absolute TTL does not refresh on cache hits** — The `get` method updates the LRU order on successful hits but does not reset the entry's timestamp. This results in absolute expiration rather than sliding TTL, which may not match expected API cachin
- `01_cache.py`: **`get` returns `None` ambiguously for missing vs. expired entries** — Both a cache miss and a TTL expiry return `None`, making it impossible for the caller to distinguish between "key was never set" and "key existed but expired." This can lead to incorrect retry or fall
- `01_cache.py`: **Unbounded object storage enables memory exhaustion** — The cache stores arbitrary Python objects without size limits or type restrictions. Malicious or large payloads can be injected via `put`, enabling uncontrolled memory growth and potential denial of s
- `02_auth_session.py`: **Global mutable `SESSIONS` dict causes race conditions** — `SESSIONS` is a module-level dictionary accessed concurrently by multiple threads or processes. Simultaneous reads and writes are not protected by any lock. Python's GIL offers limited protection for 
- `02_auth_session.py`: **Session token entropy is minimal (128 bits) with no security margin** — `secrets.token_hex(16)` produces 128 bits, which is the absolute minimum recommended by NIST for session tokens. While currently adequate, this leaves no security margin if the RNG assumption is weake
- `02_auth_session.py`: **`login` function mixes authentication and session management** — The `login` function handles both credential verification and session creation, violating the single responsibility principle. This makes the function harder to test, reuse, and maintain, especially i
- `02_auth_session.py`: **`create_session` overwrites existing token on collision without notice** — If `token` collides with an existing key in `SESSIONS` (astronomically rare but theoretically possible), the existing user's session is silently overwritten. No collision detection or regeneration loo
- `02_auth_session.py`: **No logging of authentication events** — Neither successful logins nor failures are logged. This makes forensic analysis, anomaly detection, and audit trails impossible. Failed login attempts in particular are a key signal for detecting brut
- `03_worker_pool.py`: **`fn.__name__` raises `AttributeError` for lambdas and `functools.partial`** — Lambda objects have `__name__ == '<lambda>'` (acceptable but ambiguous), while `functools.partial` objects lack `__name__` entirely, causing an `AttributeError` that crashes the worker thread. This ha
- `03_worker_pool.py`: **Error results are indistinguishable from legitimate string return values** — When a job raises an exception, the result is stored as a plain string `"ERROR: <msg>"`. If a job legitimately returns a string beginning with `"ERROR: "`, the caller cannot tell success from failure,
- `04_migration.py`: **Niepotrzebne ładowanie wyników batch do pamięci za pomocą fetchall()** — `cur.fetchall()` materializuje wszystkie wiersze zapytania zakresu ID do listy Python przed yield, a następnie list comprehension ekstrahuje pierwszy element z każdego wiersza. Przy domyślnym `BATCH_S
- `04_migration.py`: **Brak walidacji ścieżki i pliku — niejawne tworzenie bazy danych** — `sqlite3.connect(db_path)` tworzy nowy pusty plik, jeśli ścieżka nie istnieje, a migracja nie powiedzie się lub zachowa się nieoczekiwanie na nowo utworzonej pustej bazie. Jeśli `db_path` pochodzi z d
- `04_migration.py`: **Brak logowania postępu lub wskazania statusu migracji** — Dla backfill mogącego dotknąć miliony wierszy, brak logowania postępu, szacunkowego czasu zakończenia czy błędów. Operator uruchamiający migrację nie ma widoczności czy działa, jest zawieszony czy pra
- `05_parser.py`: **Keys with only whitespace stored after stripping** — A line like `   : value` has `key = ""` after stripping, which the empty-key check (once added) would catch. But a line like `  \t  : value` also strips to `""`. Without the guard these produce `{"": 
- `05_parser.py`: **Boolean check is case-insensitive but float/int checks are not** — `value.lower() in ("true", "false")` handles `True`, `TRUE`, `tRuE`, etc. But there is no equivalent flexibility for integers or floats. This inconsistency may surprise users who expect uniform case h

### JURY_3 — 24 unmatched findings
- `01_cache.py`: **Missing Input Validation for Cache Parameters** — `__init__` accepts negative or zero values for `max_size` and `ttl_seconds` without validation. When `max_size <= 0`, the cache either refuses to store any entries or exhibits undefined behavior. When
- `01_cache.py`: **TTL Not Reset on Cache Access** — The `get()` method updates the LRU order via `move_to_end` when retrieving an entry, but does not update the stored timestamp. Entries expire based on creation time regardless of access frequency, whi
- `01_cache.py`: **No Metrics or Logging for Cache Behavior** — The cache provides no visibility into hit/miss rates, eviction counts, or expired-entry removal counts. Operators cannot tune `max_size` or `ttl_seconds` or debug cache issues without external instrum
- `01_cache.py`: **Loss of Type Information in Return Type** — `get()` returns `object | None`, providing no type safety. Callers must cast or assert on every retrieval, increasing runtime type error risk and reducing IDE autocomplete quality.
- `02_auth_session.py`: **No session invalidation or logout mechanism** — There is no function to revoke or delete a session token. Users cannot log out, and compromised tokens cannot be administratively invalidated or revoked, violating the principle of least privilege for
- `02_auth_session.py`: **Missing input validation for user_id and password** — The `login` and `create_session` functions do not validate that `user_id` or `password` are non-empty strings. Empty strings could create valid sessions mapped to empty user IDs, or an empty password 
- `03_worker_pool.py`: **Function names used as result keys cause collisions and ambiguity.** — Results are keyed by `fn.__name__`, which is not unique across different functions. Multiple jobs using the same function will overwrite previous results. Lambdas all share the name `<lambda>`, making
- `03_worker_pool.py`: **No mechanism to track when submitted work is complete.** — There is no way for callers to wait for a specific job's completion or know when all pending work has finished. The underlying `queue.Queue` supports `task_done()` / `join()` semantics, but neither is
- `03_worker_pool.py`: **Constructor does not validate `num_workers` parameter.** — The `__init__` method accepts zero or negative values for `num_workers` without validation. If `num_workers <= 0`, the pool creates no worker threads and becomes non-functional. Submitted jobs queue i
- `03_worker_pool.py`: **`fn.__name__` attribute access fails for some callable types.** — The code uses `fn.__name__` to tag results, but some callable types lack this attribute. `functools.partial` objects raise `AttributeError`, and callable classes may not define `__name__`. When this f
- `04_migration.py`: **Hardcoded tier value 'free' has no configurability or validation** — Every unbackfilled user is set to `'free'` regardless of business logic. If some users should receive a different tier based on payment history, creation date, or other flags, this migration silently 
- `04_migration.py`: **No logging of migration progress or completion** — The function returns a count but produces no log output. For a migration processing thousands or millions of rows, the operator has no visibility into progress, estimated time remaining, or which batc
- `04_migration.py`: **Connection creation has no error handling** — `sqlite3.connect(db_path)` can raise `sqlite3.OperationalError` if the path is invalid or permissions are insufficient. Additionally, no `journal_mode`, `timeout`, or `busy_handler` is configured, whi
- `04_migration.py`: **Affected row counts are ignored** — `conn.execute()` returns a cursor with a `rowcount` attribute, but the code discards it without checking. If a user ID is deleted between SELECT and UPDATE, or if the table schema changes, the update 
- `05_parser.py`: **Path traversal vulnerability — no validation on input paths** — Both `parse_config` and `merge_configs` accept arbitrary string paths without validation. A caller supplying user-controlled input could read arbitrary files on the filesystem (e.g., `../../etc/shadow
- `05_parser.py`: **Keys containing colons are mis-parsed in YAML-like nested syntax** — The parser splits on the first colon only using `partition(":")`. Keys with colons (e.g., YAML nested syntax `parent:child: value`) are mis-parsed with only the part before the first colon used as the
- `05_parser.py`: **Empty key after stripping is accepted** — A line like `: some_value` produces an empty-string key `""` in the resulting dict. This is almost certainly unintentional and could cause subtle downstream bugs when code looks up config values.
- `05_parser.py`: **String "none"/"null" not coerced to None** — YAML-like configs commonly use `none`, `null`, or `~` to represent null values. This parser stores them as literal strings, which may surprise callers who expect Python `None`.
- `05_parser.py`: **In-place mutation of base config in merge_configs** — `base.update(override)` mutates the `base` dictionary in place. Callers expecting a new merged dict will inadvertently modify the original object, causing unexpected side effects and hidden state chan
- `05_parser.py`: **Inline comments treated as part of values** — Lines like `key: value # comment` are parsed as `key` with value `value # comment` because the parser only strips leading/trailing whitespace, not inline comments. Inline comments corrupt the value da
- `05_parser.py`: **UTF-8 BOM corrupts first configuration key** — Files starting with a UTF-8 Byte Order Mark (`\ufeff`) cause the first key to retain the invisible BOM character, leading to mismatched keys during lookups. For example, `key: value` with BOM becomes 
- `05_parser.py`: **Misleading "YAML-like" claim with flat-only parsing** — The docstring claims YAML-like support, but the parser only handles flat key-value pairs. It lacks indentation handling, nested structures, lists, and multi-line strings.
- `05_parser.py`: **Unused line number enumeration wastes computation** — `enumerate(text.splitlines(), 1)` calculates line numbers that are never used in the loop body, wasting CPU cycles on every line processed.
- `05_parser.py`: **Boolean coercion misses common YAML true/false variants** — The parser only recognizes `true` and `false`, ignoring standard YAML boolean aliases like `yes`, `no`, `on`, and `off`.

### JURY_3_FLASH3 — 13 unmatched findings
- `01_cache.py`: **Missing validation of constructor parameters (max_size and ttl_seconds)** — The constructor does not validate `max_size` or `ttl_seconds`. If `max_size` is zero or negative, every `put()` inserts an entry then immediately evicts it, resulting in a permanently empty cache. If 
- `01_cache.py`: **get() returns direct reference to mutable cached objects** — The method returns the raw value from the cache without copying. If the cached object is mutable (list, dict, object), external code can modify it, and the cache has no way to track the change. This b
- `02_auth_session.py`: **No session invalidation or logout functionality** — The module provides no way to delete or revoke a session once created. Users cannot log out to invalidate their sessions, and administrators cannot revoke compromised tokens. This prevents proper sess
- `02_auth_session.py`: **In-memory session store is unsafe under concurrent access and multi-process depl** — The in-memory dictionary works only within a single process. In typical production deployments with multiple web worker processes (e.g., gunicorn with multiple workers) or async frameworks with concur
- `02_auth_session.py`: **Salt parameter is not validated for randomness or strength** — The `hash_password` function accepts a `salt` parameter without validating its format, length, randomness, or entropy. This allows callers to pass weak, predictable, or reused salts across multiple us
- `02_auth_session.py`: **No collision detection for generated session tokens** — The `create_session()` function generates tokens using `secrets.token_hex(16)` (128 bits), making collisions astronomically unlikely. However, the code does not check whether the generated token alrea
- `03_worker_pool.py`: **fn.__name__ access fails for lambdas, callables, and built-ins, crashing workers** — Results are labeled using `fn.__name__`, which fails for lambdas (they all share the name `<lambda>`, making results indistinguishable), `functools.partial` objects, callable class instances with `__c
- `04_migration.py`: **fetchall() loads entire batch into memory unnecessarily** — Using `fetchall()` on the cursor loads all matching rows for the current ID range into a Python list before processing. This defeats the purpose of streaming and can cause memory spikes on large datas
- `04_migration.py`: **Hardcoded tier value 'free' not validated against schema** — The tier value `'free'` is a magic string with no validation against allowed values. If the column has a CHECK constraint or an application-level enum, a typo here would silently insert invalid data.
- `05_parser.py`: **`merge_configs` performs only shallow merge** — The `base.update(override)` call completely overwrites nested dictionaries instead of merging them recursively. If configs contain nested structures, deeper values in the base config will be lost and 
- `05_parser.py`: **`merge_configs` mutates the base config dictionary in place** — The `base.update(override)` operation modifies the original `base` dictionary before returning it. Callers expecting an immutable or fresh dictionary may experience unexpected side effects if they reu
- `05_parser.py`: **Keys containing colons cause incorrect parsing** — If a key itself contains a colon (e.g., `urn:namespace: value`), the `partition(":")` call will split on the first colon, treating `urn` as the key and `namespace: value` as the value. This misinterpr
- `05_parser.py`: **Null/None values not supported** — YAML-like config formats commonly use keywords like `none`, `null`, or `~` to represent null/None values. This parser treats them as literal strings instead, which may surprise users expecting Python 

### QWEN_SOLO — 13 unmatched findings
- `01_cache.py`: **Unbounded growth when max_size is zero or negative** — The condition `if len(self._store) > self._max_size:` never triggers if `max_size <= 0`, causing the cache to grow without bound and eventually exhaust memory.
- `01_cache.py`: **Expired entries inflate cache size beyond max_size** — `put()` checks `len(self._store)` against `max_size`, but expired entries are only removed lazily in `get()`. The cache can grow indefinitely past `max_size` if new keys are inserted while old ones si
- `01_cache.py`: **Non-reentrant lock risks deadlock on nested calls** — `threading.Lock()` is not reentrant. If any method calls another method that also acquires the lock (e.g., `get()` calling `put()` or vice versa), it will deadlock.
- `01_cache.py`: **Redundant move_to_end() call in put()** — Assigning a value to an existing key in `OrderedDict` automatically moves it to the end in modern Python versions. The explicit call is unnecessary and adds minor overhead.
- `01_cache.py`: **Negative or zero TTL causes immediate expiration** — If `ttl_seconds` is passed as 0 or negative, `time.time() - ts > self._ttl` will immediately evaluate to True, causing all entries to be deleted upon retrieval.
- `02_auth_session.py`: **Global session dictionary lacks thread safety** — The SESSIONS dictionary is accessed concurrently by multiple threads without locks or atomic operations. Simultaneous session creation or verification can cause data corruption or lost updates.
- `02_auth_session.py`: **In-memory session storage prevents horizontal scaling** — The module uses a local dictionary for session storage, which isolates sessions to a single process. This breaks session continuity in load-balanced or distributed deployments.
- `02_auth_session.py`: **Missing logging for session lifecycle events** — The module performs authentication and session management without any logging or metrics. This makes it impossible to audit access attempts or detect brute-force attacks.
- `03_worker_pool.py`: **`fn.__name__` fails for lambdas and builtins** — Accessing `fn.__name__` raises an `AttributeError` for lambda functions, built-in functions, or callable objects that do not expose this attribute, causing the error handler to crash. This occurs beca
- `04_migration.py`: **Non-idempotent UPDATE overwrites existing tier values** — The UPDATE statement lacks a tier IS NULL condition. Running the migration a second time will overwrite existing valid tier assignments with 'free', corrupting user data.
- `04_migration.py`: **Returned total overcounts actual backfilled rows** — The function increments total for every ID fetched, ignoring whether the subsequent UPDATE actually modified a row. Concurrent deletions or race conditions cause the return value to be inaccurate.
- `04_migration.py`: **Silent failure on rows deleted between SELECT and UPDATE** — If a user is deleted after their ID is fetched but before the UPDATE executes, the operation fails silently. No logging or error handling alerts the caller to the discrepancy.
- `04_migration.py`: **Hardcoded batch size and connection handling lack flexibility** — BATCH_SIZE is hardcoded, and the connection is opened/closed manually without context managers or configurable parameters, reducing reusability and testability.

### SONNET_SOLO — 18 unmatched findings
- `01_cache.py`: **`put` does not overwrite TTL on existing key update** — When an existing key is updated via `put`, `move_to_end` is called after assignment, which is correct for LRU order, but the timestamp is refreshed correctly. However, if a key already exists, it is m
- `01_cache.py`: **TTL expiry uses `>` instead of `>=`, off-by-one at boundary** — `if time.time() - ts > self._ttl` means an entry whose age is exactly `ttl_seconds` is still considered valid. The TTL contract ("expire after N seconds") is violated at the exact boundary, which can 
- `01_cache.py`: **`put` does not check for expired entry before inserting** — When inserting a key that already exists but is expired, `put` overwrites the value correctly, but the old expired entry's slot is reused without any TTL-based eviction pass. The size check then runs,
- `01_cache.py`: **`max_size=0` causes infinite eviction loop or immediate eviction** — If `max_size` is set to `0`, every `put` call will trigger `popitem(last=False)` because `len(self._store) > 0` is immediately true after insertion. The item just inserted is evicted on every write, m
- `01_cache.py`: **Negative or zero `ttl_seconds` makes all entries immediately stale** — If `ttl_seconds <= 0`, every `get` call will evaluate `time.time() - ts > self._ttl` as `True` (since elapsed time is always non-negative), causing every entry to be evicted on read. This silently mak
- `01_cache.py`: **No cache hit/miss/eviction metrics or logging** — There is no instrumentation for hits, misses, TTL evictions, or LRU evictions. In a production API-response cache, the inability to observe cache effectiveness makes tuning, debugging, and detecting c
- `01_cache.py`: **`_store` key type not validated; non-string keys silently accepted** — The type annotation says `key: str`, but Python does not enforce annotations at runtime. A caller passing a non-string (e.g., `int`, `tuple`) will silently succeed, potentially causing subtle key-coll
- `02_auth_session.py`: **Unsynchronized read-write on shared `SESSIONS` dict** — `SESSIONS` is a module-level mutable dict accessed by `create_session` (write) and `verify_session` (read) from potentially multiple threads. In CPython the GIL protects individual bytecode operations
- `02_auth_session.py`: **Token entropy is only 128 bits — acceptable but no uniqueness check** — `secrets.token_hex(16)` produces 128 bits of entropy. While statistically unlikely, there is no collision check before inserting into `SESSIONS`. A collision silently overwrites the existing user's se
- `02_auth_session.py`: **Session not rotated after successful authentication** — `login` calls `create_session` which generates a new token, but if a pre-authentication session token existed (e.g., from an anonymous session), it is not invalidated. More broadly, the pattern does n
- `02_auth_session.py`: **`login` creates session before confirming `user_id` existence** — `login` assumes `user_id` is valid and authoritative — it only checks the password hash. There is no lookup of the actual user record; a caller could pass any `user_id` string paired with a matching `
- `02_auth_session.py`: **No logging on authentication failure or success** — Failed login attempts, successful authentications, and session creations produce no log output. This makes it impossible to detect brute-force attacks, audit access, or investigate incidents after the
- `02_auth_session.py`: **Empty or whitespace `password` and `salt` accepted silently** — `hash_password` does not reject empty strings. An empty password hashes to a fixed value, and an empty salt provides no randomness. A misconfigured caller passing `salt=""` or `password=""` will produ
- `02_auth_session.py`: **`SESSIONS` dict is module-level global — untestable and stateful** — Module-level mutable state makes unit testing difficult (tests bleed into each other), prevents horizontal scaling (state is per-process), and violates dependency injection principles. The comment ack
- `03_worker_pool.py`: **Workers silently exit on `AttributeError` when callable has no `__name__`** — `fn.__name__` is accessed unconditionally in both the success and error paths. Callables that are `functools.partial` objects, lambda wrappers returned by decorators, or instances of classes implement
- `03_worker_pool.py`: **No way to associate a result with a specific submitted job** — Results are stored keyed only by `fn.__name__`, which is non-unique. If the same function is submitted multiple times, results are indistinguishable. There is no job ID, no future/promise, and no call
- `04_migration.py`: **No progress logging or error reporting during long-running migration** — For large tables the migration runs silently. Operators have no way to gauge progress, detect stalls, or see which batch failed. A migration that hangs or errors mid-way is indistinguishable from one 
- `04_migration.py`: **Hardcoded `'free'` tier may be wrong for certain legacy users** — All `NULL`-tier users are unconditionally set to `'free'` regardless of their signup date, plan history, or any other attribute. If any existing users should receive a different default (e.g., grandfa
