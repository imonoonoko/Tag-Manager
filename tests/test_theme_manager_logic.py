import pytest
import tempfile
import os
import json
import logging
from modules.theme_manager import get_available_themes_pure, load_theme_settings_pure, save_theme_settings_pure

def test_get_available_themes_pure():
    themes = get_available_themes_pure()
    assert isinstance(themes, list)
    assert "darkly" in themes
    assert len(themes) > 0

def test_load_and_save_theme_settings_pure():
    with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8') as f:
        json.dump({"theme": "testtheme"}, f, ensure_ascii=False)
        fname = f.name
    # 正常読込
    d = load_theme_settings_pure(fname)
    assert d["theme"] == "testtheme"
    os.remove(fname)
    # 存在しないファイル
    assert load_theme_settings_pure("not_exist.json") == {}
    # 保存・再読込
    with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8') as f:
        fname2 = f.name
    assert save_theme_settings_pure(fname2, "abc")
    d2 = load_theme_settings_pure(fname2)
    assert d2["theme"] == "abc"
    os.remove(fname2)
    # 壊れたJSON
    with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8') as f:
        f.write("{invalid json}")
        fname3 = f.name
    assert load_theme_settings_pure(fname3) == {}
    os.remove(fname3)
    # ディレクトリ指定
    with tempfile.TemporaryDirectory() as d:
        assert load_theme_settings_pure(d) == {}

def test_load_theme_settings_pure_logs_error_on_invalid_json(tmp_path, caplog):
    # 壊れたJSON
    file_path = tmp_path / "broken.json"
    file_path.write_text("{invalid json}", encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        d = load_theme_settings_pure(str(file_path))
        assert d == {}
        assert any("ERROR" in r or "失敗" in r for r in caplog.text.splitlines()) 

def test_theme_manager_broken_settings_file(tmp_path, monkeypatch):
    import os, json, shutil
    from modules.theme_manager import ThemeManager, THEME_FILE
    # バックアップ
    if os.path.exists(THEME_FILE):
        shutil.copy2(THEME_FILE, THEME_FILE + ".bak")
    # 壊れたファイルを書き込む
    with open(THEME_FILE, "w", encoding="utf-8") as f:
        f.write("{invalid json")
    tm = ThemeManager()
    assert tm.current_theme == "darkly"
    # 復元
    if os.path.exists(THEME_FILE + ".bak"):
        shutil.move(THEME_FILE + ".bak", THEME_FILE)
    else:
        os.remove(THEME_FILE) 

def test_save_theme_settings_pure_permission_error(monkeypatch, tmp_path):
    """書き込み権限エラー時にFalseが返ることを検証"""
    from modules.theme_manager import save_theme_settings_pure
    def raise_permission_error(*a, **kw):
        raise PermissionError("no permission")
    monkeypatch.setattr("builtins.open", raise_permission_error)
    assert not save_theme_settings_pure(str(tmp_path / "test.json"), "darkly")

def test_save_theme_settings_pure_dir_not_exist(tmp_path):
    """保存先ディレクトリが存在しない場合にFalseが返ることを検証"""
    from modules.theme_manager import save_theme_settings_pure
    not_exist_dir = tmp_path / "not_exist_dir"
    file_path = not_exist_dir / "theme.json"
    assert not save_theme_settings_pure(str(file_path), "darkly")

import logging

def test_theme_manager_save_permission_error(monkeypatch, tmp_path, caplog):
    """ThemeManager.save_theme_settingsでPermissionError時にlogger.errorが出ることを検証"""
    from modules.theme_manager import ThemeManager, THEME_FILE
    tm = ThemeManager()
    def raise_permission_error(*a, **kw):
        raise PermissionError("no permission")
    monkeypatch.setattr("builtins.open", raise_permission_error)
    with caplog.at_level(logging.ERROR):
        tm.save_theme_settings("darkly")
        assert any("エラー" in r or "permission" in r for r in caplog.text.lower().splitlines()) 

def test_load_theme_settings_pure_directory_error(tmp_path):
    """ディレクトリを指定した場合の異常系テスト"""
    from modules.theme_manager import load_theme_settings_pure
    # ディレクトリを指定
    assert load_theme_settings_pure(str(tmp_path)) == {}
    # 存在しないディレクトリ内のファイル
    not_exist_dir = tmp_path / "not_exist_dir"
    file_path = not_exist_dir / "theme.json"
    assert load_theme_settings_pure(str(file_path)) == {}

def test_save_theme_settings_pure_os_error(monkeypatch, tmp_path):
    """OSError発生時の異常系テスト"""
    from modules.theme_manager import save_theme_settings_pure
    def raise_os_error(*a, **kw):
        raise OSError("disk full")
    monkeypatch.setattr("builtins.open", raise_os_error)
    assert not save_theme_settings_pure(str(tmp_path / "test.json"), "darkly")

def test_load_theme_settings_pure_encoding_error(tmp_path):
    """エンコーディングエラー時の異常系テスト"""
    from modules.theme_manager import load_theme_settings_pure
    # バイナリファイルを作成
    file_path = tmp_path / "binary.json"
    file_path.write_bytes(b'\x00\x01\x02\x03')
    assert load_theme_settings_pure(str(file_path)) == {}

def test_save_theme_settings_pure_json_serialization_error(monkeypatch, tmp_path):
    """JSONシリアライゼーションエラー時の異常系テスト"""
    from modules.theme_manager import save_theme_settings_pure
    # シリアライズ不可能なオブジェクトを渡す（実際には文字列のみ受け付けるが、念のため）
    def mock_json_dump(*args, **kwargs):
        raise TypeError("Object of type set is not JSON serializable")
    monkeypatch.setattr("json.dump", mock_json_dump)
    assert not save_theme_settings_pure(str(tmp_path / "test.json"), "darkly")

def test_theme_manager_initialize_with_corrupted_file(tmp_path, monkeypatch):
    """破損したテーマファイルで初期化する場合の異常系テスト"""
    from modules.theme_manager import ThemeManager, THEME_FILE
    import shutil
    
    # バックアップ
    if os.path.exists(THEME_FILE):
        shutil.copy2(THEME_FILE, THEME_FILE + ".bak")
    
    # 破損したファイルを作成
    with open(THEME_FILE, "w", encoding="utf-8") as f:
        f.write("{invalid json content")
    
    # ThemeManager初期化（デフォルトテーマが使用されることを確認）
    tm = ThemeManager()
    assert tm.current_theme == "darkly"
    
    # 復元
    if os.path.exists(THEME_FILE + ".bak"):
        shutil.move(THEME_FILE + ".bak", THEME_FILE)
    else:
        os.remove(THEME_FILE)

def test_get_available_themes_pure_returns_expected_themes():
    """利用可能なテーマ一覧が正しく返されることを検証"""
    from modules.theme_manager import get_available_themes_pure
    themes = get_available_themes_pure()
    assert isinstance(themes, list)
    assert len(themes) > 0
    assert "darkly" in themes
    assert "cosmo" in themes
    # 全て文字列であることを確認
    assert all(isinstance(theme, str) for theme in themes) 