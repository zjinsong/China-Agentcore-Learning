# 快速上手：用编码助手构建第一个 AgentCore Runtime

官方 AgentCore MCP Server 可帮助编码助手转换、部署和测试兼容的 Agent。官方文档直接给出 Kiro 与 Claude Code 的示例，并说明部署流程会创建配置、构建容器、部署 Runtime 和返回 ARN。[官方步骤](https://docs.amazonaws.cn/en_us/bedrock-agentcore/latest/devguide/mcp-getting-started.html)

先完成以下前置条件：AWS CLI 已配置、Python 3.12+、Docker、适合目标区域的 IAM 权限。Global 示例可以使用 `@aws/agentcore` CLI；中国区应以本仓库的 boto3/容器方式为准，并先核对区域可用性。

| 客户端 | 配置示例 | 验证 |
| --- | --- | --- |
| Codex | [Codex](codex/README.md) | 搜索官方文档，不先授权写操作 |
| Kiro | [Kiro](kiro/README.md) | `search_agentcore_docs` 与 `fetch_agentcore_doc` |
| Claude Code | [Claude Code](claude-code/README.md) | 同上 |

完成客户端配置后，进入 [第一个 Runtime](first-runtime/README.md)。
