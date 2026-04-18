# ADR-001: API versioning via URL path

**Status:** Accepted
**Date:** 2026-04-18
**Deciders:** jotive.dev

## Context

The Order Processing API exposes public endpoints consumed by multiple clients (web, mobile, partner integrations). As the API evolves, breaking changes will be inevitable — new required fields, modified response shapes, or removed endpoints.

Without an explicit versioning strategy, any breaking change cascades into client outages. We need a mechanism that:

1. Allows multiple API versions to coexist during client migration windows.
2. Is self-documenting and discoverable by humans browsing the API.
3. Plays well with standard HTTP tooling (caching, load balancers, API gateways, logs).
4. Does not require custom client libraries to inspect the version.

## Decision

**Use URL path versioning** under the prefix `/api/v{N}`.

Current version: `/api/v1/*`. Future breaking changes ship as `/api/v2/*` while `/api/v1/*` remains available for a documented deprecation window.

## Alternatives considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| **URL path** (`/api/v1/orders`) | Explicit. Self-documenting. Trivial in logs, LB rules, caching, OpenAPI. Zero client tooling required. | Slight route duplication between versions. URL schema implies REST maturity `v1 = resource`. | **Chosen** — benefits dominate. |
| **Header-based** (`Accept: application/vnd.api.v1+json`) | Keeps URLs clean — one canonical resource URL. Aligns with HATEOAS purism. | Invisible in browser + curl without ceremony. Harder to test manually. Caching must include `Vary: Accept`. Confuses junior devs and external integrators. | Rejected — friction outweighs purity for a pragmatic portfolio API. |
| **Query param** (`/orders?version=1`) | Easy to toggle. Works without infra changes. | Pollutes query string, mixes versioning with filtering. Not "REST". Breaks CDN caching semantics. | Rejected — smells like an afterthought. |
| **No versioning** | Simpler until the first breaking change. | First breaking change becomes a migration crisis. | Rejected — API has external consumers. |
| **Semantic versioning in path** (`/api/1.2.0/orders`) | Fine-grained. | Explodes route count. Clients rarely pin minor/patch in practice. | Rejected — overkill. |

## Consequences

### Positive

- Breaking changes coexist under distinct prefixes — clients migrate on their own timeline.
- Logs, metrics, and dashboards can aggregate traffic per version trivially (`uri LIKE '/api/v1/%'`).
- OpenAPI spec is served per version (`/api/v1/docs`) — consumers fetch the spec that matches their client code.
- Load balancer rules can route deprecated versions to a dedicated instance pool if needed.

### Negative

- Route duplication between `v1` and `v2` during transition windows. Mitigated by keeping shared logic in services (not handlers) — versions diff on schema/adapter layers only.
- Deprecation discipline is required: a `v1 → v2` migration plan must ship with the first breaking change, not be improvised later.

### Follow-ups

- Define deprecation policy (minimum 6 months overlap, `Deprecation` + `Sunset` headers on legacy versions).
- When `/api/v2` is introduced, surface `X-Api-Deprecated-Version` header on `v1` responses.
