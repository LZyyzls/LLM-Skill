#!/usr/bin/env python3
"""
模式 A：极简指导型 Skill 本地运行示例
调用 DeepSeek API 进行论文摘要润色
"""

import os
import sys
import re
from pathlib import Path

# 需要安装: pip install openai pyyaml
from openai import OpenAI
import yaml


# 在文件顶部 import 区域添加
from dotenv import load_dotenv

class MinimalSkillRunner:
    """极简 Skill 加载器 + DeepSeek 调用器"""
    
    def __init__(self, skill_path: str):
        self.skill_path = Path(skill_path)
        self.metadata = {}      # 存储 YAML frontmatter
        self.instruction = ""   # 核心指令内容
        self.examples = ""      # 示例内容
        self.skill_name = ""    # 显示名称（优先 display_name）
        self.skill_id = ""      # 程序标识（name 字段）
        
        self._load_skill()
        self._init_client()
    
    def _load_skill(self):
        """解析 SKILL.md：YAML Frontmatter + 正文内容"""
        skill_file = self.skill_path / "SKILL.md"
        if not skill_file.exists():
            raise FileNotFoundError(f"找不到 Skill 文件: {skill_file}")
        
        content = skill_file.read_text(encoding="utf-8")
        
        # 1. 解析 YAML Frontmatter (--- 包裹的部分)
        if content.startswith("---"):
            try:
                end_marker = content.find("---", 3)
                if end_marker != -1:
                    yaml_block = content[3:end_marker].strip()
                    self.metadata = yaml.safe_load(yaml_block) or {}
                    content = content[end_marker+3:].strip()
            except yaml.YAMLError as e:
                print(f"⚠️ YAML 解析警告: {e}，将使用降级解析模式")
        
        # 2. 提取名称（优先级：display_name > name > id > 标题）
        self.skill_id = self.metadata.get("name") or self.metadata.get("id") or self.skill_path.name
        self.skill_name = (
            self.metadata.get("display_name") or  # ✅ 优先中文显示名
            self.metadata.get("name") or 
            self.metadata.get("id") or 
            self._extract_title(content) or 
            self.skill_path.name
        )
        
        # 3. 提取核心指令和示例
        self._parse_content(content)
    
    def _extract_title(self, content: str) -> str:
        """从 Markdown 标题提取技能名称"""
        match = re.search(r'^#\s*Skill:\s*(.+)$', content, re.MULTILINE)
        return match.group(1).strip() if match else None
    
    def _parse_content(self, content: str):
        """解析正文，提取核心指令和示例"""
        lines = content.split("\n")
        buffer = []
        current_section = None
        
        for line in lines:
            if line.strip().startswith("## 核心指令"):
                current_section = "instruction"
                continue
            elif line.strip().startswith("## 示例"):
                current_section = "example"
                continue
            elif line.strip().startswith("## "):
                if current_section in ["instruction", "example"]:
                    current_section = None
            
            if current_section == "instruction":
                buffer.append(line)
            elif current_section == "example":
                self.examples += line + "\n"
        
        self.instruction = "\n".join(buffer).strip()


    
    # 找到 _init_client 方法，完整替换为：
    def _init_client(self):
        """初始化 DeepSeek 客户端（优先读取本地 .env）"""
        # 1. 加载同目录下的 .env 文件
        env_path = self.skill_path / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            print(f"⚠️ 未找到 {env_path}，将尝试从系统环境变量读取")

        # 2. 获取 API Key
        api_key = os.getenv("DEEPSEEK_API_KEY")
        
        # 3. 兼容纯文本 fallback（可选）
        if not api_key:
            key_file = self.skill_path / "api_key.txt"
            if key_file.exists():
                api_key = key_file.read_text(encoding="utf-8").strip()
            else:
                print("❌ 错误：未找到 API Key。")
                print("   请在当前目录创建 .env 文件，写入 DEEPSEEK_API_KEY=sk-xxx")
                print("   或创建 api_key.txt 文件，直接粘贴 Key")
                sys.exit(1)

        # 4. 初始化客户端
        model_name = self.metadata.get("model") or os.getenv("SKILL_MODEL", "deepseek-chat")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        self.model = model_name    
    
    def build_messages(self, user_input: str) -> list:
        """构建符合 DeepSeek 格式的消息列表"""
        system_prompt = f"""你是一个专业的学术写作助手。请严格遵循以下 Skill 指令执行任务。

【Skill】{self.skill_name}（ID: {self.skill_id}）

【核心指令】
{self.instruction}

【参考示例】
{self.examples}

现在，请严格按照上述指令处理用户的输入。不要偏离指令要求。
"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    
    def run(self, user_input: str, stream: bool = True):
        """调用 DeepSeek API 并输出结果"""
        messages = self.build_messages(user_input)
        
        print(f"🚀 正在调用 {self.model} (Skill: {self.skill_name}) ...\n")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
                stream=stream
            )
            
            if stream:
                print("-" * 50)
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        print(chunk.choices[0].delta.content, end="", flush=True)
                print("\n" + "-" * 50)
            else:
                content = response.choices[0].message.content
                print(content)
                
        except Exception as e:
            print(f"❌ API 调用失败: {e}")
            sys.exit(1)


def main():
    skill_path = Path(__file__).parent
    runner = MinimalSkillRunner(str(skill_path))
    
    print("=" * 60)
    print(f"📝 {runner.skill_name}（模式 A：极简指导型）")
    print(f"🔖 ID: {runner.skill_id}")
    print("=" * 60)
    
    test_input = """大模型 agent 的记忆很重要，但是以前的方法不好。
我们提出了一种新方法，做了很多实验，效果很好。"""
    
    print("\n【用户输入】")
    print(test_input)
    print()
    
    runner.run(test_input, stream=True)
    print("\n✅ 完成！")


if __name__ == "__main__":
    main()