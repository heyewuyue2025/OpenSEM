#!/usr/bin/env python3
"""
闸门 G3：OpenSEM 1.4 文档勾选对账（可执行）

复跑 `1.4版本推进.md` 证据表中已登记的自动化命令，确保每条 [√] 对应的测试仍可通过。
无需 Docker；E2E（需运行中的 API）请单独执行 `backend/scripts/e2e_main_minimal.py`。

用法（仓库根目录）：
  python scripts/verify_opensem_1_4_evidence.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _npm_executable() -> str:
    """Windows 上 PATH 常为 npm.cmd，需显式解析。"""
    n = shutil.which("npm") or shutil.which("npm.cmd")
    return n or "npm"


ROOT = Path(__file__).resolve().parent.parent


def _run(name: str, cwd: Path, cmd: list[str]) -> int:
    print(f"\n== {name} ==\n$ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(cwd))
    if proc.returncode != 0:
        print(f"FAIL: {name} (exit {proc.returncode})", file=sys.stderr)
    return int(proc.returncode)


def main() -> int:
    rc = 0

    rc |= _run(
        "frontend: uiFeedback + dialogStore + miGuard",
        ROOT / "frontend",
        [
            _npm_executable(),
            "run",
            "test",
            "--",
            "src/utils/uiFeedback.test.js",
            "src/stores/dialogStore.test.js",
            "src/mi/miGuard.test.js",
        ],
    )

    rc |= _run(
        "backend: tasks validation contract",
        ROOT / "backend",
        ["python", "-m", "pytest", "tests/test_tasks_validation_contract.py", "-q"],
    )

    rc |= _run(
        "backend: export combo contract",
        ROOT / "backend",
        ["python", "-m", "pytest", "tests/test_export_contract_combo.py", "-q"],
    )

    rc |= _run(
        "backend: failure demo script contract",
        ROOT / "backend",
        ["python", "-m", "pytest", "tests/test_failure_demo_script.py", "-q"],
    )

    if rc == 0:
        print(
            "\nverify_opensem_1_4_evidence: OK (unit/contract only; Docker E2E: see 1.4 doc evidence table)"
        )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
