from __future__ import annotations

import os
from dataclasses import dataclass


def _parse_bool(v: object, *, default: bool = False) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s == "":
        return default
    return s in ("1", "true", "yes", "y", "on")


def is_celery_eager_effective() -> bool:
    """
    Celery 是否以 eager（同步）模式运行。

    - 显式设置 OPENSEM_CELERY_EAGER=1/0（或 true/false）时优先采用。
    - 未设置时：若 OPENSEM_REDIS_URL 未配置或为空，则默认 eager=True，
      便于本地无 Redis 仍跑通 tasks 流程；配置了 Redis URL 则默认走异步 broker。
    """
    raw = os.getenv("OPENSEM_CELERY_EAGER", "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    redis_url = (os.getenv("OPENSEM_REDIS_URL") or "").strip()
    return not redis_url


def _parse_int(v: object, *, default: int, min_value: int | None = None) -> int:
    if v is None:
        n = default
    else:
        s = str(v).strip()
        if s == "":
            n = default
        else:
            try:
                n = int(s, 10)
            except Exception:
                n = default
    if min_value is not None and n < min_value:
        return min_value
    return n


@dataclass(frozen=True)
class Settings:
    require_lavaan: bool
    with_lavaan: bool | None

    # Upload/parse guardrails
    upload_max_size_mb: int
    upload_max_rows: int
    upload_max_cols: int
    parse_timeout_seconds: int
    parse_concurrency: int

    @property
    def mode(self) -> str:
        return "strict" if self.require_lavaan else "lite"


def get_settings() -> Settings:
    require_lavaan = _parse_bool(os.getenv("OPENSEM_REQUIRE_LAVAAN"), default=False)
    raw_with = os.getenv("OPENSEM_WITH_LAVAAN")
    with_lavaan = None if raw_with is None else _parse_bool(raw_with, default=True)

    upload_max_size_mb = _parse_int(
        os.getenv("OPENSEM_UPLOAD_MAX_SIZE_MB"), default=100, min_value=1
    )
    upload_max_rows = _parse_int(os.getenv("OPENSEM_UPLOAD_MAX_ROWS"), default=200_000, min_value=1)
    upload_max_cols = _parse_int(os.getenv("OPENSEM_UPLOAD_MAX_COLS"), default=2_000, min_value=1)
    parse_timeout_seconds = _parse_int(
        os.getenv("OPENSEM_PARSE_TIMEOUT_SECONDS"), default=30, min_value=1
    )
    parse_concurrency = _parse_int(
        os.getenv("OPENSEM_PARSE_CONCURRENCY"), default=4, min_value=1
    )

    return Settings(
        require_lavaan=require_lavaan,
        with_lavaan=with_lavaan,
        upload_max_size_mb=upload_max_size_mb,
        upload_max_rows=upload_max_rows,
        upload_max_cols=upload_max_cols,
        parse_timeout_seconds=parse_timeout_seconds,
        parse_concurrency=parse_concurrency,
    )

