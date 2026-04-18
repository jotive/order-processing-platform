"""Structured JSON logging with request-scoped correlation IDs.

Every log record carries `request_id` (from `X-Request-ID` header or generated
per request). Makes cross-service tracing and log grep grep'able.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar

from pythonjsonlogger import jsonlogger

from app.core.config import get_settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging() -> None:
    settings = get_settings()

    handler = logging.StreamHandler()
    handler.setFormatter(
        jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
            rename_fields={"asctime": "ts", "levelname": "level", "name": "logger"},
        )
    )
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.api_log_level.upper())

    # Calm the uvicorn access logger — we emit our own request-scoped line.
    logging.getLogger("uvicorn.access").disabled = True
