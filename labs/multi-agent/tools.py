"""工具层:离线用固定数据,--live 时走真实 AWS 只读 API。

真正部署时这些函数应该放进 Gateway 的 Lambda target(第 3 章),
由专家 Runtime 通过 MCP 调用。这里为了能本地跑直接实现。
"""
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

LIVE = os.environ.get("LAB_LIVE") == "1"
REGION = os.environ.get("LAB_REGION", "cn-northwest-1")
SHANGHAI = ZoneInfo("Asia/Shanghai")


def today_window():
    """北京时间今天 00:00 到现在,转成 UTC。拿 UTC 当天当北京当天会差 8 小时。"""
    now_local = datetime.now(SHANGHAI)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_local.astimezone(ZoneInfo("UTC")), now_local.astimezone(ZoneInfo("UTC"))


def ec2_describe_running(region=REGION, **_):
    if not LIVE:
        return {"instance_ids": ["demo-instance-a", "demo-instance-b"], "synthetic": True}
    import boto3
    client = boto3.Session(region_name=region).client("ec2")
    ids = []
    for page in client.get_paginator("describe_instances").paginate(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    ):
        for reservation in page["Reservations"]:
            ids.extend(i["InstanceId"] for i in reservation["Instances"])
    return {"instance_ids": ids, "region": region}


def cloudwatch_cpu(region=REGION, instance_ids=None, **_):
    instance_ids = instance_ids or []
    if not instance_ids:
        # 空列表不是错误,是"没有资源可查" —— 要和查询失败区分开
        return {"per_instance_metrics": {}, "note": "上游未发现运行中实例"}
    if not LIVE:
        return {"per_instance_metrics": {
            i: {"average": 12.5, "maximum": 40.0, "unit": "Percent", "synthetic": True}
            for i in instance_ids
        }}
    import boto3
    start, end = today_window()
    client = boto3.Session(region_name=region).client("cloudwatch")
    out = {}
    for instance_id in instance_ids:
        r = client.get_metric_statistics(
            Namespace="AWS/EC2", MetricName="CPUUtilization",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=start, EndTime=end, Period=300,
            Statistics=["Average", "Maximum"],
        )
        points = r.get("Datapoints", [])
        if not points:
            # 空数据不等于 CPU 是 0
            out[instance_id] = {"datapoints": 0, "note": "该时间窗无数据点"}
            continue
        out[instance_id] = {
            "datapoints": len(points),
            "average": round(sum(p["Average"] for p in points) / len(points), 2),
            "maximum": round(max(p["Maximum"] for p in points), 2),
            "unit": points[0]["Unit"],
        }
    return {"per_instance_metrics": out}


def cloudtrail_stop_events(region=REGION, **_):
    if not LIVE:
        return {"audit_evidence": [{
            "event": "StopInstances", "instance_ids": ["demo-instance-a"],
            "time": "2026-01-01T02:00:00+08:00", "synthetic": True,
        }]}
    import boto3
    start, end = today_window()
    client = boto3.Session(region_name=region).client("cloudtrail")
    events = []
    for page in client.get_paginator("lookup_events").paginate(
        LookupAttributes=[{"AttributeKey": "EventName", "AttributeValue": "StopInstances"}],
        StartTime=start, EndTime=end,
    ):
        for e in page["Events"]:
            detail = json.loads(e["CloudTrailEvent"])
            # 实例 ID 在事件详情里,Resources 字段不一定有
            items = detail.get("requestParameters", {}).get("instancesSet", {}).get("items", [])
            events.append({
                "event": e["EventName"],
                "time": e["EventTime"].isoformat(),
                "instance_ids": [i.get("instanceId") for i in items],
            })
    return {"audit_evidence": events, "window": [start.isoformat(), end.isoformat()]}


REGISTRY = {
    "ec2_describe_running": ec2_describe_running,
    "cloudwatch_cpu": cloudwatch_cpu,
    "cloudtrail_stop_events": cloudtrail_stop_events,
}
