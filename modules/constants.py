import json
import os
import re
from typing import Any, Dict, Optional, List

POSITIVE_PROMPT_FILE = os.path.join('resources', 'config', "translated_tags.json") 
NEGATIVE_PROMPT_FILE = os.path.join('resources', 'config', "negative_tags.json")

DB_FILE = os.path.join('resources', "tags.db")
THEME_FILE = "theme_settings.json" # theme_settings.jsonはルートに置く想定
TRANSLATING_PLACEHOLDER = "(翻訳中...)"

# カテゴリキーワードを外部ファイルから読み込む
CATEGORY_KEYWORDS_FILE = os.path.join(os.path.dirname(__file__), '..', 'resources', 'config', 'categories.json')

def load_category_keywords() -> Dict[str, List[str]]:
    if os.path.exists(CATEGORY_KEYWORDS_FILE):
        try:
            with open(CATEGORY_KEYWORDS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"カテゴリキーワードファイルの読み込みに失敗しました: {e}")
    # デフォルトのキーワード（優先順位を考慮して並べ替え）
    return {
        "服装・ファッション": ["dress", "skirt", "jacket", "coat", "hat", "beret", "bow", "ribbon", "gloves", "scarf", "shoes", "boots", "socks", "stockings", "hoodie"],
        "髪型・ヘアスタイル": ["long hair", "short hair", "ponytail", "braid", "bangs", "curly", "straight", "wavy", "hairpin", "hairband"],
        "小物・アクセサリー": ["bag", "glasses", "necklace", "ring", "earrings", "bracelet", "watch", "belt", "hat", "mask"],
        "表情・感情": ["smile", "laugh", "cry", "angry", "sad", "happy", "surprised", "neutral", "serious", "blush"],
        "ポーズ・アクション": ["sitting", "standing", "running", "jumping", "pose", "walking", "lying", "crouching", "kneeling", "dance"],
        "人物・キャラクター": ["girl", "boy", "character", "solo", "model", "portrait", "face", "expression", "eyes", "mouth"],
        "色彩・照明": ["bright", "dark", "colorful", "neon", "glowing", "glow", "shadow", "lightning", "sunlight", "vibrant",
                     "pastel", "monochrome", "warm", "cool", "saturated", "desaturated", "muted", "hue", "contrast", "gradient",
                     "soft light", "backlight", "rim light", "ambient light", "diffuse light"],
        "特殊効果・フィルター": ["sparkles", "fog", "vignette", "bokeh", "motion blur", "grain", "noise", "lens flare", "glitch"],
        "アートスタイル・技法": ["digital art", "watercolor", "pixel art", "anime style", "oil painting", "3d render", "photorealistic", "sketch"],
        "背景・環境": ["background", "city", "forest", "night", "sky", "mountain", "beach", "blur", "bokeh", "sunset", "rain", "snow"]
    }

category_keywords = load_category_keywords()

def safe_load_json(filepath: str) -> Optional[Any]:
    """
    ファイルパスからJSONを安全に読み込む純粋関数。失敗時はNoneを返す。
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def auto_assign_category_pure(
    tag: Optional[str],
    category_keywords: Optional[Dict[str, List[str]]],
    category_priorities: Optional[Dict[str, int]] = None
) -> str:
    """
    カテゴリキーワード・優先度辞書を引数で受け取る純粋関数。
    """
    if not isinstance(tag, str) or not tag:
        return "未分類"
    tag_norm = tag.lower().strip()
    best_category = ""
    best_priority = 999
    if category_priorities is None:
        category_priorities = {}
    try:
        for category, keywords in (category_keywords or {}).items():
            for kw in (keywords or []):
                if kw and kw.lower() in tag_norm:
                    priority = category_priorities.get(category, 999)
                    if priority < best_priority:
                        best_category = category
                        best_priority = priority
    except Exception:
        pass
    if not best_category:
        return "未分類"
    return best_category

# 既存互換用エイリアス
def auto_assign_category(tag: str) -> str:
    return auto_assign_category_pure(tag, category_keywords, globals().get('category_priorities', {}))