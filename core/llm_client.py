"""
LLM 客户端 - 统一封装各类 OpenAI 兼容 API
支持：
  - 对话补全（流式 / 非流式）
  - Embedding（若模型不支持则返回 None，由上层回退到 TF-IDF）
"""
from typing import Optional, List
from openai import OpenAI
import config


class LLMClient:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or config.LLM_API_KEY
        self.base_url = base_url or config.LLM_BASE_URL
        self.model = model or config.LLM_MODEL
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "未配置 LLM_API_KEY。请在 .env 或 config.py 中设置 API Key。\n"
                    "支持任意 OpenAI 兼容服务（DeepSeek / 智谱 / Kimi / 通义等）"
                )
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    # ---------- 对话生成 ----------
    def chat(self, messages: List[dict], temperature: float = None,
             max_tokens: int = None, stream: bool = False):
        """调用对话模型。stream=True 时返回生成器，逐字产出。"""
        kwargs = dict(
            model=self.model,
            messages=messages,
            temperature=temperature if temperature is not None else config.TEMPERATURE,
            stream=stream,
        )
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        if stream:
            return self._chat_stream(kwargs)
        resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content

    def _chat_stream(self, kwargs):
        stream = self.client.chat.completions.create(**kwargs)
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    # ---------- Embedding ----------
    def embed(self, texts: List[str]) -> Optional[List[List[float]]]:
        """生成向量。若未配置 embedding 模型或调用失败，返回 None。"""
        if not config.EMBEDDING_MODEL:
            return None
        try:
            resp = self.client.embeddings.create(
                model=config.EMBEDDING_MODEL,
                input=texts,
            )
            return [d.embedding for d in resp.data]
        except Exception as e:
            print(f"[Embedding 调用失败，回退到 TF-IDF] {e}")
            return None

    # ---------- 便捷方法：单轮问答 ----------
    def ask(self, prompt: str, system: str = "", **kwargs) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, **kwargs)

    def ask_stream(self, prompt: str, system: str = "", **kwargs):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, stream=True, **kwargs)


# 单例
_default_client: Optional[LLMClient] = None


def get_client() -> LLMClient:
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
