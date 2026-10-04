# 4. 构建一个 agent 应用

第 3 章部署的是一个只会回显的应用。这一章把它变成真正的 agent:**模型 + 工具**,一个能查天气的助手。

## 4.1 agent 是什么

一个 agent 由三部分组成:

- **模型**:理解用户问题,决定调用哪个工具,把工具结果组织成回答
- **工具**:模型能调用的函数,用来获取数据或执行动作
- **循环**:模型调工具 → 看结果 → 可能再调 → 直到能回答。这个循环由 agent 框架(这里用 Strands Agents)实现

```text
用户:"北京和上海哪个热?"
  → 模型决定调 compare_temperature(北京, 上海)
  → 工具返回 {hotter: 北京, difference_c: 2}
  → 模型组织成回答:"北京更热,高 2 摄氏度。"
```

模型不自己编天气数据,而是**调工具拿真实数据**——这是 agent 和普通聊天的区别。

## 4.2 代码

[`04-agent-app/app.py`](04-agent-app/app.py) 的核心。先定义工具:

```python
from strands import tool

@tool
def get_weather(city: str) -> dict:
    """查询指定城市的当前天气。参数 city 是中文城市名,如 北京。"""
    data = _WEATHER.get(city)
    if data is None:
        return {"error": f"没有 {city} 的天气数据", "available": list(_WEATHER)}
    return {"city": city, **data}
```

`@tool` 装饰器把函数变成模型可调用的工具。**函数名、类型标注、docstring 就是模型看到的工具说明**,需清晰描述工具的用途和参数。本例工具使用示例数据,换成真实天气 API 只需修改函数体,其余不变。

再把模型和工具组装成 agent:

```python
from strands import Agent

agent = Agent(
    model=model,                                  # 第 3 章 3.10 的接法
    tools=[get_weather, compare_temperature],
    system_prompt="你是天气助手。必须调用工具获取数据后再回答,不要凭记忆编造天气。",
)
```

放进 Runtime 入口:

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def handler(event, context):
    return {"answer": str(agent(str(event.get("prompt", ""))))}

app.run()
```

`agent(prompt)` 一行就跑完整个"模型 ↔ 工具"循环,框架处理中间的多轮调用。

## 4.3 配模型

按第 3 章 [3.10](03-build.md#310-接模型从-echo-变成真-agent),三个环境变量:

```bash
export MODEL_BASE_URL="https://api.deepseek.com/v1"
export MODEL_ID="deepseek-chat"
export MODEL_API_KEY="sk-xxxxxxxx"
```

本例未配置模型也能运行:没有 `MODEL_API_KEY` 时 `app.py` 进入离线模式,直接调用工具并返回结果,用于先验证工具逻辑,再接入模型。

## 4.4 本地验证

```bash
python3 -m pip install -r 04-agent-app/requirements.txt
python3 04-agent-app/app.py
```

另开终端:

```bash
# 配了模型:
curl -X POST http://127.0.0.1:8080/invocations \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"北京和上海哪个热?"}'
# 预期 answer 里说明北京更热、温差 2 度,且是模型调用工具得出的

# 没配模型(离线):
curl -X POST http://127.0.0.1:8080/invocations \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"test"}'
# 预期返回 get_weather(北京) 的工具结果
```

验证重点:配置模型后,模型应当**确实调用了工具**。若模型未调用工具而直接编造天气,检查 docstring 是否清晰、system_prompt 是否要求"必须调用工具"。

## 4.5 部署

和第 3 章完全一样的流程,只是换个应用目录和 Runtime 名字:

```bash
# 构建 arm64 镜像(目录换成 04-agent-app)
docker buildx build --platform linux/arm64 --provenance=false --load \
  -t weather-agent:v1 04-agent-app

# 推 ECR、创建 Runtime、注入模型环境变量、调用
# 复用第 3 章 deploy_runtime.py 的步骤,environmentVariables 带上三个 MODEL_ 变量
```

部署后调用:

```bash
python3 03-build/deploy_runtime.py invoke --prompt "银川今天天气怎么样?"
```

## 4.6 加 Gateway 工具

4.2 的工具是写死在 agent 代码里的。要让工具独立于 agent、可被多个 agent 复用,就把它放到 Gateway 的 Lambda target(第 3 章 3.7–3.9),agent 侧改成调用 Gateway:

```python
@tool
def get_weather(city: str) -> dict:
    """查询指定城市的当前天气。"""
    return gateway_client.call("weather___get_weather", {"city": city})
```

什么时候用哪种:

| | 工具写在 agent 里 | 工具放 Gateway |
| --- | --- | --- |
| 适合 | 简单、专属这个 agent | 多个 agent 共用、要独立权限 |
| 权限 | 用 Runtime 执行角色 | 用 Lambda 执行角色,边界更清晰 |

## 4.7 小结

一个 agent = 模型 + 工具 + 框架的调用循环。本章的 agent 单独工作;当一个任务需要多步、有先后依赖、要控制预算和失败处理时,就需要一层编排逻辑来管这个过程 —— 那是第 5 章 Harness 的主题。

下一步:[5. Harness 应用](05-harness.md)
