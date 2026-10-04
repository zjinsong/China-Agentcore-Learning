# Claude Code MCP 配置

Claude Code standalone 示例配置位于 `~/.claude/mcp.json`。请按官方客户端文档确认实际安装路径：

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

先测试 `search_agentcore_docs`；部署、删除、Identity 或 Gateway 配置变更应保留人工审批。[官方 Claude Code 配置](https://docs.amazonaws.cn/en_us/bedrock-agentcore/latest/devguide/mcp-getting-started.html)
