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

# --- データセットURL（複数の代替URLを用意） ---
DATASET_URLS = [
    'https://huggingface.co/datasets/Gustavosta/Stable-Diffusion-Prompts/resolve/main/prompts.csv',
    'https://huggingface.co/datasets/Gustavosta/Stable-Diffusion-Prompts/resolve/main/data.csv',
    'https://huggingface.co/datasets/Gustavosta/Stable-Diffusion-Prompts/resolve/main/prompts.json',
    'https://huggingface.co/datasets/Gustavosta/Stable-Diffusion-Prompts/resolve/main/data.json'
]

# --- サンプルプロンプトデータ（フォールバック用） ---
SAMPLE_PROMPTS = [
    "beautiful, detailed, high quality, masterpiece, best quality",
    "anime style, manga, illustration, digital art",
    "portrait, face, close up, detailed eyes",
    "landscape, nature, mountains, forest, sunset",
    "fantasy, magical, mystical, ethereal, glowing",
    "cyberpunk, futuristic, neon, sci-fi, technology",
    "vintage, retro, classic, old fashioned, traditional",
    "modern, contemporary, minimalist, clean, simple",
    "dark, gothic, horror, scary, mysterious",
    "bright, cheerful, happy, colorful, vibrant",
    "realistic, photorealistic, detailed, sharp focus",
    "artistic, painterly, oil painting, watercolor",
    "cute, kawaii, adorable, sweet, charming",
    "cool, badass, tough, strong, powerful",
    "elegant, sophisticated, luxury, premium, high-end",
    "casual, everyday, normal, regular, simple",
    "formal, professional, business, official, serious",
    "creative, artistic, imaginative, unique, original",
    "natural, organic, earthy, rustic, handmade",
    "urban, city, street, modern, contemporary"
]

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

def download_file(url: str, save_path: Path) -> bool:
    """ファイルをダウンロード。成功時はTrue、失敗時はFalseを返す"""
    save_path.parent.mkdir(parents=True, exist_ok=True)
    if save_path.exists():
        log(f"[スキップ] 既に存在: {save_path}")
        return True
    log(f"[ダウンロード] {url} → {save_path}")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(r.content)
        return True
    except Exception as e:
        log(f"[エラー] ダウンロード失敗: {e}")
        return False

def create_sample_dataset(save_path: Path):
    """サンプルデータセットを作成"""
    save_path.parent.mkdir(parents=True, exist_ok=True)
    log(f"[作成] サンプルデータセット: {save_path}")
    
    with open(save_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['prompt'])  # ヘッダー
        for prompt in SAMPLE_PROMPTS:
            writer.writerow([prompt])
    
    log(f"[完了] サンプルデータセット作成: {len(SAMPLE_PROMPTS)}件")

def parse_huggingface_prompts(csv_path: Path) -> Set[str]:
    """CSVファイルからプロンプトを解析してキーワードを抽出"""
    prompts = set()
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # ヘッダーをスキップ
            next(reader, None)
            for row in reader:
                if row:
                    # 最初の列をプロンプトとして扱う
                    prompt = row[0].strip()
                    if prompt:
                        # カンマ区切りで複数プロンプトが入っている場合も考慮
                        for part in prompt.split(','):
                            word = part.strip().lower()
                            # 有効なキーワードのみ追加
                            if 2 < len(word) < 40 and word.isalpha():
                                prompts.add(word)
    except Exception as e:
        log(f"[エラー] CSV解析失敗: {e}")
        # フォールバック: 単純な行読み込み
        with open(csv_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('prompt'):  # ヘッダーをスキップ
                    for part in line.split(','):
                        word = part.strip().lower()
                        if 2 < len(word) < 40 and word.isalpha():
                            prompts.add(word)
    return prompts

def auto_classify_keyword(keyword: str, categories: List[str], category_keywords: Dict[str, List[str]]) -> str:
    """キーワードを自動分類"""
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
    
    # 複数のURLを試行
    download_success = False
    for url in DATASET_URLS:
        if download_file(url, hf_csv):
            download_success = True
            break
    
    # ダウンロード失敗時はサンプルデータセットを作成
    if not download_success:
        log("[警告] 外部データセットのダウンロードに失敗しました")
        log("[情報] サンプルデータセットを使用します")
        create_sample_dataset(hf_csv)
    
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