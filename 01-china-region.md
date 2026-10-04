# 1. 中国区功能

AgentCore 提供运行 Agent、接工具、管凭证、看运行情况的基础设施。业务逻辑、模型选择、多 Agent 协作仍然由你写。

一句话记住:**Runtime 跑代码,Gateway 接工具。**

**AgentCore 服务独立于 LLM 模型。** 它只负责托管和调度,模型由你自己选、自己配:

| | 常用模型 | 怎么接 |
| --- | --- | --- |
| 海外 | Bedrock 上的 Claude、Nova 等 | SDK 直接调 Bedrock |
| **中国区** | **DeepSeek、通义千问、Kimi 等第三方 API,或自部署模型** | **OpenAI 兼容接口(base_url + api_key + model_id)** |

中国区 Bedrock 没有基础模型,所以走第二行。配置就是三个环境变量,代码不用改 —— 见 [3.10 接模型](03-build.md#310-接模型从-echo-变成真-agent)。

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

| 服务 | 一句话 | CloudOps 里用来干什么 |
| --- | --- | --- |
| **Runtime** | 你的 Agent 代码跑在这 | 跑 Supervisor 和各专家 |
| **Gateway** | Agent 调工具的总入口 | 专家查 AWS 资源 |
| **Identity** | 托管访问外部系统的凭证 | 接企业 SaaS 时用(本教程不用) |
| **Observability** | 看哪一环慢了、错了 | 判断慢在模型还是工具 |
| **Browser** | 给 Agent 一个云端浏览器 | 只有网页没 API 的场景 |
| **Code Interpreter** | 给 Agent 一个代码沙箱 | 对查到的数据做计算 |

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

解决一个具体问题:**Agent 要访问公司内部系统或第三方 SaaS 时,凭证从哪来、放哪里。**

比如 Agent 要查公司的工单系统,那个系统只认 OAuth token,不认 AWS IAM。Identity 就是帮你托管这类外部凭证的地方 —— 存起来、按需取用、到期刷新,而不是把 token 硬写在代码里。

企业登录的常见做法:企业 IdP(Okta、Azure AD 等)签发 JWT,Gateway 配 `CUSTOM_JWT` 校验这个令牌的 issuer / audience / scope,确认调用者是谁。

本教程只访问同账户的 AWS 资源,全程用 IAM,所以不需要 Identity。中国区限制的是**部分内置 OAuth provider 和 Private IdP 配置**,不等于 OAuth 2.0 整体不可用。

### Observability

Agent 系统慢或出错时,你得知道卡在哪一环。链路有四层,每层都可能是瓶颈:

```text
浏览器请求 → 控制面任务 → Runtime 调用 → 工具调用
```

常见误判:用户说"回答很慢"就归咎于 Runtime 冷启动,实际可能是模型规划花了 20 秒、或某个工具重试了三次。**不看分层数据就是瞎猜。**

资源消耗指标在 CloudWatch 命名空间 **`AWS/Bedrock-AgentCore`**:`CPUUsed-vCPUHours`、`MemoryUsed-GBHours`,可按 Runtime 拆分(也是计费依据)。

注意**别找错命名空间**:小写的 `bedrock-agentcore` 放的是应用层指标(工具调用次数/耗时、HTTP 请求),大写的 `AWS/Bedrock-AgentCore` 才是资源消耗。两个都有用,但是不同的东西。

### Browser 和 Code Interpreter

这两个是 AgentCore 托管的**沙箱环境**,让 Agent 能"动手"而不只是"回答"。

**Browser** 给 Agent 一个云端浏览器。Agent 可以打开网页、点按钮、填表单、读页面内容 —— 用在没有 API 只有网页的场景,比如登录某个管理后台查数据、或从网页抓取信息。你还能拿到一个实时画面地址(live view),人工随时接管。

**Code Interpreter** 给 Agent 一个隔离的代码执行环境。Agent 写一段 Python 丢进去跑,拿回结果 —— 用在算数、画图、处理数据这类"模型自己算不准"的场景。比如查到 100 台实例的成本数据,让它写代码算分位数,比让模型心算靠谱。

都是中国区可用,SDK 直接调(不走 Gateway)。

什么时候用:**先把 Runtime + Gateway 主链路跑通再说**。它们各自要管会话生命周期、文件进出、成本上限,是独立的一摊事 —— 入门阶段加进来只会让你分不清问题出在哪。

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
