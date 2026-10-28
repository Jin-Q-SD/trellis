#!/usr/bin/env python3
"""Trellis 删除守卫（PreToolUse hook）：拦截项目内的删除命令，改为移进 _delete/；清空 _delete/ 需用户确认（Codex 用 --codex 和确认标记）。"""
import json
import os
import re
import shlex
import sys

DELETE_CMDS = {"rm", "rmdir", "unlink", "shred", "srm"}
PREFIXES = {"sudo", "command", "builtin", "exec", "nohup", "time"}

DENY_REASON = ("trellis 规则：项目内不直接删除文件。请先征得用户同意，再把文件移进 _delete/"
               "（保留原路径，并在 _delete/README.md 登记）。已纳入 git 的应用代码可以在用户同意后用 git rm。")
ASK_REASON = "trellis：这条命令会永久删除 _delete/ 里的文件，需要用户明确同意。"
CONFIRM_MARK = "# trellis:confirmed"
CODEX_REASON = ("trellis：这条命令会永久删除 _delete/ 里的文件。先在对话中向用户说明要删什么（文件数、大小）并询问；"
                "只有用户明确同意后，才在同一条命令末尾加上 `" + CONFIRM_MARK + "` 重新执行。没有用户同意，绝不能加这个标记。")


def project_root():
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and os.path.isfile(os.path.join(env, "agent", "trellis.json")):
        return os.path.realpath(env)
    # 脚本位于 <root>/agent/tools/scripts/
    return os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def inside(path, base):
    return path == base or path.startswith(base + os.sep)


def classify(target, cwd, root):
    """返回 'outside' | 'delete_zone' | 'project'。无法确定的路径按 project 处理。"""
    if any(c in target for c in "$`"):
        return "project"
    t = os.path.expanduser(target)
    # 通配符：只看通配符之前的目录部分
    t = re.split(r"[*?\[]", t)[0] or "."
    p = os.path.realpath(os.path.join(cwd, t)) if not os.path.isabs(t) else os.path.realpath(t)
    if not inside(p, root):
        return "outside"
    zone = os.path.join(root, "_delete")
    if inside(p, zone):
        return "delete_zone"
    return "project"


def targets_of(tokens):
    """从一段命令里找出删除目标；不是删除命令返回 None，目标不明返回 ['$UNKNOWN']。"""
    while tokens and (re.match(r"^\w+=", tokens[0]) or tokens[0] in PREFIXES):
        tokens = tokens[1:]
    if not tokens:
        return None
    cmd = os.path.basename(tokens[0])
    args = tokens[1:]
    if cmd in DELETE_CMDS:
        out, after_dd = [], False
        for x in args:
            if x == "--":
                after_dd = True
            elif after_dd or not x.startswith("-"):
                out.append(x)
        return out or None
    if cmd == "find" and ("-delete" in args or any(os.path.basename(x) in DELETE_CMDS for x in args)):
        paths = []
        for x in args:
            if x.startswith("-") or x in ("(", "!"):
                break
            paths.append(x)
        return paths or ["."]
    if cmd == "xargs" and any(os.path.basename(x) in DELETE_CMDS for x in args):
        return ["$UNKNOWN"]
    if cmd == "git" and "clean" in args:
        return ["."]
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    command = (data.get("tool_input") or {}).get("command") or ""
    if not command:
        return
    root = project_root()
    cwd = data.get("cwd") or os.getcwd()
    verdicts = set()
    for seg in re.split(r"\|\||&&|;|\||&|\n", command):
        seg = seg.strip()
        if not seg:
            continue
        try:
            tokens = shlex.split(seg, comments=True)
        except ValueError:
            if re.search(r"(^|\s)(rm|rmdir|unlink|shred)\s", seg):
                verdicts.add("project")
            continue
        if tokens and tokens[0] == "cd" and len(tokens) > 1 and not any(c in tokens[1] for c in "$`"):
            cwd = os.path.realpath(os.path.join(cwd, os.path.expanduser(tokens[1])))
            continue
        targets = targets_of(tokens)
        if targets:
            for t in targets:
                verdicts.add(classify(t, cwd, root))

    if "project" in verdicts:
        decision, reason = "deny", DENY_REASON
    elif "delete_zone" in verdicts:
        if "--codex" not in sys.argv:
            decision, reason = "ask", ASK_REASON  # Claude Code：弹窗让用户确认
        elif CONFIRM_MARK in command:
            return  # Codex 不支持 ask：用户在对话中同意后由标记放行
        else:
            decision, reason = "deny", CODEX_REASON
    else:
        return
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }}, ensure_ascii=False))


if __name__ == "__main__":
    main()
