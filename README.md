# trellis

> A skill for Claude Code and Codex that turns any folder into a project structured for human–agent collaboration, then keeps it tidy as the project grows. The docs and templates are in Chinese.

**trellis**（棚架）是一个 Claude Code / Codex skill。它把任意文件夹整理成"人与 agent 协作"的项目结构，并在项目推进中持续维护：先定好结构，内容随项目自然生长。

## 它会搭出什么

```
<项目>/
├── AGENTS.md          # agent 入口：简介、目录地图、必读顺序、硬规则
├── CLAUDE.md          # 只有一行 @AGENTS.md
├── README.md          # 给人看的项目首页
├── agent/
│   ├── PROJECT.md     # 项目简报和当前状态
│   ├── guidelines/    # 长期规则（带索引）
│   ├── memory/        # 以会话为单位的记忆 yymmdd-three-words.md（带索引）
│   └── tools/         # 项目专属的 skill、subagent、脚本、线上工具
├── import/            # 收件箱：随手丢文件，agent 负责整理
└── 按需创建：research/ docs/ design/ <app>/ deliverables/ _delete/
```

## 核心约定

- **按需创建**：除了 `agent/` 和 `import/`，其他目录都在用到时才建。
- **import 收件箱**：文件丢进 `import/` 或项目根目录，agent 会按命名标准改名并放到对应位置；拿不准的留在原地，攒在一起问你。
- **不直接删除**：删除只是移进 `_delete/`，保留原路径并登记；只有你明确说要清空时才真正删除。
- **人类可读**：每个产出目录有一个用人话写的 README；文件统一命名为 `yymmdd-描述-v01.ext`；旧版本放进同目录的 `_archive/`。
- **memory 增量记录**：由 agent 在检查点（做出决定、产出文件等之后）写入，不等到会话结束才记，避免上下文过长或会话中断时漏记。
- **版本管理三种模式**：`project` 协作（整个项目一个仓库）、`app` 只发布成品（仓库只在应用目录）、`none`；模式之间可以互相切换，切换时保留提交历史。
- **规则住在项目里**：init 之后，规则、脚本和 hooks 都复制进了项目，不依赖这个 skill 也能运转；`/trellis upgrade` 用三方比较把新版规则合并进旧项目，不会覆盖项目自己改过的部分。

## Hooks（Claude Code 和 Codex 都支持）

| 时机 | 作用 |
|---|---|
| 会话开始 | 有待处理事项（import、根目录杂项、过期索引、git 状态）时注入一行提醒 |
| 上下文压缩后 | 提醒 agent 把本次会话的进展补写进 memory |
| 执行 Bash 命令前 | 拦截项目内的删除命令。清空 `_delete/` 时：Claude Code 弹窗让你确认；Codex 要求你在对话中同意后，agent 在命令末尾加确认标记才放行 |

Codex 要求项目里的 hooks 先经过信任：第一次打开项目时在 Codex 里执行 `/hooks`。

## 安装

需要 Python 3（只用标准库）。

```bash
git clone https://github.com/Jin-Q-SD/trellis.git ~/.claude/skills/trellis
```

在 Codex 中使用：

```bash
mkdir -p ~/.agents/skills && ln -s ~/.claude/skills/trellis ~/.agents/skills/trellis
```

## 使用

| 命令 | 作用 |
|---|---|
| `/trellis` | 初始化当前文件夹（已经是 trellis 项目时，改为执行 tidy） |
| `/trellis tidy` | 整理 import 和根目录，并做一次全面体检 |
| `/trellis reindex` | 重建 `agent/` 下的索引 |
| `/trellis upgrade` | 把项目的规则、脚本和 hooks 升级到最新版 |

也可以直接用自然语言触发，例如"初始化这个项目"、"整理一下 import"。

## 文件说明

- `SKILL.md`：skill 的入口，写明四种模式的流程。
- `scripts/`：`init`、`scan`（只读体检，也给 hooks 用）、`reindex`、`add_dir`、`guard_delete`（删除守卫）、`upgrade`。
- `templates/`：入口文件、默认规则、各目录 README、hooks 配置的模板。

## License

MIT
