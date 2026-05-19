from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
import subprocess
from typing import Any


@dataclass(frozen=True)
class LavaanAvailability:
    available: bool
    reason: str | None = None


def _ensure_rpy2_conversion_context() -> None:
    """
    rpy2 的转换规则存放在 contextvars.ContextVar 中。
    FastAPI 的同步端点/线程池、Celery worker 并发等场景下，子线程可能拿不到默认 converter，
    从而触发：
      Conversion rules for `rpy2.robjects` appear to be missing.
    这里在每次进入 rpy2 调用前，为“当前上下文/线程”显式设置默认 converter，避免 strict e2e 不稳定。
    """
    try:
        import rpy2.robjects as ro
        from rpy2.robjects import conversion as cv

        try:
            cv.get_conversion()
            return
        except Exception:
            # 新线程/新 context 下可能尚未设置 converter
            cv.set_conversion(ro.default_converter)
    except Exception:
        # 可选依赖：保持上层行为（由调用方决定 supported/available）
        return


def _pandas_rpy_conversion() -> AbstractContextManager:
    """
    rpy2 3.5+ 将 localconverter 挪到 robjects.conversion；旧版仍在 pandas2ri.localconverter。
    """
    import rpy2.robjects as ro
    from rpy2.robjects import pandas2ri

    _ensure_rpy2_conversion_context()

    try:
        from rpy2.robjects.conversion import localconverter

        return localconverter(ro.default_converter + pandas2ri.converter)
    except Exception:
        return pandas2ri.localconverter(ro.default_converter + pandas2ri.converter)  # type: ignore[attr-defined]


def check_lavaan_available() -> LavaanAvailability:
    """
    rpy2 + R + lavaan 都具备时返回 available=True。
    该函数必须“可选依赖友好”：缺任何一项都不应导致后端启动失败。
    """
    try:
        import rpy2  # noqa: F401
        try:
            # 在 FastAPI/worker 多线程上下文里，直接 importr 可能触发 conversion context 报错；
            # 可用性检查改为调用 Rscript，避免将运行时上下文问题误判为“未安装”。
            probe = subprocess.run(
                ["Rscript", "-e", "if (!requireNamespace('lavaan', quietly=TRUE)) quit(status=1)"],
                check=False,
                capture_output=True,
                text=True,
                timeout=20,
            )
            if probe.returncode != 0:
                msg = (probe.stderr or probe.stdout or "").strip() or f"Rscript exit code={probe.returncode}"
                return LavaanAvailability(False, f"R 包 lavaan 不可用：{msg}")
        except Exception as e:  # lavaan/Rscript 不可用
            return LavaanAvailability(False, f"R 包 lavaan 探测失败：{str(e)}")
        return LavaanAvailability(True, None)
    except Exception as e:
        return LavaanAvailability(False, f"rpy2/R 环境不可用：{str(e)}")


def lavaan_modification_indices(*, data_df, lavaan_syntax: str, mi_threshold: float = 3.84, top_k: int = 15) -> dict[str, Any]:
    """
    使用 lavaan::modindices 输出 Modification Indices。
    返回结构尽量贴近前端展示需求与后续扩展：
    - supported: True
    - items: [{lhs, op, rhs, mi, epc, sepc_all, sepc_lv, sepc_nox, note}]
    """
    _ensure_rpy2_conversion_context()

    from rpy2.robjects import pandas2ri
    from rpy2.robjects.packages import importr
    import rpy2.robjects as ro

    lavaan = importr("lavaan")

    with _pandas_rpy_conversion():
        r_df = pandas2ri.py2rpy(data_df)

    # 允许缺失：lavaan 中常用 missing="fiml"
    # 注意：rpy2 对 R 参数名的翻译在不同版本/包装下可能不一致。
    # 为避免 "unknown argument: fixed_x" 兼容性问题，这里不显式传 fixed.x（使用 lavaan 默认即可）。
    fit = lavaan.sem(lavaan_syntax, data=r_df, missing="fiml")

    mi_df = lavaan.modindices(fit)
    # 转回 pandas DataFrame
    with _pandas_rpy_conversion():
        mi_pd = pandas2ri.rpy2py(mi_df)

    if mi_pd is None or mi_pd.empty:
        return {"supported": True, "items": [], "message": "未获得 MI（结果为空）"}

    # 常见列：lhs, op, rhs, mi, epc, sepc.all, sepc.lv, sepc.nox
    cols = [c for c in ["lhs", "op", "rhs", "mi", "epc", "sepc.all", "sepc.lv", "sepc.nox"] if c in mi_pd.columns]
    mi_pd = mi_pd[cols].copy()
    if "mi" in mi_pd.columns:
        mi_pd = mi_pd[mi_pd["mi"].astype(float) >= float(mi_threshold)]
        mi_pd = mi_pd.sort_values("mi", ascending=False)

    mi_pd = mi_pd.head(int(top_k))
    items: list[dict[str, Any]] = []
    for _, r in mi_pd.iterrows():
        items.append(
            {
                "lhs": str(r.get("lhs", "")),
                "op": str(r.get("op", "")),
                "rhs": str(r.get("rhs", "")),
                "mi": float(r.get("mi")) if r.get("mi") is not None else None,
                "epc": float(r.get("epc")) if r.get("epc") is not None else None,
                "sepc_all": float(r.get("sepc.all")) if r.get("sepc.all") is not None else None,
                "sepc_lv": float(r.get("sepc.lv")) if r.get("sepc.lv") is not None else None,
                "sepc_nox": float(r.get("sepc.nox")) if r.get("sepc.nox") is not None else None,
            }
        )

    return {"supported": True, "items": items, "message": "来自 lavaan::modindices（请结合理论，避免过拟合）"}


def _lavaan_fit_measures(fit, *, include_aicbic: bool = False) -> dict[str, float | None]:
    """
    统一抽取 lavaan 拟合度指标。
    """
    import rpy2.robjects as ro
    from rpy2.robjects.packages import importr

    lavaan = importr("lavaan")
    try:
        keys = ["chisq", "df", "cfi", "tli", "rmsea", "srmr"]
        if include_aicbic:
            keys.extend(["aic", "bic"])
        fm = lavaan.fitMeasures(fit, ro.StrVector(keys))
    except Exception:
        base = {"chi2": None, "df": None, "cfi": None, "tli": None, "rmsea": None, "srmr": None}
        if include_aicbic:
            base.update({"aic": None, "bic": None})
        return base

    # fitMeasures 返回 named numeric
    out = {}
    try:
        names = list(fm.names)
        vals = list(fm)
        for k, v in zip(names, vals):
            try:
                out[str(k)] = float(v)
            except Exception:
                out[str(k)] = None
    except Exception:
        pass

    return {
        "chi2": out.get("chisq"),
        "df": out.get("df"),
        "cfi": out.get("cfi"),
        "tli": out.get("tli"),
        "rmsea": out.get("rmsea"),
        "srmr": out.get("srmr"),
        "aic": out.get("aic"),
        "bic": out.get("bic"),
    }


def _lrt_pick(row: dict[str, Any], *must_contain: str) -> Any:
    """lavTestLRT 返回的列名因 locale / lavaan 版本略有差异，用子串匹配取值。"""
    must = [s.lower() for s in must_contain]

    def norm(s: str) -> str:
        return "".join(ch for ch in s.lower() if ch.isalnum())

    for k, v in row.items():
        kn = norm(str(k))
        if all(norm(m) in kn or m in kn for m in must):
            return v
    return None


def _lrt_to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        x = float(v)
        if x != x:  # NaN
            return None
        return x
    except (TypeError, ValueError):
        return None


def lavaan_model_compare(
    *,
    data_df,
    model_a_syntax: str,
    model_b_syntax: str,
    missing: str = "fiml",
    label_a: str = "Model A",
    label_b: str = "Model B",
) -> dict[str, Any]:
    """
    两个嵌套模型比较（lavaan）：
    - 返回 AIC/BIC + 常用拟合度（chisq/df/cfi/tli/rmsea/srmr）
    - 返回 lavTestLRT（Δχ²/Δdf/p）
    注意：LRT 是否有效取决于模型是否嵌套、是否收敛、以及 lavaan 环境可用性。
    """
    _ensure_rpy2_conversion_context()

    import rpy2.robjects as ro
    from rpy2.robjects import pandas2ri
    from rpy2.robjects.packages import importr

    lavaan = importr("lavaan")

    with _pandas_rpy_conversion():
        r_df = pandas2ri.py2rpy(data_df)

    fit_a = lavaan.sem(model_a_syntax, data=r_df, missing=missing)
    fit_b = lavaan.sem(model_b_syntax, data=r_df, missing=missing)

    a_fit = _lavaan_fit_measures(fit_a, include_aicbic=True)
    b_fit = _lavaan_fit_measures(fit_b, include_aicbic=True)

    comparison = {
        "from": label_a,
        "to": label_b,
        "ok": False,
        "chi2_diff": None,
        "df_diff": None,
        "p_value": None,
        "note": None,
    }

    lrt_error: str | None = None
    rows: list[dict[str, Any]] = []
    try:
        lrt = lavaan.lavTestLRT(fit_a, fit_b)
        with _pandas_rpy_conversion():
            lrt_pd = pandas2ri.rpy2py(lrt)
        if lrt_pd is not None and not lrt_pd.empty:
            rows = lrt_pd.to_dict(orient="records")
    except Exception as e:
        lrt_error = f"lavTestLRT 失败：{str(e)}"

    if lrt_error:
        comparison["ok"] = False
        comparison["note"] = lrt_error
    else:
        # 两模型时差异信息通常在第 2 行（索引 1）
        if len(rows) < 2:
            comparison["ok"] = False
            comparison["note"] = "lavTestLRT 结果不足（可能未收敛/版本差异导致）"
        else:
            cur_row = rows[1]
            comparison["chi2_diff"] = _lrt_to_float(_lrt_pick(cur_row, "chisq", "diff"))
            comparison["df_diff"] = _lrt_to_float(_lrt_pick(cur_row, "df", "diff"))
            comparison["p_value"] = _lrt_to_float(_lrt_pick(cur_row, "pr", "chisq"))
            comparison["ok"] = True
            comparison["note"] = None

    return {
        "supported": True,
        "success": True,
        "task": "model_compare",
        "mode": "lavaan",
        "models": [
            {"label": label_a, "fit": a_fit},
            {"label": label_b, "fit": b_fit},
        ],
        "comparison": comparison,
        "note": "建议同时参考信息准则（AIC/BIC）与嵌套模型 LRT；AIC/BIC 越小通常越优，但需结合理论与可解释性。",
    }


def _lavaan_parameter_estimates(fit, *, standardized: bool = True):
    """
    抽取 lavaan 参数估计表（pandas DataFrame）。
    """
    _ensure_rpy2_conversion_context()
    from rpy2.robjects.packages import importr
    from rpy2.robjects import pandas2ri

    lavaan = importr("lavaan")
    pe = lavaan.parameterEstimates(fit, standardized=standardized)
    with _pandas_rpy_conversion():
        return pandas2ri.rpy2py(pe)


def _inject_equal_label_for_regression(
    *,
    lavaan_syntax: str,
    outcome: str,
    predictor: str,
    n_groups: int,
    label: str = "b_eq",
) -> str:
    """
    生成“对指定回归路径跨组等值约束”的 lavaan 语法：
    - 将 `outcome ~ ... predictor ...` 中 predictor 项替换为 `c(label,label,...)*predictor`
    约束范围仅覆盖该条路径（最小增量）。
    """
    out = []
    tgt_lhs = outcome.strip()
    tgt_rhs = predictor.strip()
    if not (tgt_lhs and tgt_rhs) or n_groups < 2:
        return lavaan_syntax

    # c(label,label,...) * X
    cvec = ",".join([label] * int(n_groups))
    repl = f"c({cvec})*{tgt_rhs}"

    for raw in (lavaan_syntax or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            out.append(raw)
            continue
        if "~" not in line:
            out.append(raw)
            continue

        # 仅处理回归：lhs ~ rhs
        parts = line.split("~", 1)
        lhs = parts[0].strip()
        rhs = parts[1].strip()
        if lhs != tgt_lhs:
            out.append(raw)
            continue

        # RHS 用 + 分割，逐项替换匹配 predictor（允许带系数/label 前缀）
        items = [s.strip() for s in rhs.split("+") if s.strip()]
        changed = False
        new_items = []
        for it in items:
            # 若已经显式写成 c(...) * predictor 或 label*predictor，则不再二次包裹
            if it.endswith(tgt_rhs) or it == tgt_rhs:
                # 只在“该项明确指向 predictor”时替换
                # 简单启发：去掉空白与常见前缀后判断末尾 token
                token = it.split("*")[-1].strip()
                if token == tgt_rhs:
                    new_items.append(repl)
                    changed = True
                else:
                    new_items.append(it)
            else:
                new_items.append(it)

        if changed:
            out.append(f"{lhs} ~ " + " + ".join(new_items))
        else:
            out.append(raw)

    return "\n".join(out)


def lavaan_mga_structural_path_compare(
    *,
    data_df,
    lavaan_syntax: str,
    group_var: str,
    paths: list[dict[str, str]],
    missing: str = "fiml",
) -> dict[str, Any]:
    """
    多群组结构路径跨组比较（Wave 2 单路径 → Wave 3 分层级×多路径扩展）：
    - 层级：configural / metric / scalar / strict（测量不变性背景）
    - 每个层级内，对每条结构回归路径执行：
      - free：该层级的测量等值约束（若有），结构路径不等值
      - constrained：在 free 的基础上，仅对指定 outcome ~ predictor 加跨组等值约束
      - 输出：各组该路径估计（含标准化）+ LRT（free vs constrained）

    兼容旧最小闭环：当 paths 仅 1 条时，调用方仍可在前端按“单路径”方式展示/导出。
    """
    _ensure_rpy2_conversion_context()

    import rpy2.robjects as ro
    from rpy2.robjects import pandas2ri
    from rpy2.robjects.packages import importr

    if group_var not in data_df.columns:
        return {"supported": True, "success": False, "message": f"分组变量不存在：{group_var}"}
    if not isinstance(paths, list) or not paths:
        return {"supported": True, "success": False, "message": "paths 不能为空：请至少提供一条结构路径"}

    lavaan = importr("lavaan")
    with _pandas_rpy_conversion():
        r_df = pandas2ri.py2rpy(data_df)

    # group count（用于生成 c(label,...)）
    try:
        gvals = [x for x in data_df[group_var].dropna().unique().tolist()]
        n_groups = max(len(gvals), 0)
    except Exception:
        n_groups = 0

    def _fit_with_level(level: str):
        """
        将测量不变性层级作为背景约束：
        - configural：None
        - metric：loadings
        - scalar：loadings + intercepts
        - strict：loadings + intercepts + residuals
        """
        group_equal = None
        if level == "metric":
            group_equal = ro.StrVector(["loadings"])
        elif level == "scalar":
            group_equal = ro.StrVector(["loadings", "intercepts"])
        elif level == "strict":
            group_equal = ro.StrVector(["loadings", "intercepts", "residuals"])
        kwargs = {"data": r_df, "group": group_var, "missing": missing}
        if group_equal is not None:
            kwargs["group.equal"] = group_equal
        return lavaan.sem(lavaan_syntax, **kwargs)

    levels = ["configural", "metric", "scalar", "strict"]
    items: list[dict[str, Any]] = []

    for lv in levels:
        # 每个层级先拟合 free（结构路径不等值）
        try:
            fit_free = _fit_with_level(lv)
        except Exception as e:
            items.append(
                {
                    "level": lv,
                    "success": False,
                    "error": f"free fit failed: {str(e)}",
                }
            )
            continue

        pe = _lavaan_parameter_estimates(fit_free, standardized=True)

        for idx, pth in enumerate(paths):
            outcome = str((pth or {}).get("outcome") or "").strip()
            predictor = str((pth or {}).get("predictor") or "").strip()
            if not outcome or not predictor:
                continue

            label = f"b_eq_{idx + 1}"
            constrained_syntax = _inject_equal_label_for_regression(
                lavaan_syntax=lavaan_syntax,
                outcome=outcome,
                predictor=predictor,
                n_groups=n_groups,
                label=label,
            )

            # constrained：在同一测量层级背景下，仅该路径等值
            try:
                group_equal = None
                if lv == "metric":
                    group_equal = ro.StrVector(["loadings"])
                elif lv == "scalar":
                    group_equal = ro.StrVector(["loadings", "intercepts"])
                elif lv == "strict":
                    group_equal = ro.StrVector(["loadings", "intercepts", "residuals"])
                kwargs = {"data": r_df, "group": group_var, "missing": missing}
                if group_equal is not None:
                    kwargs["group.equal"] = group_equal
                fit_c = lavaan.sem(constrained_syntax, **kwargs)
            except Exception as e:
                items.append(
                    {
                        "level": lv,
                        "path": {"outcome": outcome, "predictor": predictor},
                        "success": False,
                        "error": f"constrained fit failed: {str(e)}",
                    }
                )
                continue

            # 参数表：按 group 抽该条回归路径
            group_rows: list[dict[str, Any]] = []
            try:
                if pe is not None and not pe.empty:
                    for _, r in pe.iterrows():
                        lhs = str(r.get("lhs", "")).strip()
                        op = str(r.get("op", "")).strip()
                        rhs = str(r.get("rhs", "")).strip()
                        if lhs == outcome and op == "~" and rhs == predictor:
                            group_rows.append(
                                {
                                    "group": int(r.get("group")) if r.get("group") is not None else None,
                                    "lhs": lhs,
                                    "op": op,
                                    "rhs": rhs,
                                    "estimate": _lrt_to_float(r.get("est")),
                                    "std_err": _lrt_to_float(r.get("se")),
                                    "p_value": _lrt_to_float(r.get("pvalue")),
                                    "std_all": _lrt_to_float(r.get("std.all")),
                                }
                            )
            except Exception:
                group_rows = []

            # LRT（free vs constrained）
            comparison = {
                "from": f"{lv}:free",
                "to": f"{lv}:constrained(path equal)",
                "ok": False,
                "chi2_diff": None,
                "df_diff": None,
                "p_value": None,
                "note": None,
            }
            lrt_error: str | None = None
            rows: list[dict[str, Any]] = []
            try:
                lrt = lavaan.lavTestLRT(fit_free, fit_c)
                with _pandas_rpy_conversion():
                    lrt_pd = pandas2ri.rpy2py(lrt)
                if lrt_pd is not None and not lrt_pd.empty:
                    rows = lrt_pd.to_dict(orient="records")
            except Exception as e:
                lrt_error = f"lavTestLRT 失败：{str(e)}"

            if lrt_error:
                comparison["ok"] = False
                comparison["note"] = lrt_error
            else:
                if len(rows) < 2:
                    comparison["ok"] = False
                    comparison["note"] = "lavTestLRT 结果不足（可能未收敛/版本差异导致）"
                else:
                    cur_row = rows[1]
                    comparison["chi2_diff"] = _lrt_to_float(_lrt_pick(cur_row, "chisq", "diff"))
                    comparison["df_diff"] = _lrt_to_float(_lrt_pick(cur_row, "df", "diff"))
                    comparison["p_value"] = _lrt_to_float(_lrt_pick(cur_row, "pr", "chisq"))
                    comparison["ok"] = True

            items.append(
                {
                    "level": lv,
                    "path": {"outcome": outcome, "predictor": predictor},
                    "n_groups": n_groups,
                    "group_estimates": group_rows,
                    "comparison": comparison,
                    "mode": "lavaan",
                    "supported": True,
                    "success": True,
                    "note": "该检验在给定测量不变性层级背景下，仅对单条结构回归路径施加跨组等值约束，其余结构参数自由，用于发表场景的逐步比较。",
                }
            )

    out: dict[str, Any] = {
        "supported": True,
        "success": True,
        "task": "mga_structural_path_compare",
        "mode": "lavaan",
        "group_var": group_var,
        "n_groups": n_groups,
        "items": items,
        "path": (paths[0] if len(paths) == 1 else None),
        "note": "输出为测量层级×结构路径的逐步比较（free vs constrained）；前端可按 level 分组展示并导出。",
    }
    return out


def lavaan_invariance_series(
    *,
    data_df,
    lavaan_syntax: str,
    group_var: str,
    missing: str = "fiml",
    top_note: str | None = None,
) -> dict[str, Any]:
    """
    多群组不变性检验（lavaan）
    输出：configural / metric / scalar / strict 的拟合度 + 嵌套对比（Δχ²/Δdf/ΔCFI）
    """
    _ensure_rpy2_conversion_context()

    import rpy2.robjects as ro
    from rpy2.robjects import pandas2ri
    from rpy2.robjects.packages import importr

    if group_var not in data_df.columns:
        return {"supported": True, "success": False, "message": f"分组变量不存在：{group_var}"}

    lavaan = importr("lavaan")

    with _pandas_rpy_conversion():
        r_df = pandas2ri.py2rpy(data_df)

    def _sanitize_sem_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
        """
        lavaan::sem 的参数名包含 fixed.x（带点）。
        在 rpy2 不同版本/调用方式下，fixed_x 可能不会被正确翻译为 fixed.x，导致 R 端报：unknown argument: fixed_x。
        这里统一“忽略 fixed_x”，回退使用 lavaan 默认 fixed.x=TRUE，保证 strict e2e 稳定。
        """
        for k in ("fixed_x", "fixedx", "fixedX"):
            kwargs.pop(k, None)

        # lavaan 的参数名是 group.equal（带点），rpy2 下 group_equal 不一定会被正确翻译。
        # 这里统一做兼容映射，避免 unknown argument: 'group_equal'。
        if "group_equal" in kwargs and "group.equal" not in kwargs:
            kwargs["group.equal"] = kwargs.pop("group_equal")
        return kwargs

    def _fit(label: str, group_equal: list[str] | None):
        kwargs = {
            "data": r_df,
            "group": group_var,
            "missing": missing,
        }
        if group_equal:
            # 注意：R 端参数名为 group.equal（带点）
            kwargs["group.equal"] = ro.StrVector(group_equal)
        fit = lavaan.sem(lavaan_syntax, **_sanitize_sem_kwargs(kwargs))
        m = _lavaan_fit_measures(fit)
        return {"model": label, "group_equal": group_equal or [], "fit": m, "_fit": fit}

    # 4 个层级
    configural = _fit("configural", None)
    metric = _fit("metric", ["loadings"])
    scalar = _fit("scalar", ["loadings", "intercepts"])
    strict = _fit("strict", ["loadings", "intercepts", "residuals"])

    models = [configural, metric, scalar, strict]

    def _delta(prev: float | None, cur: float | None) -> float | None:
        try:
            if prev is None or cur is None:
                return None
            return float(cur) - float(prev)
        except Exception:
            return None

    # 固定对比行（相邻）：configural→metric→scalar→strict
    comparison_pairs = [("configural", "metric"), ("metric", "scalar"), ("scalar", "strict")]
    comparisons: list[dict[str, Any]] = [
        {
            "from": a,
            "to": b,
            "ok": False,
            "note": None,
            "chi2_diff": None,
            "df_diff": None,
            "p_value": None,
            "delta_cfi": None,
            "delta_rmsea": None,
        }
        for a, b in comparison_pairs
    ]

    # 嵌套比较：用 lavTestLRT（configural vs metric vs scalar vs strict）
    lrt_error: str | None = None
    rows: list[dict[str, Any]] = []
    try:
        lrt = lavaan.lavTestLRT(configural["_fit"], metric["_fit"], scalar["_fit"], strict["_fit"])
        with _pandas_rpy_conversion():
            lrt_pd = pandas2ri.rpy2py(lrt)
        if lrt_pd is not None and not lrt_pd.empty:
            rows = lrt_pd.to_dict(orient="records")
    except Exception as e:
        lrt_error = f"lavTestLRT 失败：{str(e)}"

    # 填充 comparisons：始终固定 3 行；若 LRT 不可用则 ok=false + note
    # lavTestLRT 的行顺序通常与 models 对齐（第 0 行为第一个模型本身；diff 从第 1 行起）
    for i in range(3):
        prev = models[i]
        cur = models[i + 1]
        prev_name = prev["model"]
        cur_name = cur["model"]

        cfi_prev = (prev.get("fit") or {}).get("cfi")
        cfi_cur = (cur.get("fit") or {}).get("cfi")
        rmsea_prev = (prev.get("fit") or {}).get("rmsea")
        rmsea_cur = (cur.get("fit") or {}).get("rmsea")

        out = comparisons[i]
        out["from"] = prev_name
        out["to"] = cur_name
        out["delta_cfi"] = _delta(cfi_prev, cfi_cur)
        out["delta_rmsea"] = _delta(rmsea_prev, rmsea_cur)

        if lrt_error:
            out["ok"] = False
            out["note"] = lrt_error
            continue

        # rows 长度不足时也保持稳定输出
        if len(rows) <= i + 1:
            out["ok"] = False
            out["note"] = "lavTestLRT 结果不足（可能因未收敛/版本差异导致）"
            continue

        cur_row = rows[i + 1]
        out["chi2_diff"] = _lrt_to_float(_lrt_pick(cur_row, "chisq", "diff"))
        out["df_diff"] = _lrt_to_float(_lrt_pick(cur_row, "df", "diff"))
        out["p_value"] = _lrt_to_float(_lrt_pick(cur_row, "pr", "chisq"))
        out["ok"] = True
        out["note"] = None

    # 清理 _fit（不可 JSON 序列化）
    out_models = []
    for m in models:
        out_models.append({k: v for k, v in m.items() if k != "_fit"})

    return {
        "supported": True,
        "success": True,
        "task": "invariance_lavaan_series",
        "mode": "lavaan",
        "group_var": group_var,
        "models": out_models,
        "comparisons": comparisons,
        "note": top_note
        or "建议同时参考 ΔCFI（常用阈值：|ΔCFI|<0.01）与理论合理性；χ² 差异检验对样本量敏感。",
    }

