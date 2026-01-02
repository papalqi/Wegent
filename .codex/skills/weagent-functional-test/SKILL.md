---
name: weagent-functional-test
description: Run WeAgent/Wegent functional (smoke/regression) tests using the repo’s Playwright E2E suite and/or interactive Chrome MCP (chrome-devtools/playwright MCP) to validate user-requested web UI flows, capture evidence (screenshots/snapshots/logs), and write a short test report. Use when asked to do 功能测试/回归测试/冒烟测试, E2E, Playwright, UI flow verification, or to debug failing E2E with a real browser.
---

# WeAgent / Wegent 功能测试

## 先确认输入
- 代码仓库路径（例如 `.../Wegent`，或包含 `frontend/` 的目录）
- 你要验证的功能范围（必填，二选一或混合）：
  - 指定“业务链路/页面/按钮/期望行为”（例如：登录 -> 新建编程任务 -> 等待完成 -> 打开 Workbench -> 查看 diff）
  - 指定“Playwright 用例文件/用例名/grep 条件”（例如：`e2e/tests/auth.spec.ts` 或 `--grep "login"`）
- 目标环境：
  - `E2E_BASE_URL`（默认 `http://localhost:3000`）
  - `E2E_API_URL`（默认 `http://localhost:8000`）
- 测试账号与权限（优先使用项目 E2E 默认账号；如需改用环境变量覆盖，先确认变量名）
- 执行方式：自动化 E2E、Chrome MCP 交互式回归、或两者结合

## 工作流 A：跑 Playwright E2E（优先，按你指定范围选用例）
1. 启动或复用可用的后端与前端（按项目约定：`start.sh`）。
2. 进入 `frontend/`，必要时安装依赖：`npm ci`。
3. 根据你给的“功能范围/用例文件/grep 条件”运行用例（尽量只跑相关用例，避免固定全量）：
   - 指定文件：`npm run e2e -- --project=chromium <spec.ts>`
   - 指定 grep：`npm run e2e -- --project=chromium --grep "<pattern>"`
   - 仅当你明确要求“全量回归”时才跑：`npm run e2e`
4. 失败调试（更利于定位 UI/时序问题）：`npm run e2e:headed -- <同样参数>` 或 `npm run e2e:debug -- <同样参数>`。
5. 打开报告：`npm run e2e:report`。

## 工作流 B：用 Chrome MCP 做交互式功能回归（补充 / 调试，按你指定链路走）
1. 启动并保持一个可复用的浏览器会话（已登录更高效）。
2. 使用 Chrome MCP（通常是 `chrome-devtools`）完成：
   - 打开页面并访问 `E2E_BASE_URL`
   - 登录（常见路由 `/login`）
   - 按你指定的链路逐步验证（不要默认跑固定路由；只有在你未给范围时，才做最小冒烟）
   - 通过页面快照与截图保存证据（例如 `take_snapshot` / `take_screenshot`）
3. 生成测试报告（Markdown 即可），至少包含：环境信息、步骤、期望/实际、证据文件路径、以及阻塞/回滚建议。

## 临时快照：直接探查远程 UI（无法复用现成会话时）
- 适用：只需快速确认某 URL 是否可达/获取首屏截图，不依赖仓库依赖；常见场景是外部环境 3xx/防火墙不明。
- 准备：如无 Playwright，先下载独立浏览器 `npx playwright@1.41.2 install chromium`（耗时较久，联网）。
- 运行：
  - `NODE_PATH=$(npm root -g) node - <<'NODE'`+脚本，其中 `chromium.launch({ headless:true })`，`page.goto('<URL>', { waitUntil:'networkidle', timeout:30000 })`，`page.screenshot({ path:'/tmp/<name>.png', fullPage:true })`，`console.log(bodyText.slice(0,2000))`。
  - 如果返回 `ERR_CONNECTION_REFUSED`/超时，记录错误即为证据，说明当前环境无法直连目标。
- 清理：如被提示“browser already in use”，先 `ps -ef | grep mcp-chrome|playwright` 并 kill 残留，再重试。

## 证据清单（每次回归都要有）
- 可复现的步骤 + 具体环境变量
- 每个你指定的关键检查点的截图/快照
- 必要时附控制台报错 / 失败请求（状态码、接口、响应片段）
- 如果是回归：最早失败的提交/PR（如已知）

## 仓库内定位（Wegent）
- 用例目录：`frontend/e2e/tests/`
- E2E 入口与默认路由/环境变量：`frontend/e2e/config/environment.ts`
- Playwright 配置：`frontend/playwright.config.ts`

## 辅助脚本
- 使用 `scripts/run_wegent_e2e.py` 自动定位仓库并给出推荐命令（默认只打印，需显式 `--run` 才会真正执行）。
