# 3. 构建指南:Runtime → Gateway → Lambda

跑通两件事:

```text
① 本机 hello 应用 → 中国区 ECR → Runtime → 真实调用返回 hello
② Runtime → AWS_IAM Gateway → Lambda → 返回 status: ok
```

所有命令从仓库根目录执行。

## 3.0 准备

```bash
export AWS_PROFILE=china-learning
export AWS_REGION=cn-northwest-1
export AWS_DEFAULT_REGION=cn-northwest-1
aws sts get-caller-identity

python3 -m pip install -U boto3 bedrock-agentcore requests
```

四个角色各管一段,互不传递:

| 身份 | 干什么 | 需要的权限 |
| --- | --- | --- |
| 你的部署身份 | 创建和验证资源 | 建 ECR/IAM/Runtime/Gateway/Lambda + `iam:PassRole` + `bedrock-agentcore:InvokeAgentRuntime` |
| Runtime 执行角色 | 拉镜像、写日志、调 Gateway | 拉指定 ECR、写日志;②里加调 Gateway |
| Gateway 服务角色 | Gateway 调 target | `lambda:InvokeFunction` 指定函数 |
| Lambda 执行角色 | 工具代码访问 AWS | 写自己日志;业务只读权限 |

## 3.1 应用入口

`03-build/app.py` 的核心:

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def handler(event, context):
    prompt = str(event.get("prompt", ""))[:500]
    if prompt == "check gateway":
        ...                                  # 3.9 验证 Gateway 时走这条分支
    return {"answer": f"Received: {prompt}", "mode": "learning-example"}

if __name__ == "__main__":
    app.run()
```

- `BedrockAgentCoreApp()` 提供协议入口
- `@app.entrypoint` 注册请求处理函数
- `app.run()` 启动服务,自动监听 8080 并提供 `/invocations` 和 `/ping`

HTTP 协议要求:监听 `0.0.0.0:8080`,提供 `/invocations` 和 `/ping`,镜像 **arm64**。

## 3.2 本地验证

```bash
python3 -m pip install -r 03-build/requirements.txt
python3 03-build/app.py
```

另开一个终端:

```bash
curl http://127.0.0.1:8080/ping
curl -X POST http://127.0.0.1:8080/invocations \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"hello"}'
```

预期:

```json
{"answer":"Received: hello","mode":"learning-example"}
```

失败先查依赖、8080 端口占用、应用报错。这一步跟 IAM 无关。`Ctrl+C` 停掉。

## 3.3 建 ECR 和 Runtime 角色

```bash
python3 03-build/deploy_runtime.py prepare
```

创建 ECR 仓库 `agentcore-learning-runtime` 和角色 `learning-runtime-role`,结果写入 `.local/runtime.json`。

角色信任关系的关键部分:

```python
{
    "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {
        "StringEquals": {"aws:SourceAccount": account},
        "ArnLike": {"aws:SourceArn":
            f"arn:aws-cn:bedrock-agentcore:{region}:{account}:runtime/learning_runtime-*"}
    }
}
```

中国区 ARN 用 `aws-cn` 分区。`account` 从 STS 本地取,不写进仓库。

## 3.4 构建 arm64 镜像推 ECR

Dockerfile:

```dockerfile
FROM public.ecr.aws/docker/library/python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py gateway_client.py ./
EXPOSE 8080
CMD ["python", "app.py"]
```

登录 ECR 并构建:

```bash
REPO=$(python3 -c "import json;print(json.load(open('.local/runtime.json'))['repository_uri'])")
REGISTRY=${REPO%%/*}

aws ecr get-login-password | docker login --username AWS --password-stdin "$REGISTRY"

docker buildx build --platform linux/arm64 --provenance=false --load \
  -t agentcore-learning-runtime:v1 03-build

docker image inspect agentcore-learning-runtime:v1 --format '{{.Architecture}}'   # 应为 arm64
docker tag agentcore-learning-runtime:v1 "$REPO:v1"
docker push "$REPO:v1"
```

x86 机器上构建 arm64 需要 QEMU,**会比较慢**。先装一次模拟器:

```bash
docker run --privileged --rm tonistiigi/binfmt --install arm64
```

构建时间长的话放后台:

```bash
nohup docker buildx build --platform linux/arm64 --provenance=false --load \
  -t agentcore-learning-runtime:v1 03-build > /tmp/build.log 2>&1 &

# 轮询查看进度
tail -5 /tmp/build.log
```

## 3.5 创建 Runtime

```bash
python3 03-build/deploy_runtime.py create
```

实际提交的参数:

```python
client = boto3.Session(region_name=region).client("bedrock-agentcore-control")
client.create_agent_runtime(
    agentRuntimeName="learning_runtime",
    agentRuntimeArtifact={"containerConfiguration": {"containerUri": image_uri}},
    roleArn=runtime_role_arn,
    networkConfiguration={"networkMode": "PUBLIC"},
    protocolConfiguration={"serverProtocol": "HTTP"},
)
```

查状态:

```bash
python3 03-build/deploy_runtime.py status
```

创建成功只是受理,**READY 之后必须真实调用一次**。IAM 传播有延迟,刚建的角色可能短时不可用,失败先看错误再重试,别覆盖资源。

## 3.6 真实调用

```bash
python3 03-build/deploy_runtime.py invoke --prompt hello
```

调用核心:

```python
client = session.client("bedrock-agentcore")
response = client.invoke_agent_runtime(
    agentRuntimeArn=runtime_arn,
    qualifier="DEFAULT",
    runtimeSessionId=str(uuid.uuid4()),      # 至少 33 字符,UUID 是 36
    payload=json.dumps({"prompt": "hello"}).encode("utf-8"),
)
print(response["response"].read().decode("utf-8"))
```

返回包含 `Received: hello` 就是通了。boto3 自动 SigV4 签名,调用者需要 `InvokeAgentRuntime` 权限。同一 session 复用运行环境,验证新版本要换新 session。

## 3.7 Lambda 工具

`03-build/gateway-lambda/handler.py`:

```python
def handler(event, context):
    return {"status": "ok", "message": "learning tool reached"}
```

工具 schema(告诉 Gateway 这个工具叫什么、收什么参数):

```json
{
  "name": "get_learning_status",
  "description": "Check Gateway to Lambda connectivity",
  "inputSchema": {"type": "object", "properties": {}, "required": []}
}
```

## 3.8 建 Lambda + Gateway + target

一条命令做完三件事:建 Lambda(含角色)、建 Gateway、注册 target。

```bash
python3 03-build/gateway-lambda/deploy_gateway.py
```

关键参数:

```python
control.create_gateway(
    name="learning-gateway",
    roleArn=gateway_role,
    protocolType="MCP",
    authorizerType="AWS_IAM",        # 中国区只能 AWS_IAM 或 CUSTOM_JWT
)

control.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name="learning-status",
    targetConfiguration={"mcp": {"lambda": {
        "lambdaArn": lambda_arn,
        "toolSchema": {"inlinePayload": [tool_schema]},
    }}},
    credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}],
)
```

Gateway 里的工具名会带 target 前缀:`learning-status___get_learning_status`。

结果写入 `.local/gateway.json`。脚本发现已有状态文件会停下,不重复创建。

## 3.9 验证 Gateway

先直接测工具:

```bash
python3 03-build/gateway-lambda/deploy_gateway.py test
```

它用 SigV4 签名请求 Gateway 的 `/mcp`,依次做 `initialize` → `tools/list` → `tools/call`。预期看到工具名和 `status: ok`。

再让 Runtime 走完整链路。先授权并把 Gateway 地址注入 Runtime:

```bash
python3 03-build/deploy_runtime.py connect
```

这一步做三件事:给 Runtime 角色加 `InvokeGateway` 权限、把 `GATEWAY_URL` 写进环境变量、更新 Runtime 版本。

然后**用新 session** 调用:

```bash
python3 03-build/deploy_runtime.py invoke --prompt "check gateway"
```

**只创建 Gateway 不算完成**,要看到 Lambda 真实返回。

## 3.10 接模型:从 echo 变成真 agent

到这里应用还只是 echo,不是 agent —— 它不会理解问题、不会选工具。

**AgentCore 服务独立于 LLM 模型**:它负责托管和调度,模型你自己选。海外项目一般用 Bedrock 上的 Claude/Nova;中国区 Bedrock 没有基础模型,所以用第三方 API(DeepSeek、通义千问、Kimi 等)或自部署模型。它们基本都提供 **OpenAI 兼容接口**,所以配置方式统一:**三个值 —— `base_url` + `api_key` + `model_id`**。

下面以 **DeepSeek** 为例,换别的模型只改这三个值。

### 第一步:准备三个值

```bash
export MODEL_BASE_URL="https://api.deepseek.com/v1"
export MODEL_ID="deepseek-chat"
export MODEL_API_KEY="sk-xxxxxxxx"        # 在 DeepSeek 控制台申请
```

换通义千问就是:

```bash
export MODEL_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export MODEL_ID="qwen-plus"
export MODEL_API_KEY="sk-xxxxxxxx"
```

### 第二步:注入 Runtime

API Key 不进代码、不进镜像、不进 Git。创建/更新 Runtime 时用环境变量传:

```python
client.create_agent_runtime(
    agentRuntimeName="learning_runtime",
    # ... 其余参数同 3.5
    environmentVariables={
        "MODEL_BASE_URL": os.environ["MODEL_BASE_URL"],
        "MODEL_ID": os.environ["MODEL_ID"],
        "MODEL_API_KEY": os.environ["MODEL_API_KEY"],
    },
)
```

生产环境把 Key 放 Secrets Manager,Runtime 启动时用执行角色取(角色加 `secretsmanager:GetSecretValue`),环境变量里只放 secret 名字。

### 第三步:代码里读

[Strands Agents](https://github.com/strands-agents/sdk-python) 是 AWS 开源的 agent 框架,支持 OpenAI 兼容端点:

```python
import os
from strands import Agent
from strands.models.openai import OpenAIModel

model = OpenAIModel(
    client_args={
        "api_key": os.environ["MODEL_API_KEY"],
        "base_url": os.environ["MODEL_BASE_URL"],      # DeepSeek: https://api.deepseek.com/v1
    },
    model_id=os.environ["MODEL_ID"],                   # DeepSeek: deepseek-chat
    params={"temperature": 0.3, "max_tokens": 4096},
)

agent = Agent(model=model, system_prompt="你是一个助手,只根据工具返回的真实数据回答。")
```

在 `@app.entrypoint` 里调它:

```python
@app.entrypoint
def handler(event, context):
    result = agent(str(event.get("prompt", "")))
    return {"answer": str(result)}
```

依赖加一行:

```text
strands-agents
bedrock-agentcore
```

### 第四步:把工具给模型

Gateway 的 MCP 工具转成 Strands 的 `@tool`,模型即可调用:

```python
from strands import tool

@tool
def get_learning_status() -> str:
    """检查 Gateway 到 Lambda 的连通性。"""
    return gateway_client.call("learning-status___get_learning_status", {})
```

函数名、类型标注和 docstring 就是模型看到的工具说明 —— 写清楚它才会用对。

### V2 注意

模型客户端可以放模块级(只是配置,懒连接),**但不要在模块级做实际调用或取临时凭证** —— 那会被快照捕获并共享(见 [1.5](01-china-region.md#15-runtime-版本v1-和-v2))。

### 验证

```bash
python3 03-build/deploy_runtime.py invoke --prompt "check gateway"
```

模型应当**调用工具获取真实数据**后再回答,而非凭记忆编造。若模型未调用工具直接作答,检查工具 docstring 是否清晰、system prompt 是否要求"仅依据工具数据回答"。

第 4 章用一个完整的例子把"模型 + 工具"串起来 —— 一个能查天气的 agent。

## 3.11 常见失败

| 现象 | 先查 |
| --- | --- |
| 本地起不来 | Python 依赖、8080 占用、应用异常 |
| docker 构建失败 | 基础镜像和 PyPI 网络、buildx arm64 是否装了 QEMU |
| 创建时拉镜像失败 | ECR 地址、镜像 tag、角色的 ECR 权限 |
| PassRole 报错 | 部署身份权限、角色信任关系、SCP |
| READY 但 Invoke 403 | 调用者的 `InvokeAgentRuntime` 权限 |
| 调用超时 | Runtime 日志里的启动/应用错误 |
| `tools/list` 为空 | target 是否 READY、schema 格式 |
| `tools/call` 403 | Gateway 服务角色的 `lambda:InvokeFunction` |
| 模型 401/403 | `MODEL_API_KEY` 是否注入、端点和模型 id 是否匹配 |
| 模型不调用工具直接作答 | 工具 docstring 是否清晰、system prompt 是否要求仅用工具数据 |

## 清理

按顺序删(有依赖关系,先 Gateway 侧再 Runtime 侧):

```bash
python3 03-build/gateway-lambda/deploy_gateway.py cleanup   # target → gateway → lambda → 角色
python3 03-build/deploy_runtime.py cleanup                  # runtime → 角色 → ECR
```

删完确认:

```bash
aws bedrock-agentcore-control list-agent-runtimes --query 'agentRuntimes[].agentRuntimeName'
aws bedrock-agentcore-control list-gateways --query 'items[].name'
aws ecr describe-repositories --query 'repositories[].repositoryName'
aws lambda list-functions --query 'Functions[].FunctionName'
```

下一步:[4. 构建一个 agent 应用](04-agent-app.md)
