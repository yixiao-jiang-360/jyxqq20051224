"""
文档解析器 - 读取 txt / docx / pdf 文件，提取纯文本
"""
from pathlib import Path
from typing import Optional
from docx import Document as DocxDocument


class DocumentParser:
    SUPPORTED_EXT = {".txt", ".docx", ".pdf"}

    @staticmethod
    def parse(file_path: str) -> Optional[str]:
        """解析文档，返回纯文本内容。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        ext = path.suffix.lower()
        if ext == ".txt":
            return DocumentParser._parse_txt(path)
        elif ext == ".docx":
            return DocumentParser._parse_docx(path)
        elif ext == ".pdf":
            return DocumentParser._parse_pdf(path)
        else:
            raise ValueError(
                f"不支持的文件格式: {ext}，支持: {DocumentParser.SUPPORTED_EXT}"
            )

    @staticmethod
    def _parse_txt(path: Path) -> str:
        # 尝试多种编码
        for enc in ["utf-8", "gbk", "gb18030", "big5"]:
            try:
                return path.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
        # 最后兜底
        return path.read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def _parse_docx(path: Path) -> str:
        doc = DocxDocument(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    @staticmethod
    def _parse_pdf(path: Path) -> str:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    @staticmethod
    def chunk_text(text: str, chunk_size: int = None, overlap: int = None):
        """
        将长文本切分为块。优先按段落/章节切分，不足再合并。
        返回 List[str]
        """
        import config
        chunk_size = chunk_size or config.CHUNK_SIZE
        overlap = overlap or config.CHUNK_OVERLAP

        # 按双换行（段落）切分
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if not paragraphs:
            return []

        chunks = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) + 1 <= chunk_size:
                current = (current + "\n" + para).strip()
            else:
                if current:
                    chunks.append(current)
                # 单段过长，按字符硬切
                if len(para) > chunk_size:
                    for i in range(0, len(para), chunk_size - overlap):
                        chunks.append(para[i:i + chunk_size])
                    current = ""
                else:
                    current = para

        if current:
            chunks.append(current)
        return chunks
