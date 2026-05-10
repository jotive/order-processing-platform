# Order Processing Platform

> Part of the [jotive.dev](https://dev.jotive.com.co) technical portfolio — Backend Engineer · Python · Node.js

Production-grade order processing backend. Not a CRUD exercise: each architectural decision is justified with trade-offs and documented as an Architecture Decision Record (ADR).

---

## The Problem

**Camila** is CTO at a Colombian e-commerce company. $500k MRR, 8 engineers, peaks during Black Friday.

Every Black Friday, 3–5% of orders duplicate. Customers reload the page while a payment is processing — the charge goes through twice. Her support team spends the following Monday manually issuing refunds. The payment processor charges the same fee regardless. Each campaign that drives more traffic also drives more duplicate charges.

The naive fix is a database unique constraint. That alone fails under concurrent requests: two requests hit the constraint check simultaneously, both pass, both insert. The real fix is a dual-layer approach — atomic Redis check before the DB write, plus the constraint as a safety net.

**This project demonstrates that fix running in production-like conditions.**

---

## What this solves

- Zero duplicate orders regardless of client retries, network glitches, or double-clicks
- Rate limiting that doesn't allow bursts to bypass the counter (Lua-atomic token bucket)
- Read path that doesn't hit Postgres on every request (cache-aside with event-based invalidation)
- Error responses that tell the client exactly what went wrong and how to recover (RFC 7807)

---

## What this demonstrates

- **Idempotency:** Dual-layer (Redis atomic check + DB unique constraint) — not just one or the other
- **Rate limiting:** Token bucket implemented in Lua, executed atomically inside Redis
- **API Design:** REST with cursor pagination, RFC 7807 errors, versioning strategy
- **SQL Modeling:** Schema for transactional integrity, indexes for real query patterns, Alembic migrations
- **Caching:** Read-through and cache-aside strategies, TTL and event-based invalidation
- **Observability:** Structured JSON logging with correlation IDs, Prometheus metrics, OpenTelemetry-ready
- **Testing:** Unit, integration, and end-to-end layers with clear separation
- **Delivery:** Docker multi-stage builds, CI/CD with GitHub Actions

---

## Stack

**Backend:** Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2.0
**Database:** PostgreSQL 16 · Alembic migrations
**Cache:** Redis 7
**Runtime:** Docker · docker-compose
**CI/CD:** GitHub Actions · ruff · pytest · coverage

---

## Architecture

```mermaid
flowchart LR
    Client([Client]) -->|HTTPS/JSON| RL[Rate Limiter<br/>Token bucket · Lua]
    RL --> API[FastAPI<br/>/api/v1]
    API -->|SQLAlchemy 2.0 async| PG[(PostgreSQL 16<br/>orders + order_items)]
    API -->|cache-aside · TTL 5min| Cache[(Redis 7)]
    RL -.atomic counters.-> Cache
    API -->|structured logs| Logs[(stdout → collector)]
    PG -->|migrations| Alembic[Alembic]

    classDef store fill:#0b5,stroke:#062,color:#fff
    classDef infra fill:#248,stroke:#124,color:#fff
    class PG,Cache store
    class RL,Alembic infra
```

**Request flow:**

1. Rate limiter (Redis token bucket, Lua-atomic) permits or rejects with `429 + Retry-After`.
2. Handler validates + enforces idempotency via `Idempotency-Key` header + unique DB constraint.
3. Read path: cache-aside on `order:{id}`, miss falls back to Postgres.
4. Write path: transactional DB update → cache invalidation *after* commit → 200/201 response.

See [`/docs/adr/`](./docs/adr/) for the trade-off analysis behind each of these choices.

---

## Architecture Decision Records

All non-trivial decisions live in [`/docs/adr/`](./docs/adr/).

| ADR | Decision | Status |
|---|---|---|
| [001](./docs/adr/ADR-001-api-versioning.md) | API versioning via URL path | Accepted |
| [002](./docs/adr/ADR-002-cursor-pagination.md) | Cursor-based pagination | Accepted |
| [003](./docs/adr/ADR-003-postgresql-over-mongodb.md) | PostgreSQL over MongoDB | Accepted |
| [004](./docs/adr/ADR-004-caching-and-rate-limiting.md) | Caching + rate limiting via Redis | Accepted |
| 005 | Testing pyramid scope | Pending |

---

## Local development

```bash
# Requirements: Docker Desktop, Python 3.12+

make up                               # builds + starts api + Postgres 16 + Redis 7
make migrate                          # alembic upgrade head
make logs                             # tail api logs
make down                             # stop stack
```

API at `http://localhost:8000`. OpenAPI docs at `/docs`. Liveness probe at `/health`.

See [`PROGRESS.md`](./PROGRESS.md) for the current build log.

---

## Author

**[Jotive.dev](https://dev.jotive.com.co)** — Backend Engineer · Python · Node.js
[GitHub](https://github.com/jotive) · [LinkedIn](https://www.linkedin.com/in/jotive/)

---

## License

MIT
