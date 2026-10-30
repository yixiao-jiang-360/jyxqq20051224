"""
AI 写作模块 - 基于大纲/细纲生成正文
"""
from pathlib import Path
from typing import Optional, List
import config
from core.llm_client import get_client
from storage.vector_store import VectorStore


def _load_prompt(name: str) -> str:
    return (config.PROMPTS_DIR / name).read_text(encoding="utf-8")


class Writer:
    def __init__(self, book_name: str = "new_book"):
        self.book_name = book_name
        self.knowledge_store: Optional[VectorStore] = None

    def bind_knowledge(self, knowledge_book: str):
        """绑定一个已拆书的知识库，写作时自动检索相关内容作为参考。"""
        store = VectorStore(knowledge_book)
        if store.load():
            self.knowledge_store = store
            print(f"[写作] 已绑定知识库: {knowledge_book}")
        else:
            print(f"[写作] 知识库不存在: {knowledge_book}")

    def write_chapter(self, chapter_outline: str, context: str = "",
                      requirements: str = "", word_count: int = None,
                      stream: bool = False):
        """
        写一个章节。
        chapter_outline: 本章细纲
        context: 前文回顾（上一章结尾）
        requirements: 额外写作要求
        word_count: 目标字数
        """
        word_count = word_count or config.DEFAULT_WORD_COUNT
        client = get_client()

        # 若绑定了知识库，检索相关内容
        knowledge_context = ""
        if self.knowledge_store:
            results = self.knowledge_store.search(chapter_outline, top_k=3)
            if results:
                knowledge_context = "\n\n【相关参考资料】\n" + "\n---\n".join(
                    r["chunk"][:500] for r in results
                )

        prompt_tpl = _load_prompt("write_chapter.txt")
        prompt = prompt_tpl.format(
            chapter_outline=chapter_outline,
            context=context or "（开篇）",
            requirements=requirements + knowledge_context,
            word_count=word_count,
        )

        if stream:
            return client.ask_stream(prompt, system="你是才华横溢的网络小说作家。")

        result = client.ask(prompt, system="你是才华横溢的网络小说作家。")
        return result

    def continue_writing(self, current_text: str, requirements: str = "",
                         word_count: int = None, stream: bool = False):
        """续写当前文本。"""
        word_count = word_count or config.DEFAULT_WORD_COUNT
        client = get_client()
        prompt = (
            f"以下是小说的当前内容，请接着往下写，续写约 {word_count} 字。\n\n"
            f"要求：{requirements}\n\n"
            f"当前内容：\n{current_text[-1500:]}\n\n"
            f"续写："
        )
        if stream:
            return client.ask_stream(prompt, system="你是才华横溢的网络小说作家。")
        return client.ask(prompt, system="你是才华横溢的网络小说作家。")

    def polish(self, text: str, instructions: str = "润色文字，提升文采",
               stream: bool = False):
        """润色/改写已有文本。"""
        client = get_client()
        prompt = f"请对以下小说文本进行{instructions}：\n\n{text}\n\n输出修改后的完整文本。"
        if stream:
            return client.ask_stream(prompt, system="你是资深文字编辑。")
        return client.ask(prompt, system="你是资深文字编辑。")

    def save_chapter(self, chapter_num: int, title: str, content: str):
        path = config.OUTPUTS_DIR / f"{self.book_name}_第{chapter_num}章.md"
        path.write_text(f"# {title}\n\n{content}", encoding="utf-8")
        print(f"[写作] 已保存: {path}")
