# 4. Harness：让 Agent 任务可执行、可观察、可结束

完成部署链路后，你已经能运行代码和调用工具。但自然语言任务仍可能出现选错工具、漏查资源、重复调用、某一步失败后一直等待等问题。Harness 就是应用里管理这些执行行为的逻辑。

## 4.1 先用一句话理解

**Agent 决定怎么查，Harness 检查计划、执行步骤、记录结果，并保证任务最终有答复。**

例如“查宁夏运行中 EC2 的性能，再查今天是否有关机”：

```text
Agent 生成计划
  0. Monitoring：列出运行中 EC2
  1. Monitoring：按实例 ID 查询指标，依赖步骤 0
  2. CloudTrail：查询今天 StopInstances，可与步骤 0 并行

Harness 校验 → 执行就绪步骤 → 保存证据 → 推进依赖 → 汇总或明确报错
```


## 4.2 和 Runtime / Gateway 的关系

| 层 | 职责 | 不应混淆的地方 |
| --- | --- | --- |
| Runtime | 运行 Agent 代码、隔离会话与执行环境 | 不会自动实现你的业务工作流 |
| Gateway | 提供工具发现、鉴权与调用入口 | 不负责决定先查实例还是先查指标 |
| Harness | 任务生命周期、计划校验、依赖、预算、结果检查 | 不靠 Prompt 代替 IAM 权限 |

中国区未提供 AgentCore 托管 Harness 组件，因此这里采用应用侧控制逻辑。它只实现本项目需要的功能，不声称与托管产品完整等价。[中国区可用性](https://docs.amazonaws.cn/en_us/aws/latest/userguide/bedrock-agentcore.html)

## 4.3 最小实现需要哪些内容

| 内容 | 输入 / 输出 | 为什么需要 |
| --- | --- | --- |
| 能力目录 | 输入类型、工具、区域、结果字段 | 专家名字不足以说明能查什么 |
| 计划校验 | capability、depends_on、参数 | 拦截不存在能力、越权和循环依赖 |
| 调度器 | 已完成结果 → 就绪步骤 | 指标查询必须拿到真实实例 ID |
| 任务状态 | queued / running / succeeded / failed / timed_out | 页面与恢复流程知道发生了什么 |
| 预算 | 总期限、单调用期限、最大步骤和重试次数 | 不能无限等待或反复调用模型 |
| 证据 | 工具名、区域、时间窗、资源、数据、错误 | 回答可核对，区分空数据和查询失败 |
| 最终答复 | 已完成结果 + 未解决项 | 单个专家失败也不能让用户一直等 |

最初可把目录和调度放在 Python 代码里。需要异步任务、用户隔离与恢复时再使用 DynamoDB 保存任务、S3 保存证据、SQS 触发 worker，不必在第一个 Runtime 实验就引入全部组件。

## 4.4 能力目录怎么写

```json
{
  "id":"query_ec2_metrics",
  "expert":"monitoring",
  "required_inputs":["region","instance_ids","start_time","end_time"],
  "outputs":["per_instance_metrics"],
  "tools":["cloudwatch_query"],
  "access":"read_only",
  "regions":["cn-northwest-1","cn-north-1"]
}
```

部署时核对三件事：专家启用、对应 Runtime 可调用、所需工具确实出现在 Gateway inventory。文件中的声明不等于真实权限，最终仍由 IAM 和工具实现限制。

## 4.5 校验计划的正确边界

```python
allowed = {"discover_running_ec2", "query_ec2_metrics", "query_stop_events"}
for index, step in enumerate(plan):
    if step["capability"] not in allowed:
        raise ValueError("Unknown capability")
    if any(dep < 0 or dep >= index for dep in step["depends_on"]):
        raise ValueError("Dependency must reference an earlier step")
```

这是简化示意：只允许前序依赖可避免循环。正式实现还要验证输入、区域、总步骤数、身份、工具可用性与依赖输出字段。同一专家允许多步；若需要同一能力按多实例重复，应有明确的去重/批处理规则，而不是一律拒绝。

## 4.6 失败和超时怎么表现

建议学习用策略：整项任务 120 秒，工具调用最长 30 秒；每次执行前按剩余预算缩短调用期限，不能每步重新获得 120 秒。这个数字是教程建议，不是 AgentCore 的平台上限。

只读连接故障可短重试一次；权限错误和计划错误直接报错。可并行执行的独立步骤同时发出；有依赖的步骤等待真实结果。

示例最终答复：

```text
已查询到两台运行中 EC2 和 CPU 指标。
关机审计查询因权限不足失败，因此无法判断今天是否发生过关机。
任务已结束；技术错误保存在本次 task 的审计结果中。
```

不把权限错误写成“没有关机”，不把指标空数据写成“CPU 为 0”。UI 应在创建任务后立即显示 task ID 和执行阶段，并在终态呈现用户可读结果。

## 4.7 用实验理解，再接模型

[CloudOps mini 实验](../labs/cloudops-mini/README.md) 提供离线虚构数据，以及可选的真实中国区只读查询。它是确定性的工作流教学程序，不调用 LLM、不伪装自然语言多 Agent。

用它验证依赖与证据结构后，让模型只生成符合 schema 的计划；Harness 校验后通过 Runtime/Gateway 执行。参考架构见 [与 AWS Sample 对照](reference-project-comparison.md)。

下一步：[5. CloudOps 例子实践](../03-cloudops-demo/README.md)。
