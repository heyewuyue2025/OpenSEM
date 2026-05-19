#!/usr/bin/env python3
"""
最小演示脚本：一键跑通 上传 → 表单建模(to-lavaan) → 异步估算(tasks/stats-fit) → 导出（xlsx/docx/txt）。

前置条件：
- 后端服务已启动（默认 http://127.0.0.1:8020）

环境变量：
- OPENSEM_BASE_URL：后端地址（默认 http://127.0.0.1:8020）
- OPENSEM_DEMO_FIXTURE：可选，覆盖演示 CSV 路径（默认：demo/minimal_demo.csv）

输出：
- 在 demo_outputs/ 下生成：
  - *_apa_table.xlsx
  - *_apa_report.docx
  - *_model.lavaan.txt
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def _base_url() -> str:
    return os.getenv("OPENSEM_BASE_URL", "http://127.0.0.1:8020").rstrip("/")


def _fixture_path() -> Path:
    env = os.getenv("OPENSEM_DEMO_FIXTURE")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve().parent
    return (here / "minimal_demo.csv").resolve()


def _out_dir() -> Path:
    here = Path(__file__).resolve().parent
    p = (here / "demo_outputs").resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _get_json(path: str, timeout: int = 60) -> dict:
    url = f"{_base_url()}{path}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_json(path: str, payload: dict, timeout: int = 300) -> dict:
    url = f"{_base_url()}{path}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_json_bytes(path: str, payload: dict, timeout: int = 300) -> bytes:
    url = f"{_base_url()}{path}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _post_multipart_parse(file_path: Path) -> dict:
    boundary = f"----OpenSEMDemo{uuid.uuid4().hex[:16]}"
    content = file_path.read_bytes()
    filename = file_path.name.encode("ascii", errors="replace")
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="file"; filename="',
            filename,
            b'"\r\nContent-Type: text/csv\r\n\r\n',
            content,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    url = f"{_base_url()}/api/v1/data/parse"
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _poll_task(task_id: str, *, label: str, timeout_s: int = 240) -> dict:
    deadline = time.monotonic() + timeout_s
    last: dict | None = None
    while time.monotonic() < deadline:
        last = _get_json(f"/api/v1/tasks/status/{task_id}")
        if last.get("ready"):
            if not last.get("successful"):
                raise RuntimeError(f"{label} 任务失败: {last}")
            out = last.get("result")
            if not isinstance(out, dict):
                raise RuntimeError(f"{label} 结果格式异常: {last}")
            return out
        time.sleep(1)
    raise TimeoutError(f"{label} 轮询超时，最后状态: {last}")


def main() -> int:
    fixture = _fixture_path()
    if not fixture.is_file():
        print(f"缺少演示数据: {fixture}", file=sys.stderr)
        return 2

    health = _get_json("/api/health")
    if health.get("status") != "healthy":
        print(f"健康检查异常: {health}", file=sys.stderr)
        return 1
    print("Health ok:", {"mode": health.get("mode"), "lavaan": (health.get("lavaan") or {}).get("available")})

    # 1) 上传
    parsed = _post_multipart_parse(fixture)
    data_key = parsed.get("data_key")
    if not data_key:
        print(f"解析无 data_key: {parsed}", file=sys.stderr)
        return 1
    print("Upload ok:", "data_key=", data_key)

    # 1b) 有调节的中介（观测 OLS，可回归：分类 W Model 7 + 连续 W Model 14）
    mm_cat = _post_json(
        "/api/v1/tasks/moderated-mediation",
        {
            "data_key": data_key,
            "x": "q1",
            "m": "q2",
            "y": "s1",
            "w": "g",
            "w_type": "categorical",
            "hayes_model": "7",
            "n_boot": 200,
            "ci_level": 0.95,
            "missing_strategy": "listwise",
        },
        timeout=60,
    )
    tid_mm = mm_cat.get("task_id")
    if not tid_mm:
        print(f"moderated-mediation 未返回 task_id: {mm_cat}", file=sys.stderr)
        return 1
    mm_res = _poll_task(tid_mm, label="moderated-mediation (Model7 cat W)", timeout_s=120)
    if not isinstance(mm_res, dict) or mm_res.get("success") is not True:
        print(f"moderated-mediation 失败: {mm_res}", file=sys.stderr)
        return 1
    print(
        "moderated-mediation Model7 categorical ok:",
        "model=",
        mm_res.get("model"),
        "n=",
        mm_res.get("n_used"),
    )

    mm14 = _post_json(
        "/api/v1/tasks/moderated-mediation",
        {
            "data_key": data_key,
            "x": "q1",
            "m": "q2",
            "y": "s1",
            "w": "q3",
            "w_type": "continuous",
            "hayes_model": "14",
            "n_boot": 200,
            "ci_level": 0.95,
            "missing_strategy": "listwise",
        },
        timeout=60,
    )
    tid14 = mm14.get("task_id")
    if not tid14:
        print(f"moderated-mediation M14 未返回 task_id: {mm14}", file=sys.stderr)
        return 1
    mm14_res = _poll_task(tid14, label="moderated-mediation (Model14)", timeout_s=120)
    if not isinstance(mm14_res, dict) or mm14_res.get("success") is not True:
        print(f"moderated-mediation Model14 失败: {mm14_res}", file=sys.stderr)
        return 1
    print(
        "moderated-mediation Model14 ok:",
        "model=",
        mm14_res.get("model"),
        "n=",
        mm14_res.get("n_used"),
    )

    # 2) 表单建模 -> lavaan 语法（最小）
    model_payload = {
        "data_key": data_key,
        "latent_vars": [
            {"name": "F1", "indicators": ["q1", "q2", "q3", "q4", "q5"]},
            {"name": "F2", "indicators": ["s1", "s2", "s3"]},
        ],
        "paths": [{"from_var": "F2", "to_var": "F1"}],
        "error_covariances": [],
    }
    to_lavaan = _post_json("/api/v1/model/to-lavaan", model_payload, timeout=60)
    lavaan_syntax = (to_lavaan.get("lavaan_syntax") or "").strip()
    if not lavaan_syntax:
        print(f"to-lavaan 未返回 lavaan_syntax: {to_lavaan}", file=sys.stderr)
        return 1
    print("to-lavaan ok")

    # 3) 异步估算（沿用 tasks 轮询链路）
    submit = _post_json(
        "/api/v1/tasks/stats-fit",
        {"data_key": data_key, "lavaan_syntax": lavaan_syntax, "estimator": "ML", "missing_strategy": "fiml"},
        timeout=60,
    )
    task_id = submit.get("task_id")
    if not task_id:
        print(f"未返回 task_id: {submit}", file=sys.stderr)
        return 1
    print("stats-fit submitted:", "task_id=", task_id)

    fit = _poll_task(task_id, label="stats-fit", timeout_s=240)
    if fit.get("success") is not True:
        print(f"拟合未成功: {fit}", file=sys.stderr)
        return 1

    fit_indices = fit.get("fit_indices")
    estimates = fit.get("estimates")
    if not isinstance(fit_indices, dict) or not isinstance(estimates, list):
        print(f"拟合结果缺失 fit_indices/estimates: {fit}", file=sys.stderr)
        return 1
    print("stats-fit ok:", {"status": fit_indices.get("status"), "n_estimates": len(estimates)})

    # 4) 导出（xlsx/docx/txt）并落盘
    now = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    out_dir = _out_dir()
    export_payload = {
        "data_key": data_key,
        "lavaan_syntax": lavaan_syntax,
        "fit_indices": fit_indices,
        "estimator": fit.get("estimator") or "ML",
        "missing_strategy": fit.get("missing_strategy") or "fiml",
        "fit_ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "estimates": estimates,
        "bootstrap": None,
        "invariance": None,
        "invariance_series": None,
        "project_name": "OpenSEM_Min_Demo",
        "fit_stale": False,
        "allow_stale_export": False,
    }

    xlsx = _post_json_bytes("/api/v1/export/apa-table", export_payload, timeout=180)
    docx = _post_json_bytes("/api/v1/export/apa-table-docx", export_payload, timeout=180)
    txt = _post_json_bytes("/api/v1/export/lavaan-syntax", export_payload, timeout=60)

    xlsx_path = out_dir / f"{now}_apa_table.xlsx"
    docx_path = out_dir / f"{now}_apa_report.docx"
    txt_path = out_dir / f"{now}_model.lavaan.txt"
    xlsx_path.write_bytes(xlsx)
    docx_path.write_bytes(docx)
    txt_path.write_bytes(txt)

    print("Export ok:")
    print(" -", xlsx_path)
    print(" -", docx_path)
    print(" -", txt_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        raise SystemExit(1) from e
    except Exception as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(1) from e

