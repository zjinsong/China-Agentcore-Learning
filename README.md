# China AgentCore Learning

面向 AWS 中国区的 Amazon Bedrock AgentCore 学习仓库。学习路径从概念、MCP 快速上手、最小 Runtime 与 Gateway 实验，到 CloudOps 多 Agent Demo、Harness 替代模式和中外区域差异。

本仓库不包含任何 AWS 账号、ARN、IP、访问密钥、Token、客户数据、CloudTrail 事件或线上部署配置。所有命令中的 `<...>` 都是你自己的安全占位符。

## 学习路线

| 阶段 | 目标 | 入口 |
| --- | --- | --- |
| 0. 概念 | 先理解中国区能用什么、不能用什么 | [服务地图](00-concepts/00-agentcore-cn-service-map.md) |
| 1. 快速上手 | 给编码助手配置 AgentCore MCP，部署并测试第一个 Runtime | [快速上手](01-quickstart/README.md) |
| 2. 服务构建 | 从 Runtime 到 Gateway，再到 Lambda MCP target | [构建实验](02-build-agentcore/README.md) |
| 3. CloudOps | 从单专家演进到依赖式多专家协作 | [CloudOps Demo](03-cloudops-demo/README.md) |
| 4. Harness | 理解 Global Harness 与中国区应用侧控制面的关系 | [Harness](04-harness/README.md) |
| 5. 区域差异 | 将 Global 方案安全改造成中国区方案 | [中国区指南](05-china-region/README.md) |

## 先读什么

如果你第一次接触 AgentCore，按此顺序：

1. [中国区服务地图](00-concepts/00-agentcore-cn-service-map.md)
2. [身份、鉴权和授权](00-concepts/06-authentication-and-authorization.md)
3. [Kiro、Claude Code、Codex 的 MCP 配置](01-quickstart/README.md)
4. [第一个 Runtime](01-quickstart/first-runtime/README.md)
5. [Runtime → Gateway → Lambda MCP](02-build-agentcore/gateway-lambda-mcp/README.md)
6. [CloudOps 多 Agent 工作流](03-cloudops-demo/README.md)

## 安全规则

- 不提交 `.env`、AWS credentials、MCP 配置中的真实环境变量、截图中的账号信息或日志原文。
- 使用最小权限 IAM Role；Demo 默认只读，Terraform apply 需要独立人工确认。
- 先在单独的学习账号或隔离环境实验。
- GitHub 是公开仓库；提交前运行仓库中的敏感信息检查。

官方参考：[AgentCore MCP 快速上手](https://docs.amazonaws.cn/en_us/bedrock-agentcore/latest/devguide/mcp-getting-started.html)、[中国区功能差异](https://docs.amazonaws.cn/en_us/aws/latest/userguide/bedrock-agentcore.html)、[AWS CloudOps 多 Agent 示例](https://github.com/aws-samples/sample-cloudops-multi-agent-system)。
