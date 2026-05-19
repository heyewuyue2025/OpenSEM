# 环境变量说明（OpenSEM）

目标：新环境部署时**只需要复制并编辑 `.env`**（配合 `docker compose up -d --build`）即可完成 strict/lite 切换与 Redis/Celery 配置。

> 说明：Docker Compose 会自动读取仓库根目录的 `.env` 用于变量替换，但只有显式写在 `docker-compose.yml` 的变量才会被注入到容器环境中。本项目已对齐为“由 `.env` 驱动 + 有默认值”。

## 变量总表

| 变量名 | 必填 | 默认值（docker-compose） | 作用域 | strict/lite 行为 | 示例 |
|---|---:|---|---|---|---|
| `OPENSEM_WITH_LAVAAN` | 否 | `1` | **build**（Docker build arg）+ runtime（仅用于 health 回显） | `1` 时镜像构建会安装 `R + lavaan + rpy2`，MI/不变性序列等能力可用；`0` 时镜像更轻，相关能力降级 | strict：`OPENSEM_WITH_LAVAAN=1`；lite：`OPENSEM_WITH_LAVAAN=0` |
| `OPENSEM_REQUIRE_LAVAAN` | 否 | `1` | **runtime**（后端 health 门禁） | `1`（strict）时若 `lavaan` 不可用则 `GET /api/health` 返回 **503** 阻断部署；`0`（lite）时 `/api/health` 永远 **200** 但会返回 `lavaan.available=false` 与原因 | strict：`OPENSEM_REQUIRE_LAVAAN=1`；lite：`OPENSEM_REQUIRE_LAVAAN=0` |
| `OPENSEM_REDIS_URL` | 否（但建议生产显式设置） | `redis://redis:6379/0` | **runtime**（后端 + worker） | 与 strict/lite 无直接关系；影响 Celery broker/result backend 的默认值 | compose 内：`redis://redis:6379/0`；外部：`redis://10.0.0.10:6379/0` |
| `OPENSEM_CELERY_BROKER_URL` | 否 | 跟随 `OPENSEM_REDIS_URL` | **runtime**（后端 + worker） | 与 strict/lite 无直接关系；未设置时使用 `OPENSEM_REDIS_URL` | `OPENSEM_CELERY_BROKER_URL=redis://redis:6379/1` |
| `OPENSEM_CELERY_RESULT_BACKEND` | 否 | 跟随 `OPENSEM_REDIS_URL` | **runtime**（后端 + worker） | 与 strict/lite 无直接关系；未设置时使用 `OPENSEM_REDIS_URL` | `OPENSEM_CELERY_RESULT_BACKEND=redis://redis:6379/2` |
| `OPENSEM_CELERY_EAGER` | 否 | **见下（自动规则）** | **runtime**（仅后端/worker 行为开关） | **未设置时**：若 `OPENSEM_REDIS_URL` 未配置或为空 → 默认 **eager=开**（进程内同步跑任务，免本地 Redis）；若已配置 Redis URL → 默认 **eager=关**（走异步 worker）。**显式** `1`/`0` 始终覆盖自动规则。`1` 时不依赖 Redis broker，任务同步执行（开发/排障）。 | `OPENSEM_CELERY_EAGER=1` 或生产 `0` |
| `OPENSEM_UPLOAD_MAX_SIZE_MB` | 否 | `100` | **runtime**（后端） | 与 strict/lite 无直接关系；限制上传体积（同时基于 Content-Length 预检与读取后校验） | `OPENSEM_UPLOAD_MAX_SIZE_MB=50` |
| `OPENSEM_UPLOAD_MAX_ROWS` | 否 | `200000` | **runtime**（后端） | 与 strict/lite 无直接关系；限制解析后数据行数（超过返回 400） | `OPENSEM_UPLOAD_MAX_ROWS=100000` |
| `OPENSEM_UPLOAD_MAX_COLS` | 否 | `2000` | **runtime**（后端） | 与 strict/lite 无直接关系；限制解析后数据列数（超过返回 400） | `OPENSEM_UPLOAD_MAX_COLS=500` |
| `OPENSEM_PARSE_TIMEOUT_SECONDS` | 否 | `30` | **runtime**（后端） | 与 strict/lite 无直接关系；限制单次解析的最大耗时（超时返回 408） | `OPENSEM_PARSE_TIMEOUT_SECONDS=20` |
| `OPENSEM_PARSE_CONCURRENCY` | 否 | `4` | **runtime**（后端） | 与 strict/lite 无直接关系；进程内并发上限（仅对 `/api/v1/data/parse` 生效） | `OPENSEM_PARSE_CONCURRENCY=2` |
| `OPENSEM_DATA_STORE_DIR` | 否 | 系统临时目录下的 `opensem-data/`（见下） | **runtime**（后端） | 解析后的上传数据除内存与可选 Redis 外，会写入该目录下的 pickle 文件（按 `data_key` 哈希命名），进程重启后仍可按 `data_key` 取数；`drop_data` 会同步删除对应文件 | `OPENSEM_DATA_STORE_DIR=/var/lib/opensem/data` |

**`OPENSEM_DATA_STORE_DIR` 默认路径：** 未设置时等价于 `{tempfile.gettempdir()}/opensem-data`（各 OS 的临时目录，例如 Linux 常为 `/tmp/opensem-data`，Windows 常为 `%TEMP%\\opensem-data`）。生产环境建议显式设为持久卷路径。

## data_key 生命周期与清理策略（关键）

- **磁盘缓存（默认开启）**：上传后会写入 `OPENSEM_DATA_STORE_DIR` 下的 pickle 文件（默认是系统临时目录的 `opensem-data/`），因此 **后端进程重启不会导致 data_key 立刻失效**（仍可按 key 取回数据）。
- **Redis 共享层（可选）**：若配置 `OPENSEM_REDIS_URL`，会额外写入 Redis 供异步 worker 共享数据。当前实现对该 Redis key 可能设置 TTL（例如 **1 小时**），到期后 Redis 中会自动清理；但磁盘缓存仍可能存在（取决于是否显式 drop）。
- **显式清理**：当服务端调用 `drop_data(data_key)` 时，会同时删除内存、Redis key（若启用）以及磁盘文件。

## 推荐配置（可直接写入 `.env`）

### strict（默认，推荐 CI/生产）

```bash
OPENSEM_WITH_LAVAAN=1
OPENSEM_REQUIRE_LAVAAN=1
OPENSEM_REDIS_URL=redis://redis:6379/0
```

### lite（本地快速开发）

```bash
OPENSEM_WITH_LAVAAN=0
OPENSEM_REQUIRE_LAVAAN=0
# 推荐“零依赖”口径：留空 Redis → 后端会自动 eager（同步跑长任务），无需本地 Redis/worker
OPENSEM_REDIS_URL=
# 可选：显式写死 eager（也可不写，依赖自动规则）
OPENSEM_CELERY_EAGER=1
```

### 使用外部 Redis（示例）

```bash
OPENSEM_REDIS_URL=redis://10.0.0.10:6379/0
OPENSEM_CELERY_BROKER_URL=redis://10.0.0.10:6379/0
OPENSEM_CELERY_RESULT_BACKEND=redis://10.0.0.10:6379/0
```

### 上传/解析限额（示例）

```bash
OPENSEM_UPLOAD_MAX_SIZE_MB=100
OPENSEM_UPLOAD_MAX_ROWS=200000
OPENSEM_UPLOAD_MAX_COLS=2000
OPENSEM_PARSE_TIMEOUT_SECONDS=30
OPENSEM_PARSE_CONCURRENCY=4
```

