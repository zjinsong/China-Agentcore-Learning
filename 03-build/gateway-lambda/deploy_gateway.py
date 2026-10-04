"""Create an isolated, same-account Gateway/Lambda learning lab in AWS China."""
import argparse
import io
import json
from pathlib import Path
import sys
import time
import zipfile

import boto3

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".local" / "gateway.json"
FUNCTION = "agentcore-learning-status"


def save(state):
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def wait(client, operation, params):
    for _ in range(120):
        result = getattr(client, operation)(**params)
        status = result["status"]
        print(operation, status)
        if status == "READY":
            return result
        if status in {"FAILED", "CREATE_FAILED", "UPDATE_FAILED"}:
            raise RuntimeError(str(result.get("statusReasons", status)))
        time.sleep(5)
    raise TimeoutError("Resource not READY; inspect status before retrying.")


def test(session, state):
    """List tools and call get_learning_status through the Gateway."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from gateway_client import GatewayClient
    client = GatewayClient(state["gateway_url"], state["region"])
    client.initialize()
    print("tools:", [t["name"] for t in client.list_tools()])
    print("result:", json.dumps(client.learning_status(), ensure_ascii=False))


def cleanup(session, state):
    """Delete target, gateway, lambda and roles in dependency order."""
    control, lam, iam = (session.client(s) for s in ("bedrock-agentcore-control", "lambda", "iam"))
    if state.get("target_id"):
        try:
            control.delete_gateway_target(gatewayIdentifier=state["gateway_id"], targetId=state["target_id"])
            print("Target deleted:", state["target_id"])
            time.sleep(5)
        except control.exceptions.ResourceNotFoundException:
            print("Target already gone.")
    if state.get("gateway_id"):
        try:
            control.delete_gateway(gatewayIdentifier=state["gateway_id"])
            print("Gateway deleted:", state["gateway_id"])
        except control.exceptions.ResourceNotFoundException:
            print("Gateway already gone.")
    try:
        lam.delete_function(FunctionName=FUNCTION)
        print("Lambda deleted:", FUNCTION)
    except lam.exceptions.ResourceNotFoundException:
        print("Lambda already gone.")
    for role, policies in (("learning-gateway-role", ["learning-invoke-lambda"]),
                           ("learning-lambda-role", ["learning-lambda-logs"])):
        for policy in policies:
            try:
                iam.delete_role_policy(RoleName=role, PolicyName=policy)
            except iam.exceptions.NoSuchEntityException:
                pass
        try:
            iam.delete_role(RoleName=role)
            print("Role deleted:", role)
        except iam.exceptions.NoSuchEntityException:
            print("Role already gone:", role)
    try:
        session.client("logs").delete_log_group(logGroupName=f"/aws/lambda/{FUNCTION}")
    except session.client("logs").exceptions.ResourceNotFoundException:
        pass
    if STATE.exists():
        STATE.unlink()
        print("Local state removed:", STATE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="deploy", choices=["deploy", "test", "cleanup"])
    args = parser.parse_args()
    if args.action != "deploy":
        state = json.loads(STATE.read_text(encoding="utf-8"))
        session = boto3.Session(region_name=state["region"])
        (test if args.action == "test" else cleanup)(session, state)
        return
    deploy()


def deploy():
    if STATE.exists():
        raise RuntimeError("Gateway state already exists; inspect it rather than creating duplicates.")
    runtime = json.loads((ROOT / ".local" / "runtime.json").read_text(encoding="utf-8"))
    region = runtime["region"]
    if region not in {"cn-north-1", "cn-northwest-1"}:
        raise ValueError("China region required.")
    session = boto3.Session(region_name=region)
    account = session.client("sts").get_caller_identity()["Account"]
    iam, lam, control = (session.client(s) for s in ("iam", "lambda", "bedrock-agentcore-control"))
    state = {"region": region}
    save(state)
    lambda_trust = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]}
    lambda_role = iam.create_role(RoleName="learning-lambda-role", AssumeRolePolicyDocument=json.dumps(lambda_trust))["Role"]["Arn"]
    state["lambda_role_arn"] = lambda_role
    save(state)
    iam.put_role_policy(RoleName="learning-lambda-role", PolicyName="learning-lambda-logs", PolicyDocument=json.dumps({
        "Version": "2012-10-17", "Statement": [{"Effect": "Allow",
        "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
        "Resource": f"arn:aws-cn:logs:{region}:{account}:log-group:/aws/lambda/{FUNCTION}:*"}],
    }))
    session.client("logs").create_log_group(logGroupName=f"/aws/lambda/{FUNCTION}")
    session.client("logs").put_retention_policy(logGroupName=f"/aws/lambda/{FUNCTION}", retentionInDays=7)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
        package.write(Path(__file__).with_name("handler.py"), "handler.py")
    for attempt in range(12):
        try:
            result = lam.create_function(FunctionName=FUNCTION, Runtime="python3.12", Role=lambda_role,
                Handler="handler.handler", Code={"ZipFile": archive.getvalue()}, Timeout=30, MemorySize=128)
            break
        except lam.exceptions.InvalidParameterValueException as error:
            if "cannot be assumed" not in str(error) or attempt == 11:
                raise
            time.sleep(5)
    state["lambda_arn"] = result["FunctionArn"]
    save(state)
    lam.get_waiter("function_active_v2").wait(FunctionName=FUNCTION)
    gateway_trust = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow",
        "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}, "Action": "sts:AssumeRole",
        "Condition": {"StringEquals": {"aws:SourceAccount": account},
        "ArnLike": {"aws:SourceArn": f"arn:aws-cn:bedrock-agentcore:{region}:{account}:gateway/*"}}}]}
    gateway_role = iam.create_role(RoleName="learning-gateway-role", AssumeRolePolicyDocument=json.dumps(gateway_trust))["Role"]["Arn"]
    state["gateway_role_arn"] = gateway_role
    save(state)
    iam.put_role_policy(RoleName="learning-gateway-role", PolicyName="learning-invoke-lambda", PolicyDocument=json.dumps({
        "Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "lambda:InvokeFunction", "Resource": state["lambda_arn"]}],
    }))
    time.sleep(10)  # IAM propagation; a failed create is retained for inspection.
    result = control.create_gateway(name="learning-gateway", roleArn=gateway_role,
        protocolType="MCP", authorizerType="AWS_IAM")
    state.update(gateway_id=result["gatewayId"], gateway_arn=result["gatewayArn"], gateway_url=result["gatewayUrl"])
    save(state)
    wait(control, "get_gateway", {"gatewayIdentifier": state["gateway_id"]})
    gateway_trust["Statement"][0]["Condition"]["ArnLike"]["aws:SourceArn"] = state["gateway_arn"]
    iam.update_assume_role_policy(RoleName="learning-gateway-role", PolicyDocument=json.dumps(gateway_trust))
    result = control.create_gateway_target(gatewayIdentifier=state["gateway_id"], name="learning-status",
        targetConfiguration={"mcp": {"lambda": {"lambdaArn": state["lambda_arn"],
            "toolSchema": {"inlinePayload": [{"name": "get_learning_status", "description": "Check Gateway to Lambda connectivity",
                "inputSchema": {"type": "object", "properties": {}, "required": []}}]}}}},
        credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}])
    state["target_id"] = result["targetId"]
    save(state)
    wait(control, "get_gateway_target", {"gatewayIdentifier": state["gateway_id"], "targetId": state["target_id"]})
    print("Gateway and Lambda target READY. Connect the Runtime next.")


if __name__ == "__main__":
    main()
