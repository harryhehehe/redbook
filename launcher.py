"""EXE 启动入口：启动 Streamlit 并自动打开浏览器。

打包后双击 exe → 弹出控制台 → 自动开浏览器到 http://localhost:8501
关闭控制台窗口即退出整个应用。
"""
from __future__ import annotations
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _resource_path(*parts) -> Path:
    """兼容开发模式和 PyInstaller 打包模式的资源路径。"""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)).resolve()
    return base.joinpath(*parts)


def _open_browser_when_ready(url: str, delay: float = 2.5):
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main():
    # 让 streamlit 内部能找到打包进来的 streamlit_app.py 和 app/ 目录
    app_file = _resource_path("streamlit_app.py")
    if not app_file.exists():
        print(f"[启动失败] 找不到 {app_file}")
        input("按回车退出...")
        sys.exit(1)

    # 切到打包目录，让相对路径（structured/, .env 等）能解析
    os.chdir(_resource_path())

    # 显式禁用使用统计、headless 模式
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    os.environ.setdefault("STREAMLIT_GLOBAL_DEVELOPMENT_MODE", "false")

    port = 8501
    url = f"http://localhost:{port}"

    # 后台等服务起来再开浏览器
    threading.Thread(
        target=_open_browser_when_ready,
        args=(url,),
        daemon=True,
    ).start()

    print("=" * 60)
    print("  小红书数学家教帖子生成器")
    print("=" * 60)
    print(f"  正在启动… 浏览器会自动打开 {url}")
    print(f"  没自动打开就手动访问 {url}")
    print(f"  关闭此窗口即退出程序")
    print("=" * 60)

    # 用 streamlit 内部 API 启动（避开 CLI 的 sys.argv 问题）
    from streamlit.web import cli as stcli
    sys.argv = [
        "streamlit", "run",
        str(app_file),
        f"--server.port={port}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
