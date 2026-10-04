# Harness：Global 与中国区

Harness 不是“另一个专家”，而是运行 Agent 系统所需的控制逻辑：配置、能力发现、任务计划、预算、依赖、重试、状态、证据和结果检查。

Global AgentCore 可以使用托管 Harness；中国区不提供该组件。CloudOps 因此采用应用侧控制面：

```text
hierarchy.json + DynamoDB agent/task records + S3 results + worker + capability inventory
```

这不是对官方 Harness 的一比一复刻，而是针对中国区可用服务构建的最小替代。详细对比见 [参考项目对照](reference-project-comparison.md)。
