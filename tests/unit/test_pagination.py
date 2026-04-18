from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.core.pagination import Cursor, InvalidCursor


def test_cursor_roundtrip():
    c = Cursor(created_at=datetime(2026, 4, 18, 12, 0, tzinfo=UTC), id=uuid4())
    decoded = Cursor.decode(c.encode())
    assert decoded.created_at == c.created_at
    assert decoded.id == c.id


def test_cursor_encoded_has_version_prefix():
    c = Cursor(created_at=datetime.now(UTC), id=uuid4())
    assert c.encode().startswith("v1:")


def test_cursor_rejects_unknown_version():
    with pytest.raises(InvalidCursor):
        Cursor.decode("v99:bm90aGluZw")


def test_cursor_rejects_malformed_token():
    with pytest.raises(InvalidCursor):
        Cursor.decode("not-a-cursor")


def test_cursor_rejects_corrupt_payload():
    with pytest.raises(InvalidCursor):
        Cursor.decode("v1:!!!notbase64!!!")
