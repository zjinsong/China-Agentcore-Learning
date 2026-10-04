# CloudOps 架构案例

```text
Web UI → Control Plane → Supervisor Runtime → Specialist Runtime → Gateway → Lambda MCP → AWS API
                    │
                    └→ DynamoDB / S3 / SQS
```

控制面负责用户隔离、任务、依赖、重试、审批和结果持久化。Runtime 只执行 Agent；Gateway 是工具边界；Lambda target 持有最小业务权限。

与参考项目相同的思想是配置驱动 Agent、SigV4 运行时调用、工具追踪和依赖式报告；不同点是中国区不能使用托管 Harness、Memory、Registry，因此这些状态由应用控制面实现。
