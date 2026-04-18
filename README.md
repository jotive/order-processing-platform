# Order Processing Platform

> Part of the [jotive.dev](https://dev.jotive.com.co) technical portfolio — Senior Backend Engineer work.

Production-grade order processing backend. Not a CRUD exercise: each architectural decision is justified with trade-offs and documented as an Architecture Decision Record (ADR).

---

## What this demonstrates

- **API Design:** REST with idempotency keys, cursor pagination, standardized error handling (RFC 7807), versioning strategy
- **SQL Modeling:** Schema design for transactional integrity, indexes for real query patterns, migration strategy with Alembic
- **Caching:** Read-through and write-through strategies, TTL and event-based invalidation, Redis as cache vs data store
- **Observability:** Structured logging, Prometheus metrics, OpenTelemetry-ready
- **Testing:** Unit, integration, and end-to-end layers with clear separation
- **Delivery:** Docker multi-stage builds, CI/CD with GitHub Actions, security hardening

---

## Stack

**Backend:** Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2.0
**Database:** PostgreSQL 16 · Alembic migrations
**Cache:** Redis 7
**Runtime:** Docker · docker-compose
**CI/CD:** GitHub Actions · ruff · pytest · coverage

---

## Architecture

> Diagram pending — will ship with first milestone.

---

## Architecture Decision Records

All non-trivial decisions live in [`/docs/adr/`](./docs/adr/).

| ADR | Decision | Trade-off |
|---|---|---|
| 001 | API versioning via URL path | Explicit vs header-based |
| 002 | Cursor-based pagination | Robustness vs offset simplicity |
| 003 | PostgreSQL over MongoDB | Transactional integrity vs flexibility |
| 004 | Caching strategy for orders | Read-through vs write-through |
| 005 | Testing pyramid scope | Unit/integration/e2e boundaries |

---

## Local development

```bash
# Requirements: Docker Desktop, Python 3.12+

docker compose up -d                  # Postgres + Redis + API
docker compose exec api alembic upgrade head
docker compose exec api pytest
```

API available at `http://localhost:8000`. OpenAPI docs at `/docs`.

---

## Author

**[Jotive.dev](https://dev.jotive.com.co)** — Senior Backend Engineer
[GitHub](https://github.com/jotive) · [LinkedIn](https://www.linkedin.com/in/jotive/)

---

## License

MIT
