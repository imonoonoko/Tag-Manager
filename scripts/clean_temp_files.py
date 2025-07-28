#!/usr/bin/env python3
"""
キャッシュ・一時ファイル一括削除スクリプト
- __pycache__、.pytest_cache、.mypy_cache、htmlcov、logs/、*.log、*.tmp、*.bak など
"""
import os
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = [
    '__pycache__', '.pytest_cache', '.mypy_cache', 'htmlcov', 'logs'
]
EXTS = ['.log', '.tmp', '.bak']

print('[clean] 一時ファイル・キャッシュの削除を開始します')
for root, dirs, files in os.walk(PROJECT_ROOT):
    # ディレクトリ削除
    for d in dirs:
        if d in TARGETS:
            dpath = os.path.join(root, d)
            print(f'[削除] ディレクトリ: {dpath}')
            shutil.rmtree(dpath, ignore_errors=True)
    # ファイル削除
    for f in files:
        if any(f.endswith(ext) for ext in EXTS):
            fpath = os.path.join(root, f)
            print(f'[削除] ファイル: {fpath}')
            try:
                os.remove(fpath)
            except Exception:
                pass
print('[clean] 完了') 