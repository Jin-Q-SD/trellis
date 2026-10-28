#!/usr/bin/env python3
"""Trellis init：在目标文件夹里生成入口文件、agent/ 目录、hooks 和选定的产出目录（只创建，不覆盖）。"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import OrderedDict

TRELLIS_VERSION = "1.2"
SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(SKILL, "templates")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_dir import DIRS  # noqa: E402  标准产出目录的唯一定义

ORDER = ["research", "docs", "design", "app", "deliverables"]
LANG_LABEL = {"zh": "中文", "en": "英文（小写 kebab-case）"}
SCRIPTS = ["reindex.py", "scan.py", "guard_delete.py", "add_dir.py"]


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def render(text, ctx):
    for k, v in ctx.items():
        text = text.replace("{{%s}}" % k, v)
    return text


def tpl(src, ctx):
    with open(os.path.join(TPL, src), encoding="utf-8") as f:
        return render(f.read(), ctx)


def ctx_from_config(cfg):
    """upgrade 用：从 trellis.json 还原渲染受管文件所需的变量。"""
    return {
        "PROJECT_NAME": cfg["project_name"],
        "FILENAME_LANG": LANG_LABEL[cfg.get("filename_lang", "zh")],
        "APP_SLUG": cfg.get("app_dir") or "",
    }


LINKS = OrderedDict([
    (".claude/skills", "../agent/tools/skills"),
    (".claude/agents", "../agent/tools/agents"),
    (".agents/skills", "../agent/tools/skills"),  # Codex 读取项目 skill 的位置
])


def managed_files(ctx):
    """受 upgrade 追踪的文件：规则、脚本、模板、hooks。返回 {项目内相对路径: 内容}。"""
    files = OrderedDict()
    gdir = os.path.join(TPL, "agent", "guidelines")
    for f in sorted(os.listdir(gdir)):
        files["agent/guidelines/" + f] = tpl("agent/guidelines/" + f, ctx)
    files["agent/memory/_template.md"] = tpl("agent/memory/_template.md", ctx)
    for s in SCRIPTS:
        with open(os.path.join(SKILL, "scripts", s), encoding="utf-8") as fh:
            files["agent/tools/scripts/" + s] = fh.read()
    tdir = os.path.join(TPL, "dirs")
    for f in sorted(os.listdir(tdir)):
        with open(os.path.join(tdir, f), encoding="utf-8") as fh:
            files["agent/tools/templates/" + f] = fh.read()  # 不渲染：add_dir 用到时再填
    files["agent/tools/templates/gitignore.txt"] = tpl("root/gitignore", ctx)
    files[".claude/settings.json"] = tpl("root/settings.json", ctx)
    files[".codex/hooks.json"] = tpl("root/codex-hooks.json", ctx)
    return files


def init_links():
    return list(LINKS.items())


class Writer:
    def __init__(self, root):
        self.root, self.created, self.skipped = root, [], []

    def rel(self, p):
        return os.path.relpath(p, self.root)

    def write(self, relpath, content):
        p = os.path.join(self.root, relpath)
        if os.path.lexists(p):
            self.skipped.append(relpath)
            return False
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        if relpath.endswith(".py"):
            os.chmod(p, 0o755)
        self.created.append(relpath)
        return True

    def mkdir(self, relpath):
        p = os.path.join(self.root, relpath)
        if not os.path.isdir(p):
            os.makedirs(p)
            self.created.append(relpath + "/")

    def symlink(self, relpath, target):
        p = os.path.join(self.root, relpath)
        if os.path.lexists(p):
            self.skipped.append(relpath + "（已存在，未建软链接）")
            return
        os.makedirs(os.path.dirname(p), exist_ok=True)
        os.symlink(target, p)
        self.created.append("%s -> %s" % (relpath, target))

    def git_init(self, relpath):
        p = os.path.join(self.root, relpath)
        if os.path.isdir(os.path.join(p, ".git")):
            self.skipped.append(os.path.join(relpath, ".git") + "（已是 git 仓库）")
            return
        subprocess.run(["git", "init", "-q", p], check=True)
        self.created.append(os.path.normpath(os.path.join(relpath, ".git")) + "/")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("target")
    p.add_argument("--name", required=True)
    p.add_argument("--one-liner", default="")
    p.add_argument("--lang", choices=["zh", "en"], default="zh")
    p.add_argument("--dirs", default="", help="逗号分隔：research,docs,design,app,deliverables")
    p.add_argument("--app-slug", default="")
    p.add_argument("--git", choices=["project", "app", "none"], default="none",
                   help="project=根目录一个仓库（协作）；app=仓库只在应用目录（只发布成品）；none=不用 git")
    p.add_argument("--root-local-repo", action="store_true", help="app 模式下，根目录另建只在本地用、忽略应用目录的仓库")
    p.add_argument("--agent-contrib", action="store_true", help="app 模式下，在应用目录生成给贡献者 agent 的 AGENTS.md/CLAUDE.md")
    p.add_argument("--lfs", action="store_true", help="写 .gitattributes，用 Git LFS 管理设计源文件和视频")
    a = p.parse_args()

    root = os.path.abspath(a.target)
    if not os.path.isdir(root):
        sys.exit("目标文件夹不存在：%s" % root)
    if os.path.exists(os.path.join(root, "agent", "trellis.json")):
        sys.exit("已经是 trellis 项目（agent/trellis.json 已存在），请改用 tidy 或 upgrade。")

    dirs = [d.strip() for d in a.dirs.split(",") if d.strip()]
    unknown = [d for d in dirs if d not in DIRS]
    if unknown:
        sys.exit("未知目录：%s（可选：%s）" % (", ".join(unknown), ", ".join(ORDER)))
    if "app" in dirs and not a.app_slug:
        sys.exit("选了 app 时必须提供 --app-slug")
    if a.git == "app" and "app" not in dirs:
        sys.exit("--git app 需要应用目录（--dirs 里包含 app）")
    if (a.root_local_repo or a.agent_contrib) and a.git != "app":
        sys.exit("--root-local-repo 和 --agent-contrib 只用于 --git app")
    dirs = [d for d in ORDER if d in dirs]
    real = lambda d: a.app_slug if d == "app" else d

    today = datetime.date.today()
    agent_rows = ["| `agent/` | agent 的规则（guidelines）、记忆（memory）、工具（tools）和项目简报 |",
                  "| `import/` | 收件箱：用户丢进来的文件，等待整理 |"]
    human_rows = ["| `import/` | 有文件要给 agent 就丢这里 |"]
    for d in dirs:
        agent_rows.append("| `%s/` | %s |" % (real(d), DIRS[d][0]))
        human_rows.append("| `%s/` | %s |" % (real(d), DIRS[d][1]))
    human_rows.append("| `agent/` | agent 的工作区：规则、记忆、工具。一般不用看 |")

    ctx = {
        "PROJECT_NAME": a.name,
        "ONE_LINER": a.one_liner or "（待补充一句话描述）",
        "FILENAME_LANG": LANG_LABEL[a.lang],
        "DATE": today.isoformat(),
        "DIR_MAP": "\n".join(agent_rows),
        "DIR_MAP_HUMAN": "\n".join(human_rows),
        "APP_SLUG": a.app_slug,
    }
    w = Writer(root)

    # 入口文件和一次性文件（之后由项目自己维护，upgrade 不追踪）
    for f in ["AGENTS.md", "CLAUDE.md", "README.md"]:
        w.write(f, tpl("root/" + f, ctx))
    w.write("agent/PROJECT.md", tpl("agent/PROJECT.md", ctx))
    w.write("agent/tools/links.md", tpl("agent/tools/links.md", ctx))
    for sub in ["skills", "agents", "scripts"]:
        w.mkdir("agent/tools/" + sub)
    w.mkdir("agent/memory")

    # 受管文件（upgrade 会用 base 哈希做三方比较）
    base = {}
    for relpath, content in managed_files(ctx).items():
        if w.write(relpath, content):
            base[relpath] = sha(content)
    for hooks_file, src in ((".claude/settings.json", "settings.json"), (".codex/hooks.json", "codex-hooks.json")):
        if hooks_file in w.skipped:
            print("⚠ %s 已存在：trellis 的 hooks 没有写入，需要手动合并（参考 %s）。"
                  % (hooks_file, os.path.join(TPL, "root", src)))

    for link, target in init_links():
        w.symlink(link, target)

    # 产出目录
    w.write("import/README.md", tpl("dirs/import.md", ctx))
    for d in dirs:
        w.write(real(d) + "/README.md", tpl("dirs/%s.md" % d, ctx))

    # 版本管理
    ignore = tpl("root/gitignore", ctx)
    if a.git == "project":
        w.write(".gitignore", ignore)
        w.git_init(".")
    elif a.git == "app":
        app = a.app_slug
        w.write(app + "/.gitignore", ".DS_Store\n")
        w.git_init(app)
        if a.agent_contrib:
            w.write(app + "/AGENTS.md", tpl("app/AGENTS.md", ctx))
            w.write(app + "/CLAUDE.md", "@AGENTS.md\n")
        if a.root_local_repo:
            w.write(".gitignore", ignore + "/%s/\n" % app)
            w.git_init(".")
    if a.lfs and a.git != "none":
        target = a.app_slug + "/.gitattributes" if (a.git == "app" and not a.root_local_repo) else ".gitattributes"
        w.write(target, tpl("root/gitattributes", ctx))
        if not shutil.which("git-lfs"):
            print("⚠ 没有检测到 git-lfs：请用户安装（brew install git-lfs）后运行 git lfs install。")

    config = OrderedDict([
        ("trellis", TRELLIS_VERSION),
        ("project_name", a.name),
        ("created", today.isoformat()),
        ("filename_lang", a.lang),
        ("app_dir", a.app_slug or None),
        ("dirs", ["import"] + [real(d) for d in dirs]),
        ("git", OrderedDict([("mode", a.git), ("root_local_repo", a.root_local_repo),
                             ("agent_contrib", a.agent_contrib), ("lfs", a.lfs)])),
        ("restructure_threshold", 12),
        ("delete_warn_mb", 1024),
        ("base", base),
    ])
    w.write("agent/trellis.json", json.dumps(config, ensure_ascii=False, indent=2) + "\n")

    subprocess.run([sys.executable, os.path.join(root, "agent", "tools", "scripts", "reindex.py"), root],
                   check=False, stdout=subprocess.DEVNULL)

    print("## trellis init 完成（v%s）：%s\n" % (TRELLIS_VERSION, root))
    print("### 已创建 (%d)" % len(w.created))
    for c in w.created:
        print("- " + c)
    if w.skipped:
        print("\n### 已跳过（已存在，未覆盖）(%d)" % len(w.skipped))
        for s in w.skipped:
            print("- " + s)
        print("\n跳过的 AGENTS.md / CLAUDE.md / README.md / settings.json 需要手动合并 trellis 的内容。")
    print("\n已生成初始索引。下一步：迁移已有文件（先给用户确认计划）→ 填 PROJECT.md / README.md → 写第一条 memory → 运行 agent/tools/scripts/reindex.py")


if __name__ == "__main__":
    main()
