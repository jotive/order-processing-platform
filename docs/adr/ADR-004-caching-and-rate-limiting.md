# ADR-004: Redis as cache + rate limiter

**Status:** Accepted
**Date:** 2026-04-18
**Deciders:** jotive.dev

## Context

The API has two cross-cutting concerns that share an infrastructure answer:

1. **Read amplification** on hot orders. `GET /orders/{id}` is the most-called endpoint (retail partners poll for status changes). Without caching, every call hits Postgres — wasteful for data that changes on human-scale intervals (seconds to minutes).
2. **Abuse and accidental DoS**. A public API with partner integrations will see misbehaving clients: a stuck retry loop or a bad cron pattern can push per-client QPS into the thousands. Postgres will not fail gracefully under that load.

Both problems have the same shape: we need a fast, shared, expiring key-value store. Redis is already in the stack (idempotency, ADR pending for keys).

The open question is not *whether* to use Redis, but **how** — specifically:
- What caching pattern (read-through vs write-through vs cache-aside)?
- What rate limiting algorithm (token bucket vs leaky bucket vs fixed window)?
- How do we keep the cache from serving stale data after a mutation?

## Decision

### Caching

**Cache-aside with explicit invalidation on mutation.**

- `GET /orders/{id}` checks Redis first (`order:{id}`, TTL 5 minutes). On miss, reads Postgres, populates cache, returns.
- Any mutation (`POST`, `PUT .../status`, `DELETE`) explicitly deletes the cache key *after* the DB commit succeeds. Readers that arrive during the invalidation window pay one cache miss; no path serves stale data after a successful write.
- List endpoints (`GET /orders`) are **not** cached. Cursor pages are parameterized by cursor + filters + size — too many permutations to cache usefully, and the query itself is already O(log n) via the compound index.

### Rate limiting

**Token bucket, per client, atomic in Redis via Lua.**

- Default: 100 requests per minute per API client, burst capacity 150.
- Key shape: `rl:{client_id}`. Lua script reads `(tokens, last_refill)`, refills based on elapsed time, decrements by 1 if `tokens >= 1`, writes back. Entire operation is atomic — no race between concurrent requests from the same client.
- On deny: respond `429 Too Many Requests` with RFC 6585 semantics + `Retry-After` header.
- Client identity: for now, bucket by source IP (FastAPI `request.client.host`). When auth lands, switch to authenticated principal.

## Alternatives considered

### Caching pattern

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| **Cache-aside + invalidate-on-write** | Simple to reason about. Invalidation tied to the write path = no background job needed. Bounded staleness = zero after commit. | Cache miss stampede possible if a hot key expires under load. Mitigated via `redis.set(..., nx=True)` or singleflight. | **Chosen** — matches the mutation cadence of orders (writes are moments, reads are polls). |
| **Write-through** | Writer populates cache on every write. Readers always hit cache. | Writer pays the cache-populate cost even when the key isn't hot. Couples write path to cache availability — if Redis is down, writes fail. | Rejected — couples reliability of the write path to an optional component. |
| **Write-behind / write-back** | Decouples cache from DB, batches writes. | Data loss if cache dies before flushing. Wrong tier of semantics for an order system. | Rejected — unsafe for orders. |
| **TTL-only (no explicit invalidation)** | Dead-simple. Tolerable staleness window. | After a status update, clients can see stale data for up to TTL. For orders (which drive dashboards), that is visible. | Rejected — staleness after commit is a correctness defect for this domain. |

### Rate limit algorithm

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| **Token bucket** | Allows bursts (up to bucket capacity) while enforcing an average rate. Trivial to tune (rate + burst). Industry standard. | Requires atomicity — naïve `GET/SET` is racy. Solved via Lua `EVAL`. | **Chosen** — matches real API traffic shape (idle + burst). |
| **Leaky bucket** | Smooth output rate. Naturally paces downstream. | No burst allowance — rejects legitimate spiky traffic (e.g., a client catching up after a brief partition). | Rejected — too strict for partner integrations. |
| **Fixed window counter** | Simplest possible. `INCR` + `EXPIRE` per window. | Edge effect: a client can issue 2× the limit across a window boundary (50 just before `:00`, 50 just after). Observable abuse vector. | Rejected — correctness bug for a public API. |
| **Sliding window log** | Exact. No edge effects. | Stores one entry per request. At 100 RPM × 10k clients = 1M entries kept in Redis. Expensive. | Rejected — correctness wins at too high a memory cost. |
| **Sliding window counter** | Good approximation of sliding log at fixed-window memory cost. | More complex to implement correctly. | Deferred — token bucket is enough for current scale. |

## Consequences

### Positive

- Postgres is protected by two layers: cache absorbs reads, rate limiter absorbs abuse. Each layer can fail open (cache miss → DB read; rate limiter unreachable → permit and log) without cascading outage.
- Invalidation lives in the repository/service layer next to the mutation — one file to read to understand the complete read path.
- Token bucket is tunable per route or per tenant later without code changes (keys already parameterized).
- Lua script guarantees atomic bucket updates even under concurrent requests from the same client — no race-derived over-permitting.

### Negative

- One more round trip on the read path (Redis first, then Postgres on miss). Acceptable — Redis RTT is sub-millisecond on a local network.
- Cache invalidation bugs are notoriously silent. Mitigation: integration test that (a) reads, (b) mutates, (c) reads again and asserts fresh data.
- Rate limiter failure mode needs an explicit policy: **fail open** (log + allow) rather than fail closed. Closed means Redis outage = API outage, which is a worse trade than a brief permissive window.

### Follow-ups

- Implement `app/core/cache.py` with `OrderCache.get / set / invalidate` wrapping `redis.asyncio`.
- Implement `app/core/rate_limit.py` with Lua script registered once at startup. Register FastAPI middleware.
- Add integration test: mutate order, assert `GET /{id}` returns new state immediately.
- Document the `Retry-After` contract in OpenAPI responses for 429.
