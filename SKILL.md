---
name: trellis
description: 把一个文件夹整理成"人与 agent 协作"的项目结构（trellis），并持续维护它。用于：开启任何与 agent 合作的新项目、把现有文件夹整理为项目文件夹、搭项目脚手架/骨架、初始化 AGENTS.md / CLAUDE.md / agent 目录（guidelines、memory、tools）；也用于日常维护：整理 import 目录或根目录里乱丢的文件、项目体检、重建 agent 索引、把旧项目的规则升级到新版 trellis。触发词包括 /trellis、/trellis tidy、/trellis reindex、/trellis upgrade、"初始化项目"、"整理项目文件夹"、"整理一下 import"、"set up this project for agents"。
---

# Trellis

Trellis 是一个让项目沿着它生长的棚架：先定结构，内容随项目推进自然沉淀。它有四种模式：

| 模式 | 触发 | 做什么 |
|---|---|---|
| **init** | `/trellis`，或用户要新建/整理项目文件夹 | 生成入口文件、`agent/` 目录、hooks、版本管理和产出目录，迁移已有文件 |
| **tidy** | `/trellis tidy`，或用户要整理/体检 | 整理 `import/` 和根目录，检查链接、README、版本、重组、`_delete/`、git 状态 |
| **reindex** | `/trellis reindex`，或改动了 agent/ 下的文件 | 重新生成 `agent/` 下三个 INDEX.md |
| **upgrade** | `/trellis upgrade` | 把项目里的规则、脚本、模板、hooks 和最新版 trellis 做三方比较并合并 |

本 skill 的路径记为 `$SKILL`（即本文件所在目录）。脚本只用 Python 标准库。

如果目标文件夹里已有 `agent/trellis.json`，说明已经是 trellis 项目：用户说 `/trellis` 时默认走 **tidy**，不要重新 init。

---

## 模式一：init

### 1. 确定目标文件夹并扫描
目标默认是当前工作目录；用户指定了别的路径就用那个。先只读扫描：

```bash
python3 "$SKILL/scripts/scan.py" <目标文件夹>
```

非 trellis 项目会输出根目录现状（每项的文件数、大小、是否 git 仓库）。

### 2. 收集信息：先推断，只问必要的

信息来源按优先级：**用户在对话里说过的** → **目录里已有的内容**（文件夹名、README、需求文档、代码仓库的 package.json 或 git remote、文件类型分布）→ **合理默认值**。

对下面每一项，先尝试从这些来源推断：
- 能确定的，直接用。
- 推断得出但不确定的，列出来让用户一眼确认。
- 推断不出、而且现在就需要的，才问。

所有要问的问题合成一张提问卡片，一次问完，不要分多轮。

**现在必须定下来的**（会影响生成哪些文件）：
- 项目名（默认用文件夹名）
- 项目类型，决定建哪些目录（从已有文件的类型推断）
- 软件类项目的应用目录名（默认取 package.json 里的 name 或文件夹名，转成 kebab-case）

**可以以后再补的**（不确定就先用默认值，在 PROJECT.md 里标成"待补充"）：
- 一句话描述、目标、受众、交付物规格：不知道就留空并标为待补充，**不要编**。
- 文件名语言：默认跟用户对话用的语言一致。
- 版本管理：只有软件类项目，或者用户提到协作、GitHub、开源时才问，其他情况默认 `none`，以后随时可以开启。
- LFS：等真的出现大文件时再提。

之后对话中得知新信息时，按 `workspace-maintenance.md` 的"项目信息补充"一节更新：补全 PROJECT.md，需要的话用 `add_dir.py` 加目录，或者切换版本管理模式。

各项的取值参考：
- **项目类型**，决定建哪些产出目录（可多选，用户也可以直接点名目录）：

  | 类型 | 默认目录 |
  |---|---|
  | 调研 | research, docs, deliverables |
  | 写作 / 文档 | docs, research, deliverables |
  | 设计 | design, research, deliverables |
  | 软件 / App / 游戏 | `<app-slug>`, design, docs, deliverables |

  `agent/` 和 `import/` 总是创建。`_delete/` 第一次需要时才建。
- **文件名语言**：zh 或 en（目录名永远是英文）
- 软件类项目：**应用目录名**（项目英文 slug，小写 kebab-case）
- **版本管理**：
  - `project` 协作：要和别人一起做、整个项目放到 GitHub，仓库在根目录；
  - `app` 只发布成品：仓库只在应用目录（只有软件类项目能选）；
  - `none` 暂不需要。
- 选 `app` 时再问两个问题：
  - 项目是否开源，并希望别人用 agent 参与贡献？是的话加 `--agent-contrib`，在应用目录生成给贡献者 agent 看的说明；只给人用就不加。
  - 文档、设计稿要不要也有本地的版本历史？要的话加 `--root-local-repo`，根目录另建一个忽略应用目录的本地仓库。
- 有 design 目录且用 git 时：要不要用 Git LFS 管理大文件（`--lfs`）？

### 3. 生成结构
```bash
python3 "$SKILL/scripts/init.py" <目标文件夹> \
  --name "项目名" [--one-liner "一句话描述"] --lang zh \
  --dirs research,docs,design,app,deliverables --app-slug my-app \
  --git project|app|none [--agent-contrib] [--root-local-repo] [--lfs]
```
- 只创建、不覆盖：已存在的同名文件会跳过并报告。跳过的 `AGENTS.md`、`CLAUDE.md`、`README.md`、`.claude/settings.json` 需要你手动合并（保留用户原内容，补进 trellis 的部分），合并前先告诉用户。
- 会创建软链接，让项目专属的 skill 和 subagent 能被识别：
  - `.claude/skills` 和 `.agents/skills`（Codex）→ `agent/tools/skills`
  - `.claude/agents` → `agent/tools/agents`
- 会同时生成 Claude Code 的 `.claude/settings.json` 和 Codex 的 `.codex/hooks.json`（见下文"规则怎么保证执行"）。
- 会把 `scan.py`、`reindex.py`、`guard_delete.py`、`add_dir.py` 和各目录 README 模板复制进 `agent/tools/`，并生成初始索引。项目从此不依赖本 skill 也能维护自己。

### 4. 迁移已有文件（目标文件夹原本有内容时）
1. 按 `agent/guidelines/import-routing.md` 的分发规则和 `naming.md` 的命名标准，列出迁移计划表：`原路径 → 新路径`。
2. 拿不准去向的，计划为"重命名后放进 `import/`"，并附上要问用户的问题。
3. 把整张表给用户确认。确认后只用 `mv` 移动，**不删除任何东西**。
4. 已有的代码仓库（有 `.git`、`package.json` 等）整体移动，不拆开、不改名：
   - `app` 模式：直接把它作为应用目录（init 生成的空应用目录先移进 `_delete/`，或者把 README 并进去）；
   - `project` 模式：按 `agent/guidelines/version-control.md` 的"成品 → 协作"流程，把它的历史并入根仓库。先给用户看步骤。

### 5. 填内容
- 把已知信息填进 `agent/PROJECT.md`（目标、范围、交付物、当前状态）和根目录 `README.md`。未知的留空，不要编。
- 选了 `--agent-contrib` 时，尽量填好应用目录 `AGENTS.md` 里的运行方式和代码约定。
- 项目语言是英文时，把生成的人类可读文件（README 们）翻成英文。

### 6. 写第一条 memory 并建索引
- 按 `agent/memory/_template.md` 写 `agent/memory/<yymmdd>-project-trellis-init.md`，迁移表放进"文件整理记录"一节。
- 运行 `python3 agent/tools/scripts/reindex.py`。

### 7. 汇报
告诉用户：
- 建了哪些目录，迁移了什么，还有哪些文件待确认；
- 版本管理用的是哪种模式；
- 怎么和 agent 协作：丢文件进 `import/`、说"记成规则"、说 `/trellis tidy`；
- 哪些信息还标着"待补充"，等以后在对话中补上；
- 用 Codex 的话，第一次打开项目时要在 Codex 里执行 `/hooks`，审核并信任 trellis 的 hooks，否则 hooks 不会运行。hooks 文件以后有改动（比如 upgrade 之后），需要重新信任一次。

---

## 模式二：tidy

```bash
python3 agent/tools/scripts/scan.py .
```
（项目里没有脚本时用 `$SKILL/scripts/scan.py`。）scan 只读，输出一份体检报告。按报告逐项处理，规则一律以项目内的 `agent/guidelines/` 为准（项目可能已经改过默认规则）：

1. **根目录杂项** → 移进 `import/`。
2. **未登记的标准目录** → 运行 `python3 agent/tools/scripts/add_dir.py <目录>`，它会同时补登记、补目录地图和 README。
3. **`import/` 里的文件** → 按 `import-routing.md` 重命名并分发。拿不准的只重命名、留在 `import/`，登记进 `import/README.md`，所有问题攒成一条消息一次问完。
4. **命名不合规** → 只处理 `import/` 里的文件；其他目录的文件改名要先问用户（改名可能打断引用）。
5. **失效链接** → 能确定新位置的直接修，修完记一笔；不能确定的列给用户。
6. **旧版本未归档** → 移进同目录的 `_archive/`。
7. **超过阈值的目录** → 提出分类方案，等用户确认后再迁移。
8. **缺 README 或 README 过时** → 补上或更新（模板在 `agent/tools/templates/`）。
9. **git 状态与模式不符** → 按 `version-control.md` 给出修复步骤，等用户确认后执行。
10. **`_delete/` 体积超限** → 提醒用户，不自动清理。
11. **建议删除的东西**（重复文件、明显废弃的文件）→ 只列出建议；用户同意后移进 `_delete/`。
12. 结束时：把"原名 → 新路径"表写进本次会话的 memory，运行 reindex。

## 模式三：reindex

```bash
python3 agent/tools/scripts/reindex.py
```
它读取 `agent/guidelines/`、`agent/memory/`（不含 `_private/`）、`agent/tools/` 下各文件的 frontmatter，重写三个 `INDEX.md`，并报告缺少 description 的文件。缺失的 frontmatter 由你补上后再跑一次。

## 模式四：upgrade

trellis 本身更新以后，已有的项目不会自动跟着变。每个项目的规则是一份副本，可以各自调整。upgrade 用 init 时记下的基线（`trellis.json` 的 `base`）做三方比较：

```bash
python3 "$SKILL/scripts/upgrade.py" <项目>                  # 只读报告
python3 "$SKILL/scripts/upgrade.py" <项目> --diff <路径>     # 项目版本 vs 最新模板
python3 "$SKILL/scripts/upgrade.py" <项目> --apply          # 应用"可安全更新"和"新增"
python3 "$SKILL/scripts/upgrade.py" <项目> --resolve <路径>  # 冲突合并完后标记
```

1. 先跑报告，把结果告诉用户：
   - **可安全更新**：项目没改过、模板有新版；
   - **新增**：新版模板里才有的文件；
   - **冲突**：项目改过、模板也有新版；
   - **项目自定义**：项目改过、模板没变；
   - **无基线**：项目里原本就有同名文件。
2. 用户同意后执行 `--apply`。
3. **冲突**和**无基线**的文件逐个看 `--diff`，把模板的改进合并进项目版本，同时保留项目自己改过的部分；每一处都给用户确认，然后 `--resolve`。
4. 项目自定义过的文件不要动。
5. 在 memory 里记一笔这次升级。

upgrade 只管规则、脚本、模板和 hooks。`AGENTS.md`、`README.md`、`PROJECT.md` 这类已经写进项目内容的文件不在比较范围内。如果新版模板的入口文件有结构上的变化，由你读一下模板，向用户提议怎么改。

---

## 规则怎么保证执行

日常规则（检查 import、写 memory、更新 README、四档权限、`_archive/`、`_delete/`、git）写在每个项目的 `AGENTS.md` 和 `agent/guidelines/` 里，不写在本 skill 里。在 Claude Code 里打开项目根目录时，会自动加载 `CLAUDE.md` → `AGENTS.md`；Codex、Cursor 等工具也会读 `AGENTS.md`。

文字规则是指令，不是强制。关键的几条由 hooks 兜底，Claude Code 用 `.claude/settings.json`，Codex 用 `.codex/hooks.json`，两份做的事情一样：

| hook | 时机 | 作用 |
|---|---|---|
| `scan.py --brief` | 会话开始、恢复 | 有待处理事项时注入一行提醒（import、根目录、索引、git、`_delete` 体积）；没有就什么都不输出 |
| `scan.py --brief --after-compact` | 上下文压缩之后 | 提醒 agent 核对本次会话的进展是否已经写进 memory |
| `guard_delete.py` | 每次执行 Bash 命令前 | 拒绝项目内的删除命令，并提示改为移进 `_delete/`；`git rm` 和项目外的路径不拦 |

两边的差别：
- **删除 `_delete/` 里的东西时怎么确认**：Claude Code 会弹出确认窗口，由用户批准。Codex 不支持弹窗确认，所以守卫先拒绝，并提示 agent 去问用户；用户在对话里明确同意后，agent 在命令末尾加上 `# trellis:confirmed` 再执行才会放行。这一层要靠 agent 遵守，弱于 Claude Code 的弹窗。
- **找项目根目录**：Codex 没有项目根目录变量，hook 命令会从当前目录逐级向上找 `agent/trellis.json`，所以在子目录里开会话也能生效。
- **信任**：Codex 的项目 hooks 必须先在 `/hooks` 里信任才会运行，内容有改动后要重新信任。
