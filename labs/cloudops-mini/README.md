# CloudOps mini 实验

确定性的 Python 工作流,演示"资源发现 → 指标查询"的依赖关系和"审计并行"的结构。不调模型、不部署 Runtime。

配合 [第 5 章 Harness](../../05-harness.md) 读。

## 离线运行

```bash
python3 labs/cloudops-mini/workflow.py
```

用 `demo-instance-a` / `demo-instance-b` 这类明显虚构的 ID。不读 AWS 凭证、不调云端。

观察四件事:

- 发现(步骤 0)和审计(步骤 2)**并行**发出
- 指标(步骤 1)**等到**步骤 0 返回 instance_ids 才执行
- 每步证据里有工具名、时间窗、数据或错误
- 上游失败时下游标记失败,**不带空数据执行**

## 真实只读查询

需要这三个权限:`ec2:DescribeInstances`、`cloudwatch:GetMetricStatistics`、`cloudtrail:LookupEvents`。

```bash
export AWS_PROFILE=china-learning
python3 labs/cloudops-mini/workflow.py --live --region cn-northwest-1
```

查当前身份所在账户、指定区域、北京时间今天。结果写入 `.local/cloudops-mini.json`,终端只打印阶段。

查询超时或失败会写进 `error` 字段 —— 那是**失败**,不是"没有事件"。
