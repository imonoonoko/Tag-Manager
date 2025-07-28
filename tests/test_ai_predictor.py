"""
ai_predictor.pyのテスト
"""
import sys
import os
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from modules.ai_predictor import (
    TagUsageTracker,
    DynamicWeightCalculator,
    AIPredictor,
    predict_category_ai,
    suggest_similar_tags_ai,
    LEARNING_DATA_FILE,
    TAG_USAGE_PATTERNS_FILE
)
from modules.common_words import COMMON_WORDS

def is_numeric(value):
    """数値型かどうかをチェック（numpy型も含む）"""
    return isinstance(value, (int, float)) or (hasattr(value, 'dtype') and hasattr(value, 'item'))


class TestTagUsageTracker:
    """タグ使用追跡機能のテスト"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_backup_dir = os.environ.get('BACKUP_DIR')
        os.environ['BACKUP_DIR'] = self.temp_dir
        
        # テスト用のファイルパスを設定
        self.test_usage_file = os.path.join(self.temp_dir, "tag_usage_patterns.json")
        self.test_learning_file = os.path.join(self.temp_dir, "learning_data.json")
    
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if self.original_backup_dir:
            os.environ['BACKUP_DIR'] = self.original_backup_dir
        else:
            os.environ.pop('BACKUP_DIR', None)
    
    def test_record_tag_usage(self):
        """タグ使用記録のテスト"""
        # 既存のデータファイルを削除してクリーンな状態でテスト
        if os.path.exists(self.test_usage_file):
            os.remove(self.test_usage_file)
        
        tracker = TagUsageTracker(load_existing_data=False, usage_file=self.test_usage_file)
        tracker.record_tag_usage("blue hair", "髪型・髪色", ["long", "beautiful"])
        
        assert tracker.get_tag_frequency("blue hair") == 1
        assert tracker.get_most_common_category("blue hair") == "髪型・髪色"
    
    def test_record_tag_usage_multiple_times(self):
        """複数回のタグ使用記録テスト"""
        # 既存のデータファイルを削除してクリーンな状態でテスト
        if os.path.exists(self.test_usage_file):
            os.remove(self.test_usage_file)
        
        tracker = TagUsageTracker(load_existing_data=False, usage_file=self.test_usage_file)
        tracker.record_tag_usage("blue hair", "髪型・髪色")
        tracker.record_tag_usage("blue hair", "髪型・髪色")
        tracker.record_tag_usage("blue hair", "色彩・照明")
        
        assert tracker.get_tag_frequency("blue hair") == 3
        assert tracker.get_most_common_category("blue hair") == "髪型・髪色"
    
    def test_get_tag_frequency_nonexistent(self):
        """存在しないタグの頻度取得テスト"""
        tracker = TagUsageTracker(load_existing_data=False, usage_file=self.test_usage_file)
        frequency = tracker.get_tag_frequency("nonexistent")
        
        assert frequency == 0
    
    def test_get_most_common_category_nonexistent(self):
        """存在しないタグのカテゴリ取得テスト"""
        tracker = TagUsageTracker(load_existing_data=False, usage_file=self.test_usage_file)
        category = tracker.get_most_common_category("nonexistent")
        
        assert category is None
    
    def test_get_context_similarity(self):
        """コンテキスト類似度計算テスト"""
        tracker = TagUsageTracker(load_existing_data=False, usage_file=self.test_usage_file)
        tracker.record_tag_usage("blue hair", "髪型・髪色", ["long", "beautiful"])
        tracker.record_tag_usage("red hair", "髪型・髪色", ["long", "beautiful"])
        tracker.record_tag_usage("green eyes", "表情・感情", ["cute"])
        
        similarity1 = tracker.get_context_similarity("blue hair", "red hair")
        similarity2 = tracker.get_context_similarity("blue hair", "green eyes")
        
        assert similarity1 > 0
        assert similarity2 == 0.0
    
    def test_load_usage_data_existing_file(self):
        """既存ファイルからの使用データ読み込みテスト"""
        # テストデータを作成
        test_data = {
            "blue hair": {
                "count": 5,
                "categories": {"髪型・髪色": 3, "色彩・照明": 2},
                "last_used": 1234567890,
                "context_tags": {"long": 2, "beautiful": 1}
            }
        }
        
        with open(self.test_usage_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
        
        tracker = TagUsageTracker(load_existing_data=True, usage_file=self.test_usage_file)
        
        assert tracker.get_tag_frequency("blue hair") == 5
        assert tracker.get_most_common_category("blue hair") == "髪型・髪色"
    
    def test_save_usage_data(self):
        """使用データ保存テスト"""
        # 既存のデータファイルを削除してクリーンな状態でテスト
        if os.path.exists(self.test_usage_file):
            os.remove(self.test_usage_file)
        
        tracker = TagUsageTracker(load_existing_data=False, usage_file=self.test_usage_file)
        tracker.record_tag_usage("blue hair", "髪型・髪色", ["long"])
        
        # 保存を強制実行
        tracker.save_usage_data()
        
        # ファイルが作成されていることを確認
        assert os.path.exists(self.test_usage_file)
        
        # データが正しく保存されていることを確認
        with open(self.test_usage_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert "blue hair" in saved_data
        assert saved_data["blue hair"]["count"] == 1


class TestDynamicWeightCalculator:
    """動的重み計算機能のテスト"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_backup_dir = os.environ.get('BACKUP_DIR')
        os.environ['BACKUP_DIR'] = self.temp_dir
    
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if self.original_backup_dir:
            os.environ['BACKUP_DIR'] = self.original_backup_dir
        else:
            os.environ.pop('BACKUP_DIR', None)
    
    def test_calculate_dynamic_weight_basic(self):
        """基本的な動的重み計算テスト"""
        tracker = TagUsageTracker()
        calculator = DynamicWeightCalculator(tracker)
        
        weight = calculator.calculate_dynamic_weight("blue hair", "髪型・髪色")
        
        assert is_numeric(weight)
        assert weight >= 0
    
    def test_calculate_dynamic_weight_with_context(self):
        """コンテキスト付きの動的重み計算テスト"""
        tracker = TagUsageTracker()
        calculator = DynamicWeightCalculator(tracker)
        
        # 事前に使用データを記録
        tracker.record_tag_usage("blue hair", "髪型・髪色", ["long"])
        tracker.record_tag_usage("long", "髪型・髪色")
        
        weight = calculator.calculate_dynamic_weight("blue hair", "髪型・髪色", ["long"])
        
        assert is_numeric(weight)
        assert weight >= 0
    
    def test_calculate_dynamic_weight_common_word(self):
        """一般的すぎる単語の動的重み計算テスト"""
        tracker = TagUsageTracker()
        calculator = DynamicWeightCalculator(tracker)
        
        common_word = list(COMMON_WORDS)[0]
        weight = calculator.calculate_dynamic_weight(common_word, "髪型・髪色")
        
        assert is_numeric(weight)
        assert weight >= 0


class TestAIPredictor:
    """AI予測機能のテスト"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_backup_dir = os.environ.get('BACKUP_DIR')
        os.environ['BACKUP_DIR'] = self.temp_dir
    
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if self.original_backup_dir:
            os.environ['BACKUP_DIR'] = self.original_backup_dir
        else:
            os.environ.pop('BACKUP_DIR', None)
    
    def test_predict_category_with_confidence_basic(self):
        """基本的なカテゴリ予測テスト"""
        predictor = AIPredictor()
        
        category, confidence, details = predictor.predict_category_with_confidence("blue hair")
        
        assert isinstance(category, str)
        assert is_numeric(confidence)
        assert isinstance(details, dict)
        assert 0 <= confidence <= 1
    
    def test_predict_category_with_confidence_with_context(self):
        """コンテキスト付きのカテゴリ予測テスト"""
        predictor = AIPredictor()
        
        category, confidence, details = predictor.predict_category_with_confidence(
            "blue hair", 
            context_tags=["long", "beautiful"]
        )
        
        assert isinstance(category, str)
        assert is_numeric(confidence)
        assert isinstance(details, dict)
        assert 0 <= confidence <= 1
    
    def test_predict_category_with_confidence_common_word(self):
        """一般的すぎる単語のカテゴリ予測テスト"""
        predictor = AIPredictor()
        
        common_word = list(COMMON_WORDS)[0]
        category, confidence, details = predictor.predict_category_with_confidence(common_word)
        
        assert isinstance(category, str)
        assert is_numeric(confidence)
        assert isinstance(details, dict)
        assert 0 <= confidence <= 1
    
    def test_suggest_similar_tags(self):
        """類似タグ提案テスト"""
        predictor = AIPredictor()
        
        suggestions = predictor.suggest_similar_tags("blue hair", limit=3)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 3
        
        for tag, similarity in suggestions:
            assert isinstance(tag, str)
            assert is_numeric(similarity)
            assert 0 <= similarity <= 1
    
    def test_get_tag_statistics(self):
        """タグ統計取得テスト"""
        predictor = AIPredictor()
        
        stats = predictor.get_tag_statistics("blue hair")
        
        assert isinstance(stats, dict)
        assert "usage_count" in stats
        assert "most_common_category" in stats
        assert "last_used" in stats
    
    def test_record_prediction_result(self):
        """予測結果記録テスト"""
        predictor = AIPredictor()
        
        # 予測結果を記録
        predictor.record_prediction_result("blue hair", "髪型・髪色", "髪型・髪色")
        
        # 統計を取得して確認
        stats = predictor.get_tag_statistics("blue hair")
        assert stats["usage_count"] >= 0


class TestAIPredictorFunctions:
    """AI予測関数のテスト"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_backup_dir = os.environ.get('BACKUP_DIR')
        os.environ['BACKUP_DIR'] = self.temp_dir
    
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if self.original_backup_dir:
            os.environ['BACKUP_DIR'] = self.original_backup_dir
        else:
            os.environ.pop('BACKUP_DIR', None)
    
    def test_predict_category_ai(self):
        """AIカテゴリ予測関数テスト"""
        category, confidence = predict_category_ai("blue hair")
        
        assert isinstance(category, str)
        assert is_numeric(confidence)
        assert 0 <= confidence <= 1
    
    def test_predict_category_ai_with_context(self):
        """コンテキスト付きAIカテゴリ予測関数テスト"""
        category, confidence = predict_category_ai("blue hair", ["long", "beautiful"])
        
        assert isinstance(category, str)
        assert is_numeric(confidence)
        assert 0 <= confidence <= 1
    
    def test_suggest_similar_tags_ai(self):
        """AI類似タグ提案関数テスト"""
        suggestions = suggest_similar_tags_ai("blue hair", limit=3)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 3
        
        for tag, similarity in suggestions:
            assert isinstance(tag, str)
            assert is_numeric(similarity)
            assert 0 <= similarity <= 1
    
    def test_predict_category_ai_common_word(self):
        """一般的すぎる単語のAIカテゴリ予測テスト"""
        common_word = list(COMMON_WORDS)[0]
        category, confidence = predict_category_ai(common_word)
        
        assert isinstance(category, str)
        assert is_numeric(confidence)
        assert 0 <= confidence <= 1


class TestAIPredictorEdgeCases:
    """AI予測機能のエッジケーステスト"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_backup_dir = os.environ.get('BACKUP_DIR')
        os.environ['BACKUP_DIR'] = self.temp_dir
    
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if self.original_backup_dir:
            os.environ['BACKUP_DIR'] = self.original_backup_dir
        else:
            os.environ.pop('BACKUP_DIR', None)
    
    def test_empty_string_prediction(self):
        """空文字列の予測テスト"""
        predictor = AIPredictor()
        
        category, confidence, details = predictor.predict_category_with_confidence("")
        
        assert isinstance(category, str)
        assert is_numeric(confidence)
        assert isinstance(details, dict)
    
    def test_whitespace_only_prediction(self):
        """空白のみの文字列の予測テスト"""
        predictor = AIPredictor()
        
        category, confidence, details = predictor.predict_category_with_confidence("   ")
        
        assert isinstance(category, str)
        assert is_numeric(confidence)
        assert isinstance(details, dict)
    
    def test_special_characters_prediction(self):
        """特殊文字を含む文字列の予測テスト"""
        predictor = AIPredictor()
        
        category, confidence, details = predictor.predict_category_with_confidence("!@#$%^&*()")
        
        assert isinstance(category, str)
        assert is_numeric(confidence)
        assert isinstance(details, dict)
    
    def test_very_long_string_prediction(self):
        """非常に長い文字列の予測テスト"""
        predictor = AIPredictor()
        
        long_string = "a" * 1000
        category, confidence, details = predictor.predict_category_with_confidence(long_string)
        
        assert isinstance(category, str)
        assert is_numeric(confidence)
        assert isinstance(details, dict)
    
    def test_unicode_characters_prediction(self):
        """Unicode文字を含む文字列の予測テスト"""
        predictor = AIPredictor()
        
        unicode_string = "青い髪の美しい少女"
        category, confidence, details = predictor.predict_category_with_confidence(unicode_string)
        
        assert isinstance(category, str)
        assert is_numeric(confidence)
        assert isinstance(details, dict) 


def test_ai_learns_from_reassignment():
    from modules.ai_predictor import ai_predictor
    from modules.customization import customization_manager
    tag = "blue hair"
    category = "髪型・髪色"
    
    # 既存のカスタムルールをクリア
    rules = customization_manager.rule_manager.get_custom_rules()
    for rule in rules:
        if rule.get("condition", {}).get("tag") in [tag, "custom_tag_test"]:
            customization_manager.rule_manager.remove_custom_rule(rule.get("id"))
    
    # 何度か学習させる
    for _ in range(3):
        ai_predictor.usage_tracker.record_tag_usage(tag, category)
    
    # Hugging Faceモデルを無効化して従来手法を使用
    with patch.object(ai_predictor, '_get_hf_manager', return_value=None):
        # 予測で必ず髪型・髪色が最優先になることを確認
        pred_cat, conf, details = ai_predictor.predict_category_with_confidence(tag)
        assert pred_cat == category
        # category_scoresにカテゴリが含まれていることを確認
        assert category in details.get('category_scores', {}) 

def test_ai_reason_and_learning_weight():
    from modules.ai_predictor import ai_predictor
    tag = "blue hair"
    category = "髪型・髪色"
    # 学習履歴を増やす
    for _ in range(10):
        ai_predictor.usage_tracker.record_tag_usage(tag, category)
    
    # Hugging Faceモデルを無効化して従来手法を使用
    with patch.object(ai_predictor, '_get_hf_manager', return_value=None):
        pred_cat, conf, details = ai_predictor.predict_category_with_confidence(tag)
        assert pred_cat == category
        assert "修正履歴" in details.get("reason", "")
        # category_scoresの最高スコアがボーナスを受けていることを確認
        max_score = max(details.get("category_scores", {}).values()) if details.get("category_scores") else 0
        assert max_score >= 200  # ボーナスが効いている

def test_ai_custom_rule_priority():
    from modules.ai_predictor import ai_predictor
    from modules.customization import customization_manager
    tag = "custom_tag_test"
    category = "カスタムカテゴリ"
    # カスタムルールを追加
    customization_manager.rule_manager.add_custom_rule(
        "category_override",
        {"tag": tag},
        {"type": "category_override", "category": category}
    )
    pred_cat, conf, details = ai_predictor.predict_category_with_confidence(tag)
    assert pred_cat == category
    assert "カスタムルール" in details.get("reason", "")
    # 後始末（ルールIDを取得して削除）
    rules = customization_manager.rule_manager.get_custom_rules()
    for rule in rules:
        if rule.get("condition", {}).get("tag") == tag:
            customization_manager.rule_manager.remove_custom_rule(rule.get("id"))
            break

def test_ai_synonym_priority():
    from modules.ai_predictor import ai_predictor
    from modules.context_analyzer import SYNONYM_MAPPING
    from modules.customization import customization_manager
    tag = "blonde"
    category = "髪型・髪色"
    
    # 既存のカスタムルールをクリア
    rules = customization_manager.rule_manager.get_custom_rules()
    for rule in rules:
        if rule.get("condition", {}).get("tag") in ["blond", "blonde"]:
            customization_manager.rule_manager.remove_custom_rule(rule.get("id"))
    
    # 類義語にカスタムルールを追加
    SYNONYM_MAPPING["blonde"] = ["blond", "金髪"]
    customization_manager.rule_manager.add_custom_rule(
        "category_override",
        {"tag": "blond"},
        {"type": "category_override", "category": category}
    )
    pred_cat, conf, details = ai_predictor.predict_category_with_confidence(tag)
    assert pred_cat == category
    assert "カスタムルール" in details.get("reason", "")
    # 後始末（ルールIDを取得して削除）
    rules = customization_manager.rule_manager.get_custom_rules()
    for rule in rules:
        if rule.get("condition", {}).get("tag") == "blond":
            customization_manager.rule_manager.remove_custom_rule(rule.get("id"))
            break 