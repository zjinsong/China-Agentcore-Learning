# 身份、鉴权和授权：按调用方向理解

认证确定是谁，授权决定能做什么。先画出调用链，再配置对应角色或令牌。

| 环节 | 谁访问谁 | 常见配置 | 权限由谁提供 |
| --- | --- | --- | --- |
| 应用登录 | 用户 → Web / 控制面 | 企业 SSO / OIDC | 应用用户与租户授权 |
| 调用 Runtime | 控制面 → Runtime | IAM / SigV4，或符合配置的 JWT | 调用者的 IAM 策略或入站 JWT 条件 |
| 调用 Gateway | Runtime → Gateway | AWS_IAM / SigV4，或 CUSTOM_JWT | Runtime 调用身份或满足条件的令牌 |
| 调用 Lambda | Gateway → Lambda | GATEWAY_IAM_ROLE | Gateway service role 的 InvokeFunction |
| 查询 AWS 资源 | Lambda → AWS API | SDK 自动使用执行角色 | Lambda execution role 的具体 API 权限 |
| 访问外部系统 | Agent / 工具 → 企业 API / SaaS | 目标接受的 OAuth token、API Key 等 | 外部系统自己的权限模型 |

因此，给 Runtime 增加 InvokeGateway 并不等于给 Lambda 增加 DescribeInstances。用户登录应用也不自动给后台 Runtime 赋予云资源权限。

## IAM 与 JWT 两种入站例子

IAM：调用者用短期 IAM 凭证签名，服务检查身份与策略。boto3 调用 Runtime 自动完成签名；Gateway HTTP 请求需要相应签名客户端。

JWT：服务信任配置中的企业 IdP，核对签名及 audience/client/scope 等已设置条件。OAuth 2.0 描述获取/授予访问令牌的流程，JWT 是令牌的一种格式，不能把二者理解为同一层两个并列开关。

## 出站访问外部系统

AWS 角色不能直接当作任意企业系统的权限。目标支持 IAM 联合身份时，可按其流程交换或映射身份；目标只接受 OAuth 时，就按它的 OAuth 流程获得 token，并由目标系统定义 scope/资源权限。

Identity 可帮助管理出站凭证，但不自动解决目标系统的授权。中国区限制的是部分内置 OAuth provider 和 Private IdP 配置，不能推导为 OAuth 整体不支持。

正文部署案例只访问同账户 Lambda，使用 IAM，不需要配置 OAuth/API Key provider。[部署实例](../02-build-agentcore/README.md)

参考：[中国区限制](https://docs.amazonaws.cn/en_us/aws/latest/userguide/bedrock-agentcore.html)、[Gateway 入站](https://docs.amazonaws.cn/en_us/bedrock-agentcore/latest/devguide/gateway-inbound-auth.html)、[Gateway 出站](https://docs.amazonaws.cn/en_us/bedrock-agentcore/latest/devguide/gateway-building-adding-targets-authorization.html)。
