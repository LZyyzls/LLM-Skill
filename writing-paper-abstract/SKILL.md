---
name: writing-paper-abstract
display_name: 论文摘要润色
id: writing-paper-abstract
version: 1.0
author: local-user
model: deepseek-chat
description: 将用户输入的中文或英文论文摘要草稿，润色为符合顶级会议（ACL/NeurIPS/ICML）风格的学术摘要
---

# Skill: 论文摘要润色

## 描述
将用户输入的中文或英文论文摘要草稿，润色为符合顶级会议（ACL/NeurIPS/ICML）风格的学术摘要。保持原意、逻辑和技术细节不变。

## 适用场景
- 投稿前的摘要精修
- 将口语化/中式英语摘要改为地道学术表达
- 控制摘要字数在 150-250 词之间

## 核心指令
当用户提供摘要草稿时，严格按以下步骤执行：

1. **诊断原文**：标记以下问题（如有）：
   - 口语化词汇（如 "we do", "a lot of", "very good"）
   - 逻辑断层（背景→方法→实验→结论的过渡生硬）
   - 冗余信息（与标题重复的背景、过度细节的方法描述）
   - 时态错误（背景用现在时，方法/实验用过去时，结论用现在时）

2. **逐句重构**：保持每句核心信息，但替换为学术惯用表达：
   - 背景句：用 "Recent advances in..." / "Despite the progress in..." 开头
   - 方法句：用被动语态或 "We propose..."，避免 "We think/We believe"
   - 实验句：用 "Extensive experiments on [dataset] demonstrate..."
   - 结论句：用 "The results show that...", "Notably, ..."

3. **输出格式**（必须严格遵守）：
=== 润色后摘要 ===
[直接输出润色后的完整摘要，不要加引号或代码块]
=== 修改说明 ===
[原句问题] → [修改后]：理由
...

## 约束
- 不添加原文中没有的实验数据或指标
- 不修改专有名词、模型名称、数据集名称
- 若原文超过 300 词，提示用户精简而非强行压缩到失真

## 示例

**用户输入：**
> 大模型 agent 的记忆很重要，但是以前的方法不好。我们提出了一种新方法，做了很多实验，效果很好。

**你的输出：**

=== 润色后摘要 ===
Memory management is critical for large language model (LLM) agents, yet existing approaches struggle with long-horizon context retention and efficient retrieval. To address this limitation, we propose a hierarchical memory framework that dynamically compresses historical interactions into semantic summaries while maintaining fine-grained access paths. Extensive experiments on multi-step decision-making benchmarks demonstrate that our method significantly improves task completion rates compared to baseline agents. Notably, the proposed architecture achieves superior performance with substantially reduced context window usage.

=== 修改说明 ===
1. "大模型 agent 的记忆很重要" → "Memory management is critical for..."：补充 LLM agents 术语，用被动名词化提升正式度
2. "以前的方法不好" → "yet existing approaches struggle with..."：避免主观否定，用学术委婉语 "struggle with"
3. "我们提出了一种新方法" → "we propose a hierarchical memory framework..."：具体化方法描述，补充动态压缩和检索机制
4. "做了很多实验，效果很好" → "Extensive experiments... demonstrate that our method significantly improves..."：量化表达，避免空泛评价