#!/usr/bin/env python3
"""
外部データセットからタグ・キーワードの頻度・共起情報を集計するスクリプト
- backup/external_datasets/配下のCSV等を対象
- タグ・キーワードの出現頻度、共起（同時出現）パターンを集計
- 結果はbackup/tag_stats/配下にJSONで保存
- 今後のAI推論強化や類義語抽出等の基礎データとする
"""
import os
import json
import csv
import datetime
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Dict, Set

# --- 定数 ---
DATASET_DIR = Path('backup/external_datasets')
STATS_DIR = Path('backup/tag_stats')
STATS_DIR.mkdir(parents=True, exist_ok=True)

# --- 対象ファイル名 ---
DATASET_FILES = [
    'huggingface_prompts.csv',
]

# --- ユーティリティ ---
def parse_csv_words(csv_path: Path) -> List[List[str]]:
    """
    1行ごとに単語リストとして返す（共起集計用）
    """
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                # カンマ区切りで複数単語が入っている場合も考慮
                words = [w.strip().lower() for w in line.split(',') if 2 < len(w.strip()) < 40]
                if words:
                    rows.append(words)
    return rows



def main():
    freq_counter = Counter()
    cooccur_counter = defaultdict(Counter)  # {tag: Counter({co_tag: count, ...})}
    all_tags = set()
    # HuggingFaceプロンプト
    hf_csv = DATASET_DIR / 'huggingface_prompts.csv'
    if hf_csv.exists():
        rows = parse_csv_words(hf_csv)
        for words in rows:
            freq_counter.update(words)
            all_tags.update(words)
            # 共起集計
            for i, w1 in enumerate(words):
                for w2 in words[i+1:]:
                    if w1 != w2:
                        cooccur_counter[w1][w2] += 1
                        cooccur_counter[w2][w1] += 1

    # 保存
    dt = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    freq_path = STATS_DIR / f'tag_freq_{dt}.json'
    cooccur_path = STATS_DIR / f'tag_cooccur_{dt}.json'
    with open(freq_path, 'w', encoding='utf-8') as f:
        json.dump(freq_counter.most_common(), f, ensure_ascii=False, indent=2)
    with open(cooccur_path, 'w', encoding='utf-8') as f:
        # Counterはdictに変換
        cooccur_dict = {k: v.most_common(20) for k, v in cooccur_counter.items()}
        json.dump(cooccur_dict, f, ensure_ascii=False, indent=2)
    print(f'[INFO] 頻度データ: {freq_path}')
    print(f'[INFO] 共起データ: {cooccur_path}')

if __name__ == '__main__':
    main() 