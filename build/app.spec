import os

ROOT = os.path.abspath(os.getcwd())
ICON = os.path.join(ROOT, "assets", "icon.ico")
icon_arg = ICON if os.path.exists(ICON) else None

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[(os.path.join(ROOT, "config.example.json"), ".")],
    hiddenimports=["win32gui", "win32api", "win32con"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="GitHubActionsTray",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon=icon_arg,
)
