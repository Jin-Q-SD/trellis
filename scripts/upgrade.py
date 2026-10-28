#!/usr/bin/env python3
"""Trellis upgrade：把项目里的规则、脚本、模板、hooks 和最新版 trellis 做三方比较，安全的更新可一键应用，冲突逐条处理。

用法：
  upgrade.py <项目>                    只读报告
  upgrade.py <项目> --diff <路径>       看某个文件：项目版本 vs 最新模板
  upgrade.py <项目> --apply            应用所有"可安全更新"和"新增"的文件
  upgrade.py <项目> --resolve <路径>    冲突手动合并完后，标记为已与最新模板对齐
"""
import difflib
import json
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import init  # noqa: E402

LABELS = OrderedDict([
    ("safe", "可安全更新（项目没改过，模板有新版）"),
    ("new", "新增文件（新版模板里才有）"),
    ("conflict", "冲突（项目改过，模板也有新版）：逐个看 diff，合并后用 --resolve 标记"),
    ("untracked", "无基线（项目里原本就有同名文件）：看 diff 决定是否合并，合并后用 --resolve 标记"),
    ("custom", "项目自定义过，模板没变：保持不动"),
    ("removed", "项目删掉了这个文件：保持不动"),
    ("same", "已是最新"),
])


def load(root):
    p = os.path.join(root, "agent", "trellis.json")
    if not os.path.isfile(p):
        sys.exit("不是 trellis 项目：%s" % root)
    with open(p, encoding="utf-8") as f:
        return p, json.load(f, object_pairs_hook=OrderedDict)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def classify(root, cfg):
    base = cfg.get("base", {})
    result = OrderedDict()
    for rel, tmpl in init.managed_files(init.ctx_from_config(cfg)).items():
        p = os.path.join(root, rel)
        t, b = init.sha(tmpl), base.get(rel)
        if not os.path.isfile(p):
            state = "removed" if b else "new"
        else:
            cur = init.sha(read(p))
            if cur == t:
                state = "same"
            elif b is None:
                state = "untracked"
            elif cur == b:
                state = "safe"
            elif t == b:
                state = "custom"
            else:
                state = "conflict"
        result[rel] = (state, tmpl)
    return result


def save(path, cfg):
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    root = os.path.abspath(args[0])
    cfg_path, cfg = load(root)
    cfg.setdefault("base", OrderedDict())
    res = classify(root, cfg)

    if "--diff" in args:
        rel = args[args.index("--diff") + 1]
        if rel not in res:
            sys.exit("不是受管文件：" + rel)
        p = os.path.join(root, rel)
        cur = read(p).splitlines(True) if os.path.isfile(p) else []
        sys.stdout.writelines(difflib.unified_diff(cur, res[rel][1].splitlines(True), "项目/" + rel, "模板/" + rel))
        return

    if "--resolve" in args:
        rel = args[args.index("--resolve") + 1]
        if rel not in res:
            sys.exit("不是受管文件：" + rel)
        cfg["base"][rel] = init.sha(res[rel][1])
        save(cfg_path, cfg)
        print("已标记 %s 与最新模板对齐（以后模板没再变化时，它算作项目自定义）。" % rel)
        return

    missing_links = [(l, t) for l, t in init.LINKS.items() if not os.path.lexists(os.path.join(root, l))]

    if "--apply" in args:
        done = []
        for l, t in missing_links:
            p = os.path.join(root, l)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            os.symlink(t, p)
            done.append("%s -> %s" % (l, t))
        for rel, (state, tmpl) in res.items():
            if state in ("safe", "new"):
                p = os.path.join(root, rel)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(tmpl)
                if rel.endswith(".py"):
                    os.chmod(p, 0o755)
                done.append(rel)
            if state in ("safe", "new", "same"):
                cfg["base"][rel] = init.sha(tmpl)
        cfg["trellis"] = init.TRELLIS_VERSION
        save(cfg_path, cfg)
        print("已更新 %d 个文件：" % len(done))
        for d in done:
            print("- " + d)
        left = [r for r, (s, _) in res.items() if s in ("conflict", "untracked")]
        if left:
            print("\n仍需手动处理：\n" + "\n".join("- " + r for r in left))
        return

    print("## trellis upgrade 报告：项目 v%s → 最新 v%s\n" % (cfg.get("trellis", "?"), init.TRELLIS_VERSION))
    groups = OrderedDict((k, []) for k in LABELS)
    for rel, (state, _) in res.items():
        groups[state].append(rel)
    for k, rels in groups.items():
        if rels and k != "same":
            print("### %s (%d)" % (LABELS[k], len(rels)))
            print("\n".join("- " + r for r in rels) + "\n")
    if missing_links:
        print("### 缺少的软链接（--apply 时补上） (%d)" % len(missing_links))
        print("\n".join("- %s -> %s" % lt for lt in missing_links) + "\n")
    if not missing_links and not any(groups[k] for k in ("safe", "new", "conflict", "untracked")):
        print("项目已是最新，无需升级。")


if __name__ == "__main__":
    main()
