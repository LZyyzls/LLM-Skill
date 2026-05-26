---
name: csv-data-cleaner
display_name: CSV 数据质量工具集
id: csv-data-cleaner
version: 2.0
author: local-user
description: 一组独立的命令行工具，用于 CSV 数据质量检查。LLM 做调度，脚本做执行。
---

# CSV 数据质量工具集（模式 C：工具脚本型）

## 核心设计

本技能提供 **5 个原子工具**，每个只做一件事。**你（LLM）是调度者**——
读取用户需求，决定调用哪些工具、按什么顺序、是否并行、何时停止。

```
廉价工具先行 → 根据结果精准追加 → 信息足够即停
```

---

## 工具目录

### 1. `scan_file.py` —— 文件快速扫描

**成本：低**（只读元信息，不分析内容）

```
python scripts/scan_file.py <csv_path>
```

**输出字段**：`file_path`, `file_size_kb`, `encoding`, `row_count`, `col_count`, `headers`, `empty_columns`, `duplicate_headers`

**何时调用**：
- 几乎总是第一步。先了解数据规模、编码、有哪些列，再决定后续工具。
- 如果用户直接指定了列名，可跳过。

---

### 2. `column_profile.py` —— 列级统计画像

**成本：中**（遍历所有行，逐列计算统计量）

```
python scripts/column_profile.py <csv_path> [--columns col1,col2]
```

**输出字段**：`total_rows`, `profiled_columns`, `columns: {col: {type, missing, missing_pct, ...}}`
- 数值列附加：`min`, `max`, `mean`, `std`, `median`
- 分类列附加：`unique_count`, `top_values`

**何时调用**：
- 用户关心"数据分布"、"有没有缺失"、"哪些列是数值/分类"
- 用 `--columns` 精准打击特定列，避免不必要计算
- 与 `pii_detect.py` 可**并行调用**

---

### 3. `pii_detect.py` —— 敏感信息检测

**成本：中**（检查列名 + 抽样内容匹配）

```
python scripts/pii_detect.py <csv_path> [--sample 50]
```

**检测方式**：
- 列名匹配：email/phone/id_card/name/address/password 等关键词
- 内容模式：邮箱格式、手机号格式、身份证格式

**输出字段**：`pii_count`, `verdict` (clean | pii_found), `findings: [{column, pii_type, severity, recommendation}]`

**何时调用**：
- 数据包含个人信息字段（姓名、电话、邮箱、地址等）
- 用户提到"隐私"、"脱敏"、"合规"
- 与 `column_profile.py` 可**并行调用**

---

### 4. `quality_check.py` —— 规则化质量校验

**成本：中-高**（逐列应用多条规则）

```
python scripts/quality_check.py <csv_path> [--rules references/field_rules.md]
```

**校验规则**（来自 `references/field_rules.md`）：
| 规则 | 条件 | 严重度 |
|------|------|--------|
| 类型覆盖 | 列名含 `_date`/`_time`/`_at` → temporal; `_flag`/`_is_`/`_has_` → boolean | info |
| 缺失率 | > 1% → warning, > 20% → error | warning/error |
| 唯一值占比 | > 99% → 疑似主键 | warning |
| 布尔列值 | 非 0/1/true/false 值 | warning |
| 大数据集 | 行数 > 50,000 → 建议抽样 | info |

**输出字段**：`summary: {errors, warnings, info, total}`, `violations: [{column, rule, severity, detail}]`

**何时调用**：
- `column_profile` 发现缺失率偏高后，追加深度检查
- 用户要求"全面质量检查"
- `scan_file` 发现是大数据集时
- **建议在其他工具之后调用**——根据前序发现精准使用

---

### 5. `sample_data.py` —— 数据抽样预览

**成本：低**（只读前 N 行）

```
python scripts/sample_data.py <csv_path> [--n 10] [--columns col1,col2]
```

**输出字段**：`sample_size`, `total_rows`, `headers_shown`, `rows: [{col: value}]`

**何时调用**：
- 需要"看到"真实数据内容才能判断时
- 用户问"数据长什么样"
- 不确定某列的具体格式时

---

## 调度策略

### 三原则

1. **廉价优先**：`scan_file`（只读元信息）→ 再决定是否调更贵的工具
2. **独立并行**：`column_profile` 和 `pii_detect` 互不依赖，可同时调
3. **按需追加**：根据前一步结果决定是否追加 `quality_check` 或 `sample_data`
4. **精准打击**：用户只问某一列 → 用 `--columns` 参数，不扫全表

### 典型工作流

**场景 A：用户说"帮我看看这个 CSV 的数据质量"**

```
1. scan_file          → 了解: 1200 行 × 8 列, 含 email/phone/age/salary
2. column_profile  +  pii_detect  (并行)
   → age 缺失 15%, salary std 偏高
   → email/phone 列为 PII
3. quality_check      → 因缺失率超标, 追加规则校验
   → age 缺失率 error, phone 格式不一致 warning
4. 合成报告
```

**场景 B：用户说"检查 age 列有没有缺失值"**

```
1. column_profile --columns age    （精准打击，无需 scan_file）
2. 直接回答
```

**场景 C：用户说"这份数据有没有隐私风险"**

```
1. scan_file          → 发现 email, phone, name 列
2. pii_detect         → email/phone/name 均命中 PII 规则
3. 回答 + 给出脱敏建议
```

**场景 D：用户说"看看数据长什么样"**

```
1. sample_data --n 10
2. 展示数据 + scan_file 补充全局信息
```

---

## 错误处理

所有工具统一返回：

```json
{"status": "error", "error_code": 1|2|3, "message": "具体原因"}
```

| 错误码 | 含义 | 应对 |
|--------|------|------|
| 1 | 文件不存在 | 提示用户检查路径 |
| 2 | 编码错误 | 建议用户转换编码 |
| 3 | 空文件/结构异常 | 提示用户检查 CSV |

---

## 约束

- 所有工具只读，不修改原始文件
- 所有工具输出 JSON 到 stdout，exit code = error_code
- 工具之间无状态依赖——每次调用独立
- 生成最终报告使用中文
