"""
dialogs.pyのGUIテスト（拡張版）
"""
import sys
import os
import tkinter as tk
import ttkbootstrap as tb
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from modules.dialogs import CategorySelectDialog, BulkCategoryDialog
from modules.constants import category_keywords


class TestCategorySelectDialog:
    """カテゴリ選択ダイアログのテスト（拡張版）"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        try:
            self.root = tk.Tk()
            self.root.withdraw()  # ウィンドウを非表示に
        except Exception:
            pytest.skip("Tkinterが利用できないためスキップ")
        self.categories = ["カテゴリ1", "カテゴリ2", "カテゴリ3"]
    
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        if hasattr(self, 'root'):
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass
    
    @pytest.mark.gui
    def test_category_select_dialog_initialization(self):
        """カテゴリ選択ダイアログの初期化テスト"""
        dialog = CategorySelectDialog(self.root, self.categories)
        
        assert dialog.result is None
        assert dialog.categories == self.categories
        assert dialog.title() == "カテゴリ選択"
    
    @pytest.mark.gui
    def test_category_select_dialog_ui_elements(self):
        """カテゴリ選択ダイアログのUI要素テスト"""
        dialog = CategorySelectDialog(self.root, self.categories)
        
        # ラベルが存在することを確認
        assert hasattr(dialog, 'label')
        assert dialog.label.cget('text') == "カテゴリを選択してください:"
        
        # コンボボックスが存在することを確認
        assert hasattr(dialog, 'combobox')
        assert dialog.combobox.cget('values') == self.categories
        
        # 初期選択が設定されていることを確認
        assert dialog.category_var.get() == self.categories[0]
    
    @pytest.mark.gui
    def test_category_select_dialog_ok_action(self):
        """カテゴリ選択ダイアログのOKアクションテスト"""
        dialog = CategorySelectDialog(self.root, self.categories)
        
        # カテゴリを選択
        dialog.category_var.set("カテゴリ2")
        
        # OKボタンをクリック
        dialog.ok()
        
        assert dialog.result == "カテゴリ2"
    
    @pytest.mark.gui
    def test_category_select_dialog_cancel_action(self):
        """カテゴリ選択ダイアログのキャンセルアクションテスト"""
        dialog = CategorySelectDialog(self.root, self.categories)
        
        # キャンセルボタンをクリック
        dialog.cancel()
        
        assert dialog.result is None
    
    @pytest.mark.gui
    def test_category_select_dialog_empty_categories(self):
        """空のカテゴリリストでのダイアログテスト"""
        dialog = CategorySelectDialog(self.root, [])
        
        assert dialog.categories == []
        assert dialog.combobox.cget('values') == []
    
    @pytest.mark.gui
    def test_category_select_dialog_single_category(self):
        """単一カテゴリでのダイアログテスト"""
        single_category = ["カテゴリ1"]
        dialog = CategorySelectDialog(self.root, single_category)
        
        assert dialog.categories == single_category
        assert dialog.combobox.cget('values') == single_category
        assert dialog.category_var.get() == "カテゴリ1"
    
    @pytest.mark.gui
    def test_category_select_dialog_unicode_categories(self):
        """Unicode文字を含むカテゴリでのダイアログテスト"""
        unicode_categories = ["青い髪", "赤い服", "緑の目"]
        dialog = CategorySelectDialog(self.root, unicode_categories)
        
        assert dialog.categories == unicode_categories
        assert dialog.combobox.cget('values') == unicode_categories
        assert dialog.category_var.get() == "青い髪"
    
    @pytest.mark.gui
    def test_category_select_dialog_special_characters(self):
        """特殊文字を含むカテゴリでのダイアログテスト"""
        special_categories = ["カテゴリ/1", "カテゴリ\\2", "カテゴリ*3"]
        dialog = CategorySelectDialog(self.root, special_categories)
        
        assert dialog.categories == special_categories
        assert dialog.combobox.cget('values') == special_categories
    
    @pytest.mark.gui
    def test_category_select_dialog_very_long_categories(self):
        """非常に長いカテゴリ名でのダイアログテスト"""
        long_categories = ["a" * 100, "b" * 200, "c" * 300]
        dialog = CategorySelectDialog(self.root, long_categories)
        
        assert dialog.categories == long_categories
        assert dialog.combobox.cget('values') == long_categories
    
    @pytest.mark.gui
    def test_category_select_dialog_duplicate_categories(self):
        """重複カテゴリでのダイアログテスト"""
        duplicate_categories = ["カテゴリ1", "カテゴリ1", "カテゴリ2"]
        dialog = CategorySelectDialog(self.root, duplicate_categories)
        
        assert dialog.categories == duplicate_categories
        assert dialog.combobox.cget('values') == duplicate_categories


class TestBulkCategoryDialog:
    """一括カテゴリ変更ダイアログのテスト（拡張版）"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        try:
            self.root = tk.Tk()
            self.root.withdraw()  # ウィンドウを非表示に
        except Exception:
            pytest.skip("Tkinterが利用できないためスキップ")
        self.tags = ["tag1", "tag2", "tag3"]
    
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        if hasattr(self, 'root'):
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass
    
    @pytest.mark.gui
    def test_bulk_category_dialog_initialization(self):
        """一括カテゴリ変更ダイアログの初期化テスト"""
        dialog = BulkCategoryDialog(self.root, self.tags)
        
        assert dialog.selected_tags == self.tags
        assert dialog.result is None
        assert dialog.dialog.title() == "カテゴリ一括変更"
    
    @pytest.mark.gui
    def test_bulk_category_dialog_ui_elements(self):
        """一括カテゴリ変更ダイアログのUI要素テスト"""
        dialog = BulkCategoryDialog(self.root, self.tags)
        
        # ラベルが存在することを確認
        assert hasattr(dialog, 'label')
        assert f"選択中のタグ数: {len(self.tags)}" in dialog.label.cget('text')
        
        # ダイアログウィンドウが存在することを確認
        assert hasattr(dialog, 'dialog')
        assert dialog.dialog.winfo_exists()
    
    @pytest.mark.gui
    def test_bulk_category_dialog_empty_tags(self):
        """空のタグリストでのダイアログテスト"""
        dialog = BulkCategoryDialog(self.root, [])
        
        assert dialog.selected_tags == []
        assert "選択中のタグ数: 0" in dialog.label.cget('text')
    
    @pytest.mark.gui
    def test_bulk_category_dialog_single_tag(self):
        """単一タグでのダイアログテスト"""
        single_tag = ["tag1"]
        dialog = BulkCategoryDialog(self.root, single_tag)
        
        assert dialog.selected_tags == single_tag
        assert "選択中のタグ数: 1" in dialog.label.cget('text')
    
    @pytest.mark.gui
    def test_bulk_category_dialog_many_tags(self):
        """多数のタグでのダイアログテスト"""
        many_tags = [f"tag{i}" for i in range(100)]
        dialog = BulkCategoryDialog(self.root, many_tags)
        
        assert dialog.selected_tags == many_tags
        assert "選択中のタグ数: 100" in dialog.label.cget('text')
    
    @pytest.mark.gui
    def test_bulk_category_dialog_unicode_tags(self):
        """Unicode文字を含むタグでのダイアログテスト"""
        unicode_tags = ["青い髪", "赤い服", "緑の目"]
        dialog = BulkCategoryDialog(self.root, unicode_tags)
        
        assert dialog.selected_tags == unicode_tags
        assert "選択中のタグ数: 3" in dialog.label.cget('text')
    
    @pytest.mark.gui
    def test_bulk_category_dialog_special_characters(self):
        """特殊文字を含むタグでのダイアログテスト"""
        special_tags = ["tag/1", "tag\\2", "tag*3"]
        dialog = BulkCategoryDialog(self.root, special_tags)
        
        assert dialog.selected_tags == special_tags
        assert "選択中のタグ数: 3" in dialog.label.cget('text')
    
    @pytest.mark.gui
    def test_bulk_category_dialog_very_long_tags(self):
        """非常に長いタグ名でのダイアログテスト"""
        long_tags = ["a" * 100, "b" * 200, "c" * 300]
        dialog = BulkCategoryDialog(self.root, long_tags)
        
        assert dialog.selected_tags == long_tags
        assert "選択中のタグ数: 3" in dialog.label.cget('text')
    
    @pytest.mark.gui
    def test_bulk_category_dialog_duplicate_tags(self):
        """重複タグでのダイアログテスト"""
        duplicate_tags = ["tag1", "tag1", "tag2"]
        dialog = BulkCategoryDialog(self.root, duplicate_tags)
        
        assert dialog.selected_tags == duplicate_tags
        assert "選択中のタグ数: 3" in dialog.label.cget('text')
    
    @pytest.mark.gui
    def test_bulk_category_dialog_cancel_action(self):
        """一括カテゴリ変更ダイアログのキャンセルアクションテスト"""
        dialog = BulkCategoryDialog(self.root, self.tags)
        
        # キャンセルボタンをクリック
        dialog.cancel()
        
        assert dialog.result is None
    
    @pytest.mark.gui
    def test_bulk_category_dialog_window_properties(self):
        """一括カテゴリ変更ダイアログのウィンドウプロパティテスト"""
        dialog = BulkCategoryDialog(self.root, self.tags)
        
        # ウィンドウサイズが設定されていることを確認
        assert dialog.dialog.winfo_width() > 0
        assert dialog.dialog.winfo_height() > 0
        
        # リサイズ不可が設定されていることを確認
        assert not dialog.dialog.winfo_resizable()[0]  # 幅のリサイズ不可
        assert not dialog.dialog.winfo_resizable()[1]  # 高さのリサイズ不可


class TestDialogsIntegration:
    """ダイアログ統合テスト"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        try:
            self.root = tk.Tk()
            self.root.withdraw()  # ウィンドウを非表示に
        except Exception:
            pytest.skip("Tkinterが利用できないためスキップ")
    
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        if hasattr(self, 'root'):
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass
    
    @pytest.mark.gui
    def test_multiple_dialogs_creation(self):
        """複数ダイアログの作成テスト"""
        categories = ["カテゴリ1", "カテゴリ2"]
        tags = ["tag1", "tag2"]
        
        # 複数のダイアログを作成
        dialog1 = CategorySelectDialog(self.root, categories)
        dialog2 = BulkCategoryDialog(self.root, tags)
        
        assert dialog1.categories == categories
        assert dialog2.selected_tags == tags
    
    @pytest.mark.gui
    def test_dialog_with_real_categories(self):
        """実際のカテゴリでのダイアログテスト"""
        real_categories = list(category_keywords.keys())
        dialog = CategorySelectDialog(self.root, real_categories)
        
        assert dialog.categories == real_categories
        assert len(dialog.categories) > 0
    
    @pytest.mark.gui
    def test_dialog_memory_cleanup(self):
        """ダイアログのメモリクリーンアップテスト"""
        categories = ["カテゴリ1", "カテゴリ2"]
        
        # ダイアログを作成して即座に破棄
        dialog = CategorySelectDialog(self.root, categories)
        dialog.destroy()
        
        # 新しいダイアログを作成
        dialog2 = CategorySelectDialog(self.root, categories)
        
        assert dialog2.categories == categories
        assert dialog2.result is None 