#!/usr/bin/env python3
"""
ドキュメントのリンク切れ自動チェックスクリプト
- README.md, AI_REFERENCE_GUIDE.md, 技術仕様書_関数・ファイルパス一覧.md, ToDoリスト.md など
- http/https, fileパス両方を検査
"""
import re
import os
import requests

DOCS = [
    'README.md',
    'AI_REFERENCE_GUIDE.md',
    '技術仕様書_関数・ファイルパス一覧.md',
    'ToDoリスト.md',
]

URL_PATTERN = re.compile(r'(https?://[\w\-./?%&=:#]+)')
FILE_PATTERN = re.compile(r'\[([^\]]+\.md)\]')

print('[linkcheck] ドキュメントのリンク切れチェックを開始')
for doc in DOCS:
    if not os.path.exists(doc):
        print(f'[警告] {doc} が存在しません')
        continue
    with open(doc, encoding='utf-8') as f:
        content = f.read()
    # URLチェック
    for url in URL_PATTERN.findall(content):
        try:
            r = requests.head(url, timeout=5)
            if r.status_code >= 400:
                print(f'[リンク切れ] {doc}: {url} (status {r.status_code})')
        except Exception as e:
            print(f'[リンク切れ] {doc}: {url} ({e})')
    # ファイルパスチェック
    for fname in FILE_PATTERN.findall(content):
        if not os.path.exists(fname):
            print(f'[ファイルリンク切れ] {doc}: {fname}')
print('[linkcheck] 完了') 