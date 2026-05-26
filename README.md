# Skill-Agent: Skill 写法学习项目

五种 Skill 编写模式的完整示例集合，从极简到完整工作流逐步递进。

## 项目结构

```
Skill-Agent/
├── writing-paper-abstract/   # 模式 A：极简指导型
├── academic-email-writer/    # 模式 B：示例模板型
├── csv-data-cleaner/         # 模式 C：工具脚本型
├── git-commit-guide/         # 模式 D：知识库型
└── project-health-check/     # 模式 E：完整工作流型
```

## 五种模式概览

### 模式 A：极简指导型 — `writing-paper-abstract`

**核心**：一个 SKILL.md 就是全部技能。

将论文摘要润色为顶级会议风格的学术表达。SKILL.md 包含完整的指令（诊断 → 重构 → 输出），LLM 直接执行任务，无需任何脚本或模板。

```
writing-paper-abstract/
├── SKILL.md    # 62 行，全部内容
├── run.py      # 薄胶水层：读文件 → 调 API
└── .env
```

### 模式 B：示例模板型 — `academic-email-writer`

**核心**：SKILL.md 做路由，examples/ 做素材库。

根据场景自动选择邮件模板，LLM 将用户信息填入模板占位符生成专业学术邮件。

```
academic-email-writer/
├── SKILL.md                # 44 行，路由表 + 输出规范
├── examples/
│   ├── old-outreach.md     # 套磁邮件模板
│   ├── rebuttal-response.md # 审稿回复模板
│   └── follow-up.md        # 跟进邮件模板
├── run.py
└── .env
```

### 模式 C：工具脚本型 — `csv-data-cleaner`

**核心**：LLM 做调度决策，本地脚本做精确执行。

5 个独立的原子工具脚本，LLM 通过 function calling 自主决定调用哪些工具、按什么顺序、何时停止。

```
csv-data-cleaner/
├── SKILL.md                # 工具目录 + 调度指南
├── scripts/
│   ├── csv_io.py           # 共享：CSV 读取 + JSON 输出
│   ├── scan_file.py        # 文件基本信息扫描
│   ├── column_profile.py   # 列级统计画像
│   ├── pii_detect.py       # 敏感信息检测
│   ├── quality_check.py    # 规则化质量校验
│   └── sample_data.py      # 数据抽样预览
├── references/
│   └── field_rules.md      # 质量校验规则
├── demo_data.csv           # 测试数据
├── run.py
└── .env
```

### 模式 D：知识库型 — `git-commit-guide`

**核心**：SKILL.md 做极简导航，references/ 按需加载。

LLM 根据用户问题，自主决定查阅哪些参考文档，每次只加载相关的知识文件。

```
git-commit-guide/
├── SKILL.md           # 42 行，极简知识索引
├── references/
│   ├── format.md      # 提交信息格式结构
│   ├── types.md       # type 关键词选用指南
│   ├── language.md    # 中英文选择策略
│   └── tools.md       # commitlint/cz/husky 配置
├── run.py
└── .env
```

### 模式 E：完整工作流型 — `project-health-check`

**核心**：有阶段顺序 + 分支跳转 + 条件加载 + 输出模板。

对 Python 项目执行三阶段健康检查，扫描结构 → 代码质量评分 → 套模板生成报告。

```
project-health-check/
├── SKILL.md                 # 完整工作流 + 条件逻辑
├── scripts/
│   ├── scan_structure.py    # 阶段 1：项目结构扫描
│   ├── check_quality.py     # 阶段 2：8 维度代码质量评分
│   └── build_report.py      # 阶段 3：套模板生成报告
├── references/
│   ├── scoring.md           # 条件加载：评分规则
│   └── remediation.md       # 条件加载：修复指南（得分 < 60）
├── assets/
│   └── report_template.md   # 输出模板
├── run.py
└── .env
```

## 五种模式对比

| | A | B | C | D | E |
|---|---|---|---|---|---|
| 核心资产 | 1 个 prompt | 模板文件 | 可执行脚本 | 参考文档 | 脚本+文档+模板 |
| LLM 角色 | 直接执行 | 选模板+填空 | 调度决策 | 按需检索 | 按工作流调度 |
| 流程控制 | 无 | 路由表 | LLM 自主 | LLM 自主 | 阶段顺序+分支 |
| SKILL.md | 全部指令 | 路由+规范 | 工具目录 | 极简导航 | 工作流+决策点 |
| 行数 | 62 | 44 | ~170 | 42 | ~200 |

## 快速开始

### 环境要求

- Python 3.10+
- DeepSeek API Key

### 安装

```bash
git clone <repo-url>
cd Skill-Agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 配置 API Key

每个子项目目录下复制创建 `.env`，填入 DeepSeek API Key：

```bash
cp writing-paper-abstract/.env.example writing-paper-abstract/.env
# 编辑 .env: DEEPSEEK_API_KEY=sk-xxx
```

### 运行示例

```bash
# 模式 A：摘要润色
cd writing-paper-abstract && python run.py

# 模式 B：学术邮件
cd academic-email-writer && python run.py -c 0

# 模式 C：CSV 数据清洗
cd csv-data-cleaner && python run.py

# 模式 D：提交规范顾问
cd git-commit-guide && python run.py -r "feat 和 chore 有什么区别"

# 模式 E：项目健康检查
cd project-health-check && python run.py --project ../csv-data-cleaner
```

## 学习路线

建议按 A → B → C → D → E 顺序阅读，每次聚焦一个问题：

1. **A**：LLM 如何被一份好的 prompt 驱动
2. **B**：如何用模板让 LLM 输出更可控
3. **C**：如何让 LLM 调度本地工具完成精确计算
4. **D**：如何让 LLM 按需检索海量知识
5. **E**：如何将以上组合成带条件逻辑的完整工作流
