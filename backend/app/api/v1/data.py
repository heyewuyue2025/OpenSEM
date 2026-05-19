"""
4.1 数据管理模块
- 多格式导入 (CSV, XLSX, SAV)
- 变量池预览
- 缺失值处理
- 数据安全：内存流式处理，不落盘
"""
import asyncio

import anyio
from fastapi import APIRouter, UploadFile, Request
from pydantic import BaseModel
from typing import Optional

from app.api.errors import ErrorCode, api_error
from app.services.data_parser import FileTooLargeError, parse_file, get_data
from app.config import MAX_UPLOAD_SIZE_MB
from app.settings import get_settings

router = APIRouter()

_parse_semaphore: asyncio.Semaphore | None = None


def _get_parse_semaphore() -> asyncio.Semaphore:
    global _parse_semaphore
    if _parse_semaphore is None:
        s = get_settings()
        _parse_semaphore = asyncio.Semaphore(s.parse_concurrency)
    return _parse_semaphore


class VariablePreview(BaseModel):
    """变量预览"""
    name: str
    type: str  # continuous / ordinal
    n_valid: int
    missing_rate: float


class DataParseResponse(BaseModel):
    """数据解析响应"""
    success: bool
    n_rows: int
    n_cols: int
    variables: list[VariablePreview]
    data_key: Optional[str] = None
    message: Optional[str] = None
    high_missing_warning: bool = False  # 缺失率 > 5% 时 True


class DataKeyValidationRequest(BaseModel):
    data_key: str


class DataKeyValidationResponse(BaseModel):
    valid: bool
    n_rows: int = 0
    n_cols: int = 0


@router.post("/parse", response_model=DataParseResponse)
async def parse_uploaded_data(file: UploadFile, request: Request):
    """
    解析上传的数据文件（CSV / XLSX / SAV）
    流式处理，不落盘
    """
    if not file.filename:
        raise api_error(
            400,
            code=ErrorCode.NO_FILE,
            message="请选择文件",
            hint="请点击上传区域选择 CSV / XLSX / SAV 文件后重试。",
        )

    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    raw_len = request.headers.get("content-length")
    if raw_len:
        try:
            content_length = int(raw_len, 10)
            if content_length > max_bytes:
                raise api_error(
                    413,
                    code=ErrorCode.UPLOAD_TOO_LARGE,
                    message=f"上传体积超过限制（{content_length} bytes > {max_bytes} bytes / {MAX_UPLOAD_SIZE_MB} MB）",
                    hint="请压缩文件、抽样减少行数/列数，或联系管理员调整上传限额。",
                )
        except ValueError:
            # 非法 Content-Length 忽略，继续以实际读取大小为准
            pass

    content = await file.read()
    file_size = len(content)
    if file_size > max_bytes:
        raise api_error(
            413,
            code=ErrorCode.UPLOAD_TOO_LARGE,
            message=f"文件超过 {MAX_UPLOAD_SIZE_MB} MB 限制",
            hint="请精简文件后重试，或联系管理员调整上传限额。",
        )

    try:
        s = get_settings()
        sem = _get_parse_semaphore()
        async with sem:
            with anyio.fail_after(s.parse_timeout_seconds):
                result = await anyio.to_thread.run_sync(
                    parse_file,
                    content,
                    file.filename,
                    file_size,
                )
        return DataParseResponse(
            success=True,
            n_rows=result["n_rows"],
            n_cols=result["n_cols"],
            variables=[VariablePreview(**v) for v in result["variables"]],
            data_key=result.get("data_key"),
            message=result.get("message"),
            high_missing_warning=result.get("high_missing_warning", False),
        )
    except FileTooLargeError as e:
        raise api_error(
            413,
            code=ErrorCode.UPLOAD_TOO_LARGE,
            message=str(e),
            hint="请精简文件后重试，或联系管理员调整上传限额。",
        )
    except ValueError as e:
        raise api_error(
            400,
            code=ErrorCode.PARSE_FAILED,
            message=str(e),
            hint="请检查文件格式（CSV/XLSX/SAV）、首行是否为变量名、编码是否为 UTF-8/GBK。",
        )
    except TimeoutError:
        raise api_error(
            408,
            code=ErrorCode.PARSE_TIMEOUT,
            message="解析超时",
            hint="请减少数据规模（行/列/文件大小），或稍后重试。",
        )
    except Exception as e:
        raise api_error(
            500,
            code=ErrorCode.PARSE_FAILED,
            message="解析失败",
            hint=f"请检查文件格式是否正确；如持续失败，请联系管理员并提供错误信息：{str(e)}",
        )


@router.post("/validate-key", response_model=DataKeyValidationResponse)
def validate_data_key(payload: DataKeyValidationRequest):
    """
    校验 data_key 是否仍在当前后端会话内有效
    """
    key = payload.data_key.strip()
    if not key:
        raise api_error(
            400,
            code=ErrorCode.DATA_KEY_PARAM_EMPTY,
            message="data_key 不能为空",
            hint="请先在“数据导入”页上传数据后再继续。",
        )

    df = get_data(key)
    if df is None:
        return DataKeyValidationResponse(valid=False, n_rows=0, n_cols=0)
    return DataKeyValidationResponse(valid=True, n_rows=int(len(df)), n_cols=int(len(df.columns)))
