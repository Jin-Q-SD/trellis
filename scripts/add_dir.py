#!/usr/bin/env python3
"""Trellis add_dir：按约定新建标准目录（含 README），并同步 trellis.json、AGENTS.md 目录地图和 README.md。"""
import argparse
import json
import os
import re
import sys
from collections import OrderedDict

# 标准产出目录：key -> (给 agent 的说明, 给人的说明)。init.py 也从这里读取。
DIRS = OrderedDict([
    ("research", ("调研：sources/ 原始资料（只读），notes/ 笔记，reports/ 结论", "调研资料和结论")),
    ("docs", ("文字为主的产出（含排版 PDF）；brief/ 放需求和简报", "文档、文稿、PDF")),
    ("design", ("视觉为主的产出；references/ 参考（只读），assets/ 素材", "设计稿、视觉素材")),
    ("app", ("应用代码，遵循技术栈惯例，多平台时按平台分子目录", "应用代码")),
    ("deliverables", ("交付批次 yymmdd-交付名/，交出后冻结", "最终交付物，按批次存放")),
])


def find_root(start):
    d = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(d, "agent", "trellis.json")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            sys.exit("找不到 trellis 项目（agent/trellis.json）。")
        d = parent


def insert_row(path, heading, row, before=None):
    """在 heading 之后的第一张表格末尾插入一行；before 为该行之前要插入的锚点文本。"""
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    try:
        h = next(i for i, l in enumerate(lines) if l.strip().startswith("#") and heading in l)
    except StopIteration:
        return False
    i = h + 1
    while i < len(lines) and not lines[i].startswith("|"):
        i += 1
    if i >= len(lines):
        return False
    pos = i
    while pos < len(lines) and lines[pos].startswith("|"):
        if before and before in lines[pos]:
            break
        pos += 1
    if any(row.split("|")[1].strip() == l.split("|")[1].strip() for l in lines[i:pos] if l.count("|") > 2):
        return False  # 已有这一行
    lines.insert(pos, row)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("key", choices=list(DIRS))
    p.add_argument("--app-slug", default="")
    p.add_argument("--root", default=".")
    a = p.parse_args()

    root = find_root(a.root)
    cfg_path = os.path.join(root, "agent", "trellis.json")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f, object_pairs_hook=OrderedDict)

    name = a.key
    if a.key == "app":
        name = a.app_slug or cfg.get("app_dir") or ""
        if not re.match(r"^[a-z0-9][a-z0-9-]*$", name):
            sys.exit("app 需要 --app-slug（小写 kebab-case）")
        cfg["app_dir"] = name

    done = []
    d = os.path.join(root, name)
    if not os.path.isdir(d):
        os.makedirs(d)
        done.append("新建 %s/" % name)
    readme = os.path.join(d, "README.md")
    tpl = os.path.join(root, "agent", "tools", "templates", "%s.md" % a.key)
    if not os.path.isfile(readme) and os.path.isfile(tpl):
        with open(tpl, encoding="utf-8") as f:
            text = f.read().replace("{{APP_SLUG}}", name).replace("{{PROJECT_NAME}}", cfg.get("project_name", ""))
        with open(readme, "w", encoding="utf-8") as f:
            f.write(text)
        done.append("生成 %s/README.md" % name)

    if name not in cfg.setdefault("dirs", []):
        cfg["dirs"].append(name)
        done.append("登记到 trellis.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")

    agent_desc, human_desc = DIRS[a.key]
    if insert_row(os.path.join(root, "AGENTS.md"), "目录地图", "| `%s/` | %s |" % (name, agent_desc)):
        done.append("补进 AGENTS.md 目录地图")
    if insert_row(os.path.join(root, "README.md"), "去哪里找", "| `%s/` | %s |" % (name, human_desc), before="`agent/`"):
        done.append("补进 README.md")

    print("add_dir %s：%s" % (name, "；".join(done) if done else "已存在，无需改动"))


if __name__ == "__main__":
    main()
