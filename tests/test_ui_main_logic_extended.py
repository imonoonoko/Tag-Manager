"""
ui_main.pyのロジックテスト（拡張版）
"""
import sys
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from modules.ui_main import (
    build_category_descriptions,
    build_category_list
)
from modules.category_manager import CATEGORY_PRIORITIES


class TestUIMainLogicExtended:
    """UIメインロジック機能のテスト（拡張版）"""
    
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
    
    def test_build_category_descriptions_basic(self):
        """基本的なカテゴリ説明構築テスト"""
        descriptions = build_category_descriptions()
        
        assert isinstance(descriptions, dict)
        assert len(descriptions) > 0
        
        # 主要カテゴリが含まれていることを確認
        expected_categories = [
            "全カテゴリ", "お気に入り", "最近使った", "未分類",
            "品質・画質指定", "スタイル・技法", "キャラクター設定"
        ]
        
        for category in expected_categories:
            assert category in descriptions
            assert isinstance(descriptions[category], str)
            assert len(descriptions[category]) > 0
    
    def test_build_category_list_basic(self):
        """基本的なカテゴリリスト構築テスト"""
        test_keywords = {
            "カテゴリ1": ["keyword1", "keyword2"],
            "カテゴリ2": ["keyword3", "keyword4"]
        }
        
        category_list = build_category_list(test_keywords)
        
        assert isinstance(category_list, list)
        assert len(category_list) == 6  # 4つの固定カテゴリ + 2つの動的カテゴリ
        
        # 固定カテゴリが含まれていることを確認
        fixed_categories = ["全カテゴリ", "お気に入り", "最近使った", "未分類"]
        for category in fixed_categories:
            assert category in category_list
        
        # 動的カテゴリが含まれていることを確認
        for category in test_keywords.keys():
            assert category in category_list
    
    def test_build_category_list_empty_keywords(self):
        """空のキーワードでのカテゴリリスト構築テスト"""
        category_list = build_category_list({})
        
        assert isinstance(category_list, list)
        assert len(category_list) == 4  # 固定カテゴリのみ
        
        fixed_categories = ["全カテゴリ", "お気に入り", "最近使った", "未分類"]
        for category in fixed_categories:
            assert category in category_list
    

    

    
 