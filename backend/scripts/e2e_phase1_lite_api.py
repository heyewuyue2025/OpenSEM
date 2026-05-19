#!/usr/bin/env python3
"""
Phase 1（MVP）在 Docker lite（仅 semopy）下的端到端验收：

- /api/health 必须为 healthy + mode=lite
- 上传 -> 表单建模(to-lavaan) -> 异步拟合(tasks/stats-fit) -> 导出三件套(xlsx/docx/txt)

环境变量：
  OPENSEM_BASE_URL  默认 http://127.0.0.1:8020
  OPENSEM_E2E_FIXTURE  可选，CSV 路径（默认：backend/tests/fixtures/e2e_mg_sample.csv）

若本机对 127.0.0.1 走了 HTTP 代理导致 urllib 收到 502，可设置 NO_PROXY=127.0.0.1,localhost 后再运行。
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET


def _base_url() -> str:
    return os.getenv("OPENSEM_BASE_URL", "http://127.0.0.1:8020").rstrip("/")


def _fixture_path() -> Path:
    env = os.getenv("OPENSEM_E2E_FIXTURE")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve().parent
    return (here.parent / "tests" / "fixtures" / "e2e_mg_sample.csv").resolve()


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
    boundary = f"----OpenSEMPhase1E2E{uuid.uuid4().hex[:16]}"
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


def _xlsx_has_sheet(xlsx_bytes: bytes, sheet_name: str) -> bool:
    if not xlsx_bytes:
        return False
    try:
        with zipfile.ZipFile(BytesIO(xlsx_bytes), "r") as zf:
            if "xl/workbook.xml" not in zf.namelist():
                return False
            wb = ET.fromstring(zf.read("xl/workbook.xml"))
            ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            for s in wb.findall(".//m:sheets/m:sheet", ns):
                if s.attrib.get("name") == sheet_name:
                    return True
            return False
    except Exception:
        return False


def _docx_contains_text(docx_bytes: bytes, needle: str) -> bool:
    if not docx_bytes:
        return False
    try:
        with zipfile.ZipFile(BytesIO(docx_bytes), "r") as zf:
            if "word/document.xml" not in zf.namelist():
                return False
            xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
            return needle in xml
    except Exception:
        return False


def main() -> int:
    fixture = _fixture_path()
    if not fixture.is_file():
        print(f"缺少样例数据: {fixture}", file=sys.stderr)
        return 2

    # 0) health（lite）
    health = _get_json("/api/health")
    if health.get("status") != "healthy" or health.get("mode") != "lite":
        print(f"lite 健康检查异常: {health}", file=sys.stderr)
        return 1

    # 1) 上传
    parsed = _post_multipart_parse(fixture)
    data_key = parsed.get("data_key")
    if not data_key:
        print(f"解析无 data_key: {parsed}", file=sys.stderr)
        return 1

    # 2) 表单建模 -> lavaan 语法
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

    # 3) 异步拟合（stats-fit）
    submit = _post_json(
        "/api/v1/tasks/stats-fit",
        {"data_key": data_key, "lavaan_syntax": lavaan_syntax, "estimator": "ML", "missing_strategy": "fiml"},
        timeout=60,
    )
    task_id = submit.get("task_id")
    if not task_id:
        print(f"未返回 task_id: {submit}", file=sys.stderr)
        return 1

    fit = _poll_task(task_id, label="stats-fit", timeout_s=240)
    if fit.get("success") is not True:
        print(f"拟合未成功: {fit}", file=sys.stderr)
        return 1
    fit_indices = fit.get("fit_indices")
    if not isinstance(fit_indices, dict) or not fit_indices.get("status"):
        print(f"fit_indices 缺失或不完整: {fit}", file=sys.stderr)
        return 1
    estimates = fit.get("estimates")
    if not isinstance(estimates, list):
        print(f"estimates 非数组: {fit}", file=sys.stderr)
        return 1

    # 4) 导出三件套
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
        "project_name": "OpenSEM_Phase1_Lite_E2E",
        # 避免导出门禁误触发（Phase 1 以“非 stale”验收）
        "fit_stale": False,
        "allow_stale_export": False,
    }

    xlsx = _post_json_bytes("/api/v1/export/apa-table", export_payload, timeout=180)
    if not xlsx:
        print("xlsx 导出为空", file=sys.stderr)
        return 1
    for name in ("Fit_Indices", "Model_Syntax", "Meta"):
        if not _xlsx_has_sheet(xlsx, name):
            print(f"xlsx 缺少 sheet: {name}", file=sys.stderr)
            return 1

    docx = _post_json_bytes("/api/v1/export/apa-table-docx", export_payload, timeout=180)
    if not docx:
        print("docx 导出为空", file=sys.stderr)
        return 1
    if not _docx_contains_text(docx, "OpenSEM APA Report"):
        print("docx 未包含预期标题文本：OpenSEM APA Report", file=sys.stderr)
        return 1

    txt = _post_json_bytes("/api/v1/export/lavaan-syntax", export_payload, timeout=60)
    if not txt:
        print("lavaan txt 导出为空", file=sys.stderr)
        return 1

    print("Phase 1 lite e2e ok")
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

