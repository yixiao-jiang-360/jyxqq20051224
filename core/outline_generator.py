"""
大纲生成器 - 基于拆书知识或用户需求，生成大纲/细纲
"""
import json
from pathlib import Path
from typing import Optional, Dict
import config
from core.llm_client import get_client


def _load_prompt(name: str) -> str:
    return (config.PROMPTS_DIR / name).read_text(encoding="utf-8")


class OutlineGenerator:
    def __init__(self, book_name: str = "new_book"):
        self.book_name = book_name
        self.outline: str = ""

    def generate(self, requirements: str, reference: str = "",
                 stream: bool = False):
        """
        生成大纲。
        requirements: 用户的创作要求
        reference: 参考资料（可以是拆书得到的全书画像、或者用户提供的灵感）
        """
        client = get_client()
        prompt_tpl = _load_prompt("outline.txt")
        prompt = prompt_tpl.format(
            reference=reference or "（无参考资料，自由创作）",
            requirements=requirements,
        )

        if stream:
            return client.ask_stream(prompt, system="你是资深网络小说策划编辑。")

        result = client.ask(prompt, system="你是资深网络小说策划编辑。")
        self.outline = result
        self._save()
        return result

    def refine_outline(self, outline: str, feedback: str, stream: bool = False):
        """根据反馈修改大纲。"""
        client = get_client()
        prompt = (
            f"以下是一份小说大纲：\n{outline}\n\n"
            f"请根据以下修改意见调整大纲：\n{feedback}\n\n"
            f"输出调整后的完整大纲。"
        )
        if stream:
            return client.ask_stream(prompt, system="你是资深网络小说策划编辑。")
        result = client.ask(prompt, system="你是资深网络小说策划编辑。")
        self.outline = result
        self._save()
        return result

    def _save(self):
        path = config.OUTPUTS_DIR / f"{self.book_name}_大纲.md"
        path.write_text(self.outline, encoding="utf-8")
        print(f"[大纲] 已保存到: {path}")
