# ADR-003: PostgreSQL over MongoDB for order persistence

**Status:** Accepted
**Date:** 2026-04-18
**Deciders:** jotive.dev

## Context

The Order Processing Platform must persist orders and order items with the following properties:

- **Strong consistency** — a write confirmed to the client must be visible to the next read. Orders drive money movement; eventual consistency is a footgun.
- **Transactional integrity across multiple rows** — creating an order inserts one `orders` row plus N `order_items` rows. Either all succeed or none do.
- **Relational shape** — an order *has many* items, items *reference* an order. Joins, foreign keys, cascade deletes are first-class requirements, not incidental.
- **Arbitrary range and equality filters** — pagination by `created_at`, filtering by `status`, `customer_id`. All read patterns are well-known up front.
- **External consumers** — partner integrations will issue ad-hoc queries, aggregations, reports. Schema discoverability matters.
- **Constraints enforceable at the data layer** — `total_amount >= 0`, status as a closed enum, unique idempotency keys. These are correctness guarantees, not application policies.

## Decision

**Use PostgreSQL 16** as the primary datastore.

Schema is modeled relationally: `orders` (parent) + `order_items` (child, `ON DELETE CASCADE`). UUID primary keys. Compound index on `(created_at, id)` backs cursor pagination (see ADR-002). Check constraints enforce enum membership and non-negative monetary values. Unique constraint on `idempotency_key` backs the idempotency contract.

## Alternatives considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| **PostgreSQL** | ACID out of the box. Multi-row transactions. Strong types + constraints at the DB layer. Rich SQL for analytics/reporting. Mature async driver (`asyncpg`). `JSONB` column available if we later need schemaless escape hatches. Boring, well-understood operational story. | More schema discipline required up front — migrations, foreign keys, backfills. | **Chosen** — order data is intrinsically relational and correctness-critical. |
| **MongoDB** | Flexible schema. Embedded documents map naturally to `Order { items: [...] }`. Fast writes for denormalized reads. Scales horizontally via sharding. | No multi-document ACID without transactions (added in 4.0 but with performance cost and operational caveats). Constraints (enums, non-negative amounts, uniqueness across nested fields) must live in application code — one buggy service bypasses them silently. Aggregations are less ergonomic than SQL for reporting. Schema drift becomes a tax paid on every read path. | Rejected — the flexibility MongoDB offers is flexibility we do not need and pay for with correctness risk. |
| **DynamoDB** | Managed, scales to extreme throughput, predictable latency. | Access patterns must be designed up front — changing query shape requires new indexes and sometimes full re-models. Vendor lock-in. Awkward for ad-hoc reporting. | Rejected — overkill for this scale and hostile to future query evolution. |
| **SQLite** | Zero infra. Great for local dev. | Single-writer, no network access, not a production story for a system expecting concurrent clients. | Rejected — wrong tier. |
| **Postgres + separate read store** (e.g., OpenSearch) | Enables full-text search + analytics without hitting the transactional DB. | Premature. Orders at portfolio scale do not need a separate read path. | Deferred — revisit if and when search/analytics pressure materializes. |

## Consequences

### Positive

- Financial correctness is enforceable at the layer that survives application bugs: `CHECK (total_amount >= 0)` cannot be bypassed by a mis-typed service.
- Idempotency is guaranteed by a unique constraint, not a race-prone `SELECT-then-INSERT` in application code.
- Cursor pagination (ADR-002) gets a native compound index — same write path, no extra infrastructure.
- Future analytical queries ("orders per status per day", "top customers by GMV") are trivial SQL, not MapReduce ceremony.
- Operational story is mainstream: managed Postgres is a commodity on every cloud provider (RDS, Cloud SQL, Neon, Supabase, Railway).

### Negative

- Schema changes require migrations. The team (future contributors, or future-me) must respect `alembic revision --autogenerate` as the source of truth, not hand-edit DDL.
- Vertical scaling is the first knob. Horizontal sharding requires explicit work (Citus, partitioning, or a read-replica fan-out) if write throughput ever demands it. Accepted — at portfolio scale and reasonable production scale, a single well-tuned Postgres instance handles orders-of-magnitude more than this system will see.

### Follow-ups

- Baseline Alembic migration `0001_initial_orders_schema.py` covers `orders` + `order_items` + indexes + constraints (in repo).
- Connection pooling tuned for async workload: `pool_size=10, max_overflow=20, pool_pre_ping=True` in `app/db/base.py`. Revisit once load-tested.
- Document the upgrade path: `alembic upgrade head` in the Dockerfile entrypoint for staging/prod.
