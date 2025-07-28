#!/usr/bin/env python3
"""
外部データセット（Stable Diffusionプロンプト等）から
頻出キーワードを抽出し、最適なカテゴリへ自動分類・追加するスクリプト
- 既存カテゴリ構造は維持
- タグ自体は増やさず、キーワードのみ追加
- 外部データセットはbackup/external_datasets/配下に保存
- 差分バックアップ・処理ログも記録
"""
import os
import sys
import json
import csv
import datetime
import requests
from pathlib import Path
from typing import List, Dict, Set

# --- 既存モジュールの活用 ---
sys.path.append(str(Path(__file__).parent.parent))
from modules.category_manager import (
    load_category_keywords, save_category_keywords, add_category_keyword,
    get_all_categories, calculate_keyword_score, is_valid_category
)

# --- 定数 ---
BACKUP_DIR = Path('backup')
DATASET_DIR = BACKUP_DIR / 'external_datasets'
CATEGORY_KEYWORDS_FILE = Path('resources/config/category_keywords.json')
LOG_FILE = Path('logs/auto_expand_categories.log')

# --- データセットURL ---
HUGGINGFACE_PROMPT_URL = 'https://huggingface.co/datasets/Gustavosta/Stable-Diffusion-Prompts/resolve/main/prompts.csv'

# --- ユーティリティ ---
def log(msg: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.datetime.now().isoformat()} {msg}\n")
    print(msg)

def backup_keywords():
    dt = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = BACKUP_DIR / f'category_keywords_{dt}.json'
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if CATEGORY_KEYWORDS_FILE.exists():
        with open(CATEGORY_KEYWORDS_FILE, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
    log(f"[バックアップ] {backup_path} に保存しました")

def download_file(url: str, save_path: Path):
    save_path.parent.mkdir(parents=True, exist_ok=True)
    if save_path.exists():
        log(f"[スキップ] 既に存在: {save_path}")
        return
    log(f"[ダウンロード] {url} → {save_path}")
    r = requests.get(url)
    r.raise_for_status()
    with open(save_path, 'wb') as f:
        f.write(r.content)

def parse_huggingface_prompts(csv_path: Path) -> Set[str]:
    prompts = set()
    with open(csv_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                # カンマ区切りで複数プロンプトが入っている場合も考慮
                for part in line.split(','):
                    word = part.strip().lower()
                    if 2 < len(word) < 40:
                        prompts.add(word)
    return prompts



def auto_classify_keyword(keyword: str, categories: List[str], category_keywords: Dict[str, List[str]]) -> str:
    # 既存カテゴリごとにスコアを計算し、最も高いカテゴリに割り当て
    best_cat = None
    best_score = 0
    for cat in categories:
        for ref_kw in category_keywords.get(cat, []):
            score = calculate_keyword_score(keyword, ref_kw)
            if score > best_score:
                best_score = score
                best_cat = cat
    return best_cat if best_score > 0 else None

def main():
    log("=== カテゴリ自動拡充 開始 ===")
    backup_keywords()
    # データセットDL
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    hf_csv = DATASET_DIR / 'huggingface_prompts.csv'
    try:
        download_file(HUGGINGFACE_PROMPT_URL, hf_csv)
    except Exception as e:
        log(f"[エラー] データセットDL失敗: {e}")
        return
    # パース
    prompt_words = parse_huggingface_prompts(hf_csv)
    all_words = prompt_words
    log(f"[INFO] 総キーワード数: {len(all_words)}")
    # 既存キーワード取得
    category_keywords = load_category_keywords()
    categories = list(category_keywords.keys())
    # 既存キーワード集合
    existing = set()
    for kws in category_keywords.values():
        existing.update([k.lower() for k in kws])
    # 新規キーワードのみ抽出
    new_words = [w for w in all_words if w not in existing]
    log(f"[INFO] 新規候補キーワード数: {len(new_words)}")
    # 自動分類・追加
    added_count = 0
    for word in new_words:
        cat = auto_classify_keyword(word, categories, category_keywords)
        if cat and is_valid_category(cat):
            if add_category_keyword(cat, word):
                log(f"[追加] {word} → {cat}")
                added_count += 1
    log(f"[完了] 追加キーワード数: {added_count}")
    log("=== カテゴリ自動拡充 終了 ===")

if __name__ == '__main__':
    main() 