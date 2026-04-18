# Architecture Decision Records

Living record of non-trivial decisions made in this project. Every ADR follows the same structure: **Context → Decision → Alternatives → Consequences**.

## Index

| # | Title | Status |
|---|---|---|
| [001](./ADR-001-api-versioning.md) | API versioning via URL path | Accepted |
| [002](./ADR-002-cursor-pagination.md) | Cursor-based pagination | Accepted |
| [003](./ADR-003-postgresql-over-mongodb.md) | PostgreSQL over MongoDB | Accepted |
| [004](./ADR-004-caching-and-rate-limiting.md) | Caching + rate limiting via Redis | Accepted |
| 005 | Testing pyramid scope | Pending |

## Template

```markdown
# ADR-NNN: <short title>

**Status:** Proposed | Accepted | Superseded by ADR-NNN
**Date:** YYYY-MM-DD

## Context

What problem are we solving? What constraints apply?

## Decision

What we chose.

## Alternatives considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| ... | ... | ... | ... |

## Consequences

What becomes easier. What becomes harder. What trade-offs we accepted.
```
