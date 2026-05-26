#!/usr/bin/env python3
"""
模式 B：示例模板型 Skill 本地运行示例
调用 DeepSeek API，根据场景选择模板并生成学术邮件
✅ 支持本地 .env 密钥 + YAML frontmatter + 结构化输出
✅ 修复：-t/--template 参数现在可正确强制指定模板
"""

import os, sys, re, yaml, argparse
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv


class TemplateSkillRunner:
    """模式 B：SKILL.md 做路由，examples/ 做模板"""
    
    def __init__(self, skill_path: str):
        self.skill_path = Path(skill_path)
        self.metadata = {}
        self.skill_md = ""
        self.templates = {}
        
        self._load_skill()
        self._load_templates()
        self._init_client()
    
    def _load_skill(self):
        """加载 SKILL.md 并解析 YAML frontmatter"""
        skill_file = self.skill_path / "SKILL.md"
        if not skill_file.exists():
            raise FileNotFoundError(f"找不到 {skill_file}")
        
        content = skill_file.read_text(encoding="utf-8")
        
        # 解析 YAML frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                self.metadata = yaml.safe_load(content[3:end]) or {}
                content = content[end+3:].strip()
        self.skill_md = content
        print(f"✅ 已加载 Skill: {self.metadata.get('display_name', self.skill_path.name)}")
    
    def _load_templates(self):
        """加载 examples/ 目录下所有模板"""
        examples_dir = self.skill_path / "examples"
        if not examples_dir.exists():
            raise FileNotFoundError(f"找不到模板目录: {examples_dir}")
        
        for f in examples_dir.glob("*.md"):
            self.templates[f.name] = f.read_text(encoding="utf-8")
        print(f"✅ 已加载模板: {list(self.templates.keys())}")
    
    def _init_client(self):
        """初始化 DeepSeek 客户端（优先读取本地 .env）"""
        # 加载本地 .env
        env_path = self.skill_path / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            print("❌ 错误：未找到 API Key")
            print(f"   请在 {self.skill_path}/.env 中写入: DEEPSEEK_API_KEY=sk-xxx")
            sys.exit(1)
        
        self.model = self.metadata.get("model") or "deepseek-chat"
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    
    def select_template(self, user_input: str, use_llm: bool = False) -> str:
        """
        路由逻辑：关键词匹配（默认）或 LLM 辅助判断（可选）
        """
        if use_llm:
            return self._llm_route(user_input)
        
        # 关键词快速路由（与 SKILL.md 触发场景对应）
        u = user_input.lower()
        if any(k in u for k in ["套磁", "导师", "联系", "合作", "outreach", "加入实验室", "phd position"]):
            return "old-outreach.md"
        elif any(k in u for k in ["审稿", "回复", "rebuttal", "reviewer", "审稿人", "意见回复", "manuscript"]):
            return "rebuttal-response.md"
        elif any(k in u for k in ["催稿", "跟进", "状态", "进度", "follow", "多久", "结果", "status"]):
            return "follow-up.md"
        return "old-outreach.md"  # fallback
    
    def _llm_route(self, user_input: str) -> str:
        """LLM 辅助意图识别（可选增强）"""
        prompt = f"""你是一个学术邮件路由助手。请根据用户输入判断应使用哪个模板：
- cold-outreach.md: 套磁、联系导师、寻求合作
- rebuttal-response.md: 回复审稿意见、Rebuttal
- follow-up.md: 催稿、询问进度、跟进

用户输入：{user_input}

请只输出模板文件名（如 cold-outreach.md），不要解释。"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=50
            )
            tpl = response.choices[0].message.content.strip()
            return tpl if tpl in self.templates else "cold-outreach.md"
        except Exception:
            return self.select_template(user_input, use_llm=False)  # fallback
    
    def build_prompt(self, template_name: str, template_content: str, user_input: str) -> list:
        """构建 System Prompt：模板 + 用户输入 -> 生成填充邮件"""
        system_prompt = f"""你是一个专业的学术邮件生成助手。

请严格遵循以下流程：
1. 使用选定的邮件模板（见下方）
2. 从用户输入中提取模板中的变量（如 {{variable}}），用用户提供的信息填充
3. 如果某个变量在用户输入中找不到，保留为 [待填写]
4. 保持学术礼仪，语气得体
5. 输出格式必须严格遵守：

=== 生成邮件 ===
Subject: ...
[正文]
=== 使用说明 ===
模板：{template_name}
缺失变量：[变量名1, 变量名2]（如有）
建议：[补充建议]

=== 选定模板 ===
文件名：{template_name}

{template_content}

=== 用户原始需求 ===
{user_input}

请直接输出填充后的完整邮件，不要输出中间思考过程。
"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请根据以上模板和用户信息生成邮件。"}
        ]
    
    def parse_output(self, raw_output: str) -> dict:
        """解析标准输出格式，返回结构化结果"""
        parts = raw_output.split("=== 使用说明 ===")
        if len(parts) < 2:
            return {"email": raw_output, "meta": {}}
        
        email_body = parts[0].replace("=== 生成邮件 ===", "").strip()
        meta_text = parts[1].strip()
        
        # 简单解析 meta
        meta = {}
        for line in meta_text.split("\n"):
            if line.startswith("模板："):
                meta["template"] = line.replace("模板：", "").strip()
            elif line.startswith("缺失变量："):
                meta["missing"] = line.replace("缺失变量：", "").strip()
            elif line.startswith("建议："):
                meta["suggestion"] = line.replace("建议：", "").strip()
        
        return {"email": email_body, "meta": meta}
    
    def run(self, user_input: str, stream: bool = True, use_llm_route: bool = False, force_template: str = None):
        """
        执行邮件生成流程
        
        Args:
            user_input: 用户输入内容
            stream: 是否流式输出
            use_llm_route: 是否使用 LLM 辅助路由
            force_template: 强制指定的模板文件名（可选）
        """
        # 1. 路由：选择模板（优先使用强制指定的模板）
        if force_template:
            # 校验模板是否存在
            if force_template not in self.templates:
                print(f"⚠️ 警告：模板 '{force_template}' 不存在，降级为自动路由")
                print(f"   可用模板: {list(self.templates.keys())}")
                template_name = self.select_template(user_input, use_llm=use_llm_route)
            else:
                template_name = force_template
                print(f"🔒 强制使用模板: {template_name}")
        else:
            template_name = self.select_template(user_input, use_llm=use_llm_route)
        
        template_content = self.templates.get(template_name)
        if not template_content:
            print(f"❌ 未找到模板: {template_name}")
            sys.exit(1)
        
        print(f"🎯 匹配模板: {template_name}")
        
        # 2. 构建 Prompt
        messages = self.build_prompt(template_name, template_content, user_input)
        
        # 3. 调用 DeepSeek
        print(f"🚀 调用 {self.model} 生成邮件...\n")
        print("-" * 60)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.4,
                max_tokens=1500,
                stream=stream
            )
            
            full_output = ""
            if stream:
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        print(content, end="", flush=True)
                        full_output += content
                print()
            else:
                full_output = response.choices[0].message.content
                print(full_output)
                
        except Exception as e:
            print(f"❌ API 错误: {e}")
            sys.exit(1)
        
        print("-" * 60)
        
        # 4. 结构化解析（可选）
        result = self.parse_output(full_output)
        if result["meta"].get("missing"):
            print(f"\n⚠️ 注意：以下变量待填写: {result['meta']['missing']}")
        
        print(f"\n✅ 完成！模板: {template_name}")
        return result


def main():
    parser = argparse.ArgumentParser(description="模式 B：学术邮件生成器")
    parser.add_argument("--input", "-i", type=str, help="用户输入内容")
    parser.add_argument("--template", "-t", type=str, help="强制指定模板（如 cold-outreach.md）")
    parser.add_argument("--llm-route", action="store_true", help="使用 LLM 辅助路由（默认关键词匹配）")
    parser.add_argument("--case", "-c", type=int, default=-1, help="使用内置测试用例 0/1/2")
    args = parser.parse_args()
    
    skill_path = Path(__file__).parent
    runner = TemplateSkillRunner(str(skill_path))
    
    print("\n" + "=" * 60)
    print(f"📧 {runner.metadata.get('display_name', 'Academic Email Writer')}")
    print("=" * 60)
    
    # 内置测试用例
    test_cases = [
        "我想给清华大学的李明教授发封邮件，想申请加入他的实验室做 LLM Agent 记忆方向的研究。我是北大的博士生张三。",
        "审稿人让我们补充实验，我需要回复审稿意见。论文标题是 Hierarchical Memory for LLM Agents，稿件号是 114514。",
        "我三个月前投了 ACL，现在还没消息，想给编辑发邮件问问进度。",
    ]
    
    if args.input:
        user_input = args.input
    elif args.case >= 0 and args.case < len(test_cases):
        user_input = test_cases[args.case]
        print(f"\n【测试用例 {args.case}】")
    else:
        print(f"\n💡 提示：使用 -i \"你的输入\" 或 -c 0/1/2 选择测试用例")
        user_input = test_cases[0]
    
    print(f"\n📝 用户输入: {user_input}\n")
    
    # ✅ 修复：将 args.template 正确传递给 run() 方法
    runner.run(
        user_input, 
        stream=True, 
        use_llm_route=args.llm_route,
        force_template=args.template
    )


if __name__ == "__main__":
    main()