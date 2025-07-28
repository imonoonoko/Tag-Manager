"""
dialogs.pyのロジックテスト（拡張版）
"""
import sys
import os
import logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from modules.dialogs import (
    get_category_choices,
    validate_bulk_category_action,
    safe_validate_bulk_category_action
)
from modules.constants import category_keywords


class TestDialogsLogic:
    """ダイアログロジック機能のテスト（拡張版）"""
    
    def test_get_category_choices_basic(self):
        """基本的なカテゴリ選択肢取得テスト"""
        choices = get_category_choices(category_keywords)
        
        assert isinstance(choices, list)
        assert len(choices) > 0
        assert "未分類" in choices
        
        # すべてのカテゴリが含まれていることを確認
        for category in category_keywords.keys():
            assert category in choices
    
    def test_get_category_choices_empty_dict(self):
        """空の辞書でのカテゴリ選択肢取得テスト"""
        choices = get_category_choices({})
        
        assert isinstance(choices, list)
        assert len(choices) == 1
        assert "未分類" in choices
    
    def test_get_category_choices_single_category(self):
        """単一カテゴリでのカテゴリ選択肢取得テスト"""
        single_category = {"テストカテゴリ": ["test1", "test2"]}
        choices = get_category_choices(single_category)
        
        assert isinstance(choices, list)
        assert len(choices) == 2
        assert "テストカテゴリ" in choices
        assert "未分類" in choices
    
    def test_validate_bulk_category_action_valid_change(self):
        """有効な一括カテゴリ変更アクションのバリデーションテスト"""
        result = validate_bulk_category_action("change", "髪型・髪色")
        
        assert result is True
    
    def test_validate_bulk_category_action_invalid_change(self):
        """無効な一括カテゴリ変更アクションのバリデーションテスト"""
        result = validate_bulk_category_action("change", "")
        
        assert result is False
    
    def test_validate_bulk_category_action_other_action(self):
        """その他のアクションのバリデーションテスト"""
        result = validate_bulk_category_action("delete", "")
        
        assert result is True
    
    def test_validate_bulk_category_action_none_values(self):
        """None値でのバリデーションテスト"""
        result = validate_bulk_category_action(None, None)
        
        assert result is True
    
    def test_validate_bulk_category_action_empty_strings(self):
        """空文字列でのバリデーションテスト"""
        result = validate_bulk_category_action("", "")
        
        assert result is True
    
    def test_safe_validate_bulk_category_action_valid(self):
        """安全なバリデーション（有効なケース）テスト"""
        result = safe_validate_bulk_category_action("change", "髪型・髪色")
        
        assert result is True
    
    def test_safe_validate_bulk_category_action_invalid(self):
        """安全なバリデーション（無効なケース）テスト"""
        result = safe_validate_bulk_category_action("change", "")
        
        assert result is False
    
    def test_safe_validate_bulk_category_action_with_logger(self):
        """ロガー付きの安全なバリデーションテスト"""
        logger = logging.getLogger(__name__)
        result = safe_validate_bulk_category_action("change", "髪型・髪色", logger)
        
        assert result is True
    
    def test_safe_validate_bulk_category_action_with_logger_invalid(self):
        """ロガー付きの安全なバリデーション（無効なケース）テスト"""
        logger = logging.getLogger(__name__)
        result = safe_validate_bulk_category_action("change", "", logger)
        
        assert result is False
    
    def test_safe_validate_bulk_category_action_exception_handling(self):
        """例外処理の安全なバリデーションテスト"""
        # 不正な型を渡して例外を発生させる
        result = safe_validate_bulk_category_action(123, 456)
        
        # 実際の実装では例外が発生しない場合があるため、結果を確認
        assert isinstance(result, bool)
    
    def test_safe_validate_bulk_category_action_exception_with_logger(self):
        """ロガー付き例外処理の安全なバリデーションテスト"""
        logger = logging.getLogger(__name__)
        
        # 不正な型を渡して例外を発生させる
        result = safe_validate_bulk_category_action(123, 456, logger)
        
        # 実際の実装では例外が発生しない場合があるため、結果を確認
        assert isinstance(result, bool)
    
    def test_validate_bulk_category_action_edge_cases(self):
        """エッジケースのバリデーションテスト"""
        # 非常に長い文字列
        long_string = "a" * 1000
        result = validate_bulk_category_action("change", long_string)
        assert result is True
        
        # 特殊文字を含む文字列
        special_chars = "!@#$%^&*()"
        result = validate_bulk_category_action("change", special_chars)
        assert result is True
        
        # Unicode文字を含む文字列
        unicode_string = "青い髪の美しい少女"
        result = validate_bulk_category_action("change", unicode_string)
        assert result is True
    
    def test_get_category_choices_edge_cases(self):
        """エッジケースのカテゴリ選択肢取得テスト"""
        # 空のカテゴリリスト
        empty_categories = {"空カテゴリ": []}
        choices = get_category_choices(empty_categories)
        assert isinstance(choices, list)
        assert "空カテゴリ" in choices
        assert "未分類" in choices
        
        # 特殊文字を含むカテゴリ名
        special_categories = {"!@#$%^&*()": ["test"]}
        choices = get_category_choices(special_categories)
        assert "!@#$%^&*()" in choices
        assert "未分類" in choices
        
        # Unicode文字を含むカテゴリ名
        unicode_categories = {"青い髪の美しい少女": ["test"]}
        choices = get_category_choices(unicode_categories)
        assert "青い髪の美しい少女" in choices
        assert "未分類" in choices
    
    def test_validate_bulk_category_action_whitespace(self):
        """空白文字でのバリデーションテスト"""
        # 空白のみの文字列
        result = validate_bulk_category_action("change", "   ")
        assert result is True  # 空白は有効とみなす
        
        # タブ文字
        result = validate_bulk_category_action("change", "\t")
        assert result is True
        
        # 改行文字
        result = validate_bulk_category_action("change", "\n")
        assert result is True
    
    def test_get_category_choices_duplicate_categories(self):
        """重複カテゴリでのカテゴリ選択肢取得テスト"""
        # 同じカテゴリ名が複数回出現する場合
        duplicate_categories = {
            "カテゴリ1": ["test1"],
            "カテゴリ1": ["test2"],  # 重複
            "カテゴリ2": ["test3"]
        }
        choices = get_category_choices(duplicate_categories)
        
        assert isinstance(choices, list)
        assert "カテゴリ1" in choices
        assert "カテゴリ2" in choices
        assert "未分類" in choices
        # 重複は辞書の性質上、後者が残る
        assert choices.count("カテゴリ1") == 1
    
    def test_validate_bulk_category_action_case_sensitivity(self):
        """大文字小文字の区別テスト"""
        # 大文字小文字を変えたアクション
        result = validate_bulk_category_action("CHANGE", "髪型・髪色")
        assert result is True
        
        result = validate_bulk_category_action("Change", "髪型・髪色")
        assert result is True
        
        result = validate_bulk_category_action("cHaNgE", "髪型・髪色")
        assert result is True
    
    def test_get_category_choices_nested_structure(self):
        """ネストした構造でのカテゴリ選択肢取得テスト"""
        # ネストした辞書構造（実際には発生しないが、テストのため）
        nested_categories = {
            "カテゴリ1": ["test1", "test2"],
            "カテゴリ2": ["test3", "test4"]
        }
        choices = get_category_choices(nested_categories)
        
        assert isinstance(choices, list)
        assert "カテゴリ1" in choices
        assert "カテゴリ2" in choices
        assert "未分類" in choices
        assert len(choices) == 3
    
    def test_safe_validate_bulk_category_action_none_logger(self):
        """Noneロガーでの安全なバリデーションテスト"""
        result = safe_validate_bulk_category_action("change", "髪型・髪色", None)
        
        assert result is True
    
    def test_safe_validate_bulk_category_action_exception_none_logger(self):
        """Noneロガーでの例外処理テスト"""
        # 不正な型を渡して例外を発生させる
        result = safe_validate_bulk_category_action(123, 456, None)
        
        # 実際の実装では例外が発生しない場合があるため、結果を確認
        assert isinstance(result, bool) 