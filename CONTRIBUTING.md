# Contributing to OpenSEM

感谢你对 OpenSEM 的关注。欢迎通过 Issue 与 Pull Request 参与改进。

## 开发环境

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8020

# 前端
cd frontend
npm install
npm run dev
```

环境变量与 Docker 说明见 `docs/ops/environment.md` 与根目录 `README.md`。

## 提交流程

1. Fork 本仓库并创建分支（`feat/...` 或 `fix/...`）
2. 确保相关测试通过：
   - 后端：`cd backend && pytest`
   - 前端：`cd frontend && npm run test`
3. 提交 PR，说明变更动机与测试方式

## 代码范围

公开仓库仅包含可运行产品与面向用户的文档。内部规划、验收模板等请勿提交至本仓库。

## 许可证

贡献即表示你同意在 [MIT License](LICENSE) 下授权你的贡献。
