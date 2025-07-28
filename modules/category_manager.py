"""
カテゴリ管理機能
"""
import json
import os
from typing import Dict, List, Optional, Tuple, Any
from modules.config import CATEGORY_KEYWORDS_FILE
from modules.common_words import COMMON_WORDS

# カテゴリ優先度（数値が小さいほど優先度が高い）
CATEGORY_PRIORITIES = {
    "品質・画質指定": 1,      # 最も重要
    "スタイル・技法": 2,
    "キャラクター設定": 3,
    "ポーズ・動作": 4,
    "服装・ファッション": 5,
    "髪型・髪色": 6,
    "表情・感情": 7,
    "背景・環境": 8,
    "照明・色調": 9,
    "小物・アクセサリー": 10,
    "特殊効果・フィルター": 11,
    "構図・カメラ視点": 12,
    "ネガティブ": 13,   # 最も優先度が低い
}

# キーワードの重み付け（完全一致の方が部分一致より高スコア）
KEYWORD_WEIGHTS = {
    "exact_match": 100,      # 完全一致
    "word_boundary": 80,     # 単語境界での一致
    "partial_match": 50,     # 部分一致
    "prefix_match": 30,      # 接頭辞一致
    "suffix_match": 20,      # 接尾辞一致
}

def load_category_keywords() -> Dict[str, List[str]]:
    """
    カテゴリキーワード設定ファイルを読み込む
    """
    if os.path.exists(CATEGORY_KEYWORDS_FILE):
        try:
            with open(CATEGORY_KEYWORDS_FILE, 'r', encoding='utf-8') as f:
                loaded_keywords = json.load(f)
                # 一般的すぎる単語をフィルタリング
                filtered_keywords = {}
                for category, keywords in loaded_keywords.items():
                    filtered_keywords[category] = [kw for kw in keywords if kw.lower().strip() not in COMMON_WORDS]
                return filtered_keywords
        except Exception as e:
            print(f"カテゴリキーワードファイルの読み込みに失敗しました: {e}")
    
    # デフォルトのキーワード（優先順位を考慮して並べ替え）
    default_keywords = {
        "品質・画質指定": ["high quality", "best quality", "masterpiece", "lowres", "blurry", "jpeg artifacts", "detailed", "realistic", "sharp", "hdr", "4k", "8k", "ultra high res"],
        "スタイル・技法": ["digital art", "watercolor", "pixel art", "anime style", "oil painting", "3d render", "photorealistic", "sketch", "lineart", "manga", "cartoon"],
        "キャラクター設定": ["original character", "oc", "fanart", "male", "female", "boy", "girl", "man", "woman", "child", "adult"],
        "ポーズ・動作": ["sitting", "standing", "running", "jumping", "pose", "walking", "lying", "crouching", "kneeling", "dance", "jump", "walk", "sit", "stand", "action"],
        "服装・ファッション": ["dress", "skirt", "jacket", "coat", "hat", "beret", "bow", "ribbon", "gloves", "scarf", "shoes", "boots", "socks", "stockings", "hoodie", "t-shirt", "jeans", "uniform", "kimono", "swimsuit"],
        "髪型・髪色": ["long hair", "short hair", "ponytail", "braid", "bangs", "curly", "straight", "wavy", "hairpin", "hairband", "blonde", "black hair", "red hair", "blue hair"],
        "表情・感情": ["smile", "smiling", "laugh", "cry", "angry", "sad", "happy", "surprised", "neutral", "serious", "blush", "wink", "frown", "smiling face"],
        "背景・環境": ["background", "city", "forest", "night", "sky", "mountain", "beach", "blur", "bokeh", "sunset", "rain", "snow", "urban", "rural"],
        "照明・色調": ["bright", "dark", "colorful", "neon", "glowing", "glow", "shadow", "lightning", "sunlight", "vibrant", "pastel", "monochrome", "warm", "cool", "saturated", "desaturated", "muted", "hue", "contrast", "gradient", "soft light", "backlight", "rim light", "ambient light", "diffuse light"],
        "小物・アクセサリー": ["bag", "glasses", "necklace", "ring", "earrings", "bracelet", "watch", "belt", "hat", "mask", "umbrella", "phone"],
        "特殊効果・フィルター": ["sparkles", "fog", "vignette", "bokeh", "motion blur", "grain", "noise", "lens flare", "glitch", "fire", "smoke", "sparkle"],
        "構図・カメラ視点": ["close-up", "wide shot", "bird's eye view", "worm's eye view", "overhead", "side view", "front view", "rear view"],
        "ネガティブ": ["bad", "low quality", "worst quality", "error", "blurry", "duplicate", "artifact"]
    }
    
    # 一般的すぎる単語をフィルタリング
    filtered_keywords = {}
    for category, keywords in default_keywords.items():
        filtered_keywords[category] = [kw for kw in keywords if kw.lower().strip() not in COMMON_WORDS]
    
    return filtered_keywords

def save_category_keywords(category_keywords: Dict[str, List[str]]) -> bool:
    """
    カテゴリキーワード設定ファイルを保存する
    """
    # Noneの場合は保存を拒否
    if category_keywords is None:
        return False
    
    try:
        os.makedirs(os.path.dirname(CATEGORY_KEYWORDS_FILE), exist_ok=True)
        with open(CATEGORY_KEYWORDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(category_keywords, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"カテゴリキーワードファイルの保存に失敗しました: {e}")
        return False

def get_category_priority(category: str) -> int:
    """
    カテゴリの優先度を取得する
    """
    return CATEGORY_PRIORITIES.get(category, 999)

def get_all_categories() -> List[str]:
    """
    全カテゴリのリストを取得する
    """
    return list(CATEGORY_PRIORITIES.keys()) + ["未分類"]

def is_valid_category(category: str) -> bool:
    """
    カテゴリが有効かどうかをチェックする
    """
    return category in get_all_categories()

def calculate_keyword_score(tag: str, keyword: str) -> int:
    """
    タグとキーワードの一致度をスコア化する純粋関数
    """
    import re
    
    # Noneや空文字列はスコアを0にする
    if tag is None or keyword is None or tag.strip() == "" or keyword.strip() == "":
        return 0
    
    # 一般的すぎる単語はスコアを0にする
    if tag.lower().strip() in COMMON_WORDS or keyword.lower().strip() in COMMON_WORDS:
        return 0
    
    tag_lower = tag.lower()
    keyword_lower = keyword.lower()
    
    # 完全一致
    if tag_lower == keyword_lower:
        return KEYWORD_WEIGHTS["exact_match"]
    
    # 単語境界での一致（前後に空白や記号がある）
    word_pattern = r'\b' + re.escape(keyword_lower) + r'\b'
    if re.search(word_pattern, tag_lower):
        return KEYWORD_WEIGHTS["word_boundary"]
    
    # 部分一致
    if keyword_lower in tag_lower:
        return KEYWORD_WEIGHTS["partial_match"]
    
    # 接頭辞一致
    if tag_lower.startswith(keyword_lower):
        return KEYWORD_WEIGHTS["prefix_match"]
    
    # 接尾辞一致
    if tag_lower.endswith(keyword_lower):
        return KEYWORD_WEIGHTS["suffix_match"]
    
    return 0

def get_category_keywords(category: str) -> List[str]:
    """
    指定されたカテゴリのキーワードを取得する
    """
    category_keywords = load_category_keywords()
    keywords = category_keywords.get(category, [])
    # 一般的すぎる単語をフィルタリング
    return [kw for kw in keywords if kw.lower().strip() not in COMMON_WORDS]

def add_category_keyword(category: str, keyword: str) -> bool:
    """
    カテゴリにキーワードを追加する
    """
    # Noneや空文字列は追加を拒否
    if keyword is None or keyword.strip() == "":
        return False
    
    # 一般的すぎる単語は追加を拒否
    if keyword.lower().strip() in COMMON_WORDS:
        return False
    
    if not is_valid_category(category):
        return False
    
    category_keywords = load_category_keywords()
    if category not in category_keywords:
        category_keywords[category] = []
    
    if keyword not in category_keywords[category]:
        category_keywords[category].append(keyword)
        return save_category_keywords(category_keywords)
    
    return True

def remove_category_keyword(category: str, keyword: str) -> bool:
    """
    カテゴリからキーワードを削除する
    """
    category_keywords = load_category_keywords()
    if category in category_keywords and keyword in category_keywords[category]:
        category_keywords[category].remove(keyword)
        return save_category_keywords(category_keywords)
    
    return False 