"""
AI 写作助手 - 主入口
用法:
  python main.py            # 启动 CLI
  python main.py web        # 启动 Web 界面
"""
import sys


def main():
    # 加载 .env 配置
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    if len(sys.argv) > 1 and sys.argv[1] == "web":
        from ui.web import run_web
        run_web()
    else:
        from ui.cli import main as cli_main
        cli_main()


if __name__ == "__main__":
    main()
