# Observability

观察要覆盖四层：浏览器请求、控制面任务、Runtime 调用、MCP/Lambda 工具调用。不要把“模型回答慢”直接归因为 Runtime 冷启动：模型规划、工具执行、依赖等待、持久化和重试都会影响端到端时间。

CloudOps 的例子见 [CloudOps 观测与故障处理](../03-cloudops-demo/observability-and-failures.md)。
