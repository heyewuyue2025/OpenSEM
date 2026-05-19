"""OPENSEM_CELERY_EAGER 与 OPENSEM_REDIS_URL 的默认组合逻辑。"""

from app.settings import is_celery_eager_effective


def test_eager_explicit_true(monkeypatch):
    monkeypatch.setenv("OPENSEM_CELERY_EAGER", "1")
    monkeypatch.setenv("OPENSEM_REDIS_URL", "redis://x:6379/0")
    assert is_celery_eager_effective() is True


def test_eager_explicit_false(monkeypatch):
    monkeypatch.setenv("OPENSEM_CELERY_EAGER", "0")
    monkeypatch.delenv("OPENSEM_REDIS_URL", raising=False)
    assert is_celery_eager_effective() is False


def test_auto_eager_when_no_redis_url(monkeypatch):
    monkeypatch.delenv("OPENSEM_CELERY_EAGER", raising=False)
    monkeypatch.delenv("OPENSEM_REDIS_URL", raising=False)
    assert is_celery_eager_effective() is True


def test_auto_async_when_redis_url_set(monkeypatch):
    monkeypatch.delenv("OPENSEM_CELERY_EAGER", raising=False)
    monkeypatch.setenv("OPENSEM_REDIS_URL", "redis://localhost:6379/0")
    assert is_celery_eager_effective() is False


def test_empty_redis_url_means_auto_eager(monkeypatch):
    monkeypatch.delenv("OPENSEM_CELERY_EAGER", raising=False)
    monkeypatch.setenv("OPENSEM_REDIS_URL", "")
    assert is_celery_eager_effective() is True
