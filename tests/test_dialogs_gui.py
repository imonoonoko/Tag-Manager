import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import tkinter as tk
import ttkbootstrap as tb
from modules.dialogs import CategorySelectDialog, BulkCategoryDialog, get_category_choices, validate_bulk_category_action, safe_validate_bulk_category_action
import logging

# 純粋関数のテスト（GUI環境に依存しない）
def test_get_category_choices():
    """get_category_choices関数のテスト"""
    from modules.constants import category_keywords
    choices = get_category_choices(category_keywords)
    assert isinstance(choices, list)
    assert "未分類" in choices
    assert len(choices) == len(category_keywords) + 1

def test_validate_bulk_category_action():
    """validate_bulk_category_action関数のテスト"""
    # 正常なケース
    assert validate_bulk_category_action("change", "風景") == True
    assert validate_bulk_category_action("remove", "") == True
    
    # 異常なケース
    assert validate_bulk_category_action("change", "") == False

def test_safe_validate_bulk_category_action():
    """safe_validate_bulk_category_action関数のテスト"""
    # 正常なケース
    assert safe_validate_bulk_category_action("change", "風景") == True
    assert safe_validate_bulk_category_action("remove", "") == True
    
    # 異常なケース
    assert safe_validate_bulk_category_action("change", "") == False
    
    # logger付きのテスト
    logger = logging.getLogger(__name__)
    assert safe_validate_bulk_category_action("change", "風景", logger) == True

def test_safe_validate_bulk_category_action_with_logger(caplog):
    """safe_validate_bulk_category_actionのlogger機能テスト"""
    logger = logging.getLogger(__name__)
    
    # 正常なケース（ログは出力されない）
    with caplog.at_level(logging.ERROR):
        result = safe_validate_bulk_category_action("change", "風景", logger)
        assert result == True
        assert len(caplog.records) == 0

@pytest.mark.skip(reason="Tkinter環境依存のためCI等ではスキップ")
def test_category_select_dialog_initialization():
    """CategorySelectDialogの初期化テスト"""
    try:
        root = tb.Window()
    except Exception:
        pytest.skip("Tkinter/ttkbootstrapが利用できないためスキップ")
    
    root.withdraw()
    categories = ["風景", "人物", "動物"]
    dialog = CategorySelectDialog(root, categories)
    
    # 初期状態の確認
    assert dialog.result is None
    assert dialog.categories == categories
    assert dialog.category_var.get() == categories[0]  # 最初のカテゴリが選択されている
    
    dialog.destroy()
    root.destroy()

@pytest.mark.skip(reason="Tkinter環境依存のためCI等ではスキップ")
def test_category_select_dialog_ok():
    """CategorySelectDialogのOKボタンテスト"""
    try:
        root = tb.Window()
    except Exception:
        pytest.skip("Tkinter/ttkbootstrapが利用できないためスキップ")
    
    root.withdraw()
    categories = ["風景", "人物", "動物"]
    dialog = CategorySelectDialog(root, categories)
    
    # カテゴリを変更
    dialog.category_var.set("人物")
    dialog.ok()
    
    # 結果の確認
    assert dialog.result == "人物"
    
    root.destroy()

@pytest.mark.skip(reason="Tkinter環境依存のためCI等ではスキップ")
def test_category_select_dialog_cancel():
    """CategorySelectDialogのキャンセルボタンテスト"""
    try:
        root = tb.Window()
    except Exception:
        pytest.skip("Tkinter/ttkbootstrapが利用できないためスキップ")
    
    root.withdraw()
    categories = ["風景", "人物", "動物"]
    dialog = CategorySelectDialog(root, categories)
    
    # キャンセル
    dialog.cancel()
    
    # 結果の確認
    assert dialog.result is None
    
    root.destroy()

@pytest.mark.skip(reason="Tkinter環境依存のためCI等ではスキップ")
def test_bulk_category_dialog_initialization():
    """BulkCategoryDialogの初期化テスト"""
    try:
        root = tb.Window()
    except Exception:
        pytest.skip("Tkinter/ttkbootstrapが利用できないためスキップ")
    
    root.withdraw()
    tags = ["tag1", "tag2", "tag3"]
    dialog = BulkCategoryDialog(root, tags)
    
    # 初期状態の確認
    assert dialog.result is None
    assert dialog.selected_tags == tags
    assert dialog.action_var.get() == "change"  # デフォルトは"change"
    assert dialog.combobox.cget("state") == "normal"  # 変更モードでは有効
    
    dialog.destroy()
    root.destroy()

@pytest.mark.skip(reason="Tkinter環境依存のためCI等ではスキップ")
def test_bulk_category_dialog_action_change():
    """BulkCategoryDialogのアクション変更テスト"""
    try:
        root = tb.Window()
    except Exception:
        pytest.skip("Tkinter/ttkbootstrapが利用できないためスキップ")
    
    root.withdraw()
    tags = ["tag1", "tag2"]
    dialog = BulkCategoryDialog(root, tags)
    
    # アクションを"remove"に変更
    dialog.action_var.set("remove")
    
    # コンボボックスが無効化され、"未分類"が設定されることを確認
    assert dialog.combobox.cget("state") == "disabled"
    assert dialog.category_var.get() == "未分類"
    
    dialog.destroy()
    root.destroy()

@pytest.mark.skip(reason="Tkinter環境依存のためCI等ではスキップ")
def test_bulk_category_dialog_ok_change():
    """BulkCategoryDialogのOKボタン（変更モード）テスト"""
    try:
        root = tb.Window()
    except Exception:
        pytest.skip("Tkinter/ttkbootstrapが利用できないためスキップ")
    
    root.withdraw()
    tags = ["tag1", "tag2"]
    dialog = BulkCategoryDialog(root, tags)
    
    # カテゴリを設定
    dialog.category_var.set("風景")
    dialog.ok()
    
    # 結果の確認
    assert dialog.result == {"action": "change", "to_category": "風景"}
    
    root.destroy()

@pytest.mark.skip(reason="Tkinter環境依存のためCI等ではスキップ")
def test_bulk_category_dialog_ok_remove():
    """BulkCategoryDialogのOKボタン（削除モード）テスト"""
    try:
        root = tb.Window()
    except Exception:
        pytest.skip("Tkinter/ttkbootstrapが利用できないためスキップ")
    
    root.withdraw()
    tags = ["tag1", "tag2"]
    dialog = BulkCategoryDialog(root, tags)
    
    # アクションを"remove"に設定
    dialog.action_var.set("remove")
    dialog.ok()
    
    # 結果の確認（削除モードでは常に"未分類"になる）
    assert dialog.result == {"action": "remove", "to_category": "未分類"}
    
    root.destroy()

@pytest.mark.skip(reason="Tkinter環境依存のためCI等ではスキップ")
def test_bulk_category_dialog_ok_validation_error(monkeypatch):
    """BulkCategoryDialogのOKボタン（バリデーションエラー）テスト"""
    try:
        root = tb.Window()
    except Exception:
        pytest.skip("Tkinter/ttkbootstrapが利用できないためスキップ")
    
    root.withdraw()
    tags = ["tag1", "tag2"]
    dialog = BulkCategoryDialog(root, tags)
    
    # カテゴリを空に設定（バリデーションエラー）
    dialog.category_var.set("")
    
    # messagebox.showerrorをモック
    called = []
    def mock_showerror(title, message, parent=None):
        called.append((title, message))
    
    monkeypatch.setattr("tkinter.messagebox.showerror", mock_showerror)
    
    dialog.ok()
    
    # エラーメッセージが表示され、結果が設定されないことを確認
    assert len(called) == 1
    assert called[0][0] == "エラー"
    assert "カテゴリ名を入力してください" in called[0][1]
    assert dialog.result is None  # 結果は設定されない
    
    root.destroy()

@pytest.mark.skip(reason="Tkinter環境依存のためCI等ではスキップ")
def test_bulk_category_dialog_cancel():
    """BulkCategoryDialogのキャンセルボタンテスト"""
    try:
        root = tb.Window()
    except Exception:
        pytest.skip("Tkinter/ttkbootstrapが利用できないためスキップ")
    
    root.withdraw()
    tags = ["tag1", "tag2"]
    dialog = BulkCategoryDialog(root, tags)
    
    # キャンセル
    dialog.cancel()
    
    # 結果の確認
    assert dialog.result is None
    
    root.destroy()

@pytest.mark.skip(reason="Tkinter環境依存のためCI等ではスキップ")
def test_category_select_dialog_result_cancel():
    """CategorySelectDialogのキャンセル結果テスト（既存テストの改善版）"""
    try:
        root = tb.Window()
    except Exception:
        pytest.skip("Tkinter/ttkbootstrapが利用できないためスキップ")
    
    root.withdraw()
    dialog = CategorySelectDialog(root, ["A", "B"])
    dialog.cancel()
    assert dialog.result is None
    root.destroy()

@pytest.mark.skip(reason="Tkinter環境依存のためCI等ではスキップ")
def test_bulk_category_dialog_result_cancel():
    """BulkCategoryDialogのキャンセル結果テスト（既存テストの改善版）"""
    try:
        root = tb.Window()
    except Exception:
        pytest.skip("Tkinter/ttkbootstrapが利用できないためスキップ")
    
    root.withdraw()
    dialog = BulkCategoryDialog(root, ["tag1", "tag2"])
    dialog.cancel()
    assert dialog.result is None
    root.destroy() 