# Changelog

All notable changes to **OpenSEM** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

### Deprecated

### Removed

### Security

## [0.1.0] - 2026-04-01

### Added
- **Phase 1（MVP）端到端闭环**：上传 → 表单化建模 → 估算（semopy） → 结果解读 → 导出（APA xlsx/docx + lavaan 语法）。
- **异步长任务（Celery + Redis）**：拟合、Bootstrap（中介）、多群组（配置不变性拆组）、不变性序列（lavaan 可选）。
- **运行口径分档（strict/lite）**：
  - **strict**：强制 `R + lavaan + rpy2` 可用；不可用则 `/api/health` 返回 503，防止“假健康部署”。
  - **lite**：仅 semopy 主流程；MI/不变性序列等能力明确降级为 `supported:false`，但服务保持健康。
- **一键验收脚本**：`scripts/verify-docker.ps1 -Mode strict|lite`。

[Unreleased]: https://example.invalid/compare/v0.1.0...HEAD
[0.1.0]: https://example.invalid/releases/tag/v0.1.0
