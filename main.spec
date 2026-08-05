# -*- mode: python ; coding: utf-8 -*-
import os

# Иконка .exe: положи .ico-файл сюда перед сборкой (см. README). Если файла
# ещё нет, просто пропускаем параметр - PyInstaller соберёт .exe со своей
# иконкой по умолчанию вместо падения со сборки.
ICON_PATH = 'assets/icon.ico'
icon = ICON_PATH if os.path.isfile(ICON_PATH) else None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # data/config/*.json и data/locale/*.json читаются ConfigLoader/Loc, а
    # assets/{sprites,sounds,music} - SpriteManager/SoundManager/MusicManager,
    # все пятеро в рантайме ищут свою папку относительно sys._MEIPASS внутри
    # собранного .exe (см. соответствующие _default_*_root/_dir в каждом
    # модуле) — без этой строки .exe не найдёт ни конфиги/текст, ни
    # спрайты/звуки/музыку и откатится на дефолты/примитивы/тишину.
    datas=[
        ('data/config', 'data/config'),
        ('data/locale', 'data/locale'),
        ('assets/sprites', 'assets/sprites'),
        ('assets/sounds', 'assets/sounds'),
        ('assets/music', 'assets/music'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Concession',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)
