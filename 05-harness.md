# 5. Harness 实践

链路跑通后,新问题来了:模型可能选错工具、漏查资源、重复调用,某一步失败后任务一直挂着。Harness 就是管这些执行行为的那层逻辑。

中国区没有托管 Harness 组件,所以自己在应用里实现。

## 5.1 一句话

**Agent 决定怎么查,Harness 检查计划、按依赖执行、记录证据,保证任务最终有答复。**

还是那个问题:"查宁夏运行中 EC2 的性能,再查今天是否有关机"

```text
模型生成计划:
  步骤0  Monitoring  列出运行中 EC2
  步骤1  Monitoring  按实例 ID 查指标      depends_on: [0]
  步骤2  CloudTrail  查今天 StopInstances   depends_on: []

Harness:
  校验计划 → 执行就绪步骤(0 和 2 并行)→ 存证据
         → 0 完成后推进 1 → 全部结束 → 汇总
```

## 5.2 三层各管什么

| 层 | 管什么 | 不管什么 |
| --- | --- | --- |
| Runtime | 跑代码、隔离会话 | 不会自动实现你的工作流 |
| Gateway | 工具发现、鉴权、调用 | 不决定先查实例还是先查指标 |
| **Harness** | 任务生命周期、计划校验、依赖、预算、结果检查 | 不能用 prompt 代替 IAM |

## 5.3 最小实现有哪些部件

| 部件 | 输入/输出 | 为什么要 |
| --- | --- | --- |
| 能力目录 | 能力 id、工具、输入、输出、区域 | 光有专家名字不知道他能查什么 |
| 计划校验 | 计划 → 通过/拒绝 | 拦住不存在的能力、越权、循环依赖 |
| 调度器 | 已完成结果 → 就绪步骤 | 查指标必须等到真实实例 ID |
| 任务状态 | queued/running/succeeded/failed/timed_out | 页面和恢复流程要知道发生了什么 |
| 预算 | 总期限、单次期限、最大步数 | 不能无限等或反复调模型 |
| 证据 | 工具名、区域、时间窗、数据、错误 | 回答要能核对,区分空数据和失败 |
| 最终答复 | 成功结果 + 未解决项 | 一个专家失败也不能让用户干等 |

一开始把目录和调度写在 Python 里就行。需要异步、用户隔离、重启恢复时,再换成 DynamoDB 存任务 + S3 存证据 + SQS 唤醒 worker。

## 5.4 能力目录

```json
{
  "id": "query_ec2_metrics",
  "expert": "monitoring",
  "description": "按实例 ID 查询 CloudWatch 指标",
  "tools": ["cloudwatch___get_metric_data"],
  "inputs": ["region", "instance_ids", "start_time", "end_time"],
  "outputs": ["per_instance_metrics"],
  "regions": ["cn-northwest-1", "cn-north-1"],
  "access": "read_only"
}
```

部署后核对三件事,少一件这个能力就不能用:

1. 专家是启用状态
2. 对应 Runtime 可调用
3. 所需工具**确实出现在 Gateway 的实际工具清单里**

第 3 点容易漏:配置文件里写了工具名,不代表 Gateway 真注册了。要从 Gateway 实际 inventory 刷新,而不是拿本地 schema 当证明。

## 5.5 计划校验

```python
def validate(plan, catalog):
    allowed = {c["id"]: c for c in catalog}
    for index, step in enumerate(plan):
        cap = allowed.get(step["capability"])
        if not cap:
            raise ValueError(f"能力不存在: {step['capability']}")
        if cap["expert"] != step["agent"]:
            raise ValueError("能力不属于这个专家")
        for dep in step.get("depends_on", []):
            if dep < 0 or dep >= index:
                raise ValueError("依赖只能指向前面的步骤")
        if cap["regions"] and step.get("region") not in cap["regions"]:
            raise ValueError("区域超出能力范围")
```

`dep < index` 这个约束同时解决了循环依赖——只能依赖前面的步骤,图必然无环。

还要校验:总步数上限、输入字段齐全、下游要的 output 上游确实提供。

同一专家可以有多个步骤(先发现再查指标),但同一能力不要重复出现。

## 5.6 调度:谁现在能跑

```python
def ready_steps(plan, results):
    out = []
    for i, step in enumerate(plan):
        if i in results:                      # 跑过了
            continue
        deps = step.get("depends_on", [])
        if all(d in results and results[d]["status"] == "succeeded" for d in deps):
            out.append(i)
    return out
```

上游失败时,下游**直接标失败,不执行**——别让它拿着空数据去查。

依赖的结果要传给下游:

```python
step_input = {
    "prompt": step["prompt"],
    "dependency_results": {d: results[d]["data"] for d in step.get("depends_on", [])},
}
```

指标步骤从这里拿 `instance_ids`,不让模型重新猜。

## 5.7 预算和超时

学习环境建议:整个任务 120 秒,单次工具调用 30 秒。

关键:**每步执行前按剩余预算缩短本次期限**,不是每步都重新拿 120 秒。

```python
deadline = time.time() + 120
...
remaining = deadline - time.time()
if remaining <= 0:
    finish(task, "任务超出总期限,已终止")
timeout = min(30, remaining)
```

重试策略:

- 只读的连接错误/限流 → 短重试一次
- 权限错误、参数错误、计划错误 → 直接失败,重试没意义

## 5.8 失败怎么报

好的终态答复:

```text
查到两台运行中 EC2 及其 CPU 指标(见上)。
关机审计查询因权限不足失败,无法判断今天是否有关机操作。
任务已结束。
```

不能写成:

- ❌ "今天没有关机操作"(权限失败说成没有事件)
- ❌ "CPU 为 0"(空数据说成零)
- ❌ "平台不支持审计查询"(一个角色权限不足说成平台能力缺失)

界面上创建任务后应立刻显示任务 ID 和当前阶段,终态给用户可读结果。

## 5.9 动手

### 看 harness 怎么调度

```bash
cd labs/multi-agent && ./run.sh
```

这个例子的 `harness.py` 就是上面讲的那些:`available_capabilities()`、`validate()`、`ready_steps()`、`blocked_steps()`、`Budget`。

**验证并行和依赖**:

```text
并行执行: ['步骤0', '步骤2']     ← 无依赖,同时发
  ✓ 步骤0 discover_running_ec2
  ✓ 步骤2 query_stop_events
并行执行: ['步骤1']               ← 等到步骤0 的 instance_ids
  ✓ 步骤1 query_ec2_metrics
```

**验证上游失败不带空数据往下跑**。只启动 cloudtrail,不启动 monitoring:

```bash
cd labs/multi-agent
PYTHONPATH=. python3 expert.py cloudtrail &
PYTHONPATH=. python3 supervisor.py "查性能指标和关机情况"
kill %1
```

```text
  ✗ 步骤0 discover_running_ec2: Connection refused
  ✓ 步骤2 query_stop_events
  ✗ 步骤1 跳过(上游失败)
...
- monitoring/discover_running_ec2 查询失败:Connection refused —— 该结论无法得出
- monitoring/query_ec2_metrics 查询失败:上游步骤 0 失败,未执行
```

审计照常成功,指标链条明确失败 —— 不会因为一个专家挂掉就整体卡住或编造结果。

**验证计划校验**:

```bash
cd labs/multi-agent
PYTHONPATH=. python3 - <<'PY'
import harness
caps = harness.available_capabilities()
for plan, label in [
    ([{"agent":"monitoring","capability":"不存在","depends_on":[]}], "能力不存在"),
    ([{"agent":"cloudtrail","capability":"query_ec2_metrics","depends_on":[]}], "专家不匹配"),
    ([{"agent":"monitoring","capability":"discover_running_ec2","depends_on":[1]},
      {"agent":"monitoring","capability":"query_ec2_metrics","depends_on":[0]}], "循环依赖"),
]:
    try:
        harness.validate(plan, caps)
        print(f"✗ {label} 未拦截")
    except ValueError as e:
        print(f"✓ {label}: {e}")
PY
```

**验证能力目录是单一事实来源**:改 `capabilities.json` 里 `"enabled": false` 停用一个专家,再跑 —— 它的能力从可用清单消失,Supervisor 选不到。

### 另一个实验:只看查询实现

```bash
python3 labs/cloudops-mini/workflow.py
```

确定性工作流,不起服务,专注在工具查询本身(时区处理、分页、空数据)。

### 接模型

理解结构之后,把 `supervisor.py` 的 `plan()` 换成 LLM,让它输出同样结构的 JSON:

```json
{"steps": [{"agent": "monitoring", "capability": "discover_running_ec2",
            "depends_on": [], "prompt": "..."}]}
```

**harness 的校验和执行完全不用改** —— 因为它只接受符合能力目录的计划。模型负责规划,harness 负责约束,IAM 负责权限。

## 5.10 和托管 Harness 的差别

Global 的托管 Harness 提供声明式工具、内置迭代/超时/token 上限控制。自己实现的版本只覆盖项目需要的部分,不等价。

但责任边界是一样的:**模型负责规划,Harness 负责约束和执行,IAM 负责权限**。这三件事不能互相代替——prompt 写得再严也不是权限控制。

完整实现参考 [China-AgentCore-Demo](https://github.com/zjinsong/China-Agentcore-Demo) 的 `control/` 目录(能力校验、DAG 调度、任务状态、证据汇总)。
