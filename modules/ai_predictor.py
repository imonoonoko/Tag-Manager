"""
AI予測機能（機械学習ベースの動的重み付けシステム）
外部データベース連携による高度な分類精度を実現
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
from .customization import get_customized_category_keywords, apply_custom_rules, customization_manager, get_custom_category
from .context_analyzer import get_synonyms
# 遅延読み込みのため、グローバルインポートを削除
# from .huggingface_manager import hf_manager
# from .local_hf_manager import local_hf_manager
import glob

# 学習データファイル
LEARNING_DATA_FILE = os.path.join(BACKUP_DIR, "learning_data.json")
TAG_USAGE_PATTERNS_FILE = os.path.join(BACKUP_DIR, "tag_usage_patterns.json")

LEARNING_HISTORY_BONUS_BASE = 50  # 修正履歴1回ごとに加算するボーナス値（パラメータ化）
LEARNING_HISTORY_BONUS_MAX = 300  # 最大ボーナス

class TagUsageTracker:
    """
    タグ使用パターンを追跡・学習するクラス
    """
    def __init__(self, load_existing_data: bool = True, usage_file: str = None):
        self.usage_data = defaultdict(lambda: {
            "count": 0,
            "categories": defaultdict(int),
            "last_used": 0,
            "context_tags": defaultdict(int)
        })
        self.usage_file = usage_file or TAG_USAGE_PATTERNS_FILE
        if load_existing_data:
            self.load_usage_data()
    
    def record_tag_usage(self, tag: str, category: str, context_tags: List[str] = None):
        """
        タグの使用を記録する
        テストタグは学習履歴に記録されません
        """
        tag_lower = tag.lower()
        
        # テストタグを除外（test, テスト, サンプル, sample, デモ, demo を含むタグ）
        if any(test_word in tag_lower for test_word in ['test', 'テスト', 'サンプル', 'sample', 'デモ', 'demo', 'example', '例']):
            return
        
        current_time = time.time()
        
        # 使用回数を更新
        self.usage_data[tag_lower]["count"] += 1
        self.usage_data[tag_lower]["categories"][category] += 1
        self.usage_data[tag_lower]["last_used"] = current_time
        
        # コンテキストタグを記録
        if context_tags:
            for context_tag in context_tags:
                # コンテキストタグもテストタグでないことを確認
                if not any(test_word in context_tag.lower() for test_word in ['test', 'テスト', 'サンプル', 'sample', 'デモ', 'demo', 'example', '例']):
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
    
    def cleanup_test_tags(self):
        """
        既存の学習履歴データからテストタグを削除する
        """
        test_tags_to_remove = []
        for tag in self.usage_data.keys():
            if any(test_word in tag.lower() for test_word in ['test', 'テスト', 'サンプル', 'sample', 'デモ', 'demo', 'example', '例']):
                test_tags_to_remove.append(tag)
        
        for tag in test_tags_to_remove:
            del self.usage_data[tag]
        
        if test_tags_to_remove:
            self.save_usage_data()
            print(f"テストタグ {len(test_tags_to_remove)} 個を学習履歴から削除しました")
        
        return len(test_tags_to_remove)

    def load_usage_data(self):
        """
        使用データを読み込む
        """
        try:
            if os.path.exists(self.usage_file):
                with open(self.usage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.usage_data = defaultdict(lambda: {
                        "count": 0,
                        "categories": defaultdict(int),
                        "last_used": 0,
                        "context_tags": defaultdict(int)
                    })
                    for tag, info in data.items():
                        self.usage_data[tag] = defaultdict(int, info)
        except Exception as e:
            print(f"使用データの読み込みに失敗: {e}")
    
    def save_usage_data(self):
        """
        使用データを保存する
        """
        try:
            os.makedirs(os.path.dirname(self.usage_file), exist_ok=True)
            # defaultdictを通常のdictに変換
            data = {}
            for tag, info in self.usage_data.items():
                data[tag] = dict(info)
            with open(self.usage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"使用データの保存に失敗: {e}")

class DynamicWeightCalculator:
    """
    動的重み計算クラス
    """
    def __init__(self, usage_tracker: TagUsageTracker):
        self.usage_tracker = usage_tracker
    
    def calculate_dynamic_weight(self, tag: str, category: str, context_tags: List[str] = None) -> float:
        """
        タグの動的重みを計算する
        """
        base_weight = 1.0
        
        # 学習履歴による重み調整
        most_common_category = self.usage_tracker.get_most_common_category(tag)
        if most_common_category == category:
            frequency = self.usage_tracker.get_tag_frequency(tag)
            if frequency > 0:
                # 学習履歴によるボーナス（修正履歴1回ごとに50ポイント、最大300ポイント）
                learning_bonus = min(LEARNING_HISTORY_BONUS_MAX, frequency * LEARNING_HISTORY_BONUS_BASE)
                base_weight += learning_bonus
        
        # 使用頻度による重み調整
        frequency = self.usage_tracker.get_tag_frequency(tag)
        if frequency > 0:
            # 使用頻度が高いほど重みを下げる（多様性を促進）
            frequency_factor = max(0.5, 1.0 - (frequency * 0.01))
            base_weight *= frequency_factor
        
        # コンテキスト類似度による重み調整
        if context_tags:
            total_similarity = 0
            count = 0
            for context_tag in context_tags:
                similarity = self.usage_tracker.get_context_similarity(tag, context_tag)
                total_similarity += similarity
                count += 1
            
            if count > 0:
                avg_similarity = total_similarity / count
                # 類似度が高いほど重みを上げる
                context_factor = 1.0 + (avg_similarity * 0.5)
                base_weight *= context_factor
        
        return max(0.1, min(2.0, base_weight))

class AIPredictor:
    """
    AI予測クラス（遅延読み込み対応）
    """
    def __init__(self):
        self.usage_tracker = TagUsageTracker()
        self.weight_calculator = DynamicWeightCalculator(self.usage_tracker)
        self.tag_freq_stats = {}
        self.tag_cooccur_stats = {}
        self._hf_manager = None
        self._local_hf_manager = None
        self._models_loaded = False
        
        # 予測結果キャッシュを追加
        self._prediction_cache = {}
        self._cache_max_size = 1000  # 最大キャッシュサイズ
        
        # 軽量な統計データのみ読み込み
        self._load_tag_freq_stats()
        self._load_tag_cooccur_stats()
    
    def _get_hf_manager(self):
        """HuggingFace Managerを遅延読み込み"""
        if self._hf_manager is None:
            # ローカルAI機能の無効化設定をチェック
            if self._is_local_ai_disabled():
                print("ローカルAI機能が無効化されています。HuggingFace Managerをスキップします。")
                return None
            
            try:
                from .huggingface_manager import HuggingFaceManager
                print("HuggingFace Managerを初期化中...")
                self._hf_manager = HuggingFaceManager()
                
                # 初期化エラーのチェック
                if self._hf_manager._load_error:
                    print(f"HuggingFace Manager初期化エラー: {self._hf_manager._load_error}")
                    self._hf_manager = None
                    return None
                
                # モデル読み込みを非同期で開始
                if not self._hf_manager.is_ready() and not self._hf_manager.is_loading():
                    print("Hugging Faceモデルの読み込みを開始しています...")
                
            except Exception as e:
                print(f"HuggingFace Managerの読み込みに失敗: {e}")
                self._hf_manager = None
        return self._hf_manager
    
    def _get_local_hf_manager(self):
        """Local HuggingFace Managerを遅延読み込み"""
        if self._local_hf_manager is None:
            # ローカルAI機能の無効化設定をチェック
            if self._is_local_ai_disabled():
                print("ローカルAI機能が無効化されています。Local HuggingFace Managerをスキップします。")
                return None
            
            try:
                from .local_hf_manager import LocalHuggingFaceManager
                print("Local HuggingFace Managerを初期化中...")
                self._local_hf_manager = LocalHuggingFaceManager()
                
                # 初期化エラーのチェック
                if self._local_hf_manager._load_error:
                    print(f"Local HuggingFace Manager初期化エラー: {self._local_hf_manager._load_error}")
                    self._local_hf_manager = None
                    return None
                    
            except Exception as e:
                print(f"Local HuggingFace Managerの読み込みに失敗: {e}")
                self._local_hf_manager = None
        return self._local_hf_manager
    
    def _is_local_ai_disabled(self) -> bool:
        """ローカルAI機能の無効化設定をチェック"""
        try:
            import json
            import os
            settings_file = os.path.join('resources', 'config', 'ai_settings.json')
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('local_ai_disabled', False)
        except Exception as e:
            print(f"AI設定ファイルの読み込みエラー: {e}")
        return False
    
    def _load_tag_freq_stats(self):
        """タグ頻度統計を読み込み"""
        try:
            freq_file = os.path.join(BACKUP_DIR, "tag_frequency_stats.json")
            if os.path.exists(freq_file):
                with open(freq_file, 'r', encoding='utf-8') as f:
                    self.tag_freq_stats = json.load(f)
        except Exception as e:
            print(f"タグ頻度統計の読み込みに失敗: {e}")
    
    def _load_tag_cooccur_stats(self):
        """タグ共起統計を読み込み"""
        try:
            cooccur_file = os.path.join(BACKUP_DIR, "tag_cooccurrence_stats.json")
            if os.path.exists(cooccur_file):
                with open(cooccur_file, 'r', encoding='utf-8') as f:
                    self.tag_cooccur_stats = json.load(f)
        except Exception as e:
            print(f"タグ共起統計の読み込みに失敗: {e}")
    
    def get_tag_freq(self, tag: str) -> int:
        """タグの頻度を取得"""
        return self.tag_freq_stats.get(tag.lower(), 0)
    
    def get_tag_cooccurs(self, tag: str) -> dict:
        """タグの共起情報を取得"""
        return self.tag_cooccur_stats.get(tag.lower(), {})
    
    def auto_expand_synonyms(self, output_path: str = "backup/auto_synonyms.json", min_cooccur: int = 10, max_per_tag: int = 5):
        """類義語の自動展開"""
        try:
            synonyms = {}
            for tag, cooccurs in self.tag_cooccur_stats.items():
                if self.get_tag_freq(tag) >= min_cooccur:
                    # 共起頻度の高いタグを類義語として追加
                    sorted_cooccurs = sorted(cooccurs.items(), key=lambda x: x[1], reverse=True)
                    synonyms[tag] = [t[0] for t in sorted_cooccurs[:max_per_tag]]
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(synonyms, f, ensure_ascii=False, indent=2)
            
            return synonyms
        except Exception as e:
            print(f"類義語自動展開に失敗: {e}")
            return {}
    
    def predict_category_with_confidence(
        self, 
        tag: str, 
        context_tags: List[str] = None,
        confidence_threshold: float = 0.5,
        top_n: int = 3
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        タグのカテゴリを予測（信頼度付き）
        """
        # キャッシュをチェック
        context_tags_tuple = tuple(context_tags) if context_tags else ()
        cache_key = (tag, context_tags_tuple, confidence_threshold, top_n)
        if cache_key in self._prediction_cache:
            return self._prediction_cache[cache_key]
        
        # カスタムルールをチェック
        custom_category = get_custom_category(tag)
        if custom_category:
            result = custom_category, 1.0, {"reason": "カスタムルールにより割り当て"}
            self._prediction_cache[cache_key] = result
            return result
        
        # 外部データベースでの予測を試行
        external_result = self._predict_with_external_data(tag, context_tags)
        if external_result:
            predicted_category, confidence, details = external_result
            if confidence >= confidence_threshold:
                result = predicted_category, confidence, details
                self._prediction_cache[cache_key] = result
                return result
        
        # Hugging Faceモデルでの予測を試行
        hf_result = self._predict_with_huggingface(tag, context_tags)
        if hf_result:
            predicted_category, confidence, details = hf_result
            if confidence >= confidence_threshold:
                result = predicted_category, confidence, details
                self._prediction_cache[cache_key] = result
                return result
        
        # 従来手法での予測
        result = self._predict_with_traditional_method(tag, context_tags, confidence_threshold, top_n)
        
        # キャッシュサイズを管理
        if len(self._prediction_cache) >= self._cache_max_size:
            # 最も古いエントリを削除
            oldest_key = next(iter(self._prediction_cache))
            del self._prediction_cache[oldest_key]
        
        self._prediction_cache[cache_key] = result
        return result
    
    def _predict_with_external_data(self, tag: str, context_tags: List[str] = None) -> Optional[Tuple[str, float, Dict[str, Any]]]:
        """外部データベースでの予測"""
        # 実装は後で追加
        return None
    
    def _predict_with_huggingface(self, tag: str, context_tags: List[str] = None) -> Optional[Tuple[str, float, Dict[str, Any]]]:
        """Hugging Faceモデルでの予測"""
        hf_manager = self._get_hf_manager()
        if hf_manager is None:
            return None
        
        # モデルが読み込み中またはエラーの場合
        if hf_manager.is_loading():
            print("Hugging Faceモデル読み込み中です。しばらくお待ちください。")
            return None
        
        if hf_manager.get_load_error():
            print(f"Hugging Faceモデル読み込みエラー: {hf_manager.get_load_error()}")
            return None
        
        if not hf_manager.is_ready():
            # モデルがまだ読み込まれていない場合、読み込み完了を待機
            if not hf_manager.wait_for_load(timeout=10.0):  # タイムアウトを延長
                print("Hugging Faceモデル読み込みがタイムアウトしました")
                return None
        
        try:
            # 既存タグとの類似度を計算
            all_tags = []
            for category, keywords in load_category_keywords().items():
                all_tags.extend(keywords)
            
            # より低い閾値で類似タグを検索
            similar_tags = hf_manager.find_similar_tags(tag, all_tags, threshold=0.2, limit=15)
            
            if similar_tags:
                # 類似タグのカテゴリを分析
                category_scores = defaultdict(float)
                for similar_tag, similarity in similar_tags:
                    for category, keywords in load_category_keywords().items():
                        if similar_tag in keywords:
                            category_scores[category] += similarity
                
                if category_scores:
                    best_category = max(category_scores.items(), key=lambda x: x[1])
                    # 信頼度計算を改善
                    total_similarity = sum(category_scores.values())
                    confidence = min(0.95, best_category[1] / total_similarity if total_similarity > 0 else 0.0)
                    
                    # 最低信頼度を設定
                    if confidence < 0.3:
                        confidence = 0.3
                    
                    return best_category[0], confidence, {
                        "reason": "Hugging Faceモデルによる類似度分析",
                        "similar_tags": similar_tags[:3],
                        "total_similarity": total_similarity
                    }
        except Exception as e:
            print(f"Hugging Face予測エラー: {e}")
        
        return None
    
    def _predict_with_local_hf(self, tag: str, context_tags: List[str] = None, local_hf_info: Dict[str, Any] = None) -> Optional[Tuple[str, float, Dict[str, Any]]]:
        """ローカルHugging Faceモデルでの予測"""
        local_hf_manager = self._get_local_hf_manager()
        if local_hf_manager is None:
            return None
        
        # モデルが読み込み中またはエラーの場合
        if local_hf_manager.is_loading():
            print("ローカルHugging Faceモデル読み込み中です。しばらくお待ちください。")
            return None
        
        if local_hf_manager.get_load_error():
            print(f"ローカルHugging Faceモデル読み込みエラー: {local_hf_manager.get_load_error()}")
            return None
        
        if not local_hf_manager.is_ready():
            # モデルがまだ読み込まれていない場合、読み込み完了を待機
            print("ローカルHugging Faceモデルがまだ読み込まれていません。読み込み完了を待機中...")
            if not local_hf_manager.wait_for_load(timeout=60.0):  # タイムアウトを60秒に延長
                print("ローカルHugging Faceモデル読み込みがタイムアウトしました（60秒）")
                return None
        
        try:
            # 既存タグとの類似度を計算
            all_tags = []
            for category, keywords in load_category_keywords().items():
                all_tags.extend(keywords)
            
            similar_tags = local_hf_manager.find_similar_tags(tag, all_tags, threshold=0.3, limit=10)
            
            if similar_tags:
                # 類似タグのカテゴリを分析
                category_scores = defaultdict(float)
                for similar_tag, similarity in similar_tags:
                    for category, keywords in load_category_keywords().items():
                        if similar_tag in keywords:
                            category_scores[category] += similarity
                
                if category_scores:
                    best_category = max(category_scores.items(), key=lambda x: x[1])
                    confidence = min(0.9, best_category[1] / len(similar_tags))
                    return best_category[0], confidence, {
                        "reason": "ローカルHugging Faceモデルによる類似度分析",
                        "similar_tags": similar_tags[:3]
                    }
        except Exception as e:
            print(f"ローカルHugging Face予測エラー: {e}")
        
        return None
    
    def _predict_with_traditional_method(self, tag: str, context_tags: List[str] = None, 
                                       confidence_threshold: float = 0.5, top_n: int = 3) -> Tuple[str, float, Dict[str, Any]]:
        """従来手法での予測"""
        # カスタマイズされたキーワードを取得
        base_keywords = load_category_keywords()
        customized_keywords = get_customized_category_keywords(base_keywords)
        
        # キーワードマッチング
        best_category = None
        best_score = 0.0
        category_scores = {}
        
        for category, keywords in customized_keywords.items():
            # キーワードリスト内の各キーワードに対してスコアを計算
            score = max(calculate_keyword_score(tag, keyword) for keyword in keywords) if keywords else 0
            
            # コンテキスト分析による補正
            if context_tags:
                context_boost = calculate_context_boost(tag, context_tags, category)
                score += context_boost
            
            # 動的重み計算
            dynamic_weight = self.weight_calculator.calculate_dynamic_weight(tag, category, context_tags)
            score *= dynamic_weight
            
            # カスタムルールの適用
            score = apply_custom_rules(tag, category, score, context_tags)
            
            category_scores[category] = score
            if score > best_score:
                best_score = score
                best_category = category
        
        # 類義語チェック
        synonyms = get_synonyms(tag)
        if synonyms:
            for synonym in synonyms:
                for category, keywords in customized_keywords.items():
                    # 類義語がキーワードリスト内にあるかチェック
                    if synonym in keywords:
                        # 類義語自体のスコアを計算
                        synonym_score = max(calculate_keyword_score(synonym, keyword) for keyword in keywords) * 0.8  # 類義語は少し低い重み
                        if synonym_score > category_scores.get(category, 0):
                            category_scores[category] = synonym_score
                            if synonym_score > best_score:
                                best_score = synonym_score
                                best_category = category
        
        # 信頼度の計算
        total_score = sum(category_scores.values())
        confidence = best_score / total_score if total_score > 0 else 0.0
        
        # 上位カテゴリの取得
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        top_categories = sorted_categories[:top_n]
        
        # 学習履歴による修正があるかチェック
        learning_bonus_applied = False
        for category, score in category_scores.items():
            if score > 100:  # 学習履歴ボーナスが適用されている場合
                learning_bonus_applied = True
                break
        
        # 結果の詳細情報
        reason = "キーワードマッチングとコンテキスト分析"
        if learning_bonus_applied:
            reason += "（修正履歴による補正あり）"
        
        details = {
            "reason": reason,
            "category_scores": dict(top_categories),
            "best_score": best_score,
            "total_score": total_score
        }
        
        if synonyms:
            details["synonyms_found"] = synonyms
        
        if context_tags:
            details["context_tags"] = context_tags
        
        return best_category or "未分類", confidence, details
    
    def suggest_similar_tags(self, tag: str, limit: int = 5) -> List[Tuple[str, float]]:
        """類似タグの提案"""
        try:
            # Hugging Faceモデルでの類似タグ検索
            hf_manager = self._get_hf_manager()
            if hf_manager:
                # モデルが読み込み中またはエラーの場合
                if hf_manager.is_loading():
                    print("Hugging Faceモデル読み込み中です。しばらくお待ちください。")
                    return []
                
                if hf_manager.get_load_error():
                    print(f"Hugging Faceモデル読み込みエラー: {hf_manager.get_load_error()}")
                    return []
                
                if not hf_manager.is_ready():
                    # モデルがまだ読み込まれていない場合、読み込み完了を待機
                    if not hf_manager.wait_for_load(timeout=5.0):
                        print("Hugging Faceモデル読み込みがタイムアウトしました")
                        return []
                
                all_tags = []
                for category, keywords in load_category_keywords().items():
                    all_tags.extend(keywords)
                
                similar_tags = hf_manager.find_similar_tags(tag, all_tags, threshold=0.3, limit=limit)
                if similar_tags:
                    return similar_tags
        except Exception as e:
            print(f"類似タグ提案エラー: {e}")
        
        # フォールバック: 類義語辞書を使用
        synonyms = get_synonyms(tag)
        if synonyms:
            return [(synonym, 0.8) for synonym in synonyms[:limit]]
        
        return []
    
    def get_tag_statistics(self, tag: str) -> Dict[str, Any]:
        """タグの統計情報を取得"""
        tag_lower = tag.lower()
        usage_data = self.usage_tracker.usage_data[tag_lower]
        
        return {
            "frequency": self.get_tag_freq(tag),
            "cooccurrences": self.get_tag_cooccurs(tag),
            "usage_count": self.usage_tracker.get_tag_frequency(tag),
            "most_common_category": self.usage_tracker.get_most_common_category(tag),
            "last_used": usage_data.get("last_used", 0)
        }
    
    def record_prediction_result(self, tag: str, predicted_category: str, actual_category: str = None):
        """予測結果を記録"""
        if actual_category:
            # 予測が正しかった場合、使用パターンを記録
            self.usage_tracker.record_tag_usage(tag, actual_category)
    
    def cleanup(self):
        """リソースのクリーンアップ"""
        try:
            if self._hf_manager:
                self._hf_manager.cleanup()
            if self._local_hf_manager:
                self._local_hf_manager.cleanup()
            
            # キャッシュをクリア
            self._prediction_cache.clear()
            
        except Exception as e:
            print(f"クリーンアップエラー: {e}")
    
    def clear_cache(self):
        """予測キャッシュをクリア"""
        self._prediction_cache.clear()
        print("AI予測キャッシュをクリアしました")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        return {
            "cache_size": len(self._prediction_cache),
            "max_cache_size": self._cache_max_size,
            "cache_usage_percent": (len(self._prediction_cache) / self._cache_max_size) * 100
        }

# グローバルインスタンス（遅延読み込み対応）
_ai_predictor_instance = None

def get_ai_predictor():
    """AI予測インスタンスを取得（遅延読み込み）"""
    global _ai_predictor_instance
    if _ai_predictor_instance is None:
        _ai_predictor_instance = AIPredictor()
    return _ai_predictor_instance

# 後方互換性のための関数
def predict_category_ai(tag: str, context_tags: List[str] = None) -> Tuple[str, float]:
    """AI予測関数（後方互換性）"""
    predictor = get_ai_predictor()
    category, confidence, _ = predictor.predict_category_with_confidence(tag, context_tags)
    return category, confidence

def suggest_similar_tags_ai(tag: str, limit: int = 5) -> List[Tuple[str, float]]:
    """類似タグ提案関数（後方互換性）"""
    predictor = get_ai_predictor()
    return predictor.suggest_similar_tags(tag, limit)

# 後方互換性のためのグローバルインスタンス
ai_predictor = get_ai_predictor() 