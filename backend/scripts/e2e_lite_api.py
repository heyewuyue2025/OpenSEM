#!/usr/bin/env python3
"""
Lite 模式下的最小 e2e：
- /api/health 应为 healthy + mode=lite
- MI / 不变性序列应明确降级（supported:false / mode:degraded）且不崩溃

环境变量：
  OPENSEM_BASE_URL  默认 http://127.0.0.1:8020
  OPENSEM_E2E_FIXTURE  可选，CSV 路径（默认：backend/tests/fixtures/e2e_mg_sample.csv）
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


def _post_multipart_parse(file_path: Path) -> dict:
    boundary = f"----OpenSEMLiteE2E{uuid.uuid4().hex[:16]}"
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


def _poll_task(task_id: str, *, label: str, timeout_s: int = 180) -> dict:
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
        print(f"缺少样例数据: {fixture}", file=sys.stderr)
        return 2

    health = _get_json("/api/health")
    if health.get("status") != "healthy" or health.get("mode") != "lite":
        print(f"lite 健康检查异常: {health}", file=sys.stderr)
        return 1

    parsed = _post_multipart_parse(fixture)
    data_key = parsed.get("data_key")
    if not data_key:
        print(f"解析无 data_key: {parsed}", file=sys.stderr)
        return 1

    lavaan_syntax = (
        "F1 =~ q1 + q2 + q3 + q4 + q5\n"
        "F2 =~ s1 + s2 + s3\n"
        "F1 ~ F2"
    )

    # MI（lite 下“不强制 lavaan”，因此 supported 可能为 true 或 false；关键是“不崩 + 结构可解释”）
    mi = _post_json(
        "/api/v1/stats/mi",
        {"data_key": data_key, "lavaan_syntax": lavaan_syntax, "top_k": 5, "mi_threshold": 3.84},
        timeout=120,
    )
    if mi.get("supported") is True:
        if not isinstance(mi.get("items"), list):
            print(f"MI supported=true 但 items 非列表: {mi}", file=sys.stderr)
            return 1
        print("MI supported ok:", "items=", len(mi.get("items") or []))
    elif mi.get("supported") is False:
        if not mi.get("message"):
            print(f"MI supported=false 但缺少 message: {mi}", file=sys.stderr)
            return 1
        print("MI degraded ok")
    else:
        print(f"MI supported 字段异常: {mi}", file=sys.stderr)
        return 1

    submit = _post_json(
        "/api/v1/tasks/invariance-lavaan-series",
        {"data_key": data_key, "lavaan_syntax": lavaan_syntax, "group_var": "g", "missing_strategy": "fiml"},
        timeout=60,
    )
    task_id = submit.get("task_id")
    if not task_id:
        print(f"未返回 task_id: {submit}", file=sys.stderr)
        return 1

    inv = _poll_task(task_id, label="invariance-lavaan-series", timeout_s=180)
    if inv.get("supported") is False or inv.get("mode") == "degraded":
        if not inv.get("message"):
            print(f"不变性序列降级但缺少 message：{inv}", file=sys.stderr)
            return 1
        # Epic2 契约：降级也要保持 4+3 + delta_rmsea 字段稳定
        models = inv.get("models") or []
        comparisons = inv.get("comparisons") or []
        if len(models) != 4:
            print(f"不变性序列降级时 models 应为 4 行，实际：{len(models)}; inv={inv}", file=sys.stderr)
            return 1
        if len(comparisons) != 3:
            print(f"不变性序列降级时 comparisons 应为 3 行，实际：{len(comparisons)}; inv={inv}", file=sys.stderr)
            return 1
        if any(isinstance(c, dict) and ("delta_rmsea" not in c) for c in comparisons):
            print(f"不变性序列降级时 comparisons 缺少 delta_rmsea 字段: {comparisons}", file=sys.stderr)
            return 1
        print("Invariance series degraded ok")
    elif inv.get("supported") is True:
        models = inv.get("models") or []
        comparisons = inv.get("comparisons") or []
        if len(models) < 4:
            print(f"不变性序列 supported=true 但 models 不足 4：{inv}", file=sys.stderr)
            return 1
        if len(comparisons) != 3:
            print(f"不变性序列 comparisons 应为 3 行，实际：{len(comparisons)}", file=sys.stderr)
            return 1
        if any(isinstance(c, dict) and ("delta_rmsea" not in c) for c in comparisons):
            print(f"不变性序列 comparisons 缺少 delta_rmsea 字段: {comparisons}", file=sys.stderr)
            return 1
        print("Invariance series supported ok:", "models=", len(models), "comparisons=", len(comparisons))
    else:
        print(f"不变性序列 supported 字段异常：{inv}", file=sys.stderr)
        return 1
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

