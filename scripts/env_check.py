#!/usr/bin/env python3
"""
環境自動検証スクリプト
- Pythonバージョン
- requirements.txtの整合性
- 主要ツール（pytest, mypy, sqlite3, ttkbootstrap等）の存在
"""
import sys
import subprocess
import pkg_resources

REQUIRED_PYTHON = (3, 8)
REQUIRED_PACKAGES = [
    'pytest', 'mypy', 'sqlite3', 'ttkbootstrap'
]

print("[環境チェック] Pythonバージョン: {}.{}".format(sys.version_info.major, sys.version_info.minor))
if sys.version_info < REQUIRED_PYTHON:
    print(f"❌ Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]} 以上が必要です")
    sys.exit(1)
else:
    print("✅ PythonバージョンOK")

print("[環境チェック] requirements.txtのパッケージ整合性を確認...")
try:
    pkg_resources.require(open('requirements.txt').readlines())
    print("✅ requirements.txt OK")
except Exception as e:
    print(f"❌ requirements.txtのパッケージに問題があります: {e}")
    sys.exit(1)

print("[環境チェック] 主要ツールの存在確認...")
for pkg in REQUIRED_PACKAGES:
    try:
        __import__(pkg)
        print(f"✅ {pkg} インポートOK")
    except ImportError:
        print(f"❌ {pkg} がインストールされていません")
        sys.exit(1)

print("[環境チェック] 全てのチェックに合格しました！") 