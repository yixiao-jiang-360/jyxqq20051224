"""
拆书模块 - 将投喂的文档拆解、吸收、结构化存储
功能：
  1. 解析文档 → 分块
  2. 建立向量索引（用于检索）
  3. 用 LLM 逐块分析，提取人物/情节/设定等结构化知识
  4. 汇总全书画像
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
import config
from core.document_parser import DocumentParser
from storage.vector_store import VectorStore
from core.llm_client import get_client


def _load_prompt(name: str) -> str:
    return (config.PROMPTS_DIR / name).read_text(encoding="utf-8")


class BookAnalyzer:
    def __init__(self, book_name: str):
        self.book_name = book_name
        self.vector_store = VectorStore(book_name)
        self.analysis: List[Dict] = []   # 每块的结构化分析结果
        self.book_profile: Dict = {}     # 全书汇总画像

    # ---------- 第一步：解析 + 分块 + 建索引 ----------
    def ingest(self, file_path: str, use_embedding: bool = False) -> int:
        """投喂一本书，解析并建立索引。返回块数。"""
        print(f"[拆书] 正在解析: {file_path}")
        text = DocumentParser.parse(file_path)
        print(f"[拆书] 文本长度: {len(text)} 字符")

        chunks = DocumentParser.chunk_text(text)
        print(f"[拆书] 切分为 {len(chunks)} 块")

        metadata = [{"chunk_id": i, "source": Path(file_path).name} for i in range(len(chunks))]
        self.vector_store.build(chunks, metadata, use_embedding=use_embedding)
        return len(chunks)

    # ---------- 第二步：逐块 LLM 分析 ----------
    def analyze_chunks(self, max_chunks: int = None) -> List[Dict]:
        """用 LLM 分析每个文本块，提取结构化信息。"""
        if not self.vector_store.chunks:
            raise RuntimeError("请先调用 ingest() 投喂文档")

        client = get_client()
        prompt_tpl = _load_prompt("analyze_book.txt")
        chunks = self.vector_store.chunks
        if max_chunks:
            chunks = chunks[:max_chunks]

        self.analysis = []
        for i, chunk in enumerate(chunks):
            print(f"[拆书] 分析第 {i+1}/{len(chunks)} 块...", end="\r")
            prompt = prompt_tpl.format(content=chunk)
            try:
                resp = client.ask(prompt, system="你是专业的文学分析专家。")
                parsed = self._parse_json(resp)
                parsed["chunk_id"] = i
                self.analysis.append(parsed)
            except Exception as e:
                print(f"\n[警告] 第 {i+1} 块分析失败: {e}")
                self.analysis.append({"chunk_id": i, "raw": resp})

        print(f"\n[拆书] 分析完成，共 {len(self.analysis)} 块")
        self._save_analysis()
        return self.analysis

    @staticmethod
    def _parse_json(text: str) -> Dict:
        """从 LLM 输出中提取 JSON。"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except Exception:
            pass
        # 提取 ```json ... ``` 块
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
        # 提取最外层 {}
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        return {"raw": text}

    # ---------- 第三步：汇总全书画像 ----------
    def build_profile(self) -> Dict:
        """汇总所有块的分析，生成全书画像。"""
        if not self.analysis:
            raise RuntimeError("请先调用 analyze_chunks()")

        all_chars = []
        all_themes = []
        all_keywords = []
        summaries = []
        settings = []

        for a in self.analysis:
            all_chars.extend(a.get("characters", []))
            all_themes.extend(a.get("themes", []))
            all_keywords.extend(a.get("keywords", []))
            if a.get("plot_summary"):
                summaries.append(a["plot_summary"])
            if a.get("setting"):
                settings.append(a["setting"])

        # 去重
        def dedup(seq):
            seen = set()
            out = []
            for x in seq:
                if x and x not in seen:
                    seen.add(x)
                    out.append(x)
            return out

        # 用 LLM 做最终汇总
        client = get_client()
        merge_prompt = (
            f"以下是一部小说各片段的分析结果，请汇总成完整的全书画像。\n\n"
            f"人物（去重整合）：{dedup(all_chars)}\n"
            f"背景设定：{settings[:5]}\n"
            f"主题：{dedup(all_themes)}\n"
            f"各段情节摘要：{summaries[:10]}\n\n"
            f"请输出 JSON：\n"
            f'{{"title": "暂定书名", "genre": "题材", "setting": "完整世界观", '
            f'"characters": ["人物：身份性格"], "main_plot": "全书主线情节", '
            f'"themes": ["主题"], "writing_style": "文风", "keywords": ["关键词"]}}'
        )
        try:
            resp = client.ask(merge_prompt, system="你是资深文学编辑。")
            profile = self._parse_json(resp)
        except Exception as e:
            print(f"[警告] 汇总画像生成失败: {e}")
            profile = {
                "characters": dedup(all_chars),
                "themes": dedup(all_themes),
                "keywords": dedup(all_keywords),
                "plot_summaries": summaries,
            }

        self.book_profile = profile
        self._save_profile()
        return profile

    # ---------- 检索相关片段 ----------
    def retrieve(self, query: str, top_k: int = None) -> List[Dict]:
        """根据查询检索相关内容。"""
        return self.vector_store.search(query, top_k)

    # ---------- 持久化 ----------
    def _save_analysis(self):
        path = config.KNOWLEDGE_DIR / self.book_name / "analysis.json"
        path.write_text(json.dumps(self.analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    def _save_profile(self):
        path = config.KNOWLEDGE_DIR / self.book_name / "profile.json"
        path.write_text(json.dumps(self.book_profile, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> bool:
        """加载已有的拆书结果。"""
        base = config.KNOWLEDGE_DIR / self.book_name
        if not (base / "index.json").exists():
            return False
        self.vector_store.load()
        if (base / "analysis.json").exists():
            self.analysis = json.loads((base / "analysis.json").read_text(encoding="utf-8"))
        if (base / "profile.json").exists():
            self.book_profile = json.loads((base / "profile.json").read_text(encoding="utf-8"))
        return True
