# Codex MCP 配置

在 Codex 的 MCP 配置中加入以下**示例**。具体配置文件位置和客户端版本以你的 Codex 文档为准；不要把 AWS access key 写入配置文件，使用 AWS profile、SSO 或环境的短期凭证。

```toml
[mcp_servers.agentcore]
command = "uvx"
args = ["awslabs.amazon-bedrock-agentcore-mcp-server@latest"]

[mcp_servers.agentcore.env]
FASTMCP_LOG_LEVEL = "ERROR"
```

先只启用文档查询工具，然后让 Codex 执行：

> 搜索 AgentCore Runtime 在中国区的可用性，并给出官方文档链接；不要创建或修改资源。

确认文档工具可用后，再进入 [最小 Runtime](../first-runtime/README.md)。不要把“客户端已连接 MCP”误解为“已拥有生产环境写权限”。
