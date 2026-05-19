from __future__ import annotations

from typing import Any

from collections import defaultdict

import math
import re
from statistics import NormalDist

from celery import states
import numpy as np
import pandas as pd
from semopy import Model, calc_stats

from app.celery_app import celery_app
from app.tasks.task_error_format import celery_failure_meta
from app.services.data_parser import get_data
from app.services.lavaan_service import (
    check_lavaan_available,
    lavaan_invariance_series,
    lavaan_model_compare,
    lavaan_mga_structural_path_compare,
)


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        value = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def _pick_stat(stats_df: Any, key: str) -> float | None:
    try:
        if hasattr(stats_df, "loc"):
            if "Value" in getattr(stats_df, "index", []):
                return _to_float(stats_df.loc["Value", key])
            if hasattr(stats_df, "columns") and key in stats_df.columns and len(stats_df.index) > 0:
                return _to_float(stats_df.iloc[0][key])
        if isinstance(stats_df, dict) and key in stats_df:
            return _to_float(stats_df[key])
    except Exception:
        return None
    return None


def _format_metric(v: float | None) -> float | str:
    if v is None:
        return "-"
    return round(v, 4)


def _format_param(v: float | None) -> float | None:
    if v is None:
        return None
    return round(v, 6)


def _score_fit(chi2_df: float | None, rmsea: float | None, srmr: float | None, cfi: float | None, tli: float | None) -> str:
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
    return df.copy().dropna(axis=0, how="any")


def _obj(estimator: str, missing_strategy: str) -> str:
    if missing_strategy == "fiml":
        return "FIML"
    if estimator == "GLS":
        return "GLS"
    return "MLW"


def run_semopy_model_compare(
    *,
    data: pd.DataFrame,
    syntax_a: str,
    syntax_b: str,
    estimator: str,
    missing_strategy: str,
    label_a: str = "Model A",
    label_b: str = "Model B",
) -> dict[str, Any]:
    """
    semopy 版本的两模型对照（不保证 LRT）。
    目的：即使未启用 lavaan，也能返回稳定 schema 与 AIC/BIC（若可用），用于结果页/导出。
    """
    m_a = Model(syntax_a)
    m_a.fit(
        data,
        obj=_obj(estimator, missing_strategy),
        solver="SLSQP",
        options={"maxiter": 50},
    )
    s_a = calc_stats(m_a)

    m_b = Model(syntax_b)
    m_b.fit(
        data,
        obj=_obj(estimator, missing_strategy),
        solver="SLSQP",
        options={"maxiter": 50},
    )
    s_b = calc_stats(m_b)

    def _fit_from_stats(stats_df: Any) -> dict[str, Any]:
        chi2 = _pick_stat(stats_df, "chi2")
        dof = _pick_stat(stats_df, "DoF")
        cfi = _pick_stat(stats_df, "CFI")
        tli = _pick_stat(stats_df, "TLI")
        rmsea = _pick_stat(stats_df, "RMSEA")
        srmr = _pick_stat(stats_df, "SRMR")
        aic = _pick_stat(stats_df, "AIC")
        bic = _pick_stat(stats_df, "BIC")
        return {
            "chi2": chi2,
            "df": dof,
            "cfi": cfi,
            "tli": tli,
            "rmsea": rmsea,
            "srmr": srmr,
            "aic": aic,
            "bic": bic,
        }

    return {
        "supported": True,
        "mode": "semopy",
        "models": [
            {"label": label_a, "fit": _fit_from_stats(s_a)},
            {"label": label_b, "fit": _fit_from_stats(s_b)},
        ],
        "comparison": {
            "from": label_a,
            "to": label_b,
            "ok": False,
            "chi2_diff": None,
            "df_diff": None,
            "p_value": None,
            "note": "semopy 模式下未启用嵌套模型 LRT（建议启用 lavaan 以获得论文级 LRT）。",
        },
    }


def _rhs_tokens_for_interaction(rval: str) -> set[str]:
    """粗略拆分回归右侧，用于判断是否同时包含两个潜变量名。"""
    s = (rval or "").replace("*", " ").replace(":", " ")
    parts = re.split(r"\s*\+\s*", s)
    out: set[str] = set()
    for p in parts:
        t = p.strip()
        if t:
            out.add(t)
    return out


def _filter_latent_interaction_rows(
    estimates: list[dict[str, Any]],
    *,
    y: str,
    f1: str,
    f2: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    返回 (结局 y 上所有结构回归行, 同时涉及 f1/f2 的候选交互行)。
    semopy 输出中交互可能写作 F1:F2、乘积潜变量名等，此处做保守匹配。
    """
    structural: list[dict[str, Any]] = []
    matched: list[dict[str, Any]] = []
    for row in estimates:
        op = str(row.get("op") or "").strip()
        if op != "~":
            continue
        lval = str(row.get("lval") or "").strip()
        rval = str(row.get("rval") or "").strip()
        if lval != y:
            continue
        structural.append(row)
        if (f"{f1}:{f2}" in rval or f"{f2}:{f1}" in rval) or (f"{f1}*{f2}" in rval or f"{f2}*{f1}" in rval):
            matched.append(row)
            continue
        toks = _rhs_tokens_for_interaction(rval)
        if f1 in toks and f2 in toks:
            matched.append(row)
    return structural, matched


def _latent_interaction_preconditions(
    *,
    y: str,
    f1: str,
    f2: str,
    estimator: str,
    missing_strategy: str,
) -> dict[str, Any]:
    return {
        "input_constraints": {
            "required_fields": ["data_key", "lavaan_syntax", "y", "f1", "f2"],
            "distinct_roles": {"y": y, "f1": f1, "f2": f2, "all_distinct": len({y, f1, f2}) == 3},
            "estimator": estimator,
            "missing_strategy": missing_strategy,
            "supported_estimators": ["ML", "GLS"],
            "supported_missing_strategy": ["listwise", "fiml", "mean_impute"],
        },
        "environment_boundaries": {
            "engine": "semopy",
            "interaction_scope": "仅探测已显式写入语法的交互项，不自动生成 LMS/乘积指标",
            "lavaan_note": "启用 R+lavaan 时可做更完整潜交互复核；当前任务返回 semopy 筛选结果",
        },
        "runtime_checks": [
            "data_key 对应数据可读取",
            "缺失值处理后样本量 > 0",
            "语法可被 semopy 拟合并产出结构路径",
        ],
    }


def _extract_estimates(sem_model: Model) -> list[dict[str, Any]]:
    try:
        df = sem_model.inspect(std_est=True)
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        rows.append(
            {
                "lval": str(r.get("lval", "")),
                "op": str(r.get("op", "")),
                "rval": str(r.get("rval", "")),
                "estimate": _format_param(_to_float(r.get("Estimate"))),
                "est_std": _format_param(_to_float(r.get("Est. Std"))),
                "std_err": _format_param(_to_float(r.get("Std. Err"))),
                "z_value": _format_param(_to_float(r.get("z-value"))),
                "p_value": _format_param(_to_float(r.get("p-value"))),
            }
        )
    return rows


def _parse_effect_key(lval: str, op: str, rval: str) -> str:
    return f"{lval} {op} {rval}"


def _clean_sequence(values: list[Any] | tuple[Any, ...] | None) -> list[str]:
    if not values:
        return []
    seq: list[str] = []
    for raw in values:
        item = str(raw or "").strip()
        if item:
            seq.append(item)
    return seq


_EFFECT_VAR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_LABEL_FORBIDDEN = ';`$\n\r\x00'


def _parse_sequence_text(raw: str) -> list[str]:
    """将 sequence_text（逗号/空白/箭头分隔）解析为节点列表；仅支持路径序列，不支持表达式求值。"""
    s = str(raw or "").replace("→", " ").replace("->", " ")
    if any(ch in s for ch in ("+", "*", "/", "=", "(", ")")):
        raise ValueError("仅支持路径序列自定义效应（如 X -> M -> Y），不支持表达式运算")
    s = re.sub(r"[,;|]+", " ", s)
    return [p.strip() for p in s.split() if p.strip()]


def _validate_user_effect_label(label: str) -> None:
    if len(label) > 256:
        raise ValueError("效应 label 过长（最大 256 字符）")
    for ch in _LABEL_FORBIDDEN:
        if ch in label:
            raise ValueError("效应 label 含不允许字符（如分号、反引号、美元符或换行）")


def _identifiers_from_lavaan_syntax(syntax: str) -> set[str]:
    return set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", syntax or ""))


def _validate_effect_specs_allowlist(
    effect_specs: list[dict[str, Any]],
    *,
    lavaan_syntax: str,
    data_columns: list[str],
) -> None:
    """防注入：路径节点须为安全标识符，且出现在数据列名或 lavaan 语法中（可复现、可静态校验）。"""
    allowed = _identifiers_from_lavaan_syntax(lavaan_syntax) | {str(c) for c in data_columns}
    for spec in effect_specs:
        ul = spec.get("_user_label")
        if isinstance(ul, str) and ul.strip():
            _validate_user_effect_label(ul.strip())
        for node in spec.get("sequence") or []:
            n = str(node or "").strip()
            if not _EFFECT_VAR_RE.match(n):
                raise ValueError(f"路径节点命名非法：{n!r}（须字母/下划线开头，≤64 字符）")
            if n not in allowed:
                raise ValueError(f"路径节点 {n!r} 未出现在当前数据列或 lavaan 语法中")


def _normalize_effect_spec(item: dict[str, Any]) -> dict[str, Any] | None:
    sequence = _clean_sequence(item.get("sequence"))
    if not sequence:
        st = str(item.get("sequence_text") or "").strip()
        if st:
            sequence = _parse_sequence_text(st)
    if len(sequence) >= 3:
        x = sequence[0]
        y = sequence[-1]
        mediators = sequence[1:-1]
    else:
        x = str(item.get("x", "")).strip()
        m = str(item.get("m", "")).strip()
        y = str(item.get("y", "")).strip()
        if not (x and m and y):
            return None
        mediators = [m]
        sequence = [x, m, y]

    if len(sequence) < 3:
        return None
    if len(sequence) > 24:
        raise ValueError("路径过长（最多 24 个节点）")

    raw_label = item.get("label")
    user_label = str(raw_label).strip() if raw_label is not None and str(raw_label).strip() else None
    if user_label:
        _validate_user_effect_label(user_label)
    label = user_label or " → ".join(sequence)
    spec = {
        "x": x,
        "y": y,
        "mediators": mediators,
        "sequence": sequence,
        "label": label,
        "path_key": "->".join(sequence),
        "xy_key": f"{x}->{y}",
        "effect_type": "specific_indirect",
        "_user_label": user_label,
    }
    return spec


def _clean_covariates(
    covariates: list[Any] | None,
    *,
    exclude_vars: set[str],
) -> list[str]:
    covs_in = covariates or []
    covs: list[str] = []
    seen: set[str] = set()
    for raw in covs_in:
        s = str(raw or "").strip()
        if not s:
            continue
        if s in exclude_vars:
            continue
        if s not in seen:
            covs.append(s)
            seen.add(s)
    return covs


def _augment_lavaan_syntax_with_covariates(
    lavaan_syntax: str,
    *,
    outcomes: list[str],
    covariates: list[str],
) -> str:
    """
    最小实现：将 covariates 以主效应形式加入指定 outcome 的回归方程中。
    - 若已存在 `Y ~ ...`：追加 `+ C1 + C2`（避免重复）
    - 若不存在：追加新行 `Y ~ C1 + C2`
    约束：不解析复杂语法（例如多行续写/分组/约束），仅做稳健的“行级补丁”以保持现有风格与最小改动面。
    """
    covs = [str(c).strip() for c in (covariates or []) if str(c).strip()]
    outs = [str(o).strip() for o in (outcomes or []) if str(o).strip()]
    if not covs or not outs:
        return (lavaan_syntax or "").strip()

    # 仅处理结构回归：`lhs ~ rhs`；跳过 measurement `=~` 与 covariances `~~`
    lines_in = (lavaan_syntax or "").splitlines()
    lines = list(lines_in)
    by_lhs: dict[str, int] = {}
    rhs_terms_by_lhs: dict[str, list[str]] = {}

    for idx, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        if "=~" in line or "~~" in line:
            continue
        if "~" not in line:
            continue

        parts = line.split("~", 1)
        lhs = parts[0].strip()
        rhs = parts[1].strip()
        if not lhs or not rhs:
            continue
        if rhs == "1":  # intercept-only; allow augment
            rhs = ""

        terms = []
        for t in rhs.split("+"):
            s = t.strip()
            if s:
                terms.append(s)
        by_lhs[lhs] = idx
        rhs_terms_by_lhs[lhs] = terms

    appended_lines: list[str] = []
    for lhs in outs:
        existing_idx = by_lhs.get(lhs)
        if existing_idx is not None:
            existing_terms = rhs_terms_by_lhs.get(lhs, [])
            term_set = set(existing_terms)
            add_terms = [c for c in covs if c not in term_set]
            if not add_terms:
                continue
            merged = existing_terms + add_terms
            lines[existing_idx] = f"{lhs} ~ " + " + ".join(merged)
        else:
            appended_lines.append(f"{lhs} ~ " + " + ".join(covs))

    out_lines = [l.rstrip() for l in lines]
    if appended_lines:
        if out_lines and out_lines[-1].strip() != "":
            out_lines.append("")
        out_lines.extend(appended_lines)
    return "\n".join(out_lines).strip()


def _extract_path_map(sem_model: Model, use_standardized: bool) -> dict[str, float]:
    """
    返回路径系数字典：
    key: "lval op rval"
    val: estimate 或 est_std（若可用）
    """
    try:
        df = sem_model.inspect(std_est=True)
    except Exception:
        return {}

    mp: dict[str, float] = {}
    for _, r in df.iterrows():
        lval = str(r.get("lval", "")).strip()
        op = str(r.get("op", "")).strip()
        rval = str(r.get("rval", "")).strip()
        if not (lval and op and rval):
            continue

        if use_standardized:
            v = _to_float(r.get("Est. Std"))
            if v is None:
                v = _to_float(r.get("Estimate"))
        else:
            v = _to_float(r.get("Estimate"))

        if v is None:
            continue
        mp[_parse_effect_key(lval, op, rval)] = float(v)
    return mp


def _compute_indirect_effect(path_map: dict[str, float], sequence: list[str]) -> float | None:
    """
    通用间接效应：
    - sequence=["X","M","Y"] => (M ~ X) * (Y ~ M)
    - sequence=["X","M1","M2","Y"] => (M1 ~ X) * (M2 ~ M1) * (Y ~ M2)
    """
    seq = _clean_sequence(sequence)
    if len(seq) < 3:
        return None

    effect = 1.0
    for idx in range(len(seq) - 1):
        predictor = seq[idx]
        outcome = seq[idx + 1]
        coef = path_map.get(_parse_effect_key(outcome, "~", predictor))
        if coef is None:
            return None
        effect *= float(coef)
    return float(effect)


def _build_total_indirect_rows(
    effect_specs: list[dict[str, Any]],
    point_by_path: dict[str, float | None],
    boot_values: dict[str, list[float]],
    ci_level: float,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for spec in effect_specs:
        grouped.setdefault(spec["xy_key"], []).append(spec)

    rows: list[dict[str, Any]] = []
    for xy_key, specs in grouped.items():
        if len(specs) < 2:
            continue

        point_parts: list[float] = []
        for spec in specs:
            point = point_by_path.get(spec["path_key"])
            if point is None:
                point_parts = []
                break
            point_parts.append(float(point))
        if not point_parts:
            rows.append(
                {
                    "x": specs[0]["x"],
                    "y": specs[0]["y"],
                    "mediators": [],
                    "sequence": [specs[0]["x"], specs[0]["y"]],
                    "path_label": f'{specs[0]["x"]} → {specs[0]["y"]}',
                    "effect_type": "total_indirect",
                    "label": f'总间接效应：{specs[0]["x"]} → {specs[0]["y"]}',
                    "component_paths": [spec["label"] for spec in specs],
                    "indirect_point": None,
                    "ci": None,
                    "note": "至少一条特定间接效应无法计算，未生成总间接效应",
                }
            )
            continue

        valid_counts = [len(boot_values.get(spec["path_key"], [])) for spec in specs]
        min_len = min(valid_counts) if valid_counts else 0
        total_boot = []
        for idx in range(min_len):
            try:
                total_boot.append(sum(float(boot_values[spec["path_key"]][idx]) for spec in specs))
            except Exception:
                continue

        point = float(sum(point_parts))
        rows.append(
            {
                "x": specs[0]["x"],
                "y": specs[0]["y"],
                "mediators": [],
                "sequence": [specs[0]["x"], specs[0]["y"]],
                "path_label": f'{specs[0]["x"]} → {specs[0]["y"]}',
                "effect_type": "total_indirect",
                "label": f'总间接效应：{specs[0]["x"]} → {specs[0]["y"]}',
                "component_paths": [spec["label"] for spec in specs],
                "indirect_point": point,
                "ci": _bootstrap_ci(total_boot, point, ci_level),
                "note": f"由 {len(specs)} 条特定间接效应汇总",
            }
        )
    return rows


def _build_decomposition_rows(
    effect_specs: list[dict[str, Any]],
    point_by_path: dict[str, float | None],
    boot_values: dict[str, list[float]],
    boot_direct_by_xy: dict[str, list[float]],
    ci_level: float,
) -> list[dict[str, Any]]:
    """
    对同一对 (X,Y) 输出直接效应与总效应（总效应 = 直接 + 所有特定间接之和）。
    与总间接（多条路径之和）在数值上：总效应 = 直接 + 总间接（当总间接可算时）。
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for spec in effect_specs:
        grouped.setdefault(spec["xy_key"], []).append(spec)

    rows: list[dict[str, Any]] = []
    for _xy_key, specs in grouped.items():
        if not specs:
            continue
        x, y = specs[0]["x"], specs[0]["y"]
        dk = _parse_effect_key(y, "~", x)
        direct_pt = point_by_path.get(dk)

        parts: list[float] = []
        for spec in specs:
            pt = point_by_path.get(spec["path_key"])
            if pt is None or not np.isfinite(pt):
                parts = []
                break
            parts.append(float(pt))
        sum_indirect = float(sum(parts)) if parts else None

        total_pt: float | None = None
        total_note: str | None = None
        if sum_indirect is not None and direct_pt is not None and np.isfinite(direct_pt):
            total_pt = float(direct_pt) + float(sum_indirect)
        elif sum_indirect is not None:
            total_pt = float(sum_indirect)
            if direct_pt is None or not np.isfinite(direct_pt):
                total_note = "未估计 X→Y 直接路径：总效应暂等于特定间接效应之和（非完整 c′+Σab）"
        elif direct_pt is not None and np.isfinite(direct_pt):
            total_pt = float(direct_pt)

        lengths = [len(boot_values.get(s["path_key"], [])) for s in specs]
        min_ind = min(lengths) if lengths else 0
        indirect_boot: list[float] = []
        for i in range(min_ind):
            try:
                indirect_boot.append(sum(float(boot_values[s["path_key"]][i]) for s in specs))
            except Exception:
                continue

        dlist = boot_direct_by_xy.get(specs[0]["xy_key"], [])
        total_boot: list[float] = []
        if sum_indirect is not None and (direct_pt is None or not np.isfinite(direct_pt)):
            total_boot = list(indirect_boot)
        elif sum_indirect is not None and direct_pt is not None and np.isfinite(direct_pt):
            min_tot = min(len(indirect_boot), len(dlist))
            for i in range(min_tot):
                di = dlist[i]
                ib = indirect_boot[i]
                if np.isfinite(di) and np.isfinite(ib):
                    total_boot.append(float(di) + float(ib))

        direct_ci = None
        if direct_pt is not None and np.isfinite(direct_pt):
            dvals = [v for v in dlist if np.isfinite(v)]
            direct_ci = _bootstrap_ci(dvals, float(direct_pt), ci_level)

        total_ci = None
        if total_pt is not None and np.isfinite(total_pt) and total_boot:
            total_ci = _bootstrap_ci(total_boot, float(total_pt), ci_level)

        rows.append(
            {
                "x": x,
                "y": y,
                "mediators": [],
                "sequence": [x, y],
                "path_label": f"{x} → {y}（直接）",
                "effect_type": "direct_effect",
                "label": f"直接效应：{x} → {y}",
                "component_paths": [],
                "indirect_point": float(direct_pt) if direct_pt is not None and np.isfinite(direct_pt) else None,
                "ci": direct_ci,
                "note": None if direct_pt is not None and np.isfinite(direct_pt) else "缺少 Y ~ X 路径系数（直接效应）",
            }
        )
        rows.append(
            {
                "x": x,
                "y": y,
                "mediators": [],
                "sequence": [x, y],
                "path_label": f"{x} → {y}（总效应）",
                "effect_type": "total_effect",
                "label": f"总效应：{x} → {y}（直接 + 特定间接之和）",
                "component_paths": [s["label"] for s in specs],
                "indirect_point": total_pt,
                "ci": total_ci,
                "note": (
                    total_note
                    if total_pt is not None and np.isfinite(total_pt)
                    else "无法汇总总效应（缺少间接效应分量）"
                ),
            }
        )
    return rows


def _bootstrap_ci(values: list[float], point: float, ci_level: float) -> dict[str, Any]:
    """
    返回 percentile CI + bias-corrected (BC, a=0) CI
    """
    vals = np.array([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    if vals.size < 20:
        return {
            "n_boot_valid": int(vals.size),
            "ci_level": float(ci_level),
            "percentile": None,
            "bc": None,
        }

    alpha = (1.0 - float(ci_level)) / 2.0
    lo_p, hi_p = np.quantile(vals, [alpha, 1 - alpha]).tolist()

    # Bias-correction (BC): z0 based on proportion of bootstrap estimates less than point estimate
    prop = float(np.mean(vals < float(point)))
    prop = min(max(prop, 1e-6), 1 - 1e-6)
    nd = NormalDist()
    z0 = nd.inv_cdf(prop)

    def _adj(a: float) -> float:
        z = nd.inv_cdf(a)
        return nd.cdf(2 * z0 + z)

    lo_a = _adj(alpha)
    hi_a = _adj(1 - alpha)
    lo_bc, hi_bc = np.quantile(vals, [lo_a, hi_a]).tolist()

    return {
        "n_boot_valid": int(vals.size),
        "ci_level": float(ci_level),
        "percentile": {"lo": float(lo_p), "hi": float(hi_p)},
        "bc": {"lo": float(lo_bc), "hi": float(hi_bc), "note": "BC (bias-corrected) with a=0; BCa acceleration not implemented yet"},
    }


def _ols_fit(design: np.ndarray, y: np.ndarray, term_names: list[str]) -> list[dict[str, Any]]:
    xtx = design.T @ design
    xtx_inv = np.linalg.pinv(xtx)
    beta = xtx_inv @ design.T @ y
    fitted = design @ beta
    resid = y - fitted
    n = len(y)
    p = design.shape[1]
    dof = max(n - p, 1)
    sigma2 = float((resid.T @ resid) / dof)
    cov = sigma2 * xtx_inv
    se = np.sqrt(np.clip(np.diag(cov), a_min=0.0, a_max=None))
    nd = NormalDist()

    rows: list[dict[str, Any]] = []
    for idx, name in enumerate(term_names):
        estimate = float(beta[idx])
        std_err = float(se[idx]) if np.isfinite(se[idx]) else None
        if std_err and std_err > 0:
            z_value = estimate / std_err
            p_value = 2 * (1 - nd.cdf(abs(z_value)))
        else:
            z_value = None
            p_value = None
        rows.append(
            {
                "term": name,
                "estimate": _format_param(estimate),
                "std_err": _format_param(std_err),
                "z_value": _format_param(z_value),
                "p_value": _format_param(p_value),
            }
        )
    return rows


def run_observed_moderation_analysis(
    df: pd.DataFrame,
    x: str,
    w: str,
    y: str,
    moderator_type: str = "continuous",
    covariates: list[str] | None = None,
) -> dict[str, Any]:
    covs_in = covariates or []
    covs: list[str] = []
    seen = set()
    for raw in covs_in:
        s = str(raw or "").strip()
        if not s:
            continue
        if s in (x, w, y):
            continue
        if s not in seen:
            covs.append(s)
            seen.add(s)

    required = [x, w, y]
    cols = required + covs
    missing_cols = [col for col in cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"变量不存在：{', '.join(missing_cols)}")

    data = df[cols].copy().dropna(axis=0, how="any")
    if data.empty:
        raise ValueError("调节分析在缺失值处理后无可用样本")

    x_vec = pd.to_numeric(data[x], errors="coerce")
    y_vec = pd.to_numeric(data[y], errors="coerce")
    data = data.assign(__x__=x_vec, __y__=y_vec)
    for i, c in enumerate(covs):
        data[f"__c{i}__"] = pd.to_numeric(data[c], errors="coerce")
    drop_cols = ["__x__", "__y__"] + [f"__c{i}__" for i in range(len(covs))]
    data = data.dropna(subset=drop_cols)
    if data.empty:
        if covs:
            raise ValueError("X / Y / 协变量需为可计算的数值变量（建议检查协变量是否为数值型）")
        raise ValueError("X / Y 需为可计算的数值变量")

    moderator_kind = (moderator_type or "continuous").strip().lower()

    if moderator_kind == "categorical":
        data["__w__"] = data[w].astype(str).str.strip()
        data = data[data["__w__"] != ""]
        groups = sorted(data["__w__"].unique().tolist())
        if len(groups) < 2:
            raise ValueError("分类调节变量至少需要 2 个有效类别")

        reference_group = groups[0]
        dummy_groups = groups[1:]
        x_arr = data["__x__"].to_numpy(dtype=float)
        design_cols = [np.ones(len(data)), x_arr]
        term_names = ["Intercept", x]

        for group in dummy_groups:
            dummy = (data["__w__"] == group).astype(float).to_numpy()
            design_cols.append(dummy)
            term_names.append(f"{w}[{group}]")

        for i, c in enumerate(covs):
            design_cols.append(data[f"__c{i}__"].to_numpy(dtype=float))
            term_names.append(c)

        for group in dummy_groups:
            dummy = (data["__w__"] == group).astype(float).to_numpy()
            design_cols.append(x_arr * dummy)
            term_names.append(f"{x}×{w}[{group}]")

        design = np.column_stack(design_cols)
        y_arr = data["__y__"].to_numpy(dtype=float)
        coefficients = _ols_fit(design, y_arr, term_names)
        coef_map = {row["term"]: float(row["estimate"]) for row in coefficients if row["estimate"] is not None}
        base_slope = coef_map.get(x, 0.0)
        simple_slopes = [{"group": reference_group, "slope_x": _format_param(base_slope), "note": "参考组"}]
        for group in dummy_groups:
            slope = base_slope + coef_map.get(f"{x}×{w}[{group}]", 0.0)
            simple_slopes.append({"group": group, "slope_x": _format_param(slope), "note": f"相对参考组 {reference_group}"})

        interaction_terms = [row for row in coefficients if "×" in row["term"]]
        interaction = {
            "term": " ; ".join(row["term"] for row in interaction_terms),
            "estimates": interaction_terms,
        }
        moderator_meta = {
            "name": w,
            "type": "categorical",
            "reference_group": reference_group,
            "groups": groups,
        }
    else:
        data["__w_num__"] = pd.to_numeric(data[w], errors="coerce")
        data = data.dropna(subset=["__w_num__"])
        if data.empty:
            raise ValueError("连续调节变量需为可计算的数值变量")

        x_arr = data["__x__"].to_numpy(dtype=float)
        w_arr = data["__w_num__"].to_numpy(dtype=float)
        design_cols = [np.ones(len(data)), x_arr, w_arr, x_arr * w_arr]
        y_arr = data["__y__"].to_numpy(dtype=float)
        term_names = ["Intercept", x, w, f"{x}×{w}"]
        for i, c in enumerate(covs):
            design_cols.append(data[f"__c{i}__"].to_numpy(dtype=float))
            term_names.append(c)
        design = np.column_stack(design_cols)
        coefficients = _ols_fit(design, y_arr, term_names)
        coef_map = {row["term"]: float(row["estimate"]) for row in coefficients if row["estimate"] is not None}
        w_mean = float(np.mean(w_arr))
        w_sd = float(np.std(w_arr, ddof=0))
        simple_slopes = []
        for label, value in [
            ("低水平 (-1 SD)", w_mean - w_sd),
            ("均值", w_mean),
            ("高水平 (+1 SD)", w_mean + w_sd),
        ]:
            slope = coef_map.get(x, 0.0) + coef_map.get(f"{x}×{w}", 0.0) * value
            simple_slopes.append({"group": label, "w_value": _format_param(value), "slope_x": _format_param(slope)})

        interaction = next((row for row in coefficients if row["term"] == f"{x}×{w}"), None) or {
            "term": f"{x}×{w}",
            "estimate": None,
        }
        moderator_meta = {
            "name": w,
            "type": "continuous",
            "reference_group": None,
            "groups": [],
        }

    return {
        "success": True,
        "n_used": int(len(data)),
        "outcome": y,
        "predictor": x,
        "moderator": moderator_meta,
        "covariates": covs,
        "coefficients": coefficients,
        "interaction": interaction,
        "simple_slopes": simple_slopes,
    }


def _ols_beta_only(design: np.ndarray, y: np.ndarray) -> np.ndarray:
    xtx = design.T @ design
    xtx_inv = np.linalg.pinv(xtx)
    return xtx_inv @ design.T @ y


def _fit_model7_boot_indirects(
    data: pd.DataFrame,
    x: str,
    m: str,
    y: str,
    w: str,
    covs: list[str],
) -> tuple[float, float, float, float] | None:
    """
    Hayes PROCESS Model 7（观测变量、连续 W）：
      M ~ 1 + X + W + X*W + covs
      Y ~ 1 + M + X + W + covs
    条件间接：(β_X→M + β_XW→M · w) × β_M→Y
    返回 (ind_-1SD, ind_mean, ind_+1SD, diff_+1SD_minus_-1SD)
    """
    n = len(data)
    if n < 8:
        return None
    xv = data[x].to_numpy(dtype=float)
    mv = data[m].to_numpy(dtype=float)
    yv = data[y].to_numpy(dtype=float)
    wv = data[w].to_numpy(dtype=float)
    xw = xv * wv
    cols_m = [np.ones(n), xv, wv, xw]
    cols_y = [np.ones(n), mv, xv, wv]
    for c in covs:
        cols_m.append(data[c].to_numpy(dtype=float))
        cols_y.append(data[c].to_numpy(dtype=float))
    design_m = np.column_stack(cols_m)
    design_y = np.column_stack(cols_y)
    try:
        beta_m = _ols_beta_only(design_m, mv)
        beta_y = _ols_beta_only(design_y, yv)
    except Exception:
        return None
    if beta_m.size < 4 or beta_y.size < 2:
        return None
    a1 = float(beta_m[1])
    a3 = float(beta_m[3])
    b = float(beta_y[1])
    if not (math.isfinite(a1) and math.isfinite(a3) and math.isfinite(b)):
        return None
    w_mean = float(np.mean(wv))
    w_sd = float(np.std(wv, ddof=0))
    if not math.isfinite(w_sd) or w_sd < 1e-12:
        w_sd = 1.0
    w_lo = w_mean - w_sd
    w_hi = w_mean + w_sd

    def ind(ww: float) -> float:
        return (a1 + a3 * ww) * b

    d0 = ind(w_lo)
    d1 = ind(w_mean)
    d2 = ind(w_hi)
    if not all(math.isfinite(v) for v in (d0, d1, d2)):
        return None
    return (d0, d1, d2, float(d2 - d0))


def _fit_model7_categorical_boot_indirects(
    data: pd.DataFrame,
    x: str,
    m: str,
    y: str,
    w_col: str,
    groups: list[str],
    dummy_groups: list[str],
    covs: list[str],
) -> tuple[list[float], float] | None:
    """
    Hayes Model 7 + 分类 W：虚拟编码（参考组为排序后首类），
    M ~ X + ΣD + X·D + covs；Y ~ M + X + ΣD + covs。
    返回（各类别条件间接效应列表[与 groups 对齐]，末类 vs 参考组之差）。
    """
    n = len(data)
    nd = len(dummy_groups)
    nc = len(covs)
    p_m = 2 + nd + nc + nd
    if n < max(p_m + 2, 8):
        return None
    xv = data[x].to_numpy(dtype=float)
    mv = data[m].to_numpy(dtype=float)
    yv = data[y].to_numpy(dtype=float)
    wstr = data[w_col].astype(str)

    cols_m = [np.ones(n), xv]
    for g in dummy_groups:
        cols_m.append((wstr == g).astype(float).to_numpy())
    for c in covs:
        cols_m.append(data[c].to_numpy(dtype=float))
    for g in dummy_groups:
        cols_m.append(xv * (wstr == g).astype(float).to_numpy())

    cols_y = [np.ones(n), mv, xv]
    for g in dummy_groups:
        cols_y.append((wstr == g).astype(float).to_numpy())
    for c in covs:
        cols_y.append(data[c].to_numpy(dtype=float))

    design_m = np.column_stack(cols_m)
    design_y = np.column_stack(cols_y)
    try:
        beta_m = _ols_beta_only(design_m, mv)
        beta_y = _ols_beta_only(design_y, yv)
    except Exception:
        return None
    if beta_m.size < p_m or beta_y.size < 3 + nd + nc:
        return None
    b = float(beta_y[1])
    a_ref = float(beta_m[1])
    if not (math.isfinite(b) and math.isfinite(a_ref)):
        return None
    base_xw = 2 + nd + nc
    indirects: list[float] = [a_ref * b]
    for j in range(nd):
        aj = a_ref + float(beta_m[base_xw + j])
        indirects.append(aj * b)
    if not all(math.isfinite(v) for v in indirects):
        return None
    diff = indirects[-1] - indirects[0]
    if not math.isfinite(diff):
        return None
    return (indirects, float(diff))


def run_observed_moderated_mediation_model7_categorical(
    df: pd.DataFrame,
    x: str,
    m: str,
    y: str,
    w: str,
    *,
    covariates: list[str] | None = None,
    n_boot: int = 2000,
    ci_level: float = 0.95,
    seed: int | None = None,
    max_categories: int = 8,
) -> dict[str, Any]:
    """
    Model 7 + 分类调节 W：组内条件间接 + Bootstrap；指数 = 排序末类 vs 参考组（首类）条件间接之差。
    """
    covs_in = covariates or []
    covs: list[str] = []
    seen: set[str] = set()
    for raw in covs_in:
        s = str(raw or "").strip()
        if not s:
            continue
        if s in (x, m, y, w):
            continue
        if s not in seen:
            covs.append(s)
            seen.add(s)

    required = [x, m, y, w]
    for c in covs:
        required.append(c)
    missing_cols = [col for col in required if col not in df.columns]
    if missing_cols:
        raise ValueError(f"变量不存在：{', '.join(missing_cols)}")

    data = df[required].copy().dropna(axis=0, how="any")
    if data.empty:
        raise ValueError("有调节的中介在缺失值处理后无可用样本")

    data[w] = data[w].astype(str).str.strip()
    data = data[data[w] != ""]
    for col in (x, m, y):
        data[col] = pd.to_numeric(data[col], errors="coerce")
    for c in covs:
        data[c] = pd.to_numeric(data[c], errors="coerce")
    data = data.dropna(axis=0, how="any")
    if data.empty:
        raise ValueError("X / M / Y / 协变量需为可计算的数值变量")

    groups = sorted(data[w].unique().tolist())
    if len(groups) < 2:
        raise ValueError("分类调节变量 W 至少需要 2 个有效类别")
    if len(groups) > max_categories:
        raise ValueError(f"分类调节变量类别数过多（>{max_categories}），请先合并类别或改用数值编码")

    dummy_groups = groups[1:]
    if len(data) < 8:
        raise ValueError("有效样本量过小，无法估计有调节的中介模型")

    if n_boot < 200:
        n_boot = 200
    if n_boot > 5000:
        n_boot = 5000

    rng = np.random.default_rng(int(seed) if seed is not None else None)
    n = len(data)

    xv = data[x].to_numpy(dtype=float)
    mv = data[m].to_numpy(dtype=float)
    yv = data[y].to_numpy(dtype=float)
    wstr = data[w].astype(str)

    cols_m = [np.ones(n), xv]
    term_m = ["Intercept", x]
    for g in dummy_groups:
        cols_m.append((wstr == g).astype(float).to_numpy())
        term_m.append(f"{w}[{g}]")
    for c in covs:
        cols_m.append(data[c].to_numpy(dtype=float))
        term_m.append(c)
    for g in dummy_groups:
        cols_m.append(xv * (wstr == g).astype(float).to_numpy())
        term_m.append(f"{x}×{w}[{g}]")

    cols_y = [np.ones(n), mv, xv]
    term_y = ["Intercept", m, x]
    for g in dummy_groups:
        cols_y.append((wstr == g).astype(float).to_numpy())
        term_y.append(f"{w}[{g}]")
    for c in covs:
        cols_y.append(data[c].to_numpy(dtype=float))
        term_y.append(c)

    design_m = np.column_stack(cols_m)
    design_y = np.column_stack(cols_y)
    first_stage = _ols_fit(design_m, mv, term_m)
    second_stage = _ols_fit(design_y, yv, term_y)

    boot0 = _fit_model7_categorical_boot_indirects(data, x, m, y, w, groups, dummy_groups, covs)
    if boot0 is None:
        raise ValueError("模型系数无法估计（可能共线或数据不足）")
    point_list, p_diff = boot0

    nd = len(dummy_groups)
    boots_per_group: list[list[float]] = [[] for _ in groups]
    boots_diff: list[float] = []
    failures = 0

    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n, endpoint=False)
        sample = data.iloc[idx]
        r = _fit_model7_categorical_boot_indirects(sample, x, m, y, w, groups, dummy_groups, covs)
        if r is None:
            failures += 1
            continue
        inds, df_ = r
        for i, val in enumerate(inds):
            boots_per_group[i].append(val)
        boots_diff.append(df_)

    conditional: list[dict[str, Any]] = []
    for i, g in enumerate(groups):
        note = "参考组（虚拟编码基准）" if i == 0 else f"相对参考组 {groups[0]}"
        conditional.append(
            {
                "label": f"组别：{g}",
                "w_value": g,
                "note": note,
                "indirect_point": _format_param(float(point_list[i])),
                "ci": _bootstrap_ci(boots_per_group[i], float(point_list[i]), ci_level),
            }
        )

    index_row = {
        "contrast": f"{groups[-1]} vs 参考组 {groups[0]}（条件间接效应之差）",
        "point": _format_param(float(p_diff)),
        "ci": _bootstrap_ci(boots_diff, float(p_diff), ci_level),
    }

    return {
        "success": True,
        "task": "moderated_mediation",
        "model": "hayes_process_7_categorical",
        "note": (
            "观测变量、分类 W（虚拟编码）；W 调节 X→M；Y ~ M+X+W 主效应。"
            " 指数对比排序末类与参考组；类别顺序按字符串排序，请确保编码符合研究假设。"
        ),
        "x": x,
        "m": m,
        "y": y,
        "w": w,
        "w_type": "categorical",
        "moderator_meta": {
            "name": w,
            "type": "categorical",
            "reference_group": groups[0],
            "groups": groups,
        },
        "covariates": covs,
        "n_used": int(n),
        "n_boot": int(n_boot),
        "ci_level": float(ci_level),
        "failures": int(failures),
        "first_stage": {"outcome": m, "equation": f"{m} ~ {x} + W(dummies) + {x}:W + covs", "coefficients": first_stage},
        "second_stage": {"outcome": y, "equation": f"{y} ~ {m} + {x} + W(dummies) + covs", "coefficients": second_stage},
        "conditional_indirect": conditional,
        "index_moderated_mediation": index_row,
    }


def _fit_model14_boot_indirects(
    data: pd.DataFrame,
    x: str,
    m: str,
    y: str,
    w: str,
    covs: list[str],
) -> tuple[float, float, float, float] | None:
    """
    Hayes PROCESS Model 14（连续 W）：M ~ X + covs；Y ~ M + X + W + M*W + covs。
    条件间接：a · (b_M + b_MW · w)，其中 a 为 X→M。
    """
    n = len(data)
    nc = len(covs)
    if n < max(10 + nc, 8):
        return None
    xv = data[x].to_numpy(dtype=float)
    mv = data[m].to_numpy(dtype=float)
    yv = data[y].to_numpy(dtype=float)
    wv = data[w].to_numpy(dtype=float)
    mw = mv * wv
    cols_m = [np.ones(n), xv]
    for c in covs:
        cols_m.append(data[c].to_numpy(dtype=float))
    cols_y = [np.ones(n), mv, xv, wv, mw]
    for c in covs:
        cols_y.append(data[c].to_numpy(dtype=float))
    design_m = np.column_stack(cols_m)
    design_y = np.column_stack(cols_y)
    try:
        beta_m = _ols_beta_only(design_m, mv)
        beta_y = _ols_beta_only(design_y, yv)
    except Exception:
        return None
    need_m = 2 + nc
    need_y = 5 + nc
    if beta_m.size < need_m or beta_y.size < need_y:
        return None
    a1 = float(beta_m[1])
    b_m = float(beta_y[1])
    b_mw = float(beta_y[4])
    if not (math.isfinite(a1) and math.isfinite(b_m) and math.isfinite(b_mw)):
        return None

    w_mean = float(np.mean(wv))
    w_sd = float(np.std(wv, ddof=0))
    if not math.isfinite(w_sd) or w_sd < 1e-12:
        w_sd = 1.0
    w_lo = w_mean - w_sd
    w_mid = w_mean
    w_hi = w_mean + w_sd

    def ind(ww: float) -> float:
        return a1 * (b_m + b_mw * ww)

    d0 = ind(w_lo)
    d1 = ind(w_mid)
    d2 = ind(w_hi)
    if not all(math.isfinite(v) for v in (d0, d1, d2)):
        return None
    return (d0, d1, d2, float(d2 - d0))


def run_observed_moderated_mediation_model14(
    df: pd.DataFrame,
    x: str,
    m: str,
    y: str,
    w: str,
    *,
    covariates: list[str] | None = None,
    n_boot: int = 2000,
    ci_level: float = 0.95,
    seed: int | None = None,
) -> dict[str, Any]:
    """
    有调节的中介（MVP）：Hayes PROCESS Model 14，W 调节 M→Y；第一阶段仅 X→M。
    仅支持连续型 W。
    """
    covs_in = covariates or []
    covs: list[str] = []
    seen: set[str] = set()
    for raw in covs_in:
        s = str(raw or "").strip()
        if not s:
            continue
        if s in (x, m, y, w):
            continue
        if s not in seen:
            covs.append(s)
            seen.add(s)

    required = [x, m, y, w]
    for c in covs:
        required.append(c)
    missing_cols = [col for col in required if col not in df.columns]
    if missing_cols:
        raise ValueError(f"变量不存在：{', '.join(missing_cols)}")

    data = df[required].copy().dropna(axis=0, how="any")
    if data.empty:
        raise ValueError("有调节的中介在缺失值处理后无可用样本")

    for col in required:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.dropna(axis=0, how="any")
    if len(data) < 8:
        raise ValueError("有效样本量过小，无法估计有调节的中介模型")

    if n_boot < 200:
        n_boot = 200
    if n_boot > 5000:
        n_boot = 5000

    rng = np.random.default_rng(int(seed) if seed is not None else None)
    n = len(data)

    xv = data[x].to_numpy(dtype=float)
    mv = data[m].to_numpy(dtype=float)
    yv = data[y].to_numpy(dtype=float)
    wv = data[w].to_numpy(dtype=float)
    mw = mv * wv

    cols_m = [np.ones(n), xv]
    term_m = ["Intercept", x]
    for c in covs:
        cols_m.append(data[c].to_numpy(dtype=float))
        term_m.append(c)
    cols_y = [np.ones(n), mv, xv, wv, mw]
    term_y = ["Intercept", m, x, w, f"{m}×{w}"]
    for c in covs:
        cols_y.append(data[c].to_numpy(dtype=float))
        term_y.append(c)

    design_m = np.column_stack(cols_m)
    design_y = np.column_stack(cols_y)
    first_stage = _ols_fit(design_m, mv, term_m)
    second_stage = _ols_fit(design_y, yv, term_y)

    boot_out = _fit_model14_boot_indirects(data, x, m, y, w, covs)
    if boot_out is None:
        raise ValueError("模型系数无法估计（可能共线或数据不足）")
    p_lo, p_mid, p_hi, p_diff = boot_out

    boots_lo: list[float] = []
    boots_mid: list[float] = []
    boots_hi: list[float] = []
    boots_diff: list[float] = []
    failures = 0

    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n, endpoint=False)
        sample = data.iloc[idx]
        r = _fit_model14_boot_indirects(sample, x, m, y, w, covs)
        if r is None:
            failures += 1
            continue
        boots_lo.append(r[0])
        boots_mid.append(r[1])
        boots_hi.append(r[2])
        boots_diff.append(r[3])

    level_specs = [
        ("低水平 (-1 SD)", float(np.mean(wv) - np.std(wv, ddof=0)), p_lo, boots_lo),
        ("均值", float(np.mean(wv)), p_mid, boots_mid),
        ("高水平 (+1 SD)", float(np.mean(wv) + np.std(wv, ddof=0)), p_hi, boots_hi),
    ]

    conditional: list[dict[str, Any]] = []
    for label, w_val, point, bvals in level_specs:
        conditional.append(
            {
                "label": label,
                "w_value": _format_param(float(w_val)),
                "indirect_point": _format_param(float(point)),
                "ci": _bootstrap_ci(bvals, float(point), ci_level),
            }
        )

    index_row = {
        "contrast": "+1 SD vs -1 SD（条件间接效应之差，Model 14）",
        "point": _format_param(float(p_diff)),
        "ci": _bootstrap_ci(boots_diff, float(p_diff), ci_level),
    }

    return {
        "success": True,
        "task": "moderated_mediation",
        "model": "hayes_process_14",
        "note": "观测变量、连续 W；W 调节 M→Y；M ~ X+covs；Y ~ M+X+W+M:W+covs。条件间接 = a·(b_M+b_MW·W)。",
        "x": x,
        "m": m,
        "y": y,
        "w": w,
        "w_type": "continuous",
        "covariates": covs,
        "n_used": int(n),
        "n_boot": int(n_boot),
        "ci_level": float(ci_level),
        "failures": int(failures),
        "first_stage": {"outcome": m, "equation": f"{m} ~ {x} + covs", "coefficients": first_stage},
        "second_stage": {"outcome": y, "equation": f"{y} ~ {m} + {x} + {w} + {m}:{w} + covs", "coefficients": second_stage},
        "conditional_indirect": conditional,
        "index_moderated_mediation": index_row,
    }


def run_observed_moderated_mediation_model7(
    df: pd.DataFrame,
    x: str,
    m: str,
    y: str,
    w: str,
    *,
    covariates: list[str] | None = None,
    n_boot: int = 2000,
    ci_level: float = 0.95,
    seed: int | None = None,
    w_type: str = "continuous",
) -> dict[str, Any]:
    """
    有调节的中介（MVP）：Hayes PROCESS Model 7，W 调节 X→M；第二阶段不含 M×W。
    w_type=continuous：连续 W，条件间接在 W 的均值与 ±1SD。
    w_type=categorical：分类 W（虚拟编码），见 run_observed_moderated_mediation_model7_categorical。
    """
    wt = (w_type or "continuous").strip().lower()
    if wt == "categorical":
        return run_observed_moderated_mediation_model7_categorical(
            df,
            x,
            m,
            y,
            w,
            covariates=covariates,
            n_boot=n_boot,
            ci_level=ci_level,
            seed=seed,
        )

    covs_in = covariates or []
    covs: list[str] = []
    seen: set[str] = set()
    for raw in covs_in:
        s = str(raw or "").strip()
        if not s:
            continue
        if s in (x, m, y, w):
            continue
        if s not in seen:
            covs.append(s)
            seen.add(s)

    required = [x, m, y, w]
    for c in covs:
        required.append(c)
    missing_cols = [col for col in required if col not in df.columns]
    if missing_cols:
        raise ValueError(f"变量不存在：{', '.join(missing_cols)}")

    data = df[required].copy().dropna(axis=0, how="any")
    if data.empty:
        raise ValueError("有调节的中介在缺失值处理后无可用样本")

    for col in required:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.dropna(axis=0, how="any")
    if len(data) < 8:
        raise ValueError("有效样本量过小，无法估计有调节的中介模型")

    if n_boot < 200:
        n_boot = 200
    if n_boot > 5000:
        n_boot = 5000

    rng = np.random.default_rng(int(seed) if seed is not None else None)
    n = len(data)

    # 点估计 + 系数表
    xv = data[x].to_numpy(dtype=float)
    mv = data[m].to_numpy(dtype=float)
    yv = data[y].to_numpy(dtype=float)
    wv = data[w].to_numpy(dtype=float)
    xw = xv * wv
    cols_m = [np.ones(n), xv, wv, xw]
    cols_y = [np.ones(n), mv, xv, wv]
    for c in covs:
        cols_m.append(data[c].to_numpy(dtype=float))
        cols_y.append(data[c].to_numpy(dtype=float))
    design_m = np.column_stack(cols_m)
    design_y = np.column_stack(cols_y)
    term_m = ["Intercept", x, w, f"{x}×{w}"] + covs
    term_y = ["Intercept", m, x, w] + covs
    first_stage = _ols_fit(design_m, mv, term_m)
    second_stage = _ols_fit(design_y, yv, term_y)

    boot_out = _fit_model7_boot_indirects(data, x, m, y, w, covs)
    if boot_out is None:
        raise ValueError("模型系数无法估计（可能共线或数据不足）")
    p_lo, p_mid, p_hi, p_diff = boot_out

    boots_lo: list[float] = []
    boots_mid: list[float] = []
    boots_hi: list[float] = []
    boots_diff: list[float] = []
    failures = 0

    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n, endpoint=False)
        sample = data.iloc[idx]
        r = _fit_model7_boot_indirects(sample, x, m, y, w, covs)
        if r is None:
            failures += 1
            continue
        boots_lo.append(r[0])
        boots_mid.append(r[1])
        boots_hi.append(r[2])
        boots_diff.append(r[3])

    level_specs = [
        ("低水平 (-1 SD)", float(np.mean(wv) - np.std(wv, ddof=0)), p_lo, boots_lo),
        ("均值", float(np.mean(wv)), p_mid, boots_mid),
        ("高水平 (+1 SD)", float(np.mean(wv) + np.std(wv, ddof=0)), p_hi, boots_hi),
    ]

    conditional: list[dict[str, Any]] = []
    for label, w_val, point, bvals in level_specs:
        conditional.append(
            {
                "label": label,
                "w_value": _format_param(float(w_val)),
                "indirect_point": _format_param(float(point)),
                "ci": _bootstrap_ci(bvals, float(point), ci_level),
            }
        )

    index_row = {
        "contrast": "+1 SD vs -1 SD（条件间接效应之差）",
        "point": _format_param(float(p_diff)),
        "ci": _bootstrap_ci(boots_diff, float(p_diff), ci_level),
    }

    return {
        "success": True,
        "task": "moderated_mediation",
        "model": "hayes_process_7",
        "note": "观测变量、连续 W；W 调节 X→M；Y ~ M+X+W+covs。分类 W 请在请求中指定 w_type=categorical。",
        "x": x,
        "m": m,
        "y": y,
        "w": w,
        "w_type": "continuous",
        "covariates": covs,
        "n_used": int(n),
        "n_boot": int(n_boot),
        "ci_level": float(ci_level),
        "failures": int(failures),
        "first_stage": {"outcome": m, "equation": f"{m} ~ {x} + {w} + {x}:{w} + covs", "coefficients": first_stage},
        "second_stage": {"outcome": y, "equation": f"{y} ~ {m} + {x} + {w} + covs", "coefficients": second_stage},
        "conditional_indirect": conditional,
        "index_moderated_mediation": index_row,
    }


@celery_app.task(bind=True, name="stats.fit_semopy")
def fit_semopy_task(self, payload: dict[str, Any]):
    """
    异步估算（semopy）
    payload 对齐 /api/v1/stats/fit 的请求体（EstimateRequest）。
    """
    try:
        self.update_state(state=states.STARTED, meta={"progress": 1, "message": "读取数据…"})
        data_key = (payload.get("data_key") or "").strip()
        syntax = (payload.get("lavaan_syntax") or "").strip()
        estimator = (payload.get("estimator") or "ML").strip()
        missing_strategy = (payload.get("missing_strategy") or "listwise").strip()

        df = get_data(data_key)
        if df is None:
            raise ValueError("data_key 无效或已过期，请先重新上传数据")
        if not syntax:
            raise ValueError("lavaan_syntax 不能为空，请先在建模页生成语法")

        self.update_state(state=states.STARTED, meta={"progress": 12, "message": "缺失值处理…"})
        data = _apply_missing_strategy(df, missing_strategy)
        if data.empty:
            raise ValueError("缺失值处理后无可用样本，请检查数据")

        self.update_state(state=states.STARTED, meta={"progress": 35, "message": "模型拟合中（最多 50 次迭代）…"})
        sem_model = Model(syntax)
        sem_model.fit(
            data,
            obj=_obj(estimator, missing_strategy),
            solver="SLSQP",
            options={"maxiter": 50},
        )

        self.update_state(state=states.STARTED, meta={"progress": 80, "message": "计算拟合指标与参数表…"})
        stats_df = calc_stats(sem_model)

        chi2 = _pick_stat(stats_df, "chi2")
        dof = _pick_stat(stats_df, "DoF")
        rmsea = _pick_stat(stats_df, "RMSEA")
        srmr = _pick_stat(stats_df, "SRMR")
        tli = _pick_stat(stats_df, "TLI")
        cfi = _pick_stat(stats_df, "CFI")
        chi2_df = None if (chi2 is None or dof is None or dof == 0) else chi2 / dof

        fit_indices = {
            "chi2": _format_metric(chi2),
            "chi2_df": _format_metric(chi2_df),
            "rmsea": _format_metric(rmsea),
            "srmr": _format_metric(srmr),
            "tli": _format_metric(tli),
            "cfi": _format_metric(cfi),
            "status": _score_fit(chi2_df, rmsea, srmr, cfi, tli),
        }

        result = {
            "success": True,
            "n_used": int(len(data)),
            "missing_strategy": missing_strategy,
            "estimator": estimator,
            "fit_indices": fit_indices,
            "estimates": _extract_estimates(sem_model),
        }
        self.update_state(state=states.STARTED, meta={"progress": 100, "message": "完成"})
        return result
    except Exception as e:
        self.update_state(state=states.FAILURE, meta=celery_failure_meta(e))
        raise RuntimeError(str(e)) from e


@celery_app.task(bind=True, name="stats.latent_interaction_probe")
def latent_interaction_probe_task(self, payload: dict[str, Any]):
    """
    潜变量交互 MVP：在已写好的 lavaan 语法上拟合 semopy，并筛选与 F1/F2 相关的结构路径。
    不自动生成 LMS；边界说明见返回 boundary 字段。
    """
    try:
        self.update_state(state=states.STARTED, meta={"progress": 8, "message": "潜变量交互（MVP）…"})
        data_key = (payload.get("data_key") or "").strip()
        syntax = (payload.get("lavaan_syntax") or "").strip()
        estimator = (payload.get("estimator") or "ML").strip()
        missing_strategy = (payload.get("missing_strategy") or "listwise").strip()
        y = (payload.get("y") or "").strip()
        f1 = (payload.get("f1") or "").strip()
        f2 = (payload.get("f2") or "").strip()

        if not data_key or not syntax:
            raise ValueError("data_key 与 lavaan_syntax 不能为空")
        if not (y and f1 and f2):
            raise ValueError("请提供结局变量 y 以及两个潜变量/因子名 f1、f2")
        if len({y, f1, f2}) < 3:
            raise ValueError("y、f1、f2 须互不相同")

        df = get_data(data_key)
        if df is None:
            raise ValueError("data_key 无效或已过期，请先重新上传数据")

        self.update_state(state=states.STARTED, meta={"progress": 28, "message": "缺失值处理…"})
        data = _apply_missing_strategy(df, missing_strategy)
        if data.empty:
            raise ValueError("缺失值处理后无可用样本，请检查数据")

        self.update_state(state=states.STARTED, meta={"progress": 55, "message": "拟合模型（semopy）…"})
        sem_model = Model(syntax)
        sem_model.fit(
            data,
            obj=_obj(estimator, missing_strategy),
            solver="SLSQP",
            options={"maxiter": 50},
        )
        est = _extract_estimates(sem_model)
        structural, matched = _filter_latent_interaction_rows(est, y=y, f1=f1, f2=f2)

        result = {
            "success": True,
            "task": "latent_interaction_probe",
            "n_used": int(len(data)),
            "y": y,
            "f1": f1,
            "f2": f2,
            "preconditions": _latent_interaction_preconditions(
                y=y,
                f1=f1,
                f2=f2,
                estimator=estimator,
                missing_strategy=missing_strategy,
            ),
            "boundary": {
                "semopy": "MVP：OpenSEM 使用 semopy 估计。请在语法中显式写出交互（如乘积潜变量 F_INT，或右侧含 F1:F2 的结构式）。纯「潜变量相乘」需乘积指标/LMS 时，请以论文方法为准并在 lavaan 环境复核。",
                "lavaan": "启用 R+lavaan 时可使用更完整的潜交互建模流程；本探测任务仍通过 semopy 返回系数表筛选结果。",
            },
            "structural_for_y": structural,
            "matching": matched,
        }
        self.update_state(state=states.STARTED, meta={"progress": 100, "message": "完成"})
        return result
    except Exception as e:
        self.update_state(state=states.FAILURE, meta=celery_failure_meta(e))
        raise RuntimeError(str(e)) from e


@celery_app.task(bind=True, name="stats.bootstrap_mediation")
def bootstrap_mediation_task(self, payload: dict[str, Any]):
    """
    Bootstrap（中介效应）最小实现：
    - 支持多条 (x, m, y) 间接效应
    - 使用 semopy 重复拟合；每次自助抽样行
    """
    try:
        self.update_state(state=states.STARTED, meta={"progress": 1, "message": "读取数据…"})
        data_key = (payload.get("data_key") or "").strip()
        syntax = (payload.get("lavaan_syntax") or "").strip()
        estimator = (payload.get("estimator") or "ML").strip()
        missing_strategy = (payload.get("missing_strategy") or "listwise").strip()
        effects = payload.get("effects") or []
        covariates_raw = payload.get("covariates")
        covariates_in = covariates_raw if isinstance(covariates_raw, list) else []
        n_boot = int(payload.get("n_boot") or 2000)
        ci_level = float(payload.get("ci_level") or 0.95)
        seed = payload.get("seed")
        use_standardized = bool(payload.get("use_standardized", True))

        if n_boot < 200:
            n_boot = 200
        if n_boot > 5000:
            n_boot = 5000

        df = get_data(data_key)
        if df is None:
            raise ValueError("data_key 无效或已过期，请先重新上传数据")
        if not syntax:
            raise ValueError("lavaan_syntax 不能为空，请先在建模页生成语法")
        if not isinstance(effects, list) or not effects:
            raise ValueError("effects 不能为空：请至少提供一条 (x,m,y) 中介路径")

        self.update_state(state=states.STARTED, meta={"progress": 10, "message": "缺失值处理…"})
        data = _apply_missing_strategy(df, missing_strategy)
        if data.empty:
            raise ValueError("缺失值处理后无可用样本，请检查数据")

        rng = np.random.default_rng(int(seed) if seed is not None else None)

        effect_specs: list[dict[str, Any]] = []
        for idx, item in enumerate(effects):
            if not isinstance(item, dict):
                raise ValueError(f"effects[{idx}] 须为对象")
            spec = _normalize_effect_spec(item)
            if not spec:
                raise ValueError(
                    f"effects[{idx}] 无效：请提供 sequence / sequence_text，或完整的 x、m、y（单中介）"
                )
            effect_specs.append(spec)

        # 协变量：以主效应形式加入每条中介链相关回归（所有中介与最终 Y）
        exclude_vars: set[str] = set()
        for spec in effect_specs:
            for v in spec.get("sequence") or []:
                if isinstance(v, str) and v.strip():
                    exclude_vars.add(v.strip())
        covariates = _clean_covariates(covariates_in, exclude_vars=exclude_vars)
        if covariates:
            missing_cols = [c for c in covariates if c not in data.columns]
            if missing_cols:
                raise ValueError(f"协变量不存在：{', '.join(missing_cols)}")

        outcomes: list[str] = []
        seen_out: set[str] = set()
        for spec in effect_specs:
            seq = spec.get("sequence") or []
            for v in seq[1:]:
                s = str(v or "").strip()
                if not s:
                    continue
                if s not in seen_out:
                    outcomes.append(s)
                    seen_out.add(s)

        syntax_used = (
            _augment_lavaan_syntax_with_covariates(syntax, outcomes=outcomes, covariates=covariates)
            if covariates
            else syntax
        )

        _validate_effect_specs_allowlist(
            effect_specs,
            lavaan_syntax=syntax_used,
            data_columns=list(data.columns),
        )

        self.update_state(state=states.STARTED, meta={"progress": 18, "message": "拟合原始样本（点估计）…"})
        base_model = Model(syntax_used)
        base_model.fit(
            data,
            obj=_obj(estimator, missing_strategy),
            solver="SLSQP",
            options={"maxiter": 50},
        )
        base_paths = _extract_path_map(base_model, use_standardized=use_standardized)

        xy_lookup: dict[str, tuple[str, str]] = {}
        for spec in effect_specs:
            xy_lookup.setdefault(spec["xy_key"], (spec["x"], spec["y"]))

        point_by_path: dict[str, float | None] = {}
        for spec in effect_specs:
            point_by_path[spec["path_key"]] = _compute_indirect_effect(base_paths, spec["sequence"])
        for _xyk, (xv, yv) in xy_lookup.items():
            dk = _parse_effect_key(yv, "~", xv)
            point_by_path[dk] = base_paths.get(dk)

        self.update_state(state=states.STARTED, meta={"progress": 25, "message": f"Bootstrap 抽样中（{n_boot} 次）…"})
        n = len(data)
        boot_values: dict[str, list[float]] = {spec["path_key"]: [] for spec in effect_specs}
        boot_direct_by_xy: dict[str, list[float]] = defaultdict(list)
        failures = 0

        # progress: 25..95
        for i in range(n_boot):
            idx = rng.integers(0, n, size=n, endpoint=False)
            sample = data.iloc[idx]
            try:
                m = Model(syntax_used)
                m.fit(
                    sample,
                    obj=_obj(estimator, missing_strategy),
                    solver="SLSQP",
                    options={"maxiter": 50},
                )
                paths = _extract_path_map(m, use_standardized=use_standardized)
                for spec in effect_specs:
                    key = spec["path_key"]
                    v = _compute_indirect_effect(paths, spec["sequence"])
                    if v is not None and np.isfinite(v):
                        boot_values[key].append(float(v))
                for xyk, (xv, yv) in xy_lookup.items():
                    dk = _parse_effect_key(yv, "~", xv)
                    dv = paths.get(dk)
                    if dv is not None and np.isfinite(dv):
                        boot_direct_by_xy[xyk].append(float(dv))
                    else:
                        boot_direct_by_xy[xyk].append(float("nan"))
            except Exception:
                failures += 1

            if (i + 1) % max(1, n_boot // 25) == 0:
                p = 25 + int(70 * (i + 1) / n_boot)
                self.update_state(
                    state=states.STARTED,
                    meta={"progress": min(p, 95), "message": f"Bootstrap 抽样中… {i+1}/{n_boot}（失败 {failures}）"},
                )

        self.update_state(state=states.STARTED, meta={"progress": 96, "message": "汇总置信区间…"})
        out_items: list[dict[str, Any]] = []
        for spec in effect_specs:
            key = spec["path_key"]
            point = point_by_path.get(key)
            if point is None or not np.isfinite(point):
                out_items.append(
                    {
                        "x": spec["x"],
                        "y": spec["y"],
                        "mediators": spec["mediators"],
                        "sequence": spec["sequence"],
                        "path_label": " → ".join(spec["sequence"]),
                        "effect_type": spec["effect_type"],
                        "label": spec["label"],
                        "component_paths": [],
                        "indirect_point": point,
                        "ci": None,
                        "note": "点估计无法计算（缺少路径系数）",
                    }
                )
                continue
            ci = _bootstrap_ci(boot_values.get(key, []), float(point), ci_level)
            out_items.append(
                {
                    "x": spec["x"],
                    "y": spec["y"],
                    "mediators": spec["mediators"],
                    "sequence": spec["sequence"],
                    "path_label": " → ".join(spec["sequence"]),
                    "effect_type": spec["effect_type"],
                    "label": spec["label"],
                    "component_paths": [],
                    "indirect_point": float(point),
                    "ci": ci,
                    "note": None,
                }
            )

        total_rows = _build_total_indirect_rows(effect_specs, point_by_path, boot_values, ci_level)
        out_items.extend(total_rows)
        decomp_rows = _build_decomposition_rows(
            effect_specs, point_by_path, boot_values, boot_direct_by_xy, ci_level
        )
        out_items.extend(decomp_rows)

        result = {
            "success": True,
            "task": "bootstrap_mediation",
            "custom_effect_mode": "path_sequence_only",
            "custom_effect_label": "路径序列自定义效应",
            "n_used": int(len(data)),
            "n_boot": int(n_boot),
            "ci_level": float(ci_level),
            "use_standardized": bool(use_standardized),
            "failures": int(failures),
            "n_effects": len(effect_specs),
            "covariates": covariates,
            "items": out_items,
            "decomposition_note": "direct_effect / total_effect 行：总效应 = 直接效应 + 各特定间接效应之和（若未估计直接路径则总效应退化为间接之和并附说明）。",
        }
        self.update_state(state=states.STARTED, meta={"progress": 100, "message": "完成"})
        return result
    except Exception as e:
        self.update_state(state=states.FAILURE, meta=celery_failure_meta(e))
        raise RuntimeError(str(e)) from e


@celery_app.task(bind=True, name="stats.moderation_analysis")
def moderation_analysis_task(self, payload: dict[str, Any]):
    try:
        self.update_state(state=states.STARTED, meta={"progress": 1, "message": "读取数据…"})
        data_key = (payload.get("data_key") or "").strip()
        x = (payload.get("x") or "").strip()
        w = (payload.get("w") or "").strip()
        y = (payload.get("y") or "").strip()
        moderator_type = (payload.get("moderator_type") or "continuous").strip()
        missing_strategy = (payload.get("missing_strategy") or "listwise").strip()
        covariates_raw = payload.get("covariates")
        covariates = covariates_raw if isinstance(covariates_raw, list) else []

        if not data_key:
            raise ValueError("data_key 不能为空")
        if not x or not w or not y:
            raise ValueError("调节分析需要同时提供 X / W / Y")

        df = get_data(data_key)
        if df is None:
            raise ValueError("data_key 无效或已过期，请先重新上传数据")

        self.update_state(state=states.STARTED, meta={"progress": 15, "message": "缺失值处理…"})
        data = _apply_missing_strategy(df, missing_strategy)
        if data.empty:
            raise ValueError("缺失值处理后无可用样本，请检查数据")

        self.update_state(state=states.STARTED, meta={"progress": 55, "message": "计算调节效应…"})
        result = run_observed_moderation_analysis(
            df=data,
            x=x,
            w=w,
            y=y,
            moderator_type=moderator_type,
            covariates=[str(v or "").strip() for v in covariates],
        )
        result["task"] = "moderation_analysis"
        result["missing_strategy"] = missing_strategy

        self.update_state(state=states.STARTED, meta={"progress": 100, "message": "完成"})
        return result
    except Exception as e:
        self.update_state(state=states.FAILURE, meta=celery_failure_meta(e))
        raise RuntimeError(str(e)) from e


@celery_app.task(bind=True, name="stats.moderated_mediation")
def moderated_mediation_task(self, payload: dict[str, Any]):
    try:
        self.update_state(state=states.STARTED, meta={"progress": 1, "message": "读取数据…"})
        data_key = (payload.get("data_key") or "").strip()
        x = (payload.get("x") or "").strip()
        m = (payload.get("m") or "").strip()
        y = (payload.get("y") or "").strip()
        w = (payload.get("w") or "").strip()
        missing_strategy = (payload.get("missing_strategy") or "listwise").strip()
        covariates_raw = payload.get("covariates")
        covariates = covariates_raw if isinstance(covariates_raw, list) else []
        n_boot = int(payload.get("n_boot") or 2000)
        ci_level = float(payload.get("ci_level") or 0.95)
        seed = payload.get("seed")

        if not data_key:
            raise ValueError("data_key 不能为空")
        if not x or not m or not y or not w:
            raise ValueError("有调节的中介需要同时提供 X / M / Y / W")
        if len({x, m, y, w}) < 4:
            raise ValueError("X / M / Y / W 须为互不相同的变量名")

        df = get_data(data_key)
        if df is None:
            raise ValueError("data_key 无效或已过期，请先重新上传数据")

        self.update_state(state=states.STARTED, meta={"progress": 15, "message": "缺失值处理…"})
        data = _apply_missing_strategy(df, missing_strategy)
        if data.empty:
            raise ValueError("缺失值处理后无可用样本，请检查数据")

        self.update_state(state=states.STARTED, meta={"progress": 40, "message": "估计有调节的中介（Bootstrap）…"})
        hm = (payload.get("hayes_model") or "7").strip().lower()
        if hm in ("14", "process_14", "model14", "m14"):
            w_type = (payload.get("w_type") or "continuous").strip().lower()
            if w_type != "continuous":
                raise ValueError("PROCESS Model 14（W 调节 M→Y）当前仅支持连续调节变量 W，请将 w_type 设为 continuous")
            result = run_observed_moderated_mediation_model14(
                df=data,
                x=x,
                m=m,
                y=y,
                w=w,
                covariates=[str(v or "").strip() for v in covariates],
                n_boot=n_boot,
                ci_level=ci_level,
                seed=int(seed) if seed is not None else None,
            )
        elif hm in ("7", "process_7", "model7", "m7", ""):
            result = run_observed_moderated_mediation_model7(
                df=data,
                x=x,
                m=m,
                y=y,
                w=w,
                covariates=[str(v or "").strip() for v in covariates],
                n_boot=n_boot,
                ci_level=ci_level,
                seed=int(seed) if seed is not None else None,
                w_type=(payload.get("w_type") or "continuous"),
            )
        else:
            raise ValueError("hayes_model 无效：请使用 7（X→M 受 W 调节）或 14（M→Y 受 W 调节）")
        result["missing_strategy"] = missing_strategy

        self.update_state(state=states.STARTED, meta={"progress": 100, "message": "完成"})
        return result
    except Exception as e:
        self.update_state(state=states.FAILURE, meta=celery_failure_meta(e))
        raise RuntimeError(str(e)) from e


@celery_app.task(bind=True, name="stats.invariance_configural")
def invariance_configural_task(self, payload: dict[str, Any]):
    """
    多群组不变性检验（最小实现：仅配置不变性 / Configural）
    - 以 group_var 拆分数据并分别拟合，返回各组拟合度与参数表
    - 载荷/截距/残差 等约束模型（metric/scalar/strict）留待后续 lavaan 迁移后补齐
    """
    try:
        self.update_state(state=states.STARTED, meta={"progress": 1, "message": "读取数据…"})
        data_key = (payload.get("data_key") or "").strip()
        syntax = (payload.get("lavaan_syntax") or "").strip()
        estimator = (payload.get("estimator") or "ML").strip()
        missing_strategy = (payload.get("missing_strategy") or "listwise").strip()
        group_var = (payload.get("group_var") or "").strip()
        max_groups = int(payload.get("max_groups") or 8)

        df = get_data(data_key)
        if df is None:
            raise ValueError("data_key 无效或已过期，请先重新上传数据")
        if not syntax:
            raise ValueError("lavaan_syntax 不能为空，请先在建模页生成语法")
        if not group_var:
            raise ValueError("group_var 不能为空：请选择分组变量")
        if group_var not in df.columns:
            raise ValueError(f"分组变量不存在：{group_var}")

        self.update_state(state=states.STARTED, meta={"progress": 10, "message": "缺失值处理…"})
        data = _apply_missing_strategy(df, missing_strategy)
        if data.empty:
            raise ValueError("缺失值处理后无可用样本，请检查数据")

        # group values
        g = data[group_var]
        groups = [x for x in g.dropna().unique().tolist()]
        if not groups:
            raise ValueError("分组变量无有效取值（全缺失）")
        if len(groups) > max_groups:
            groups = groups[:max_groups]

        results: list[dict[str, Any]] = []
        total = len(groups)

        for i, gv in enumerate(groups):
            self.update_state(
                state=states.STARTED,
                meta={"progress": 15 + int(70 * i / max(1, total)), "message": f"拟合组别 {i+1}/{total}: {gv} …"},
            )
            subset = data[data[group_var] == gv].drop(columns=[group_var])
            if subset.empty:
                results.append({"group": str(gv), "success": False, "error": "该组无可用样本"})
                continue

            try:
                m = Model(syntax)
                m.fit(
                    subset,
                    obj=_obj(estimator, missing_strategy),
                    solver="SLSQP",
                    options={"maxiter": 50},
                )
                stats_df = calc_stats(m)
                chi2 = _pick_stat(stats_df, "chi2")
                dof = _pick_stat(stats_df, "DoF")
                rmsea = _pick_stat(stats_df, "RMSEA")
                srmr = _pick_stat(stats_df, "SRMR")
                tli = _pick_stat(stats_df, "TLI")
                cfi = _pick_stat(stats_df, "CFI")
                chi2_df = None if (chi2 is None or dof is None or dof == 0) else chi2 / dof

                fit_indices = {
                    "chi2": _format_metric(chi2),
                    "chi2_df": _format_metric(chi2_df),
                    "rmsea": _format_metric(rmsea),
                    "srmr": _format_metric(srmr),
                    "tli": _format_metric(tli),
                    "cfi": _format_metric(cfi),
                    "status": _score_fit(chi2_df, rmsea, srmr, cfi, tli),
                }
                results.append(
                    {
                        "group": str(gv),
                        "success": True,
                        "n_used": int(len(subset)),
                        "fit_indices": fit_indices,
                        "estimates": _extract_estimates(m),
                    }
                )
            except Exception as e:
                results.append({"group": str(gv), "success": False, "error": str(e)})

        self.update_state(state=states.STARTED, meta={"progress": 96, "message": "汇总结果…"})
        result = {
            "success": True,
            "task": "invariance_configural",
            "group_var": group_var,
            "groups": [r.get("group") for r in results],
            "items": results,
            "note": "当前仅实现配置不变性（各组分别拟合，不加等值约束）。metric/scalar/strict 将在 lavaan 迁移后补齐。",
        }
        self.update_state(state=states.STARTED, meta={"progress": 100, "message": "完成"})
        return result
    except Exception as e:
        self.update_state(state=states.FAILURE, meta=celery_failure_meta(e))
        raise RuntimeError(str(e)) from e


@celery_app.task(bind=True, name="stats.invariance_lavaan_series")
def invariance_lavaan_series_task(self, payload: dict[str, Any]):
    """
    lavaan 多群组不变性序列（configural/metric/scalar/strict）
    - 若当前环境未启用 rpy2+R+lavaan：返回 supported=false（不抛异常，方便前端提示并回退 semopy 方案）
    """
    try:
        self.update_state(state=states.STARTED, meta={"progress": 1, "message": "检查 lavaan 环境…"})
        availability = check_lavaan_available()
        if not availability.available:
            self.update_state(state=states.STARTED, meta={"progress": 100, "message": "未启用 lavaan"})
            group_var = (payload.get("group_var") or "").strip()
            # Epic2 契约：即使降级，也要保持固定 schema（models=4, comparisons=3），避免前端/导出分叉与“基本满足”体验破碎。
            models = [
                {"model": "configural", "group_equal": [], "fit": {"chi2": None, "df": None, "cfi": None, "tli": None, "rmsea": None, "srmr": None}, "converged": None},
                {"model": "metric", "group_equal": ["loadings"], "fit": {"chi2": None, "df": None, "cfi": None, "tli": None, "rmsea": None, "srmr": None}, "converged": None},
                {"model": "scalar", "group_equal": ["loadings", "intercepts"], "fit": {"chi2": None, "df": None, "cfi": None, "tli": None, "rmsea": None, "srmr": None}, "converged": None},
                {"model": "strict", "group_equal": ["loadings", "intercepts", "residuals"], "fit": {"chi2": None, "df": None, "cfi": None, "tli": None, "rmsea": None, "srmr": None}, "converged": None},
            ]
            comparisons = [
                {
                    "from": "configural",
                    "to": "metric",
                    "ok": False,
                    "chi2_diff": None,
                    "df_diff": None,
                    "p_value": None,
                    "delta_cfi": None,
                    "delta_rmsea": None,
                    "note": f"当前环境未启用 lavaan（{availability.reason}）",
                },
                {
                    "from": "metric",
                    "to": "scalar",
                    "ok": False,
                    "chi2_diff": None,
                    "df_diff": None,
                    "p_value": None,
                    "delta_cfi": None,
                    "delta_rmsea": None,
                    "note": f"当前环境未启用 lavaan（{availability.reason}）",
                },
                {
                    "from": "scalar",
                    "to": "strict",
                    "ok": False,
                    "chi2_diff": None,
                    "df_diff": None,
                    "p_value": None,
                    "delta_cfi": None,
                    "delta_rmsea": None,
                    "note": f"当前环境未启用 lavaan（{availability.reason}）",
                },
            ]
            return {
                "success": True,
                "supported": False,
                "task": "invariance_lavaan_series",
                "mode": "degraded",
                "message": f"当前环境未启用 lavaan（{availability.reason}）",
                "group_var": group_var or None,
                "models": models,
                "comparisons": comparisons,
                "note": "当前为降级输出：结构已固定为 4+3 以便前端/导出稳定展示；如需真实序列检验请启用 R + lavaan + rpy2。",
            }

        data_key = (payload.get("data_key") or "").strip()
        syntax = (payload.get("lavaan_syntax") or "").strip()
        group_var = (payload.get("group_var") or "").strip()
        missing_strategy = (payload.get("missing_strategy") or "fiml").strip()

        if not data_key:
            raise ValueError("data_key 不能为空")
        if not syntax:
            raise ValueError("lavaan_syntax 不能为空，请先在建模页生成语法")
        if not group_var:
            raise ValueError("group_var 不能为空：请选择分组变量")

        df = get_data(data_key)
        if df is None:
            raise ValueError("data_key 无效或已过期，请先重新上传数据")

        # lavaan 自带 missing="fiml"，这里仍允许 listwise/mean_impute 做预处理以复用 Phase1 习惯
        self.update_state(state=states.STARTED, meta={"progress": 12, "message": "缺失值处理…"})
        if missing_strategy in ("listwise", "mean_impute"):
            data = _apply_missing_strategy(df, missing_strategy)
        else:
            data = df.copy()

        if data.empty:
            raise ValueError("缺失值处理后无可用样本，请检查数据")

        self.update_state(state=states.STARTED, meta={"progress": 40, "message": "lavaan 拟合与不变性序列检验中…"})
        lavaan_missing = "fiml" if missing_strategy == "fiml" else "listwise"
        out = lavaan_invariance_series(
            data_df=data,
            lavaan_syntax=syntax,
            group_var=group_var,
            missing=lavaan_missing,
        )
        # lavaan_service 已返回固定 schema；这里仅统一顶层字段，避免上层依赖时出现分叉
        out["supported"] = True
        out["mode"] = out.get("mode") or "lavaan"
        out["success"] = True if out.get("success") is not False else False

        self.update_state(state=states.STARTED, meta={"progress": 100, "message": "完成"})
        return out
    except Exception as e:
        self.update_state(state=states.FAILURE, meta=celery_failure_meta(e))
        raise RuntimeError(str(e)) from e


@celery_app.task(bind=True, name="stats.model_compare")
def model_compare_task(self, payload: dict[str, Any]):
    """
    模型比较（AIC/BIC + 嵌套模型 LRT）：
    - 优先使用 lavaan（若可用）：提供 AIC/BIC + lavTestLRT
    - 若 lavaan 不可用：返回降级输出（仍给出 AIC/BIC/拟合度，LRT 置空 + note）
    """
    try:
        self.update_state(state=states.STARTED, meta={"progress": 1, "message": "检查 lavaan 环境…"})
        availability = check_lavaan_available()

        data_key = (payload.get("data_key") or "").strip()
        syntax_a = (payload.get("lavaan_syntax_a") or "").strip()
        syntax_b = (payload.get("lavaan_syntax_b") or "").strip()
        estimator = (payload.get("estimator") or "ML").strip()
        missing_strategy = (payload.get("missing_strategy") or "fiml").strip()
        label_a = (payload.get("label_a") or "Model A").strip()
        label_b = (payload.get("label_b") or "Model B").strip()

        if not data_key:
            raise ValueError("data_key 不能为空")
        if not syntax_a or not syntax_b:
            raise ValueError("模型比较需要同时提供两份 lavaan_syntax（A / B）")

        df = get_data(data_key)
        if df is None:
            raise ValueError("data_key 无效或已过期，请先重新上传数据")

        self.update_state(state=states.STARTED, meta={"progress": 10, "message": "缺失值处理…"})
        if missing_strategy in ("listwise", "mean_impute"):
            data = _apply_missing_strategy(df, missing_strategy)
        else:
            data = df.copy()
        if data.empty:
            raise ValueError("缺失值处理后无可用样本，请检查数据")

        if not availability.available:
            self.update_state(state=states.STARTED, meta={"progress": 100, "message": "未启用 lavaan（已降级）"})
            out = run_semopy_model_compare(
                data=data,
                syntax_a=syntax_a,
                syntax_b=syntax_b,
                estimator=estimator,
                missing_strategy=("listwise" if missing_strategy == "fiml" else missing_strategy),
                label_a=label_a,
                label_b=label_b,
            )
            # 统一契约：supported 标识代表“是否为 lavaan 论文级对比”
            return {
                "success": True,
                "task": "model_compare",
                "supported": False,
                "mode": "degraded",
                "message": f"当前环境未启用 lavaan（{availability.reason}）：LRT 不可用，已降级输出。",
                "models": out.get("models") or [],
                "comparison": out.get("comparison") or {},
                "note": "降级输出：AIC/BIC 可能可用，但嵌套模型 LRT 需要 lavaan::lavTestLRT。",
            }

        self.update_state(state=states.STARTED, meta={"progress": 45, "message": "lavaan 拟合与模型比较中…"})
        lavaan_missing = "fiml" if missing_strategy == "fiml" else "listwise"
        out = lavaan_model_compare(
            data_df=data,
            model_a_syntax=syntax_a,
            model_b_syntax=syntax_b,
            missing=lavaan_missing,
            label_a=label_a,
            label_b=label_b,
        )
        out["success"] = True if out.get("success") is not False else False
        out["supported"] = True
        out["mode"] = out.get("mode") or "lavaan"
        out["task"] = "model_compare"

        self.update_state(state=states.STARTED, meta={"progress": 100, "message": "完成"})
        return out
    except Exception as e:
        self.update_state(state=states.FAILURE, meta=celery_failure_meta(e))
        raise RuntimeError(str(e)) from e


def _semopy_pick_regression_coef(
    *,
    sem_model: Model,
    outcome: str,
    predictor: str,
) -> dict[str, Any] | None:
    try:
        insp = sem_model.inspect(std_est=True)
    except Exception:
        return None
    if insp is None or getattr(insp, "empty", False):
        return None
    o = str(outcome).strip()
    p = str(predictor).strip()
    if not (o and p):
        return None
    try:
        sub = insp[(insp["lval"].astype(str).str.strip() == o) & (insp["op"].astype(str).str.strip() == "~") & (insp["rval"].astype(str).str.strip() == p)]
        if sub.empty:
            return None
        r = sub.iloc[0]
        return {
            "lhs": o,
            "op": "~",
            "rhs": p,
            "estimate": _to_float(r.get("Estimate")),
            "std_err": _to_float(r.get("Std. Err")),
            "p_value": _to_float(r.get("p-value")),
            "std_all": _to_float(r.get("Est. Std")),
        }
    except Exception:
        return None


@celery_app.task(bind=True, name="stats.mga_structural_path_compare")
def mga_structural_path_compare_task(self, payload: dict[str, Any]):
    """
    MGA：结构路径跨组比较（最小闭环：单条回归路径）
    - lavaan 可用：free vs constrained（仅该路径等值）+ lavTestLRT
    - lavaan 不可用：降级为“各组分别拟合 + 提取该路径系数”，并提示 LRT 不可用
    """
    try:
        self.update_state(state=states.STARTED, meta={"progress": 1, "message": "检查 lavaan 环境…"})
        availability = check_lavaan_available()

        data_key = (payload.get("data_key") or "").strip()
        syntax = (payload.get("lavaan_syntax") or "").strip()
        group_var = (payload.get("group_var") or "").strip()
        outcome = (payload.get("outcome") or "").strip()
        predictor = (payload.get("predictor") or "").strip()
        raw_paths = payload.get("paths")
        estimator = (payload.get("estimator") or "ML").strip()
        missing_strategy = (payload.get("missing_strategy") or "fiml").strip()

        if not data_key:
            raise ValueError("data_key 不能为空")
        if not syntax:
            raise ValueError("lavaan_syntax 不能为空，请先在建模页生成语法")
        if not group_var:
            raise ValueError("group_var 不能为空：请选择分组变量")
        # Wave 3：允许多条路径（若未提供则回退到单条）
        paths: list[dict[str, str]] = []
        if isinstance(raw_paths, list) and raw_paths:
            for it in raw_paths:
                if not isinstance(it, dict):
                    continue
                px = str(it.get("predictor") or "").strip()
                oy = str(it.get("outcome") or "").strip()
                if px and oy:
                    paths.append({"predictor": px, "outcome": oy})
        if not paths:
            if not outcome or not predictor:
                raise ValueError("结构路径比较需要提供 outcome/predictor（或提供 paths 列表）")
            paths = [{"predictor": predictor, "outcome": outcome}]

        df = get_data(data_key)
        if df is None:
            raise ValueError("data_key 无效或已过期，请先重新上传数据")
        if group_var not in df.columns:
            raise ValueError(f"分组变量不存在：{group_var}")

        self.update_state(state=states.STARTED, meta={"progress": 10, "message": "缺失值处理…"})
        if missing_strategy in ("listwise", "mean_impute"):
            data = _apply_missing_strategy(df, missing_strategy)
        else:
            data = df.copy()
        if data.empty:
            raise ValueError("缺失值处理后无可用样本，请检查数据")

        levels = ["configural", "metric", "scalar", "strict"]

        if not availability.available:
            # 降级：不支持测量层级约束与 LRT，仅输出“各组分别拟合”的系数对照（按 level×path 复制结构，便于前端/导出稳定）
            self.update_state(state=states.STARTED, meta={"progress": 100, "message": "未启用 lavaan（已降级）"})
            groups = [x for x in data[group_var].dropna().unique().tolist()]
            items: list[dict[str, Any]] = []
            for lv in levels:
                for pth in paths:
                    px = pth.get("predictor")
                    oy = pth.get("outcome")
                    group_rows = []
                    for gv in groups:
                        subset = data[data[group_var] == gv].drop(columns=[group_var])
                        if subset.empty:
                            group_rows.append({"group": str(gv), "success": False, "error": "该组无可用样本"})
                            continue
                        try:
                            m = Model(syntax)
                            m.fit(
                                subset,
                                obj=_obj(estimator, ("listwise" if missing_strategy == "fiml" else missing_strategy)),
                                solver="SLSQP",
                                options={"maxiter": 50},
                            )
                            coef = _semopy_pick_regression_coef(sem_model=m, outcome=oy, predictor=px)
                            group_rows.append({"group": str(gv), "success": True, "coef": coef})
                        except Exception as e:
                            group_rows.append({"group": str(gv), "success": False, "error": str(e)})
                    items.append(
                        {
                            "level": lv,
                            "path": {"outcome": oy, "predictor": px},
                            "group_estimates": group_rows,
                            "comparison": {
                                "from": "free",
                                "to": "constrained(path equal)",
                                "ok": False,
                                "chi2_diff": None,
                                "df_diff": None,
                                "p_value": None,
                                "note": "降级：未启用 lavaan，无法执行测量不变性层级与嵌套模型 LRT。",
                            },
                        }
                    )

            return {
                "success": True,
                "task": "mga_structural_path_compare",
                "supported": False,
                "mode": "degraded",
                "message": f"当前环境未启用 lavaan（{availability.reason}）：测量层级约束与结构路径等值约束 LRT 不可用，已降级为各组分别拟合的系数对照。",
                "group_var": group_var,
                "path": (paths[0] if len(paths) == 1 else None),
                "items": items,
                "note": "降级输出：仅提供各组该路径的系数/标准化系数（若可提取）。如需论文级跨组约束与逐步比较请启用 R + lavaan + rpy2。",
            }

        self.update_state(state=states.STARTED, meta={"progress": 45, "message": "lavaan 多群组拟合（分层级×多路径）与逐步比较中…"})
        lavaan_missing = "fiml" if missing_strategy == "fiml" else "listwise"
        out = lavaan_mga_structural_path_compare(
            data_df=data,
            lavaan_syntax=syntax,
            group_var=group_var,
            paths=paths,
            missing=lavaan_missing,
        )
        out["success"] = True if out.get("success") is not False else False
        out["supported"] = True
        out["task"] = "mga_structural_path_compare"

        self.update_state(state=states.STARTED, meta={"progress": 100, "message": "完成"})
        return out
    except Exception as e:
        self.update_state(state=states.FAILURE, meta=celery_failure_meta(e))
        raise RuntimeError(str(e)) from e

