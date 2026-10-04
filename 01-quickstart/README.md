# 2. Vibe coding MCP 使用

把 **Amazon Bedrock AgentCore MCP Server** 接到 Kiro、Claude Code 或 Codex，让编码助手查 AgentCore 文档，协助你修改、部署和测试应用。

## 2.1 MCP 干什么

MCP 是让编码助手使用外部工具的协议。AgentCore MCP Server 提供 AgentCore 文档与开发辅助工具；实际工具以安装版本的列表为准。先调用 `search_agentcore_docs` 搜索，再调用 `fetch_agentcore_doc` 阅读详情。

官方入门展示了“改造应用 → 部署 → 测试”的对话流程。助手部署时需要通过终端或相应工具使用你的 AWS 身份；配置 MCP 本身不会创建 Runtime。[官方流程](https://docs.amazonaws.cn/en_us/bedrock-agentcore/latest/devguide/mcp-getting-started.html)

```text
开发时：你 → 编码助手 → 本地 AgentCore MCP → 文档与开发辅助
运行时：用户 → Runtime → Gateway → 业务工具
```

本章配置第一行。第三部分部署第二行。开发用 MCP 不会自动成为 CloudOps 专家的查询工具。

## 2.2 准备

安装 Python、uv 和 AWS CLI。`uvx` 随 uv 提供，启动 MCP 包；见 [uv 安装文档](https://docs.astral.sh/uv/getting-started/installation/)。

```powershell
python --version
uvx --version
aws --version
```

文档查询可先不配置部署身份。部署前按企业登录流程配置中国区 profile；下列名字只是本地别名：

```powershell
$env:AWS_PROFILE = "china-learning"
$env:AWS_REGION = "cn-northwest-1"
$env:AWS_DEFAULT_REGION = "cn-northwest-1"
aws sts get-caller-identity --region cn-northwest-1
```

应返回自己的身份，账户信息只在本地查看。profile 不存在时先完成 [CLI 配置](https://docs.amazonaws.cn/en_us/cli/latest/userguide/cli-chap-configure.html)，不要在 MCP JSON 写密钥。`@latest` 方便首次体验，验证后可锁定包版本。

## 2.3 Kiro

在项目创建 `.kiro/settings/mcp.json`，合并已有 Server：

```json
{
  "mcpServers": {
    "bedrock-agentcore-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.amazon-bedrock-agentcore-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_REGION": "cn-northwest-1",
        "AWS_DEFAULT_REGION": "cn-northwest-1"
      },
      "disabled": false,
      "autoApprove": ["search_agentcore_docs", "fetch_agentcore_doc"]
    }
  }
}
```

启动命令和工具名参照 [AWS 配置示例](https://docs.amazonaws.cn/en_us/bedrock-agentcore/latest/devguide/mcp-getting-started.html)，增加中国区环境变量。重启或重连 MCP，查看 Server 和文档工具；自动批准只包含文档读取。

GUI 可能不继承终端环境，需要 AWS 身份时在本地 `env` 加 `AWS_PROFILE`；部署终端也要核对身份。

## 2.4 Claude Code

在终端执行：

```powershell
claude mcp add --scope user --transport stdio --env FASTMCP_LOG_LEVEL=ERROR --env AWS_REGION=cn-northwest-1 --env AWS_DEFAULT_REGION=cn-northwest-1 bedrock-agentcore-mcp-server -- uvx awslabs.amazon-bedrock-agentcore-mcp-server@latest
claude mcp list
```

`--scope user` 供当前用户复用；`--` 后是 Server 启动命令。会话内输入 `/mcp` 查看连接和工具。项目共享配置使用 `.mcp.json`，不照搬 Kiro 的自动批准字段。[Claude Code 官方配置](https://code.claude.com/docs/en/mcp)

AWS 页面还描述了 standalone app 的 JSON 位置；Claude Code CLI 本教程按客户端官方 CLI 方式注册。

## 2.5 Codex

```powershell
codex mcp add bedrock-agentcore-mcp-server --env FASTMCP_LOG_LEVEL=ERROR --env AWS_REGION=cn-northwest-1 --env AWS_DEFAULT_REGION=cn-northwest-1 -- uvx awslabs.amazon-bedrock-agentcore-mcp-server@latest
codex mcp list
```

也可在 `~/.codex/config.toml` 合并：

```toml
[mcp_servers.bedrock-agentcore-mcp-server]
command = "uvx"
args = ["awslabs.amazon-bedrock-agentcore-mcp-server@latest"]
startup_timeout_sec = 60

[mcp_servers.bedrock-agentcore-mcp-server.env]
FASTMCP_LOG_LEVEL = "ERROR"
AWS_REGION = "cn-northwest-1"
AWS_DEFAULT_REGION = "cn-northwest-1"
```

重启 Codex，在 CLI 中用 `/mcp` 看活动 Server。[OpenAI MCP 配置](https://developers.openai.com/codex/mcp)

AWS 入门未明确列出 Codex，这里根据 Codex 的 stdio 接口接入同一包，以连接验证为准。

## 2.6 直接可用的对话例子

### A. 验证 MCP

```text
使用 AgentCore MCP 搜索并读取 Runtime HTTP 协议要求。
说明端口、容器架构、调用路径和健康检查路径，给出处链接。
核对 AWS 中国区差异，不创建资源。
```

成功标志：助手实际调用文档工具，回答 8080、ARM64、/invocations、/ping。只有口头回答不能证明连接成功。

### B. 改造应用并本地测试

```text
读取 01-quickstart/first-runtime/app.py，参考 MCP 文档解释
BedrockAgentCoreApp、@app.entrypoint 和 app.run()。
检查依赖和 Dockerfile，本地运行，发 hello 请求，展示实际返回。
```

成功标志：`/invocations` 返回 `Received: hello`。先验证服务链路，再加模型。

### C. 部署到中国区

```text
按本仓库第 3 部分把 learning_runtime 部署到 cn-northwest-1。
用我的本地身份，构建 ARM64 镜像并上传中国区 ECR。
逐步解释执行角色、镜像地址和创建参数，等 READY 后实际调用 hello。
真实账户信息只放 .local/，不输出密钥。
```

成功标志：READY 且真实 Invoke 返回应用结果。正文采用 boto3 + 容器实验，不假设 MCP 包所有开发工具都在中国区可用。

### D. 接 Gateway 工具

```text
按第 3 部分创建 AWS_IAM Gateway，注册 get_learning_status Lambda。
说明 Runtime → Gateway、Gateway → Lambda 各用哪个角色。
测试 tools/list、tools/call，再从 Runtime 发 check gateway 验证整条链路。
```

成功标志：工具返回 Lambda 的 `status: ok`。仅创建 Gateway 不算完成联调。

## 2.7 排错

| 现象 | 检查 |
| --- | --- |
| 找不到 uvx | 客户端环境的 PATH；运行 uvx --version |
| 首次启动超时 | 下载包、代理和文档网络；完成下载后重连 |
| 没有文档工具 | 配置是否加载、包版本、Server 日志 |
| 能查文档但不能部署 | 终端身份、区域、创建资源与 PassRole 权限 |
| 生成 Global 或 Cognito 快速创建配置 | 要求按中国区差异和正文参数复核 |

下一步：[3. 部署指南](../02-build-agentcore/README.md)。
