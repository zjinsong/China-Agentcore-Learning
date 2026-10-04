# 中国区设计指南

中国区不是把 Global 模板换一个 region 名称。先读官方 [功能差异页](https://docs.amazonaws.cn/en_us/aws/latest/userguide/bedrock-agentcore.html)，再选择替代模式。

| Global 设计 | 中国区问题 | 推荐替代 |
| --- | --- | --- |
| AgentCore Memory | 不可用 | DynamoDB 保存索引/状态，S3 保存正文与结果 |
| AgentCore Harness | 不可用 | 应用 worker、能力目录、DAG 与审计事件 |
| AgentCore Registry | 不可用 | 声明式配置 + DynamoDB 专家记录 |
| AgentCore Policy | 不可用 | IAM、Lambda adapter allowlist、计划校验、人工审批 |
| Gateway semantic search | 不可用 | 应用侧能力清单与显式工具选择 |
| Gateway Cognito authorizer | 不适用 | 企业 OIDC IdP 的 CUSTOM_JWT，或 AWS_IAM |
| 内置 OAuth providers | 部分不可用 | 自建兼容 OAuth/OIDC 集成，或由应用管理凭证 |

Runtime 仅支持 MicroVM；Gateway 没有 No authorization 选项，必须使用 AWS_IAM 或 CUSTOM_JWT。详见 [部署指南](deployment-guide-cn.md)。
