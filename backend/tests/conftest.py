"""
Pytest 配置：确保在任意工作目录运行 pytest 时，都能导入 backend/app 下的包。

背景：
- 从仓库根目录执行 `pytest` 时，`from app.main import app` 可能因为 sys.path 不含 backend 而失败。
- 该文件把 backend 目录加入 sys.path，避免依赖用户手动设置 PYTHONPATH。
"""

import sys
from pathlib import Path


def _ensure_backend_on_syspath() -> None:
    backend_dir = Path(__file__).resolve().parents[1]  # .../backend
    backend_dir_str = str(backend_dir)
    if backend_dir_str not in sys.path:
        sys.path.insert(0, backend_dir_str)


_ensure_backend_on_syspath()

