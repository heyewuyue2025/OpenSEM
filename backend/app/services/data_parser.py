"""
数据解析服务 — 解析在内存中完成；解析后的 DataFrame 按 data_key 可缓存在内存、
Redis（若配置）与本地磁盘（OPENSEM_DATA_STORE_DIR），以便进程重启后仍可按 key 取数。
"""
import hashlib
import io
import os
import pickle
import tempfile
import uuid
from pathlib import Path
from typing import Optional
import pandas as pd

from app.config import MAX_UPLOAD_SIZE_MB
from app.settings import get_settings

# 内存存储：data_key -> DataFrame（仅用于当前会话，生产环境用 Redis）
_data_store: dict[str, pd.DataFrame] = {}


class FileTooLargeError(ValueError):
    pass


def _redis_client():
    url = os.getenv("OPENSEM_REDIS_URL", "").strip()
    if not url:
        return None
    try:
        import redis  # type: ignore

        return redis.Redis.from_url(url, decode_responses=False)
    except Exception:
        return None


def _redis_key(data_key: str) -> str:
    return f"opensem:data:{data_key}"


def _data_store_dir() -> Path:
    """上传数据磁盘缓存目录；默认系统临时目录下 opensem-data/。"""
    override = os.getenv("OPENSEM_DATA_STORE_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path(tempfile.gettempdir()) / "opensem-data"


def _disk_filename(data_key: str) -> str:
    h = hashlib.sha256(data_key.encode("utf-8")).hexdigest()
    return f"{h}.pkl"


def _disk_path(data_key: str) -> Path:
    return _data_store_dir() / _disk_filename(data_key)


def _save_df_to_disk(data_key: str, df: pd.DataFrame) -> None:
    path = _disk_path(data_key)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = pickle.dumps(df, protocol=pickle.HIGHEST_PROTOCOL)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(payload)
        tmp.replace(path)
    except Exception:
        pass


def _load_df_from_disk(data_key: str) -> Optional[pd.DataFrame]:
    path = _disk_path(data_key)
    try:
        if not path.is_file():
            return None
        raw = path.read_bytes()
        df = pickle.loads(raw)
        if isinstance(df, pd.DataFrame):
            return df
        return None
    except Exception:
        return None


def _delete_df_from_disk(data_key: str) -> None:
    path = _disk_path(data_key)
    try:
        if path.is_file():
            path.unlink()
    except Exception:
        pass


def _infer_var_type(series: pd.Series) -> str:
    """推断变量类型：continuous 或 ordinal"""
    n_unique = series.nunique()
    if pd.api.types.is_integer_dtype(series) and n_unique <= 10:
        return "ordinal"
    return "continuous"


def _parse_csv(content: bytes, filename: str) -> tuple[pd.DataFrame, Optional[str]]:
    """解析 CSV，自动检测编码"""
    encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "latin1"]
    msg = None
    for enc in encodings:
        try:
            text = content.decode(enc)
            df = pd.read_csv(io.StringIO(text))
            if enc in ("gbk", "gb2312") and msg is None:
                msg = f"检测到文件编码为 {enc.upper()}，已自动转换"
            return df, msg
        except (UnicodeDecodeError, Exception):
            continue
    raise ValueError("无法识别文件编码，请转换为 UTF-8 后重试")


def _parse_xlsx(content: bytes) -> pd.DataFrame:
    """解析 XLSX"""
    return pd.read_excel(io.BytesIO(content), engine="openpyxl")


def _parse_sav(content: bytes) -> pd.DataFrame:
    """解析 SAV (SPSS)"""
    import pyreadstat
    df, _ = pyreadstat.read_sav(io.BytesIO(content))
    return df


def parse_file(
    content: bytes,
    filename: str,
    file_size: int,
) -> dict:
    """
    解析数据文件，返回变量预览。
    数据存入内存 store，返回 data_key 供后续分析使用。
    """
    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise FileTooLargeError(f"文件超过 {MAX_UPLOAD_SIZE_MB} MB 限制，请精简后重试")

    ext = filename.lower().split(".")[-1] if "." in filename else ""
    msg = None

    if ext == "csv":
        df, msg = _parse_csv(content, filename)
    elif ext in ("xlsx", "xls"):
        df = _parse_xlsx(content)
    elif ext == "sav":
        df = _parse_sav(content)
    else:
        raise ValueError(f"不支持的文件格式 .{ext}，请上传 CSV / XLSX / SAV")

    if df.empty:
        raise ValueError("解析结果为空，请检查文件内容")

    s = get_settings()
    n_rows = int(len(df))
    n_cols = int(len(df.columns))
    if n_rows > s.upload_max_rows:
        raise ValueError(f"数据行数超过上限（{n_rows} > {s.upload_max_rows}）。请抽样/筛选后重试")
    if n_cols > s.upload_max_cols:
        raise ValueError(f"数据列数超过上限（{n_cols} > {s.upload_max_cols}）。请删除无关变量后重试")

    variables = []
    for col in df.columns:
        s = df[col]
        n_valid = int(s.notna().sum())
        n_total = len(s)
        missing_rate = round((n_total - n_valid) / n_total * 100, 2) if n_total else 0
        variables.append({
            "name": str(col),
            "type": _infer_var_type(s.dropna()),
            "n_valid": n_valid,
            "missing_rate": missing_rate,
        })

    high_missing = any(v["missing_rate"] > 5 for v in variables)

    data_key = str(uuid.uuid4())
    _data_store[data_key] = df

    _save_df_to_disk(data_key, df)

    r = _redis_client()
    if r is not None:
        # 让 Celery worker 也能取到上传数据（避免仅存内存导致异步任务 data_key 无效）
        try:
            payload = pickle.dumps(df, protocol=pickle.HIGHEST_PROTOCOL)
            r.set(_redis_key(data_key), payload, ex=60 * 60)  # 1h TTL
        except Exception:
            # Redis 只是加速/共享层，失败不阻断主流程
            pass

    return {
        "success": True,
        "n_rows": n_rows,
        "n_cols": n_cols,
        "variables": variables,
        "data_key": data_key,
        "message": msg,
        "high_missing_warning": high_missing,
    }


def get_data(data_key: str) -> Optional[pd.DataFrame]:
    """从 store 获取 DataFrame"""
    df = _data_store.get(data_key)
    if df is not None:
        return df

    r = _redis_client()
    if r is not None:
        try:
            raw = r.get(_redis_key(data_key))
            if raw:
                df = pickle.loads(raw)
                if isinstance(df, pd.DataFrame):
                    _data_store[data_key] = df
                    return df
        except Exception:
            pass

    df = _load_df_from_disk(data_key)
    if df is not None:
        _data_store[data_key] = df
    return df


def drop_data(data_key: str) -> None:
    """分析完成后销毁数据"""
    _data_store.pop(data_key, None)
    r = _redis_client()
    if r is not None:
        try:
            r.delete(_redis_key(data_key))
        except Exception:
            pass
    _delete_df_from_disk(data_key)
