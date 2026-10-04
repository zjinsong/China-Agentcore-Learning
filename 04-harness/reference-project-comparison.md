# 与 AWS CloudOps 示例的对照

参考项目采用 Supervisor → 领域 Agent → Leaf Agent 的层级结构，使用统一配置、Runtime 间 SigV4 HTTP、Gateway 工具、追踪和报告 DAG。[参考项目](https://github.com/aws-samples/sample-cloudops-multi-agent-system)

CloudOps Demo 保留配置驱动、工具边界、任务依赖与证据汇总；在中国区用 DynamoDB/S3/worker 替代 Memory、Harness、Registry。当前团队规模下两层更快：Supervisor 直接选择专家。增加中间领域 Agent 的条件是工具与领域显著增多，而不是为了模仿三层图。
