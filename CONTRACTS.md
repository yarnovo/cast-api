# cast-api · CONTRACTS

本仓对上下游的契约声明 · 改 endpoint / schema 前查谁会受影响。

## 上游 (本仓不依赖具体 caller · 只暴露 HTTP API)

无强耦合 · 任何持有合法 user_id / agent_id 的服务都可调。

## 下游 (依赖本仓的消费方)

| 仓 | 调用面 | 说明 |
|---|---|---|
| akong-agent-harness | `POST/GET/DELETE /api/chat_messages` | RdsSession 持久化 chat 轮次 (跨 FC 实例 session 续接) |
| akong-agent-harness | `POST/GET /api/agents/{id}/memories` | 长记忆 log · agent 自己写自己读 |
| akong-agent-harness | `POST /api/agents/{id}/update-self` | 自演化 · 改 soul/playbook/style/rules_json |
| akong-agent-harness | `GET /api/agents/{id}/tools` `GET /api/tools` | tools registry · runtime 注入 LLM function-calling |
| cast-agents (builtin sync) | `POST /api/agents?id_override=ag_builtin_<slug>` | 确定性 id 同步内置 agent |
| cast-web (前端) | `GET /api/agents` `GET /api/agents/{id}` `POST /api/orders` | 市场页 / 角色卡 / 下单 |

## 改动影响

- 改 `/api/chat_messages` schema → 通知 akong-agent-harness maintainer 调整 RdsSession
- 改 `/api/agents/*/memories` schema → 通知 akong-agent-harness maintainer
- 改 `/api/agents` schema (尤其 role / rules_json / metadata_json) → 通知 cast-agents + akong-agent-harness
- alembic migration 必双向跑过 (upgrade + downgrade)
- 删 endpoint 必先 deprecate 一版 + 通知所有下游
