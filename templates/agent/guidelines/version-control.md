---
name: version-control
description: git 怎么用：协作 / 成品 / 不用三种模式，模式之间怎么切换，推送前检查，LFS
category: workspace
---

# 版本管理

当前模式记在 `agent/trellis.json` 的 `git.mode`。切换模式后要同步更新这个字段。

## 三种模式

| 模式 | 适合 | 仓库在哪 |
|---|---|---|
| `project` 协作 | 要和别人一起做，整个项目放到 GitHub | 项目根目录，只有一个仓库。应用目录**不能**有自己的 `.git` |
| `app` 成品 | 只发布产品代码 | 应用目录。根目录不是仓库；如果 `git.root_local_repo` 为 true，根目录另有一个只在本地用、并在 `.gitignore` 里忽略应用目录的仓库 |
| `none` | 暂不需要版本管理 | 无 |

`app` 模式下，`git.agent_contrib` 为 true 表示项目开源，并希望别人用 agent 参与贡献。这时应用目录里有一份给贡献者 agent 看的 `AGENTS.md`，要随着产品的运行方式和代码约定一起更新。为 false 时不生成这份文件，产品仓库保持干净。

## 日常规则

- **commit**：在自然的检查点提交，例如一个功能做完、一批文件整理完。提交信息写清楚做了什么。
- **push**：每次推送前都要征得用户同意。
- **推送前检查**：扫一遍要推送的内容里有没有敏感信息，包括 `agent/tools/links.md`、memory、`.env`、各类配置文件里的密钥和 token。发现就停下来告诉用户。
- **私密记忆**：不想让协作者看到的 memory 写进 `agent/memory/_private/`，这个目录在 `.gitignore` 里，reindex 也不会把它编进索引。
- **大文件**：设计源文件和视频用 Git LFS（见 `.gitattributes`）。`git.lfs` 为 false 但出现了超过 50MB 的文件时，建议用户开启 LFS。

## 开启版本管理（从 `none` 开始）

先问用户选哪种模式，然后：
- **project**：`cp agent/tools/templates/gitignore.txt .gitignore && git init`，再做第一次提交。
- **app**：在应用目录里执行 `git init`，并写一个只含 `.DS_Store` 的 `.gitignore`。如果用户也想给文档、设计稿留本地历史，根目录照 project 的做法执行，并在 `.gitignore` 里加一行 `/<app>/`，同时把 `root_local_repo` 设为 true。
- 开源并希望别人用 agent 贡献时，把应用目录 README 里的运行方式和代码约定整理成应用目录下的 `AGENTS.md`，再加一个内容为 `@AGENTS.md` 的 `CLAUDE.md`，并把 `agent_contrib` 设为 true。

最后更新 `trellis.json` 的 `git` 字段。

## 切换模式

这几项操作都涉及历史改写或推送：**先把完整步骤给用户看，用户确认后再执行**。

### 成品 → 协作（把应用仓库并入根仓库，保留提交历史）

1. 确认应用仓库没有未提交的改动，记下它的当前分支名 `<B>`。
2. 把整个应用目录移进 `_delete/`，作为备份，并在 `_delete/README.md` 登记：
   `mv <app> _delete/<app>-repo`
3. 根目录如果还不是仓库就执行 `git init`。确认 `.gitignore` 里有 `_delete/`，并且**删掉** `/<app>/` 这一行（如果有）。提交当前所有内容。
4. 把应用历史并入根仓库：
   `git subtree add --prefix=<app> _delete/<app>-repo <B>`
5. 把 `trellis.json` 改为 `git.mode = "project"`，`root_local_repo = false`。

### 协作 → 成品

先问清楚用户要哪一种：

- **A. 继续协作，同时单独发布产品**：根仓库不动，把应用目录的历史拆成一个分支，推到产品仓库。
  ```
  git subtree split --prefix=<app> -b <app>-release
  git push <产品仓库地址> <app>-release:main
  ```
  以后每次发布都重复这两步。模式仍然是 `project`。
- **B. 彻底转为成品模式**：
  1. `git subtree split --prefix=<app> -b <app>-release`
  2. 在应用目录建仓库，接上拆出来的历史：
     `git -C <app> init && git -C <app> fetch .. <app>-release && git -C <app> reset FETCH_HEAD`
  3. 根仓库停止追踪应用目录：`git rm -r --cached <app>`，并在 `.gitignore` 里加上 `/<app>/`，然后提交。用户如果不想保留根仓库，就把根目录的 `.git` 移进 `_delete/`。
  4. 更新 `trellis.json`：`mode = "app"`，`root_local_repo` 按是否保留根仓库设置。

### 已有的代码自带 `.git`

- 协作模式：把它当成一个应用仓库，按"成品 → 协作"的流程并入根仓库。
- 成品模式：把它整体移进来作为应用目录，不要动它的 `.git`。
