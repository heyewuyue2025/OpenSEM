"""
4.2 逻辑表单建模模块（核心创新）
- 测量模型 (CFA)
- 结构模型 (Path)
- 双向路径处理
- 误差协变设定
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator
from collections import defaultdict

from app.api.errors import ErrorCode, api_error
from app.services.data_parser import get_data

router = APIRouter()


class LatentVariable(BaseModel):
    """潜变量定义"""
    name: str
    indicators: list[str] = Field(default_factory=list)


class PathRelation(BaseModel):
    """路径关系"""
    from_var: str
    to_var: str


class SemModel(BaseModel):
    """SEM 模型定义"""
    data_key: str
    latent_vars: list[LatentVariable] = Field(default_factory=list)
    paths: list[PathRelation] = Field(default_factory=list)
    error_covariances: list[list[str]] = Field(default_factory=list)  # [[e1, e2], ...]


def _build_model_context(model: SemModel) -> tuple[set[str], set[str], list[str]]:
    """统一校验模型并构建变量上下文，返回 (latent_names, observed_names, warnings)"""
    df = get_data(model.data_key)
    if df is None:
        raise api_error(
            400,
            code=ErrorCode.DATA_KEY_INVALID,
            message="data_key 无效或已过期",
            hint="请回到“数据导入”页重新上传数据，然后再继续建模。",
        )

    dataset_vars = {str(c) for c in df.columns}
    latent_names: set[str] = set()
    observed_names: set[str] = set()
    warnings: list[str] = []

    # CFA 校验：潜变量命名、题项数、题项存在性
    for lv in model.latent_vars:
        name = lv.name.strip()
        if not name:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message="潜变量名称不能为空")
        if name in dataset_vars:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message=f"潜变量名称不能与观测变量重名：{name}")
        if name in latent_names:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message=f"潜变量重名：{name}")
        if len(lv.indicators) < 2:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message=f"潜变量 {name} 至少需要 2 个观测变量")

        latent_names.add(name)
        seen_indicators: set[str] = set()
        for ind in lv.indicators:
            ind_name = ind.strip()
            if not ind_name:
                raise api_error(400, code=ErrorCode.BAD_REQUEST, message=f"潜变量 {name} 的题项名不能为空")
            if ind_name in seen_indicators:
                raise api_error(400, code=ErrorCode.BAD_REQUEST, message=f"潜变量 {name} 存在重复题项：{ind_name}")
            if ind_name not in dataset_vars:
                raise api_error(400, code=ErrorCode.BAD_REQUEST, message=f"题项 {ind_name} 不存在于数据中")
            seen_indicators.add(ind_name)
            observed_names.add(ind_name)

    all_symbols = dataset_vars | latent_names

    # 路径校验：变量存在、避免自回归、检测双向路径
    path_set: set[tuple[str, str]] = set()
    for p in model.paths:
        src = p.from_var.strip()
        dst = p.to_var.strip()
        if not src or not dst:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message="路径变量不能为空")
        if src == dst:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message=f"不支持自回归路径：{src} -> {dst}")
        if src not in all_symbols:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message=f"路径起点变量不存在：{src}")
        if dst not in all_symbols:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message=f"路径终点变量不存在：{dst}")
        if (src, dst) in path_set:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message=f"重复路径：{src} -> {dst}")

        if (dst, src) in path_set:
            warnings.append(f"检测到双向路径：{src} <-> {dst}，请确认理论依据")
        path_set.add((src, dst))

    # 误差协变校验：长度必须为 2，变量存在，每个误差项最多 3 条协变关系
    cov_degree: dict[str, int] = defaultdict(int)
    cov_pair_set: set[tuple[str, str]] = set()
    for pair in model.error_covariances:
        if len(pair) != 2:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message="每条误差协变必须且仅包含 2 个变量")
        a = pair[0].strip()
        b = pair[1].strip()
        if not a or not b:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message="误差协变变量不能为空")
        if a == b:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message=f"误差协变两端不能相同：{a}")
        if a not in observed_names and a not in dataset_vars:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message=f"误差项不存在：{a}")
        if b not in observed_names and b not in dataset_vars:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message=f"误差项不存在：{b}")

        key = tuple(sorted((a, b)))
        if key in cov_pair_set:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message=f"重复的误差协变：{a} ~~ {b}")
        cov_pair_set.add(key)

        cov_degree[a] += 1
        cov_degree[b] += 1
        if cov_degree[a] > 3:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message=f"误差项 {a} 的协变关系超过 3 条")
        if cov_degree[b] > 3:
            raise api_error(400, code=ErrorCode.BAD_REQUEST, message=f"误差项 {b} 的协变关系超过 3 条")

    return latent_names, observed_names, warnings


def _to_lavaan(model: SemModel) -> str:
    """表单模型转 lavaan 语法"""
    lines: list[str] = []

    # 测量模型：首个题项固定载荷 1（1*indicator）
    for lv in model.latent_vars:
        indicators = [ind.strip() for ind in lv.indicators]
        first, *rest = indicators
        rhs = [f"1*{first}"] + rest
        lines.append(f"{lv.name.strip()} =~ {' + '.join(rhs)}")

    # 结构路径
    for p in model.paths:
        lines.append(f"{p.to_var.strip()} ~ {p.from_var.strip()}")

    # 误差协变
    for pair in model.error_covariances:
        lines.append(f"{pair[0].strip()} ~~ {pair[1].strip()}")

    return "\n".join(lines)


@router.post("/validate")
def validate_model(model: SemModel):
    """
    校验模型定义（识别度、双向路径等）
    """
    _latent_names, _observed_names, warnings = _build_model_context(model)
    return {"valid": True, "warnings": warnings}


@router.post("/to-lavaan")
def model_to_lavaan(model: SemModel):
    """
    将表单逻辑转译为 lavaan 语法
    """
    _latent_names, _observed_names, warnings = _build_model_context(model)
    return {"lavaan_syntax": _to_lavaan(model), "warnings": warnings}


class LatentInteractionSnippetBody(BaseModel):
    """潜变量交互 MVP：生成乘积指标/交互潜变量骨架（需数据侧先构造乘积列）。"""

    f1: str = Field(min_length=1)
    f2: str = Field(min_length=1)
    outcome: str = Field(min_length=1)
    n_products: int = Field(default=3, ge=1, le=12)

    @field_validator("f1", "f2", "outcome", mode="before")
    @classmethod
    def _strip_names(cls, v):
        return str(v or "").strip()


@router.post("/latent-interaction-snippet")
def latent_interaction_snippet(body: LatentInteractionSnippetBody):
    """
    返回可追加到 lavaan 语法的乘积指标骨架与 semopy/lavaan 能力边界说明（不修改数据）。
    """
    f1 = body.f1
    f2 = body.f2
    y = body.outcome
    k = int(body.n_products)
    prod = " + ".join(f"P{i+1}" for i in range(k))
    lines = [
        "# --- OpenSEM 潜变量交互 MVP（乘积指标骨架）---",
        f"# 请先在数据表中创建 P1..P{k}（如中心化后的题项乘积），列名需与下列一致；再运行估算。",
        f"F_INT =~ {prod}",
        f"{y} ~ {f1} + {f2} + F_INT",
        "",
    ]
    return {
        "lavaan_snippet": "\n".join(lines),
        "semopy_note": "semopy 可估计显式写在语法中的乘积潜变量/交互项；数据列须真实存在。",
        "lavaan_note": "论文级潜交互（如 LMS）请在 R+lavaan 中复核；本骨架为可复现的最小起点。",
    }
