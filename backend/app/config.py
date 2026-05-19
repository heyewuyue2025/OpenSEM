"""
OpenSEM 配置
"""
import os

# 上传与处理
from app.settings import get_settings

_s = get_settings()
MAX_UPLOAD_SIZE_MB = _s.upload_max_size_mb
PARSE_TIMEOUT_SECONDS = _s.parse_timeout_seconds
# 用户数据不落盘，仅内存处理
DATA_PERSISTENCE = False

# 统计算法
DEFAULT_ML_ITERATIONS = 50
DEFAULT_BOOTSTRAP_SAMPLES = 2000

# 性能基准 (c5.xlarge: 4 vCPU, 8GB RAM)
MAX_CONCURRENT_USERS = 50

# Phase 3: 长任务（Celery + Redis）
# 默认本机 Redis；生产环境请通过环境变量覆盖
REDIS_URL = os.getenv("OPENSEM_REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("OPENSEM_CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("OPENSEM_CELERY_RESULT_BACKEND", REDIS_URL)
