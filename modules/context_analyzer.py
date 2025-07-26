"""
コンテキスト分析機能
"""
from typing import Dict, List, Any, Tuple
from .common_words import COMMON_WORDS

# コンテキスト認識用の同義語・類義語マッピング
SYNONYM_MAPPING = {
    # 髪型関連
    "hair": ["long hair", "short hair", "curly", "straight", "wavy", "braid", "ponytail"],
    "long": ["long hair", "long dress", "long skirt"],
    "short": ["short hair", "short dress", "short skirt"],
    
    # 色関連
    "blue": ["blue hair", "blue dress", "blue eyes", "blue sky"],
    "red": ["red hair", "red dress", "red lips"],
    "green": ["green hair", "green dress", "green eyes"],
    "pink": ["pink hair", "pink dress", "pink lips"],
    "purple": ["purple hair", "purple dress", "purple eyes"],
    "blonde": ["blonde hair", "blonde"],
    "brown": ["brown hair", "brown eyes"],
    "black": ["black hair", "black dress", "black eyes"],
    
    # 表情関連
    "smile": ["smiling", "smile", "happy", "grin"],
    "laugh": ["laughing", "laugh", "giggle"],
    "cry": ["crying", "cry", "tears", "sad"],
    "angry": ["angry", "mad", "furious"],
    "surprised": ["surprised", "shocked", "amazed"],
    
    # 服装関連
    "dress": ["dress", "gown", "frock"],
    "skirt": ["skirt", "mini skirt", "long skirt"],
    "jacket": ["jacket", "coat", "blazer"],
    "shoes": ["shoes", "boots", "heels", "sneakers"],
}

# コンテキスト強化ルール（タグの組み合わせによるカテゴリ強化）
CONTEXT_BOOST_RULES: Dict[Tuple[str, str], Dict[str, Any]] = {
    # 髪型 + 色の組み合わせ
    ("髪型・ヘアスタイル", "色彩・照明"): {
        "boost_score": 50,
        "examples": [
            ("long hair", "blue"),
            ("short hair", "red"),
            ("curly", "pink"),
            ("straight", "blonde"),
        ]
    },
    
    # 表情 + 人物の組み合わせ
    ("表情・感情", "人物・キャラクター"): {
        "boost_score": 40,
        "examples": [
            ("smiling", "girl"),
            ("laughing", "boy"),
            ("crying", "character"),
        ]
    },
    
    # 服装 + 色の組み合わせ
    ("服装・ファッション", "色彩・照明"): {
        "boost_score": 45,
        "examples": [
            ("dress", "blue"),
            ("skirt", "red"),
            ("jacket", "black"),
        ]
    },
    
    # 小物 + 色の組み合わせ
    ("小物・アクセサリー", "色彩・照明"): {
        "boost_score": 35,
        "examples": [
            ("glasses", "black"),
            ("necklace", "gold"),
            ("ring", "silver"),
        ]
    },
}

# 否定語・修飾語の認識
NEGATION_WORDS = ["no", "not", "without", "none", "negative", "anti"]
MODIFIER_WORDS = ["very", "extremely", "slightly", "somewhat", "quite", "rather"]

def analyze_tag_context(tag: str) -> Dict[str, Any]:
    """
    タグのコンテキストを分析する純粋関数
    """
    # 一般的すぎる単語はコンテキスト分析をスキップ
    if tag.lower().strip() in COMMON_WORDS:
        return {
            "has_negation": False,
            "has_modifier": False,
            "color_keywords": [],
            "style_keywords": [],
            "synonyms": []
        }
    
    tag_lower = tag.lower()
    context_info: Dict[str, Any] = {
        "has_negation": any(neg in tag_lower for neg in NEGATION_WORDS),
        "has_modifier": any(mod in tag_lower for mod in MODIFIER_WORDS),
        "color_keywords": [],
        "style_keywords": [],
        "synonyms": []
    }
    
    # 色キーワードの検出
    color_keywords = ["blue", "red", "green", "pink", "purple", "blonde", "brown", "black", "white", "yellow", "orange"]
    for color in color_keywords:
        if color in tag_lower:
            context_info["color_keywords"].append(color)
    
    # スタイルキーワードの検出
    style_keywords = ["long", "short", "curly", "straight", "wavy", "mini", "maxi"]
    for style in style_keywords:
        if style in tag_lower:
            context_info["style_keywords"].append(style)
    
    # 同義語の検出
    for base_word, synonyms in SYNONYM_MAPPING.items():
        if base_word in tag_lower:
            context_info["synonyms"].extend(synonyms)
    
    return context_info

def calculate_context_boost(tag: str, category: str, all_tags: List[str]) -> int:
    """
    コンテキストに基づくスコアブーストを計算する純粋関数
    """
    # 一般的すぎる単語はコンテキストブーストを適用しない
    if tag.lower().strip() in COMMON_WORDS:
        return 0
    
    boost_score = 0
    tag_lower = tag.lower()
    
    # 他のタグとの組み合わせをチェック
    for other_tag in all_tags:
        if other_tag == tag:
            continue
        
        other_tag_lower = other_tag.lower()
        
        # コンテキスト強化ルールをチェック
        for (cat1, cat2), rule in CONTEXT_BOOST_RULES.items():
            if category in [cat1, cat2]:
                examples = rule.get("examples", [])
                for example_tag, example_context in examples:
                    # タグとコンテキストの組み合わせをチェック
                    if (example_tag in tag_lower and example_context in other_tag_lower) or \
                       (example_context in tag_lower and example_tag in other_tag_lower):
                        boost_score += rule.get("boost_score", 0)
                        break
    
    return boost_score

def get_synonyms(word: str) -> List[str]:
    """
    指定された単語の同義語を取得する
    """
    return SYNONYM_MAPPING.get(word.lower(), [])

def has_negation(tag: str) -> bool:
    """
    タグに否定語が含まれているかをチェックする
    """
    # 一般的すぎる単語は否定語チェックをスキップ
    if tag.lower().strip() in COMMON_WORDS:
        return False
    
    tag_lower = tag.lower()
    return any(neg in tag_lower for neg in NEGATION_WORDS)

def has_modifier(tag: str) -> bool:
    """
    タグに修飾語が含まれているかをチェックする
    """
    # 一般的すぎる単語は修飾語チェックをスキップ
    if tag.lower().strip() in COMMON_WORDS:
        return False
    
    tag_lower = tag.lower()
    return any(mod in tag_lower for mod in MODIFIER_WORDS)

def extract_color_keywords(tag: str) -> List[str]:
    """
    タグから色キーワードを抽出する
    """
    # 一般的すぎる単語は色キーワード抽出をスキップ
    if tag.lower().strip() in COMMON_WORDS:
        return []
    
    tag_lower = tag.lower()
    color_keywords = ["blue", "red", "green", "pink", "purple", "blonde", "brown", "black", "white", "yellow", "orange"]
    return [color for color in color_keywords if color in tag_lower]

def extract_style_keywords(tag: str) -> List[str]:
    """
    タグからスタイルキーワードを抽出する
    """
    # 一般的すぎる単語はスタイルキーワード抽出をスキップ
    if tag.lower().strip() in COMMON_WORDS:
        return []
    
    tag_lower = tag.lower()
    style_keywords = ["long", "short", "curly", "straight", "wavy", "mini", "maxi"]
    return [style for style in style_keywords if style in tag_lower]

def get_context_rules_for_category(category: str) -> List[Tuple[str, Dict[str, Any]]]:
    """
    指定されたカテゴリに関連するコンテキストルールを取得する
    """
    rules = []
    for (cat1, cat2), rule in CONTEXT_BOOST_RULES.items():
        if category in [cat1, cat2]:
            rules.append((f"{cat1} + {cat2}", rule))
    return rules 