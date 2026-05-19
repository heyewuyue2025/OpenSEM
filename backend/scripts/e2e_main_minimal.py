#!/usr/bin/env python3
"""
闸门 G2：主流程 HTTP E2E 最小集（成功 + 失败分支）

成功路径：委托 `e2e_phase1_lite_api.py`（上传 → to-lavaan → stats-fit → 导出三件套）。

失败路径（不依赖具体随机 data_key，顺序执行）：
  1) data_key 失效：validate-key 返回 valid=false
  2) 导出 data_key 无效：POST /api/v1/export/apa-table → 400 + EXPORT_DATA_KEY_INVALID
  3) 任务参数非法：POST /api/v1/tasks/model-compare → 422 + VALIDATION_ERROR
  4) 估算任务失败：stats-fit 使用不可识别语法，轮询 ready 且 successful=false，
     error 存在且不包含裸露 Traceback（与 tasks._sanitize_task_error_message 口径一致）

环境变量：
  OPENSEM_BASE_URL  默认 http://127.0.0.1:8020
  OPENSEM_E2E_FIXTURE  传给 Phase1 子进程（可选）

若本机对 127.0.0.1 走了 HTTP 代理导致 urllib 收到 502，可设置 NO_PROXY=127.0.0.1,localhost 后再运行。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def _base_url() -> str:
    return os.getenv("OPENSEM_BASE_URL", "http://127.0.0.1:8020").rstrip("/")


def _script_dir() -> Path:
    return Path(__file__).resolve().parent


def _fixture_path() -> Path:
    env = os.getenv("OPENSEM_E2E_FIXTURE")
    if env:
        return Path(env).resolve()
    return (_script_dir().parent / "tests" / "fixtures" / "e2e_mg_sample.csv").resolve()


def _post_multipart_parse(file_path: Path) -> dict:
    boundary = f"----OpenSEMMainE2E{uuid.uuid4().hex[:16]}"
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


def _post_json_error(path: str, payload: dict, timeout: int = 120) -> tuple[int, dict]:
    """POST JSON，返回 (HTTP 状态码, 解析后的 JSON body)。"""
    url = f"{_base_url()}{path}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            body = json.loads(raw) if raw.strip() else {}
            return resp.getcode(), body if isinstance(body, dict) else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            body = {"_raw": raw}
        return e.code, body if isinstance(body, dict) else {}


def _run_phase1_success() -> int:
    phase1 = _script_dir() / "e2e_phase1_lite_api.py"
    env = os.environ.copy()
    # 继承 OPENSEM_BASE_URL / OPENSEM_E2E_FIXTURE
    proc = subprocess.run(
        [sys.executable, str(phase1)],
        cwd=str(_script_dir().parent.parent),
        env=env,
    )
    return int(proc.returncode)


def _detail_code(body: dict) -> str | None:
    d = body.get("detail")
    if isinstance(d, dict):
        return str(d.get("code") or "")
    return None


def _failure_branches() -> int:
    fake_key = str(uuid.uuid4())

    # 1) validate-key：失效 data_key
    vk = _post_json("/api/v1/data/validate-key", {"data_key": fake_key}, timeout=60)
    if vk.get("valid") is not False:
        print(f"validate-key 应对失效 key 返回 valid=false: {vk}", file=sys.stderr)
        return 1

    # 2) 导出：无效 data_key
    code, body = _post_json_error(
        "/api/v1/export/apa-table",
        {
            "data_key": fake_key,
            "lavaan_syntax": "F1 =~ q1",
            "fit_indices": {"status": "ok"},
            "estimates": [],
            "fit_stale": False,
        },
        timeout=120,
    )
    if code != 400 or _detail_code(body) != "EXPORT_DATA_KEY_INVALID":
        print(f"导出无效 data_key 预期 400+EXPORT_DATA_KEY_INVALID，实际 {code} {body}", file=sys.stderr)
        return 1

    # 3) 422：model-compare 非法 estimator
    code, body = _post_json_error(
        "/api/v1/tasks/model-compare",
        {
            "data_key": fake_key,
            "lavaan_syntax_a": "F1 =~ q1",
            "lavaan_syntax_b": "F1 =~ q1 + q2",
            "estimator": "ULS",
        },
        timeout=60,
    )
    if code != 422 or _detail_code(body) != "VALIDATION_ERROR":
        print(f"model-compare 非法参数预期 422+VALIDATION_ERROR，实际 {code} {body}", file=sys.stderr)
        return 1

    # 4) 任务失败：先解析真实数据，再提交必败语法
    fixture = _fixture_path()
    if not fixture.is_file():
        print(f"缺少样例数据: {fixture}", file=sys.stderr)
        return 2

    parsed = _post_multipart_parse(fixture)
    data_key = parsed.get("data_key")
    if not data_key:
        print(f"解析无 data_key: {parsed}", file=sys.stderr)
        return 1

    bad_syntax = "FactorBad =~ this_column_does_not_exist_zzz"
    submit = _post_json(
        "/api/v1/tasks/stats-fit",
        {
            "data_key": data_key,
            "lavaan_syntax": bad_syntax,
            "estimator": "ML",
            "missing_strategy": "fiml",
        },
        timeout=60,
    )
    task_id = submit.get("task_id")
    if not task_id:
        print(f"未返回 task_id: {submit}", file=sys.stderr)
        return 1

    deadline = time.monotonic() + 180
    last: dict | None = None
    while time.monotonic() < deadline:
        last = _get_json(f"/api/v1/tasks/status/{task_id}")
        if last.get("ready"):
            break
        time.sleep(1)
    else:
        print(f"stats-fit 失败分支轮询超时: {last}", file=sys.stderr)
        return 1

    if last is None or last.get("successful") is not False:
        print(f"预期任务失败，实际状态: {last}", file=sys.stderr)
        return 1
    err = (last.get("error") or "").strip()
    if not err:
        print(f"失败任务缺少 error 字段: {last}", file=sys.stderr)
        return 1
    if "Traceback" in err and "File \"" in err:
        print(f"error 仍含技术 Traceback（应被清洗）: {err[:500]}", file=sys.stderr)
        return 1

    print("e2e main minimal: failure branches ok")
    return 0


def main() -> int:
    health = _get_json("/api/health")
    if health.get("status") != "healthy":
        print(f"健康检查异常: {health}", file=sys.stderr)
        return 1
    if health.get("mode") != "lite":
        print(f"本脚本面向 Docker lite（mode=lite），当前: {health}", file=sys.stderr)
        return 1

    rc = _run_phase1_success()
    if rc != 0:
        return rc

    rc = _failure_branches()
    if rc == 0:
        print("e2e main minimal: all ok (phase1 success + failure branches)")
    return rc


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
