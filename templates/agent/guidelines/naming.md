---
name: naming
description: 文件和目录的命名标准：yymmdd-描述-v01.ext，文件名语言，哪些地方不受此约束
category: workspace
---

# 命名标准

## 文件

```
yymmdd-描述-v01.ext
```

- **日期**：文件内容所对应的日期。不清楚时，用创建日期或导入日期。日期放在开头，在 Finder 里按名称排序就是时间顺序。
- **描述**：用 {{FILENAME_LANG}}，简短具体，2–6 个词，词之间用 `-` 连接。
  - 中文示例：`260128-竞品定价调研-v01.md`
  - 英文示例：`260128-competitor-pricing-scan-v01.md`（全部小写）
- **版本号**：只有会迭代的文件才加，从 `v01` 开始，两位数字。禁止使用 `final`、`最终版`、`new`、`改` 这类词。
- **原始资料**（`research/sources/`、`design/references/`）：如果原文件名包含有用信息（作者、标题），保留在描述里，例如 `260115-smith-城市更新报告.pdf`。
- 不要用空格和这些特殊字符：`/ \ : * ? " < > |`。

## 目录

- 一律用英文小写，kebab-case：`user-interviews/`、`brand-assets/`。
- 交付批次例外，用 `yymmdd-交付名/`，交付名按文件名语言写。
- 系统目录以下划线开头：`_archive/`、`_delete/`。

## 不受此标准约束的

- `README.md`、`AGENTS.md`、`CLAUDE.md`
- `agent/` 下的文件（memory 有自己的命名规则，见 [memory-and-guidelines](memory-and-guidelines.md)）
- 应用目录里的一切（遵循所在技术生态的惯例）
- 交付批次文件夹里面的文件（遵循交付要求；没有要求时仍然按本标准）
