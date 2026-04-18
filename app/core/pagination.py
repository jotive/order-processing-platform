"""Cursor encoding — see ADR-002.

Cursor payload is versioned (`v1:<b64>`) so schema can rotate across deploys
without breaking in-flight pagers. Payload currently carries (created_at, id)
tuple matching the compound index on `orders`.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

CURSOR_VERSION = "v1"


class InvalidCursor(ValueError):
    pass


@dataclass(frozen=True)
class Cursor:
    created_at: datetime
    id: UUID

    def encode(self) -> str:
        payload = {"c": self.created_at.isoformat(), "i": str(self.id)}
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        b64 = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
        return f"{CURSOR_VERSION}:{b64}"

    @classmethod
    def decode(cls, token: str) -> Cursor:
        try:
            version, b64 = token.split(":", 1)
        except ValueError as e:
            raise InvalidCursor("Malformed cursor") from e
        if version != CURSOR_VERSION:
            raise InvalidCursor(f"Unsupported cursor version: {version}")
        padding = "=" * (-len(b64) % 4)
        try:
            raw = base64.urlsafe_b64decode(b64 + padding)
            payload = json.loads(raw)
            return cls(
                created_at=datetime.fromisoformat(payload["c"]),
                id=UUID(payload["i"]),
            )
        except (ValueError, KeyError, TypeError) as e:
            raise InvalidCursor("Malformed cursor payload") from e
