# Roadmap — Order Processing Platform

Plan público. Items concretos, no ideas. Si no está acá, no está commited.

> Live narrative log of past sessions: [`PROGRESS.md`](PROGRESS.md). Structured event log: [`TRACE.md`](TRACE.md).

## Now (2026-05)

- [ ] **ADR-005**: testing pyramid (unit / integration / e2e boundaries, when to reach for each)
- [ ] **OpenTelemetry tracing** with OTLP exporter — span per request through middleware → handler → repo → DB/Redis
- [ ] **Prometheus metrics** — `orders_created_total{status}`, request duration histogram, rate-limit reject counter
- [ ] **k6 load baseline** — capture p50 / p95 / p99 with and without rate-limit at 100/200/500 req/min

## Next (next 30 days)

- [ ] **Authentication layer** — current rate-limit key is `request.client.host`. Move to authenticated principal (JWT or API key).
- [ ] **Authorization** — tenant scoping for orders (multi-tenant prerequisite).
- [ ] **ADR-006**: auth strategy (JWT vs API key vs OAuth client credentials, why)
- [ ] **Webhook delivery** — outbound notifications on status change with retry + signature verification
- [ ] **Test coverage to 80%+ global** (currently focused on unit + integration paths; gaps in middleware edge cases and lifespan teardown)

## Later (60–90 days)

- [ ] **Event-driven extension** — emit `OrderCreated`, `OrderShipped`, `OrderDelivered` to a broker (Kafka or NATS) for downstream consumers
- [ ] **Saga pattern** for order fulfillment — orchestrate inventory reservation, payment authorization, shipping label, with compensating actions on failure
- [ ] **Read replicas + CQRS** — split list/get queries to a read replica once write load justifies
- [ ] **Public demo deployment** — read-only with seed data, linked from README

## Won't do (yet)

- GraphQL endpoint. REST + cursor pagination is enough for the current consumers.
- Vendor lock-in for events (managed Kafka). NATS or self-hosted Kafka covers the use case at lower cost until scale demands otherwise.
- Multi-region active-active. Premature; premium operational cost vs current load.
- gRPC alternative API. JSON over HTTP keeps the surface inspectable; gRPC adds tooling cost without product gain at current scale.

## Revisit conditions

- If load test shows token bucket adds > 5ms p99 latency → reconsider rate-limit algorithm (sliding window log, leaky bucket).
- If write load exceeds ~1k orders/min sustained → CQRS read path moves from Later to Next.
- If a real customer requires webhook delivery → moves from Next to Now.
- If the authenticated-principal work blocks for > 14 days → break ADR-006 into smaller decisions to unblock scope.

---

*Tracked alongside [`PROGRESS.md`](PROGRESS.md) (session narrative) and [`TRACE.md`](TRACE.md) (structured events).*
