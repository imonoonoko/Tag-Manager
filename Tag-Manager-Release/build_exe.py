#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tag Manager .exe ビルドスクリプト
PyInstallerを使用して.exeファイルを作成します
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_pyinstaller():
    """PyInstallerがインストールされているかチェック"""
    try:
        import PyInstaller
        print("✓ PyInstaller が見つかりました")
        return True
    except ImportError:
        print("✗ PyInstaller が見つかりません")
        print("インストール中...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        return True

def create_spec_file():
    """PyInstallerのspecファイルを作成"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('modules', 'modules'),
    ],
    hiddenimports=[
        'modules.ai_predictor',
        'modules.category_manager',
        'modules.common_words',
        'modules.config',
        'modules.constants',
        'modules.context_analyzer',
        'modules.customization',
        'modules.dialogs',
        'modules.huggingface_manager',
        'modules.local_hf_manager',
        'modules.prompt_translator',
        'modules.prompt_translator_dialog',
        'modules.tag_manager',
        'modules.theme_manager',
        'modules.ui_ai_features',
        'modules.ui_dialogs',
        'modules.ui_export_import',
        'modules.ui_main',
        'modules.ui_main_lightweight',
        'modules.ui_utils',
        'modules.spec_checker.comparator',
        'modules.spec_checker.extractor',
        'modules.spec_checker.filepath_checker',
        'modules.spec_checker.import_checker',
        'modules.spec_checker.reporter',
        'modules.spec_checker.spec_parser',
        'modules.spec_checker.updater',
        'ttkbootstrap',
        'tkinter',
        'sqlite3',
        'json',
        'pathlib',
        'logging',
        'threading',
        'queue',
        'requests',
        'transformers',
        'torch',
        'numpy',
        'pandas',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Tag-Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/プロンプトタグ管理ツール.ico',
)
'''
    
    with open('Tag-Manager.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    print("✓ specファイルを作成しました")

def build_exe():
    """exeファイルをビルド"""
    print("exeファイルをビルド中...")
    
    # PyInstallerでビルド
    result = subprocess.run([
        'pyinstaller',
        '--clean',
        '--noconfirm',
        'Tag-Manager.spec'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ exeファイルのビルドが完了しました")
        print(f"出力先: dist/Tag-Manager.exe")
        return True
    else:
        print("✗ ビルドに失敗しました")
        print("エラー出力:")
        print(result.stderr)
        return False

def create_installer_script():
    """インストーラー用のバッチファイルを作成"""
    installer_content = '''@echo off
echo Tag Manager インストーラー
echo ========================

REM 必要なディレクトリを作成
if not exist "%USERPROFILE%\\AppData\\Local\\Tag-Manager" mkdir "%USERPROFILE%\\AppData\\Local\\Tag-Manager"
if not exist "%USERPROFILE%\\AppData\\Local\\Tag-Manager\\resources" mkdir "%USERPROFILE%\\AppData\\Local\\Tag-Manager\\resources"

REM ファイルをコピー
copy "Tag-Manager.exe" "%USERPROFILE%\\AppData\\Local\\Tag-Manager\\"
copy "resources\\*" "%USERPROFILE%\\AppData\\Local\\Tag-Manager\\resources\\" /E /I /H /Y

REM デスクトップにショートカットを作成
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = "%USERPROFILE%\\Desktop\\Tag Manager.lnk" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "%USERPROFILE%\\AppData\\Local\\Tag-Manager\\Tag-Manager.exe" >> CreateShortcut.vbs
echo oLink.WorkingDirectory = "%USERPROFILE%\\AppData\\Local\\Tag-Manager" >> CreateShortcut.vbs
echo oLink.Description = "Tag Manager" >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs
cscript //nologo CreateShortcut.vbs
del CreateShortcut.vbs

echo インストールが完了しました！
echo デスクトップにショートカットが作成されました。
pause
'''
    
    with open('install.bat', 'w', encoding='utf-8') as f:
        f.write(installer_content)
    print("✓ インストーラースクリプトを作成しました")

def main():
    """メイン処理"""
    print("Tag Manager .exe ビルドスクリプト")
    print("=" * 40)
    
    # 現在のディレクトリを確認
    if not os.path.exists('main.py'):
        print("✗ main.py が見つかりません")
        print("このスクリプトはTag-Manager-Releaseフォルダ内で実行してください")
        return False
    
    # PyInstallerの確認
    if not check_pyinstaller():
        return False
    
    # specファイルの作成
    create_spec_file()
    
    # exeファイルのビルド
    if not build_exe():
        return False
    
    # インストーラースクリプトの作成
    create_installer_script()
    
    print("\n" + "=" * 40)
    print("ビルド完了！")
    print("以下のファイルが作成されました:")
    print("- dist/Tag-Manager.exe (実行ファイル)")
    print("- install.bat (インストーラー)")
    print("\n使用方法:")
    print("1. dist/Tag-Manager.exe を直接実行")
    print("2. または install.bat を実行してインストール")
    
    return True

if __name__ == "__main__":
    main() 