# 1. 中国区功能

AgentCore 提供运行 Agent、接工具、管凭证、看运行情况的基础设施。业务逻辑、模型选择、多 Agent 协作仍然由你写。

一句话记住:**Runtime 跑代码,Gateway 接工具。**

**模型不在里面。** AgentCore 不提供基础模型,中国区 Bedrock 也没有可用模型 —— 模型要从外部接(自部署的,或 DeepSeek、通义千问这类第三方 API,多数提供 OpenAI 兼容接口)。怎么接见 [3.10](03-build.md#310-接模型从-echo-变成真-agent)。

## 1.1 一条请求怎么走

用户问"运行中 EC2 的 CPU 多少":

```text
用户 → Runtime(Agent 理解问题,决定调哪个工具)
     → Gateway(验证身份,路由到工具)
     → Lambda(执行查询,用自己的角色访问 AWS)
     → Runtime(整理结果,回答)
```

每个箭头是**不同的权限环节**:给 Runtime 加调 Gateway 的权限,不等于给 Lambda 加 DescribeInstances。

## 1.2 六项可用服务

| 服务 | 作用 | CloudOps 里用来干什么 |
| --- | --- | --- |
| **Runtime** | 托管运行 Agent 代码 | 跑 Supervisor 和各专家 |
| **Gateway** | 工具的统一入口(MCP) | 专家查 AWS 资源 |
| **Identity** | 管理访问外部系统的凭证 | 接企业 SaaS 时用(本教程不用) |
| **Observability** | 指标、日志、追踪 | 判断慢在模型还是工具 |
| **Browser** | 托管浏览器会话 | 必须网页交互的任务 |
| **Code Interpreter** | 隔离的代码执行环境 | 对已取得的数据做计算 |

入门只用 Runtime + Gateway。

### Runtime

把 Agent 的服务部署成托管环境。中国区只有 **MicroVM**(没有 Managed EC2 容量提供方),所以关注容器启动、依赖体积、健康检查。

每会话资源上限 **2 vCPU / 8 GB**,不可调。默认空闲 15 分钟回收会话,会话最长 8 小时(`idleRuntimeSessionTimeout` / `maxLifetime` 可配)。

Runtime 只管跑代码,**不管**你的业务状态和任务编排——那些放应用侧(第 5 章)。

### Gateway

Agent 调工具的统一入口。它验证调用者,再路由到 Lambda 等 target。

两个容易混的东西:

- **入站鉴权**:谁能调 Gateway。中国区只能 `AWS_IAM` 或 `CUSTOM_JWT`(没有 Cognito user pool、没有 No-auth)
- **出站凭证**:Gateway 代表 Agent 访问外部 SaaS 时用的 OAuth / API Key

本教程入站用 `AWS_IAM`(SigV4),不配出站凭证。

### Identity

管理 Agent 访问外部系统的凭证。企业登录的常见做法:企业 IdP 签发 JWT,Gateway 用 `CUSTOM_JWT` 校验 issuer / audience / scope。

中国区限制的是**部分内置 OAuth provider 和 Private IdP 配置**,不等于 OAuth 2.0 整体不可用。

### Observability

看四层:浏览器请求 → 控制面任务 → Runtime 调用 → 工具调用。

资源消耗指标在 CloudWatch 命名空间 **`AWS/Bedrock-AgentCore`**:`CPUUsed-vCPUHours`、`MemoryUsed-GBHours`,可按 Runtime 拆分。注意不是小写的 `bedrock-agentcore`(那里放的是应用层 strands/http 指标)。

### Browser 和 Code Interpreter

都可用,但别默认加进团队。它们需要独立的会话生命周期、文件访问和成本边界,等主链路跑通再考虑。

## 1.3 中国区没有什么

指 AgentCore 平台的对应能力缺失,不是说 AWS 其他产品的同名功能不可用。

| 缺的能力 | 怎么替代 |
| --- | --- |
| Memory | DynamoDB 存索引/状态,S3 存正文和结果 |
| Harness | 应用自己实现计划、状态、依赖、重试(第 5 章) |
| Registry | 配置文件 + 数据库维护能力清单 |
| Policy | IAM + 工具参数校验 + 计划校验 |
| Knowledge Bases | 自选检索/RAG 方案 |
| Evaluations / Optimizations | 自建验收用例和执行记录 |

缺这些不代表做不了多 Agent,只是**状态和治理的责任从托管组件转到你的应用**。

## 1.4 可用服务内部的差异

| 差异 | 怎么应对 |
| --- | --- |
| Runtime 只有 MicroVM | 用容器部署,关注启动速度 |
| Runtime 没有 Cognito 入站 | 入门用 IAM;企业接入另配 IdP |
| Gateway 没有语义工具搜索 | 应用侧维护能力目录,显式选工具 |
| Gateway 入站只能 AWS_IAM / CUSTOM_JWT | 本教程用 AWS_IAM / SigV4 |
| 部分 Gateway 连接器、推理 target 缺失 | 用 Lambda target |

## 1.5 Runtime 版本:V1 和 V2

中国区现在默认 **V2**。区别在启动方式:

| | V1 | V2 |
| --- | --- | --- |
| 启动 | 每个新会话拉取并解压镜像 | 从快照恢复 |
| 冷启动受镜像大小影响 | 是 | 否 |
| 速度 | 慢 | 快且稳定 |

查版本:

```bash
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id <runtime-id> --query 'platformVersion' --output text
```

**V2 的编程约束**:启动阶段(模块级代码)做的事会被快照捕获,所有恢复出来的实例共享同一份。所以:

```python
# 错:V2 下所有实例的"现在"都是部署那一刻
START = datetime.now()

def handler(event, context):
    ...

# 对:每次请求取真实时间
def handler(event, context):
    now = datetime.now()
```

规则:**时间、随机数、唯一 ID、会话状态放请求处理函数内**;无状态配置(boto3 client、FastAPI app)可以放模块级。

下一步:[2. Vibe coding 上手](02-vibe-coding.md)
