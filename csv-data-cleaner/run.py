#!/usr/bin/env python3
"""
模式 C：工具脚本型 Skill —— LLM 调度器 + 本地脚本执行器
DeepSeek 通过 function calling 自主决定：调用哪些工具、按什么顺序、何时停止。

用法:
    python run.py --csv demo_data.csv --request "检查数据质量"
    python run.py --csv data.csv -r "age 列有没有缺失值"
    python run.py  （使用默认测试用例）
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

# ── 5 个工具的函数定义（供 DeepSeek function calling 使用） ──

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "scan_file",
            "description": "快速扫描CSV基本信息：编码、行列数、表头列表、空列、重复表头。成本最低，几乎总是第一步调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "csv_path": {"type": "string", "description": "CSV文件路径"}
                },
                "required": ["csv_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "column_profile",
            "description": "对CSV列做统计画像：类型推断(numeric/categorical)、缺失值统计、数值列(mean/std/min/max/median)、分类列(unique/top10)。可用columns参数精准指定列名，避免不必要计算。",
            "parameters": {
                "type": "object",
                "properties": {
                    "csv_path": {"type": "string", "description": "CSV文件路径"},
                    "columns": {"type": "string", "description": "逗号分隔的列名，如'age,salary'。不指定则分析全部列。"}
                },
                "required": ["csv_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pii_detect",
            "description": "检测CSV中的敏感信息(PII)：列名匹配(email/phone/姓名/身份证/地址/密码等)+内容模式匹配(邮箱格式/手机号格式/身份证格式)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "csv_path": {"type": "string", "description": "CSV文件路径"},
                    "sample": {"type": "integer", "description": "内容模式匹配的抽样行数，默认50"}
                },
                "required": ["csv_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "quality_check",
            "description": "基于规则的数据质量深度校验。检查：缺失率是否超标(>1%警告,>20%错误)、唯一值占比是否过高(疑似主键)、布尔列值是否合法、类型覆盖规则。当column_profile发现异常后追加调用，不要作为第一步。",
            "parameters": {
                "type": "object",
                "properties": {
                    "csv_path": {"type": "string", "description": "CSV文件路径"},
                    "rules": {"type": "string", "description": "规则文件路径，默认 references/field_rules.md"}
                },
                "required": ["csv_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sample_data",
            "description": "预览CSV前N行真实数据。当需要'看到'数据内容才能判断时调用，比如不确定某列的格式。",
            "parameters": {
                "type": "object",
                "properties": {
                    "csv_path": {"type": "string", "description": "CSV文件路径"},
                    "n": {"type": "integer", "description": "返回行数，默认10"},
                    "columns": {"type": "string", "description": "逗号分隔的列名，不指定则返回全部列"}
                },
                "required": ["csv_path"]
            }
        }
    }
]

# 工具名 → 脚本文件名
SCRIPT_MAP = {
    "scan_file":      "scan_file.py",
    "column_profile": "column_profile.py",
    "pii_detect":     "pii_detect.py",
    "quality_check":  "quality_check.py",
    "sample_data":    "sample_data.py",
}


# ── Agent ──

class ToolSkillAgent:
    """模式 C Agent：LLM 做调度决策，本地脚本做精确执行"""

    def __init__(self, skill_path: str):
        self.skill_path = Path(skill_path)
        self.scripts_dir = self.skill_path / "scripts"

        skill_md = self.skill_path / "SKILL.md"
        self.skill_text = skill_md.read_text(encoding="utf-8") if skill_md.exists() else ""

        self._init_client()

    def _init_client(self):
        env_path = self.skill_path / ".env"
        if env_path.exists():
            load_dotenv(env_path)

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            print("❌ 未找到 DEEPSEEK_API_KEY")
            print(f"   请在 {self.skill_path}/.env 中写入: DEEPSEEK_API_KEY=sk-xxx")
            sys.exit(1)

        self.model = "deepseek-chat"
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    # ── 工具执行 ──

    def _run_script(self, name: str, args: dict) -> str:
        """执行对应的本地脚本，返回 stdout 字符串"""
        script = SCRIPT_MAP.get(name)
        if not script:
            return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)

        cmd = ["python", str(self.scripts_dir / script), args.get("csv_path", "")]

        # 按工具拼接可选参数
        if name == "column_profile" and args.get("columns"):
            cmd += ["--columns", args["columns"]]
        if name == "quality_check" and args.get("rules"):
            cmd += ["--rules", args["rules"]]
        if name == "pii_detect" and args.get("sample"):
            cmd += ["--sample", str(args["sample"])]
        if name == "sample_data":
            if args.get("n"):
                cmd += ["--n", str(args["n"])]
            if args.get("columns"):
                cmd += ["--columns", args["columns"]]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=30)
            return proc.stdout.strip() or proc.stderr.strip()
        except subprocess.TimeoutExpired:
            return json.dumps({"error": "工具执行超时"}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    # ── 主循环 ──

    def run(self, csv_path: str, user_request: str):
        system_prompt = f"""你是一个CSV数据质量分析助手。你可以调用函数来检查CSV文件。

## 你的工作方式
1. 分析用户需求 → 决定需要哪些工具
2. 独立的工具可以一次同时调用多个（并行）
3. 每个工具返回JSON结果 → 你解读 → 根据发现决定是否追加工具
4. 信息足够后 → 生成结构化的数据质量报告

## 调度原则
- 先调廉价工具(scan_file)了解全貌，再决定后续
- column_profile 和 pii_detect 互不依赖，可并行
- 只在发现异常时才追加 quality_check（不要一开始就调）
- 用户只问特定列 → 用 columns 参数精准打击，不扫全表
- 可以一次调用多个独立工具，减少轮数

## 最终报告格式（中文输出）
=== 数据概览 ===
=== 列统计摘要 ===
=== 警告信息 ===
=== 建议 ===

## 参考：SKILL.md 完整内容
{self.skill_text}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"CSV文件路径: {csv_path}\n用户需求: {user_request}"}
        ]

        print("=" * 60)
        print("📊 CSV 数据质量分析（模式 C：LLM 调度 + 脚本执行）")
        print(f"📁 文件: {csv_path}")
        print(f"📝 需求: {user_request}")
        print("=" * 60)

        for turn in range(1, 9):  # 最多 8 轮，防止死循环
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS,
                temperature=0.3,
            )
            msg = response.choices[0].message

            # —— LLM 决定调工具 ——
            if msg.tool_calls:
                print(f"\n🔧 第 {turn} 轮 — DeepSeek 决定调用以下工具:")
                tool_results = []

                for tc in msg.tool_calls:
                    name = tc.function.name
                    args = json.loads(tc.function.arguments)
                    print(f"   → {name}({json.dumps(args, ensure_ascii=False)})")

                    result = self._run_script(name, args)
                    # 截断过长输出，避免超出 context
                    if len(result) > 3000:
                        result = result[:3000] + "\n...(truncated)"
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result
                    })

                messages.append(msg)
                messages.extend(tool_results)

            # —— LLM 输出最终报告 ——
            else:
                print("\n" + "=" * 60)
                print(msg.content)
                print("=" * 60)
                return

        print("\n⚠️ 达到最大轮数限制（8轮），分析终止。")


# ── 入口 ──

def main():
    import argparse
    parser = argparse.ArgumentParser(description="CSV 数据质量分析（模式 C：LLM调度+脚本执行）")
    parser.add_argument("--csv", type=str, help="CSV文件路径")
    parser.add_argument("--request", "-r", type=str, help="分析需求描述")
    args = parser.parse_args()

    skill_path = Path(__file__).parent
    agent = ToolSkillAgent(str(skill_path))

    csv_file = args.csv or str(skill_path / "demo_data.csv")
    default_request = "帮我全面检查这份CSV的数据质量"
    request = args.request or default_request

    agent.run(csv_file, request)


if __name__ == "__main__":
    main()
