# Progress Log

> Live log of what's shipped, what's next, and why. One entry per working session. Newest on top.

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
