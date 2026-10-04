# 5. Harness 应用

第 4 章的 agent 能调工具回答问题。但当一个任务需要**多步、有先后依赖、要控制预算和失败**时,光靠模型自己跑循环不够可靠 —— 它可能漏步、重复调、某步失败后不知所措。Harness 就是管这个执行过程的那层逻辑。

## 5.1 Harness 是什么

AgentCore 官方的 **Harness** 是一个托管的 agent 循环:一次 API 调用指定模型、系统提示词和工具,平台负责编排、工具执行、记忆管理和生成回答。

**中国区没有托管 Harness**,所以用应用代码实现等价的最小循环。职责是一样的:

| Harness 负责 | 不负责 |
| --- | --- |
| 校验计划、按依赖调度、记录证据、保证任务有终态 | 不代替模型做规划 |
| 控制预算(总时长、步数) | 不代替 IAM 做权限 |

一句话:**模型决定做什么,Harness 保证做的过程可控、可观察、有结果。**

## 5.2 最小实现需要什么

| 部件 | 作用 |
| --- | --- |
| 工具目录 | 声明每个工具要什么输入、产出什么;计划只能引用目录里的工具 |
| 计划校验 | 拦住不存在的工具、循环依赖 |
| 依赖调度 | 就绪的步骤执行,上游失败的跳过 |
| 证据记录 | 每步的工具、结果或错误都留痕,可核对 |
| 预算 | 总时长、步数上限,避免无限循环 |

## 5.3 一个例子

[`05-harness/harness.py`](05-harness/harness.py) 不到 110 行,实现上面全部部件。任务:**查天气 → 根据天气给穿衣建议**(第二步依赖第一步的结果)。

工具目录是单一事实来源:

```python
TOOLS = {
    "get_weather":    {"inputs": ["city"],    "outputs": ["weather"]},
    "suggest_outfit": {"inputs": ["weather"], "outputs": ["suggestion"]},
}
```

计划校验只接受目录里的工具,且依赖只能指向更早的步骤(这样图必然无环):

```python
def validate(plan):
    for i, step in enumerate(plan):
        if step["tool"] not in TOOLS:
            raise ValueError(f"步骤 {i}: 工具不存在 {step['tool']}")
        for dep in step.get("depends_on", []):
            if dep < 0 or dep >= i:
                raise ValueError(f"步骤 {i}: 依赖 {dep} 必须指向更早的步骤")
```

调度按依赖推进,上游失败则下游跳过(不带空数据往下跑):

```python
# 上游失败 -> 下游直接标失败
if any(results.get(d, {}).get("status") == "failed"
       for d in step.get("depends_on", [])):
    results[i] = {"status": "failed", "error": "上游失败,未执行"}
```

依赖的产出会传给下游 —— 穿衣建议用的是上一步查到的真实天气,不是模型猜的。

## 5.4 跑一下

```bash
python3 05-harness/harness.py
```

正常输出(依赖链):

```text
完成 2 步,失败 0 步
  步骤0 get_weather: {'weather': {'city': '上海', 'temp_c': 18, 'condition': '雨'}}
  步骤1 suggest_outfit: {'suggestion': '外套 + 带伞'}
```

**失败传播** —— 查一个没有数据的城市:

```python
plan = [
    {"tool": "get_weather", "args": {"city": "广州"}, "depends_on": []},
    {"tool": "suggest_outfit", "depends_on": [0]},
]
```

```text
完成 0 步,失败 2 步
  步骤0 get_weather 失败: 没有 广州 的天气数据
  步骤1 suggest_outfit 失败: 上游失败,未执行
```

第二步没有拿着空数据硬跑,而是明确跳过 —— 这正是 Harness 的价值:**失败是失败,不会被当成"没有结果"糊弄过去。**

**计划校验**:

```python
validate([{"tool": "不存在", "depends_on": []}])              # 工具不存在
validate([{"tool": "get_weather", "depends_on": [1]}, ...])  # 循环依赖
```

两种都会被拒。

## 5.5 接模型

例子里的 `plan` 是手写的。真实场景让模型生成它 —— 模型只输出计划的 JSON 结构:

```json
{"plan": [
  {"tool": "get_weather", "args": {"city": "上海"}, "depends_on": []},
  {"tool": "suggest_outfit", "depends_on": [0]}
]}
```

**`validate()` 和 `run()` 一个字都不用改**:模型输出不合法的计划(用了不存在的工具、循环依赖)会被 `validate()` 直接拒掉。这就是分工 ——

- **模型**负责规划(把自然语言变成计划)
- **Harness**负责约束和执行(校验、调度、记录)
- **IAM**负责权限(工具能访问什么)

三者不互相替代。模型会犯错,所以计划要校验;prompt 写得再严也不是权限,所以权限归 IAM。

## 5.6 从最小实现到生产

| 这里 | 生产 |
| --- | --- |
| 工具是本地函数 | Gateway 的 Lambda target,agent 通过 MCP 调 |
| `plan` 手写 | 模型输出 JSON 计划 |
| 结果在内存 | 外部存储(DynamoDB 存状态,S3 存证据) |
| 单次运行 | 异步任务 + 恢复(用 `runtimeSessionId` 续上下文) |

核心的"校验 → 调度 → 记录"逻辑在扩展过程中基本不变,这是把它单独拎出来做成一层的意义。

至此五章完成:中国区能用什么([1](01-china-region.md))→ 用 MCP 辅助开发([2](02-vibe-coding.md))→ 部署一条链路([3](03-build.md))→ 构建一个 agent([4](04-agent-app.md))→ 让多步任务可靠执行(本章)。
