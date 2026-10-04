# CloudOps Demo：从单 Agent 到协作 DAG

本章以当前 CloudOps Demo 的公开、脱敏架构为案例，不复制任何生产配置。

```text
Supervisor
 ├─ Monitoring：发现运行中的 EC2
 │    └─ Monitoring：按实例 ID 查询 CloudWatch 指标
 └─ CloudTrail：并行查询 StopInstances 审计事件
```

学习顺序：

1. [架构](architecture.md)
2. [能力目录](capability-catalog.md)
3. [依赖工作流](dependency-workflow.md)
4. [观测与失败](observability-and-failures.md)
5. [Terraform 安全边界](terraform-safety.md)

参考架构来自 [aws-samples/sample-cloudops-multi-agent-system](https://github.com/aws-samples/sample-cloudops-multi-agent-system)。本项目选择两层 Supervisor → 专家，而非先复制其三层树；当领域数量和工具规模增长后，才评估增加中间领域协调员。
