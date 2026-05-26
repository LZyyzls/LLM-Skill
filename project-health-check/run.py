#!/usr/bin/env python3
"""
模式 E：完整工作流型 Skill —— 有阶段顺序 + 分支跳转 + 条件加载
DeepSeek 遵循工作流（1→2→3），但在阶段内部自主决策（跳过 2？加载 remediation？）

用法:
    python run.py --project E:/my_project
    python run.py --project E:/my_project --request "只检查结构"
    python run.py  （交互式输入项目路径）
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Fix Windows console encoding for emoji and Chinese output
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from openai import OpenAI
from dotenv import load_dotenv

# ── 工具定义 ──

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "scan_structure",
            "description": "阶段1（必跑）：扫描项目结构。统计 Python 文件数、代码行数、依赖文件、目录树。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "项目目录路径"}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_quality",
            "description": "阶段2（有条件）：检查代码质量，8个维度评分。仅在阶段1发现 Python 文件后调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "项目目录路径"}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "build_report",
            "description": "阶段3（必跑）：使用模板生成最终报告。需要先执行 scan_structure 和 check_quality，将它们的 JSON 输出文件路径传入。",
            "parameters": {
                "type": "object",
                "properties": {
                    "scan_json": {"type": "string", "description": "scan_structure 输出的 JSON 文件路径"},
                    "quality_json": {"type": "string", "description": "check_quality 输出的 JSON 文件路径"}
                },
                "required": ["scan_json", "quality_json"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_reference",
            "description": "读取 references/ 中的参考文档。scoring.md: 评分规则（阶段2后始终加载）。remediation.md: 修复指南（仅在得分<60时加载）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "description": "文件名：scoring.md 或 remediation.md",
                        "enum": ["scoring.md", "remediation.md"]
                    }
                },
                "required": ["file"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_template",
            "description": "读取 assets/report_template.md 报告模板。阶段3前调用。",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]


class WorkflowAgent:
    """模式 E Agent：遵循工作流（1→2→3），阶段内自主决策"""

    def __init__(self, skill_path: str):
        self.skill_path = Path(skill_path)
        self.scripts_dir = self.skill_path / "scripts"
        self.ref_dir = self.skill_path / "references"
        self.assets_dir = self.skill_path / "assets"

        self.tmp_dir = Path(tempfile.mkdtemp())
        self.scan_json = self.tmp_dir / "scan_result.json"
        self.quality_json = self.tmp_dir / "quality_result.json"

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

    def _run_script(self, script_name: str, *args: str) -> str:
        cmd = ["python", str(self.scripts_dir / script_name)] + list(args)
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=60)
            # Decode bytes manually with error tolerance — Windows console
            # may output GBK bytes that aren't valid UTF-8
            out = proc.stdout.decode("utf-8", errors="replace").strip()
            if out:
                return out
            return proc.stderr.decode("utf-8", errors="replace").strip()
        except subprocess.TimeoutExpired:
            return json.dumps({"error": "脚本执行超时"}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def _handle_tool_call(self, tc) -> str:
        name = tc.function.name
        args = json.loads(tc.function.arguments)

        if name == "scan_structure":
            result = self._run_script("scan_structure.py", args["project_path"])
            self.scan_json.write_text(result, encoding="utf-8")
            return result

        elif name == "check_quality":
            result = self._run_script("check_quality.py", args["project_path"])
            self.quality_json.write_text(result, encoding="utf-8")
            return result

        elif name == "build_report":
            out_file = str(self.tmp_dir / "report.md")
            # Always use our saved temp files, ignore whatever paths the LLM passes
            self._run_script(
                "build_report.py",
                str(self.scan_json),
                str(self.quality_json),
                "--output", out_file
            )
            if Path(out_file).exists():
                return Path(out_file).read_text(encoding="utf-8")
            return f"[报告生成失败, 输出文件不存在: {out_file}]"

        elif name == "read_reference":
            f = args["file"]
            path = self.ref_dir / f
            return path.read_text(encoding="utf-8") if path.exists() else f"[文件不存在: {f}]"

        elif name == "read_template":
            path = self.assets_dir / "report_template.md"
            return path.read_text(encoding="utf-8") if path.exists() else "[模板文件不存在]"

        return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)

    # ── 主循环 ──

    def run(self, project_path: str, user_request: str = ""):
        request_text = user_request or f"请对 {project_path} 执行完整的项目健康检查"

        system_prompt = f"""你是一个 Python 项目健康检查助手。严格按照以下工作流执行任务。

## 工作流规则

### 阶段顺序（不可颠倒）
1. **scan_structure** — 必跑，总是第一步
2. **check_quality** — 仅当阶段1返回 has_python_code=true 时执行
3. **build_report** — 必跑，最后一步

### 参考资料加载规则
- 阶段2完成后 → **始终**调用 read_reference("scoring.md")
- 阶段2得分<60 或 needs_remediation=true → **必须**调用 read_reference("remediation.md")
- 阶段3之前 → 调用 read_template 获取报告模板

### 决策点
- 阶段1 has_python_code=false → 跳过阶段2，直接进入阶段3
- 阶段2 needs_remediation=true → 加载修复文档，报告中强调修复方案
- 阶段2 得分≥75 → 报告重点放优秀指标，不必加载修复文档

### 注意事项
- 每次只调用必要的工具，不要一次调用所有工具。先跑阶段1看结果再决定。
- scan_structure 和 check_quality 的结果会自动保存为 JSON 文件，build_report 需要传入这些文件路径。
- 最终输出格式丰富的项目健康报告。

{self.skill_text}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request_text}
        ]

        resolved_path = str(Path(project_path).resolve())

        print("=" * 60)
        print("🔍 Python 项目健康检查（模式 E：完整工作流型）")
        print(f"📁 项目: {resolved_path}")
        print("=" * 60)

        for turn in range(1, 10):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS,
                temperature=0.3,
            )
            msg = response.choices[0].message

            if msg.tool_calls:
                tool_results = []
                print(f"\n📋 第 {turn} 轮:")

                for tc in msg.tool_calls:
                    name = tc.function.name
                    args = json.loads(tc.function.arguments)

                    # Force the correct project path (don't trust LLM's guess)
                    if name in ("scan_structure", "check_quality"):
                        args["project_path"] = resolved_path

                    phase_label = {
                        "scan_structure": "阶段1",
                        "check_quality": "阶段2",
                        "build_report": "阶段3",
                        "read_reference": "参考",
                        "read_template": "模板"
                    }.get(name, "工具")

                    print(f"   [{phase_label}] {name}")

                    result = self._handle_tool_call(tc)
                    if len(result) > 4000:
                        result = result[:4000] + "\n...(truncated)"

                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result
                    })

                messages.append(msg)
                messages.extend(tool_results)

            else:
                print("\n" + "=" * 60)
                print(msg.content)
                print("=" * 60)
                return

        print("\n⚠️ 达到最大轮数限制（10轮）。")

    def cleanup(self):
        """Remove temporary files."""
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Python 项目健康检查（模式 E）")
    parser.add_argument("--project", "-p", type=str, help="项目目录路径")
    parser.add_argument("--request", "-r", type=str, help="具体需求（可选）")
    args = parser.parse_args()

    skill_path = Path(__file__).parent
    agent = WorkflowAgent(str(skill_path))

    if args.project:
        project = args.project
    else:
        project = input("请输入项目路径: ").strip()
        if not project:
            print("❌ 未输入路径，使用当前 skill 目录作为示例")
            project = str(skill_path)

    try:
        agent.run(project, args.request or "")
    finally:
        agent.cleanup()


if __name__ == "__main__":
    main()
