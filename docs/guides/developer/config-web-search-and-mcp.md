# WEB_SEARCH 与 MCP 配置速查

放置位置：后端环境变量（`.env` 或部署环境）。所有示例请按需调整。

## Web Search
- `WEB_SEARCH_ENABLED`：是否开启搜索工具，默认 `false`。
- `WEB_SEARCH_ENGINES`：JSON，定义搜索引擎及 `max_results`、`api_key` 等。
- `WEB_SEARCH_DEFAULT_MAX_RESULTS`：LLM 未指定时的默认返回数量，默认 `100`。可被引擎 `max_results` 或 LLM 参数覆盖。

示例：
```
WEB_SEARCH_ENABLED=true
WEB_SEARCH_DEFAULT_MAX_RESULTS=50
WEB_SEARCH_ENGINES={"google":{"api_key":"***","cx":"***","max_results":20}}
```

## MCP（Model Context Protocol）
- `CHAT_MCP_ENABLED`：是否允许 Chat Shell 模式启用 MCP，默认 `false`。
- `CHAT_MCP_SERVERS`：JSON，列出可用 MCP 服务器及 headers/urls。
- 支持变量替换：`${{user.name}}`、`${{user.id}}` 可用于 headers、urls。

示例：
```
CHAT_MCP_ENABLED=true
CHAT_MCP_SERVERS={
  "gh": {
    "url": "https://mcp.example.com",
    "headers": {"X-User": "${{user.name}}"}
  }
}
```

### GitHub MCP（最小权限建议）

若使用 `ghcr.io/github/github-mcp-server`，建议默认启用只读并显式枚举 toolset：

```
GITHUB_READ_ONLY=true
GITHUB_TOOLSETS=repos,pulls
```

写操作需要显式关闭只读并配合平台侧策略门禁/审计（不建议仅依赖提示词）。

## 使用提示
- 生产环境密钥请用平台 Secret 管理，勿写入仓库。
- 若搜索/MCP 关闭，前端相关入口需显示为不可用或降级提示。
- 变更配置后需重启后端服务生效。
