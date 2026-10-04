# 中国区部署检查表

1. 选择北京或宁夏，并在代码、IAM、日志和工具参数中保持一致。
2. 用容器和 boto3 部署 Runtime；不要假设 Global AgentCore CLI 路径在中国区可用。
3. Gateway 选择 AWS_IAM 或企业 OIDC 的 CUSTOM_JWT；不要配置 No auth。
4. 使用 MicroVM，控制镜像体积与冷启动依赖。
5. 将会话、任务与结果放在 DynamoDB/S3；不要依赖托管 Memory/Harness/Registry。
6. Gateway 工具发现使用应用能力目录；不要依赖 semantic search。
7. 用 IAM 和工具适配器限制区域、读写操作、结果量和敏感字段。
8. 用真实中国区工具调用验证，而不是只验证部署状态。

部署前后均需复核官方区域差异：[AWS China AgentCore](https://docs.amazonaws.cn/en_us/aws/latest/userguide/bedrock-agentcore.html)。

完整逐步操作在 [第 3 部分部署指南](../02-build-agentcore/README.md)，本页作为补充核对清单。
