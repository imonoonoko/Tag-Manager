"""
定数定義（後方互換性のため残す）
新しい実装では各機能別モジュールを使用してください
"""
import json
import os
from typing import Any, Dict, Optional, List, Tuple

# 基本設定（config.pyからインポート）
from modules.config import (
    POSITIVE_PROMPT_FILE, NEGATIVE_PROMPT_FILE, DB_FILE, THEME_FILE,
    TRANSLATING_PLACEHOLDER, CATEGORY_KEYWORDS_FILE
)

# カテゴリ管理機能（category_manager.pyからインポート）
from modules.category_manager import (
    load_category_keywords, CATEGORY_PRIORITIES, KEYWORD_WEIGHTS,
    calculate_keyword_score, get_category_priority, get_all_categories,
    is_valid_category, get_category_keywords, add_category_keyword, remove_category_keyword
)

# コンテキスト分析機能（context_analyzer.pyからインポート）
from modules.context_analyzer import (
    SYNONYM_MAPPING, CONTEXT_BOOST_RULES, NEGATION_WORDS, MODIFIER_WORDS,
    analyze_tag_context, calculate_context_boost, get_synonyms,
    has_negation, has_modifier, extract_color_keywords, extract_style_keywords,
    get_context_rules_for_category
)

# AI予測機能（ai_predictor.pyからインポート）
from modules.ai_predictor import (
    predict_category_ai, suggest_similar_tags_ai, ai_predictor
)

# ユーザーカスタマイズ機能（customization.pyからインポート）
from modules.customization import (
    get_customized_category_keywords, apply_custom_rules, customization_manager
)

# 後方互換性のための関数
def safe_load_json(filepath: str) -> Optional[Any]:
    """
    ファイルパスからJSONを安全に読み込む純粋関数。失敗時はNoneを返す。
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

from modules.common_words import COMMON_WORDS

def auto_assign_category_context_aware_pure(
    tag: Optional[str],
    category_keywords: Optional[Dict[str, List[str]]],
    category_priorities: Optional[Dict[str, int]] = None,
    all_tags: Optional[List[str]] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    コンテキスト認識機能付きのカテゴリ自動割り当て機能（後方互換性）
    """
    if not isinstance(tag, str) or not tag:
        return "未分類", {"reason": "タグが空または無効", "score": 0}
    
    if category_priorities is None:
        category_priorities = CATEGORY_PRIORITIES
    
    if all_tags is None:
        all_tags = []
    
    tag_norm = tag.lower().strip()
    
    # 一般的すぎる単語は未分類として扱う
    if tag_norm in COMMON_WORDS:
        return "未分類", {"reason": "一般的すぎる単語のため", "score": 0}
    
    best_category = "未分類"
    best_score = 0
    best_reason = "マッチするキーワードが見つかりませんでした"
    category_scores = {}
    
    # コンテキスト分析
    context_info = analyze_tag_context(tag)
    
    try:
        for category, keywords in (category_keywords or {}).items():
            category_score = 0
            matched_keywords = []
            
            for keyword in (keywords or []):
                if not keyword:
                    continue
                
                score = calculate_keyword_score(tag_norm, keyword)
                if score > 0:
                    category_score += score
                    matched_keywords.append((keyword, score))
            
            # 複数キーワードマッチングのボーナス
            if len(matched_keywords) > 1:
                category_score += len(matched_keywords) * 10
            
            # カテゴリ優先度を考慮
            priority = category_priorities.get(category, 999)
            priority_bonus = max(0, (999 - priority) * 2)
            category_score += priority_bonus
            
            # コンテキストブーストを適用
            context_boost = calculate_context_boost(tag, category, all_tags)
            category_score += context_boost
            
            # 否定語の場合はスコアを下げる
            if context_info["has_negation"]:
                category_score = max(0, category_score - 30)
            
            # 修飾語の場合はスコアを少し上げる
            if context_info["has_modifier"]:
                category_score += 10
            
            category_scores[category] = {
                "score": category_score,
                "matched_keywords": matched_keywords,
                "priority": priority,
                "priority_bonus": priority_bonus,
                "context_boost": context_boost,
                "context_info": context_info
            }
            
            if category_score > best_score:
                best_score = category_score
                best_category = category
                best_reason = f"キーワード: {', '.join([kw for kw, _ in matched_keywords])}"
                if context_boost > 0:
                    best_reason += f" (コンテキストブースト: +{context_boost})"
        
        # スコアが低すぎる場合は未分類
        if best_score < 20:
            best_category = "未分類"
            best_reason = f"スコアが低すぎます（{best_score}）"
        
        return best_category, {
            "reason": best_reason,
            "score": best_score,
            "category_scores": category_scores,
            "assigned_category": best_category,
            "context_analysis": context_info
        }
        
    except Exception as e:
        return "未分類", {"reason": f"エラーが発生しました: {str(e)}", "score": 0}

def auto_assign_category_advanced_pure(
    tag: Optional[str],
    category_keywords: Optional[Dict[str, List[str]]],
    category_priorities: Optional[Dict[str, int]] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    より洗練されたカテゴリ自動割り当て機能（後方互換性）
    """
    if not isinstance(tag, str) or not tag:
        return "未分類", {"reason": "タグが空または無効", "score": 0}
    
    if category_priorities is None:
        category_priorities = CATEGORY_PRIORITIES
    
    tag_norm = tag.lower().strip()
    
    # 一般的すぎる単語は未分類として扱う
    if tag_norm in COMMON_WORDS:
        return "未分類", {"reason": "一般的すぎる単語のため", "score": 0}
    
    best_category = "未分類"
    best_score = 0
    best_reason = "マッチするキーワードが見つかりませんでした"
    category_scores = {}
    
    try:
        for category, keywords in (category_keywords or {}).items():
            category_score = 0
            matched_keywords = []
            
            for keyword in (keywords or []):
                if not keyword:
                    continue
                
                score = calculate_keyword_score(tag_norm, keyword)
                if score > 0:
                    category_score += score
                    matched_keywords.append((keyword, score))
            
            # 複数キーワードマッチングのボーナス
            if len(matched_keywords) > 1:
                category_score += len(matched_keywords) * 10
            
            # カテゴリ優先度を考慮
            priority = category_priorities.get(category, 999)
            priority_bonus = max(0, (999 - priority) * 2)
            category_score += priority_bonus
            
            category_scores[category] = {
                "score": category_score,
                "matched_keywords": matched_keywords,
                "priority": priority,
                "priority_bonus": priority_bonus
            }
            
            if category_score > best_score:
                best_score = category_score
                best_category = category
                best_reason = f"キーワード: {', '.join([kw for kw, _ in matched_keywords])}"
        
        # スコアが低すぎる場合は未分類
        if best_score < 20:
            best_category = "未分類"
            best_reason = f"スコアが低すぎます（{best_score}）"
        
        return best_category, {
            "reason": best_reason,
            "score": best_score,
            "category_scores": category_scores,
            "assigned_category": best_category
        }
        
    except Exception as e:
        return "未分類", {"reason": f"エラーが発生しました: {str(e)}", "score": 0}

def auto_assign_category_pure(
    tag: Optional[str],
    category_keywords: Optional[Dict[str, List[str]]],
    category_priorities: Optional[Dict[str, int]] = None
) -> str:
    """
    カテゴリキーワード・優先度辞書を引数で受け取る純粋関数（後方互換性）
    """
    category, _ = auto_assign_category_advanced_pure(tag, category_keywords, category_priorities)
    return category

# 既存互換用エイリアス
def auto_assign_category(tag: str) -> str:
    """
    既存互換用エイリアス（後方互換性）
    """
    category_keywords = load_category_keywords()
    return auto_assign_category_pure(tag, category_keywords, CATEGORY_PRIORITIES)

# グローバル変数（後方互換性）
category_keywords = load_category_keywords()