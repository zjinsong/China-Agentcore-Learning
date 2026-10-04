# Terraform 安全边界

Agent 可生成配置和 plan，不能自行 apply。用户确认必须绑定具体 plan、内容指纹和有效期；executor 只执行保存的二进制 plan。执行超时、进程重启或结果不明时进入人工核对，不自动重放。
