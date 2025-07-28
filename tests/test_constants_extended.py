"""
constants.pyのテスト（拡張版）
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from modules.constants import (
    safe_load_json,
    auto_assign_category_context_aware_pure,
    auto_assign_category_advanced_pure,
    auto_assign_category_pure,
    auto_assign_category
)
from modules.config import (
    POSITIVE_PROMPT_FILE, NEGATIVE_PROMPT_FILE, DB_FILE, THEME_FILE,
    TRANSLATING_PLACEHOLDER, CATEGORY_KEYWORDS_FILE, DEFAULT_CATEGORIES,
    SUPPORTED_IMPORT_FORMATS, SUPPORTED_EXPORT_FORMATS, LOG_LEVEL, LOG_FILE,
    CACHE_TIMEOUT, MAX_CONCURRENT_OPERATIONS, BATCH_SIZE, DEFAULT_WINDOW_SIZE
)


class TestConstantsExtended:
    """定数機能のテスト（拡張版）"""
    
    def test_safe_load_json_valid_file(self):
        """有効なJSONファイルの読み込みテスト"""
        import tempfile
        import json
        
        # 一時的なJSONファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_data = {"test": "data", "number": 123}
            json.dump(test_data, f)
            temp_file = f.name
        
        try:
            result = safe_load_json(temp_file)
            assert result == test_data
        finally:
            os.unlink(temp_file)
    
    def test_safe_load_json_invalid_file(self):
        """無効なJSONファイルの読み込みテスト"""
        import tempfile
        
        # 無効なJSONファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name
        
        try:
            result = safe_load_json(temp_file)
            assert result is None
        finally:
            os.unlink(temp_file)
    
    def test_safe_load_json_nonexistent_file(self):
        """存在しないファイルの読み込みテスト"""
        result = safe_load_json("nonexistent_file.json")
        assert result is None
    
    def test_auto_assign_category_context_aware_pure(self):
        """コンテキスト認識版カテゴリ自動割り当てテスト"""
        # 正常なケース
        result, details = auto_assign_category_context_aware_pure(
            "beautiful landscape", 
            {"背景・環境": ["landscape", "beautiful"]}
        )
        assert isinstance(result, str)
        assert isinstance(details, dict)
        assert "score" in details
        
        # 空のタグ
        result, details = auto_assign_category_context_aware_pure("", {})
        assert result == "未分類"
        
        # Noneのタグ
        result, details = auto_assign_category_context_aware_pure(None, {})
        assert result == "未分類"
    
    def test_auto_assign_category_advanced_pure(self):
        """高度版カテゴリ自動割り当てテスト"""
        # 正常なケース
        result, details = auto_assign_category_advanced_pure(
            "beautiful landscape", 
            {"背景・環境": ["landscape", "beautiful"]}
        )
        assert isinstance(result, str)
        assert isinstance(details, dict)
        
        # 空のタグ
        result, details = auto_assign_category_advanced_pure("", {})
        assert result == "未分類"
    
    def test_auto_assign_category_pure(self):
        """基本版カテゴリ自動割り当てテスト"""
        # 正常なケース
        result = auto_assign_category_pure(
            "beautiful landscape", 
            {"背景・環境": ["landscape", "beautiful"]}
        )
        assert isinstance(result, str)
        
        # 空のタグ
        result = auto_assign_category_pure("", {})
        assert result == "未分類"
    
    def test_auto_assign_category(self):
        """後方互換性用カテゴリ自動割り当てテスト"""
        # 正常なケース
        result = auto_assign_category("beautiful landscape")
        assert isinstance(result, str)
        
        # 空のタグ
        result = auto_assign_category("")
        assert result == "未分類"
    
    def test_config_constants(self):
        """設定定数のテスト"""
        assert isinstance(POSITIVE_PROMPT_FILE, str)
        assert isinstance(NEGATIVE_PROMPT_FILE, str)
        assert isinstance(DB_FILE, str)
        assert isinstance(THEME_FILE, str)
        assert isinstance(TRANSLATING_PLACEHOLDER, str)
        assert isinstance(CATEGORY_KEYWORDS_FILE, str)
        assert isinstance(LOG_LEVEL, str)
        assert isinstance(LOG_FILE, str)
        assert isinstance(CACHE_TIMEOUT, int)
        assert isinstance(MAX_CONCURRENT_OPERATIONS, int)
        assert isinstance(BATCH_SIZE, int)
        assert isinstance(DEFAULT_WINDOW_SIZE, str)
        assert isinstance(DEFAULT_CATEGORIES, list)
        assert isinstance(SUPPORTED_IMPORT_FORMATS, list)
        assert isinstance(SUPPORTED_EXPORT_FORMATS, list) 