# 2. Vibe coding 上手

把 AgentCore MCP Server 接到编码助手(Kiro / Claude Code / Codex),让它查 AgentCore 文档、改代码、帮你部署。

## 2.1 它是什么

MCP 是编码助手调用外部工具的协议。`awslabs.amazon-bedrock-agentcore-mcp-server` 这个包提供两类工具:

- **文档工具**:`search_agentcore_docs`、`fetch_agentcore_doc`
- **平台工具**:建/管 Runtime、Gateway、Memory、Identity、Policy 等(底层是 boto3)

分清两条线:

```text
开发时:你 → 编码助手 → 本地 AgentCore MCP → 文档 + 平台 API
运行时:用户 → Runtime → Gateway → 业务工具
```

本章配**第一行**。第 3 章部署**第二行**。开发用的 MCP 不会变成 CloudOps 专家的查询工具。

**中国区可用**:这个包纯 Python + boto3,不依赖 `@aws/agentcore` CLI(那个不支持中国区)。只要设 `AWS_REGION=cn-northwest-1`,boto3 自动解析到 `.amazonaws.com.cn`。

## 2.2 准备

```bash
# uv 提供 uvx,用来启动 MCP 包
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

python3 --version
uvx --version
aws --version
```

查文档不需要 AWS 身份。要让助手帮你部署,先配好:

```bash
export AWS_PROFILE=china-learning
export AWS_REGION=cn-northwest-1
export AWS_DEFAULT_REGION=cn-northwest-1
aws sts get-caller-identity
```

## 2.3 Kiro

创建 `.kiro/settings/mcp.json`(已有文件就合并 `mcpServers`):

```json
{
  "mcpServers": {
    "bedrock-agentcore-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.amazon-bedrock-agentcore-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "china-learning",
        "AWS_REGION": "cn-northwest-1",
        "AWS_DEFAULT_REGION": "cn-northwest-1"
      },
      "disabled": false,
      "autoApprove": ["search_agentcore_docs", "fetch_agentcore_doc"]
    }
  }
}
```

重启 Kiro。`autoApprove` 只放文档读取,写操作每次手工确认。

**工具分组开关**(可选):默认全开 8 组约 109 个工具,其中 browser / code_interpreter 依赖 playwright,启动较慢。只要 agent 开发相关的,在 `env` 里加一行(白名单):

```text
"AGENTCORE_ENABLE_TOOLS": "runtime,gateway,memory"
```

反过来用 `AGENTCORE_DISABLE_TOOLS` 是黑名单。

GUI 客户端可能不继承终端环境变量,所以上面把 `AWS_PROFILE` 写进了 `env`。

## 2.4 Claude Code

```bash
claude mcp add --scope user --transport stdio \
  --env FASTMCP_LOG_LEVEL=ERROR \
  --env AWS_PROFILE=china-learning \
  --env AWS_REGION=cn-northwest-1 \
  --env AWS_DEFAULT_REGION=cn-northwest-1 \
  bedrock-agentcore-mcp-server \
  -- uvx awslabs.amazon-bedrock-agentcore-mcp-server@latest

claude mcp list
```

会话里输入 `/mcp` 看连接状态。

## 2.5 Codex

```bash
codex mcp add bedrock-agentcore-mcp-server \
  --env FASTMCP_LOG_LEVEL=ERROR \
  --env AWS_PROFILE=china-learning \
  --env AWS_REGION=cn-northwest-1 \
  --env AWS_DEFAULT_REGION=cn-northwest-1 \
  -- uvx awslabs.amazon-bedrock-agentcore-mcp-server@latest

codex mcp list
```

或写进 `~/.codex/config.toml`:

```toml
[mcp_servers.bedrock-agentcore-mcp-server]
command = "uvx"
args = ["awslabs.amazon-bedrock-agentcore-mcp-server@latest"]
startup_timeout_sec = 60

[mcp_servers.bedrock-agentcore-mcp-server.env]
FASTMCP_LOG_LEVEL = "ERROR"
AWS_PROFILE = "china-learning"
AWS_REGION = "cn-northwest-1"
AWS_DEFAULT_REGION = "cn-northwest-1"
```

## 2.6 验证连通

命令行直接验证(不用进客户端):

```bash
export AWS_REGION=cn-northwest-1
uvx --from awslabs.amazon-bedrock-agentcore-mcp-server@latest python - <<'PY'
import asyncio
from awslabs.amazon_bedrock_agentcore_mcp_server.server import mcp
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.runtime.runtime_client import get_control_client

async def main():
    tools = await mcp.list_tools()
    print(f"工具数: {len(tools)}")
    c = get_control_client()
    print("endpoint:", c.meta.endpoint_url)
    print("现有 runtime:", [r["agentRuntimeName"] for r in c.list_agent_runtimes(maxResults=5).get("agentRuntimes", [])])

asyncio.run(main())
PY
```

endpoint 应该是 `https://bedrock-agentcore-control.cn-northwest-1.amazonaws.com.cn`。

## 2.7 对话例子

直接复制给助手用。

**A. 验证文档工具**

```text
用 AgentCore MCP 搜索并读取 Runtime 协议契约。
列出 HTTP、MCP、A2A、AG-UI 四种协议各自的端口和挂载路径,给出处链接。
不要创建资源。
```

成功标志:助手**实际调用**了文档工具,回答 8080 `/invocations`、8000 `/mcp`、9000 `/`、8080 `/invocations`。光嘴答不算。

**B. 本地跑通应用**

```text
读 03-build/app.py,解释 BedrockAgentCoreApp、@app.entrypoint、app.run() 各做什么。
然后本地运行,发一个 hello 请求,把实际返回贴出来。
```

成功标志:`/invocations` 返回 `Received: hello`。

**C. 部署到中国区**

```text
按第 3 章把 learning_runtime 部署到 cn-northwest-1。
用我本地的 AWS 身份,构建 arm64 镜像推到中国区 ECR。
逐步说明执行角色、镜像地址、创建参数;等 READY 后真实调用一次 hello。
```

成功标志:状态 READY **且**真实 Invoke 返回结果。只创建成功不算。

**D. 接 Gateway**

```text
按第 3 章创建 AWS_IAM Gateway,注册 get_learning_status Lambda 为 target。
说明 Runtime→Gateway、Gateway→Lambda 各用哪个角色。
先测 tools/list 和 tools/call,再从 Runtime 发 check gateway 验证整条链路。
```

成功标志:工具返回 Lambda 的 `status: ok`。

## 2.8 排错

| 现象 | 查什么 |
| --- | --- |
| 找不到 uvx | 客户端环境的 PATH;`uvx --version` |
| 首次启动超时 | 下载包的网络;下完重连 |
| 没有文档工具 | 配置是否加载、包版本、Server 日志 |
| 能查文档不能部署 | 终端身份、区域、创建资源和 PassRole 权限 |
| 助手生成 Global 配置(Cognito 等) | 要求按第 1 章的中国区差异重做 |

下一步:[3. 构建指南](03-build.md)
