# 从 Runtime 到 Gateway

本章不跳步。先让 Agent 在 Runtime 中运行，再给它接入 Gateway，最后让 Gateway 调用最小权限 Lambda MCP target。

1. [Runtime](../01-quickstart/first-runtime/README.md)：部署 Agent 服务。
2. [Gateway 与 Lambda MCP](gateway-lambda-mcp/README.md)：暴露一个只读工具。
3. [鉴权](../00-concepts/06-authentication-and-authorization.md)：明确每一跳用哪个 IAM Role。
4. [观测](../00-concepts/04-observability.md)：查看 Runtime、Gateway、Lambda 和控制面的证据。

不要让浏览器直接带 AWS 凭证调用 Gateway；也不要把业务 API 权限授予 Agent Runtime。Runtime 应只被允许调用 Gateway，Lambda target 才拥有受限的 AWS API 权限。
