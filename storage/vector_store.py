"""
向量存储 - 支持两种检索模式，自动选择：
  1. Embedding 模式：使用 LLM 的 embedding API + FAISS（需要 API 支持）
  2. TF-IDF 模式：jieba 分词 + 余弦相似度（纯本地，无需 API，默认可用）
"""
import json
import math
import re
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
import jieba
import config


class VectorStore:
    def __init__(self, name: str = "default"):
        self.name = name
        self.store_dir = config.KNOWLEDGE_DIR / name
        self.store_dir.mkdir(exist_ok=True)
        self.chunks: List[str] = []
        self.metadata: List[Dict] = []
        self._use_embedding = False
        self._faiss_index = None
        self._tfidf_matrix = None
        self._vocab: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}

    # ---------- 构建索引 ----------
    def build(self, chunks: List[str], metadata: List[Dict] = None,
              use_embedding: bool = False):
        """对文本块建立索引。use_embedding=True 尝试用向量 API。"""
        self.chunks = chunks
        self.metadata = metadata or [{} for _ in chunks]

        if use_embedding:
            ok = self._build_embedding_index()
            if ok:
                self._use_embedding = True
                self.save()
                print(f"[向量库] 使用 Embedding 模式，共 {len(chunks)} 块")
                return

        # 回退到 TF-IDF
        self._build_tfidf_index()
        self._use_embedding = False
        self.save()
        print(f"[向量库] 使用 TF-IDF 模式，共 {len(chunks)} 块")

    def _build_embedding_index(self) -> bool:
        try:
            import faiss
            from core.llm_client import get_client
            client = get_client()
            embeddings = client.embed(self.chunks)
            if embeddings is None:
                return False
            matrix = np.array(embeddings, dtype="float32")
            # 归一化以便内积 = 余弦
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            matrix = matrix / np.maximum(norms, 1e-10)
            dim = matrix.shape[1]
            self._faiss_index = faiss.IndexFlatIP(dim)
            self._faiss_index.add(matrix)
            return True
        except Exception as e:
            print(f"[Embedding 索引构建失败] {e}")
            return False

    def _build_tfidf_index(self):
        # 分词
        tokenized = [self._tokenize(c) for c in self.chunks]
        # 构建词表
        vocab: Dict[str, int] = {}
        for tokens in tokenized:
            for t in set(tokens):
                if t not in vocab:
                    vocab[t] = len(vocab)
        self._vocab = vocab

        # 计算 IDF
        n_docs = len(tokenized)
        idf = {}
        for word, idx in vocab.items():
            df = sum(1 for tokens in tokenized if word in tokens)
            idf[word] = math.log((n_docs + 1) / (df + 1)) + 1
        self._idf = idf

        # 构建 TF-IDF 矩阵
        matrix = np.zeros((n_docs, len(vocab)), dtype="float32")
        for i, tokens in enumerate(tokenized):
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            for word, count in tf.items():
                j = vocab[word]
                matrix[i, j] = count * idf[word]
        # L2 归一化
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        matrix = matrix / np.maximum(norms, 1e-10)
        self._tfidf_matrix = matrix

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        # 去标点，jieba 分词，过滤单字和停用词
        text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", " ", text)
        words = jieba.lcut(text)
        stop = set("的了是在我有和就不人都一上也很到说要去你会着没有看好自己这那")
        return [w.strip() for w in words if len(w.strip()) > 1 and w.strip() not in stop]

    # ---------- 检索 ----------
    def search(self, query: str, top_k: int = None) -> List[Dict]:
        """检索最相关的文本块，返回 [{chunk, metadata, score}]"""
        top_k = top_k or config.TOP_K
        if not self.chunks:
            return []

        if self._use_embedding:
            return self._search_embedding(query, top_k)
        return self._search_tfidf(query, top_k)

    def _search_embedding(self, query: str, top_k: int) -> List[Dict]:
        from core.llm_client import get_client
        emb = get_client().embed([query])
        if emb is None:
            return self._search_tfidf(query, top_k)
        vec = np.array(emb, dtype="float32")
        vec = vec / np.maximum(np.linalg.norm(vec), 1e-10)
        scores, indices = self._faiss_index.search(vec, min(top_k, len(self.chunks)))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                results.append({
                    "chunk": self.chunks[idx],
                    "metadata": self.metadata[idx],
                    "score": float(score),
                })
        return results

    def _search_tfidf(self, query: str, top_k: int) -> List[Dict]:
        tokens = self._tokenize(query)
        if not tokens or self._tfidf_matrix is None:
            return []
        q_vec = np.zeros(len(self._vocab), dtype="float32")
        for t in tokens:
            if t in self._vocab:
                q_vec[self._vocab[t]] += self._idf.get(t, 1.0)
        norm = np.linalg.norm(q_vec)
        if norm == 0:
            return []
        q_vec = q_vec / norm
        scores = self._tfidf_matrix @ q_vec
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [
            {
                "chunk": self.chunks[i],
                "metadata": self.metadata[i],
                "score": float(scores[i]),
            }
            for i in top_indices if scores[i] > 0
        ]

    # ---------- 持久化 ----------
    def save(self):
        data = {
            "chunks": self.chunks,
            "metadata": self.metadata,
            "use_embedding": self._use_embedding,
            "vocab": self._vocab,
            "idf": self._idf,
        }
        (self.store_dir / "index.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if self._tfidf_matrix is not None:
            np.save(self.store_dir / "tfidf.npy", self._tfidf_matrix)
        if self._faiss_index is not None:
            import faiss
            faiss.write_index(self._faiss_index, str(self.store_dir / "faiss.index"))

    def load(self) -> bool:
        idx_file = self.store_dir / "index.json"
        if not idx_file.exists():
            return False
        data = json.loads(idx_file.read_text(encoding="utf-8"))
        self.chunks = data["chunks"]
        self.metadata = data["metadata"]
        self._use_embedding = data["use_embedding"]
        self._vocab = data.get("vocab", {})
        self._idf = data.get("idf", {})

        tfidf_file = self.store_dir / "tfidf.npy"
        if tfidf_file.exists():
            self._tfidf_matrix = np.load(tfidf_file)

        faiss_file = self.store_dir / "faiss.index"
        if faiss_file.exists():
            import faiss
            self._faiss_index = faiss.read_index(str(faiss_file))
        return True
