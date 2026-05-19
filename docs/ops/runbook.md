# OpenSEM 运维 Runbook（30 分钟内恢复）

适用对象：非研发同学。目标：在 **30 分钟内**把 OpenSEM 服务恢复到“可用”（至少 `GET /api/health` 返回 200 且 `status=healthy`）。

## 0. 你需要具备的工具（Windows）

- **PowerShell**
- **Docker Desktop**（确保 `docker` 命令可用）

> 所有命令都假设你在仓库根目录 `d:\OpenSEM` 执行。

## 1. 快速判断服务是否可用（2 分钟）

### 1.1 检查容器是否在跑

```powershell
docker compose ps
```

预期看到 3 个服务：`redis`、`backend`、`celery-worker` 都是 `running`（或至少 `backend` running 且能通过 health）。

### 1.2 健康检查（必做）

```powershell
$health = Invoke-RestMethod -Method GET -Uri "http://127.0.0.1:8020/api/health" -TimeoutSec 10
$health | ConvertTo-Json -Depth 8
```

- **健康**：`status` 为 `"healthy"`（HTTP 200）
- **不健康**：HTTP 503 且 `status` 为 `"unhealthy"`

关键字段：
- `mode`：`strict` 或 `lite`
- `lavaan.available`：`true/false`
- `require_lavaan`：`true/false`
- `celery_eager`：`true/false`

### 1.3 指标端点（可选，但有助排障）

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8020/api/metrics" -TimeoutSec 10 | Select-Object -ExpandProperty Content
```

如果这里都请求失败，优先处理 `backend` 是否启动/端口是否冲突。

## 2. 标准恢复流程（10 分钟内完成）

> 适用于：不确定原因、或服务明显异常时的“一把梭”恢复。

### 2.1 拉起/重建（默认 strict）

```powershell
docker compose down
docker compose up -d --build
docker compose ps
```

### 2.2 等待健康（最多 3 分钟）

```powershell
$deadline = (Get-Date).AddMinutes(3)
while ((Get-Date) -lt $deadline) {
  try {
    $h = Invoke-RestMethod -Method GET -Uri "http://127.0.0.1:8020/api/health" -TimeoutSec 5
    if ($h.status -eq "healthy") { break }
  } catch {}
  Start-Sleep -Seconds 2
}
Invoke-RestMethod -Method GET -Uri "http://127.0.0.1:8020/api/health" -TimeoutSec 10 | ConvertTo-Json -Depth 8
```

如果仍然不健康，按下面“常见问题”对症处理。

## 3. Start / Stop / Restart（常用）

### 3.1 启动（后台）

```powershell
docker compose up -d
```

### 3.2 停止并清理容器（保留镜像）

```powershell
docker compose down
```

### 3.3 仅重启后端 / worker / redis

```powershell
docker compose restart backend
docker compose restart celery-worker
docker compose restart redis
```

### 3.4 查看日志（最近 200 行）

```powershell
docker compose logs --tail 200 backend
docker compose logs --tail 200 celery-worker
docker compose logs --tail 200 redis
```

## 4. 常见问题与处理（按概率排序）

## 4.1 Redis 挂了 / 连接不上

**症状**
- `celery-worker` 不在 running，或日志里出现连接失败（例如 `Connection refused` / `Name or service not known`）
- `/api/health` 可能仍然 healthy（取决于当下请求），但异步任务会卡住/失败

**处理**

```powershell
docker compose ps
docker compose logs --tail 200 redis
docker compose restart redis
```

确认 Redis 端口是否被宿主机占用（理论上 compose 会占用 `6379`）：

```powershell
Get-NetTCPConnection -LocalPort 6379 -ErrorAction SilentlyContinue | Select-Object -First 5
```

如发现 `6379` 已被其他进程占用且导致 `redis` 起不来，先停掉占用进程（需要管理员权限时请联系 IT），再：

```powershell
docker compose up -d
```

## 4.2 worker 没在跑（`celery-worker` down）

**症状**
- `docker compose ps` 里 `celery-worker` 不是 running
- 任务状态长期 `PENDING`，或前端轮询一直转

**处理**

```powershell
docker compose restart celery-worker
docker compose ps
docker compose logs --tail 200 celery-worker
```

若日志出现“未注册任务”（`Received unregistered task`），直接做一次全量重建：

```powershell
docker compose down
docker compose up -d --build
```

## 4.3 任务失败（FAILURE / 报错）

**症状**
- 前端提示任务失败，或导出/估算失败
- worker 或 backend 日志出现 Python 异常

**处理（先定位是哪一层报错）**

1) 先看 backend/worker 日志：

```powershell
docker compose logs --tail 200 backend
docker compose logs --tail 200 celery-worker
```

2) 确认 Redis 与 worker 都正常后，重启两者（通常可恢复短暂性失败）：

```powershell
docker compose restart redis
docker compose restart celery-worker
docker compose restart backend
```

3) 再做一次健康检查：

```powershell
Invoke-RestMethod -Method GET -Uri "http://127.0.0.1:8020/api/health" -TimeoutSec 10 | ConvertTo-Json -Depth 8
```

## 4.4 `/api/health` 返回 503（strict 门禁：lavaan 不可用）

**症状**
- `GET /api/health` 返回 **HTTP 503**
- 响应里 `require_lavaan=true` 且 `lavaan.available=false`

这表示当前运行是 **strict**，但容器里 `R + lavaan + rpy2` 没装好或检测失败。处理方式有两条路：

### 方案 A（推荐）：修复 strict（适合生产/CI 口径）

```powershell
docker compose down
$env:OPENSEM_WITH_LAVAAN="1"
$env:OPENSEM_REQUIRE_LAVAAN="1"
docker compose up -d --build
Invoke-RestMethod -Method GET -Uri "http://127.0.0.1:8020/api/health" -TimeoutSec 10 | ConvertTo-Json -Depth 8
```

如果依然 503，马上看后端日志里的 `lavaan.reason` 对应错误信息：

```powershell
docker compose logs --tail 200 backend
```

### 方案 B：临时降级到 lite（为了先恢复主流程）

lite 会让 `/api/health` 永远 200（即使 `lavaan.available=false`），主流程（上传→建模→估算→导出）仍可用，但 MI/不变性序列等会明确降级。

```powershell
docker compose down
$env:OPENSEM_WITH_LAVAAN="0"
$env:OPENSEM_REQUIRE_LAVAAN="0"
docker compose up -d --build
Invoke-RestMethod -Method GET -Uri "http://127.0.0.1:8020/api/health" -TimeoutSec 10 | ConvertTo-Json -Depth 8
```

恢复后请把“为什么 strict 失败”记录到故障单（至少附上 `lavaan.reason` 与 `backend` 日志片段）。

## 4.5 端口冲突（8020 或 6379 被占用）

**症状**
- `backend` 或 `redis` 起不来
- `docker compose ps` 显示 `Exit 1`，日志里含 `bind: address already in use`

**处理**

检查宿主机端口占用：

```powershell
Get-NetTCPConnection -LocalPort 8020 -ErrorAction SilentlyContinue | Select-Object -First 5
Get-NetTCPConnection -LocalPort 6379 -ErrorAction SilentlyContinue | Select-Object -First 5
```

如果是旧的 OpenSEM 容器残留，直接清掉并重启：

```powershell
docker compose down
docker compose up -d
```

如果是其他程序占用，需要先停止占用程序（或由 IT 协助），再 `docker compose up -d`。

## 4.6 导出失败（xlsx/docx/txt 导出）

**症状**
- 前端导出时报错/下载失败
- 后端日志出现 export 相关异常

**处理**

1) 先确认后端是 healthy：

```powershell
Invoke-RestMethod -Method GET -Uri "http://127.0.0.1:8020/api/health" -TimeoutSec 10 | ConvertTo-Json -Depth 8
```

2) 拉取后端日志定位具体异常（通常能看到堆栈）：

```powershell
docker compose logs --tail 200 backend
```

3) 若是短暂性错误，先重启后端再复测：

```powershell
docker compose restart backend
```

4) 若同样操作在多次重启后仍失败，优先按“高内存/容器被杀”检查（下一节），并把 `backend` 日志与当次导出的时间点一起上报。

## 4.7 内存过高 / 容器被 OOM 杀掉

**症状**
- 容器反复退出、重启后又崩
- 导出/解析大文件时更容易发生

**处理**

1) 看资源占用：

```powershell
docker stats --no-stream
```

2) 先用最小化恢复手段（重启服务）：

```powershell
docker compose restart backend
docker compose restart celery-worker
```

3) 如果仍然频繁崩溃：
- 临时降低并发（减少瞬时内存峰值），编辑 `.env`（仓库根目录），把 `OPENSEM_PARSE_CONCURRENCY` 调小（例如从 `4` 改 `2`），然后：

```powershell
docker compose up -d
docker compose restart backend
```

4) 若仍不稳定，把 `docker stats` 输出与 `backend/celery-worker` 日志一并上报（这通常需要研发介入优化）。

## 5. 一键验收（建议在恢复后做，5–10 分钟）

仓库已提供脚本做端到端冒烟/验收（PowerShell）。

### lite（主流程验收：推荐用于快速确认“能用”）

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify-docker.ps1 -Mode lite
```

### strict（包含 lavaan 能力：更接近生产口径）

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify-docker.ps1 -Mode strict
```

## 6. 升级/回滚（仅 Docker 口径）

> 最小操作：切换到目标版本的代码/镜像，然后重建容器。

```powershell
docker compose down
# 如果你的代码目录是 git 仓库，可用 tag/commit 切换版本（示例）：
#   git status
#   git log -n 5 --oneline
#   git checkout <tag-or-commit>
docker compose up -d --build
```

完成后务必复查：

```powershell
Invoke-RestMethod -Method GET -Uri "http://127.0.0.1:8020/api/health" -TimeoutSec 10 | ConvertTo-Json -Depth 8
Invoke-WebRequest -Uri "http://127.0.0.1:8020/api/metrics" -TimeoutSec 10 | Select-Object -ExpandProperty StatusCode
```

