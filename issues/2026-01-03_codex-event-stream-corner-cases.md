### 背景
目前前端的 **Codex 事件流**（`codex_events`）在任务结束后可能“消失/变空”，根因是 executor 的 `update_subtask` 在终态更新时可能只携带 `result.value`（或 `result=None`），后端把 `subtask.result` 覆盖写导致已累积的 `codex_events` / `shell_type` 丢失。

本分支已做的修复方向（供参考）：
- 后端 `update_subtask` 对 `result` 做 merge，确保 `codex_events` / `shell_type` 不被终态覆盖丢失，并把 `codex_event` 追加进 `codex_events`。
- 前端渲染条件从 `shell_type === 'Codex'` 放宽为 “`codex_events` 非空则显示”。

---

### 需要提前关注的 Corner Cases / 风险

#### 1) 并发更新导致事件丢失（lost update）
- 场景：executor 并行/高频上报，两次更新都基于相同的旧 JSON 做 append，然后后写入覆盖前写入。
- 影响：`codex_events` 仍可能“偶发缺条”。
- 建议：
  - 从根上改为 **事件单独表**（append-only）或引入 **乐观锁/版本号**，或 DB 层原子 append（MySQL JSON_APPEND 之类）+ 重试。

#### 2) `codex_events` 无上限增长（DB/网络/前端性能）
- DB：subtask.result JSON 越来越大，更新/读取变慢，可能触发 MySQL 包大小/行大小/索引压力。
- WS：如果后端在 chunk/done 把整个 `codex_events` 送回前端，会导致 payload 过大。
- 前端：`CodexEventStreamPanel` 会对全部事件 pretty-json（`JSON.stringify`），事件多时会卡 UI。
- 建议：
  - 后端：保留完整事件用于回放/导出，但对 WS/列表接口默认只返回最后 N 条（例如 200）+ `total_count`。
  - 前端：默认只渲染最后 N 条 + 虚拟列表/懒计算；点击“展开全部/导出 JSON”再拉全量。

#### 3) “清空事件流”的语义
- 场景：executor 可能发送 `codex_events: []` 试图表达“清空/重置”。
- 风险：如果把空数组当作“不更新”以避免误清空，会改变语义；反之若当作覆盖，又可能把历史误清空。
- 建议：引入显式字段（例如 `clear_codex_events: true`）来表达清空，避免用空数组做隐式语义。

#### 4) `codex_events`（列表）与 `codex_event`（单条）同时出现
- 场景：同一次 update 同时带 “全量快照列表” + “增量单条”。
- 风险：merge 顺序不当会导致最后一条被覆盖/丢失。
- 建议：明确 merge 规则：先采用更“新”的列表（可用长度/序号判断），再 append 单条。

#### 5) 事件重复/乱序
- 场景：重试/重放/断线恢复可能导致同一事件重复出现，或事件顺序与时间不一致。
- 建议：事件结构里若有 `id`/`seq`/`ts`，前端可去重/按序；否则至少允许用户导出 raw JSON 以便排查。

#### 6) 前端显示条件误判
- 放宽为“`codex_events` 非空就显示”后：如果未来其他 shell 也复用 `codex_events` 字段，会被展示出来。
- 建议：可考虑加一个更明确的 `result.shell_type`（或 `result.has_codex_events=true`）作为辅助标识，避免误展示。

---

### 建议的验收/回归检查
- executor RUNNING 期间多次上报 `codex_event`，最终 COMPLETED 只上报 `value`：事件流仍保留。
- 断线重连/刷新：事件流可回放（至少最后 N 条）。
- 超长任务（> 10k events）：UI 不明显卡顿；WS payload 不爆。
- 重试/重放：不出现明显重复/乱序导致的 UI 误导（或提供可接受的降级表现）。

