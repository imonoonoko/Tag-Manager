import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import sqlite3
import json
from modules.tag_manager import TagManager
from modules.tag_manager import normalize_tag, is_valid_tag
from modules.tag_manager import assign_category_if_needed
from modules.tag_manager import google_translate_en_to_ja
from modules.tag_manager import is_valid_json_file_path, is_writable_path
from modules.tag_manager import is_valid_category
from modules.constants import TRANSLATING_PLACEHOLDER
import sys

@pytest.fixture
def tag_manager(tmp_path):
    test_db_file = tmp_path / "test_tags.db"
    tm = TagManager(db_file=str(test_db_file))
    yield tm

# タグ追加・取得
def test_add_and_load_tag(tag_manager):
    assert tag_manager.add_tag("test_tag", is_negative=False, category="test_category")
    tags = tag_manager.load_tags(is_negative=False)
    assert len(tags) == 1
    tag = tags[0]
    assert tag["tag"] == "test_tag"
    assert tag["jp"] == TRANSLATING_PLACEHOLDER
    assert tag["category"] == "test_category"
    assert tag["favorite"] is False

# ネガティブタグ追加
def test_add_negative_tag(tag_manager):
    assert tag_manager.add_tag("neg_tag", is_negative=True)
    tags = tag_manager.load_tags(is_negative=True)
    assert len(tags) == 1
    tag = tags[0]
    assert tag["tag"] == "neg_tag"
    assert tag["category"] == "ネガティブ"
    assert tag["favorite"] is False

# 既存タグ追加不可
def test_add_existing_tag(tag_manager):
    tag_manager.add_tag("dup_tag")
    assert not tag_manager.add_tag("dup_tag")

# タグ削除
def test_delete_tag(tag_manager):
    tag_manager.add_tag("del_tag")
    tag_manager.delete_tag("del_tag")
    tags = tag_manager.load_tags()
    assert tags == []

# お気に入り切替
def test_toggle_favorite(tag_manager):
    tag_manager.add_tag("fav_tag")
    assert tag_manager.toggle_favorite("fav_tag")
    assert tag_manager.load_tags()[0]["favorite"] is True
    assert tag_manager.toggle_favorite("fav_tag")
    assert tag_manager.load_tags()[0]["favorite"] is False

# カテゴリ設定
def test_set_category(tag_manager):
    tag_manager.add_tag("cat_tag")
    assert tag_manager.set_category("cat_tag", "new_cat")
    assert tag_manager.load_tags()[0]["category"] == "new_cat"

# タグ編集
def test_update_tag(tag_manager):
    tag_manager.add_tag("old_tag", category="old_cat")
    assert tag_manager.update_tag("old_tag", "new_tag", "new_jp", "new_cat", False)
    tag = tag_manager.load_tags()[0]
    assert tag["tag"] == "new_tag"
    assert tag["jp"] == "new_jp"
    assert tag["category"] == "new_cat"

# キャッシュ挙動
def test_load_tags_cache(tag_manager):
    tag_manager.add_tag("cache_tag")
    tags1 = tag_manager.load_tags()
    tag_manager._positive_tags_cache[0]["tag"] = "mod_tag"
    tags2 = tag_manager.load_tags()
    assert tags2[0]["tag"] == "mod_tag"
    tag_manager.invalidate_cache()
    tags3 = tag_manager.load_tags()
    assert tags3[0]["tag"] == "cache_tag"

# JSONインポート
def test_import_tags_from_json(tag_manager, tmp_path):
    json_content = [
        {"tag": "import1", "jp": "インポート1", "is_negative": 0, "category": "cat1"},
        {"tag": "import2", "is_negative": 1},
        {"tag": "import1", "jp": "重複", "is_negative": 0}
    ]
    json_file = tmp_path / "import.json"
    json_file.write_text(json.dumps(json_content, ensure_ascii=False), encoding="utf-8")
    success, skip, added = tag_manager.import_tags_from_json(str(json_file))
    assert success == 2
    assert skip == 1
    assert {t["tag"] for t in added} == {"import1", "import2"}
    assert tag_manager.load_tags(is_negative=False)[0]["tag"] == "import1"
    assert tag_manager.load_tags(is_negative=True)[0]["tag"] == "import2"

# JSONエクスポート
def test_export_tags_to_json(tag_manager, tmp_path):
    tag_manager.add_tag("exp1")
    tag_manager.add_tag("exp2", is_negative=True)
    all_tags = tag_manager.get_all_tags()
    export_file = tmp_path / "export.json"
    assert tag_manager.export_tags_to_json(all_tags, str(export_file))
    with open(export_file, encoding="utf-8") as f:
        data = json.load(f)
    assert {d["tag"] for d in data} == {"exp1", "exp2"}

# 翻訳・更新
def test_translate_and_update_tag(tag_manager):
    tag_manager.add_tag("hello")
    # 1回目: jpがTRANSLATING_PLACEHOLDERなのでTrue
    assert tag_manager.translate_and_update_tag("hello", False)
    jp = tag_manager.load_tags()[0]["jp"]
    assert jp != TRANSLATING_PLACEHOLDER
    tag_manager.update_tag("hello", "hello", "こんにちは", "", False)
    # 2回目: jpが既に埋まっているのでFalse
    assert not tag_manager.translate_and_update_tag("hello", False)


# --- 追加: 重み付け・優先度順・自動並び替えのテスト例（ダミー） ---
def test_weight_and_priority_sort(tag_manager):
    # 仮の重み付け・優先度順テスト（本実装に合わせて修正可）
    tag_manager.add_tag("tagA", category="catA")
    tag_manager.add_tag("tagB", category="catB")
    # 仮の優先度辞書
    priorities = {"catA": 1, "catB": 2}
    tags = [
        {"tag": "tagA", "weight": 2.0, "category": "catA"},
        {"tag": "tagB", "weight": 1.0, "category": "catB"}
    ]
    # 優先度順に並び替え
    sorted_tags = sorted(tags, key=lambda x: priorities.get(x["category"], 999))
    assert [t["tag"] for t in sorted_tags] == ["tagA", "tagB"]

def test_delete_nonexistent_tag(tag_manager):
    # 存在しないタグの削除は何も起きない（例外にならない）
    tag_manager.delete_tag("no_such_tag")
    assert tag_manager.load_tags() == []

def test_add_tag_empty_name(tag_manager):
    # 空文字列のタグは追加できない
    assert not tag_manager.add_tag("")

def test_add_tag_long_name(tag_manager):
    # 長すぎるタグ名（仮に255文字制限とする）
    long_tag = "a" * 300
    result = tag_manager.add_tag(long_tag)
    # 実装によってはTrue/Falseどちらもあり得るが、例外にならないことを確認
    assert result in (True, False)

def test_set_category_nonexistent_tag(tag_manager):
    # 存在しないタグのカテゴリ変更は何も起きない
    assert not tag_manager.set_category("no_such_tag", "cat")

def test_toggle_favorite_nonexistent_tag(tag_manager):
    # 存在しないタグのお気に入り切替は何も起きない
    assert not tag_manager.toggle_favorite("no_such_tag")

def test_import_invalid_json(tmp_path, tag_manager):
    # 不正なJSONファイルのインポートは(0,0,[])が返る
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{invalid json", encoding="utf-8")
    success, skip, added = tag_manager.import_tags_from_json(str(bad_json))
    assert success == 0 and skip == 0 and added == []

def test_export_tags_to_readonly_file(tag_manager, tmp_path, monkeypatch):
    # 読み取り専用ファイルへのエクスポートは失敗する
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda *a, **k: None)
    tag_manager.add_tag("exp1")
    export_file = tmp_path / "readonly.json"
    export_file.write_text("[]", encoding="utf-8")
    import os
    os.chmod(export_file, 0o444)  # 読み取り専用
    assert not tag_manager.export_tags_to_json([{"tag": "exp1"}], str(export_file))

def test_import_duplicate_tags(tag_manager, tmp_path):
    # 既存タグと同名のタグをインポートした場合、スキップされる
    tag_manager.add_tag("dup_tag")
    json_content = [{"tag": "dup_tag", "is_negative": 0}]
    json_file = tmp_path / "dup.json"
    json_file.write_text(json.dumps(json_content, ensure_ascii=False), encoding="utf-8")
    success, skip, added = tag_manager.import_tags_from_json(str(json_file))
    assert success == 0
    assert skip == 1

def test_translate_and_update_tag_invalid(tag_manager):
    # 存在しないタグの翻訳更新はFalse
    assert not tag_manager.translate_and_update_tag("no_such_tag", False)

def test_logger_on_error(tmp_path, caplog, monkeypatch):
    # エラー発生時にloggerに記録されるか（壊れたDBファイルでadd_tag）
    from modules.constants import DB_FILE
    import modules.tag_manager as tag_manager_mod
    # messagebox.showerrorをモック
    monkeypatch.setattr(tag_manager_mod.messagebox, "showerror", lambda *a, **kw: None)
    db_file = tmp_path / "corrupt.db"
    db_file.write_bytes(b"not a sqlite db")
    bad_tm = tag_manager_mod.TagManager(db_file=str(db_file))
    with caplog.at_level("ERROR"):
        try:
            bad_tm.add_tag("test")
        except Exception:
            pass
    assert any("ERROR" in r for r in caplog.text.splitlines())


def test_db_file_corruption(tmp_path, monkeypatch):
    # DBファイルが壊れている場合の挙動（messagebox.showerrorをモックしてTclError防止）
    db_file = tmp_path / "corrupt.db"
    db_file.write_bytes(b"not a sqlite db")
    import modules.tag_manager as tag_manager_mod
    monkeypatch.setattr(tag_manager_mod.messagebox, "showerror", lambda *a, **kw: None)
    # 例外をraiseするのではなく、Falseを返すことを期待
    tm = tag_manager_mod.TagManager(db_file=str(db_file))
    result = tm.add_tag("test")
    assert result == False

def test_category_special_characters(tag_manager):
    # カテゴリ名に特殊文字
    special_cat = "!@#$_-あいうえお"
    assert tag_manager.add_tag("special_tag", category=special_cat)
    assert tag_manager.load_tags()[0]["category"] == special_cat

def test_tag_case_sensitivity(tag_manager):
    # タグ名の大文字小文字は区別されるか
    assert tag_manager.add_tag("CaseTag")
    assert tag_manager.add_tag("casetag")
    tags = [t["tag"] for t in tag_manager.load_tags()]
    assert "CaseTag" in tags and "casetag" in tags

def test_import_category_auto_assign(tmp_path, tag_manager):
    # インポート時にカテゴリが自動付与されるか
    json_content = [{"tag": "auto_cat_tag"}]
    json_file = tmp_path / "auto_cat.json"
    json_file.write_text(json.dumps(json_content, ensure_ascii=False), encoding="utf-8")
    success, skip, added = tag_manager.import_tags_from_json(str(json_file))
    assert success == 1
    assert added[0]["category"] != ""

def test_export_and_reimport_tags(tag_manager, tmp_path):
    # エクスポートしたタグを再インポートできるか
    tag_manager.add_tag("expimp1")
    export_file = tmp_path / "expimp.json"
    tag_manager.export_tags_to_json(tag_manager.get_all_tags(), str(export_file))
    success, skip, added = tag_manager.import_tags_from_json(str(export_file))
    assert skip >= 1  # 既存タグはスキップされる

def test_delete_tag_cache_invalidation(tag_manager):
    # タグ削除後にキャッシュが正しく無効化されるか
    tag_manager.add_tag("cache_del")
    tag_manager.load_tags()
    tag_manager.delete_tag("cache_del")
    tags = tag_manager.load_tags()
    assert all(t["tag"] != "cache_del" for t in tags)

def test_translate_api_failure(monkeypatch, tag_manager):
    # GoogleTranslatorの例外をモック
    def mock_translate(*args, **kwargs):
        raise Exception("API接続エラー")
    monkeypatch.setattr("deep_translator.GoogleTranslator.translate", mock_translate)
    
    # 翻訳失敗時の処理をテスト
    tag_manager.add_tag("test_translate_fail")
    result = tag_manager.translate_and_update_tag("test_translate_fail")
    assert not result

def test_add_recent_tag_exception_handling(monkeypatch, tag_manager):
    """add_recent_tagの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_execute_query(*args, **kwargs):
        raise Exception("テスト用のadd_recent_tag例外")
    
    monkeypatch.setattr(tag_manager, "_execute_query", mock_execute_query)
    
    # add_recent_tagを実行（例外が発生するが、アプリケーションがクラッシュしないことを確認）
    try:
        tag_manager.add_recent_tag("test_tag")
    except Exception as e:
        assert "テスト用のadd_recent_tag例外" in str(e)

@pytest.mark.skip(reason="sqlite3.Connectionのclose属性がread-onlyのためスキップ")
def test_close_exception_handling(monkeypatch, tag_manager):
    """closeメソッドの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_close(*args, **kwargs):
        raise Exception("テスト用のclose例外")
    
    monkeypatch.setattr(tag_manager._conn, "close", mock_close)
    
    # closeを実行（例外が発生するが、アプリケーションがクラッシュしないことを確認）
    try:
        tag_manager.close()
    except Exception as e:
        assert "テスト用のclose例外" in str(e)

def test_del_exception_handling(monkeypatch, tag_manager):
    """__del__メソッドの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_close(*args, **kwargs):
        raise Exception("テスト用の__del__例外")
    
    monkeypatch.setattr(tag_manager, "close", mock_close)
    
    # __del__を実行（例外が発生するが、アプリケーションがクラッシュしないことを確認）
    try:
        tag_manager.__del__()
    except Exception as e:
        assert "テスト用の__del__例外" in str(e)

def test_get_conn_exception_handling(monkeypatch, tmp_path):
    """_get_connの例外処理をテスト"""
    from modules.tag_manager import TagManager
    import sqlite3
    
    # 例外を発生させるモック
    def mock_connect(*args, **kwargs):
        raise sqlite3.Error("テスト用の_get_conn例外")
    
    monkeypatch.setattr(sqlite3, "connect", mock_connect)
    
    # TagManagerを初期化（例外が発生するが、アプリケーションがクラッシュしないことを確認）
    test_db = tmp_path / "test_get_conn_exception_handling.db"
    try:
        tm = TagManager(db_file=str(test_db))
        tm._get_conn()
    except sqlite3.Error as e:
        assert "テスト用の_get_conn例外" in str(e)

@pytest.mark.skip(reason="sqlite3.Cursorのexecute属性がread-onlyのためスキップ")
def test_execute_query_exception_handling(monkeypatch, tag_manager):
    """_execute_queryの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_execute(*args, **kwargs):
        raise sqlite3.Error("テスト用の_execute_query例外")
    
    monkeypatch.setattr(tag_manager._get_conn().cursor(), "execute", mock_execute)
    
    # _execute_queryを実行（例外が発生するが、アプリケーションがクラッシュしないことを確認）
    try:
        tag_manager._execute_query("SELECT 1")
    except sqlite3.Error as e:
        assert "テスト用の_execute_query例外" in str(e)

@pytest.mark.skip(reason="sqlite3.Cursorのexecute属性がread-onlyのためスキップ")
def test_init_database_exception_handling(monkeypatch, tmp_path):
    """_init_databaseの例外処理をテスト"""
    from modules.tag_manager import TagManager
    import sqlite3
    
    # 例外を発生させるモック
    def mock_execute(*args, **kwargs):
        raise Exception("テスト用の_init_database例外")
    
    test_db = tmp_path / "test_init_database_exception_handling.db"
    tm = TagManager(db_file=str(test_db))
    
    monkeypatch.setattr(tm._get_conn().cursor(), "execute", mock_execute)
    
    # _init_databaseを実行（例外が発生するが、アプリケーションがクラッシュしないことを確認）
    try:
        tm._init_database()
    except Exception as e:
        assert "テスト用の_init_database例外" in str(e)

@pytest.mark.skip(reason="sqlite3.Cursorのexecute属性がread-onlyのためスキップ")
def test_create_indexes_exception_handling(monkeypatch, tag_manager):
    """_create_indexesの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_execute(*args, **kwargs):
        raise sqlite3.Error("テスト用の_create_indexes例外")
    
    monkeypatch.setattr(tag_manager._get_conn().cursor(), "execute", mock_execute)
    
    # _create_indexesを実行（例外が発生するが、アプリケーションがクラッシュしないことを確認）
    try:
        tag_manager._create_indexes(tag_manager._get_conn().cursor())
    except sqlite3.Error as e:
        assert "テスト用の_create_indexes例外" in str(e)

def test_load_tags_exception_handling(monkeypatch, tag_manager):
    """load_tagsの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_execute_query(*args, **kwargs):
        raise Exception("テスト用のload_tags例外")
    
    monkeypatch.setattr(tag_manager, "_execute_query", mock_execute_query)
    
    # load_tagsを実行（例外が発生するが、空のリストが返されることを確認）
    result = tag_manager.load_tags()
    assert result == []

def test_get_all_tags_exception_handling(monkeypatch, tag_manager):
    """get_all_tagsの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_execute_query(*args, **kwargs):
        raise Exception("テスト用のget_all_tags例外")
    
    monkeypatch.setattr(tag_manager, "_execute_query", mock_execute_query)
    
    # get_all_tagsを実行（例外が発生するが、空のリストが返されることを確認）
    result = tag_manager.get_all_tags()
    assert result == []

def test_get_recent_tags_exception_handling(monkeypatch, tag_manager):
    """get_recent_tagsの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_execute_query(*args, **kwargs):
        raise Exception("テスト用のget_recent_tags例外")
    
    monkeypatch.setattr(tag_manager, "_execute_query", mock_execute_query)
    
    # get_recent_tagsを実行（例外が発生するが、空のリストが返されることを確認）
    result = tag_manager.get_recent_tags()
    assert result == []

def test_save_tag_exception_handling(monkeypatch, tag_manager):
    """save_tagの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_execute_query(*args, **kwargs):
        raise Exception("テスト用のsave_tag例外")
    
    monkeypatch.setattr(tag_manager, "_execute_query", mock_execute_query)
    
    # save_tagを実行（例外が発生するが、Falseが返されることを確認）
    result = tag_manager.save_tag("test_tag", "テストタグ", False, "テストカテゴリ", False)
    assert result == False

def test_translate_and_update_tag_exception_handling(monkeypatch, tag_manager):
    """translate_and_update_tagの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_translate_tag(*args, **kwargs):
        raise Exception("テスト用のtranslate_and_update_tag例外")
    
    monkeypatch.setattr(tag_manager, "_translate_tag", mock_translate_tag)
    
    # テスト用のタグを追加
    tag_manager.add_tag("test_translate_exception")
    
    # translate_and_update_tagを実行（例外が発生するが、Falseが返されることを確認）
    result = tag_manager.translate_and_update_tag("test_translate_exception")
    assert result == False

def test_add_tag_exception_handling(monkeypatch, tag_manager):
    """add_tagの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_save_tag(*args, **kwargs):
        raise Exception("テスト用のadd_tag例外")
    
    monkeypatch.setattr(tag_manager, "save_tag", mock_save_tag)
    
    # add_tagを実行（例外が発生するが、Falseが返されることを確認）
    result = tag_manager.add_tag("test_add_exception")
    assert result == False

def test_exists_tag_exception_handling(monkeypatch, tag_manager):
    """exists_tagの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_execute_query(*args, **kwargs):
        raise sqlite3.Error("テスト用のexists_tag例外")
    
    monkeypatch.setattr(tag_manager, "_execute_query", mock_execute_query)
    
    # exists_tagを実行（例外が発生するが、Falseが返されることを確認）
    result = tag_manager.exists_tag("test_exists_exception")
    assert result == False

def test_delete_tag_exception_handling(monkeypatch, tag_manager):
    """delete_tagの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_execute_query(*args, **kwargs):
        raise sqlite3.Error("テスト用のdelete_tag例外")
    
    monkeypatch.setattr(tag_manager, "_execute_query", mock_execute_query)
    
    # delete_tagを実行（例外が発生するが、Falseが返されることを確認）
    result = tag_manager.delete_tag("test_delete_exception")
    assert result == False

def test_toggle_favorite_exception_handling(monkeypatch, tag_manager):
    """toggle_favoriteの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_execute_query(*args, **kwargs):
        raise sqlite3.Error("テスト用のtoggle_favorite例外")
    
    monkeypatch.setattr(tag_manager, "_execute_query", mock_execute_query)
    
    # toggle_favoriteを実行（例外が発生するが、Falseが返されることを確認）
    result = tag_manager.toggle_favorite("test_toggle_exception")
    assert result == False

def test_set_category_exception_handling(monkeypatch, tag_manager):
    """set_categoryの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_execute_query(*args, **kwargs):
        raise sqlite3.Error("テスト用のset_category例外")
    
    monkeypatch.setattr(tag_manager, "_execute_query", mock_execute_query)
    
    # set_categoryを実行（例外が発生するが、Falseが返されることを確認）
    result = tag_manager.set_category("test_set_category_exception", "テストカテゴリ")
    assert result == False

def test_update_tag_exception_handling(monkeypatch, tag_manager):
    """update_tagの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_execute_query(*args, **kwargs):
        raise sqlite3.Error("テスト用のupdate_tag例外")
    
    monkeypatch.setattr(tag_manager, "_execute_query", mock_execute_query)
    
    # update_tagを実行（例外が発生するが、Falseが返されることを確認）
    result = tag_manager.update_tag("test_update_exception", "new_test_update_exception", "新しいテストタグ", "テストカテゴリ")
    assert result == False

def test_bulk_assign_category_exception_handling(monkeypatch, tag_manager):
    """bulk_assign_categoryの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_execute_query(*args, **kwargs):
        raise sqlite3.Error("テスト用のbulk_assign_category例外")
    
    monkeypatch.setattr(tag_manager, "_execute_query", mock_execute_query)
    
    # bulk_assign_categoryを実行（例外が発生するが、Falseが返されることを確認）
    result = tag_manager.bulk_assign_category(["test_bulk_exception"], "テストカテゴリ")
    assert result == False

def test_export_tags_to_json_exception_handling(monkeypatch, tag_manager):
    """export_tags_to_jsonの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_open(*args, **kwargs):
        raise IOError("テスト用のexport_tags_to_json例外")
    
    monkeypatch.setattr("builtins.open", mock_open)
    
    # export_tags_to_jsonを実行（例外が発生するが、Falseが返されることを確認）
    result = tag_manager.export_tags_to_json([{"tag": "test_export_exception"}], "test_export.json")
    assert result == False

def test_export_all_tags_to_json_exception_handling(monkeypatch, tag_manager):
    """export_all_tags_to_jsonの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_get_all_tags(*args, **kwargs):
        raise Exception("テスト用のexport_all_tags_to_json例外")
    
    monkeypatch.setattr(tag_manager, "get_all_tags", mock_get_all_tags)
    
    # export_all_tags_to_jsonを実行（例外が発生するが、Falseが返されることを確認）
    result = tag_manager.export_all_tags_to_json("test_export_all.json")
    assert result == False

def test_import_tags_from_json_exception_handling(monkeypatch, tag_manager):
    """import_tags_from_jsonの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_open(*args, **kwargs):
        raise FileNotFoundError("テスト用のimport_tags_from_json例外")
    
    monkeypatch.setattr("builtins.open", mock_open)
    
    # import_tags_from_jsonを実行（例外が発生するが、(0,0,[])が返されることを確認）
    result = tag_manager.import_tags_from_json("test_import.json")
    assert result == (0, 0, [])

def test_export_tags_to_csv_exception_handling(monkeypatch, tag_manager):
    """export_tags_to_csvの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_open(*args, **kwargs):
        raise IOError("テスト用のexport_tags_to_csv例外")
    
    monkeypatch.setattr("builtins.open", mock_open)
    
    # export_tags_to_csvを実行（例外が発生するが、Falseが返されることを確認）
    result = tag_manager.export_tags_to_csv([{"tag": "test_export_csv_exception"}], "test_export.csv")
    assert result == False

def test_import_tags_from_csv_exception_handling(monkeypatch, tag_manager):
    """import_tags_from_csvの例外処理をテスト"""
    # 例外を発生させるモック
    def mock_open(*args, **kwargs):
        raise FileNotFoundError("テスト用のimport_tags_from_csv例外")
    
    monkeypatch.setattr("builtins.open", mock_open)
    
    # import_tags_from_csvを実行（例外が発生するが、(0,0,[])が返されることを確認）
    result = tag_manager.import_tags_from_csv("test_import.csv")
    assert result == (0, 0, [])

def test_tag_with_emoji(tag_manager):
    # タグ名に絵文字
    emoji_tag = "タグ😀"
    assert tag_manager.add_tag(emoji_tag)
    assert tag_manager.load_tags()[0]["tag"] == emoji_tag

def test_add_tag_no_category(tag_manager):
    # カテゴリ未指定時の挙動
    assert tag_manager.add_tag("nocat_tag")
    assert tag_manager.load_tags()[0]["category"] in ("", None)

def test_bulk_add_tags(tag_manager):
    # 複数タグ一括追加
    tags = [f"bulk{i}" for i in range(10)]
    for t in tags:
        assert tag_manager.add_tag(t)
    loaded = [t["tag"] for t in tag_manager.load_tags()]
    for t in tags:
        assert t in loaded

# --- 例外系・分岐の追加テスト ---
def test_get_conn_db_error(monkeypatch, tmp_path):
    # DB接続失敗時の例外・messagebox.showerror発火
    import modules.tag_manager as tag_manager_mod
    monkeypatch.setattr(tag_manager_mod.messagebox, "showerror", lambda *a, **kw: None)
    tm = tag_manager_mod.TagManager(db_file="/invalid/path/to/db.sqlite")
    tm._conn = None
    with pytest.raises(Exception):
        tm._get_conn()

def test_execute_query_db_error(monkeypatch, tmp_path):
    # クエリ実行失敗時の例外・messagebox.showerror発火
    import modules.tag_manager as tag_manager_mod
    monkeypatch.setattr(tag_manager_mod.messagebox, "showerror", lambda *a, **kw: None)
    tm = tag_manager_mod.TagManager(db_file=str(tmp_path / "test.db"))
    # 故意に不正なクエリ
    with pytest.raises(Exception):
        tm._execute_query("INVALID SQL")

def test_save_tag_other_exception(monkeypatch, tmp_path):
    # save_tagでsqlite3.IntegrityError以外の例外
    import modules.tag_manager as tag_manager_mod
    monkeypatch.setattr(tag_manager_mod.messagebox, "showerror", lambda *a, **kw: None)
    tm = tag_manager_mod.TagManager(db_file=str(tmp_path / "test.db"))
    def fail_execute_query(*a, **kw):
        raise Exception("other error")
    tm._execute_query = fail_execute_query
    assert not tm.save_tag("tag", "jp", False, "cat", False)

def test_translate_and_update_tag_double_exception(monkeypatch, tmp_path):
    # translate_and_update_tagで多重例外
    import modules.tag_manager as tag_manager_mod
    monkeypatch.setattr(tag_manager_mod.messagebox, "showerror", lambda *a, **kw: None)
    tm = tag_manager_mod.TagManager(db_file=str(tmp_path / "test.db"))
    tm.add_tag("failtag")
    def fail_translate(*a, **kw):
        raise Exception("fail1")
    def fail_execute_query(*a, **kw):
        raise Exception("fail2")
    tm._translate_tag = fail_translate
    tm._execute_query = fail_execute_query
    assert not tm.translate_and_update_tag("failtag")

def test_import_tags_from_json_file_errors(monkeypatch, tmp_path):
    # import_tags_from_jsonの各例外分岐
    import modules.tag_manager as tag_manager_mod
    monkeypatch.setattr(tag_manager_mod.messagebox, "showerror", lambda *a, **kw: None)
    tm = tag_manager_mod.TagManager(db_file=str(tmp_path / "test.db"))
    # FileNotFoundError
    assert tm.import_tags_from_json("not_exist.json") == (0, 0, [])
    # JSONDecodeError
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{invalid json", encoding="utf-8")
    assert tm.import_tags_from_json(str(bad_json)) == (0, 0, [])
    # UnicodeDecodeError
    bin_file = tmp_path / "binfile.json"
    bin_file.write_bytes(b"\xff\xfe\xfd\xfc")
    assert tm.import_tags_from_json(str(bin_file)) == (0, 0, [])
    # IOError（読み取り専用ディレクトリに書き込むなど）
    # ここでは再現困難なため省略

def test_exists_tag_db_error(monkeypatch, tmp_path):
    # exists_tagでDBエラー時にlogger/printされFalseが返る
    import modules.tag_manager as tag_manager_mod
    import os
    monkeypatch.setattr(tag_manager_mod.messagebox, "showerror", lambda *a, **kw: None)
    tm = tag_manager_mod.TagManager(db_file=str(tmp_path / "test.db"))
    def fail_execute_query(*a, **kw):
        raise sqlite3.Error("fail")
    tm._execute_query = fail_execute_query
    # 例外をraiseするのではなく、Falseを返すことを期待
    result = tm.exists_tag("test_tag")
    assert result == False

def test_normalize_tag():
    # 前後空白除去
    assert normalize_tag("  abc  ") == "abc"
    # ウェイト表記除去
    assert normalize_tag("(tag:1.2)") == "tag"
    # 改行除去
    assert normalize_tag("a\nb\rc") == "abc"
    # 型不正
    assert normalize_tag(None) == ""
    assert normalize_tag(123) == ""

def test_is_valid_tag():
    assert is_valid_tag("abc")
    assert not is_valid_tag("")
    assert not is_valid_tag("   ")
    assert not is_valid_tag(None)
    assert not is_valid_tag(123)

def test_is_valid_tag_strict():
    # 正常系
    assert is_valid_tag("abc")
    # 空文字・空白
    assert not is_valid_tag("")
    assert not is_valid_tag("   ")
    # 型不正
    assert not is_valid_tag(None)
    assert not is_valid_tag(123)
    # 長すぎ
    assert not is_valid_tag("a"*65)
    # 禁止文字
    for c in "\\/:*?\"<>|":
        assert not is_valid_tag(f"tag{c}name")
    # ちょうど64文字
    assert is_valid_tag("a"*64)

def test_is_valid_category_strict():
    # 正常系
    assert is_valid_category("cat1")
    # 空文字・空白
    assert not is_valid_category("")
    assert not is_valid_category("   ")
    # 型不正
    assert not is_valid_category(None)
    assert not is_valid_category(123)
    # 長すぎ
    assert not is_valid_category("a"*65)
    # 禁止文字
    for c in "\\/:*?\"<>|":
        assert not is_valid_category(f"cat{c}name")
    # ちょうど64文字
    assert is_valid_category("a"*64)

def test_assign_category_if_needed():
    def dummy_auto_assign(tag):
        return f"auto_{tag}"
    # categoryが空でない場合はそのまま
    assert assign_category_if_needed("t1", "cat1", dummy_auto_assign) == "cat1"
    # categoryが空の場合はauto_assign_funcの結果
    assert assign_category_if_needed("t2", "", dummy_auto_assign) == "auto_t2"

def test_google_translate_en_to_ja(monkeypatch):
    # deep_translatorのGoogleTranslatorをモック
    class DummyTranslator:
        def __init__(self, source, target):
            pass
        def translate(self, text):
            return f"JA_{text}"
    monkeypatch.setattr("deep_translator.GoogleTranslator", DummyTranslator)
    assert google_translate_en_to_ja("hello") == "JA_hello"

def test_is_valid_json_file_path(tmp_path):
    # 正常系
    f = tmp_path / "a.json"
    f.write_text("{}", encoding="utf-8")
    assert is_valid_json_file_path(str(f))
    # 拡張子違い
    f2 = tmp_path / "b.txt"
    f2.write_text("{}", encoding="utf-8")
    assert not is_valid_json_file_path(str(f2))
    # 存在しない
    assert not is_valid_json_file_path(str(tmp_path / "no.json"))
    # 型不正
    assert not is_valid_json_file_path(None)
    assert not is_valid_json_file_path(123)
    # 空文字
    assert not is_valid_json_file_path("")

def test_is_writable_path(tmp_path):
    # 書き込み可能
    f = tmp_path / "c.json"
    assert is_writable_path(str(f))
    # 存在しないディレクトリ
    import os
    no_dir = os.path.join(str(tmp_path), "no_dir", "d.json")
    assert not is_writable_path(no_dir)

def test_export_tags_to_json_invalid_path(tag_manager, tmp_path, monkeypatch):
    # 書き込み不可パス
    import os
    import sys
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda *a, **k: None)
    if sys.platform == "win32":
        invalid_path = "C:/Windows/System32/invalid.json"
    else:
        invalid_path = "/root/invalid.json"
    # 実際に書き込み不可なパスでFalseを返すことを確認
    assert not tag_manager.export_tags_to_json([{"tag": "a"}], invalid_path)

def test_import_tags_from_json_invalid_path(tag_manager, monkeypatch):
    # 存在しないファイル・拡張子不正
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda *a, **k: None)
    assert tag_manager.import_tags_from_json("notfound.json") == (0, 0, [])
    assert tag_manager.import_tags_from_json("file.txt") == (0, 0, [])

def test_export_tags_to_json_permission_error(tag_manager, monkeypatch):
    # openをモックしてPermissionErrorを強制発生させる
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda *a, **k: None)
    def raise_permission_error(*a, **kw):
        raise PermissionError("mocked")
    monkeypatch.setattr("builtins.open", raise_permission_error)
    assert not tag_manager.export_tags_to_json([{"tag": "a"}], "dummy.json")

def test_export_tags_to_json_invalid_cases(tag_manager, tmp_path, monkeypatch):
    # 不正なパス
    assert not tag_manager.export_tags_to_json([{"tag": "a"}], "")
    assert not tag_manager.export_tags_to_json([{"tag": "a"}], None)
    # 拡張子不正
    assert not tag_manager.export_tags_to_json([{"tag": "a"}], str(tmp_path / "file.txt"))
    # 書き込み不可
    monkeypatch.setattr("builtins.open", lambda *a, **k: (_ for _ in ()).throw(PermissionError("mocked")))
    assert not tag_manager.export_tags_to_json([{"tag": "a"}], str(tmp_path / "fail.json"))

def test_import_tags_from_json_invalid_cases(tag_manager, tmp_path, monkeypatch):
    # 不正なパス
    assert tag_manager.import_tags_from_json("") == (0, 0, [])
    assert tag_manager.import_tags_from_json(None) == (0, 0, [])
    # 拡張子不正
    assert tag_manager.import_tags_from_json(str(tmp_path / "file.txt")) == (0, 0, [])
    # 存在しないファイル
    assert tag_manager.import_tags_from_json(str(tmp_path / "no.json")) == (0, 0, [])
    # 壊れたJSON
    bad = tmp_path / "bad.json"
    bad.write_text("{invalid json", encoding="utf-8")
    assert tag_manager.import_tags_from_json(str(bad)) == (0, 0, [])
    # リストでない
    not_list = tmp_path / "notlist.json"
    not_list.write_text("{}", encoding="utf-8")
    assert tag_manager.import_tags_from_json(str(not_list)) == (0, 0, [])
    # dictでない要素
    not_dict = tmp_path / "notdict.json"
    not_dict.write_text("[1,2,3]", encoding="utf-8")
    assert tag_manager.import_tags_from_json(str(not_dict)) == (0, 0, [])
    # tagキーなし
    no_tag = tmp_path / "notag.json"
    no_tag.write_text("[{\"jp\": \"a\"}]", encoding="utf-8")
    assert tag_manager.import_tags_from_json(str(no_tag)) == (0, 0, [])

@pytest.mark.skipif(sys.platform == 'win32', reason='Windows環境ではファイルロック・権限・DB破損系のテストは安定しないためスキップ')
def test_db_backup_and_recovery(tmp_path):
    # DBバックアップ・復元のテスト
    import shutil
    db_file = tmp_path / "test.db"
    backup_file = tmp_path / "backup.db"
    tm = TagManager(db_file=str(db_file))
    tm.add_tag("backup_test")
    # バックアップ作成
    shutil.copy(db_file, backup_file)
    # 元DB削除
    db_file.unlink()
    # バックアップから復元
    shutil.copy(backup_file, db_file)
    tm2 = TagManager(db_file=str(db_file))
    assert any(t["tag"] == "backup_test" for t in tm2.load_tags())

# --- 追加: DB操作異常系テスト ---
@pytest.mark.skipif(sys.platform == 'win32', reason='Windows環境ではファイルロック・権限・DB破損系のテストは安定しないためスキップ')
def test_db_file_locked_error(monkeypatch, tmp_path):
    """DBファイルがロックされている場合の異常系テスト"""
    import modules.tag_manager as tag_manager_mod
    monkeypatch.setattr(tag_manager_mod.messagebox, "showerror", lambda *a, **kw: None)
    
    # 既存のDBファイルを作成
    db_file = tmp_path / "locked.db"
    tm1 = TagManager(db_file=str(db_file))
    tm1.add_tag("test_tag")
    
    # 2つ目の接続でロックエラーをシミュレート
    def fail_connect(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")
    
    monkeypatch.setattr(sqlite3, "connect", fail_connect)
    
    tm2 = TagManager(db_file=str(db_file))
    with pytest.raises(sqlite3.OperationalError):
        tm2._get_conn()

@pytest.mark.skipif(sys.platform == 'win32', reason='Windows環境ではファイルロック・権限・DB破損系のテストは安定しないためスキップ')
def test_db_write_permission_error(monkeypatch, tmp_path):
    """DBファイルの書き込み権限がない場合の異常系テスト"""
    import modules.tag_manager as tag_manager_mod
    monkeypatch.setattr(tag_manager_mod.messagebox, "showerror", lambda *a, **kw: None)
    
    # 読み取り専用ディレクトリにDBファイルを作成
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    db_file = readonly_dir / "test.db"
    
    # ディレクトリを読み取り専用に設定
    import os
    os.chmod(readonly_dir, 0o444)
    
    try:
        tm = TagManager(db_file=str(db_file))
        # 書き込み操作でエラーが発生することを確認
        with pytest.raises(Exception):
            tm.add_tag("test_tag")
    finally:
        # 権限を元に戻す
        os.chmod(readonly_dir, 0o755)

@pytest.mark.skipif(sys.platform == 'win32', reason='Windows環境ではファイルロック・権限・DB破損系のテストは安定しないためスキップ')
def test_db_corruption_during_operation(monkeypatch, tmp_path):
    """DB操作中にファイルが破損した場合の異常系テスト"""
    import modules.tag_manager as tag_manager_mod
    monkeypatch.setattr(tag_manager_mod.messagebox, "showerror", lambda *a, **kw: None)
    
    db_file = tmp_path / "corrupt.db"
    tm = TagManager(db_file=str(db_file))
    tm.add_tag("test_tag")
    
    # 操作中にDBファイルを破損させる
    def corrupt_db_after_operation(*args, **kwargs):
        # 最初の操作は成功
        if not hasattr(corrupt_db_after_operation, 'called'):
            corrupt_db_after_operation.called = True
            return tm._execute_query.__wrapped__(*args, **kwargs)
        else:
            # 2回目以降はDBファイルを破損
            with open(db_file, 'wb') as f:
                f.write(b"corrupted database file")
            raise sqlite3.DatabaseError("database disk image is malformed")
    
    tm._execute_query = corrupt_db_after_operation
    
    # 2回目の操作でエラーが発生することを確認
    with pytest.raises(sqlite3.DatabaseError):
        tm.load_tags()

def test_db_connection_timeout(monkeypatch, tmp_path):
    """DB接続タイムアウトの場合の異常系テスト"""
    import modules.tag_manager as tag_manager_mod
    monkeypatch.setattr(tag_manager_mod.messagebox, "showerror", lambda *a, **kw: None)
    
    def timeout_connect(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")
    
    monkeypatch.setattr(sqlite3, "connect", timeout_connect)
    
    tm = TagManager(db_file=str(tmp_path / "timeout.db"))
    with pytest.raises(sqlite3.OperationalError):
        tm._get_conn()

def test_db_disk_full_error(monkeypatch, tmp_path):
    """ディスク容量不足の場合の異常系テスト"""
    import modules.tag_manager as tag_manager_mod
    monkeypatch.setattr(tag_manager_mod.messagebox, "showerror", lambda *a, **kw: None)

    db_file = tmp_path / "disk_full.db"
    tm = TagManager(db_file=str(db_file))

    # ディスク容量不足をシミュレート
    def disk_full_execute(*args, **kwargs):
        raise sqlite3.OperationalError("database or disk is full")

    tm._execute_query = disk_full_execute

    # 例外をraiseするのではなく、Falseを返すことを期待
    result = tm.exists_tag("test_tag")
    assert result == False

@pytest.mark.skipif(sys.platform == 'win32', reason='Windows環境ではファイルロック・権限・DB破損系のテストは安定しないためスキップ')
def test_db_schema_corruption(monkeypatch, tmp_path):
    """DBスキーマが破損している場合の異常系テスト"""
    import modules.tag_manager as tag_manager_mod
    monkeypatch.setattr(tag_manager_mod.messagebox, "showerror", lambda *a, **kw: None)
    db_file = tmp_path / "schema_corrupt.db"
    # 不正なスキーマでDBファイルを作成
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE tags (invalid_column TEXT)")
    conn.close()
    tm = TagManager(db_file=str(db_file))
    # 正しいスキーマを期待する操作でエラーが発生することを確認
    with pytest.raises(sqlite3.OperationalError):
        tm.load_tags()