"""Supervisor:规划 → harness 校验 → 按 DAG 调专家 → 汇总证据。

规划器默认是确定性的关键词匹配(不调模型,便于理解和复跑)。
真实项目里把 plan() 换成 LLM 输出 JSON 计划即可 —— 后面的校验和执行不用改,
因为 harness 只接受符合能力目录的计划。
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import harness


def plan(question, capabilities):
    """生成计划。换成 LLM 时只要输出同样结构的 JSON。"""
    ids = {c["id"] for c in capabilities}
    steps = []
    wants_metrics = any(k in question for k in ("性能", "指标", "CPU", "cpu"))
    wants_audit = any(k in question for k in ("关机", "停止", "审计", "Stop"))

    if wants_metrics and {"discover_running_ec2", "query_ec2_metrics"} <= ids:
        steps.append({"agent": "monitoring", "capability": "discover_running_ec2",
                      "depends_on": [], "prompt": "枚举运行中的 EC2"})
        steps.append({"agent": "monitoring", "capability": "query_ec2_metrics",
                      "depends_on": [0], "prompt": "按上游返回的实例 ID 查询 CPU"})
    if wants_audit and "query_stop_events" in ids:
        steps.append({"agent": "cloudtrail", "capability": "query_stop_events",
                      "depends_on": [], "prompt": "查询今天的 StopInstances"})
    return steps


def call_expert(step, cap, dependency_input, timeout):
    """A2A 调用:JSON-RPC 2.0 发到专家根路径。"""
    body = json.dumps({
        "jsonrpc": "2.0",
        "id": f"{step['agent']}-{cap['id']}",
        "method": "message/send",
        "params": {"message": {
            "contextId": "lab-conversation",
            "parts": [{"kind": "text", "text": step["prompt"]}],
            "metadata": {
                "capability": cap["id"],
                "region": harness.CATALOG["region"],
                "dependency_input": dependency_input,
            },
        }},
    }).encode("utf-8")

    request = urllib.request.Request(
        f"http://127.0.0.1:{cap['port']}/",
        data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        message = json.loads(response.read())
    if "error" in message:
        raise RuntimeError(message["error"]["message"])
    return message["result"]


def run(question):
    capabilities = harness.available_capabilities()
    steps = plan(question, capabilities)
    if not steps:
        return {"answer": "没有匹配的能力,未启动专家。", "tasks": []}

    by_id = harness.validate(steps, capabilities)
    budget = harness.Budget(total=120, per_call=30)
    results = {}

    print(f"计划({len(steps)} 步):")
    for i, s in enumerate(steps):
        dep = f" 依赖{s['depends_on']}" if s["depends_on"] else " 可并行"
        print(f"  {i}. {s['agent']}/{s['capability']}{dep}")

    while len(results) < len(steps):
        for index, upstream in harness.blocked_steps(steps, results):
            results[index] = {"status": "failed",
                              "expert": steps[index]["agent"],
                              "capability": steps[index]["capability"],
                              "error": f"上游步骤 {upstream} 失败,未执行"}
            print(f"  ✗ 步骤{index} 跳过(上游失败)")

        batch = harness.ready_steps(steps, results)
        if not batch:
            break

        print(f"\n并行执行: {[f'步骤{i}' for i in batch]}")
        with ThreadPoolExecutor(max_workers=len(batch)) as pool:
            futures = {}
            for index in batch:
                step = steps[index]
                futures[pool.submit(
                    call_expert, step, by_id[step["capability"]],
                    harness.dependency_input(step, results), budget.call_timeout(),
                )] = index
            for future, index in futures.items():
                try:
                    results[index] = {"status": "succeeded", **future.result()}
                    print(f"  ✓ 步骤{index} {steps[index]['capability']}")
                except (urllib.error.URLError, RuntimeError, TimeoutError, OSError) as error:
                    results[index] = {"status": "failed", "error": str(error),
                                      "capability": steps[index]["capability"],
                                      "expert": steps[index]["agent"]}
                    print(f"  ✗ 步骤{index} {steps[index]['capability']}: {error}")

    return {"answer": summarize(question, steps, results), "tasks": results}


def summarize(question, steps, results):
    """汇总必须区分:真实数据 / 空数据 / 工具错误。"""
    done = [r for r in results.values() if r["status"] == "succeeded"]
    failed = [r for r in results.values() if r["status"] == "failed"]
    lines = [f"问题:{question}", f"子任务:{len(done)} 成功 / {len(failed)} 失败"]

    for index, step in enumerate(steps):
        r = results.get(index, {})
        if r.get("status") != "succeeded":
            continue
        data = r.get("data", {})
        if "instance_ids" in data:
            ids = data["instance_ids"]
            lines.append(f"- 发现 {len(ids)} 台运行中实例" if ids else "- 未发现运行中实例")
        if "per_instance_metrics" in data:
            metrics = data["per_instance_metrics"]
            if not metrics:
                lines.append(f"- 无指标可查({data.get('note', '')})")
            for instance_id, m in metrics.items():
                if m.get("datapoints") == 0:
                    lines.append(f"- {instance_id}: 该时间窗无数据点(不等于 CPU 为 0)")
                else:
                    lines.append(f"- {instance_id}: 平均 {m.get('average')}% 最高 {m.get('maximum')}%")
        if "audit_evidence" in data:
            events = data["audit_evidence"]
            lines.append(f"- 审计:{len(events)} 条 StopInstances" if events
                         else "- 审计:该时间窗无 StopInstances 记录")

    for r in failed:
        lines.append(f"- {r.get('expert', '?')}/{r.get('capability', '?')} 查询失败:"
                     f"{r.get('error')} —— 该结论无法得出,不能当作'没有事件'")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?",
                        default="查宁夏运行中 EC2 的性能指标,并检查今天有没有关机操作")
    parser.add_argument("--json", action="store_true", help="输出完整任务记录")
    args = parser.parse_args()

    outcome = run(args.question)
    print("\n" + "=" * 60)
    print(outcome["answer"])
    if args.json:
        print("\n完整记录:")
        print(json.dumps(outcome["tasks"], ensure_ascii=False, indent=2))
    sys.exit(0)
