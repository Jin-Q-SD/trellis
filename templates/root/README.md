# {{PROJECT_NAME}}

{{ONE_LINER}}

## 当前进展

<!-- agent 在每次会话结束时更新这里，只保留最近两三条 -->
- {{DATE}}：项目初始化。

## 去哪里找

| 目录 | 里面是什么 |
|---|---|
{{DIR_MAP_HUMAN}}

## 怎么和 agent 协作

- **给 agent 文件**：直接丢进 `import/`（丢在根目录也可以）。agent 会按规则改名，放到该去的地方；拿不准的会留在原地并问你。
- **让 agent 记住一条规则**：直接说"记成规则"，它会写进 `agent/guidelines/`。
- **整理和体检**：说 `/trellis tidy`。
- **删除**：agent 不会真的删除文件，只会移进 `_delete/`。确认不需要了，再让它清空。
- **用 Codex 的话**：第一次打开项目时在 Codex 里执行 `/hooks`，信任项目的 hooks。这些 hooks 负责提醒和拦截删除。
