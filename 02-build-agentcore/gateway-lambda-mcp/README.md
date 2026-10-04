# Lab：Gateway → Lambda MCP target

目标：提供一个不接触真实账户资源的 `get_learning_status` MCP 工具，理解 Gateway 的身份链路。生产 CloudOps 将相同模式用于 EC2、CloudWatch、CloudTrail、Pricing 和 AgentCore 查询。

```text
Agent Runtime -- SigV4 --> Gateway -- invoke --> Lambda target
```

## 构建顺序

1. 建立 Lambda execution role，只允许写自己的 CloudWatch Logs。
2. 部署 `handler.py`，先在 Lambda 控制台或 CLI 以测试事件验证。
3. 在 Gateway 注册 Lambda target 与工具 schema。
4. 给 Runtime execution role 仅授予调用此 Gateway 的权限。
5. 从 Runtime 使用 SigV4 调用 Gateway，确认工具结果与 Lambda 日志。

## 为什么先做无业务数据工具

这样可以把“Runtime 不通、Gateway 鉴权失败、target schema 不匹配、Lambda 权限不足”分开排查。等链路打通后，再将 Lambda 变成只读 EC2/CloudWatch 工具，并添加命令、区域和结果数量限制。

参见 [CloudOps Gateway 模式](../../03-cloudops-demo/architecture.md)。
