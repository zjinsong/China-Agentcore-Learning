# 3.3 清理学习资源

完成实验后，先从 `.local/runtime.json` 与 `.local/gateway.json` 核对学习资源，再按下面顺序清理。不要填入 CloudOps 线上资源。只有部署了本实验才执行本页命令；本次文档检查没有执行云资源删除。

## 1. 读取本地记录

从仓库根目录执行，使用部署时相同的账户身份：

```powershell
$runtimeLab = Get-Content .local/runtime.json -Raw | ConvertFrom-Json
$gatewayLab = Get-Content .local/gateway.json -Raw | ConvertFrom-Json
aws sts get-caller-identity --region $runtimeLab.region
```

对照账户、区域和资源名称。若创建中途失败，记录可能缺少字段；用控制台查看已创建的学习资源，仅删除实际存在的条目。脚本不会覆盖同名资源，冲突资源未必属于本次实验。

## 2. 先删除 Gateway target 和 Gateway

```powershell
aws bedrock-agentcore-control delete-gateway-target --gateway-identifier $gatewayLab.gateway_id --target-id $gatewayLab.target_id --region $gatewayLab.region
aws bedrock-agentcore-control list-gateway-targets --gateway-identifier $gatewayLab.gateway_id --region $gatewayLab.region
```

等 target 完全删除、列表为空后再执行：

```powershell
aws bedrock-agentcore-control delete-gateway --gateway-identifier $gatewayLab.gateway_id --region $gatewayLab.region
```

不要在 target 仍在删除中时反复提交 Gateway 删除。

## 3. 删除实验 Runtime 和 Lambda

```powershell
aws bedrock-agentcore-control delete-agent-runtime --agent-runtime-id $runtimeLab.runtime_id --region $runtimeLab.region
aws lambda delete-function --function-name $gatewayLab.lambda_arn --region $gatewayLab.region
```

等 Runtime 删除完成再删除依赖角色和镜像。若删除被 endpoint 或其他关联资源阻止，查看该学习 Runtime 的关联资源并清理；不扩大到其他 Runtime。

## 4. 删除本实验 ECR 与日志组

核对仓库中只有学习镜像后执行：

```powershell
aws ecr delete-repository --repository-name agentcore-learning-runtime --force --region $runtimeLab.region
aws logs delete-log-group --log-group-name /aws/lambda/agentcore-learning-status --region $gatewayLab.region
aws logs describe-log-groups --log-group-name-prefix /aws/bedrock-agentcore/runtimes/learning_runtime --region $runtimeLab.region
```

最后一条只列举 Runtime 日志组。核对完整名称与本实验 Runtime ID 后，在控制台删除对应日志组，或用 `aws logs delete-log-group --log-group-name <核对后的名称>`。不要按宽泛前缀批量删其他应用日志。

## 5. 删除内联策略与角色

确认角色 ARN 与本地记录一致，且仅由本实验创建。先移除策略，再删除角色：

```powershell
aws iam delete-role-policy --role-name learning-runtime-role --policy-name learning-invoke-gateway
aws iam delete-role-policy --role-name learning-runtime-role --policy-name learning-runtime-base
aws iam delete-role --role-name learning-runtime-role
aws iam delete-role-policy --role-name learning-gateway-role --policy-name learning-invoke-lambda
aws iam delete-role --role-name learning-gateway-role
aws iam delete-role-policy --role-name learning-lambda-role --policy-name learning-lambda-logs
aws iam delete-role --role-name learning-lambda-role
```

只做 Runtime 实验时，不存在 Gateway 策略及后两种角色，跳过相应命令。若有未知额外策略或资源关联，先查清来源，不直接剥离。

完成后确认服务列表中学习资源已删除，保留或手动移走 `.local/` 记录；这些记录不提交 GitHub。

继续阅读：[4. Harness](../04-harness/README.md)。
