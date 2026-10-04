# Kiro MCP 配置

创建或更新 `.kiro/settings/mcp.json`：

```json
{
  "mcpServers": {
    "bedrock-agentcore-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.amazon-bedrock-agentcore-mcp-server@latest"],
      "env": {"FASTMCP_LOG_LEVEL": "ERROR"},
      "disabled": false,
      "autoApprove": ["search_agentcore_docs", "fetch_agentcore_doc"]
    }
  }
}
```

重启客户端后检查文档查询工具。这个配置与 AWS 官方 Kiro 示例一致；不要把 deploy/delete 类工具加入自动批准列表。[官方 Kiro 配置](https://docs.amazonaws.cn/en_us/bedrock-agentcore/latest/devguide/mcp-getting-started.html)
