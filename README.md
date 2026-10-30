# AI 网络小说写作助手

为网络小说作者打造的 AI 辅助写作工具，支持拆书学习、大纲生成、AI 写作等功能。

## 功能

- 📚 **拆书学习**：投喂 txt / docx / pdf，自动解析、分块、向量化，并提取人物、情节、设定等结构化知识
- 📋 **大纲细纲**：基于拆书知识或你的创作需求，生成完整大纲（世界观、人物、卷纲、章节细纲）
- ✍️ **AI 写作**：按细纲生成章节正文，可绑定知识库自动检索相关内容
- 🔄 **续写 / 润色**：续写已有内容，或按要求改写润色

## 快速开始

### 1. 配置 API

复制 `.env.example` 为 `.env`，填入你的 API Key：

```bash
cp .env.example .env
```

支持任意 **OpenAI 兼容 API**（DeepSeek / 智谱 GLM / Kimi / 通义千问 / OpenAI 等）：

```
LLM_API_KEY=你的API_KEY
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

> Embedding 可选。不填则使用本地 TF-IDF（jieba）检索，无需额外 API。

### 2. 启动

```bash
# 命令行界面
python main.py

# Web 界面
python main.py web
# 然后浏览器打开 http://127.0.0.1:5000
```

## 使用流程

1. **拆书**：上传文档 → 建立知识库（可选 AI 分析提取人物/情节）
2. **生成大纲**：填写创作要求，可参考已拆书的知识库
3. **写作**：填写本章细纲 → AI 生成正文 → 保存章节
4. **续写/润色**：粘贴原文 → 选择续写或润色

## 目录结构

```
.
├── core/              # 核心模块
│   ├── llm_client.py      # LLM 客户端（OpenAI 兼容）
│   ├── document_parser.py # 文档解析（txt/docx/pdf）
│   ├── book_analyzer.py   # 拆书分析
│   ├── outline_generator.py # 大纲生成
│   └── writer.py          # AI 写作
├── storage/
│   └── vector_store.py    # 向量存储（FAISS / TF-IDF）
├── prompts/           # Prompt 模板
├── books/             # 投喂的文档
├── knowledge/         # 拆书后的知识库
├── outputs/           # 生成的大纲和章节
├── ui/
│   ├── cli.py         # 命令行界面
│   └── web.py         # Web 界面
└── config.py          # 配置
```
