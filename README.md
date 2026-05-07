# xhs-clone-api

xhs-clone 后端 API · FastAPI + SQLAlchemy + sqlite (dev) / postgres (prod) · uv 管包。

## 跑

```bash
uv sync
uv run uvicorn xhs_clone_api.main:app --reload --port 8000
# 浏览器开 http://localhost:8000/docs
```

## 测

```bash
uv run pytest -v
```

## API

| Method | Path | 说明 |
|---|---|---|
| GET | /api/notes?cursor&limit | 瀑布流 (cursor 分页) |
| GET | /api/notes/{id} | 笔记详情 |
| POST | /api/notes | 发布笔记 |
| GET | /api/notes/{id}/comments | 评论列表 |
| POST | /api/notes/{id}/comments | 发表评论 |
| POST | /api/notes/{id}/like | 点赞切换 |
| POST | /api/notes/{id}/collect | 收藏切换 |
| GET | /api/users/{id} | 用户信息 |
| GET | /api/users/{id}/notes | 用户笔记 |
| GET | /health | 健康检查 |
| GET | /docs | OpenAPI swagger |

启动时自动建表 + seed 20 条 mock 笔记 + 10 个用户 + 100 条评论 (跟前端 `xhs-clone/src/data/mock.ts` 1:1 对应)。

## 部署

- staging: `develop` 分支推送 → FC v3 `xhs-clone-api-staging` → `https://staging.api.xhs.agentaily.com`
- prod: `main` 分支推送 → FC v3 `xhs-clone-api` → `https://api.xhs.agentaily.com`

(workflow 待加 · 见 `.github/workflows/`)

## 没做

- 真用户登录 (现 hardcode `u01`)
- 图片上传 OSS
- 推荐 feed (现按 created_at desc)
- 搜索
- alembic migration (现 `Base.metadata.create_all` 启动时建表)
