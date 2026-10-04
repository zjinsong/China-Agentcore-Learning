# 中国区 AgentCore 服务地图

AgentCore 是构建和连接 Agent 的平台。先区分“平台提供的能力”和“应用需要自己补齐的能力”。

| 服务 | 中国区 | 本仓库如何学习/替代 |
| --- | --- | --- |
| Runtime | 可用 | 容器化 Agent、IAM、MicroVM、调用与日志 |
| Gateway | 可用 | MCP 工具入口、AWS_IAM/CUSTOM_JWT、Lambda target |
| Identity | 可用但有限制 | 企业 JWT、OAuth 外部凭证与角色边界 |
| Observability | 可用 | Runtime 指标、日志、工具错误与任务耗时 |
| Browser | 可用 | 独立实验，按用户隔离会话与人工接管 |
| Code Interpreter | 可用 | 独立实验，限制文件、网络与工件输出 |
| Memory | 不可用 | DynamoDB/S3 保存会话、摘要与结果 |
| Harness | 不可用 | 配置、任务 DAG、能力校验、重试和证据链由应用控制面实现 |
| Registry | 不可用 | `hierarchy.json` + DynamoDB 专家配置 |
| Policy | 不可用 | IAM、Gateway target、工具适配器和计划校验 |
| Knowledge Bases | 不可用 | 外部检索/RAG 服务或应用侧检索 |
| Evaluations / Optimizations | 不可用 | 测试集、任务记录、CloudWatch 指标和离线评测 |

官方差异页是唯一需要随服务更新复核的来源：[Amazon Bedrock AgentCore in AWS China](https://docs.amazonaws.cn/en_us/aws/latest/userguide/bedrock-agentcore.html)。

接下来阅读：[Runtime](01-runtime.md)、[Gateway](02-gateway.md)、[Identity](03-identity.md)、[Observability](04-observability.md)、[鉴权与授权](06-authentication-and-authorization.md)。
