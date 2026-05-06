# TRACE — Order Processing Platform

Append-only structured log. Cross-project decisions, locks, kills, pivots. Newest at top.

> Full session narrative: [`PROGRESS.md`](PROGRESS.md). Future plan: [`ROADMAP.md`](ROADMAP.md). Decisions in detail: [`docs/adr/`](docs/adr/).

Types: `DECISION` | `EVENT` | `MILESTONE` | `KILL` | `PIVOT` | `LOCK` | `BLOCKER`

---

## 2026-05-05 — EVENT — Project hygiene aligned to vault standard

Added `ROADMAP.md` (Now / Next / Later / Won't do) and this `TRACE.md` to comply with the project structure standard: README + docs/ + ADRs + ROADMAP + TRACE.

Existing artifacts kept as-is:
- `README.md` — project spec.
- `docs/adr/ADR-001-api-versioning.md` — `/v1/` URL prefix over header negotiation.
- `docs/adr/ADR-002-cursor-pagination.md` — cursor over offset, signed token format.
- `docs/adr/ADR-003-postgresql-over-mongodb.md` — Postgres for relational invariants.
- `docs/adr/ADR-004-caching-and-rate-limiting.md` — read-through cache + token bucket via Redis Lua.
- `PROGRESS.md` — session-by-session narrative log, kept as the rich log.

This file is the structured cross-reference layer.

## 2026-04-18 — MILESTONE — Day 3.5: integration CI green 10/10

Three independent root causes fixed:
1. `pytest-asyncio` auto mode + pooled asyncpg connections across event loops → switched to `NullPool` + per-test engine.
2. `MissingGreenlet` on `OrderRead` serialization → `selectinload(Order.items)` in `get`, `get_by_idempotency_key`, `list_page`.
3. `MissingGreenlet` on `updated_at` after status update → explicit `session.refresh(order, attribute_names=["updated_at"])` in `update_status`.

Locked decisions:
- `LOCK` Integration tests do not share a connection pool across tests. `NullPool` is the default for any async DB test suite in this repo.
- `LOCK` Every endpoint returning an ORM row must either use eager-loaded queries or refresh touched columns before serialization.
- `LOCK` `ruff format` runs in CI and fails the build.

Full narrative: `PROGRESS.md` 2026-04-18 Day 3.5.

## 2026-04-18 — DECISION — ADR-004 caching + rate limiting

Read-through cache + explicit invalidation. Token bucket over Redis with atomic Lua `EVAL`. Limiter fails *open* (Redis outage does not become an API outage; correctness floor is the DB unique constraint).

Reference: `docs/adr/ADR-004-caching-and-rate-limiting.md`.

## 2026-04-18 — DECISION — Idempotency two layers

Redis (fast path, `SET NX EX 86400` on SHA-256 of body) + DB unique constraint (correctness floor). Race fallback reads the cached mapping; no double-charge path exists.

## 2026-04-18 — DECISION — Order items as snapshots

`sku`, `name`, `unit_price`, `currency`, `total_amount` denormalized onto order items at purchase time. Prevents historical orders from drifting if the product catalog changes. Caught at schema-design time.

## 2026-04-18 — DECISION — Status transitions as data graph

`_TRANSITIONS` graph in code, testable as data, not scattered as `if`s. Invariant: terminal states (`delivered`, `cancelled`) have zero outgoing edges, asserted in tests.

## 2026-04-18 — MILESTONE — Day 2: full CRUD wired with idempotency, cursor pagination, status state machine

19 unit tests green. CI green (ruff + pytest unit + Docker build). Endpoints: `POST` (idempotent), `GET` list (cursor), `GET /{id}`, `PUT /{id}/status`, `DELETE /{id}`.

Full narrative: `PROGRESS.md` 2026-04-18 Day 2.

## 2026-04-18 — DECISION — ADR-001 / ADR-002 / ADR-003

- `ADR-001` URL versioning over headers — explicit, cache-friendly, debuggable.
- `ADR-002` Cursor over offset — stable under inserts, no O(N) scan past page N, deterministic.
- `ADR-003` PostgreSQL over MongoDB — relational invariants (idempotency uniqueness, status FSM, foreign keys) outweigh schema flexibility for this domain.

References under `docs/adr/`.

## 2026-04-18 — EVENT — Project bootstrap

Initial scaffold: FastAPI + SQLAlchemy 2 async + Alembic + Redis + Postgres in Docker Compose. Public from day 1 on `jotive/order-processing-platform`.
