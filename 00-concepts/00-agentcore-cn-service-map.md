# 1. 中国区服务功能

AgentCore 提供运行 Agent、连接工具、管理外部凭证和观察运行情况的基础设施。你仍需写业务逻辑、选择模型，并决定多个 Agent 如何协作。

先记住：**Runtime 运行代码，Gateway 接入工具。** 例如查询 EC2 CPU：Runtime 中的 Agent 理解问题，调用 Gateway 的监控工具，工具再查 CloudWatch。

## 1.1 六项可用服务

以下区域能力按 [AWS 中国区差异页](https://docs.amazonaws.cn/en_us/aws/latest/userguide/bedrock-agentcore.html) 核对，北京与宁夏均在支持区域内。更新时复核该页。

| 服务 | 作用 | CloudOps 例子 | 详情 |
| --- | --- | --- | --- |
| **Runtime** | 托管运行 Agent 或工具应用 | 运行 Supervisor 和专家 Python 代码 | [Runtime](01-runtime.md) |
| **Gateway** | 把 Lambda、API 等整理成可发现、可调用的工具入口 | 专家通过 MCP 查询 AWS 资源 | [Gateway](02-gateway.md) |
| **Identity** | 为 Agent 访问外部系统管理身份及凭证 | 按外部系统要求使用 OAuth 或 API Key | [Identity](03-identity.md) |
| **Observability** | 指标、日志、追踪；应用需配置相应采集 | 判断耗时在模型还是工具 | [Observability](04-observability.md) |
| **Browser** | 托管浏览器会话 | 处理必须网页交互的任务 | [Browser](05-browser-and-code-interpreter.md) |
| **Code Interpreter** | 隔离的代码执行环境 | 统计已取得的数据 | [Code Interpreter](05-browser-and-code-interpreter.md) |

入门实验先用 Runtime 和 Gateway。查询 AWS API 的业务权限由执行角色提供，其余服务按需求加入。

## 1.2 一条请求中的分工

```text
用户：查询运行中 EC2 的 CPU
  → Runtime：运行 Agent，理解请求并选择工具
  → Gateway：验证调用身份，找到工具并转发
  → Lambda：执行查询，用自己的角色访问 AWS API
  → Runtime：整理工具结果，返回回答

Observability：观察运行过程
Identity：需要外部系统凭证时按需接入
```

登录应用、调用 Runtime、查询 EC2 是不同的权限环节。部署章节在具体位置解释，完整对照见 [鉴权与授权](06-authentication-and-authorization.md)。

## 1.3 中国区缺失项

下表指 AgentCore 平台的对应能力，不代表 AWS 其他产品中的同名功能都不可用。

| 未提供能力 | 应用如何应对 |
| --- | --- |
| Memory | DynamoDB / S3 保存会话、摘要与结果 |
| Harness | 应用实现计划、状态、依赖、重试；见 [第 4 部分](../04-harness/README.md) |
| Registry | 配置文件和应用数据库维护能力清单 |
| Policy | IAM、应用授权、工具参数限制、计划校验 |
| Knowledge Bases | 选择可用的应用检索或 RAG 方案 |
| Evaluations / Optimizations | 自建验收问题、执行记录和离线评测 |
| Payments | 本项目不依赖 |

## 1.4 可用服务内部的差异

| 差异 | 教程选择 |
| --- | --- |
| Runtime 仅提供 MicroVM，缺少 Managed EC2 容量提供方 | 使用容器部署 |
| Runtime 不提供 Cognito user pool 入站选项 | 入门用 IAM；企业接入另配符合要求的 IdP |
| Gateway 没有语义工具搜索 | 正常列举与调用工具，应用按能力目录筛选 |
| Gateway 入站必须为 AWS_IAM 或 CUSTOM_JWT | 示例用 AWS_IAM / SigV4 |
| Identity 缺少 Private IdP 配置及部分内置 OAuth provider | 集成前核对 provider、网络和令牌流程 |
| 部分 Gateway 连接器目录、推理 target、WAF 集成和规则等缺失 | 使用 Lambda target；完整限制见官方差异页 |

部分内置 OAuth provider 缺失不等于 OAuth 2.0 整体不支持；JWT 入站与 OAuth 出站凭证是不同环节。

下一步：[2. Vibe coding MCP 使用](../01-quickstart/README.md)。
