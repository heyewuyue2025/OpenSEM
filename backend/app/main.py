"""
OpenSEM - 结构方程建模平台
Backend API - FastAPI
"""
import os
from contextlib import asynccontextmanager

import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.errors import ErrorCode, default_code_for_status, normalize_detail_payload
from app.api.v1 import data, model, stats, export, tasks
from app.celery_app import _is_eager
from app.observability.logging import (
    configure_json_logging,
    get_or_create_request_id,
    log_request,
    set_request_id_response_header,
    RequestTimer,
)
from app.observability.metrics import metrics
from app.settings import get_settings

logger = configure_json_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    eager = _is_eager()
    logger.info(
        "OpenSEM startup celery_mode=%s redis_url_configured=%s",
        "eager_sync" if eager else "async_worker",
        "yes" if (os.getenv("OPENSEM_REDIS_URL") or "").strip() else "no",
    )
    yield


app = FastAPI(
    title="OpenSEM API",
    description="面向社科学术研究的云端 SEM 分析平台",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_observability_middleware(request: Request, call_next):
    request_id = get_or_create_request_id(request)
    request.state.request_id = request_id

    with RequestTimer() as t:
        response = await call_next(request)

    set_request_id_response_header(response, request_id)

    duration_ms = t.duration_ms
    status_code = getattr(response, "status_code", 0) or 0
    path = request.url.path
    method = request.method

    metrics.observe(method=method, status_code=status_code, duration_ms=duration_ms)
    log_request(
        logger,
        request_id=request_id,
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
    )
    return response


@app.get("/api/metrics")
def metrics_endpoint():
    return PlainTextResponse(metrics.render_text(), media_type="text/plain; charset=utf-8")


# Phase 1 / 3 模块路由（tasks：长任务中心）
app.include_router(data.router, prefix="/api/v1/data", tags=["数据管理"])
app.include_router(model.router, prefix="/api/v1/model", tags=["表单建模"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["统计估算"])
app.include_router(export.router, prefix="/api/v1/export", tags=["导出"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["任务中心"])


@app.exception_handler(RequestValidationError)
async def opensem_validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Pydantic 请求体验证失败：统一为 { code, message, hint }，hint 含字段级 loc/msg。
    """
    errors = exc.errors()
    first = errors[0] if errors else {}
    loc_parts = [str(x) for x in (first.get("loc") or []) if x != "body"]
    loc_hint = " → ".join(loc_parts) if loc_parts else "请求体"
    msg = str(first.get("msg") or "参数校验失败")
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": ErrorCode.VALIDATION_ERROR,
                "message": f"{loc_hint}：{msg}",
                # Pydantic 部分错误（如 model_validator 的 ctx）可能含不可 JSON 序列化对象，default=str 保证 422 可返回
                "hint": json.dumps(errors, ensure_ascii=False, default=str),
            }
        },
    )


@app.exception_handler(HTTPException)
async def opensem_http_exception_handler(request: Request, exc: HTTPException):
    """
    统一错误 JSON：{"detail": {"code", "message", "hint"}}
    兼容历史：detail 为纯字符串时自动补全 code/hint。
    """
    detail = exc.detail
    if isinstance(detail, dict) and "message" in detail:
        payload = normalize_detail_payload(detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": payload})
    if isinstance(detail, str):
        payload = {
            "code": default_code_for_status(exc.status_code),
            "message": detail,
            "hint": None,
        }
        return JSONResponse(status_code=exc.status_code, content={"detail": payload})
    payload = normalize_detail_payload(detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": payload})


@app.get("/")
def root():
    return {"name": "OpenSEM API", "status": "ok", "version": "0.1.0"}


@app.get("/api/health")
def health():
    s = get_settings()

    lavaan = {"available": False, "reason": "unknown"}
    try:
        from app.services.lavaan_service import check_lavaan_available

        a = check_lavaan_available()
        lavaan = {"available": bool(a.available), "reason": a.reason}
    except Exception as e:
        lavaan = {"available": False, "reason": f"check_failed: {str(e)}"}

    eager = _is_eager()
    body = {
        "status": "healthy",
        "mode": s.mode,
        "celery_eager": eager,
        "celery_execution_mode": "eager_sync" if eager else "async_worker",
        "lavaan": lavaan,
        "require_lavaan": s.require_lavaan,
        "with_lavaan": s.with_lavaan,
    }
    if s.require_lavaan and not lavaan.get("available"):
        body["status"] = "unhealthy"
        return JSONResponse(status_code=503, content=body)
    return body
