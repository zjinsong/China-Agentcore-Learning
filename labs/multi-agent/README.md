# 最小多 Agent 例子

一个 Supervisor + 两个专家,用**真实 A2A 协议**通信,**真实 harness 逻辑**调度。
默认离线跑(不需要模型、不需要部署、不需要 AWS 凭证)。

对应 [第 4 章 CloudOps 实践](../../04-cloudops.md) 和 [第 5 章 Harness](../../05-harness.md)。

## 跑起来

```bash
./run.sh
```

输出:

```text
计划(3 步):
  0. monitoring/discover_running_ec2 可并行
  1. monitoring/query_ec2_metrics 依赖[0]
  2. cloudtrail/query_stop_events 可并行

并行执行: ['步骤0', '步骤2']
  ✓ 步骤0 discover_running_ec2
  ✓ 步骤2 query_stop_events

并行执行: ['步骤1']
  ✓ 步骤1 query_ec2_metrics
```

看三件事:

- 步骤 0 和 2 **同时**发出(无依赖)
- 步骤 1 **等**步骤 0 返回 `instance_ids` 才跑
- 同一个专家(monitoring)执行了**两个不同能力**

## 文件

| 文件 | 作用 |
| --- | --- |
| `capabilities.json` | 能力目录。加能力改这里,不改代码 |
| `harness.py` | 计划校验、DAG 调度、预算(第 5 章那层) |
| `expert.py` | 专家 A2A 服务:Agent Card + JSON-RPC 2.0 |
| `supervisor.py` | 规划、调专家、按依赖推进、汇总 |
| `tools.py` | 工具实现。离线用固定数据,`--live` 走真实 AWS |

## 看 A2A 协议长什么样

启动一个专家:

```bash
PYTHONPATH=. python3 expert.py monitoring &
```

**Agent Card**(A2A 的发现机制,别的 Agent 靠它知道你能干什么):

```bash
curl -s http://127.0.0.1:9001/.well-known/agent-card.json | python3 -m json.tool
```

**JSON-RPC 2.0 调用**(method 固定是 `message/send`):

```bash
curl -s -X POST http://127.0.0.1:9001/ \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {"message": {
      "contextId": "demo",
      "parts": [{"kind": "text", "text": "列出运行中实例"}],
      "metadata": {"capability": "discover_running_ec2", "region": "cn-northwest-1"}
    }}
  }' | python3 -m json.tool

kill %1
```

## 换问题

```bash
./run.sh --question "今天有没有关机操作"      # 只触发审计,单步
./run.sh --question "查一下 CPU"               # 只触发监控,两步依赖链
./run.sh --json                                # 打印完整任务记录
```

## 真实只读查询

需要 `ec2:DescribeInstances`、`cloudwatch:GetMetricStatistics`、`cloudtrail:LookupEvents`:

```bash
export AWS_PROFILE=china-learning
./run.sh --live --region cn-northwest-1
```

真实模式下会看到三种结果的区别:

- **真实数据**:实例 ID 和指标值
- **空数据**:`该时间窗无数据点(不等于 CPU 为 0)`
- **工具错误**:权限不足等,明确报失败,**不说成"没有事件"**

## 失败传播

故意不启动 monitoring,只启动 cloudtrail:

```bash
PYTHONPATH=. python3 expert.py cloudtrail &
PYTHONPATH=. python3 supervisor.py "查性能指标和关机情况"
kill %1
```

结果:

```text
  ✗ 步骤0 discover_running_ec2: Connection refused
  ✓ 步骤2 query_stop_events
  ✗ 步骤1 跳过(上游失败)
```

步骤 1 **不带空数据执行**,直接标失败。审计不受影响照常完成。

## 计划校验

harness 只接受符合能力目录的计划:

```bash
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

四种都会被拒:能力不存在、专家不匹配、循环依赖(依赖只能指向前序步骤)、同一能力重复。

## 停用一个专家

改 `capabilities.json` 里 `"enabled": false`,再跑一次 —— 那个专家的能力会从可用清单消失,Supervisor 选不到它。这就是第 5 章说的"能力目录是单一事实来源"。

## 和真实部署的差距

这个例子为了能本地跑做了简化:

| 这里 | 真实部署 |
| --- | --- |
| 标准库 HTTP server,localhost 端口 | AgentCore Runtime,A2A 协议端口 9000 |
| 无鉴权 | SigV4 签名 |
| 工具函数直接调 boto3 | 工具在 Gateway 的 Lambda target,专家通过 MCP 调 |
| 关键词匹配生成计划 | LLM 输出 JSON 计划(harness 校验不变) |
| 任务状态在内存 | DynamoDB 存任务,S3 存证据,SQS 唤醒 worker |

**协议结构和 harness 逻辑是一样的** —— 换成真实部署时,`plan()` 换 LLM、`call_expert()` 换成 SigV4 调 Runtime、`tools.py` 搬进 Lambda,`harness.py` 基本不用改。

完整实现见 [China-AgentCore-Demo](https://github.com/zjinsong/China-Agentcore-Demo) 的 `control/` 目录。
