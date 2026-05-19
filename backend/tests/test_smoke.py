"""API 冒烟：确保应用可导入且核心路由可响应（CI 门禁）。"""

import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert "version" in body


def test_health():
    r = client.get("/api/health")
    # 默认本地/CI 可能不要求 lavaan；Docker 生产态会通过 OPENSEM_REQUIRE_LAVAAN=1 开启强门禁
    require = str(os.getenv("OPENSEM_REQUIRE_LAVAAN", "0")).strip() in ("1", "true", "True", "YES", "yes")
    body = r.json()
    if require:
        # strict：若 require_lavaan=true 且 lavaan 不可用，则 /api/health 返回 503（unhealthy）
        lavaan_ok = body.get("lavaan", {}).get("available") is True
        if lavaan_ok:
            assert r.status_code == 200
            assert body.get("status") == "healthy"
        else:
            assert r.status_code == 503
            assert body.get("status") == "unhealthy"
    else:
        assert r.status_code in (200, 503)
        assert body.get("status") in ("healthy", "unhealthy")
