# Gateway

Gateway 是 Agent 调用 MCP 工具的统一入口。它验证调用者，再路由到 Lambda 或其他 target。CloudOps 使用一个 AWS_IAM Gateway，所有专家通过 SigV4 调用；浏览器不直接调用 Gateway。

Gateway 的入站鉴权与外部系统凭证是两件事：入站 `AWS_IAM` 或 `CUSTOM_JWT` 决定谁能调用 Gateway；OAuth/API Key Provider 用于 Gateway 代表 Agent 访问外部 SaaS。两者不可混为一谈。

下一步：[Gateway 与 Lambda MCP 实验](../02-build-agentcore/gateway-lambda-mcp/README.md)。
