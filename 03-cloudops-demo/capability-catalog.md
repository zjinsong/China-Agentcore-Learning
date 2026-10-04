# 能力目录

不要仅按“专家名称”路由。每项能力应声明：输入、输出、允许区域、工具、访问级别和执行指导。

```json
{
  "id": "discover_monitoring_resources",
  "expert": "monitoring",
  "inputs": ["service", "region"],
  "outputs": ["resource_identifiers"],
  "access": "read_only"
}
```

实际可用性必须同时满足：专家启用、Runtime 可用、工具已挂载、Gateway inventory 中存在该工具。声明文件不是权限证明，真实调用仍由 Lambda execution role 决定。
