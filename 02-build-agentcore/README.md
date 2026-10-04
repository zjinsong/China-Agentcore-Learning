# 3. 部署指南：Runtime → Gateway → Lambda

本部分按顺序创建真实 AWS 中国区学习资源。先让应用返回一句话，再通过同一个 Runtime 调用一个 Lambda 工具，最后将这个工具模式用于 CloudOps。

```text
步骤 1：本机 hello 应用 → 中国区 ECR → Runtime → 返回 hello
步骤 2：Runtime → AWS_IAM Gateway → Lambda → 返回 status: ok
```

## 开始前

在仓库根目录执行。需要 Python 3.12、AWS CLI、Docker Desktop（Linux 容器及 ARM64 构建支持）、中国区 AWS 身份。Docker 镜像与 Python 包下载需要相应网络；镜像下载失败时可换成你已批准、可访问的 ARM64 Python 基础镜像。

```powershell
$env:AWS_PROFILE = "china-learning"
$env:AWS_REGION = "cn-northwest-1"
$env:AWS_DEFAULT_REGION = "cn-northwest-1"
aws sts get-caller-identity --region cn-northwest-1
python -m pip install -U boto3 bedrock-agentcore requests
```

操作者需要创建/管理本实验 ECR、IAM Role 和内联策略、Runtime、Gateway、target、Lambda、日志组，以及向服务传递实验角色的 `iam:PassRole`。调用 Runtime 另需 `bedrock-agentcore:InvokeAgentRuntime`。已有权限边界或 SCP 仍可能限制这些操作。

| 身份 | 负责什么 | 本实验权限 |
| --- | --- | --- |
| 你的部署身份 | 创建和验证实验资源 | 创建/管理对应资源、PassRole；调用实验 Runtime |
| Runtime execution role | Runtime 启动与应用访问工具 | 拉取指定 ECR、写日志；第二步追加调用指定 Gateway |
| Gateway service role | Gateway 访问 target | 调用指定 Lambda |
| Lambda execution role | 工具代码执行 | 写自己的日志；CloudOps 时再加只读业务权限 |

部署身份的权限不会自动传给 Runtime，Runtime 的权限也不会自动传给 Lambda。官方参考：[Runtime 权限](https://docs.amazonaws.cn/en_us/bedrock-agentcore/latest/devguide/runtime-permissions.html)、[Gateway 权限](https://docs.amazonaws.cn/en_us/bedrock-agentcore/latest/devguide/gateway-prerequisites-permissions.html)。

## 操作顺序

1. **[3.1 部署第一个 Runtime](../01-quickstart/first-runtime/README.md)**：代码、入口、本地请求、镜像构建、角色、创建、真实 Invoke。
2. **[3.2 接入 Gateway 和 Lambda 工具](gateway-lambda-mcp/README.md)**：Lambda、schema、Gateway、target、签名调用与端到端验证。
3. **[3.3 清理实验资源](cleanup.md)**：先删除 Gateway target，再删除 Gateway、Runtime 和工具资源。

每个章节正文包含命令与关键代码，完整文件在章节末尾。脚本不会在导入时部署；只有你明确执行部署命令才会调用云端创建 API。本次仓库验证只做本地与 SDK 参数检查，没有创建新的云资源。

实验状态在 `.local/runtime.json` 与 `.local/gateway.json`，含你自己的资源标识，不要发布。脚本使用固定学习资源名，遇到同名资源或已有状态会停止；失败后查看本地状态与控制台，不盲目重跑创建。

下一步：[3.1 第一个 Runtime](../01-quickstart/first-runtime/README.md)。

## 本次仓库检查范围

已在本地验证 Runtime `/ping`、`hello` 与未配置 Gateway 的返回；检查 Python/JSON/TOML 示例、本地文档链接，执行离线工作流成功、审计失败、上游失败场景；对部署流程的 23 次 AWS 请求做 SDK 参数模型验证，并检查外部参考链接及公开信息扫描。

这些检查未创建云资源、未验证中国区云端权限与服务行为，也未重新运行真实多 Agent 场景。读者部署后的验收依据是上述章节的实际 Invoke 和工具结果。可复跑本地检查：

```powershell
python scripts/check_learning_material.py
python scripts/check_public_safety.py
```
