# Release 流程（OpenSEM）

目标：让任何一次演示/验收都能用 **tag + 环境 + 数据 + 脚本**复现，并支持快速回滚。

> 约定：本仓库采用 SemVer，版本从 `v0.1.0` 起步；变更记录写入 `CHANGELOG.md`。

---

## 发布前检查清单

- `CHANGELOG.md` 的 `[Unreleased]` 已补齐本次变更说明，并准备落到新版本号
- Docker 启动与健康检查通过
- 一键验收脚本通过（至少 lite；对外发布建议 strict 也通过）

---

## 版本号规则（SemVer）

- **MAJOR**：破坏性变更（API 契约/导出契约/前端存储结构不兼容等）
- **MINOR**：向后兼容的新功能（新增能力、新增导出表等）
- **PATCH**：向后兼容的问题修复

---

## 发布步骤（Git Tag + GitHub Release + GHCR）

### 1) 更新变更记录

- 在 `CHANGELOG.md` 中把本次内容从 `[Unreleased]` 归档到新版本（例如 `0.1.1`），并写明发布日期

### 2) 创建并推送 tag

在仓库根目录（PowerShell）：

```powershell
git tag v0.1.1
git push origin v0.1.1
```

### 3) 构建并推送镜像（GHCR）

> 说明：镜像仓库为 GHCR。镜像名（与 CI 保持一致）：`ghcr.io/<org-or-user>/OpenSEM`。

推荐在 CI 中完成 build/tag/push。若需要本地构建验证：

```powershell
docker compose build
docker compose up -d
```

若需要直接拉取并运行已发布镜像（以 `v0.1.1` 为例）：

```powershell
docker pull ghcr.io/<org-or-user>/OpenSEM:v0.1.1

# HTTP API: http://localhost:8020
docker run --rm -p 8020:8000 `
  -e OPENSEM_REDIS_URL=redis://host.docker.internal:6379/0 `
  -e OPENSEM_WITH_LAVAAN=1 `
  -e OPENSEM_REQUIRE_LAVAAN=1 `
  ghcr.io/<org-or-user>/OpenSEM:v0.1.1
```

也可以拉取 `latest`（始终指向最新 tag 发布构建）：

```powershell
docker pull ghcr.io/<org-or-user>/OpenSEM:latest
```

### 4) 运行验收（建议严格版与轻量版都跑）

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify-docker.ps1 -Mode lite
powershell -ExecutionPolicy Bypass -File .\scripts\verify-docker.ps1 -Mode strict
```

验收证据应包含：
- 使用的 **tag**
- 运行环境（OS、Docker 版本、关键环境变量）
- 验收日志（脚本输出）

### 5) 创建 GitHub Release

- Release 标题：`v0.1.1`
- Release 内容：从 `CHANGELOG.md` 对应版本段落粘贴（或摘要后附链接）
- 附件（可选）：示例导出文件、验收报告 PDF/MD、录屏链接等

---

## 回滚策略

### 回滚到上一个版本（推荐）

1. 找到上一版本 tag（例如 `v0.1.0`）
2. 拉取对应镜像 tag（或切换到对应 tag 的部署配置）
3. 重新启动并跑 `verify-docker.ps1 -Mode lite`（对外环境建议再跑 strict）

### 变更口径（strict/lite）

- **strict**：`OPENSEM_WITH_LAVAAN=1` 且 `OPENSEM_REQUIRE_LAVAAN=1`  
  - `/api/health` 必须 `200` 且 `lavaan.available=true`；否则返回 `503`（正确的“阻断部署”行为）
- **lite**：`OPENSEM_WITH_LAVAAN=0` 且 `OPENSEM_REQUIRE_LAVAAN=0`  
  - `/api/health` 永远 `200`，但会明确提示 lavaan 不可用原因；MI/不变性序列等返回 `supported:false`

---

## 验收与复现的最小信息集（必须写在报告里）

- 版本：tag（例如 `v0.1.1`）
- 环境：OS / Docker / Python（若非容器）/ 浏览器
- 运行方式：strict 或 lite（以及关键环境变量）
- 数据集：文件名/来源/哈希（如可提供）
- 步骤：可复现的操作步骤
- 成功判定：每一步“看到什么算成功”
- 证据：录屏/截图/日志链接
