"""
AI 写作助手 - 全局配置
支持任意 OpenAI 兼容 API（OpenAI / DeepSeek / 智谱 / Kimi / 通义千问 等）
"""
import os
from pathlib import Path

# ========== 路径配置 ==========
BASE_DIR = Path(__file__).resolve().parent
BOOKS_DIR = BASE_DIR / "books"            # 存放投喂的文档
KNOWLEDGE_DIR = BASE_DIR / "knowledge"    # 拆书后的知识库
OUTPUTS_DIR = BASE_DIR / "outputs"        # 生成的大纲、写作内容
PROMPTS_DIR = BASE_DIR / "prompts"        # Prompt 模板

for d in [BOOKS_DIR, KNOWLEDGE_DIR, OUTPUTS_DIR, PROMPTS_DIR]:
    d.mkdir(exist_ok=True)

# ========== LLM 配置 ==========
# 推荐：复制 .env.example 为 .env 并填写；或直接改这里
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

# Embedding 配置（用于向量化；若 API 不支持则自动回退到 TF-IDF）
EMBEDDING_API_KEY = os.environ.get("EMBEDDING_API_KEY", LLM_API_KEY)
EMBEDDING_BASE_URL = os.environ.get("EMBEDDING_BASE_URL", LLM_BASE_URL)
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "")  # 留空则用 TF-IDF 本地方案

# ========== 拆书配置 ==========
CHUNK_SIZE = 1200        # 每个文本块的字符数
CHUNK_OVERLAP = 200      # 块之间重叠字符数
TOP_K = 5                # 检索时返回的相关块数量

# ========== 写作配置 ==========
DEFAULT_WORD_COUNT = 2000   # 默认每段写作字数
TEMPERATURE = 0.7           # 生成温度
