# {{PROJECT_NAME}} · Agent 入口

> 这是给 agent 的入口文件。给人看的项目介绍在 [README.md](README.md)。

{{ONE_LINER}}

## 每次会话开始：必读顺序

1. [agent/PROJECT.md](agent/PROJECT.md)：项目简报和当前状态。标着"待补充"的信息，在对话中得知时随手补上。
2. [agent/guidelines/INDEX.md](agent/guidelines/INDEX.md)：规则索引，按当前任务打开相关条目。
3. 需要历史背景时，查 [agent/memory/INDEX.md](agent/memory/INDEX.md)，按标签或日期只打开相关的几条。不要整目录加载。
4. 需要工具时，查 [agent/tools/INDEX.md](agent/tools/INDEX.md)。
5. 看一眼 `import/` 和根目录有没有待整理的文件，有就按 [import-routing](agent/guidelines/import-routing.md) 处理。

## 硬规则

1. **不直接删除任何文件。** 删除要先得到用户同意，而且只移进 `_delete/`（保留原路径，并在 `_delete/README.md` 登记）。只有用户明确要求清空时，才真正删除。
2. **`agent/` 之外是人的空间**：新增可以直接做；修正要留记录；重组先提方案；删除只提建议。详见 [workspace-maintenance](agent/guidelines/workspace-maintenance.md)。
3. **用户手动做的修改和整理优先**，不覆盖，也不改回去。
4. **memory 在检查点增量写，不要等到结束。** 做出决定、产出或整理了文件、解决了一个问题之后，就新建或更新本次会话的 memory；对话已经很长时，先记一笔再继续。具体时机由你判断，规则见 [memory-and-guidelines](agent/guidelines/memory-and-guidelines.md)。会话收尾时，再更新 `agent/PROJECT.md` 的当前状态和 `README.md` 的"当前进展"，然后运行 `python3 agent/tools/scripts/reindex.py`。
5. **文件命名**按 [naming](agent/guidelines/naming.md)，文件名语言用 **{{FILENAME_LANG}}**。目录名一律用英文。

## 目录地图

| 目录 | 放什么 |
|---|---|
{{DIR_MAP}}

表里没有的标准目录，等用到时运行 `python3 agent/tools/scripts/add_dir.py <目录>` 创建，它会同步更新这张表、`README.md` 和 `trellis.json`。约定见 [workspace-maintenance](agent/guidelines/workspace-maintenance.md)。
