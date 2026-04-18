# Progress Log

> Live log of what's shipped, what's next, and why. One entry per working session. Newest on top.

## 2026-04-18 · Day 2 — Endpoints wired end-to-end

**Shipped:**
- Schema ↔ ORM alignment: orders carry `sku`/`name`/`unit_price`/`currency`/`total_amount` — items are snapshots at purchase time, not live references (prevents historical orders from drifting if product catalog changes).
- `app/core/pagination.py`: versioned cursor codec (`v1:<urlsafe-b64-json>`) over `(created_at, id)`. Decode rejects malformed tokens and unknown versions.
- `app/services/order_repository.py`: repository pattern. Create flushes atomically and surfaces idempotency collisions as `OrderConflict`. List uses keyset filter (`created_at < cursor.created_at OR (=, id < cursor.id)`), fetches `size+1` to compute `next_cursor`. Status transitions enforced by explicit `_TRANSITIONS` graph.
- `app/db/redis.py`: `IdempotencyStore` with SHA-256 of request body + `SET NX EX 86400`. Same key + same payload returns cached order; same key + different payload is 409.
- `app/api/v1/dependencies.py`: `AsyncSession` commit/rollback wrapper, Redis singleton, repo injection.
- Endpoints wired: `POST` (idempotent with race-safe fallback), `GET` list (cursor), `GET /{id}`, `PUT /{id}/status`, `DELETE /{id}`.
- Tests: 19 unit tests green — cursor roundtrip + malformed-token rejection, status transition matrix (10 parametrized cases + terminal-state invariant), idempotency hash stability.
- CI: GitHub Actions — ruff check + ruff format + pytest unit + Docker build (cached via `type=gha`).

**Decisions locked:**
- Order items are **snapshots**, not references. Caught at schema-design time before it became a data migration.
- Status transitions live in a dedicated graph (`_TRANSITIONS`) — testable as data, not scattered as `if`s across the repo. Invariant: terminal states (`delivered`, `cancelled`) have zero outgoing edges, asserted in tests.
- Idempotency is enforced at two layers: Redis (fast path) + DB unique constraint (correctness floor). Race between cache-check and insert falls back to reading the cached mapping — no double-charge path exists.

**Not yet:**
- Integration tests against real Postgres (testcontainers or compose fixture).
- Redis rate limiting (token bucket) — ADR-004 pending.
- Read-through cache on `GET /{id}` — ADR-004 pending.
- Observability: structured logs, Prometheus counters, OTel tracing.
- Secret rotation in Docker/compose for prod.

**Next session:**
1. ADR-004: caching + rate limiting strategy.
2. Token bucket rate limiter middleware over Redis.
3. Integration test suite against compose-provided Postgres.
4. Structured JSON logging middleware (correlation IDs).

---

## 2026-04-18 · Day 1 — Scaffolding + design decisions

**Shipped:**
- Repo bootstrapped: `pyproject.toml` (Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 async, asyncpg, Alembic, Redis), `README.md`, project layout (`app/{api/v1,core,db,models,schemas,services}`, `tests/{unit,integration}`, `docs/adr`).
- FastAPI scaffold: `app/main.py` with RFC 7807 Problem Details exception handlers (`StarletteHTTPException` + `RequestValidationError`), `/health` liveness probe, versioned router under `/api/v1`.
- Pydantic schemas: `OrderCreate`, `OrderRead`, `OrderStatusUpdate`, `PaginatedOrders`, `ProblemDetail`, status enum.
- Five endpoint stubs documented in OpenAPI: `POST /orders` (idempotent), `GET /orders` (cursor paginated), `GET /orders/{id}`, `PUT /orders/{id}/status`, `DELETE /orders/{id}`. All return 501 until Bloque next.
- Persistence layer: SQLAlchemy 2.0 async engine + session factory, `Order` + `OrderItem` ORM with UUID PKs, FK cascade delete, check constraints (status enum, non-negative amounts), unique constraint on idempotency key, compound index `(created_at, id)`.
- Alembic wired (async env) + baseline migration `0001_initial_orders_schema.py`.
- Docker stack: multi-stage `Dockerfile` (builder + slim runtime, non-root user, healthcheck), `docker-compose.yml` with Postgres 16 + Redis 7 + healthchecks + named volumes, `Makefile` shortcuts.
- Three ADRs accepted: ADR-001 (API versioning via URL path), ADR-002 (cursor-based pagination on `(created_at, id)`), ADR-003 (PostgreSQL over MongoDB).
- LRU Cache writeup in English — approach, complexity, mapping to Redis eviction policy.

**Decisions locked:**
- URL path versioning over header/query — discoverability wins over HATEOAS purism.
- Cursor pagination over offset — O(1) page depth + stability under concurrent inserts.
- PostgreSQL over MongoDB — order data is intrinsically relational; correctness lives in the DB, not the app.

**Not yet:**
- Endpoint bodies (wire SQLAlchemy repositories + idempotency logic).
- Redis integration (idempotency key store + read-through cache).
- CI (GitHub Actions: lint + mypy + pytest).
- Integration tests against real Postgres (testcontainers or compose fixture).
- Rate limiting (token bucket in Redis) — ADR-004 pending.
- Caching strategy writeup — ADR-004 pending.
- Testing pyramid scope — ADR-005 pending.

**Next session:**
1. Implement `POST /orders` end-to-end: repository pattern, idempotency via unique constraint, transactional insert of order + items.
2. Implement `GET /orders` with cursor encoding utility (`app/core/pagination.py`, version-prefixed base64).
3. Wire integration test: paginate 1,000 seeded orders, assert no duplicates/gaps.

---

## 2026-04-18 · Day 0 — Track reframe

- Career track 1 repriced as #1 priority: **Senior Python Engineer** positioning, not "exit DN."
- Target: "Top 5% Senior Python LATAM hispano" as measurable identity — 2+ public repos with ADRs, 12+ blog posts, 3+ inbound recruiters/month by Q4 2026.
- Portfolio home: `github.com/jotive` under `jotive.dev` submarca. Kept separate from GeosData (products lab).
- Tools inventoried: Canva Pro, Adobe CC, Hostinger, dev.jotive.com.co (Astro), LinkedIn, GitHub, Instagram `@jotive.dev`.
