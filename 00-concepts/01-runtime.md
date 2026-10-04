# Runtime

Runtime 把 Agent 的 HTTP 服务部署为 AgentCore 托管执行环境。中国区只支持 MicroVM capacity provider；因此要关注容器启动、依赖大小、健康检查和单次调用超时。

Runtime 负责运行 Agent，不负责你的业务状态、用户授权映射或任务编排。CloudOps 将这些放在控制面：DynamoDB 保存任务状态，S3 保存正文与结果，worker 负责恢复。

下一步：[第一个 Runtime 实验](../01-quickstart/first-runtime/README.md)。
