"""Celery 任务失败时的可展示错误：避免把完整 Traceback 直接塞进 meta.error。"""

from __future__ import annotations

from typing import Any

from app.api.errors import ErrorCode


def format_worker_exception(exc: BaseException) -> dict[str, str | None]:
    """生成 {code, message, hint}，供 Celery meta.error_detail 与前端展示。"""
    raw = str(exc).strip()
    code = ErrorCode.TASK_FAILED

    if "Traceback" in raw or 'File "' in raw or (raw.count("\n") > 2 and len(raw) > 500):
        return {
            "code": code,
            "message": "任务执行失败（计算过程出错）",
            "hint": "请检查数据列名、缺失值策略与模型设定是否与当前数据一致；可尝试简化模型或减少 Bootstrap 次数后重试。",
        }

    first = raw.split("\n")[0].strip() if raw else ""
    if len(first) > 280:
        first = first[:277] + "..."

    name = type(exc).__name__
    hint: str | None = None
    if name == "KeyError":
        hint = "请确认变量名与数据列名一致（含大小写与空格）。"
    elif name == "ValueError":
        hint = "请检查 data_key 是否有效、语法是否完整，以及缺失值处理后样本是否仍足够。"
    elif name in ("RuntimeError", "OSError", "MemoryError"):
        hint = "若反复出现，请减少 Bootstrap 次数、缩小模型或更换缺失值策略后再试。"

    return {"code": code, "message": first or "任务执行失败", "hint": hint}


def celery_failure_meta(exc: BaseException) -> dict[str, Any]:
    detail = format_worker_exception(exc)
    return {
        "progress": 100,
        "message": "失败",
        "error": detail["message"],
        "error_detail": detail,
    }
