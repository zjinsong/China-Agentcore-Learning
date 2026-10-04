# 3.1 部署第一个 Runtime

目标：在宁夏创建 `learning_runtime`，实际调用后返回 `Received: hello`。这个实验先验证托管应用链路，不依赖模型或真实业务数据。前置条件见 [部署指南](../../02-build-agentcore/README.md)。以下命令都从仓库根目录运行。

## 步骤 1：理解应用入口

应用入口如下：

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp
app = BedrockAgentCoreApp()

@app.entrypoint
def handler(event, context):
    return {"answer": "Received: " + str(event.get("prompt", ""))}

if __name__ == "__main__":
    app.run()
```

`BedrockAgentCoreApp` 提供协议入口，装饰器把函数注册为请求处理器，`app.run()` 启动服务。

HTTP 容器需监听 `0.0.0.0:8080`，提供 `/invocations` 和 `/ping`，部署镜像为 ARM64。[HTTP 协议要求](https://docs.amazonaws.cn/en_us/bedrock-agentcore/latest/devguide/runtime-http-protocol-contract.html)

## 步骤 2：本地运行与验证

```powershell
python -m pip install -r 01-quickstart/first-runtime/requirements.txt
python 01-quickstart/first-runtime/app.py
```

保留服务终端，在第二个终端执行：

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8080/ping
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8080/invocations -ContentType application/json -Body '{"prompt":"hello"}'
```

预期健康检查成功，调用结果包含：

```json
{"answer":"Received: hello","mode":"learning-example"}
```

如果这一步失败，先查依赖、8080 端口与应用异常；此时不需要排查 IAM。测试后可 Ctrl+C 停止本地服务。

## 步骤 3：准备中国区 ECR 和 Runtime 角色

```powershell
python 01-quickstart/first-runtime/deploy_runtime.py prepare --region cn-northwest-1
```

命令创建私有 ECR `agentcore-learning-runtime` 和 `learning-runtime-role`。真实 URI、角色 ARN 写入 `.local/runtime.json`。角色信任 AgentCore 服务，仅允许本账户、本区域的学习 Runtime；执行权限只包含拉取本仓库镜像和 Runtime 日志。

信任关系的核心结构是：

```python
{
    "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {
        "StringEquals": {"aws:SourceAccount": account},
        "ArnLike": {"aws:SourceArn": f"arn:aws-cn:bedrock-agentcore:{region}:{account}:runtime/learning_runtime-*"}
    }
}
```

`account` 在本地通过 STS 获得，不在仓库写真实值。服务 Principal 不凭域名后缀猜测，按服务文档要求使用；资源 ARN 使用中国区 `aws-cn`。

## 步骤 4：构建 ARM64 镜像并推送

本实验 Dockerfile：

```dockerfile
FROM public.ecr.aws/docker/library/python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py gateway_client.py ./
EXPOSE 8080
CMD ["python", "app.py"]
```

在 PowerShell 读取本地准备结果并登录中国区 ECR：

```powershell
$lab = Get-Content .local/runtime.json -Raw | ConvertFrom-Json
$labRegistry = $lab.repository_uri.Split('/')[0]
aws ecr get-login-password --region $lab.region | docker login --username AWS --password-stdin $labRegistry
```

预期 `Login Succeeded`。然后构建并推送：

```powershell
docker buildx build --platform linux/arm64 --provenance=false --load -t agentcore-learning-runtime:v1 01-quickstart/first-runtime
docker image inspect agentcore-learning-runtime:v1 --format '{{.Architecture}}'
docker tag agentcore-learning-runtime:v1 "$($lab.repository_uri):v1"
docker push "$($lab.repository_uri):v1"
```

架构应为 `arm64`，推送成功应显示镜像 digest。基础镜像是公开镜像来源；最终应用镜像必须上传自己的中国区 ECR。公网拉取受限时替换已批准的可访问基础镜像。

## 步骤 5：创建 Runtime，等待 READY

```powershell
python 01-quickstart/first-runtime/deploy_runtime.py create
```

创建脚本真正提交的关键参数：

```python
client = boto3.Session(region_name=region).client("bedrock-agentcore-control")
result = client.create_agent_runtime(
    agentRuntimeName="learning_runtime",
    agentRuntimeArtifact={"containerConfiguration": {"containerUri": image_uri}},
    roleArn=runtime_role_arn,
    networkConfiguration={"networkMode": "PUBLIC"},
    protocolConfiguration={"serverProtocol": "HTTP"},
)
```

`image_uri` 是步骤 4 推送的 `:v1` URI，`runtime_role_arn` 来自步骤 3。这里使用中国区 MicroVM 默认部署，不配置 Global Managed EC2 容量提供方，不创建 Cognito。

脚本保存 Runtime ID/ARN，再轮询状态。创建请求成功只是受理，**READY 后还要做真实调用**。IAM 传播延迟可能导致刚创建的角色暂时不可用，遇到失败先检查服务状态与错误，不覆盖原资源。

```powershell
python 01-quickstart/first-runtime/deploy_runtime.py status
```

API 参考：[create_agent_runtime](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agentcore-control/client/create_agent_runtime.html)。

## 步骤 6：IAM 调用真实 Runtime

```powershell
python 01-quickstart/first-runtime/deploy_runtime.py invoke --prompt hello
```

调用核心：

```python
client = session.client("bedrock-agentcore")
response = client.invoke_agent_runtime(
    agentRuntimeArn=runtime_arn,
    qualifier="DEFAULT",
    runtimeSessionId=str(uuid.uuid4()),
    payload=json.dumps({"prompt": "hello"}).encode("utf-8"),
)
print(response["response"].read().decode("utf-8"))
```

boto3 用当前调用者凭证自动签名；调用者需要 InvokeAgentRuntime 权限，资源范围覆盖本实验 Runtime 及实际 endpoint。UUID 字符串为 36 个字符，满足 session ID 至少 33 字符要求。相同 session 可复用运行环境；验证新版本用新 session。

返回应包含 `Received: hello`。这是部署通过的依据，不把官方示例耗时当作你的实测延迟。[Invoke API](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agentcore/client/invoke_agent_runtime.html)

## 常见失败

| 现象 | 优先检查 |
| --- | --- |
| 本地无法启动 | Python 依赖、端口和应用异常 |
| Docker 构建失败 | 基础镜像与 PyPI 网络、buildx ARM64 支持 |
| 创建时镜像拉取失败 | 中国区 ECR 地址、镜像 tag、角色 ECR 权限 |
| Permission / PassRole 错误 | 部署者权限与角色信任、SCP / 权限边界 |
| READY 但 Invoke 403 | 调用者的 InvokeAgentRuntime 权限；不修改 Lambda 角色 |
| 调用异常或超时 | Runtime 日志中的启动/应用错误、网络、客户端期限 |

## 代码参考与下一步

正文已经展开操作。文件供复用与查看完整实现：[应用](app.py)、[依赖](requirements.txt)、[Dockerfile](Dockerfile)、[部署与调用辅助](deploy_runtime.py)。

下一步：[3.2 Gateway 和 Lambda 工具](../../02-build-agentcore/gateway-lambda-mcp/README.md)。
