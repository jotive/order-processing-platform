# Architecture Decision Records

Living record of non-trivial decisions made in this project. Every ADR follows the same structure: **Context → Decision → Alternatives → Consequences**.

## Index

| # | Title | Status |
|---|---|---|
| 001 | API versioning strategy | Proposed |
| 002 | Cursor-based pagination | Proposed |
| 003 | PostgreSQL over MongoDB | Proposed |
| 004 | Caching strategy | Pending |
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
