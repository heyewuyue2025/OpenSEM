# OpenSEM - 结构方程建模平台

面向社科学术研究的云端 SEM 分析平台，以「表单化建模替代自由画布」为核心交互创新。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite |
| 后端 | Python FastAPI |
| 统计算法 | semopy (Phase 1) → lavaan/rpy2 (Phase 3) |
| 任务队列 | Celery + Redis (Phase 2+) |

## 快速启动

### 方式一：本地开发（推荐）

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8020

# 前端（新终端）
cd frontend
npm install
npm run dev
```

- 前端: http://localhost:5173
- 后端 API: http://localhost:8020
- API 文档: http://localhost:8020/docs

### 方式二：Docker

```bash
# 首次使用建议：
# 1) 复制环境变量模板：copy .env.example .env（Windows）或 cp .env.example .env（Linux/macOS）
# 2) 按需编辑 .env（strict/lite、Redis/Celery 等）
docker compose up -d
# 后端: http://localhost:8020
```

> 环境变量详细说明见：`docs/ops/environment.md`

> 运维排障/恢复手册见：`docs/ops/runbook.md`

## Docker 运行口径（强制版 vs 轻量版）

OpenSEM 有两档运行口径，差异主要体现在 `GET /api/health` 的“门禁行为”和 MI/不变性序列是否可用。

### 能力矩阵（strict/lite）

| 能力/行为 | strict（强制版） | lite（轻量版） |
|---|---|---|
| 服务健康检查 `GET /api/health` | `lavaan.available=false` 会返回 **503**（阻断部署） | 永远 **200**，但会返回 `lavaan.available=false` 与原因（允许降级运行） |
| Phase 1 主流程（上传→建模→估算→导出） | 可用 | 可用 |
| 异步长任务（Celery/轮询） | 可用 | 可用 |
| MI（Modification Indices） | **真实可用**（依赖 `R + lavaan + rpy2`） | **降级**：返回 `supported:false` + message（不影响主流程） |
| 不变性序列（configural→metric→scalar→strict） | **真实可用**（lavaan） | **降级**：入口置灰/提示；返回 `supported:false` 或 `mode:"degraded"`（按实现） |
| 多群组（配置不变性拆组拟合） | 可用 | 可用 |
| 导出（APA xlsx/docx + 语法） | 可用；Meta 可追溯（含环境/指纹等） | 可用；降级能力会在 Meta 中标注（如有） |

### 强制版（默认，推荐用于 CI/生产/他人照着跑）

- **目的**：保证容器内 `R + lavaan + rpy2` 真实可用；不可用就直接判定不健康，避免“假健康部署”。
- **关键环境变量**
  - `OPENSEM_WITH_LAVAAN=1`：构建镜像时安装 R + `lavaan`（Dockerfile build arg）
  - `OPENSEM_REQUIRE_LAVAAN=1`：运行时强门禁；lavaan 不可用则 `/api/health` 返回 503

启动（默认就是强制版）：

```bash
docker compose up -d --build
```

预期：
- `GET http://localhost:8020/api/health` 返回 **200**，且 `mode=strict`、`lavaan.available=true`
- 若 `lavaan.available=false`，则返回 **503**（这是正确行为：代表环境没装好）

### 轻量版（开发可选：仅 semopy，允许降级）

- **目的**：本机快速跑通主流程，不被 R/lavaan 环境卡住。
- **关键环境变量**
  - `OPENSEM_WITH_LAVAAN=0`：构建镜像时不安装 R/lavaan（镜像更轻）
  - `OPENSEM_REQUIRE_LAVAAN=0`：运行时不强门禁；`/api/health` 永远 200，但会在响应里说明 lavaan 不可用原因

启动：

```bash
OPENSEM_WITH_LAVAAN=0 OPENSEM_REQUIRE_LAVAAN=0 docker compose up -d --build
```

预期：
- `GET http://localhost:8020/api/health` 返回 **200**，且 `mode=lite`
- MI/不变性序列会返回 `supported:false` 并解释原因（主流程不受影响）

## 一键验收（Docker）

在 Windows PowerShell 中运行：

```powershell
# 强制版：会跑完整 e2e（上传→MI→不变性序列）
powershell -ExecutionPolicy Bypass -File .\scripts\verify-docker.ps1 -Mode strict

# 轻量版：只验证 health/连通性（不强行跑 MI/不变性序列）
powershell -ExecutionPolicy Bypass -File .\scripts\verify-docker.ps1 -Mode lite
```

## 项目结构

```
opensem/
├── backend/           # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/    # 数据、建模、统计、导出
│   │   ├── main.py
│   │   └── config.py
│   └── requirements.txt
├── frontend/          # Vue 3 前端
│   ├── src/
│   │   ├── views/     # 数据 / 建模 / 结果
│   │   ├── router/
│   │   └── api/
│   └── package.json
└── OpenSEM_PRD_V2.docx
```

## Phase 1 路线图

- [x] 项目 scaffold
- [x] 数据导入解析 (CSV/XLSX/SAV)
- [x] 表单化 CFA/Path 建模
- [x] semopy 单群组 ML 估算
- [x] 拟合度红绿灯
- [x] APA 表格 + lavaan 导出

## 当前可用流程（Phase 1）

1. 在 `数据管理` 页上传数据，拿到 `data_key`
2. 在 `表单建模` 页生成 `lavaan` 语法
3. 在 `结果` 页运行 ML 估算，查看 χ²/df、RMSEA、SRMR、TLI、CFI 与红黄绿状态
4. 在 `结果` 页导出：
   - APA 基础表：`{project}_{YYYYMMDD_HHMMSS}_apa_table.xlsx`
   - APA 基础报告：`{project}_{YYYYMMDD_HHMMSS}_apa_table.docx`
   - 模型语法：`{project}_{YYYYMMDD_HHMMSS}_model.lavaan.txt`

## 产品化补充（当前已支持）

- 本地持久化：刷新页面后自动恢复最近一次数据概览、lavaan 语法、拟合度结果
- 一键重置：顶部 `Reset` 按钮可清空当前分析会话（数据 / 模型 / 结果）
