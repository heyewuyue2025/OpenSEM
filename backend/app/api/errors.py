"""
统一 API 错误体：detail 为 { code, message, hint }，便于前端展示与埋点。
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


class ErrorCode:
    """稳定错误码（与 HTTP 状态码独立，供前端分支判断）。"""

    DATA_KEY_INVALID = "DATA_KEY_INVALID"
    LAVAAN_SYNTAX_EMPTY = "LAVAAN_SYNTAX_EMPTY"
    DATA_EMPTY_AFTER_MISSING = "DATA_EMPTY_AFTER_MISSING"
    ESTIMATION_FAILED = "ESTIMATION_FAILED"
    NO_FILE = "NO_FILE"
    DATA_KEY_PARAM_EMPTY = "DATA_KEY_PARAM_EMPTY"
    UPLOAD_TOO_LARGE = "UPLOAD_TOO_LARGE"
    PARSE_TIMEOUT = "PARSE_TIMEOUT"
    PARSE_FAILED = "PARSE_FAILED"
    INTERNAL_PARSE_ERROR = "INTERNAL_PARSE_ERROR"
    TASK_SUBMIT_FAILED = "TASK_SUBMIT_FAILED"
    BAD_REQUEST = "BAD_REQUEST"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TASK_FAILED = "TASK_FAILED"


def api_error(
    status_code: int,
    *,
    code: str,
    message: str,
    hint: str | None = None,
) -> HTTPException:
    detail: dict[str, Any] = {"code": code, "message": message, "hint": hint}
    return HTTPException(status_code=status_code, detail=detail)


def default_code_for_status(status_code: int) -> str:
    if status_code == 408:
        return ErrorCode.PARSE_TIMEOUT
    if status_code == 413:
        return ErrorCode.UPLOAD_TOO_LARGE
    if status_code >= 500:
        return ErrorCode.INTERNAL_ERROR
    return ErrorCode.BAD_REQUEST


def normalize_detail_payload(detail: Any) -> dict[str, Any]:
    """
    将 HTTPException.detail 规范为 { code, message, hint }。
    用于异常处理器与单测。
    """
    if isinstance(detail, dict):
        if "message" in detail:
            code = str(detail.get("code") or ErrorCode.BAD_REQUEST)
            msg = str(detail.get("message") or "")
            hint = detail.get("hint")
            return {
                "code": code,
                "message": msg,
                "hint": hint if hint is not None else None,
            }
        return {
            "code": ErrorCode.BAD_REQUEST,
            "message": str(detail),
            "hint": None,
        }
    if isinstance(detail, str):
        return {"code": ErrorCode.BAD_REQUEST, "message": detail, "hint": None}
    return {
        "code": ErrorCode.INTERNAL_ERROR,
        "message": "未知错误",
        "hint": None,
    }
