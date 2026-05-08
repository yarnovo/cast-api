# cast-api

Cast C2A2C 虚拟角色平台后端 API · FastAPI + SQLAlchemy + sqlite (dev) / postgres (prod) · uv 管包。

## 业务

Cast = C2A2C (Consumer → Agent → Consumer) 虚拟角色平台:

- 真人 owner 通过阿空小造 (meta-agent) 创建虚拟角色 (虚拟角色 = persona + 服务包)
- buyer 在市场页浏览虚拟角色 · 下单虚拟角色提供的服务包
- 工单生命周期: pending → paid → accepted → in_progress → delivered → completed
- 交付模式 3 选 1: AI 自动 / 真人 owner / 混合

## 跑

```bash
uv sync
uv run alembic upgrade head           # 生产: 走迁移建表
uv run uvicorn cast_api.main:app --reload --port 8000
# 浏览器开 http://localhost:8000/docs
```

MVP 阶段 lifespan 启动时也会跑 `Base.metadata.create_all` + seed (幂等) · 方便本地直接起。

## 测

```bash
uv run pytest -v
```

## API

### 用户
| Method | Path | 说明 |
|---|---|---|
| GET | /api/users/{id} | 用户信息 (真人 / 虚拟角色 persona 共用) |

### 虚拟角色 + 服务包
| Method | Path | 说明 |
|---|---|---|
| GET | /api/agents?q&limit | 市场页 · 浏览虚拟角色 |
| POST | /api/agents?owner_id | 创建虚拟角色 (owner 真人) |
| GET | /api/agents/mine?owner_id | 我创建的虚拟角色 |
| GET | /api/agents/{id} | 虚拟角色详情 + 服务包 |
| PATCH | /api/agents/{id}?owner_id | 改虚拟角色 |
| DELETE | /api/agents/{id}?owner_id | 删虚拟角色 |
| POST | /api/agents/{id}/services?owner_id | 加服务包 |
| DELETE | /api/agents/{id}/services/{sid}?owner_id | 删服务包 |

### 工单
| Method | Path | 说明 |
|---|---|---|
| POST | /api/orders?buyer_id | buyer 下单 |
| POST | /api/orders/{id}/pay | 标已付款 (MVP mock) |
| POST | /api/orders/{id}/accept?actor_id | 接单 (owner 或 persona AI) |
| POST | /api/orders/{id}/deliver?actor_id | 交付 |
| POST | /api/orders/{id}/complete?buyer_id | buyer 验收 |
| POST | /api/orders/{id}/cancel?actor_id | 取消 |
| GET | /api/orders/mine?user_id | 我的订单 (作为 buyer) |
| GET | /api/orders/inbox?owner_id | 待办订单 (作为虚拟角色 owner) |
| GET | /api/orders/{id} | 工单详情 |

### 私信 / 提醒 (虚拟角色 ↔ owner / buyer 协作用)
| Method | Path | 说明 |
|---|---|---|
| POST | /api/messages?user_id | 发私信 |
| GET | /api/messages/inbox?user_id | 收件箱 |
| GET | /api/messages/conversations?user_id | 会话列表 |
| GET | /api/messages/with/{other_user_id}?user_id | 与某人对话 (顺带标已读) |
| GET | /api/messages/unread-count?user_id | 未读数 |
| POST | /api/reminders?user_id | 设提醒 (虚拟角色排程用) |
| GET | /api/reminders?user_id | 列我的提醒 |
| GET | /api/reminders/due | 已到期未触发 (scheduler 拉) |
| POST | /api/reminders/{id}/fire | 标已触发 |
| DELETE | /api/reminders/{id} | 删提醒 |

### agent harness · chat session 持久化 (REQ-001)
跨 FC 实例多轮对话不丢上下文 · akong-agent-harness 的 RdsSession 调本组。
跟 `/api/agents/{id}/memories` 是分两层抽象 (chat = 短期 turn · memory = 长期沉淀)。

| Method | Path | 说明 |
|---|---|---|
| POST | /api/chat_messages | 单条 turn 写入 (role: user/assistant/tool/system) |
| GET | /api/chat_messages?session_id&limit&before | 拉 history · asc · limit≤500 · before=cm_id 分页 |
| DELETE | /api/chat_messages?session_id | 清整个 session · 返 `{deleted: N}` |

### Meta
| Method | Path | 说明 |
|---|---|---|
| GET | /health | 健康检查 |
| GET | /docs | OpenAPI swagger |

## Schema (核心表)

- `users` 用户 (真人 / 虚拟角色 persona 共用)
- `agents` 虚拟角色 + harness 字段 (role / rules_json / metadata_json)
- `services` `orders` 服务包 + 工单
- `posts` `post_likes` `follows` 社交 feed
- `messages` `reminders` 私信 + 提醒
- `agent_memories` agent 长记忆 log (append-only · agent 自己写)
- `tools` `agent_tools` 平台 tools registry + 授权
- `agent_change_log` 自演化 append-only log
- `chat_messages` agent harness chat session 持久化 (REQ-001 · 跨 FC 实例 · 索引: (session_id,created_at) + (agent_id,created_at))

## Seed

启动时幂等 seed:
- 5 个演示真人 user (u01-u05)
- 3 个示范虚拟角色 (LOGO 设计 · 心理咨询 · 全栈程序员) + 各自 2 个服务包

让市场首页不空 · 真 owner 通过阿空小造 (meta-agent) 创建更多。

## 部署

- staging: `develop` 分支推送 → FC v3 `cast-api-staging` → `https://staging.api.cast.agentaily.com`
- prod: `main` 分支推送 → FC v3 `cast-api` → `https://api.cast.agentaily.com`

(workflow 见 `.github/workflows/`)

## 没做

- 真用户登录 (现 hardcode `u01` 等 query 参数 user_id)
- 真支付 (现 mock `/pay` 直接标 paid)
- 推荐 / 排序 (现按 created_at desc)
- 头像 / 文件上传 OSS
