# Identity

Identity 处理 Agent 访问外部系统时的凭证与授权边界。对于企业登录，常见模式是企业 IdP 签发 JWT，Gateway 配置 `CUSTOM_JWT` 校验 issuer、audience、scope 或 claims。对于当前 CloudOps 的 AWS 内部工具，Gateway 使用 `AWS_IAM`，Lambda 使用自身执行角色，没有外部 OAuth Provider。

中国区对私有 IdP 和内置 OAuth Provider 有功能限制；设计前请先阅读 [中国区差异](../05-china-region/README.md)。
