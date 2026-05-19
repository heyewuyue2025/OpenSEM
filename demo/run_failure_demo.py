#!/usr/bin/env python3
"""
失败演示脚本（交付演示/排障）：
复现 3 个典型失败分支并输出结构化结果。

覆盖分支：
1) validate-key 失效 data_key -> valid=false
2) 导出接口无效 data_key -> 400 + EXPORT_DATA_KEY_INVALID
3) model-compare 参数非法 -> 422 + VALIDATION_ERROR

环境变量：
- OPENSEM_BASE_URL（默认 http://127.0.0.1:8020）
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import uuid


def _base_url() -> str:
    return os.getenv("OPENSEM_BASE_URL", "http://127.0.0.1:8020").rstrip("/")


def _post_json(path: str, payload: dict, timeout: int = 120) -> dict:
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


def _post_json_status(path: str, payload: dict, timeout: int = 120) -> tuple[int, dict]:
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
        return int(e.code), body if isinstance(body, dict) else {}


def _detail_code(body: dict) -> str:
    detail = body.get("detail")
    if isinstance(detail, dict):
        return str(detail.get("code") or "")
    return ""


def collect_failure_cases() -> dict[str, dict]:
    fake_key = str(uuid.uuid4())
    validate_resp = _post_json("/api/v1/data/validate-key", {"data_key": fake_key}, timeout=60)
    export_status, export_body = _post_json_status(
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
    compare_status, compare_body = _post_json_status(
        "/api/v1/tasks/model-compare",
        {
            "data_key": fake_key,
            "lavaan_syntax_a": "F1 =~ q1",
            "lavaan_syntax_b": "F1 =~ q1 + q2",
            "estimator": "ULS",
        },
        timeout=60,
    )
    return {
        "validate_key_invalid": {"status": 200, "body": validate_resp},
        "export_invalid_key": {"status": export_status, "body": export_body},
        "model_compare_validation_error": {"status": compare_status, "body": compare_body},
    }


def check_failure_contract(cases: dict[str, dict]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    validate_case = cases.get("validate_key_invalid") or {}
    if (validate_case.get("body") or {}).get("valid") is not False:
        issues.append(f"validate-key 预期 valid=false，实际: {validate_case}")

    export_case = cases.get("export_invalid_key") or {}
    export_code = _detail_code(export_case.get("body") or {})
    if export_case.get("status") != 400 or export_code != "EXPORT_DATA_KEY_INVALID":
        issues.append(
            "export 预期 400 + EXPORT_DATA_KEY_INVALID，"
            f"实际 status={export_case.get('status')} code={export_code or '<empty>'}"
        )

    compare_case = cases.get("model_compare_validation_error") or {}
    compare_code = _detail_code(compare_case.get("body") or {})
    if compare_case.get("status") != 422 or compare_code != "VALIDATION_ERROR":
        issues.append(
            "model-compare 预期 422 + VALIDATION_ERROR，"
            f"实际 status={compare_case.get('status')} code={compare_code or '<empty>'}"
        )
    return len(issues) == 0, issues


def main() -> int:
    cases = collect_failure_cases()
    ok, issues = check_failure_contract(cases)
    print(json.dumps({"ok": ok, "cases": cases, "issues": issues}, ensure_ascii=False, indent=2))
    if not ok:
        for item in issues:
            print(item, file=sys.stderr)
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
