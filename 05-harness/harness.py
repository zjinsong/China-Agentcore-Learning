"""最小 Harness:一个 agent 任务要可执行、可观察、可结束,需要的那层逻辑。

中国区没有 AgentCore 托管 Harness,所以用应用代码实现等价的最小循环。
本文件不依赖模型和网络,直接运行即可看到:计划校验、依赖调度、证据记录、
失败处理。真实场景把 TOOLS 换成 Gateway 工具、把 plan() 换成模型输出即可。
"""
import time

# 工具目录:每个工具声明它要什么输入、产出什么。
# 这是单一事实来源 —— 计划只能引用这里有的工具。
TOOLS = {
    "get_weather": {"inputs": ["city"], "outputs": ["weather"]},
    "suggest_outfit": {"inputs": ["weather"], "outputs": ["suggestion"]},
}


def _get_weather(city):
    data = {"北京": {"temp_c": 28, "condition": "晴"},
            "上海": {"temp_c": 18, "condition": "雨"}}.get(city)
    if data is None:
        raise ValueError(f"没有 {city} 的天气数据")
    return {"weather": {"city": city, **data}}


def _suggest_outfit(weather):
    temp = weather["temp_c"]
    tip = "短袖" if temp >= 25 else "外套" if temp >= 15 else "厚外套"
    if weather["condition"] == "雨":
        tip += " + 带伞"
    return {"suggestion": tip}


IMPL = {"get_weather": _get_weather, "suggest_outfit": _suggest_outfit}


def validate(plan):
    """拦住:不存在的工具、指向后面步骤的依赖(循环)。"""
    if not plan:
        raise ValueError("计划为空")
    for i, step in enumerate(plan):
        if step["tool"] not in TOOLS:
            raise ValueError(f"步骤 {i}: 工具不存在 {step['tool']}")
        for dep in step.get("depends_on", []):
            if dep < 0 or dep >= i:
                raise ValueError(f"步骤 {i}: 依赖 {dep} 必须指向更早的步骤")


def run(plan, total_budget=30):
    """按依赖推进:就绪的步骤执行,上游失败的跳过,全部结束后返回证据。"""
    validate(plan)
    deadline = time.time() + total_budget
    results = {}

    while len(results) < len(plan):
        # 上游失败 -> 下游直接标失败,不带空数据执行
        for i, step in enumerate(plan):
            if i in results:
                continue
            if any(results.get(d, {}).get("status") == "failed"
                   for d in step.get("depends_on", [])):
                results[i] = {"status": "failed", "tool": step["tool"],
                              "error": "上游失败,未执行"}

        ready = [i for i, step in enumerate(plan)
                 if i not in results
                 and all(results.get(d, {}).get("status") == "succeeded"
                         for d in step.get("depends_on", []))]
        if not ready:
            break
        if time.time() > deadline:
            for i in ready:
                results[i] = {"status": "failed", "tool": plan[i]["tool"],
                              "error": "超出总预算"}
            break

        for i in ready:
            step = plan[i]
            # 依赖的产出传给当前步骤
            args = dict(step.get("args", {}))
            for d in step.get("depends_on", []):
                args.update(results[d]["data"])
            try:
                data = IMPL[step["tool"]](**{k: args[k] for k in TOOLS[step["tool"]]["inputs"]})
                results[i] = {"status": "succeeded", "tool": step["tool"], "data": data}
            except Exception as error:                       # noqa: BLE001
                results[i] = {"status": "failed", "tool": step["tool"], "error": str(error)}
    return results


def summarize(results):
    done = sum(r["status"] == "succeeded" for r in results.values())
    failed = sum(r["status"] == "failed" for r in results.values())
    lines = [f"完成 {done} 步,失败 {failed} 步"]
    for i in sorted(results):
        r = results[i]
        if r["status"] == "succeeded":
            lines.append(f"  步骤{i} {r['tool']}: {r['data']}")
        else:
            lines.append(f"  步骤{i} {r['tool']} 失败: {r['error']}")
    return "\n".join(lines)


if __name__ == "__main__":
    # 计划:查天气 -> 根据天气给穿衣建议(有依赖)。真实场景由模型生成这个结构。
    plan = [
        {"tool": "get_weather", "args": {"city": "上海"}, "depends_on": []},
        {"tool": "suggest_outfit", "depends_on": [0]},
    ]
    print(summarize(run(plan)))
