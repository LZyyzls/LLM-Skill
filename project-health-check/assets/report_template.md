# 项目健康检查报告

**项目路径**：`{{project_path}}`
**检查时间**：`{{timestamp}}`
**整体评分**：{{overall_score}}/100 — {{grade}}

---

## 1. 项目结构概览

| 指标 | 数值 |
|------|------|
| Python 文件数 | {{py_file_count}} |
| 总代码行数 | {{total_lines}} |
| 目录数 | {{dir_count}} |
| 依赖文件 | {{dep_files}} |

**目录结构**：
```
{{dir_tree}}
```

## 2. 代码质量评分

**总分**：{{overall_score}}/100（{{grade}}）

| 维度 | 得分 | 权重 | 加权 |
|------|:----:|:----:|:----:|
| 函数长度 | {{func_len}} | 20% | {{func_len_w}} |
| 行长度 | {{line_len}} | 10% | {{line_len_w}} |
| 文档覆盖 | {{doc_cov}} | 20% | {{doc_cov_w}} |
| 类型注解 | {{type_ann}} | 15% | {{type_ann_w}} |
| 注释比例 | {{comment_ratio}} | 10% | {{comment_ratio_w}} |
| TODO/FIXME | {{todo_count}} | 5% | {{todo_w}} |
| 导入规范 | {{import_quality}} | 10% | {{import_w}} |
| 文件结构 | {{file_struct}} | 10% | {{file_struct_w}} |

## 3. 发现的问题

{{issues_list}}

## 4. 改进建议

{{recommendations}}
