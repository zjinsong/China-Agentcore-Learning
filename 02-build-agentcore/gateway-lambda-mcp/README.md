# 3.2 Runtime → Gateway → Lambda MCP

目标：从刚部署的 Runtime 发出 `check gateway`，通过 Gateway 调用 `get_learning_status`，拿到 Lambda 的成功结果。完成 [3.1 Runtime](../../01-quickstart/first-runtime/README.md) 后继续，命令从仓库根目录执行。

```text
调用者 -- boto3/IAM --> Runtime
Runtime execution role -- SigV4 / InvokeGateway --> Gateway
Gateway service role -- InvokeFunction --> Lambda
Lambda execution role --> 自己的日志（本工具不访问业务数据）
```

## 步骤 1：定义 Lambda 行为

Lambda 是具体工具代码。本实验不要求创建常驻 MCP 服务：Gateway 根据工具 schema 把 MCP 请求转换为 Lambda 调用。

```python
def handler(event, context):
    return {
        "status": "ok",
        "message": "Gateway-to-Lambda learning target is reachable"
    }
```

本工具无输入，也不读取真实账户资源，方便验证接入链路。部署时配置 `handler.handler`、Python 3.12、30 秒 Lambda 超时。Lambda 角色只写自己的日志；这个 30 秒不是整个 Agent 任务的总期限。

## 步骤 2：定义工具 schema

```json
{
  "name": "get_learning_status",
  "description": "Check Gateway to Lambda connectivity",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

schema 告诉调用方工具的名字、用途和输入。新增业务工具时，输入参数必须和 Lambda 实际处理一致，且在 Lambda 侧再次校验。

## 步骤 3：创建 Lambda、Gateway 和 target

```powershell
python 02-build-agentcore/gateway-lambda-mcp/deploy_gateway.py
```

辅助脚本按顺序创建 Lambda role、日志组、函数、Gateway role、Gateway、target，并分别等待 READY。它从 `.local/runtime.json` 读取区域，把结果存入 `.local/gateway.json`。固定资源名均以 learning 标记；遇到冲突不会覆盖。

**先创建 Gateway role**，信任 `bedrock-agentcore.amazonaws.com`，限制本账户/区域；给它以下权限，Resource 仅为新 Lambda：

```python
{
    "Effect": "Allow",
    "Action": "lambda:InvokeFunction",
    "Resource": lambda_arn
}
```

这是同账户 Lambda target，Gateway role 的身份策略足以提供调用权限；跨账户还需 Lambda 资源策略。它和 Lambda 查询业务 API 的执行角色是两回事。[Gateway 角色说明](https://docs.amazonaws.cn/en_us/bedrock-agentcore/latest/devguide/gateway-prerequisites-permissions.html)

**创建 AWS_IAM Gateway**：

```python
gateway = control.create_gateway(
    name="learning-gateway",
    roleArn=gateway_role_arn,
    protocolType="MCP",
    authorizerType="AWS_IAM",
)
```

中国区必须使用 AWS_IAM 或 CUSTOM_JWT；入门采用 IAM，省去企业 IdP 配置。代码不启用语义搜索，正常 tools/list 和 tools/call 可用。返回 URL 直接取 `gatewayUrl`，不要手工猜测服务域名。

**创建 Lambda target**：

```python
target = control.create_gateway_target(
    gatewayIdentifier=gateway["gatewayId"],
    name="learning-status",
    targetConfiguration={
        "mcp": {"lambda": {
            "lambdaArn": lambda_arn,
            "toolSchema": {"inlinePayload": [tool_schema]}
        }}
    },
    credentialProviderConfigurations=[
        {"credentialProviderType": "GATEWAY_IAM_ROLE"}
    ],
)
```

`GATEWAY_IAM_ROLE` 表示 Gateway 用自己的服务角色调用这个 target，和入站 AWS_IAM 分开配置。[Lambda target API](https://docs.amazonaws.cn/en_us/bedrock-agentcore/latest/devguide/gateway-add-target-api-target-config.html)

脚本创建后把 Gateway role 的信任条件收紧到新 Gateway ARN。状态 READY 是资源建立完成，工具调用还需下一步。

## 步骤 4：让 Runtime 有权调用 Gateway

```powershell
python 01-quickstart/first-runtime/deploy_runtime.py connect
```

命令为 **Runtime execution role** 追加限定该 Gateway 的策略：

```python
{
    "Effect": "Allow",
    "Action": "bedrock-agentcore:InvokeGateway",
    "Resource": gateway_arn
}
```

同时更新 Runtime 环境变量：`GATEWAY_URL` 为服务返回 URL，`TOOL_REGION` 为目标中国区。更新需要等待 READY。[入站 IAM 权限](https://docs.amazonaws.cn/en_us/bedrock-agentcore/latest/devguide/gateway-inbound-auth.html)

## 步骤 5：理解 tools/list 和 tools/call

应用发 JSON-RPC 请求；签名的关键代码如下：

```python
request = AWSRequest(method="POST", url=gateway_url, data=body, headers=headers)
credentials = session.get_credentials().get_frozen_credentials()
SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(request)
response = requests.post(gateway_url, data=body, headers=dict(request.headers), timeout=(5, 30))
```

凭证来自 Runtime 角色，不写密钥。签名后请求体必须保持不变；使用临时凭证时 botocore 一并设置 session token。

先 MCP initialize、发送 initialized 通知，再列举工具：

```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
```

工具名取返回值；本例通常是 `learning-status___get_learning_status`。然后调用：

```json
{
  "jsonrpc":"2.0",
  "id":3,
  "method":"tools/call",
  "params":{"name":"learning-status___get_learning_status","arguments":{}}
}
```

辅助客户端处理 initialize、服务返回的会话头、工具分页、JSON / 有限 SSE 响应和工具错误。生产应用用成熟 MCP SDK 管理流式连接；本实验只演示这个简单查询。

## 步骤 6：从真实 Runtime 验证整条链路

```powershell
python 01-quickstart/first-runtime/deploy_runtime.py invoke --prompt "check gateway"
```

默认创建新 session，避开旧运行环境继续使用更新前配置。应用实际会列举工具，选择 `get_learning_status`，调用它并返回 `tool_result`。

预期结构示意，服务包装可能略有差异：

```json
{
  "status": "ok",
  "tool_result": {
    "content": [{"type":"text","text":"{\"status\":\"ok\",\"message\":\"Gateway-to-Lambda learning target is reachable\"}"}]
  }
}
```

外层 Runtime 成功、内层 Lambda `status: ok` 同时出现，才证明完整调用成功。日志应能看到 Lambda 被调用；不要仅凭资源状态下结论。

## 排错顺序

| 错误 | 查哪一层 |
| --- | --- |
| Runtime 返回 not_configured | connect 是否完成、新 session 是否用了新版本 |
| Gateway 403 | Runtime role InvokeGateway、SigV4 区域/服务、临时凭证 |
| 找不到工具 | target READY、tools/list 分页、实际名字与 schema |
| target 调用失败 | Gateway role InvokeFunction、Lambda 状态、函数日志 |
| MCP isError | 工具执行失败；不能作为成功数据汇总 |
| 工具超时 | Lambda 日志、函数期限与客户端期限；再核对任务总预算 |

## 代码参考

[Lambda](handler.py)、[创建 Gateway 和 target](deploy_gateway.py)、[Runtime 内签名客户端](../../01-quickstart/first-runtime/gateway_client.py)、[Runtime 接入与调用](../../01-quickstart/first-runtime/deploy_runtime.py)。

下一步：[清理实验资源](../cleanup.md)，再读 [4. Harness](../../04-harness/README.md)。
