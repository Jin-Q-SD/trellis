#!/usr/bin/env python3
"""Trellis scan：只读体检，列出待整理的文件、命名问题、失效链接、未归档旧版本、需重组的目录、git 状态等。"""
import json
import os
import re
import sys
from urllib.parse import unquote

SKIP_DIRS = {".git", ".claude", "node_modules", ".venv", "venv", "__pycache__", ".next", "dist", "build"}
MANAGED = ["research", "docs", "design", "deliverables"]
STD_ROOT = {"AGENTS.md", "CLAUDE.md", "README.md", "agent", "import", "_delete"}
DATE_RE = re.compile(r"^\d{6}-")
VER_RE = re.compile(r"^(.*)-v(\d{2,})(\.[^.]+)?$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
COMPACT_NOTE = ("[trellis] 上下文刚被压缩。先检查本次会话的进展（决定、产出、文件整理）是否已经写进 agent/memory/ "
                "里本次会话的记录；没有就现在补写或更新，再继续手上的工作。")


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%.0f%s" % (n, u)
        n /= 1024.0
    return "%.1fTB" % n


def tree_size(p):
    if os.path.isfile(p) or os.path.islink(p):
        try:
            return 1, os.lstat(p).st_size
        except OSError:
            return 1, 0
    count = size = 0
    for dp, dn, fn in os.walk(p):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            try:
                size += os.lstat(os.path.join(dp, f)).st_size
                count += 1
            except OSError:
                pass
    return count, size


def preview(root):
    print("## 非 trellis 项目：根目录现状\n")
    print("`%s`\n" % root)
    entries = sorted(os.listdir(root))
    if not entries:
        print("（空文件夹）")
        return
    print("| 项 | 类型 | 文件数 | 大小 |\n|---|---|---|---|")
    for e in entries:
        p = os.path.join(root, e)
        c, s = tree_size(p)
        kind = "目录" if os.path.isdir(p) else "文件"
        if os.path.isdir(os.path.join(p, ".git")):
            kind += "（git 仓库）"
        print("| %s | %s | %d | %s |" % (e, kind, c, human(s)))


def walk_files(base, skip=()):
    for dp, dn, fn in os.walk(base):
        dn[:] = sorted(d for d in dn if d not in SKIP_DIRS and os.path.join(dp, d) not in skip)
        for f in sorted(fn):
            if not f.startswith("."):
                yield dp, f


def git_issues(root, cfg):
    g = cfg.get("git") or {}
    if isinstance(g, bool):
        g = {"mode": "project" if g else "none"}
    mode, app = g.get("mode", "none"), cfg.get("app_dir")
    root_git = os.path.isdir(os.path.join(root, ".git"))
    app_git = bool(app) and os.path.isdir(os.path.join(root, app, ".git"))
    ignore = ""
    if os.path.isfile(os.path.join(root, ".gitignore")):
        with open(os.path.join(root, ".gitignore"), encoding="utf-8") as f:
            ignore = f.read()
    app_ignored = bool(app) and re.search(r"^/?%s/?\s*$" % re.escape(app), ignore, re.M)
    out = []
    if mode == "project":
        if not root_git:
            out.append("模式是 project，但根目录不是 git 仓库")
        if app_git:
            out.append("模式是 project，但应用目录 %s/ 里有自己的 .git（嵌套仓库）：按 version-control.md 的“成品 → 协作”流程并入根仓库" % app)
        if root_git and "_delete" not in ignore:
            out.append(".gitignore 里没有 _delete/")
    elif mode == "app":
        if not app_git:
            out.append("模式是 app，但应用目录 %s/ 不是 git 仓库" % app)
        if root_git and not g.get("root_local_repo"):
            out.append("模式是 app，但根目录也有 .git：确认是否应把 git.root_local_repo 设为 true，或改用 project 模式")
        if root_git and not app_ignored:
            out.append("根目录仓库没有在 .gitignore 里忽略 /%s/（会形成嵌套仓库）" % app)
    else:
        if root_git or app_git:
            out.append("模式是 none，但发现了 git 仓库：更新 agent/trellis.json 的 git.mode")
    return out


def report(root, cfg, brief=False):
    app = cfg.get("app_dir")
    threshold = int(cfg.get("restructure_threshold", 12))
    J = lambda *x: os.path.join(root, *x)
    app_path = J(app) if app else None
    skip_tree = {p for p in (app_path, J("_delete"), J(".git")) if p}
    rep = {}

    allowed = STD_ROOT | set(cfg.get("dirs", [])) | ({app} if app else set())
    rest = [e for e in sorted(os.listdir(root)) if not e.startswith(".") and e not in allowed]
    rep["unregistered_dirs"] = [e for e in rest if e in MANAGED and os.path.isdir(J(e))]
    rep["root_strays"] = [e for e in rest if e not in rep["unregistered_dirs"]]

    items = []
    try:
        with open(J("import", "README.md"), encoding="utf-8") as fh:
            pending_text = fh.read()
    except OSError:
        pending_text = ""
    if os.path.isdir(J("import")):
        for e in sorted(os.listdir(J("import"))):
            if e.startswith(".") or e == "README.md":
                continue
            c, s = tree_size(J("import", e))
            items.append({"name": e, "dir": os.path.isdir(J("import", e)), "files": c, "size": human(s),
                          "named_ok": bool(DATE_RE.match(e)), "pending": e in pending_text})
    rep["import"] = items

    stale_idx = []
    for sub in ("guidelines", "memory", "tools"):
        idx = J("agent", sub, "INDEX.md")
        if not os.path.isfile(idx):
            stale_idx.append(sub + "（无 INDEX.md）")
            continue
        t0 = os.path.getmtime(idx)
        for dp, f in walk_files(J("agent", sub)):
            if f != "INDEX.md" and os.path.getmtime(os.path.join(dp, f)) > t0:
                stale_idx.append(sub)
                break
    rep["stale_index"] = stale_idx

    if os.path.isdir(J("_delete")):
        c, s = tree_size(J("_delete"))
        if os.path.isfile(J("_delete", "README.md")):
            c, s = c - 1, s - os.path.getsize(J("_delete", "README.md"))
        rep["delete"] = {"files": c, "size": human(s), "over_limit": s > cfg.get("delete_warn_mb", 1024) * 1024 * 1024}

    rep["git"] = git_issues(root, cfg)
    if brief:
        return rep

    bad = []
    for d in MANAGED:
        if not os.path.isdir(J(d)):
            continue
        if d == "deliverables":
            for e in sorted(os.listdir(J(d))):
                p = J(d, e)
                if os.path.isdir(p) and not e.startswith(("_", ".")) and not DATE_RE.match(e):
                    bad.append(os.path.relpath(p, root) + "/")
            continue
        for dp, f in walk_files(J(d)):
            if f == "README.md" or "/_archive" in dp.replace(os.sep, "/"):
                continue
            if not DATE_RE.match(f):
                bad.append(os.path.relpath(os.path.join(dp, f), root))
    rep["naming"] = bad

    need = ["import"] + [d for d in cfg.get("dirs", []) if d != "import"] + rep["unregistered_dirs"] \
        + (["_delete"] if os.path.isdir(J("_delete")) else [])
    rep["missing_readme"] = [d for d in need if os.path.isdir(J(d)) and not os.path.isfile(J(d, "README.md"))]
    rep["missing_dirs"] = [d for d in cfg.get("dirs", []) if not os.path.isdir(J(d))]

    crowded = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS and not d.startswith(".") and os.path.join(dp, d) not in skip_tree]
        r = os.path.relpath(dp, root).replace(os.sep, "/")
        if r in (".", "agent/memory") or "/_archive" in "/" + r or r.startswith("deliverables/"):
            continue
        n = len([f for f in fn if not f.startswith(".") and f != "README.md"])
        if n > threshold:
            crowded.append({"dir": r, "files": n})
    rep["crowded"] = crowded

    stale = []
    for d in MANAGED:
        if not os.path.isdir(J(d)):
            continue
        for dp, dn, fn in os.walk(J(d)):
            dn[:] = [x for x in dn if x != "_archive" and x not in SKIP_DIRS]
            groups = {}
            for f in fn:
                m = VER_RE.match(f)
                if m:
                    groups.setdefault((m.group(1), m.group(3) or ""), []).append((int(m.group(2)), f))
            for vs in groups.values():
                if len(vs) > 1:
                    vs.sort()
                    stale += [os.path.relpath(os.path.join(dp, f), root) for _, f in vs[:-1]]
    rep["unarchived_versions"] = sorted(stale)

    broken = []
    for dp, f in walk_files(root, skip=skip_tree):
        if not f.endswith(".md"):
            continue
        p = os.path.join(dp, f)
        try:
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        for target in LINK_RE.findall(text):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
                continue
            t = unquote(target.split("#")[0])
            if t and not os.path.exists(os.path.normpath(os.path.join(dp, t))):
                broken.append({"file": os.path.relpath(p, root), "link": target})
    rep["broken_links"] = broken
    return rep


def print_brief(rep, after_compact):
    parts = []
    if rep["root_strays"]:
        parts.append("根目录有 %d 项杂项，要移进 import/" % len(rep["root_strays"]))
    if rep["unregistered_dirs"]:
        parts.append("未登记的标准目录（用 add_dir.py 补登记）：" + "、".join(rep["unregistered_dirs"]))
    todo = [i for i in rep["import"] if not i["pending"]]
    pend = [i for i in rep["import"] if i["pending"]]
    if todo:
        parts.append("import/ 有 %d 项待整理" % len(todo))
    if pend:
        parts.append("import/ 有 %d 项在等用户确认，找合适的时机再问" % len(pend))
    if rep["stale_index"]:
        parts.append("索引需要更新（%s），运行 agent/tools/scripts/reindex.py" % "、".join(rep["stale_index"]))
    if rep.get("delete", {}).get("over_limit"):
        parts.append("_delete/ 已有 %s，提醒用户" % rep["delete"]["size"])
    parts += ["git：" + x for x in rep["git"]]
    lines = []
    if after_compact:
        lines.append(COMPACT_NOTE)
    if parts:
        lines.append("[trellis] 待处理：" + "；".join(parts) + "。规则见 agent/guidelines/。")
    if lines:
        print("\n".join(lines))


def print_full(rep, cfg, threshold):
    out = ["## trellis 体检：%s\n" % cfg.get("project_name", "")]

    def sec(title, rows, hint=""):
        if rows:
            out.append("### %s (%d)" % (title, len(rows)))
            if hint:
                out.append(hint)
            out.append("")
            out.extend(rows)
            out.append("")

    sec("根目录杂项 → 移进 import/", ["- " + x for x in rep["root_strays"]])
    sec("未登记的标准目录", ["- %s/" % x for x in rep["unregistered_dirs"]],
        "运行 agent/tools/scripts/add_dir.py <目录> 补登记。")
    sec("import/ 待整理", ["- %s%s — %s，%s%s" % (i["name"], "/" if i["dir"] else "",
        "%d 个文件" % i["files"] if i["dir"] else "文件", i["size"],
        "，已登记待用户确认" if i["pending"] else ("" if i["named_ok"] else "，需重命名"))
        for i in rep["import"]], "按 guidelines/import-routing.md 分发。")
    sec("命名不合规", ["- " + x for x in rep["naming"]], "不在 import/ 里的文件，改名前先问用户。")
    sec("旧版本未归档 → 移进同目录 _archive/", ["- " + x for x in rep["unarchived_versions"]])
    sec("平铺文件过多（> %d）" % threshold, ["- %s（%d 个）" % (c["dir"], c["files"]) for c in rep["crowded"]],
        "提出分类方案，等用户确认。")
    sec("失效链接", ["- %s → `%s`" % (b["file"], b["link"]) for b in rep["broken_links"]])
    sec("缺 README", ["- %s/" % x for x in rep["missing_readme"]], "标准目录运行 add_dir.py 补；其他目录参考 agent/tools/templates/。")
    sec("trellis.json 里登记但不存在的目录", ["- %s/" % x for x in rep["missing_dirs"]])
    sec("索引需要更新", ["- agent/%s" % x for x in rep["stale_index"]], "运行 agent/tools/scripts/reindex.py。")
    sec("git 状态与模式不符", ["- " + x for x in rep["git"]], "见 guidelines/version-control.md。")
    if "delete" in rep:
        d = rep["delete"]
        out.append("### _delete/\n%d 个文件，共 %s%s\n" % (d["files"], d["size"],
                   "，**已超过提醒阈值，告知用户**" if d["over_limit"] else ""))
    if len(out) == 1:
        out.append("一切整洁，没有待处理事项。")
    print("\n".join(out))


def main():
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = os.path.abspath(args[0] if args else ".")
    cfg_path = os.path.join(root, "agent", "trellis.json")
    if not os.path.isfile(cfg_path):
        if "--brief" not in flags:
            preview(root)
        return
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    brief = "--brief" in flags
    try:
        rep = report(root, cfg, brief=brief)
    except Exception as e:  # hook 里出错不能打断会话
        if brief:
            print("[trellis] scan 出错：%s" % e)
            return
        raise
    if brief:
        print_brief(rep, "--after-compact" in flags)
    elif "--json" in flags:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print_full(rep, cfg, int(cfg.get("restructure_threshold", 12)))


if __name__ == "__main__":
    main()
