from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.asyncio


def _order_payload(sku: str = "SKU-1", qty: int = 2, price: str = "15.00") -> dict:
    return {
        "customer_id": str(uuid.uuid4()),
        "currency": "USD",
        "items": [{"sku": sku, "name": f"Product {sku}", "quantity": qty, "unit_price": price}],
    }


async def test_create_order_returns_201_and_matches_payload(client):
    body = _order_payload()
    r = await client.post(
        "/api/v1/orders", json=body, headers={"Idempotency-Key": uuid.uuid4().hex}
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["customer_id"] == body["customer_id"]
    assert data["status"] == "pending"
    assert len(data["items"]) == 1
    assert data["total_amount"] == "30.00"


async def test_idempotent_create_returns_same_order(client):
    key = uuid.uuid4().hex
    body = _order_payload()

    r1 = await client.post("/api/v1/orders", json=body, headers={"Idempotency-Key": key})
    r2 = await client.post("/api/v1/orders", json=body, headers={"Idempotency-Key": key})

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


async def test_idempotency_key_reuse_with_different_payload_409(client):
    key = uuid.uuid4().hex
    r1 = await client.post(
        "/api/v1/orders", json=_order_payload(), headers={"Idempotency-Key": key}
    )
    assert r1.status_code == 201

    r2 = await client.post(
        "/api/v1/orders",
        json=_order_payload(sku="DIFFERENT"),
        headers={"Idempotency-Key": key},
    )
    assert r2.status_code == 409


async def test_get_order_by_id(client):
    create = await client.post(
        "/api/v1/orders",
        json=_order_payload(),
        headers={"Idempotency-Key": uuid.uuid4().hex},
    )
    order_id = create.json()["id"]

    r = await client.get(f"/api/v1/orders/{order_id}")
    assert r.status_code == 200
    assert r.json()["id"] == order_id


async def test_get_missing_order_404(client):
    r = await client.get(f"/api/v1/orders/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_status_transitions_happy_path(client):
    create = await client.post(
        "/api/v1/orders",
        json=_order_payload(),
        headers={"Idempotency-Key": uuid.uuid4().hex},
    )
    order_id = create.json()["id"]

    for target in ["confirmed", "processing", "shipped", "delivered"]:
        r = await client.put(f"/api/v1/orders/{order_id}/status", json={"status": target})
        assert r.status_code == 200, f"{target}: {r.text}"
        assert r.json()["status"] == target


async def test_invalid_status_transition_409(client):
    create = await client.post(
        "/api/v1/orders",
        json=_order_payload(),
        headers={"Idempotency-Key": uuid.uuid4().hex},
    )
    order_id = create.json()["id"]

    r = await client.put(f"/api/v1/orders/{order_id}/status", json={"status": "delivered"})
    assert r.status_code == 409


async def test_cancel_order_204(client):
    create = await client.post(
        "/api/v1/orders",
        json=_order_payload(),
        headers={"Idempotency-Key": uuid.uuid4().hex},
    )
    order_id = create.json()["id"]

    r = await client.delete(f"/api/v1/orders/{order_id}")
    assert r.status_code == 204

    check = await client.get(f"/api/v1/orders/{order_id}")
    assert check.json()["status"] == "cancelled"


async def test_list_cursor_pagination_no_duplicates_no_gaps(client):
    customer_id = str(uuid.uuid4())
    total = 55
    for _ in range(total):
        await client.post(
            "/api/v1/orders",
            json={**_order_payload(), "customer_id": customer_id},
            headers={"Idempotency-Key": uuid.uuid4().hex},
        )

    seen: list[str] = []
    cursor: str | None = None
    while True:
        params = {"customer_id": customer_id, "size": 10}
        if cursor:
            params["cursor"] = cursor
        r = await client.get("/api/v1/orders", params=params)
        assert r.status_code == 200
        body = r.json()
        seen.extend(o["id"] for o in body["data"])
        cursor = body["next_cursor"]
        if not cursor:
            break

    assert len(seen) == total
    assert len(set(seen)) == total  # no duplicates


async def test_mutation_invalidates_cache_no_stale_read(client):
    create = await client.post(
        "/api/v1/orders",
        json=_order_payload(),
        headers={"Idempotency-Key": uuid.uuid4().hex},
    )
    order_id = create.json()["id"]

    # Prime cache
    await client.get(f"/api/v1/orders/{order_id}")
    # Mutate
    await client.put(f"/api/v1/orders/{order_id}/status", json={"status": "confirmed"})
    # Next read must reflect new state, not cached stale
    r = await client.get(f"/api/v1/orders/{order_id}")
    assert r.json()["status"] == "confirmed"
