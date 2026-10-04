# 认证与授权

认证回答“调用者是谁”，授权回答“它能做什么”。CloudOps 的边界如下：

```text
用户 → 控制面：应用登录与用户隔离
Runtime → Gateway：AWS_IAM / SigV4
Gateway → Lambda：Gateway 调用角色
Lambda → AWS API：Lambda 执行角色最小权限
Terraform apply：用户确认过的具体 plan + 独立执行角色
```

`AWS_IAM` 不代表无鉴权，而是调用者用短期 IAM 凭证签名。OAuth Provider 数量为零，只表示未配置 Gateway 访问外部 SaaS 所需的 OAuth 凭证。
