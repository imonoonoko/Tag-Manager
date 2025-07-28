"""
tag_manager.pyのテスト（拡張版）
"""
import sys
import os
import sqlite3
import tempfile
import shutil
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from modules.tag_manager import (
    TagManager,
    normalize_tag,
    is_valid_tag,
    assign_category_if_needed,
    google_translate_en_to_ja,
    is_valid_json_file_path,
    is_writable_path,
    is_valid_category
)


class TestTagManagerExtended:
    """タグ管理機能のテスト（拡張版）"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, "test_tags.db")
        self.tag_manager = TagManager(self.test_db_path)
    
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        if hasattr(self, 'tag_manager'):
            self.tag_manager.close()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_normalize_tag_basic(self):
        """基本的なタグ正規化テスト"""
        result = normalize_tag("  test tag  ")
        assert result == "test tag"
    
    def test_normalize_tag_with_weight(self):
        """ウェイト表記付きタグの正規化テスト"""
        result = normalize_tag("(test:1.5)")
        assert result == "test"
    
    def test_normalize_tag_with_newlines(self):
        """改行付きタグの正規化テスト"""
        result = normalize_tag("test\ntag\r\n")
        assert result == "testtag"
    
    def test_normalize_tag_invalid_input(self):
        """無効な入力のタグ正規化テスト"""
        result = normalize_tag(None)
        assert result == ""
        
        result = normalize_tag(123)
        assert result == ""
    
    def test_is_valid_tag_basic(self):
        """基本的なタグ有効性テスト"""
        assert is_valid_tag("valid tag") is True
        assert is_valid_tag("") is False
        assert is_valid_tag(None) is False
    
    def test_is_valid_tag_length(self):
        """タグ長さの有効性テスト"""
        # 64文字以内は有効
        assert is_valid_tag("a" * 64) is True
        # 65文字以上は無効
        assert is_valid_tag("a" * 65) is False
    
    def test_is_valid_tag_special_characters(self):
        """特殊文字の有効性テスト"""
        invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            assert is_valid_tag(f"test{char}tag") is False
    
    def test_assign_category_if_needed(self):
        """カテゴリ自動割り当てテスト"""
        def mock_auto_assign(tag):
            return "自動カテゴリ"
        
        # カテゴリが空の場合
        result = assign_category_if_needed("test tag", "", mock_auto_assign)
        assert result == "自動カテゴリ"
        
        # カテゴリが既に設定されている場合
        result = assign_category_if_needed("test tag", "既存カテゴリ", mock_auto_assign)
        assert result == "既存カテゴリ"
    
    def test_is_valid_json_file_path(self):
        """JSONファイルパスの有効性テスト"""
        # 有効なJSONファイル
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            f.write(b'{"test": "data"}')
            temp_file = f.name
        
        try:
            assert is_valid_json_file_path(temp_file) is True
        finally:
            os.unlink(temp_file)
        
        # 無効なパス
        assert is_valid_json_file_path("nonexistent.json") is False
        assert is_valid_json_file_path("test.txt") is False
        assert is_valid_json_file_path("") is False
        assert is_valid_json_file_path(None) is False
    
    def test_is_writable_path(self):
        """書き込み可能パスのテスト"""
        # 一時ディレクトリは書き込み可能
        assert is_writable_path(self.test_db_path) is True
        
        # 存在しないディレクトリ
        assert is_writable_path("/nonexistent/path/file.txt") is False
    
    def test_is_valid_category(self):
        """カテゴリ有効性テスト"""
        assert is_valid_category("valid category") is True
        assert is_valid_category("") is False
        assert is_valid_category(None) is False
        
        # 長さ制限
        assert is_valid_category("a" * 64) is True
        assert is_valid_category("a" * 65) is False
        
        # 特殊文字制限
        invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            assert is_valid_category(f"test{char}category") is False
    
    def test_tag_manager_basic_operations(self):
        """TagManagerの基本操作テスト"""
        # タグ追加
        result = self.tag_manager.add_tag("test tag", False, "テストカテゴリ")
        assert result is True
        
        # タグ存在確認
        assert self.tag_manager.exists_tag("test tag") is True
        
        # 全タグ取得
        tags = self.tag_manager.get_all_tags()
        assert len(tags) > 0
        
        # タグ削除
        result = self.tag_manager.delete_tag("test tag")
        assert result is True
        assert self.tag_manager.exists_tag("test tag") is False
    
    def test_tag_manager_favorite_operations(self):
        """TagManagerのお気に入り操作テスト"""
        # タグ追加
        self.tag_manager.add_tag("favorite tag", False, "テストカテゴリ")
        
        # お気に入り切り替え
        result = self.tag_manager.toggle_favorite("favorite tag")
        assert result is True
        
        # タグ存在確認
        assert self.tag_manager.exists_tag("favorite tag") is True
    
    def test_tag_manager_category_operations(self):
        """TagManagerのカテゴリ操作テスト"""
        # タグ追加
        self.tag_manager.add_tag("category tag", False, "初期カテゴリ")
        
        # カテゴリ変更
        result = self.tag_manager.set_category("category tag", "新しいカテゴリ")
        assert result is True
        
        # タグ存在確認
        assert self.tag_manager.exists_tag("category tag") is True
    
    def test_tag_manager_negative_tags(self):
        """TagManagerのネガティブタグテスト"""
        # ネガティブタグ追加
        result = self.tag_manager.add_tag("negative tag", True, "ネガティブカテゴリ")
        assert result is True
        
        # ネガティブタグ確認
        assert self.tag_manager.exists_tag("negative tag") is True
        
        # ネガティブタグ一覧取得
        negative_tags = self.tag_manager.negative_tags
        assert len(negative_tags) > 0 