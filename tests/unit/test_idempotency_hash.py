from app.db.redis import IdempotencyStore


def test_hash_stable_across_key_ordering():
    a = IdempotencyStore.hash_payload({"b": 1, "a": 2})
    b = IdempotencyStore.hash_payload({"a": 2, "b": 1})
    assert a == b


def test_hash_changes_when_value_changes():
    a = IdempotencyStore.hash_payload({"qty": 1})
    b = IdempotencyStore.hash_payload({"qty": 2})
    assert a != b


def test_hash_handles_nested_structures():
    payload = {"items": [{"sku": "ABC", "qty": 3}], "customer": "c1"}
    assert len(IdempotencyStore.hash_payload(payload)) == 64  # sha256 hex
