"""
OpenSEM Phase 3 - Celery 应用入口
用于 bootstrap / 多群组 / 迁移 lavaan 等长任务统一调度。
"""

from celery import Celery

from app.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND
from app.settings import is_celery_eager_effective

# 进程启动时快照：与 broker 配置一致（改环境变量需重启进程）
_CELERY_EAGER_EFFECTIVE = is_celery_eager_effective()


def _is_eager() -> bool:
    return _CELERY_EAGER_EFFECTIVE


broker_url = "memory://" if _CELERY_EAGER_EFFECTIVE else CELERY_BROKER_URL
result_backend = "cache+memory://" if _CELERY_EAGER_EFFECTIVE else CELERY_RESULT_BACKEND

celery_app = Celery("opensem", broker=broker_url, backend=result_backend)

# Celery 的 autodiscover 默认会找 <package>.tasks 模块。
# 我们的任务放在 app.tasks.stats_tasks（不是 app.tasks.tasks），因此需要显式导入/注册，
# 否则 worker 会出现 “Received unregistered task of type …”/KeyError('stats.xxx')。
celery_app.autodiscover_tasks(["app.tasks"])
celery_app.conf.imports = tuple(set((celery_app.conf.get("imports") or ())) | {"app.tasks.stats_tasks"})

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
)

# 本地开发兜底：未配置 OPENSEM_REDIS_URL 时默认 eager；或显式 OPENSEM_CELERY_EAGER=1
if _CELERY_EAGER_EFFECTIVE:
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        task_store_eager_result=True,
    )

