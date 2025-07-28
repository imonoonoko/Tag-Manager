"""
customization.pyのテスト
"""
import sys
import os
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from modules.customization import (
    UserSettings,
    CustomKeywordManager,
    CustomRuleManager,
    CustomizationManager,
    get_customized_category_keywords,
    apply_custom_rules,
    USER_SETTINGS_FILE,
    CUSTOM_KEYWORDS_FILE,
    CUSTOM_RULES_FILE
)
from modules.common_words import COMMON_WORDS


class TestUserSettings:
    """ユーザー設定機能のテスト"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        
        # テスト用のファイルパスを設定
        self.test_settings_file = os.path.join(self.temp_dir, "user_settings.json")
        
        # モジュールのファイルパスを一時的に変更
        from modules import customization
        self.original_settings_file = customization.USER_SETTINGS_FILE
        customization.USER_SETTINGS_FILE = self.test_settings_file
    
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # モジュールのファイルパスを元に戻す
        from modules import customization
        customization.USER_SETTINGS_FILE = self.original_settings_file
    
    def test_user_settings_initialization(self):
        """ユーザー設定の初期化テスト"""
        settings = UserSettings()
        
        assert settings.settings["ai_prediction_enabled"] is True
        assert settings.settings["confidence_threshold"] == 0.7
        assert settings.settings["auto_suggest_enabled"] is True
        assert settings.settings["learning_enabled"] is True
        assert "ui_preferences" in settings.settings
    
    def test_get_setting_basic(self):
        """基本的な設定取得テスト"""
        settings = UserSettings()
        
        value = settings.get_setting("ai_prediction_enabled")
        assert value is True
        
        value = settings.get_setting("confidence_threshold")
        assert value == 0.7
    
    def test_get_setting_nested(self):
        """ネストした設定取得テスト"""
        settings = UserSettings()
        
        value = settings.get_setting("ui_preferences.theme")
        assert value == "cosmo"
        
        value = settings.get_setting("ui_preferences.window_size")
        assert value == "1200x800"
    
    def test_get_setting_nonexistent(self):
        """存在しない設定の取得テスト"""
        settings = UserSettings()
        
        value = settings.get_setting("nonexistent")
        assert value is None
        
        value = settings.get_setting("nonexistent", "default")
        assert value == "default"
    
    def test_set_setting_basic(self):
        """基本的な設定設定テスト"""
        settings = UserSettings()
        
        settings.set_setting("ai_prediction_enabled", False)
        assert settings.settings["ai_prediction_enabled"] is False
    
    def test_set_setting_nested(self):
        """ネストした設定設定テスト"""
        settings = UserSettings()
        
        settings.set_setting("ui_preferences.theme", "darkly")
        assert settings.settings["ui_preferences"]["theme"] == "darkly"
    
    def test_set_setting_new_nested(self):
        """新しいネストした設定設定テスト"""
        settings = UserSettings()
        
        settings.set_setting("new_category.new_setting", "value")
        assert settings.settings["new_category"]["new_setting"] == "value"
    
    def test_load_settings_existing_file(self):
        """既存ファイルからの設定読み込みテスト"""
        # テストデータを作成
        test_settings = {
            "ai_prediction_enabled": False,
            "confidence_threshold": 0.8,
            "ui_preferences": {
                "theme": "darkly",
                "show_confidence": False
            }
        }
        
        with open(self.test_settings_file, 'w', encoding='utf-8') as f:
            json.dump(test_settings, f, ensure_ascii=False, indent=2)
        
        settings = UserSettings()
        
        assert settings.settings["ai_prediction_enabled"] is False
        assert settings.settings["confidence_threshold"] == 0.8
        assert settings.settings["ui_preferences"]["theme"] == "darkly"
        assert settings.settings["ui_preferences"]["show_confidence"] is False
    
    def test_save_settings(self):
        """設定保存テスト"""
        settings = UserSettings()
        settings.set_setting("test_setting", "test_value")
        
        # 保存を実行
        result = settings.save_settings()
        
        assert result is True
        assert os.path.exists(self.test_settings_file)
        
        # 保存されたデータを確認
        with open(self.test_settings_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data["test_setting"] == "test_value"


class TestCustomKeywordManager:
    """カスタムキーワード管理機能のテスト"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        
        # テスト用のファイルパスを設定
        self.test_keywords_file = os.path.join(self.temp_dir, "custom_keywords.json")
        
        # モジュールのファイルパスを一時的に変更
        from modules import customization
        self.original_keywords_file = customization.CUSTOM_KEYWORDS_FILE
        customization.CUSTOM_KEYWORDS_FILE = self.test_keywords_file
    
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # モジュールのファイルパスを元に戻す
        from modules import customization
        customization.CUSTOM_KEYWORDS_FILE = self.original_keywords_file
    
    def test_custom_keyword_manager_initialization(self):
        """カスタムキーワード管理の初期化テスト"""
        manager = CustomKeywordManager()
        
        assert isinstance(manager.custom_keywords, dict)
    
    def test_add_custom_keyword(self):
        """カスタムキーワード追加テスト"""
        manager = CustomKeywordManager()
        
        result = manager.add_custom_keyword("髪型・髪色", "custom_blue", 1.5)
        
        assert result is True
        assert "髪型・髪色" in manager.custom_keywords
        # 新しいデータ構造に対応
        keywords = manager.custom_keywords["髪型・髪色"]
        assert any(kw["keyword"] == "custom_blue" for kw in keywords)
        assert any(kw["keyword"] == "custom_blue" and kw["weight"] == 1.5 for kw in keywords)
    
    def test_add_custom_keyword_common_word(self):
        """一般的すぎる単語のカスタムキーワード追加テスト"""
        manager = CustomKeywordManager()
        
        common_word = list(COMMON_WORDS)[0]
        result = manager.add_custom_keyword("髪型・髪色", common_word, 1.5)
        
        assert result is False
    
    def test_remove_custom_keyword(self):
        """カスタムキーワード削除テスト"""
        manager = CustomKeywordManager()
        
        # まずキーワードを追加
        manager.add_custom_keyword("髪型・髪色", "custom_blue", 1.5)
        
        # 削除を実行
        result = manager.remove_custom_keyword("髪型・髪色", "custom_blue")
        
        assert result is True
        keywords = manager.custom_keywords["髪型・髪色"]
        assert not any(kw["keyword"] == "custom_blue" for kw in keywords)
    
    def test_remove_custom_keyword_nonexistent(self):
        """存在しないカスタムキーワード削除テスト"""
        manager = CustomKeywordManager()
        
        result = manager.remove_custom_keyword("髪型・髪色", "nonexistent")
        
        assert result is False
    
    def test_get_custom_keywords_all(self):
        """全カスタムキーワード取得テスト"""
        manager = CustomKeywordManager()
        
        manager.add_custom_keyword("髪型・髪色", "custom_blue", 1.5)
        manager.add_custom_keyword("表情・感情", "custom_smile", 2.0)
        
        keywords = manager.get_custom_keywords()
        
        assert "髪型・髪色" in keywords
        assert "表情・感情" in keywords
        assert any(kw["keyword"] == "custom_blue" for kw in keywords["髪型・髪色"])
        assert any(kw["keyword"] == "custom_smile" for kw in keywords["表情・感情"])
    
    def test_get_custom_keywords_specific_category(self):
        """特定カテゴリのカスタムキーワード取得テスト"""
        manager = CustomKeywordManager()
        
        manager.add_custom_keyword("髪型・髪色", "custom_blue", 1.5)
        manager.add_custom_keyword("表情・感情", "custom_smile", 2.0)
        
        keywords = manager.get_custom_keywords("髪型・髪色")
        
        assert any(kw["keyword"] == "custom_blue" for kw in keywords)
        assert not any(kw["keyword"] == "custom_smile" for kw in keywords)
    
    def test_get_custom_keyword_weight(self):
        """カスタムキーワード重み取得テスト"""
        manager = CustomKeywordManager()
        
        manager.add_custom_keyword("髪型・髪色", "custom_blue", 1.5)
        
        weight = manager.get_custom_keyword_weight("髪型・髪色", "custom_blue")
        
        assert weight == 1.5
    
    def test_get_custom_keyword_weight_nonexistent(self):
        """存在しないカスタムキーワード重み取得テスト"""
        manager = CustomKeywordManager()
        
        weight = manager.get_custom_keyword_weight("髪型・髪色", "nonexistent")
        
        assert weight == 1.0
    
    def test_load_custom_keywords_existing_file(self):
        """既存ファイルからのカスタムキーワード読み込みテスト"""
        # テストデータを作成（新しいデータ構造）
        test_keywords = {
            "髪型・髪色": [
                {"keyword": "custom_blue", "weight": 1.5, "created_at": "2025-07-27"},
                {"keyword": "custom_red", "weight": 2.0, "created_at": "2025-07-27"}
            ]
        }
        
        with open(self.test_keywords_file, 'w', encoding='utf-8') as f:
            json.dump(test_keywords, f, ensure_ascii=False, indent=2)
        
        manager = CustomKeywordManager()
        
        assert "髪型・髪色" in manager.custom_keywords
        keywords = manager.custom_keywords["髪型・髪色"]
        assert any(kw["keyword"] == "custom_blue" for kw in keywords)
        assert any(kw["keyword"] == "custom_blue" and kw["weight"] == 1.5 for kw in keywords)
    
    def test_save_custom_keywords(self):
        """カスタムキーワード保存テスト"""
        manager = CustomKeywordManager()
        manager.add_custom_keyword("髪型・髪色", "custom_blue", 1.5)
        
        # 保存を実行
        result = manager.save_custom_keywords()
        
        assert result is True
        assert os.path.exists(self.test_keywords_file)
        
        # 保存されたデータを確認
        with open(self.test_keywords_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert "髪型・髪色" in saved_data
        keywords = saved_data["髪型・髪色"]
        assert any(kw["keyword"] == "custom_blue" for kw in keywords)


class TestCustomRuleManager:
    """カスタムルール管理機能のテスト"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        
        # テスト用のファイルパスを設定
        self.test_rules_file = os.path.join(self.temp_dir, "custom_rules.json")
        
        # モジュールのファイルパスを一時的に変更
        from modules import customization
        self.original_rules_file = customization.CUSTOM_RULES_FILE
        customization.CUSTOM_RULES_FILE = self.test_rules_file
    
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # モジュールのファイルパスを元に戻す
        from modules import customization
        customization.CUSTOM_RULES_FILE = self.original_rules_file
    
    def test_custom_rule_manager_initialization(self):
        """カスタムルール管理の初期化テスト"""
        manager = CustomRuleManager()
        
        assert isinstance(manager.custom_rules, list)
    
    def test_add_custom_rule(self):
        """カスタムルール追加テスト"""
        manager = CustomRuleManager()
        
        condition = {"type": "keyword_match", "keyword": "blue"}
        action = {"type": "boost_score", "value": 10}
        
        result = manager.add_custom_rule("keyword_boost", condition, action, 1)
        
        assert result is True
        assert len(manager.custom_rules) == 1
        assert manager.custom_rules[0]["type"] == "keyword_boost"
    
    def test_remove_custom_rule(self):
        """カスタムルール削除テスト"""
        manager = CustomRuleManager()
        
        condition = {"type": "keyword_match", "keyword": "blue"}
        action = {"type": "boost_score", "value": 10}
        
        manager.add_custom_rule("keyword_boost", condition, action, 1)
        
        # ルールIDを取得して削除
        rules = manager.get_custom_rules()
        rule_id = rules[0]["id"]
        
        result = manager.remove_custom_rule(rule_id)
        
        assert result is True
        assert len(manager.custom_rules) == 0
    
    def test_remove_custom_rule_nonexistent(self):
        """存在しないカスタムルール削除テスト"""
        manager = CustomRuleManager()
        
        result = manager.remove_custom_rule("nonexistent")
        
        assert result is False
    
    def test_get_custom_rules_all(self):
        """全カスタムルール取得テスト"""
        manager = CustomRuleManager()
        
        condition1 = {"type": "keyword_match", "keyword": "blue"}
        action1 = {"type": "boost_score", "value": 10}
        manager.add_custom_rule("keyword_boost", condition1, action1, 1)
        
        condition2 = {"type": "keyword_match", "keyword": "red"}
        action2 = {"type": "boost_score", "value": 5}
        manager.add_custom_rule("keyword_boost", condition2, action2, 1)
        
        rules = manager.get_custom_rules()
        
        assert len(rules) == 2
        assert all(rule["type"] == "keyword_boost" for rule in rules)
    
    def test_get_custom_rules_specific_type(self):
        """特定タイプのカスタムルール取得テスト"""
        manager = CustomRuleManager()
        
        condition1 = {"type": "keyword_match", "keyword": "blue"}
        action1 = {"type": "boost_score", "value": 10}
        manager.add_custom_rule("keyword_boost", condition1, action1, 1)
        
        condition2 = {"type": "keyword_match", "keyword": "red"}
        action2 = {"type": "boost_score", "value": 5}
        manager.add_custom_rule("category_boost", condition2, action2, 1)
        
        rules = manager.get_custom_rules("keyword_boost")
        
        assert len(rules) == 1
        assert rules[0]["type"] == "keyword_boost"
    
    def test_evaluate_custom_rules(self):
        """カスタムルール評価テスト"""
        manager = CustomRuleManager()
        
        condition = {"type": "keyword_match", "keyword": "blue"}
        action = {"type": "boost_score", "value": 10}
        manager.add_custom_rule("keyword_boost", condition, action, 1)
        
        result = manager.evaluate_custom_rules("blue hair")
        
        assert isinstance(result, dict)
        # 結果の構造を確認（実際の実装に合わせて調整）
        assert len(result) > 0
    
    def test_evaluate_custom_rules_no_match(self):
        """マッチしないカスタムルール評価テスト"""
        manager = CustomRuleManager()
        
        condition = {"type": "keyword_match", "keyword": "blue"}
        action = {"type": "boost_score", "value": 10}
        manager.add_custom_rule("keyword_boost", condition, action, 1)
        
        result = manager.evaluate_custom_rules("red hair")
        
        assert isinstance(result, dict)
        assert len(result) == 0
    
    def test_load_custom_rules_existing_file(self):
        """既存ファイルからのカスタムルール読み込みテスト"""
        # テストデータを作成（新しいデータ構造）
        test_rules = [
            {
                "id": "test_rule_1",
                "type": "keyword_boost",
                "condition": {"type": "keyword_match", "keyword": "blue"},
                "action": {"type": "boost_score", "value": 10},
                "priority": 1,
                "enabled": True,
                "created_at": "2025-07-27"
            }
        ]
        
        with open(self.test_rules_file, 'w', encoding='utf-8') as f:
            json.dump(test_rules, f, ensure_ascii=False, indent=2)
        
        manager = CustomRuleManager()
        
        assert len(manager.custom_rules) == 1
        assert manager.custom_rules[0]["type"] == "keyword_boost"
    
    def test_save_custom_rules(self):
        """カスタムルール保存テスト"""
        manager = CustomRuleManager()
        
        condition = {"type": "keyword_match", "keyword": "blue"}
        action = {"type": "boost_score", "value": 10}
        manager.add_custom_rule("keyword_boost", condition, action, 1)
        
        # 保存を実行
        result = manager.save_custom_rules()
        
        assert result is True
        assert os.path.exists(self.test_rules_file)
        
        # 保存されたデータを確認
        with open(self.test_rules_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert len(saved_data) == 1
        assert saved_data[0]["type"] == "keyword_boost"


class TestCustomizationManager:
    """カスタマイズ管理機能のテスト"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_customization_manager_initialization(self):
        """カスタマイズ管理の初期化テスト"""
        manager = CustomizationManager()
        
        assert manager.settings is not None
        assert manager.keyword_manager is not None
        assert manager.rule_manager is not None
    
    def test_get_enhanced_category_keywords(self):
        """拡張カテゴリキーワード取得テスト"""
        manager = CustomizationManager()
        
        base_keywords = {
            "髪型・髪色": ["blue", "red"],
            "表情・感情": ["smile", "cry"]
        }
        
        # カスタムキーワードを追加
        manager.keyword_manager.add_custom_keyword("髪型・髪色", "custom_blue", 1.5)
        
        enhanced_keywords = manager.get_enhanced_category_keywords(base_keywords)
        
        assert "髪型・髪色" in enhanced_keywords
        assert "custom_blue" in enhanced_keywords["髪型・髪色"]
        assert "blue" in enhanced_keywords["髪型・髪色"]
    
    def test_apply_custom_rules_to_score(self):
        """カスタムルール適用テスト"""
        manager = CustomizationManager()
        
        # 既存のルールをクリア
        manager.rule_manager.custom_rules = []
        
        # カスタムルールを追加
        condition = {"type": "keyword_match", "keyword": "blue"}
        action = {"type": "boost_score", "value": 10}
        manager.rule_manager.add_custom_rule("keyword_boost", condition, action, 1)
        
        score = manager.apply_custom_rules_to_score("blue hair", "髪型・髪色", 50.0)
        
        assert score == 60.0  # 基本スコア50 + ブースト10
    
    def test_get_customization_summary(self):
        """カスタマイズ要約取得テスト"""
        manager = CustomizationManager()
        
        # 既存のカスタムキーワードとルールをクリア
        manager.keyword_manager.custom_keywords = {}
        manager.rule_manager.custom_rules = []
        
        # カスタムキーワードとルールを追加
        manager.keyword_manager.add_custom_keyword("髪型・髪色", "custom_blue", 1.5)
        
        condition = {"type": "keyword_match", "keyword": "blue"}
        action = {"type": "boost_score", "value": 10}
        manager.rule_manager.add_custom_rule("keyword_boost", condition, action, 1)
        
        summary = manager.get_customization_summary()
        
        assert "custom_keywords_count" in summary
        assert "custom_rules_count" in summary
        assert "categories_with_custom_keywords" in summary
        assert summary["custom_keywords_count"] == 1
        assert summary["custom_rules_count"] == 1


class TestCustomizationFunctions:
    """カスタマイズ関数のテスト"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_get_customized_category_keywords(self):
        """カスタマイズされたカテゴリキーワード取得テスト"""
        base_keywords = {
            "髪型・髪色": ["blue", "red"],
            "表情・感情": ["smile", "cry"]
        }
        
        customized_keywords = get_customized_category_keywords(base_keywords)
        
        assert isinstance(customized_keywords, dict)
        assert "髪型・髪色" in customized_keywords
        assert "表情・感情" in customized_keywords
    
    def test_apply_custom_rules(self):
        """カスタムルール適用テスト"""
        score = apply_custom_rules("blue hair", "髪型・髪色", 50.0)
        
        assert isinstance(score, float)
        assert score >= 50.0  # 基本スコア以上であることを確認
    
    def test_apply_custom_rules_with_context(self):
        """コンテキスト付きカスタムルール適用テスト"""
        score = apply_custom_rules("blue hair", "髪型・髪色", 50.0, ["long", "beautiful"])
        
        assert isinstance(score, float)
        assert score >= 50.0  # 基本スコア以上であることを確認 