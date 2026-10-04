"""一个能查天气的 agent:模型 + 两个工具,部署到 AgentCore Runtime。

工具用确定性的示例数据,不依赖外部天气 API —— 这样不配任何第三方 key 也能
跑通"模型理解问题 → 调工具 → 用结果回答"的完整链路。换成真实天气 API 只需
改工具函数体,agent 代码不变。

模型通过 OpenAI 兼容接口接入(见第 3 章 3.10),三个环境变量:
MODEL_BASE_URL / MODEL_ID / MODEL_API_KEY。未配置时用离线回显模型,方便本地
先验证工具链路。
"""
import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool

# 示例数据:城市 -> 天气。真实场景替换成天气 API 调用。
_WEATHER = {
    "北京": {"condition": "晴", "temp_c": 28, "humidity": 35},
    "上海": {"condition": "多云", "temp_c": 26, "humidity": 60},
    "银川": {"condition": "晴", "temp_c": 24, "humidity": 30},
}


@tool
def get_weather(city: str) -> dict:
    """查询指定城市的当前天气。参数 city 是中文城市名,如 北京。"""
    data = _WEATHER.get(city)
    if data is None:
        return {"error": f"没有 {city} 的天气数据", "available": list(_WEATHER)}
    return {"city": city, **data}


@tool
def compare_temperature(city_a: str, city_b: str) -> dict:
    """比较两个城市的气温,返回更热的城市和温差。"""
    a, b = _WEATHER.get(city_a), _WEATHER.get(city_b)
    if a is None or b is None:
        return {"error": "城市数据缺失", "available": list(_WEATHER)}
    diff = a["temp_c"] - b["temp_c"]
    hotter = city_a if diff > 0 else city_b if diff < 0 else "相同"
    return {"hotter": hotter, "difference_c": abs(diff)}


def build_model():
    """配了三个环境变量就用真实模型,否则用离线回显模型(只验证工具链路)。"""
    if os.environ.get("MODEL_API_KEY"):
        from strands.models.openai import OpenAIModel
        return OpenAIModel(
            client_args={
                "api_key": os.environ["MODEL_API_KEY"],
                "base_url": os.environ["MODEL_BASE_URL"],
            },
            model_id=os.environ["MODEL_ID"],
            params={"temperature": 0.2, "max_tokens": 2048},
        )
    return None


app = BedrockAgentCoreApp()
_model = build_model()
_agent = Agent(
    model=_model,
    tools=[get_weather, compare_temperature],
    system_prompt="你是天气助手。必须调用工具获取数据后再回答,不要凭记忆编造天气。",
) if _model else None


@app.entrypoint
def handler(event, context):
    prompt = str(event.get("prompt", ""))
    if _agent is None:
        # 离线模式:没有模型,直接演示工具本身
        return {"mode": "offline", "note": "未配置模型,直接调用工具演示",
                "get_weather(北京)": get_weather("北京")}
    return {"answer": str(_agent(prompt))}


if __name__ == "__main__":
    app.run()
