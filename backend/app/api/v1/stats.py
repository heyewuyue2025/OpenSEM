"""
4.3 统计估算配置模块
- ML / GLS 估计
- 拟合度指标
"""
from typing import Any, Literal, Optional

import math

from fastapi import APIRouter
from pydantic import BaseModel
from semopy import Model, calc_stats

from app.api.errors import ErrorCode, api_error
from app.services.data_parser import get_data
from app.services.lavaan_service import check_lavaan_available, lavaan_modification_indices

router = APIRouter()


class EstimateRequest(BaseModel):
    """估算请求"""
    data_key: str
    lavaan_syntax: str
    estimator: Literal["ML", "GLS"] = "ML"
    missing_strategy: Literal["listwise", "fiml", "mean_impute"] = "listwise"


class MiRequest(BaseModel):
    """MI 请求（Phase 2 预留）"""
    data_key: str
    lavaan_syntax: str
    top_k: int = 15
    mi_threshold: float = 3.84  # chi-square(1) @ p=0.05


class FitIndices(BaseModel):
    """拟合度指标"""
    chi2: Optional[float] = None
    chi2_df: Optional[float] = None
    rmsea: Optional[float | str] = None
    srmr: Optional[float | str] = None
    tli: Optional[float | str] = None
    cfi: Optional[float | str] = None
    status: str  # good / borderline / poor


class ParameterEstimateRow(BaseModel):
    """参数估计（用于前端展示与 APA 导出）"""
    lval: str
    op: str
    rval: str
    estimate: Optional[float] = None
    est_std: Optional[float] = None  # standardized estimate (beta / loading, etc.)
    std_err: Optional[float] = None
    z_value: Optional[float] = None
    p_value: Optional[float] = None


def _to_float(v: Any) -> Optional[float]:
    """尽量将 semopy 统计值稳健转换为 float。"""
    if v is None:
        return None
    try:
        value = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def _pick_stat(stats_df: Any, key: str) -> Optional[float]:
    """
    从 semopy calc_stats 结果中按 key 取值。
    兼容 DataFrame / dict 等常见结构。
    """
    try:
        if hasattr(stats_df, "loc"):
            # semopy 常见格式：索引为 "Value"，列为指标名
            if "Value" in getattr(stats_df, "index", []):
                return _to_float(stats_df.loc["Value", key])
            # 兜底：第一行
            if hasattr(stats_df, "columns") and key in stats_df.columns and len(stats_df.index) > 0:
                return _to_float(stats_df.iloc[0][key])
        if isinstance(stats_df, dict) and key in stats_df:
            return _to_float(stats_df[key])
    except Exception:
        return None
    return None


def _format_metric(v: Optional[float]) -> Optional[float | str]:
    """前端展示友好格式：缺失值返回 '-'。"""
    if v is None:
        return "-"
    return round(v, 4)


def _format_param(v: Optional[float]) -> Optional[float]:
    if v is None:
        return None
    return round(v, 6)


def _score_fit(chi2_df: Optional[float], rmsea: Optional[float], srmr: Optional[float], cfi: Optional[float], tli: Optional[float]) -> str:
    """
    红黄绿规则（Phase 1 简化）：
    - good: 至少 3 项达优阈值
    - poor: 至少 2 项落入差阈值
    - 其他: borderline
    """
    good_count = 0
    poor_count = 0

    if chi2_df is not None:
        if chi2_df < 3:
            good_count += 1
        elif chi2_df > 5:
            poor_count += 1
    if rmsea is not None:
        if rmsea < 0.06:
            good_count += 1
        elif rmsea > 0.1:
            poor_count += 1
    if srmr is not None:
        if srmr < 0.08:
            good_count += 1
        elif srmr > 0.1:
            poor_count += 1
    if cfi is not None:
        if cfi >= 0.95:
            good_count += 1
        elif cfi < 0.9:
            poor_count += 1
    if tli is not None:
        if tli >= 0.95:
            good_count += 1
        elif tli < 0.9:
            poor_count += 1

    if good_count >= 3:
        return "good"
    if poor_count >= 2:
        return "poor"
    return "borderline"


def _apply_missing_strategy(df, strategy: str):
    """
    缺失值处理（Phase 1）
    - listwise: 列表删除（dropna any）
    - mean_impute: 均值插补（仅数值列；非数值列原样）
    - fiml: 交由 semopy 的 FIML obj 处理（不在此预处理）
    """
    if strategy == "fiml":
        return df.copy()
    if strategy == "listwise":
        return df.copy().dropna(axis=0, how="any")
    if strategy == "mean_impute":
        data = df.copy()
        for col in data.columns:
            s = data[col]
            if getattr(s, "dtype", None) is not None and hasattr(s, "mean"):
                if s.dtype.kind in ("i", "u", "f"):
                    m = s.mean(skipna=True)
                    data[col] = s.fillna(m)
        return data
    # pydantic 已限制取值；这里兜底
    return df.copy().dropna(axis=0, how="any")


def _obj_from_request(payload: EstimateRequest) -> str:
    if payload.missing_strategy == "fiml":
        return "FIML"
    if payload.estimator == "GLS":
        return "GLS"
    # PRD 的“ML”在 semopy 里对齐到 MLW（默认目标）
    return "MLW"


def _extract_estimates(sem_model: Model) -> list[dict[str, Any]]:
    """
    semopy.inspect(std_est=True) 输出列：
    lval, op, rval, Estimate, Est. Std, Std. Err, z-value, p-value
    """
    try:
        df = sem_model.inspect(std_est=True)
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        rows.append(
            ParameterEstimateRow(
                lval=str(r.get("lval", "")),
                op=str(r.get("op", "")),
                rval=str(r.get("rval", "")),
                estimate=_format_param(_to_float(r.get("Estimate"))),
                est_std=_format_param(_to_float(r.get("Est. Std"))),
                std_err=_format_param(_to_float(r.get("Std. Err"))),
                z_value=_format_param(_to_float(r.get("z-value"))),
                p_value=_format_param(_to_float(r.get("p-value"))),
            ).model_dump()
        )
    return rows


def _run_estimation(payload: EstimateRequest) -> dict:
    df = get_data(payload.data_key)
    if df is None:
        raise api_error(
            400,
            code=ErrorCode.DATA_KEY_INVALID,
            message="data_key 无效或已过期",
            hint="请回到“数据导入”页重新上传数据，然后再运行估算。",
        )

    syntax = payload.lavaan_syntax.strip()
    if not syntax:
        raise api_error(
            400,
            code=ErrorCode.LAVAAN_SYNTAX_EMPTY,
            message="lavaan 语法为空",
            hint="请先在“建模”页生成 lavaan 语法后再估算。",
        )

    # Phase 1: 缺失值策略（FIML 由 semopy 处理）
    data = _apply_missing_strategy(df, payload.missing_strategy)
    if data.empty:
        raise api_error(
            400,
            code=ErrorCode.DATA_EMPTY_AFTER_MISSING,
            message="缺失值处理后无可用样本",
            hint="建议：切换缺失处理策略（例如从“列表删除”改为 FIML/均值插补），或检查变量是否存在大量缺失。",
        )

    try:
        sem_model = Model(syntax)
        # 将最大迭代控制在 50 次，满足 PRD 的不收敛处理要求
        sem_model.fit(
            data,
            obj=_obj_from_request(payload),
            solver="SLSQP",
            options={"maxiter": 50},
        )
    except Exception as e:
        raise api_error(
            400,
            code=ErrorCode.ESTIMATION_FAILED,
            message="模型未收敛或估算失败（已达 50 次上限）",
            hint=f"建议：检查路径设定是否过于复杂、是否存在共线/极端缺失、样本量是否足够；必要时简化模型后再试。原始信息：{str(e)}",
        ) from e

    stats_df = calc_stats(sem_model)

    chi2 = _pick_stat(stats_df, "chi2")
    dof = _pick_stat(stats_df, "DoF")
    rmsea = _pick_stat(stats_df, "RMSEA")
    srmr = _pick_stat(stats_df, "SRMR")
    tli = _pick_stat(stats_df, "TLI")
    cfi = _pick_stat(stats_df, "CFI")
    chi2_df = None if (chi2 is None or dof is None or dof == 0) else chi2 / dof

    fit = FitIndices(
        chi2=_format_metric(chi2),
        chi2_df=_format_metric(chi2_df),
        rmsea=_format_metric(rmsea),
        srmr=_format_metric(srmr),
        tli=_format_metric(tli),
        cfi=_format_metric(cfi),
        status=_score_fit(chi2_df, rmsea, srmr, cfi, tli),
    )
    return {
        "success": True,
        "n_used": int(len(data)),
        "missing_strategy": payload.missing_strategy,
        "estimator": payload.estimator,
        "fit_indices": fit.model_dump(),
        "estimates": _extract_estimates(sem_model),
    }


@router.post("/fit")
def fit_model(payload: EstimateRequest):
    """单群组 ML 估算（semopy）"""
    return _run_estimation(payload)


@router.post("/estimate")
def run_ml_estimation(payload: EstimateRequest):
    """向后兼容旧路径。"""
    return _run_estimation(payload)


@router.post("/mi")
def modification_indices(payload: MiRequest):
    """
    Modification Indices（Phase 2）
    - 若检测到 rpy2+R+lavaan 可用：返回真实 MI（lavaan::modindices）
    - 否则：保持占位行为（supported=false），不影响 Phase 1 主流程
    """
    df = get_data(payload.data_key)
    if df is None:
        raise api_error(
            400,
            code=ErrorCode.DATA_KEY_INVALID,
            message="data_key 无效或已过期",
            hint="请回到“数据导入”页重新上传数据，然后再获取 MI。",
        )
    syntax = payload.lavaan_syntax.strip()
    if not syntax:
        raise api_error(
            400,
            code=ErrorCode.LAVAAN_SYNTAX_EMPTY,
            message="lavaan 语法为空",
            hint="请先在“建模”页生成 lavaan 语法后再获取 MI。",
        )

    availability = check_lavaan_available()
    if not availability.available:
        return {
            "supported": False,
            "items": [],
            "message": f"当前环境未启用 lavaan（{availability.reason}）。仍使用 semopy（Phase 1），暂不支持真实 MI。",
        }

    try:
        return lavaan_modification_indices(
            data_df=df,
            lavaan_syntax=syntax,
            mi_threshold=float(payload.mi_threshold),
            top_k=int(payload.top_k),
        )
    except Exception as e:
        return {
            "supported": False,
            "items": [],
            "message": f"lavaan MI 计算失败：{str(e)}",
        }
