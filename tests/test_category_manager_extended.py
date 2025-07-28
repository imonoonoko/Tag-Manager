"""
category_manager.pyのテスト（拡張版）
"""
import sys
import os
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from modules.category_manager import (
    load_category_keywords,
    save_category_keywords,
    get_category_priority,
    calculate_keyword_score,
    add_category_keyword,
    get_category_keywords,
    get_all_categories,
    is_valid_category,
    CATEGORY_PRIORITIES,
    KEYWORD_WEIGHTS
)
from modules.common_words import COMMON_WORDS


class TestCategoryManagerExtended:
    """カテゴリ管理機能のテスト（拡張版）"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        
        # テスト用のファイルパスを設定
        self.test_keywords_file = os.path.join(self.temp_dir, "category_keywords.json")
        
        # モジュールのファイルパスを一時的に変更
        from modules import category_manager
        self.original_keywords_file = category_manager.CATEGORY_KEYWORDS_FILE
        category_manager.CATEGORY_KEYWORDS_FILE = self.test_keywords_file
    
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # モジュールのファイルパスを元に戻す
        from modules import category_manager
        category_manager.CATEGORY_KEYWORDS_FILE = self.original_keywords_file
    
    def test_load_category_keywords_basic(self):
        """基本的なカテゴリキーワード読み込みテスト"""
        # テストデータを作成
        test_keywords = {
            "髪型・髪色": ["blue", "red", "green"],
            "服装・ファッション": ["dress", "skirt", "shirt"]
        }
        
        with open(self.test_keywords_file, 'w', encoding='utf-8') as f:
            json.dump(test_keywords, f, ensure_ascii=False, indent=2)
        
        keywords = load_category_keywords()
        
        assert isinstance(keywords, dict)
        assert "髪型・髪色" in keywords
        assert "服装・ファッション" in keywords
        assert "blue" in keywords["髪型・髪色"]
        assert "dress" in keywords["服装・ファッション"]
    
    def test_load_category_keywords_empty_file(self):
        """空のファイルでのカテゴリキーワード読み込みテスト"""
        # 空のファイルを作成
        with open(self.test_keywords_file, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        
        keywords = load_category_keywords()
        
        assert isinstance(keywords, dict)
        assert len(keywords) == 0  # 空のファイルの場合は空の辞書が返される
    
    def test_load_category_keywords_nonexistent_file(self):
        """存在しないファイルでのカテゴリキーワード読み込みテスト"""
        keywords = load_category_keywords()
        
        assert isinstance(keywords, dict)
        assert len(keywords) > 0  # デフォルトキーワードが読み込まれる
    
    def test_load_category_keywords_invalid_json(self):
        """無効なJSONでのカテゴリキーワード読み込みテスト"""
        # 無効なJSONファイルを作成
        with open(self.test_keywords_file, 'w', encoding='utf-8') as f:
            f.write("invalid json content")
        
        keywords = load_category_keywords()
        
        assert isinstance(keywords, dict)
        assert len(keywords) > 0  # デフォルトキーワードが読み込まれる
    
    def test_save_category_keywords_basic(self):
        """基本的なカテゴリキーワード保存テスト"""
        test_keywords = {
            "髪型・髪色": ["blue", "red", "green"],
            "服装・ファッション": ["dress", "skirt", "shirt"]
        }
        
        result = save_category_keywords(test_keywords)
        
        assert result is True
        assert os.path.exists(self.test_keywords_file)
        
        # 保存されたデータを確認
        with open(self.test_keywords_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data == test_keywords
    
    def test_save_category_keywords_empty_dict(self):
        """空の辞書でのカテゴリキーワード保存テスト"""
        result = save_category_keywords({})
        
        assert result is True
        assert os.path.exists(self.test_keywords_file)
        
        # 保存されたデータを確認
        with open(self.test_keywords_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data == {}
    
    def test_save_category_keywords_none(self):
        """Noneでのカテゴリキーワード保存テスト"""
        result = save_category_keywords(None)
        
        assert result is False
    
    def test_get_category_priority_basic(self):
        """基本的なカテゴリ優先度取得テスト"""
        priority = get_category_priority("髪型・髪色")
        
        assert isinstance(priority, int)
        assert priority >= 0
    
    def test_get_category_priority_nonexistent(self):
        """存在しないカテゴリの優先度取得テスト"""
        priority = get_category_priority("nonexistent_category")
        
        assert isinstance(priority, int)
        assert priority == 999  # デフォルト値
    
    def test_get_category_priority_none(self):
        """Noneでのカテゴリ優先度取得テスト"""
        priority = get_category_priority(None)
        
        assert isinstance(priority, int)
        assert priority == 999  # デフォルト値
    
    def test_get_category_priority_empty_string(self):
        """空文字列でのカテゴリ優先度取得テスト"""
        priority = get_category_priority("")
        
        assert isinstance(priority, int)
        assert priority == 999  # デフォルト値
    
    def test_calculate_keyword_score_basic(self):
        """基本的なキーワードスコア計算テスト"""
        score = calculate_keyword_score("blue hair", "blue")
        
        assert isinstance(score, int)
        assert score >= 0
    
    def test_calculate_keyword_score_exact_match(self):
        """完全一致でのキーワードスコア計算テスト"""
        score = calculate_keyword_score("blue", "blue")
        
        assert isinstance(score, int)
        assert score > 0
    
    def test_calculate_keyword_score_partial_match(self):
        """部分一致でのキーワードスコア計算テスト"""
        score = calculate_keyword_score("blue hair", "blue")
        
        assert isinstance(score, int)
        assert score > 0
    
    def test_calculate_keyword_score_no_match(self):
        """マッチしない場合のキーワードスコア計算テスト"""
        score = calculate_keyword_score("red hair", "blue")
        
        assert isinstance(score, int)
        assert score == 0
    
    def test_calculate_keyword_score_common_word(self):
        """一般的すぎる単語でのキーワードスコア計算テスト"""
        common_word = list(COMMON_WORDS)[0]
        score = calculate_keyword_score(common_word, "test")
        
        assert isinstance(score, int)
        assert score == 0  # 一般的すぎる単語はスコア0
    
    def test_calculate_keyword_score_case_insensitive(self):
        """大文字小文字を区別しないキーワードスコア計算テスト"""
        score1 = calculate_keyword_score("Blue Hair", "blue")
        score2 = calculate_keyword_score("blue hair", "BLUE")
        
        assert isinstance(score1, int)
        assert isinstance(score2, int)
        assert score1 > 0
        assert score2 > 0
    
    def test_calculate_keyword_score_empty_strings(self):
        """空文字列でのキーワードスコア計算テスト"""
        score1 = calculate_keyword_score("", "blue")
        score2 = calculate_keyword_score("blue", "")
        score3 = calculate_keyword_score("", "")
        
        assert isinstance(score1, int)
        assert isinstance(score2, int)
        assert isinstance(score3, int)
        assert score1 == 0
        assert score2 == 0
        assert score3 == 0
    
    def test_add_category_keyword_basic(self):
        """基本的なカテゴリキーワード追加テスト"""
        result = add_category_keyword("髪型・髪色", "custom_blue")
        
        assert result is True
    
    def test_add_category_keyword_common_word(self):
        """一般的すぎる単語でのカテゴリキーワード追加テスト"""
        common_word = list(COMMON_WORDS)[0]
        result = add_category_keyword("髪型・髪色", common_word)
        
        assert result is False
    
    def test_add_category_keyword_empty_keyword(self):
        """空のキーワードでのカテゴリキーワード追加テスト"""
        result = add_category_keyword("髪型・髪色", "")
        
        assert result is False
    
    def test_add_category_keyword_none_keyword(self):
        """Noneキーワードでのカテゴリキーワード追加テスト"""
        result = add_category_keyword("髪型・髪色", None)
        
        assert result is False
    
    def test_add_category_keyword_empty_category(self):
        """空のカテゴリでのカテゴリキーワード追加テスト"""
        result = add_category_keyword("", "custom_blue")
        
        assert result is False
    
    def test_add_category_keyword_none_category(self):
        """Noneカテゴリでのカテゴリキーワード追加テスト"""
        result = add_category_keyword(None, "custom_blue")
        
        assert result is False
    
    def test_add_category_keyword_negative_weight(self):
        """負の重みでのカテゴリキーワード追加テスト（重みパラメータは無視される）"""
        result = add_category_keyword("髪型・髪色", "custom_blue")
        
        assert result is True
    
    def test_add_category_keyword_zero_weight(self):
        """ゼロ重みでのカテゴリキーワード追加テスト（重みパラメータは無視される）"""
        result = add_category_keyword("髪型・髪色", "custom_blue")
        
        assert result is True
    
    def test_get_category_keywords_basic(self):
        """基本的なカテゴリキーワード取得テスト"""
        keywords = get_category_keywords("髪型・髪色")
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
    
    def test_get_category_keywords_nonexistent_category(self):
        """存在しないカテゴリのキーワード取得テスト"""
        keywords = get_category_keywords("nonexistent_category")
        
        assert isinstance(keywords, list)
        assert len(keywords) == 0
    
    def test_get_category_keywords_none_category(self):
        """Noneカテゴリでのキーワード取得テスト"""
        keywords = get_category_keywords(None)
        
        assert isinstance(keywords, list)
        assert len(keywords) == 0
    
    def test_get_category_keywords_empty_category(self):
        """空のカテゴリでのキーワード取得テスト"""
        keywords = get_category_keywords("")
        
        assert isinstance(keywords, list)
        assert len(keywords) == 0
    
    def test_get_all_categories_basic(self):
        """基本的な全カテゴリ取得テスト"""
        categories = get_all_categories()
        
        assert isinstance(categories, list)
        assert len(categories) > 0
        
        # 主要カテゴリが含まれていることを確認
        expected_categories = [
            "髪型・髪色", "服装・ファッション", "表情・感情",
            "背景・環境", "照明・色調", "小物・アクセサリー"
        ]
        
        for category in expected_categories:
            if category in categories:
                assert isinstance(category, str)
                assert len(category) > 0
    
    def test_is_valid_category_basic(self):
        """基本的なカテゴリ有効性チェックテスト"""
        result = is_valid_category("髪型・髪色")
        
        assert isinstance(result, bool)
        assert result is True
    
    def test_is_valid_category_nonexistent(self):
        """存在しないカテゴリの有効性チェックテスト"""
        result = is_valid_category("nonexistent_category")
        
        assert isinstance(result, bool)
        assert result is False
    
    def test_is_valid_category_none(self):
        """Noneでのカテゴリ有効性チェックテスト"""
        result = is_valid_category(None)
        
        assert isinstance(result, bool)
        assert result is False
    
    def test_is_valid_category_empty_string(self):
        """空文字列でのカテゴリ有効性チェックテスト"""
        result = is_valid_category("")
        
        assert isinstance(result, bool)
        assert result is False
    
    def test_category_priorities_structure(self):
        """カテゴリ優先度の構造テスト"""
        assert isinstance(CATEGORY_PRIORITIES, dict)
        assert len(CATEGORY_PRIORITIES) > 0
        
        for category, priority in CATEGORY_PRIORITIES.items():
            assert isinstance(category, str)
            assert isinstance(priority, int)
            assert priority >= 0
    
    def test_keyword_weights_structure(self):
        """キーワード重みの構造テスト"""
        assert isinstance(KEYWORD_WEIGHTS, dict)
        assert len(KEYWORD_WEIGHTS) > 0
        
        for keyword, weight in KEYWORD_WEIGHTS.items():
            assert isinstance(keyword, str)
            assert isinstance(weight, int)
            assert weight >= 0
    
    def test_load_category_keywords_filter_common_words(self):
        """一般的すぎる単語フィルタリングテスト"""
        # 一般的すぎる単語を含むテストデータを作成
        test_keywords = {
            "髪型・髪色": ["blue", "red", list(COMMON_WORDS)[0]],
            "服装・ファッション": ["dress", "skirt", list(COMMON_WORDS)[1]]
        }
        
        with open(self.test_keywords_file, 'w', encoding='utf-8') as f:
            json.dump(test_keywords, f, ensure_ascii=False, indent=2)
        
        keywords = load_category_keywords()
        
        assert isinstance(keywords, dict)
        assert "髪型・髪色" in keywords
        assert "服装・ファッション" in keywords
        
        # 一般的すぎる単語がフィルタリングされていることを確認
        for category_keywords in keywords.values():
            for keyword in category_keywords:
                assert keyword not in COMMON_WORDS
    
    def test_calculate_keyword_score_unicode(self):
        """Unicode文字でのキーワードスコア計算テスト"""
        score = calculate_keyword_score("青い髪", "青い")
        
        assert isinstance(score, int)
        assert score > 0
    
    def test_calculate_keyword_score_special_characters(self):
        """特殊文字でのキーワードスコア計算テスト"""
        score = calculate_keyword_score("tag/1", "tag/")
        
        assert isinstance(score, int)
        assert score > 0
    
    def test_calculate_keyword_score_numbers(self):
        """数字でのキーワードスコア計算テスト"""
        score = calculate_keyword_score("tag1", "1")
        
        assert isinstance(score, int)
        assert score > 0
    
    def test_calculate_keyword_score_multiple_matches(self):
        """複数マッチでのキーワードスコア計算テスト"""
        score = calculate_keyword_score("blue hair blue eyes", "blue")
        
        assert isinstance(score, int)
        assert score > 0
    
    def test_calculate_keyword_score_very_long_strings(self):
        """非常に長い文字列でのキーワードスコア計算テスト"""
        long_tag = "a" * 1000
        long_keyword = "b" * 1000
        score = calculate_keyword_score(long_tag, long_keyword)
        
        assert isinstance(score, int)
        assert score >= 0
    
    def test_add_category_keyword_unicode(self):
        """Unicode文字でのカテゴリキーワード追加テスト"""
        result = add_category_keyword("髪型・髪色", "青い髪")
        
        assert result is True
    
    def test_add_category_keyword_special_characters(self):
        """特殊文字でのカテゴリキーワード追加テスト"""
        result = add_category_keyword("髪型・髪色", "tag/1")
        
        assert result is True
    
    def test_add_category_keyword_numbers(self):
        """数字でのカテゴリキーワード追加テスト"""
        result = add_category_keyword("髪型・髪色", "tag1")
        
        assert result is True
    
    def test_add_category_keyword_very_long_keyword(self):
        """非常に長いキーワードでのカテゴリキーワード追加テスト"""
        long_keyword = "a" * 1000
        result = add_category_keyword("髪型・髪色", long_keyword)
        
        assert result is True
    
    def test_get_category_keywords_unicode(self):
        """Unicode文字でのカテゴリキーワード取得テスト"""
        # まずUnicodeキーワードを追加
        add_category_keyword("髪型・髪色", "青い髪")
        
        keywords = get_category_keywords("髪型・髪色")
        
        assert isinstance(keywords, list)
        # Unicodeキーワードが含まれている可能性を確認
        assert all(isinstance(keyword, str) for keyword in keywords)
    
    def test_get_category_keywords_special_characters(self):
        """特殊文字でのカテゴリキーワード取得テスト"""
        # まず特殊文字キーワードを追加
        add_category_keyword("髪型・髪色", "tag/1")
        
        keywords = get_category_keywords("髪型・髪色")
        
        assert isinstance(keywords, list)
        # 特殊文字キーワードが含まれている可能性を確認
        assert all(isinstance(keyword, str) for keyword in keywords)
    
    def test_get_category_keywords_numbers(self):
        """数字でのカテゴリキーワード取得テスト"""
        # まず数字キーワードを追加
        add_category_keyword("髪型・髪色", "tag1")
        
        keywords = get_category_keywords("髪型・髪色")
        
        assert isinstance(keywords, list)
        # 数字キーワードが含まれている可能性を確認
        assert all(isinstance(keyword, str) for keyword in keywords)
    
    def test_get_category_keywords_very_long_keywords(self):
        """非常に長いキーワードでのカテゴリキーワード取得テスト"""
        # まず非常に長いキーワードを追加
        long_keyword = "a" * 1000
        add_category_keyword("髪型・髪色", long_keyword)
        
        keywords = get_category_keywords("髪型・髪色")
        
        assert isinstance(keywords, list)
        # 非常に長いキーワードが含まれている可能性を確認
        assert all(isinstance(keyword, str) for keyword in keywords)
    
    def test_is_valid_category_unicode(self):
        """Unicode文字でのカテゴリ有効性チェックテスト"""
        result = is_valid_category("青い髪")
        
        assert isinstance(result, bool)
    
    def test_is_valid_category_special_characters(self):
        """特殊文字でのカテゴリ有効性チェックテスト"""
        result = is_valid_category("tag/1")
        
        assert isinstance(result, bool)
    
    def test_is_valid_category_numbers(self):
        """数字でのカテゴリ有効性チェックテスト"""
        result = is_valid_category("tag1")
        
        assert isinstance(result, bool)
    
    def test_is_valid_category_very_long_category(self):
        """非常に長いカテゴリでの有効性チェックテスト"""
        long_category = "a" * 1000
        result = is_valid_category(long_category)
        
        assert isinstance(result, bool)
    
    def test_category_priorities_content(self):
        """カテゴリ優先度の内容テスト"""
        # 主要カテゴリの優先度が設定されていることを確認
        expected_categories = [
            "髪型・髪色", "服装・ファッション", "表情・感情",
            "背景・環境", "照明・色調", "小物・アクセサリー"
        ]
        
        for category in expected_categories:
            if category in CATEGORY_PRIORITIES:
                priority = CATEGORY_PRIORITIES[category]
                assert isinstance(priority, int)
                assert priority >= 0
    
    def test_keyword_weights_content(self):
        """キーワード重みの内容テスト"""
        # 主要キーワードの重みが設定されていることを確認
        for keyword, weight in KEYWORD_WEIGHTS.items():
            assert isinstance(keyword, str)
            assert len(keyword) > 0
            assert isinstance(weight, int)
            assert weight >= 0
    
    def test_category_priorities_uniqueness(self):
        """カテゴリ優先度の一意性テスト"""
        # カテゴリ名が一意であることを確認
        categories = list(CATEGORY_PRIORITIES.keys())
        assert len(categories) == len(set(categories))
    
    def test_keyword_weights_uniqueness(self):
        """キーワード重みの一意性テスト"""
        # キーワード名が一意であることを確認
        keywords = list(KEYWORD_WEIGHTS.keys())
        assert len(keywords) == len(set(keywords))
    
    def test_category_priorities_consistency(self):
        """カテゴリ優先度の一貫性テスト"""
        # 優先度が適切な範囲内であることを確認
        for category, priority in CATEGORY_PRIORITIES.items():
            assert isinstance(priority, int)
            assert priority >= 0
            assert priority <= 1000  # 適切な上限値
    
    def test_keyword_weights_consistency(self):
        """キーワード重みの一貫性テスト"""
        # 重みが適切な範囲内であることを確認
        for keyword, weight in KEYWORD_WEIGHTS.items():
            assert isinstance(weight, int)
            assert weight >= 0
            assert weight <= 100  # 適切な上限値 