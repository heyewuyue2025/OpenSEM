from __future__ import annotations

from typing import Any, Literal

from celery.result import AsyncResult
from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator, model_validator

# 与 stats.EstimateRequest 对齐，便于任务入口与同步估算约束一致
EstimatorLiteral = Literal["ML", "GLS"]
MissingStrategyLiteral = Literal["listwise", "fiml", "mean_impute"]

from app.celery_app import celery_app
from app.api.errors import ErrorCode, api_error
from app.api.v1.stats import EstimateRequest
from app.tasks.stats_tasks import (
    fit_semopy_task,
    bootstrap_mediation_task,
    latent_interaction_probe_task,
    moderation_analysis_task,
    moderated_mediation_task,
    invariance_configural_task,
    invariance_lavaan_series_task,
    model_compare_task,
    mga_structural_path_compare_task,
)


router = APIRouter()


def _sanitize_task_error_message(s: str | None) -> str | None:
    """避免轮询接口把完整 Python Traceback 直接返回给前端。"""
    if not s:
        return s
    if len(s) > 500 and ("Traceback" in s or 'File "' in s):
        return "任务执行失败（技术性错误详情已省略，请检查数据列名、缺失值与模型设定）"
    return s


class TaskSubmitResponse(BaseModel):
    task_id: str


class TaskStatusResponse(BaseModel):
    task_id: str
    state: str
    ready: bool
    successful: bool | None = None
    progress: int | None = None
    message: str | None = None
    result: Any | None = None
    error: str | None = None
    # Celery meta.error_detail：{ code, message, hint }，与 api_error 对齐
    error_detail: dict[str, Any] | None = None


@router.post("/stats-fit", response_model=TaskSubmitResponse)
def submit_stats_fit(payload: EstimateRequest):
    """
    提交“统计估算”长任务（Phase 3 骨架）
    返回 task_id，前端轮询 /api/v1/tasks/status/{task_id} 获取进度与结果。
    """
    # 注意：send_task 在 eager 模式下也会走 broker；这里直接用任务对象以支持本地 eager 兜底
    try:
        task = fit_semopy_task.apply_async(args=[payload.model_dump()])
        return TaskSubmitResponse(task_id=task.id)
    except Exception as e:
        raise api_error(
            500,
            code=ErrorCode.TASK_SUBMIT_FAILED,
            message="任务提交失败",
            hint="请检查 Celery/Redis 配置或改用 eager 模式重试。",
        ) from e


class BootstrapEffectSpec(BaseModel):
    # 兼容旧版单中介写法
    x: str | None = None
    m: str | None = None
    y: str | None = None
    # 新版通用写法：完整路径序列，如 ["X", "M1", "M2", "Y"]
    sequence: list[str] | None = None
    # 与 sequence 二选一：如 "X, M1, M2, Y" 或 "X M1 M2 Y"
    sequence_text: str | None = None
    label: str | None = None


class BootstrapMediationRequest(BaseModel):
    data_key: str = Field(min_length=1)
    lavaan_syntax: str = Field(min_length=1)
    estimator: Literal["ML", "GLS"] = "ML"
    missing_strategy: Literal["listwise", "fiml", "mean_impute"] = "listwise"
    effects: list[BootstrapEffectSpec] = Field(min_length=1)
    covariates: list[str] | None = None
    n_boot: int = Field(default=2000, ge=200, le=5000)
    ci_level: float = Field(default=0.95, gt=0, lt=1)
    seed: int | None = None
    use_standardized: bool = True

    @field_validator("data_key", "lavaan_syntax", mode="before")
    @classmethod
    def _strip_bootstrap_core(cls, v: Any) -> str:
        return str(v or "").strip()


@router.post("/bootstrap-mediation", response_model=TaskSubmitResponse)
def submit_bootstrap_mediation(payload: BootstrapMediationRequest):
    """
    提交 Bootstrap（中介效应）长任务
    """
    try:
        task = bootstrap_mediation_task.apply_async(args=[payload.model_dump()])
        return TaskSubmitResponse(task_id=task.id)
    except Exception as e:
        raise api_error(
            500,
            code=ErrorCode.TASK_SUBMIT_FAILED,
            message="任务提交失败",
            hint="请检查 Celery/Redis 配置或改用 eager 模式重试。",
        ) from e


class ModerationAnalysisRequest(BaseModel):
    data_key: str = Field(min_length=1)
    x: str = Field(min_length=1)
    w: str = Field(min_length=1)
    y: str = Field(min_length=1)
    covariates: list[str] | None = None
    moderator_type: Literal["continuous", "categorical"] = "continuous"
    missing_strategy: Literal["listwise", "fiml", "mean_impute"] = "listwise"

    @field_validator("data_key", "x", "w", "y", mode="before")
    @classmethod
    def _strip_moderation_core(cls, v: Any) -> str:
        return str(v or "").strip()


@router.post("/moderation-analysis", response_model=TaskSubmitResponse)
def submit_moderation_analysis(payload: ModerationAnalysisRequest):
    """
    提交调节变量分析长任务
    """
    try:
        task = moderation_analysis_task.apply_async(args=[payload.model_dump()])
        return TaskSubmitResponse(task_id=task.id)
    except Exception as e:
        raise api_error(
            500,
            code=ErrorCode.TASK_SUBMIT_FAILED,
            message="任务提交失败",
            hint="请检查 Celery/Redis 配置或改用 eager 模式重试。",
        ) from e


class ModeratedMediationRequest(BaseModel):
    data_key: str = Field(min_length=1)
    x: str = Field(min_length=1)
    m: str = Field(min_length=1)
    y: str = Field(min_length=1)
    w: str = Field(min_length=1)
    covariates: list[str] | None = None
    n_boot: int = Field(default=2000, ge=200, le=5000)
    ci_level: float = Field(default=0.95, gt=0, lt=1)
    seed: int | None = None
    missing_strategy: str = "listwise"
    w_type: str = "continuous"
    hayes_model: str = "7"

    @field_validator("data_key", "x", "m", "y", "w", mode="before")
    @classmethod
    def _strip_core(cls, v: Any) -> str:
        return str(v or "").strip()

    @field_validator("hayes_model", mode="before")
    @classmethod
    def _norm_hayes(cls, v: Any) -> str:
        if v is None or str(v).strip() == "":
            return "7"
        s = str(v).strip().lower()
        if s in ("7", "process_7", "model7", "m7"):
            return "7"
        if s in ("14", "process_14", "model14", "m14"):
            return "14"
        raise ValueError("hayes_model 仅支持 7（X→M 受 W 调节）或 14（M→Y 受 W 调节）")

    @field_validator("w_type", mode="before")
    @classmethod
    def _norm_w_type(cls, v: Any) -> str:
        if v is None or str(v).strip() == "":
            return "continuous"
        s = str(v).strip().lower()
        if s in ("continuous", "categorical"):
            return s
        raise ValueError("w_type 须为 continuous 或 categorical")

    @model_validator(mode="after")
    def _m14_requires_continuous_w(self) -> ModeratedMediationRequest:
        if self.hayes_model == "14" and self.w_type != "continuous":
            raise ValueError("PROCESS Model 14 当前仅支持连续调节变量 W（请使用 w_type=continuous）")
        return self


@router.post("/moderated-mediation", response_model=TaskSubmitResponse)
def submit_moderated_mediation(payload: ModeratedMediationRequest):
    """
    提交有调节的中介（Hayes Model 7，观测变量）长任务
    """
    try:
        task = moderated_mediation_task.apply_async(args=[payload.model_dump()])
        return TaskSubmitResponse(task_id=task.id)
    except Exception as e:
        raise api_error(
            500,
            code=ErrorCode.TASK_SUBMIT_FAILED,
            message="任务提交失败",
            hint="请检查 Celery/Redis 配置或改用 eager 模式重试。",
        ) from e


class LatentInteractionProbeRequest(BaseModel):
    """潜变量交互 MVP：在完整语法上拟合并筛选与 f1/f2 相关的结构路径。"""

    data_key: str = Field(min_length=1)
    lavaan_syntax: str = Field(min_length=1)
    y: str = Field(min_length=1)
    f1: str = Field(min_length=1)
    f2: str = Field(min_length=1)
    estimator: EstimatorLiteral = "ML"
    missing_strategy: MissingStrategyLiteral = "listwise"

    @field_validator("data_key", "lavaan_syntax", "y", "f1", "f2", mode="before")
    @classmethod
    def _strip_li(cls, v: Any) -> str:
        return str(v or "").strip()


@router.post("/latent-interaction-probe", response_model=TaskSubmitResponse)
def submit_latent_interaction_probe(payload: LatentInteractionProbeRequest):
    """
    提交潜变量交互探测（semopy 拟合 + 结构路径筛选）
    """
    try:
        task = latent_interaction_probe_task.apply_async(args=[payload.model_dump()])
        return TaskSubmitResponse(task_id=task.id)
    except Exception as e:
        raise api_error(
            500,
            code=ErrorCode.TASK_SUBMIT_FAILED,
            message="任务提交失败",
            hint="请检查 Celery/Redis 配置或改用 eager 模式重试。",
        ) from e


class InvarianceConfiguralRequest(BaseModel):
    data_key: str = Field(min_length=1, max_length=512)
    lavaan_syntax: str = Field(min_length=1, max_length=500_000)
    estimator: EstimatorLiteral = "ML"
    missing_strategy: MissingStrategyLiteral = "listwise"
    group_var: str = Field(min_length=1, max_length=256)
    max_groups: int = Field(default=8, ge=1, le=64)

    @field_validator("data_key", "lavaan_syntax", "group_var", mode="before")
    @classmethod
    def _strip_inv_cfg(cls, v: Any) -> str:
        return str(v or "").strip()


@router.post("/invariance-configural", response_model=TaskSubmitResponse)
def submit_invariance_configural(payload: InvarianceConfiguralRequest):
    """
    提交多群组配置不变性（各组分别拟合）长任务
    """
    try:
        task = invariance_configural_task.apply_async(args=[payload.model_dump()])
        return TaskSubmitResponse(task_id=task.id)
    except Exception as e:
        raise api_error(
            500,
            code=ErrorCode.TASK_SUBMIT_FAILED,
            message="任务提交失败",
            hint="请检查 Celery/Redis 配置或改用 eager 模式重试。",
        ) from e


class InvarianceLavaanSeriesRequest(BaseModel):
    data_key: str = Field(min_length=1, max_length=512)
    lavaan_syntax: str = Field(min_length=1, max_length=500_000)
    missing_strategy: MissingStrategyLiteral = "fiml"
    group_var: str = Field(min_length=1, max_length=256)

    @field_validator("data_key", "lavaan_syntax", "group_var", mode="before")
    @classmethod
    def _strip_inv_series(cls, v: Any) -> str:
        return str(v or "").strip()


@router.post("/invariance-lavaan-series", response_model=TaskSubmitResponse)
def submit_invariance_lavaan_series(payload: InvarianceLavaanSeriesRequest):
    """
    提交 lavaan 多群组不变性序列（configural/metric/scalar/strict）
    """
    try:
        task = invariance_lavaan_series_task.apply_async(args=[payload.model_dump()])
        return TaskSubmitResponse(task_id=task.id)
    except Exception as e:
        raise api_error(
            500,
            code=ErrorCode.TASK_SUBMIT_FAILED,
            message="任务提交失败",
            hint="请检查 Celery/Redis 配置或改用 eager 模式重试。",
        ) from e


class ModelCompareRequest(BaseModel):
    data_key: str = Field(min_length=1, max_length=512)
    lavaan_syntax_a: str = Field(min_length=1, max_length=500_000)
    lavaan_syntax_b: str = Field(min_length=1, max_length=500_000)
    label_a: str | None = Field(default=None, max_length=256)
    label_b: str | None = Field(default=None, max_length=256)
    estimator: EstimatorLiteral = "ML"
    missing_strategy: MissingStrategyLiteral = "fiml"

    @field_validator("data_key", "lavaan_syntax_a", "lavaan_syntax_b", mode="before")
    @classmethod
    def _strip_mc_core(cls, v: Any) -> str:
        return str(v or "").strip()

    @field_validator("label_a", "label_b", mode="before")
    @classmethod
    def _strip_mc_labels(cls, v: Any) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None


@router.post("/model-compare", response_model=TaskSubmitResponse)
def submit_model_compare(payload: ModelCompareRequest):
    """
    提交模型比较长任务（AIC/BIC + 嵌套模型 LRT）
    """
    try:
        task = model_compare_task.apply_async(args=[payload.model_dump()])
        return TaskSubmitResponse(task_id=task.id)
    except Exception as e:
        raise api_error(
            500,
            code=ErrorCode.TASK_SUBMIT_FAILED,
            message="任务提交失败",
            hint="请检查 Celery/Redis 配置或改用 eager 模式重试。",
        ) from e


class StructuralPathItem(BaseModel):
    """单条结构路径（回归：outcome ~ predictor）。"""

    predictor: str = Field(min_length=1, max_length=256)
    outcome: str = Field(min_length=1, max_length=256)

    @field_validator("predictor", "outcome", mode="before")
    @classmethod
    def _strip_path_item(cls, v: Any) -> str:
        return str(v or "").strip()


class MgaStructuralPathCompareRequest(BaseModel):
    data_key: str = Field(min_length=1, max_length=512)
    lavaan_syntax: str = Field(min_length=1, max_length=500_000)
    group_var: str = Field(min_length=1, max_length=256)
    outcome: str | None = Field(default=None, max_length=256)
    predictor: str | None = Field(default=None, max_length=256)
    # Wave 3：发表场景补齐（更复杂）：允许一次任务比较多条结构路径。
    # 兼容旧协议：若 paths 为空，则使用 outcome/predictor 作为单条路径。
    paths: list[StructuralPathItem] | None = Field(default=None, max_length=32)
    estimator: EstimatorLiteral = "ML"
    missing_strategy: MissingStrategyLiteral = "fiml"

    @field_validator("data_key", "lavaan_syntax", "group_var", mode="before")
    @classmethod
    def _strip_mga_core(cls, v: Any) -> str:
        return str(v or "").strip()

    @field_validator("outcome", "predictor", mode="before")
    @classmethod
    def _strip_mga_path_fields(cls, v: Any) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    @model_validator(mode="after")
    def _paths_or_legacy_pair(self) -> MgaStructuralPathCompareRequest:
        if self.paths:
            return self
        if self.outcome and self.predictor:
            return self
        raise ValueError("须提供 paths（至少一条）或同时提供 outcome 与 predictor")


@router.post("/mga-structural-path-compare", response_model=TaskSubmitResponse)
def submit_mga_structural_path_compare(payload: MgaStructuralPathCompareRequest):
    """
    提交 MGA 结构路径跨组比较长任务（单条路径最小闭环）
    """
    try:
        task = mga_structural_path_compare_task.apply_async(args=[payload.model_dump()])
        return TaskSubmitResponse(task_id=task.id)
    except Exception as e:
        raise api_error(
            500,
            code=ErrorCode.TASK_SUBMIT_FAILED,
            message="任务提交失败",
            hint="请检查 Celery/Redis 配置或改用 eager 模式重试。",
        ) from e


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    r = AsyncResult(task_id, app=celery_app)
    try:
        info = r.info
        meta = info if isinstance(info, dict) else {}

        progress = meta.get("progress")
        message = meta.get("message")
        error = meta.get("error")
        error_detail = meta.get("error_detail")
        if not isinstance(error_detail, dict):
            error_detail = None

        ready = r.ready()
        successful = (r.successful() if ready else None)
        result = (r.result if (ready and successful) else None)
        failure_str = (str(r.result) if (ready and successful is False) else None)

        merged_err = error if error else failure_str
        merged_err = _sanitize_task_error_message(merged_err)

        return TaskStatusResponse(
            task_id=task_id,
            state=r.state,
            ready=ready,
            successful=successful,
            progress=progress,
            message=message,
            result=result,
            error=merged_err,
            error_detail=error_detail,
        )
    except Exception as e:
        # Celery 在某些异常序列化/反序列化失败时会抛 ValueError（例如缺 exc_type），
        # 这里兜底保证轮询接口不直接 500。
        return TaskStatusResponse(
            task_id=task_id,
            state="FAILURE",
            ready=True,
            successful=False,
            progress=100,
            message="任务失败（结果解码异常）",
            result=None,
            error="任务失败（结果解码异常）",
            error_detail={
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "任务失败（结果解码异常）",
                "hint": "请重试任务；若持续出现，请检查 worker 日志与依赖版本。",
            },
        )

