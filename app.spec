# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for 小红书帖子生成器 (onedir)."""
from PyInstaller.utils.hooks import (
    collect_all, copy_metadata, collect_data_files, collect_submodules,
)

# Streamlit 的静态资源 / 元数据 / 子模块全部抓全
datas = []
binaries = []
hiddenimports = []

for pkg in [
    "streamlit", "altair", "pyarrow", "plotly", "pydeck",
    "tornado", "blinker", "watchdog", "validators", "cachetools",
    "click", "toml", "tenacity", "pympler", "rich", "gitpython",
    "pillow", "protobuf", "numpy", "pandas",
]:
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception:
        pass

# importlib.metadata 需要这些包的 dist-info 才能正常运行
for pkg in [
    "streamlit", "altair", "pandas", "numpy", "click", "tornado",
    "rich", "watchdog", "validators", "cachetools", "blinker",
    "tenacity", "toml", "protobuf", "pillow", "pyarrow",
    "openai", "reportlab", "pymupdf", "python-dotenv", "pydantic",
]:
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

# 项目自带数据 / 模板 / 范例 / 主入口 / app 模块
datas += [
    ("streamlit_app.py", "."),
    ("structured", "structured"),
    ("tests", "tests"),
    ("app", "app"),
]

hiddenimports += collect_submodules("streamlit")
hiddenimports += [
    "app", "app.data", "app.recommender", "app.prompt_builder",
    "app.llm_client", "app.renderer", "app.lead_magnet_gen", "app.cli",
    "openai", "reportlab", "fitz", "dotenv",
]


block_cipher = None

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6", "matplotlib"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="小红书帖子生成器",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="小红书帖子生成器",
)
