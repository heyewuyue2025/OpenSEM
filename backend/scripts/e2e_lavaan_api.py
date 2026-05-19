#!/usr/bin/env python3
"""
通过真实 HTTP 调用验证：数据上传 -> MI(lavaan) -> 多群组不变性序列(lavaan 长任务)。

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


def _get_json(path: str, timeout: int = 60) -> dict:
    url = f"{_base_url()}{path}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_multipart_parse(file_path: Path) -> dict:
    boundary = f"----OpenSEME2E{uuid.uuid4().hex[:16]}"
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


def _poll_task(task_id: str, *, label: str, timeout_s: int = 300) -> dict:
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
        time.sleep(2)
    raise TimeoutError(f"{label} 轮询超时，最后状态: {last}")

def _xlsx_sheet_headers(xlsx_bytes: bytes, sheet_name: str) -> list[str]:
    """
    无第三方依赖提取 xlsx 的某个 sheet 第一行（header row）文本。
    仅用于 e2e 验收：校验 sheet 存在、列名稳定。
    """
    if not xlsx_bytes:
        raise ValueError("xlsx 内容为空")

    def _xml(path: str) -> ET.Element:
        raw = zf.read(path)
        return ET.fromstring(raw)

    def _ns(tag: str, ns_uri: str) -> str:
        return f"{{{ns_uri}}}{tag}"

    with zipfile.ZipFile(BytesIO(xlsx_bytes), "r") as zf:
        if "xl/workbook.xml" not in zf.namelist():
            raise ValueError("xlsx 缺少 xl/workbook.xml")
        if "xl/_rels/workbook.xml.rels" not in zf.namelist():
            raise ValueError("xlsx 缺少 xl/_rels/workbook.xml.rels")

        wb = _xml("xl/workbook.xml")
        rels = _xml("xl/_rels/workbook.xml.rels")

        # Collect shared strings (optional but typical)
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            ss = _xml("xl/sharedStrings.xml")
            ns_ss = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            for si in ss.findall(f".//{_ns('si', ns_ss)}"):
                texts: list[str] = []
                for t in si.findall(f".//{_ns('t', ns_ss)}"):
                    if t.text:
                        texts.append(t.text)
                shared.append("".join(texts))

        ns_wb = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        ns_rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        ns_rels = "http://schemas.openxmlformats.org/package/2006/relationships"

        sheet_el = None
        for s in wb.findall(f".//{_ns('sheet', ns_wb)}"):
            if s.attrib.get("name") == sheet_name:
                sheet_el = s
                break
        if sheet_el is None:
            raise ValueError(f"xlsx 缺少 sheet: {sheet_name}")

        rid = sheet_el.attrib.get(_ns("id", ns_rel))
        if not rid:
            raise ValueError(f"sheet {sheet_name} 缺少 r:id")

        target = None
        for r in rels.findall(f".//{_ns('Relationship', ns_rels)}"):
            if r.attrib.get("Id") == rid:
                target = r.attrib.get("Target")
                break
        if not target:
            raise ValueError(f"sheet {sheet_name} 无法从 rels 找到 Target")

        # Target can be either 'worksheets/sheet5.xml' or 'xl/worksheets/sheet5.xml' depending on producer.
        t = target.lstrip("/")
        sheet_path = t if t.startswith("xl/") else ("xl/" + t)
        if sheet_path not in zf.namelist():
            raise ValueError(f"sheet xml 不存在: {sheet_path}")

        sh = _xml(sheet_path)

        # First row in sheetData
        row = sh.find(f".//{_ns('sheetData', ns_wb)}/{_ns('row', ns_wb)}")
        if row is None:
            raise ValueError(f"sheet {sheet_name} 没有任何行")

        def _cell_text(c: ET.Element) -> str:
            t = c.attrib.get("t")  # 's' for shared string, 'inlineStr' for inline string
            if t == "inlineStr":
                is_el = c.find(_ns("is", ns_wb))
                if is_el is None:
                    return ""
                # inlineStr may have multiple t nodes (rich text)
                texts: list[str] = []
                for t_el in is_el.findall(f".//{_ns('t', ns_wb)}"):
                    if t_el.text:
                        texts.append(t_el.text)
                return "".join(texts)

            v = c.find(_ns("v", ns_wb))
            if v is None or v.text is None:
                return ""
            raw = v.text
            if t == "s":
                try:
                    idx = int(raw)
                    return shared[idx] if 0 <= idx < len(shared) else ""
                except Exception:
                    return ""
            return raw

        headers: list[str] = []
        for c in row.findall(_ns("c", ns_wb)):
            headers.append(_cell_text(c).strip())
        # 过滤空列（例如 pandas 写出的尾部空单元格）
        headers = [h for h in headers if h]
        if not headers:
            raise ValueError(f"sheet {sheet_name} header 为空")
        return headers


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

    # 0) 健康检查（强门禁环境下应 lavaan 可用）
    health = _get_json("/api/health")
    if health.get("status") != "healthy":
        print(f"健康检查异常: {health}", file=sys.stderr)
        return 1
    if not health.get("lavaan", {}).get("available"):
        print(f"lavaan 不可用: {health}", file=sys.stderr)
        return 1

    # 1) 上传数据
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

    # 2) MI（同步）
    mi = _post_json(
        "/api/v1/stats/mi",
        {
            "data_key": data_key,
            "lavaan_syntax": lavaan_syntax,
            "top_k": 10,
            "mi_threshold": 3.84,
        },
        timeout=300,
    )
    if not mi.get("supported"):
        print(f"MI 未启用: {mi}", file=sys.stderr)
        return 1
    if not isinstance(mi.get("items"), list):
        print(f"MI 返回缺少 items 列表: {mi}", file=sys.stderr)
        return 1
    print("MI ok:", "items=", len(mi["items"]))

    # 3) 不变性序列（异步 + 轮询）
    submit = _post_json(
        "/api/v1/tasks/invariance-lavaan-series",
        {
            "data_key": data_key,
            "lavaan_syntax": lavaan_syntax,
            "group_var": "g",
            "missing_strategy": "fiml",
        },
        timeout=60,
    )
    task_id = submit.get("task_id")
    if not task_id:
        print(f"未返回 task_id: {submit}", file=sys.stderr)
        return 1

    inv = _poll_task(task_id, label="invariance-lavaan-series", timeout_s=300)
    if inv.get("supported") is False:
        print(f"不变性序列未支持: {inv}", file=sys.stderr)
        return 1
    if inv.get("success") is False:
        print(f"不变性序列未成功: {inv}", file=sys.stderr)
        return 1
    models = inv.get("models") or []
    if len(models) < 4:
        print(f"不变性序列 models 不足 4 层: {inv}", file=sys.stderr)
        return 1
    comparisons = inv.get("comparisons") or []
    print("Invariance series ok: models=", len(models), "comparisons=", len(comparisons))
    if len(comparisons) != 3:
        print(f"不变性序列 comparisons 应固定为 3 行，实际：{len(comparisons)}", file=sys.stderr)
        return 1
    # delta_rmsea 必须存在（可为 null，但字段要有）
    if any(isinstance(c, dict) and ("delta_rmsea" not in c) for c in comparisons):
        print(f"不变性序列 comparisons 缺少 delta_rmsea 字段: {comparisons}", file=sys.stderr)
        return 1

    # 4) 导出（xlsx/docx）：校验 sheet 存在与列稳定（含 delta_rmsea）
    export_payload = {
        "data_key": data_key,
        "lavaan_syntax": lavaan_syntax,
        "fit_indices": None,  # e2e 只验证导出契约，不强行依赖 fit
        "estimator": "ML",
        "missing_strategy": "fiml",
        "fit_ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "estimates": [],
        "bootstrap": None,
        "invariance": None,
        "invariance_series": inv,
        "project_name": "OpenSEM_E2E",
    }

    xlsx = _post_json_bytes("/api/v1/export/apa-table", export_payload, timeout=300)
    # 必验：两张 invariance series sheet 存在且 header 契约一致
    models_header = _xlsx_sheet_headers(xlsx, "Invariance_Series_Models")
    lrt_header = _xlsx_sheet_headers(xlsx, "Invariance_Series_LRT")
    expected_models = ["model", "group_equal", "chi2", "df", "cfi", "tli", "rmsea", "srmr", "converged"]
    expected_lrt = ["from", "to", "ok", "chi2_diff", "df_diff", "p_value", "delta_cfi", "delta_rmsea", "note"]
    if models_header[: len(expected_models)] != expected_models:
        print(f"xlsx Models header 不匹配。\nexpected={expected_models}\nactual={models_header}", file=sys.stderr)
        return 1
    if lrt_header[: len(expected_lrt)] != expected_lrt:
        print(f"xlsx LRT header 不匹配。\nexpected={expected_lrt}\nactual={lrt_header}", file=sys.stderr)
        return 1

    docx = _post_json_bytes("/api/v1/export/apa-table-docx", export_payload, timeout=300)
    # docx 验证：至少能导出且包含 delta_rmsea（表头文本）
    if not _docx_contains_text(docx, "delta_rmsea"):
        print("docx 不包含 delta_rmsea（表头/内容），导出口径可能回退", file=sys.stderr)
        return 1
    # 加固导出契约：docx 表头与 xlsx 契约关键字段一致（至少要出现 ok/note/converged）
    for key in ("ok", "note", "converged"):
        if not _docx_contains_text(docx, key):
            print(f"docx 不包含 {key}（表头/内容），导出契约可能与 xlsx 不一致", file=sys.stderr)
            return 1

    print("Export ok: xlsx sheets+headers stable; docx contains delta_rmsea")
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
