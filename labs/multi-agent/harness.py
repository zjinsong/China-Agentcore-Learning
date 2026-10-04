"""Harness: 能力目录、计划校验、DAG 调度、任务状态。

这是第 5 章讲的那层逻辑的最小实现。模型(或固定规划器)只生成计划,
由这里校验和推进 —— 模型不碰执行和权限。
"""
import json
import time
from pathlib import Path

CATALOG = json.loads((Path(__file__).with_name("capabilities.json")).read_text(encoding="utf-8"))


def available_capabilities():
    """只返回已启用专家的能力。部署时这里还要核对 Gateway 实际工具清单。"""
    out = []
    for expert, cfg in CATALOG["experts"].items():
        if not cfg.get("enabled"):
            continue
        for cap in cfg["capabilities"]:
            out.append({**cap, "expert": expert, "port": cfg["port"]})
    return out


def validate(plan, capabilities):
    """拦住不存在的能力、专家不匹配、非法依赖。返回 (能力 id -> 能力) 映射。"""
    by_id = {c["id"]: c for c in capabilities}
    if not plan:
        raise ValueError("计划为空")
    if len(plan) > 6:
        raise ValueError("步骤超过 6 步上限")
    seen = set()
    for index, step in enumerate(plan):
        cap = by_id.get(step.get("capability"))
        if cap is None:
            raise ValueError(f"能力不存在或专家已停用: {step.get('capability')}")
        if cap["expert"] != step.get("agent"):
            raise ValueError(f"能力 {cap['id']} 属于 {cap['expert']},不是 {step.get('agent')}")
        if cap["id"] in seen:
            raise ValueError(f"同一能力重复: {cap['id']}")
        seen.add(cap["id"])
        for dep in step.get("depends_on", []):
            # 只允许依赖前序步骤 —— 这同时保证图无环
            if dep < 0 or dep >= index:
                raise ValueError(f"步骤 {index} 的依赖 {dep} 必须指向更早的步骤")
    return by_id


def ready_steps(plan, results):
    """哪些步骤现在可以跑:没跑过,且所有依赖都已成功。"""
    out = []
    for i, step in enumerate(plan):
        if i in results:
            continue
        deps = step.get("depends_on", [])
        if all(results.get(d, {}).get("status") == "succeeded" for d in deps):
            out.append(i)
    return out


def blocked_steps(plan, results):
    """上游失败 -> 下游直接标失败,不带空数据执行。"""
    out = []
    for i, step in enumerate(plan):
        if i in results:
            continue
        for d in step.get("depends_on", []):
            if results.get(d, {}).get("status") == "failed":
                out.append((i, d))
                break
    return out


def dependency_input(step, results):
    """把上游输出传给下游 —— 指标步骤从这里拿真实 instance_ids。"""
    merged = {}
    for d in step.get("depends_on", []):
        merged.update(results[d].get("data", {}))
    return merged


class Budget:
    """总期限 + 单次期限。每步按剩余预算缩短,不是每步重新计时。"""

    def __init__(self, total=120, per_call=30):
        self.deadline = time.time() + total
        self.per_call = per_call

    def remaining(self):
        return self.deadline - time.time()

    def call_timeout(self):
        left = self.remaining()
        if left <= 0:
            raise TimeoutError("任务超出总期限")
        return min(self.per_call, left)
