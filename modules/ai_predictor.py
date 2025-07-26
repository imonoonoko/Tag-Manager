"""
AI予測機能（機械学習ベースの動的重み付けシステム）
"""
import json
import os
import time
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
from .config import BACKUP_DIR
from .category_manager import load_category_keywords, CATEGORY_PRIORITIES, calculate_keyword_score
from .context_analyzer import analyze_tag_context, calculate_context_boost
from .common_words import COMMON_WORDS

# 学習データファイル
LEARNING_DATA_FILE = os.path.join(BACKUP_DIR, "learning_data.json")
TAG_USAGE_PATTERNS_FILE = os.path.join(BACKUP_DIR, "tag_usage_patterns.json")

class TagUsageTracker:
    """
    タグ使用パターンを追跡・学習するクラス
    """
    def __init__(self):
        self.usage_data = defaultdict(lambda: {
            "count": 0,
            "categories": defaultdict(int),
            "last_used": 0,
            "context_tags": defaultdict(int)
        })
        self.load_usage_data()
    
    def record_tag_usage(self, tag: str, category: str, context_tags: List[str] = None):
        """
        タグの使用を記録する
        """
        tag_lower = tag.lower()
        current_time = time.time()
        
        # 使用回数を更新
        self.usage_data[tag_lower]["count"] += 1
        self.usage_data[tag_lower]["categories"][category] += 1
        self.usage_data[tag_lower]["last_used"] = current_time
        
        # コンテキストタグを記録
        if context_tags:
            for context_tag in context_tags:
                self.usage_data[tag_lower]["context_tags"][context_tag.lower()] += 1
        
        # 定期的にデータを保存
        if self.usage_data[tag_lower]["count"] % 10 == 0:
            self.save_usage_data()
    
    def get_tag_frequency(self, tag: str) -> int:
        """
        タグの使用頻度を取得する
        """
        return self.usage_data[tag.lower()]["count"]
    
    def get_most_common_category(self, tag: str) -> Optional[str]:
        """
        タグの最も一般的なカテゴリを取得する
        """
        categories = self.usage_data[tag.lower()]["categories"]
        if categories:
            return max(categories.items(), key=lambda x: x[1])[0]
        return None
    
    def get_context_similarity(self, tag1: str, tag2: str) -> float:
        """
        2つのタグのコンテキスト類似度を計算する
        """
        context1 = set(self.usage_data[tag1.lower()]["context_tags"].keys())
        context2 = set(self.usage_data[tag2.lower()]["context_tags"].keys())
        
        if not context1 or not context2:
            return 0.0
        
        intersection = len(context1.intersection(context2))
        union = len(context1.union(context2))
        
        return intersection / union if union > 0 else 0.0
    
    def load_usage_data(self):
        """
        使用データを読み込む
        """
        try:
            if os.path.exists(TAG_USAGE_PATTERNS_FILE):
                with open(TAG_USAGE_PATTERNS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.usage_data = defaultdict(lambda: {
                        "count": 0,
                        "categories": defaultdict(int),
                        "last_used": 0,
                        "context_tags": defaultdict(int)
                    })
                    for tag, info in data.items():
                        self.usage_data[tag] = {
                            "count": info.get("count", 0),
                            "categories": defaultdict(int, info.get("categories", {})),
                            "last_used": info.get("last_used", 0),
                            "context_tags": defaultdict(int, info.get("context_tags", {}))
                        }
        except Exception as e:
            print(f"使用データの読み込みに失敗しました: {e}")
    
    def save_usage_data(self):
        """
        使用データを保存する
        """
        try:
            os.makedirs(os.path.dirname(TAG_USAGE_PATTERNS_FILE), exist_ok=True)
            # defaultdictを通常のdictに変換
            data = {}
            for tag, info in self.usage_data.items():
                data[tag] = {
                    "count": info["count"],
                    "categories": dict(info["categories"]),
                    "last_used": info["last_used"],
                    "context_tags": dict(info["context_tags"])
                }
            
            with open(TAG_USAGE_PATTERNS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"使用データの保存に失敗しました: {e}")

class DynamicWeightCalculator:
    """
    動的重み付けを計算するクラス
    """
    def __init__(self, usage_tracker: TagUsageTracker):
        self.usage_tracker = usage_tracker
        self.base_weights = {
            "frequency": 0.3,      # 使用頻度の重み
            "recency": 0.2,        # 最近使用の重み
            "context": 0.3,        # コンテキストの重み
            "user_preference": 0.2  # ユーザー設定の重み
        }
    
    def calculate_dynamic_weight(self, tag: str, category: str, context_tags: List[str] = None) -> float:
        """
        タグの動的重みを計算する
        """
        tag_lower = tag.lower()
        usage_info = self.usage_tracker.usage_data[tag_lower]
        
        # 使用頻度スコア
        frequency_score = min(usage_info["count"] / 100.0, 1.0)  # 最大1.0に正規化
        
        # 最近使用スコア（1週間以内なら高スコア）
        current_time = time.time()
        days_since_last_use = (current_time - usage_info["last_used"]) / (24 * 3600)
        recency_score = max(0, 1.0 - (days_since_last_use / 7.0))
        
        # コンテキストスコア
        context_score = 0.0
        if context_tags:
            context_matches = 0
            for context_tag in context_tags:
                if context_tag.lower() in usage_info["context_tags"]:
                    context_matches += 1
            context_score = context_matches / len(context_tags) if context_tags else 0.0
        
        # カテゴリ一致スコア
        category_score = usage_info["categories"].get(category, 0) / max(usage_info["count"], 1)
        
        # 総合スコア
        total_score = (
            frequency_score * self.base_weights["frequency"] +
            recency_score * self.base_weights["recency"] +
            context_score * self.base_weights["context"] +
            category_score * self.base_weights["user_preference"]
        )
        
        return total_score

class AIPredictor:
    """
    AI予測機能のメインクラス
    """
    def __init__(self):
        self.usage_tracker = TagUsageTracker()
        self.weight_calculator = DynamicWeightCalculator(self.usage_tracker)
        self.category_keywords = load_category_keywords()
    
    def predict_category_with_confidence(
        self, 
        tag: str, 
        context_tags: List[str] = None,
        confidence_threshold: float = 0.7
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        タグのカテゴリを予測し、信頼度も返す
        """
        if not tag:
            return "未分類", 0.0, {"reason": "タグが空"}
        
        # 一般的すぎる単語は未分類として扱う
        if tag.lower().strip() in COMMON_WORDS:
            return "未分類", 0.0, {"reason": "一般的すぎる単語のため"}
        
        # 基本的なカテゴリ割り当て
        category_scores = {}
        tag_lower = tag.lower()
        
        for category, keywords in self.category_keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                keyword_score = calculate_keyword_score(tag_lower, keyword)
                if keyword_score > 0:
                    score += keyword_score
                    matched_keywords.append((keyword, keyword_score))
            
            # 動的重みを適用
            dynamic_weight = self.weight_calculator.calculate_dynamic_weight(tag, category, context_tags)
            score *= (1.0 + dynamic_weight)
            
            # コンテキストブーストを適用
            if context_tags:
                context_boost = calculate_context_boost(tag, category, context_tags)
                score += context_boost
            
            category_scores[category] = {
                "score": score,
                "matched_keywords": matched_keywords,
                "dynamic_weight": dynamic_weight,
                "context_boost": context_boost if context_tags else 0
            }
        
        # 最高スコアのカテゴリを選択
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1]["score"])
            best_score = best_category[1]["score"]
            best_category_name = best_category[0]
            
            # 信頼度を計算（スコアを0-1の範囲に正規化）
            max_possible_score = 200  # 概算の最大スコア
            confidence = min(best_score / max_possible_score, 1.0)
            
            # 信頼度が低い場合は未分類
            if confidence < confidence_threshold:
                best_category_name = "未分類"
                confidence = 0.0
            
            return best_category_name, confidence, {
                "category_scores": category_scores,
                "best_score": best_score,
                "reason": f"キーワード: {', '.join([kw for kw, _ in best_category[1]['matched_keywords']])}"
            }
        
        return "未分類", 0.0, {"reason": "マッチするキーワードが見つかりませんでした"}
    
    def suggest_similar_tags(self, tag: str, limit: int = 5) -> List[Tuple[str, float]]:
        """
        類似タグを提案する
        """
        tag_lower = tag.lower()
        suggestions = []
        
        # 使用パターンから類似タグを検索
        for other_tag, usage_info in self.usage_tracker.usage_data.items():
            if other_tag == tag_lower:
                continue
            
            # 類似度を計算
            similarity = self.usage_tracker.get_context_similarity(tag_lower, other_tag)
            if similarity > 0.1:  # 閾値以上の場合のみ
                suggestions.append((other_tag, similarity))
        
        # 類似度でソートして上位を返す
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:limit]
    
    def get_tag_statistics(self, tag: str) -> Dict[str, Any]:
        """
        タグの統計情報を取得する
        """
        tag_lower = tag.lower()
        usage_info = self.usage_tracker.usage_data[tag_lower]
        
        return {
            "usage_count": usage_info["count"],
            "most_common_category": self.usage_tracker.get_most_common_category(tag),
            "category_distribution": dict(usage_info["categories"]),
            "last_used": usage_info["last_used"],
            "context_tags": dict(usage_info["context_tags"])
        }
    
    def record_prediction_result(self, tag: str, predicted_category: str, actual_category: str = None):
        """
        予測結果を記録して学習に使用する
        """
        if actual_category:
            # 実際のカテゴリが分かっている場合は使用を記録
            self.usage_tracker.record_tag_usage(tag, actual_category)
        else:
            # 予測されたカテゴリを記録
            self.usage_tracker.record_tag_usage(tag, predicted_category)

# グローバルインスタンス
ai_predictor = AIPredictor()

def predict_category_ai(tag: str, context_tags: List[str] = None) -> Tuple[str, float]:
    """
    AI予測機能を使用してカテゴリを予測する（簡易版）
    """
    # 一般的すぎる単語は未分類として扱う
    if tag.lower().strip() in COMMON_WORDS:
        return "未分類", 0.0
    
    category, confidence, _ = ai_predictor.predict_category_with_confidence(tag, context_tags)
    return category, confidence

def suggest_similar_tags_ai(tag: str, limit: int = 5) -> List[Tuple[str, float]]:
    """
    AI予測機能を使用して類似タグを提案する
    """
    return ai_predictor.suggest_similar_tags(tag, limit) 