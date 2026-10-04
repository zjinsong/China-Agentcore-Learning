# CloudOps Mini Lab

这个 Lab 的目标是实现最小安全工作流，而不是复制完整系统：

```text
Supervisor → resource discovery → metric query
                 └────────────→ audit query
```

实验数据使用你自己的隔离账号，并只授予 `DescribeInstances`、CloudWatch 读取和 CloudTrail `LookupEvents` 等最小权限。先运行无业务数据的 Gateway Lab，再接入真实只读资源。

实现要求：

- 将实例 ID 作为结构化上游结果传给指标步骤；
- 审计步骤独立并行；
- 上游失败时不运行指标步骤；
- 任务最终失败时在聊天里写用户可读答复；
- 不将 ARN、实例 ID、账号 ID、审计事件或截图提交到 Git。

完整设计见 [CloudOps Demo](../../03-cloudops-demo/README.md)。
