# ADR-002: Cursor-based pagination for list endpoints

**Status:** Accepted
**Date:** 2026-04-18
**Deciders:** jotive.dev

## Context

The `GET /api/v1/orders` endpoint must return a page of orders from a dataset that:

- Grows continuously (new orders inserted at the top of the time-sorted result).
- Will reach millions of rows within the expected lifetime of the system.
- Is consumed by external clients (retail partners, internal dashboards), not just an admin UI.

Two dominant strategies exist for paginating such a resource: **offset-based** and **cursor-based**. They differ in performance characteristics and correctness under concurrent writes.

## Decision

**Use cursor-based pagination** keyed on `(created_at DESC, id DESC)`.

The cursor is an opaque base64-encoded payload containing the last-seen `created_at` and `id`. The client passes it back as `?cursor=<opaque>` to fetch the next page.

Page size is capped at 100 and defaults to 20.

## Alternatives considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| **Offset-based** (`?page=5&size=20`) | Trivial to implement. Supports random-access UX ("jump to page 87"). Matches most tutorial code. | Performance degrades **O(offset)** — `OFFSET 999980` forces Postgres to scan and discard 999,980 rows. With 1M orders, deep paging becomes unusable. Shows duplicate or skipped rows when rows are inserted mid-iteration — a correctness defect, not just a UX issue. | Rejected — API has public consumers; performance is non-negotiable. |
| **Cursor-based** | Constant-time per page — `WHERE created_at < :cursor` hits the index directly, independent of page depth. Stable under concurrent writes: the cursor anchors to a specific row, so inserts above the cursor don't shift results. | Cannot jump to arbitrary pages. Requires total-order guarantee in the sort key (solved via `(created_at, id)` compound cursor). Opaque cursor is harder to eyeball during debugging. | **Chosen** — the only option that meets scale + correctness. |
| **Keyset without opaque encoding** (`?after_id=uuid&after_date=iso`) | No encoding/decoding overhead. Client-transparent. | Exposes the internal sort strategy. If we ever change it (e.g., adding a secondary sort), clients break. | Rejected — coupling internal sort to public contract is a future-pain trap. |
| **Snapshot pagination** (materialize page IDs at first request) | Perfect stability. | Requires server-side state + TTL management. Overkill for orders — cursor gives 95% of the benefit. | Rejected — complexity does not earn its keep. |

## Consequences

### Positive

- Deep pagination stays fast at 10M+ rows — same query plan whether you're on page 1 or page 10,000.
- Clients iterating in real-time (e.g., an integration polling for new orders) see a stable view: once they have a cursor, inserts above it do not cause duplicates or gaps.
- The compound cursor `(created_at, id)` resolves the tie-breaking problem when multiple orders share the same timestamp (common under concurrent writes).

### Negative

- No "jump to page N" UX. The Admin UI, if built later, must paginate linearly or switch to a filtered search. Documented as an acceptable trade-off — the Admin is not the primary consumer.
- Cursor encoding/decoding must be stable across deploys. Approach: version the cursor payload (`v1:<base64>`) so we can rotate the schema without breaking in-flight pagers.

### Follow-ups

- Implement cursor encoding utility in `app/core/pagination.py` with version prefix.
- Add integration test: paginate 1,000 orders in pages of 10, assert no duplicates and no gaps under concurrent inserts.
