"""
CLI 交互界面 - 命令行使用写作助手
"""
import sys
from pathlib import Path

# 确保能 import 到 core 等模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.book_analyzer import BookAnalyzer
from core.outline_generator import OutlineGenerator
from core.writer import Writer


def print_menu():
    print("\n" + "=" * 50)
    print("  📖 AI 网络小说写作助手")
    print("=" * 50)
    print("  1. 投喂文档（拆书）")
    print("  2. 查看已拆书的知识库")
    print("  3. 生成大纲/细纲")
    print("  4. AI 写作")
    print("  5. 续写 / 润色")
    print("  0. 退出")
    print("=" * 50)


def cmd_ingest():
    path = input("请输入文档路径（txt/docx/pdf）: ").strip().strip('"').strip("'")
    if not Path(path).exists():
        print("文件不存在！")
        return
    name = input("给这本书起个名字（用于知识库标识）: ").strip() or Path(path).stem
    use_emb = input("是否使用 Embedding 向量检索？(y/N，默认 N 用本地 TF-IDF): ").strip().lower() == "y"

    analyzer = BookAnalyzer(name)
    n = analyzer.ingest(path, use_embedding=use_emb)
    print(f"已切分为 {n} 块并建立索引。")

    do_analyze = input("是否立即用 AI 逐块分析提取人物/情节？(Y/n): ").strip().lower()
    if do_analyze != "n":
        max_c = input("最多分析多少块？(回车=全部): ").strip()
        max_c = int(max_c) if max_c else None
        analyzer.analyze_chunks(max_chunks=max_c)
        print("正在生成全书画像...")
        profile = analyzer.build_profile()
        print("\n全书画像:")
        import json
        print(json.dumps(profile, ensure_ascii=False, indent=2))


def cmd_list_books():
    import config
    books = [d for d in config.KNOWLEDGE_DIR.iterdir() if d.is_dir()]
    if not books:
        print("暂无知识库。")
        return
    print("\n已有知识库:")
    for b in books:
        print(f"  - {b.name}")


def cmd_outline():
    name = input("给你的新书起个名字: ").strip() or "my_novel"
    ref_book = input("参考哪本已拆书的知识库？(留空=不参考): ").strip()

    reference = ""
    if ref_book:
        analyzer = BookAnalyzer(ref_book)
        if analyzer.load():
            import json
            reference = json.dumps(analyzer.book_profile, ensure_ascii=False)
            print(f"已加载知识库 {ref_book} 的画像作为参考。")
        else:
            print(f"知识库 {ref_book} 不存在。")

    req = input("描述你的创作要求（题材、风格、核心设定等）: ").strip()

    gen = OutlineGenerator(name)
    print("\n正在生成大纲...")
    stream = gen.generate(req, reference=reference, stream=True)
    for chunk in stream:
        print(chunk, end="", flush=True)
    print("\n[大纲已保存到 outputs/]")


def cmd_write():
    name = input("书名: ").strip() or "my_novel"
    ref_book = input("绑定哪个知识库辅助写作？(留空=不绑定): ").strip()

    writer = Writer(name)
    if ref_book:
        writer.bind_knowledge(ref_book)

    outline = input("本章细纲（要写什么内容）: ").strip()
    context = input("前文回顾（上一章结尾，可留空）: ").strip()
    req = input("额外写作要求（可留空）: ").strip()
    wc = input("目标字数（回车=2000）: ").strip()
    wc = int(wc) if wc else None

    print("\n正在写作...")
    stream = writer.write_chapter(outline, context=context, requirements=req,
                                  word_count=wc, stream=True)
    full = ""
    for chunk in stream:
        print(chunk, end="", flush=True)
        full += chunk
    print()

    save = input("\n保存本章？(Y/n): ").strip().lower()
    if save != "n":
        ch = input("第几章？: ").strip()
        title = input("章节标题: ").strip()
        writer.save_chapter(int(ch), title, full)


def cmd_polish():
    print("1. 续写  2. 润色改写")
    choice = input("选择: ").strip()
    text = input("粘贴原文（输入 END 结束）:\n")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    text = text + "\n" + "\n".join(lines)

    req = input("要求（如'续写1000字'/'提升文采'/'改得更幽默'）: ").strip()

    writer = Writer()
    if choice == "1":
        result = writer.continue_writing(text, requirements=req, stream=True)
    else:
        result = writer.polish(text, instructions=req, stream=True)

    for chunk in result:
        print(chunk, end="", flush=True)
    print()


def main():
    # 加载 .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    while True:
        print_menu()
        choice = input("请选择: ").strip()
        if choice == "0":
            print("再见！")
            break
        elif choice == "1":
            cmd_ingest()
        elif choice == "2":
            cmd_list_books()
        elif choice == "3":
            cmd_outline()
        elif choice == "4":
            cmd_write()
        elif choice == "5":
            cmd_polish()
        else:
            print("无效选择。")


if __name__ == "__main__":
    main()
