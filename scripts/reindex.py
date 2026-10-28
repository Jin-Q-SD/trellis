#!/usr/bin/env python3
"""Trellis reindex：根据 frontmatter 重新生成 agent/guidelines、agent/memory、agent/tools 的 INDEX.md。"""
import os
import re
import sys
from collections import Counter, OrderedDict

HEADER = "<!-- 由 trellis reindex.py 自动生成，请勿手改。改各文件的 frontmatter 后重新运行。 -->\n"
warnings = []


def find_root(arg):
    if arg:
        return os.path.abspath(arg)
    for start in (os.getcwd(), os.path.dirname(os.path.abspath(__file__))):
        d = start
        while True:
            if os.path.isfile(os.path.join(d, "agent", "trellis.json")):
                return d
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    sys.exit("找不到 trellis 项目（agent/trellis.json）。请把项目路径作为参数传入。")


def frontmatter(path):
    """极简 frontmatter 解析：支持 key: value、[a, b] 列表和 '- a' 列表。"""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (UnicodeDecodeError, OSError):
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    data, key = {}, None
    for line in text[3:end].splitlines():
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                data[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
            elif val in ("|", ">", ""):
                data[key] = "" if val else []
            else:
                data[key] = val.strip("'\"")
        elif key and re.match(r"^\s+-\s+", line):
            if not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(re.sub(r"^\s+-\s+", "", line).strip().strip("'\""))
        elif key and isinstance(data.get(key), str):
            data[key] = (data[key] + " " + line.strip()).strip()
    return data


def desc_of(path, base):
    d = frontmatter(path).get("description", "")
    if isinstance(d, list):
        d = " ".join(d)
    if not d:
        warnings.append("缺少 description：" + os.path.relpath(path, base))
        return "⚠ 缺少 description"
    return d


def write_index(path, body):
    with open(path, "w", encoding="utf-8") as f:
        f.write(HEADER + body.rstrip() + "\n")


def visible(name):
    return not name.startswith(".") and not name.startswith("_") and name != "INDEX.md"


def index_guidelines(root):
    gdir = os.path.join(root, "agent", "guidelines")
    groups = OrderedDict()
    for dirpath, dirnames, filenames in os.walk(gdir):
        dirnames[:] = sorted(d for d in dirnames if visible(d))
        for f in sorted(filenames):
            if not f.endswith(".md") or not visible(f):
                continue
            p = os.path.join(dirpath, f)
            relp = os.path.relpath(p, gdir)
            sub = os.path.dirname(relp)
            fm = frontmatter(p)
            group = sub or fm.get("category") or "general"
            groups.setdefault(group, []).append(
                "- [%s](%s) — %s" % (fm.get("name") or f[:-3], relp, desc_of(p, root)))
    lines = ["# Guidelines 索引", "",
             "长期规则。按当前任务挑相关条目打开；新增或修改规则见 memory-and-guidelines.md。", ""]
    if not groups:
        lines.append("（暂无）")
    for g in sorted(groups):
        lines += ["## " + g, ""] + groups[g] + [""]
    write_index(os.path.join(gdir, "INDEX.md"), "\n".join(lines))
    return sum(len(v) for v in groups.values())


def index_memory(root):
    mdir = os.path.join(root, "agent", "memory")
    rows, tags = [], Counter()
    files = sorted((f for f in os.listdir(mdir) if f.endswith(".md") and visible(f)), reverse=True)
    for f in files:
        p = os.path.join(mdir, f)
        fm = frontmatter(p)
        t = fm.get("tags") or []
        if isinstance(t, str):
            t = [x.strip() for x in t.split(",") if x.strip()]
        tags.update(t)
        if not re.match(r"^\d{6}-", f):
            warnings.append("memory 文件名不是 yymmdd- 开头：" + f)
        tag_str = "  " + " ".join("`%s`" % x for x in t) if t else ""
        rows.append("- [%s](%s) — %s%s" % (f[:-3], f, desc_of(p, root), tag_str))
    lines = ["# Memory 索引", "",
             "以会话为单位的记忆，新的在上。先按标签或日期挑，再打开具体文件；也可以在本目录 grep 关键词。", ""]
    if tags:
        lines += ["**标签**：" + " · ".join("`%s` (%d)" % (k, v) for k, v in sorted(tags.items(), key=lambda x: (-x[1], x[0]))), ""]
    lines += rows or ["（暂无）"]
    write_index(os.path.join(mdir, "INDEX.md"), "\n".join(lines))
    return len(rows)


def first_comment(path):
    """脚本的第一行注释或 docstring 作为说明。"""
    try:
        with open(path, encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines()[:15]]
    except (UnicodeDecodeError, OSError):
        return ""
    for l in lines:
        if not l or l.startswith("#!"):
            continue
        for pre in ('"""', "'''"):
            if l.startswith(pre):
                return l.strip(pre).strip()
        m = re.match(r"^(#|//|--|;)\s*(.+)$", l)
        if m:
            return m.group(2).strip()
        break
    return ""


def index_tools(root):
    tdir = os.path.join(root, "agent", "tools")
    sections = OrderedDict()

    sdir = os.path.join(tdir, "skills")
    if os.path.isdir(sdir):
        for s in sorted(os.listdir(sdir)):
            p = os.path.join(sdir, s, "SKILL.md")
            if visible(s) and os.path.isfile(p):
                fm = frontmatter(p)
                sections.setdefault("Skills（已软链接到 .claude/skills 和 .agents/skills）", []).append(
                    "- [%s](skills/%s/SKILL.md) — %s" % (fm.get("name") or s, s, desc_of(p, root)))

    adir = os.path.join(tdir, "agents")
    if os.path.isdir(adir):
        for f in sorted(os.listdir(adir)):
            p = os.path.join(adir, f)
            if visible(f) and f.endswith(".md"):
                fm = frontmatter(p)
                sections.setdefault("Subagents（已软链接到 .claude/agents）", []).append(
                    "- [%s](agents/%s) — %s" % (fm.get("name") or f[:-3], f, desc_of(p, root)))

    scdir = os.path.join(tdir, "scripts")
    if os.path.isdir(scdir):
        for f in sorted(os.listdir(scdir)):
            p = os.path.join(scdir, f)
            if visible(f) and os.path.isfile(p):
                d = first_comment(p)
                if not d:
                    warnings.append("脚本缺少首行说明注释：agent/tools/scripts/" + f)
                    d = "⚠ 缺少说明"
                sections.setdefault("Scripts", []).append("- [%s](scripts/%s) — %s" % (f, f, d))

    other = []
    for f in sorted(os.listdir(tdir)):
        p = os.path.join(tdir, f)
        if not visible(f) or f in ("skills", "agents", "scripts"):
            continue
        if os.path.isdir(p):
            n = sum(len(fs) for _, _, fs in os.walk(p))
            other.append("- [%s/](%s/) — %d 个文件" % (f, f, n))
        elif f == "links.md":
            other.append("- [links.md](links.md) — 线上工具与外部服务")
        else:
            d = desc_of(p, root) if f.endswith(".md") else (first_comment(p) or "")
            other.append("- [%s](%s)%s" % (f, f, " — " + d if d else ""))
    if other:
        sections["其他"] = other

    lines = ["# Tools 索引", "", "本项目专属的工具。登记规则见 guidelines/memory-and-guidelines.md。", ""]
    for k, v in sections.items():
        lines += ["## " + k, ""] + v + [""]
    write_index(os.path.join(tdir, "INDEX.md"), "\n".join(lines))
    return sum(len(v) for v in sections.values())


def main():
    root = find_root(sys.argv[1] if len(sys.argv) > 1 else None)
    for sub in ("guidelines", "memory", "tools"):
        os.makedirs(os.path.join(root, "agent", sub), exist_ok=True)
    g, m, t = index_guidelines(root), index_memory(root), index_tools(root)
    print("reindex 完成：guidelines %d 条，memory %d 条，tools %d 条" % (g, m, t))
    for w in warnings:
        print("⚠ " + w)


if __name__ == "__main__":
    main()
