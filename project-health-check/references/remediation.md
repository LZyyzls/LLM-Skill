# 代码质量修复指南

本文件在检查得分 < 60 时被 LLM 条件加载，提供具体的修复方案。

---

## 函数过长

**问题**：函数平均行数 > 30 行

**修复**：
1. 按职责拆分：一个函数只做一件事
2. 提取公共逻辑到私有函数
3. 用 `@dataclass` 或 `NamedTuple` 替代大量参数传递

**示例**：
```python
# 重构前
def process_order(order, user, db, cache):
    # 50 行：验证、计算价格、更新库存、发通知...
    pass

# 重构后
def process_order(order, user, db, cache):
    _validate(order)
    price = _calculate_price(order)
    _update_inventory(order, db)
    _notify(user, order, cache)
```

---

## 缺少文档字符串

**问题**：docstring 覆盖率 < 50%

**修复**：
1. 每个公开函数必须有 docstring（至少一行）
2. 复杂函数用 Google/NumPy 风格描述参数和返回值
3. 私有函数（`_` 前缀）可省略

**示例**：
```python
def calculate_score(metrics: dict, weights: dict) -> float:
    """根据指标和权重计算加权总得分。

    Args:
        metrics: 各维度的原始分值，如 {"func_len": 85, "line_len": 90}
        weights: 各维度的权重，如 {"func_len": 0.2, "line_len": 0.1}

    Returns:
        加权后的总分，范围 0-100
    """
```

---

## 类型注解缺失

**问题**：类型注解覆盖率 < 30%

**修复**：
1. 所有函数签名添加参数类型和返回值类型
2. 使用 `from typing import List, Dict, Optional` 等
3. Python 3.10+ 可用 `list[int]` 替代 `List[int]`

---

## 注释比例失衡

**问题**：注释率 < 5%（缺注释）或 > 30%（过度注释）

**修复**：
- 注释过少：关键算法、业务规则、非显而易见的逻辑必须注释
- 注释过多：删除"代码自解释"的注释，如 `i += 1  # 自增`

---

## TODO/FIXME 过多

**问题**：未完成标记 > 5 个

**修复**：
1. 每个 TODO/FIXME 必须关联 issue 或负责人
2. 定期清理已完成或过期的标记
3. 格式：`# TODO(zhangsan): 实现缓存过期策略 #42`

---

## 导入混乱

**问题**：存在 `from module import *` 或不规范的导入顺序

**修复**：
1. 导入分三组：标准库 → 第三方 → 本地模块，组间空行分隔
2. 禁止 `import *`
3. 用 `isort` 自动排序

**示例**：
```python
# 标准库
import os
from pathlib import Path

# 第三方
import pandas as pd
from flask import Flask

# 本地
from .utils import helper
from .models import User
```
