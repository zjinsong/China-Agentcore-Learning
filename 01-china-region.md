# 1. 中国区功能与替代方案

Amazon Bedrock AgentCore 是用于构建、部署和运维 AI agent 的平台。它由一组**模块化服务**组成,可以单独用,也可以组合用;兼容任意 agent 框架(Strands Agents、LangGraph、CrewAI 等)和任意基础模型。

本章说明:每个服务是什么、中国区(宁夏 `cn-northwest-1`、北京 `cn-north-1`)哪些可用、不可用的用什么替代。以 [AWS 中国区功能差异页](https://docs.amazonaws.cn/en_us/aws/latest/userguide/bedrock-agentcore.html) 为准,更新时请复核该页。

## 1.1 核心服务

| 服务 | 作用 |
| --- | --- |
| **Runtime** | 无服务器运行环境,托管和伸缩 agent 或工具代码,提供会话隔离 |
| **Gateway** | 把 API、Lambda、现有服务转换成 MCP 工具,或接入已有 MCP server,供 agent 调用 |
| **Identity** | agent 的身份与凭证管理,兼容现有身份提供商(IdP) |
| **Memory** | 短期(多轮对话)与长期(跨会话)记忆 |
| **Code Interpreter** | 隔离的代码执行沙箱,让 agent 运行代码 |
| **Browser** | 云端浏览器,让 agent 操作网页 |
| **Observability** | 基于 OpenTelemetry 的追踪、调试和监控 |

> AgentCore 不提供基础模型。模型由你选择 —— 海外项目常用 Bedrock 上的 Claude、Nova 等;中国区 Bedrock 无基础模型,改用第三方 OpenAI 兼容接口(DeepSeek、通义千问等),见 [第 3 章](03-build.md)。

## 1.2 一次 agent 调用的分工

以"查询某城市天气"为例,看服务怎么配合:

```text
用户请求
  → Runtime        运行 agent 代码,调用模型理解请求、决定调用哪个工具
  → Gateway        验证调用者身份,路由到对应工具
  → Lambda 工具     执行查询(用自己的执行角色访问资源)
  → Runtime        把工具结果交给模型,生成回答
```

每个箭头是独立的权限边界。给 Runtime 调用 Gateway 的权限,不等于给 Lambda 访问具体资源的权限。入门只需要 Runtime 和 Gateway。

## 1.3 中国区不可用的服务与替代方案

下表的"不可用"指 AgentCore 平台的对应托管能力,不代表 AWS 其他产品的同名功能不可用。替代方案把相应职责从托管组件转移到你自己的应用。

| 服务 | 中国区 | 替代方案 |
| --- | --- | --- |
| Harness | 不可用 | 应用自行实现 agent 循环:计划、工具调度、状态管理(见 [第 5 章](05-harness.md)) |
| Memory | 不可用 | DynamoDB 存会话索引与状态,S3 存正文与结果 |
| Identity(内置 OAuth provider / 私有 IdP) | 部分不可用 | 用 `CUSTOM_JWT` 对接企业 IdP,或应用自管凭证 |
| Evaluations / Optimization | 不可用 | 自建评测用例与离线分析 |
| Payments | 不可用 | 不依赖 |

> Harness 是 AgentCore 提供的"托管 agent 循环"——用一次 API 调用就能指定模型、提示词、工具并运行,平台负责编排、工具执行和记忆。中国区没有它,所以第 5 章讲怎么用应用代码实现等价的最小循环。

## 1.4 可用服务的区域差异

| 服务 | 差异 | 应对 |
| --- | --- | --- |
| Runtime | 仅 MicroVM 计算类型,无 Managed EC2 容量提供方 | 用容器部署;单会话上限 2 vCPU / 8 GB |
| Runtime | 无 Cognito user pool 入站授权 | 入站用 `AWS_IAM`;企业场景用 `CUSTOM_JWT` |
| Gateway | 入站授权仅 `AWS_IAM` 或 `CUSTOM_JWT`,无 No-auth | 本教程用 `AWS_IAM`(SigV4) |
| Gateway | 无语义工具搜索 | 应用维护工具清单,显式选择工具 |
| Identity | 部分内置 OAuth provider、私有 IdP 配置缺失 | 集成前核对目标系统的 provider 与令牌流程 |

## 1.5 Runtime 平台版本(V1 / V2)

`platformVersion` 字段控制 Runtime 的启动方式,取值 `V1` 或 `V2`。

| | V1 | V2 |
| --- | --- | --- |
| 启动方式 | 每个新会话拉取并解压容器镜像 | 从快照恢复环境 |
| 冷启动受镜像大小影响 | 是 | 否 |

查看现有 Runtime 的版本:

```bash
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id <runtime-id> --region cn-northwest-1 \
  --query 'platformVersion' --output text
```

V2 的编程约束:启动阶段(模块级代码)的执行结果会被写入快照,并由所有恢复出来的会话共享。因此时间戳、随机数、唯一 ID、会话相关状态必须在**请求处理函数内**生成,不能放模块级。

```python
# 错误:V2 下所有会话共享快照时刻的时间
START = datetime.now()

# 正确:每次请求生成
def handler(event, context):
    now = datetime.now()
```

无状态的配置对象(boto3 client、框架 app 实例)可以放模块级 —— 它们不含启动时固化的状态。

## 1.6 会话生命周期

- 每个会话有唯一 `runtimeSessionId`,运行在独立 MicroVM 中(CPU、内存、文件系统隔离)
- 会话最长 **8 小时**;空闲 **15 分钟**后终止
- 会话终止后 MicroVM 销毁、内存清理;用同一 `runtimeSessionId` 再次请求会创建新环境
- 会话状态是临时的,不要用于持久化(持久化用外部存储)

下一步:[2. Vibe coding MCP 快速上手](02-vibe-coding.md)
