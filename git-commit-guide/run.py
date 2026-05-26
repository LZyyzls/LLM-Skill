#!/usr/bin/env python3
"""
模式 D：知识库型 Skill —— LLM 按需查阅参考文档
DeepSeek 根据用户问题，自主决定读取哪些 reference 文件，然后回答。

用法:
    python run.py --request "提交格式怎么写"
    python run.py -r "feat 和 chore 的区别"
    python run.py  （使用默认测试用例）
"""

import json
import os
import sys
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

# ── 工具定义：只有"读取参考文档"这一个工具 ──

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_reference",
            "description": "读取指定的参考文档。根据用户问题涉及的知识领域，选择对应的文件。\n"
                           "可用文件: format.md(格式结构), types.md(类型词), "
                           "language.md(中英文选择), tools.md(工具配置)。\n"
                           "可以一次调用读取多个文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["format.md", "types.md", "language.md", "tools.md"]},
                        "description": "要读取的文件名列表，如 ['format.md', 'types.md']"
                    }
                },
                "required": ["files"]
            }
        }
    }
]


class KnowledgeBaseAgent:
    """模式 D Agent：LLM 按需查阅知识库"""

    def __init__(self, skill_path: str):
        self.skill_path = Path(skill_path)
        self.ref_dir = self.skill_path / "references"

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

    def _read_reference(self, files: list) -> str:
        """读取指定的参考文档，返回内容"""
        results = []
        for f in files:
            file_path = self.ref_dir / f
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                results.append(f"=== {f} ===\n{content}")
            else:
                results.append(f"=== {f} ===\n[文件不存在]")
        return "\n\n".join(results)

    def run(self, user_request: str):
        system_prompt = f"""你是一个 Git 提交信息规范顾问。

## 你的工作方式
1. 用户提出关于 Git 提交规范的问题
2. 你判断问题涉及哪个知识领域，调用 read_reference 读取对应的参考文档
3. 基于文档内容给出准确、可操作的指导
4. 如果问题涉及多个领域，可以一次读取多个文件

## 知识库索引
| 领域 | 文件 | 适用问题 |
|------|------|---------|
| 格式结构 | format.md | "格式怎么写"、"body 和 footer 怎么用"、"subject 多长" |
| 类型词 | types.md | "type 有哪些"、"什么时候用 feat/fix/chore"、"scope 怎么写" |
| 语言选择 | language.md | "用中文还是英文"、"中英混合可以吗" |
| 工具配置 | tools.md | "怎么配 commitlint"、"husky 怎么用"、"commitizen 怎么装" |

## 注意事项
- 必须先读文档再回答，不要凭记忆编造
- 回答时引用文档中的具体示例
- 只读当前问题需要的文档，不需要的文件不要加载

## SKILL.md 全文
{self.skill_text}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_request}
        ]

        print("=" * 60)
        print("📖 Git 提交信息规范顾问（模式 D：知识库型）")
        print(f"📝 问题: {user_request}")
        print("=" * 60)

        for turn in range(1, 5):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS,
                temperature=0.3,
            )
            msg = response.choices[0].message

            # —— LLM 要查文档 ——
            if msg.tool_calls:
                tc = msg.tool_calls[0]
                args = json.loads(tc.function.arguments)
                files = args.get("files", [])

                print(f"\n📂 第 {turn} 轮 — DeepSeek 决定查阅: {', '.join(files)}")

                content = self._read_reference(files)
                # 截断过长内容
                if len(content) > 6000:
                    content = content[:6000] + "\n...(truncated)"

                messages.append(msg)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": content
                })

            # —— LLM 给出最终回答 ——
            else:
                print("\n" + "=" * 60)
                print(msg.content)
                print("=" * 60)
                return

        print("\n⚠️ 达到最大轮数限制。")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Git 提交信息规范顾问（模式 D）")
    parser.add_argument("--request", "-r", type=str, help="你的问题")
    args = parser.parse_args()

    skill_path = Path(__file__).parent
    agent = KnowledgeBaseAgent(str(skill_path))

    test_cases = [
        "feat 和 chore 有什么区别？scope 怎么写比较好？",
        "提交信息格式长什么样？给我一个完整示例",
        "团队里有些人用中文有些人用英文，怎么统一？",
        "怎么在项目里配 commitlint？",
    ]

    if args.request:
        request = args.request
    else:
        print("💡 使用 --request/-r 传入你的问题，或从默认用例中选择：")
        for i, tc in enumerate(test_cases):
            print(f"  [{i}] {tc}")
        print()
        choice = input("选择用例 (0-3，默认 0): ").strip()
        idx = int(choice) if choice.isdigit() and 0 <= int(choice) < 4 else 0
        request = test_cases[idx]

    agent.run(request)


if __name__ == "__main__":
    main()
