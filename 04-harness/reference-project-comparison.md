# 与 AWS CloudOps 参考项目的对照

参考：[aws-samples/sample-cloudops-multi-agent-system](https://github.com/aws-samples/sample-cloudops-multi-agent-system)。它展示配置驱动的层级 Agent、Runtime 间调用、Gateway 工具和运行追踪。

| 思路 | 学习项目怎么用 |
| --- | --- |
| Supervisor → 领域 Agent → Leaf Agent | 入门先用 Supervisor 直接调少量专家，理解后按领域规模考虑增加层级 |
| 声明式层级配置 | 声明专家 Runtime、工具和能力输入/输出 |
| Runtime 间 IAM / SigV4 调用 | 用部署章节相同的 Invoke 方式委派任务，限制目标 Runtime |
| Gateway 工具接入 | 按正文给 Lambda 加 schema 和只读权限，不把所有 AWS 权限交给 Supervisor |
| 工具追踪、任务依赖与报告 | Harness 保存结构化证据，再汇总；失败时保留未解决项 |

这些思想可借鉴，不需要复制完整 UI 与所有专家。原参考项目是否使用托管 Harness 应按其当前代码核对，不能因为中国区缺失该组件就推断参考项目一定依赖它。

中国区学习实现按自身需要使用配置、应用任务状态和 worker；DynamoDB / S3 是可选的持久化方式。具体实践见 [CloudOps](../03-cloudops-demo/README.md)。
