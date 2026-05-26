---
name: project-health-check
display_name: Python 项目健康检查
id: project-health-check
version: 1.0
author: local-user
description: 扫描 Python 项目结构、检查代码质量、生成评分报告。模式 E：完整工作流型。
---

# Python 项目健康检查（模式 E：完整工作流型）

## 概述

本技能对 Python 项目执行三阶段健康检查，生成结构化评分报告。

**核心特征**：
- 有**推荐的执行顺序**（阶段 1 → 2 → 3），但有**分支和跳过逻辑**
- 参考资料按**中间结果条件加载**（不是用户问才加载，是得分低自动加载）
- 输出模板存放在 `assets/`，最后一步套用

---

## 工作流总览

```
用户指定项目路径
       │
       ▼
┌──────────────────────────────────┐
│ 阶段 1：项目结构扫描              │  ← 必跑（scan_structure.py）
│ 文件数、代码量、依赖、目录结构     │
└──────────────┬───────────────────┘
               │
         有 .py 文件？
         /          \
       否            是
       │             │
       │             ▼
       │  ┌──────────────────────────┐
       │  │ 阶段 2：代码质量检查       │  ← 有 Python 文件才跑
       │  │ 8 维度评分、等级判定       │     (check_quality.py)
       │  └──────────┬───────────────┘
       │             │
       │        ┌────┴────┐
       │     ≥ 60       < 60
       │       │           │
       │       │    ┌──────▼──────────────────┐
       │       │    │ ➕ 条件加载              │
       │       │    │ remediation.md          │  ← 得分低才加载
       │       │    │ 修复方案逐条输出          │
       │       │    └──────┬──────────────────┘
       │       │           │
       └───┬───┴───────────┘
           │
           ▼
┌──────────────────────────────────┐
│ 阶段 3：生成报告                  │  ← 必跑（build_report.py +
│ 套用 assets/report_template.md   │     assets/report_template.md）
│ 输出完整的评分报告                 │
└──────────────────────────────────┘
```

---

## 决策点说明

| 决策点 | 条件 | 动作 |
|--------|------|------|
| **跳过阶段 2？** | 阶段 1 发现 `has_python_code == false` | 跳过 check_quality，直接进入阶段 3 |
| **加载 remediation.md？** | 阶段 2 得分 < 60 或 `needs_remediation == true` | 用 `read_reference` 工具加载修复文档 |
| **加载 scoring.md？** | 阶段 2 完成后 | 始终加载，用于解读评分含义 |
| **报告强调什么？** | 得分 < 60 | 报告重点放修复建议 |
| **报告强调什么？** | 得分 ≥ 75 | 报告重点放优秀指标 |

---

## 工具目录

### 阶段 1：`scan_structure.py`
```
python scripts/scan_structure.py <project_path>
```
**输出**：`py_file_count`, `total_py_lines`, `dir_tree`, `dep_files`, `health_files`, `has_python_code`

**何时**：总是第一步。

---

### 阶段 2：`check_quality.py`
```
python scripts/check_quality.py <project_path>
```
**输出**：`overall_score`, `grade`(A/B/C/D), `dimension_scores`(8维), `top_issues`, `needs_remediation`

**何时**：阶段 1 确认有 Python 文件后才跑。
**8 个维度**：函数长度(20%)、行长度(10%)、文档覆盖(20%)、类型注解(15%)、注释比例(10%)、TODO/FIXME(5%)、导入规范(10%)、文件结构(10%)

---

### 阶段 3：`build_report.py`
```
python scripts/build_report.py <scan_json> <quality_json> [--template assets/report_template.md]
```
**输入**：阶段 1 和阶段 2 的 JSON 输出文件路径
**输出**：填充后的 markdown 报告

**何时**：阶段 1 完成后（无论是否跑了阶段 2）。

---

### 辅助工具 1：`read_reference`
读取 `references/` 中的参考文档：
- `scoring.md`：评分规则和等级含义
- `remediation.md`：修复指南（得分 < 60 时加载）

---

### 辅助工具 2：`read_template`
读取 `assets/report_template.md`，获取报告模板内容。

---

## 参考资料的条件加载规则

| 文件 | 加载条件 | 用途 |
|------|---------|------|
| `references/scoring.md` | 阶段 2 完成后 **始终加载** | 解读分数含义、确定等级 |
| `references/remediation.md` | 仅在 `needs_remediation == true` 时加载 | 逐条输出修复方案 |

---

## 完整执行示例

**用户**："检查 E:/my_project 的健康状况"

**你的决策链**：
1. 调 `scan_structure("E:/my_project")` → 必跑
2. 看到 `has_python_code: true`，`py_file_count: 12`
3. 调 `check_quality("E:/my_project")` → 有 Python 文件，跑阶段 2
4. 调 `read_reference("scoring.md")` → 始终加载
5. 看到 `overall_score: 52, grade: D, needs_remediation: true`
6. 调 `read_reference("remediation.md")` → 得分 < 60，条件加载
7. 调 `read_template` → 获取报告模板
8. 调 `build_report(...)` → 套模板生成报告
9. 基于模板输出最终报告，重点强调修复建议

---

## 约束

- 只读不写：不修改被检查项目的任何文件
- 阶段顺序：1 → 2 → 3，不可颠倒
- 阶段 1 和阶段 3 必跑，阶段 2 按条件跑
- 脚本输出存为临时 JSON 文件，build_report.py 需要读取
- 最终报告使用中文
