# CloudOps mini：理解工作流再接 Agent

本实验是确定性的 Python 工作流，演示资源发现、CPU 查询、关机审计和证据记录。它不调用模型、不部署 Runtime，不代表自然语言多 Agent 已完成部署。

## 离线运行

从仓库根目录执行：

```powershell
python labs/cloudops-mini/workflow.py
```

使用 `demo-instance-a` / `demo-instance-b` 等明显虚构标识。预期三个步骤完成，CPU 按实例呈现，审计返回单独标记的虚构事件。离线模式不读取 AWS 凭证、不调用云端。

## 真实只读查询

需要 EC2 DescribeInstances、CloudWatch GetMetricStatistics、CloudTrail LookupEvents：

```powershell
$env:AWS_PROFILE = "china-learning"
python labs/cloudops-mini/workflow.py --live --region cn-northwest-1
```

查询本地身份所在账户、中国区、北京时间今天。结果只保存在 `.local/cloudops-mini.json`，终端打印完成阶段，避免直接输出真实数据。实时查询超时/失败会写入 error 字段；不是“没有事件”。

本程序未实现生产任务的硬截止与持久化恢复。生产 Harness 要对总预算、单调用超时、并发、分页总量和任务终态分别控制；见 [Harness](../../04-harness/README.md)。

## 如何变成部署后工具

将 `discover`、`metrics`、`audit` 分别封装为 Lambda handler，配置输入 schema 和只读权限，按 [Gateway 部署](../../02-build-agentcore/gateway-lambda-mcp/README.md) 注册工具。专家 Runtime 调用这些工具，Supervisor 生成计划，由 Harness 校验并执行。

完整实践：[CloudOps 例子](../../03-cloudops-demo/README.md)。代码最后参考：[workflow.py](workflow.py)。
