# Lab：第一个 Runtime

目标：把一个最小 Python HTTP Agent 变为 AgentCore Runtime 兼容应用，再部署和调用它。示例不访问 AWS 资源，不读取凭证，也不含业务数据。

## 1. 本地运行

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

在另一个终端调用：

```bash
curl -X POST http://127.0.0.1:8080/invocations \
  -H 'content-type: application/json' \
  -d '{"prompt":"你好"}'
```

## 2. 用 MCP 辅助改造

把 `app.py` 打开后，对编码助手说：

> Transform this AgentCore agent code to be compatible with AgentCore runtime. Update imports, dependencies, and application structure as needed.

这个提示词来自 [官方 MCP 快速上手](https://docs.amazonaws.cn/en_us/bedrock-agentcore/latest/devguide/mcp-getting-started.html)。逐行审阅改动后再部署。

## 3. 部署前检查

- 选择正确的中国区区域。
- 创建最小权限 Runtime execution role。
- 不在代码或 Dockerfile 中写密钥。
- 记录 Runtime ARN 到私有部署状态，不要提交 Git。

部署后用一个固定请求调用，核对响应、CloudWatch 日志和 Runtime 状态。下一实验是 [Gateway 与 Lambda MCP target](../../02-build-agentcore/gateway-lambda-mcp/README.md)。
