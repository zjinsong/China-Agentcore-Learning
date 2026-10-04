"""Offline fixtures by default; --live performs only China-region read operations."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta, timezone
import json
from pathlib import Path


def today_window():
    local_zone = timezone(timedelta(hours=8))
    end = datetime.now(local_zone)
    start = datetime.combine(end.date(), time.min, tzinfo=local_zone)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


class Offline:
    def discover(self):
        return ["demo-instance-a", "demo-instance-b"]

    def metrics(self, instance_ids):
        return {instance: {"synthetic": True, "average_cpu_percent": cpu}
                for instance, cpu in zip(instance_ids, [8.5, 16.0])}

    def audit(self):
        return [{"synthetic": True, "event": "StopInstances", "instance_ids": ["demo-instance-a"],
                 "note": "Fictional event: instance may have been restarted afterward"}]


class Live:
    def __init__(self, region, start, end):
        import boto3
        from botocore.config import Config
        # Build clients before scheduling threads; do not share a boto3 Session across threads.
        session = boto3.Session(region_name=region)
        config = Config(connect_timeout=5, read_timeout=30, retries={"total_max_attempts": 2})
        self.ec2 = session.client("ec2", config=config)
        self.cloudwatch = session.client("cloudwatch", config=config)
        self.cloudtrail = session.client("cloudtrail", config=config)
        self.start, self.end = start, end

    def discover(self):
        instances = []
        for page in self.ec2.get_paginator("describe_instances").paginate(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]):
            for reservation in page["Reservations"]:
                instances.extend(instance["InstanceId"] for instance in reservation["Instances"])
        return instances

    def metrics(self, instance_ids):
        results = {}
        for instance in instance_ids:
            response = self.cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2", MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": instance}],
                StartTime=self.start, EndTime=self.end, Period=300,
                Statistics=["Average", "Maximum"])
            points = sorted(response.get("Datapoints", []), key=lambda point: point["Timestamp"])
            results[instance] = {"datapoints": points, "empty": not points,
                                 "note": "No datapoints is not zero CPU" if not points else "CPU only"}
        return results

    def audit(self):
        events = []
        for page in self.cloudtrail.get_paginator("lookup_events").paginate(
                LookupAttributes=[{"AttributeKey": "EventName", "AttributeValue": "StopInstances"}],
                StartTime=self.start, EndTime=self.end):
            for event in page.get("Events", []):
                detail = json.loads(event.get("CloudTrailEvent", "{}"))
                request = detail.get("requestParameters") or {}
                items = (request.get("instancesSet") or {}).get("items") or []
                events.append({"event": event.get("EventName"), "time": event.get("EventTime"),
                    "instance_ids": [item["instanceId"] for item in items if "instanceId" in item],
                    "actor_type": (detail.get("userIdentity") or {}).get("type"),
                    "api_error": detail.get("errorCode"),
                    "note": "Successful API call does not prove the instance completed shutdown"})
        return events


def capture(callback, *args):
    try:
        return {"status": "succeeded", "result": callback(*args)}
    except Exception as error:
        return {"status": "failed", "error": str(error)}


def run(backend, region, start, end):
    # Independent discovery and audit may run together; metrics consumes discovery output.
    with ThreadPoolExecutor(max_workers=2) as pool:
        discovery_future = pool.submit(capture, backend.discover)
        audit_future = pool.submit(capture, backend.audit)
        discovery = discovery_future.result()
        metrics = (capture(backend.metrics, discovery["result"]) if discovery["status"] == "succeeded"
                   else {"status": "skipped", "reason": "Resource discovery failed"})
        audit = audit_future.result()
    steps = {"discovery": discovery, "metrics": metrics, "audit": audit}
    return {"mode": "synthetic" if isinstance(backend, Offline) else "live",
            "region": region, "start_utc": start, "end_utc": end,
            "status": "succeeded" if all(step["status"] == "succeeded" for step in steps.values()) else "partial_failure",
            "steps": steps}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--region", default="cn-northwest-1", choices=["cn-northwest-1", "cn-north-1"])
    args = parser.parse_args()
    start, end = today_window()
    backend = Live(args.region, start, end) if args.live else Offline()
    result = run(backend, args.region, start, end)
    if args.live:
        root = Path(__file__).resolve().parents[2]
        local = root / ".local"
        local.mkdir(exist_ok=True)
        (local / "cloudops-mini.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print("Live results saved to ignored .local/cloudops-mini.json")
        print("Task:", result["status"])
        for name, step in result["steps"].items():
            print(name, step["status"])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
