from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from fastapi import Request, Response

REQUEST_ID_HEADER = "X-Request-Id"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": _utc_iso(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Keep output stable; only include a small allowlist of extras.
        for key in (
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "client",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_json_logging(*, logger_name: str = "opensem") -> logging.Logger:
    """
    Configure a minimal JSON logger that writes to stdout (Docker-friendly).
    Safe to call multiple times; it will not duplicate handlers.
    """
    level = os.getenv("OPENSEM_LOG_LEVEL", "INFO").upper().strip() or "INFO"

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.propagate = False

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger


def get_or_create_request_id(request: Request) -> str:
    rid = request.headers.get(REQUEST_ID_HEADER)
    if rid and rid.strip():
        return rid.strip()
    return str(uuid.uuid4())


def set_request_id_response_header(response: Response, request_id: str) -> None:
    response.headers[REQUEST_ID_HEADER] = request_id


def log_request(
    logger: logging.Logger,
    *,
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    extra: Mapping[str, Any] | None = None,
) -> None:
    e: dict[str, Any] = {
        "request_id": request_id,
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(float(duration_ms), 3),
    }
    if extra:
        e.update(extra)
    logger.info("http_request", extra=e)


class RequestTimer:
    def __enter__(self) -> "RequestTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._end = time.perf_counter()

    @property
    def duration_ms(self) -> float:
        end = getattr(self, "_end", None)
        if end is None:
            end = time.perf_counter()
        return (end - self._start) * 1000.0

