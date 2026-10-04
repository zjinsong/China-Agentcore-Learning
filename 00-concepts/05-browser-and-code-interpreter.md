# Browser 与 Code Interpreter

两者在中国区可用，但不应默认加入 CloudOps 团队。Browser 适合需要网页自动化且有人工接管的场景；Code Interpreter 适合隔离的数据处理或生成工件。

它们需要独立的用户隔离、会话生命周期、文件访问、网络访问、输出审计和成本边界。本学习仓库先讲治理原则；在没有这些控制前，不把它们接入生产式 CloudOps 流程。
