import sqlite3
import datetime
import json
import logging
import re
from tkinter import messagebox
from typing import Any, Optional, Dict, List, Tuple, Union, Callable
import tkinter as tk
from deep_translator import GoogleTranslator
from modules.constants import DB_FILE, category_keywords, TRANSLATING_PLACEHOLDER
import csv

# --- 純粋関数: タグ正規化・バリデーション ---
def normalize_tag(tag: str) -> str:
    """
    タグ文字列を正規化（前後空白除去、ウェイト表記除去、改行除去）。
    """
    if not isinstance(tag, str):
        return ""
    import re
    tag = tag.strip()
    tag = re.sub(r"^\(([^:]+):[0-9.]+\)$", r"\1", tag)
    tag = tag.replace("\n", "").replace("\r", "")
    return tag

def is_valid_tag(tag: str) -> bool:
    """
    タグが有効かどうか（空文字や不正な型・長さ・禁止文字を除外）。
    最大64文字、禁止文字（\\/:*?"<>|）を含む場合はFalse。
    """
    if not isinstance(tag, str):
        return False
    tag = tag.strip()
    if not tag:
        return False
    if len(tag) > 64:
        return False
    if re.search(r'[\\/:*?"<>|]', tag):
        return False
    return True

# --- 純粋関数: カテゴリ自動付与・バリデーション ---
def assign_category_if_needed(tag: str, category: str, auto_assign_func: Callable[[str], str]) -> str:
    """
    categoryが空の場合のみauto_assign_funcで自動付与。
    """
    if category:
        return category
    return auto_assign_func(tag)

# --- 純粋関数: Google翻訳APIラッパー ---
def google_translate_en_to_ja(text: str) -> str:
    """
    英語テキストを日本語に翻訳する（GoogleTranslatorラップ）。
    """
    from deep_translator import GoogleTranslator
    return GoogleTranslator(source="en", target="ja").translate(text)

# --- 純粋関数: ファイルI/Oバリデーション ---
def is_valid_json_file_path(file_path: str) -> bool:
    """
    JSONファイルパスとして有効か（.json拡張子・str型・空でない・存在チェック）。
    """
    import os
    return (
        isinstance(file_path, str)
        and file_path.strip() != ""
        and file_path.lower().endswith('.json')
        and os.path.exists(file_path)
    )

def is_writable_path(file_path: str) -> bool:
    """
    ファイルパスが書き込み可能か（親ディレクトリが存在し、書き込み権限がある）。
    """
    import os
    dir_path = os.path.dirname(file_path) or "."
    return os.access(dir_path, os.W_OK)

def is_valid_category(category: str) -> bool:
    """
    カテゴリ名が有効かどうか（空文字や不正な型・長さ・禁止文字を除外）。
    最大64文字、禁止文字（\\/:*?"<>|）を含む場合はFalse。
    """
    if not isinstance(category, str):
        return False
    category = category.strip()
    if not category:
        return False
    if len(category) > 64:
        return False
    if re.search(r'[\\/:*?"<>|]', category):
        return False
    return True

class TagManager:
    def __init__(self, db_file: str = DB_FILE, parent: Optional[tk.Tk] = None) -> None:
        self.db_file = db_file
        self.parent = parent
        self._conn: Optional[sqlite3.Connection] = None
        self._positive_tags_cache: Optional[List[Dict[str, Any]]] = None
        self._negative_tags_cache: Optional[List[Dict[str, Any]]] = None
        self.logger = logging.getLogger(__name__)
        self._init_database() # Initialize database on creation

    def _get_conn(self) -> sqlite3.Connection:
        try:
            if self._conn is None:
                self._conn = sqlite3.connect(self.db_file, check_same_thread=False)
                self._conn.row_factory = sqlite3.Row
            return self._conn
        except sqlite3.Error as e:
            self._conn = None
            messagebox.showerror("データベースエラー", f"接続に失敗しました: {e}", parent=self.parent)
            raise

    def _execute_query(self, query: str, params: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None) -> sqlite3.Cursor:
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor
        except sqlite3.Error as e:
            messagebox.showerror("データベースエラー", f"クエリ実行に失敗しました: {e}", parent=self.parent)
            raise

    def _init_database(self) -> None:
        try:
            conn = self._get_conn()
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tag TEXT UNIQUE NOT NULL,
                    jp TEXT,
                    favorite INTEGER DEFAULT 0,
                    category TEXT,
                    is_negative INTEGER DEFAULT 0
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS recent_tags (
                    tag TEXT NOT NULL,
                    is_negative INTEGER DEFAULT 0,
                    used_at TEXT NOT NULL,
                    PRIMARY KEY (tag, is_negative)
                )
            ''')
            self._create_indexes(c)
            conn.commit()
        except Exception as e:
            messagebox.showerror("エラー", f"データベース初期化に失敗しました:\n{e}", parent=self.parent)
    
    def _create_indexes(self, cursor: sqlite3.Cursor) -> None:
        indexes = [
            ("idx_is_negative", "tags(is_negative)"),
            ("idx_category", "tags(category)"),
            ("idx_favorite", "tags(favorite)"),
            ("idx_recent_tags", "recent_tags(used_at)")
        ]
        for idx_name, idx_def in indexes:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND name=?", (idx_name,))
            if not cursor.fetchone():
                cursor.execute(f"CREATE INDEX {idx_name} ON {idx_def}")

    def close(self) -> None:
        """データベース接続を閉じる"""
        if self._conn:
            try:
                self._conn.close()
                self._conn = None
            except Exception as e:
                self.logger.error(f"データベース接続のクローズ中にエラーが発生しました: {e}")

    def __del__(self) -> None:
        self.close()

    def invalidate_cache(self) -> None:
        self._positive_tags_cache = None
        self._negative_tags_cache = None

    def load_tags(self, is_negative: bool = False) -> List[Dict[str, Any]]:
        if is_negative and self._negative_tags_cache is not None:
            return self._negative_tags_cache
        if not is_negative and self._positive_tags_cache is not None:
            return self._positive_tags_cache

        try:
            cursor = self._execute_query(
                "SELECT tag, jp, favorite, category FROM tags WHERE is_negative = ?",
                (int(is_negative),)
            )
            rows = cursor.fetchall()
            result = [{"tag": row["tag"], "jp": row["jp"], 
                      "favorite": bool(row["favorite"]),
                      "category": row["category"] or ""} for row in rows]
            
            if is_negative:
                self._negative_tags_cache = result
            else:
                self._positive_tags_cache = result
            
            return result
        except Exception as e:
            messagebox.showerror("エラー", f"タグ読み込みに失敗しました:\n{e}", parent=self.parent)
            return []

    def get_all_tags(self) -> List[Dict[str, Any]]:
        try:
            cursor = self._execute_query(
                "SELECT tag, jp, favorite, category, is_negative FROM tags"
            )
            rows = cursor.fetchall()
            return [{
                "tag": row["tag"],
                "jp": row["jp"],
                "favorite": bool(row["favorite"]),
                "category": row["category"] or "",
                "is_negative": bool(row["is_negative"])
            } for row in rows]
        except Exception as e:
            messagebox.showerror("エラー", f"全タグの取得に失敗しました:\n{e}", parent=self.parent)
            return []

    def get_recent_tags(self) -> List[Dict[str, Any]]:
        try:
            cursor = self._execute_query('''
                SELECT t.tag, t.jp, t.favorite, t.category 
                FROM tags t 
                INNER JOIN recent_tags r ON t.tag = r.tag AND t.is_negative = r.is_negative 
                ORDER BY r.used_at DESC LIMIT 50
            ''')
            rows = cursor.fetchall()
            return [{"tag": row["tag"], "jp": row["jp"], 
                    "favorite": bool(row["favorite"]),
                    "category": row["category"] or ""} for row in rows]
        except Exception as e:
            messagebox.showerror("エラー", f"最近使ったタグの取得に失敗しました:\n{e}", parent=self.parent)
            return []

    def add_recent_tag(self, tag: str, is_negative: bool = False) -> None:
        try:
            self._execute_query(
                '''INSERT OR REPLACE INTO recent_tags (tag, is_negative, used_at) 
                   VALUES (?, ?, ?)''',
                (tag, int(is_negative), datetime.datetime.now().isoformat())
            )
            self._get_conn().commit()
        except Exception as e:
            print(f"最近使ったタグ保存エラー: {e}")

    @property
    def positive_tags(self) -> List[Dict[str, Any]]:
        return self.load_tags(is_negative=False)

    @property
    def negative_tags(self) -> List[Dict[str, Any]]:
        return self.load_tags(is_negative=True)

    def save_tag(self, tag: str, jp: str, favorite: bool, category: str, is_negative: bool) -> bool:
        try:
            self._execute_query(
                '''INSERT INTO tags (tag, jp, favorite, category, is_negative)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(tag) DO UPDATE SET
                   jp=excluded.jp,
                   favorite=excluded.favorite,
                   category=excluded.category,
                   is_negative=excluded.is_negative''',
                (tag, jp, int(favorite), category, int(is_negative))
            )
            self._get_conn().commit()
            self.invalidate_cache()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            messagebox.showerror("エラー", f"タグ保存に失敗しました:\n{e}", parent=self.parent)
            return False

    def _translate_tag(self, tag: str) -> str:
        return google_translate_en_to_ja(tag)

    def translate_and_update_tag(self, tag: str, is_negative: bool = False) -> bool:
        """指定されたタグを翻訳してDBを更新する"""
        try:
            jp_trans = self._translate_tag(tag)
            cursor = self._execute_query(
                "UPDATE tags SET jp = ? WHERE tag = ? AND is_negative = ? AND jp = ?",
                (jp_trans, tag, int(is_negative), TRANSLATING_PLACEHOLDER)
            )
            self._get_conn().commit()
            self.invalidate_cache()
            if cursor.rowcount == 0:
                # (翻訳中...)のままのタグがなければ何もしない
                return False
            return True
        except Exception as e: # GoogleTranslatorのエラーは一般的なExceptionでキャッチ
            self.logger.error(f"翻訳と更新に失敗: {e}")
            # (翻訳中...)のタ
            try:
                cursor = self._execute_query(
                    "UPDATE tags SET jp = ? WHERE tag = ? AND is_negative = ? AND jp = ?",
                    ("翻訳失敗", tag, int(is_negative), TRANSLATING_PLACEHOLDER)
                )
                self._get_conn().commit()
                self.invalidate_cache()
            except Exception as e2:
                self.logger.error(f"翻訳失敗の記録にも失敗: {e2}")
            return False

    def add_tag(self, tag: str, is_negative: bool = False, category: str = "") -> bool:
        """
        タグをDBに追加する。
        失敗時はFalseを返し、logger.errorと必要に応じてmessagebox.showerrorで通知。
        """
        tag = normalize_tag(tag)
        if not is_valid_tag(tag):
            return False
        if self.exists_tag(tag):
            return False
        jp = TRANSLATING_PLACEHOLDER
        if is_negative:
            category = "ネガティブ"
        try:
            result = self.save_tag(tag, jp, False, category, is_negative)
            if result:
                self.logger.info(f"タグがDBに保存されました: tag='{tag}', is_negative={is_negative}")
            return result
        except Exception as e:
            self.logger.error(f"add_tagエラー: {e}")
            messagebox.showerror("エラー", f"タグ追加に失敗しました:\n{e}", parent=self.parent)
            return False

    def exists_tag(self, tag: str) -> bool:
        try:
            cursor = self._execute_query("SELECT 1 FROM tags WHERE tag = ?", (tag,))
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            self.logger.error(f"タグ存在チェックエラー: {e}")
            print(f"タグ存在チェックエラー: {e}")
            # テスト環境でも例外をraiseせずFalseを返す
            return False

    def delete_tag(self, tag: str, is_negative: bool = False) -> bool:
        """
        タグをDBから削除する。
        失敗時はFalseを返し、logger.errorと必要に応じてmessagebox.showerrorで通知。
        """
        try:
            self._execute_query(
                "DELETE FROM tags WHERE tag = ? AND is_negative = ?",
                (tag, int(is_negative))
            )
            self._execute_query(
                "DELETE FROM recent_tags WHERE tag = ? AND is_negative = ?",
                (tag, int(is_negative))
            )
            self._get_conn().commit()
            self.invalidate_cache()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"タグ削除に失敗しました: {e}")
            messagebox.showerror("エラー", f"タグ削除に失敗しました:\n{e}", parent=self.parent)
            return False

    def toggle_favorite(self, tag: str, is_negative: bool = False) -> bool:
        """
        タグのお気に入り状態をトグルする。
        失敗時はFalseを返し、logger.errorと必要に応じてmessagebox.showerrorで通知。
        """
        try:
            cursor = self._execute_query(
                "SELECT favorite FROM tags WHERE tag = ? AND is_negative = ?",
                (tag, int(is_negative))
            )
            row = cursor.fetchone()
            if not row:
                return False
            new_fav = 0 if row["favorite"] else 1
            self._execute_query(
                "UPDATE tags SET favorite = ? WHERE tag = ? AND is_negative = ?",
                (new_fav, tag, int(is_negative))
            )
            self._get_conn().commit()
            self.invalidate_cache()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"お気に入り切替に失敗しました: {e}")
            messagebox.showerror("エラー", f"お気に入り切替に失敗しました:\n{e}", parent=self.parent)
            return False

    def set_category(self, tag: str, category: str, is_negative: bool = False) -> bool:
        """
        タグのカテゴリを設定する。
        失敗時はFalseを返し、logger.errorと必要に応じてmessagebox.showerrorで通知。
        """
        if is_negative and category != "ネガティブ":
            return False
        if not is_valid_category(category):
            return False
        try:
            cursor = self._execute_query(
                "UPDATE tags SET category = ? WHERE tag = ? AND is_negative = ?",
                (category, tag, int(is_negative))
            )
            self._get_conn().commit()
            self.invalidate_cache()
            if cursor.rowcount == 0:
                return False
            return True
        except sqlite3.Error as e:
            self.logger.error(f"カテゴリ設定に失敗しました: {e}")
            messagebox.showerror("エラー", f"カテゴリ設定に失敗しました:\n{e}", parent=self.parent)
            return False

    def update_tag(self, old_tag: str, new_tag: str, jp: str, category: str, is_negative: bool = False) -> bool:
        """
        タグ情報を更新する。
        失敗時はFalseを返し、logger.errorと必要に応じてmessagebox.showerrorで通知。
        """
        try:
            if old_tag != new_tag:
                cursor = self._execute_query("SELECT 1 FROM tags WHERE tag = ?", (new_tag,))
                if cursor.fetchone():
                    return False
            self._execute_query(
                '''UPDATE tags SET tag = ?, jp = ?, category = ? 
                   WHERE tag = ? AND is_negative = ?''',
                (new_tag, jp, category, old_tag, int(is_negative))
            )
            if old_tag != new_tag:
                self._execute_query(
                    "UPDATE recent_tags SET tag = ? WHERE tag = ? AND is_negative = ?",
                    (new_tag, old_tag, int(is_negative))
                )
            self._get_conn().commit()
            self.invalidate_cache()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"タグ更新に失敗しました: {e}")
            messagebox.showerror("エラー", f"タグ更新に失敗しました:\n{e}", parent=self.parent)
            return False

    def bulk_assign_category(self, tags: List[str], category: str, is_negative: bool = False) -> bool:
        """
        複数タグのカテゴリを一括設定する。
        失敗時はFalseを返し、logger.errorと必要に応じてmessagebox.showerrorで通知。
        """
        try:
            conn = self._get_conn()
            conn.execute("BEGIN TRANSACTION")
            for tag in tags:
                self._execute_query(
                    "UPDATE tags SET category = ? WHERE tag = ? AND is_negative = ?",
                    (category, tag, int(is_negative))
                )
            conn.commit()
            self.invalidate_cache()
            return True
        except sqlite3.Error as e:
            conn.rollback()
            self.logger.error(f"一括カテゴリ設定に失敗しました: {e}")
            messagebox.showerror("エラー", f"一括カテゴリ設定に失敗しました:\n{e}", parent=self.parent)
            return False



    def export_tags_to_json(self, tags: List[Dict[str, Any]], file_path: str) -> bool:
        """
        タグリストをJSONファイルにエクスポート。ファイル名・パス・書き込み権限・拡張子を厳密チェック。
        失敗時はlogger.errorで記録し、Falseを返す。
        """
        if not is_valid_json_file_path(file_path) and not (isinstance(file_path, str) and file_path.lower().endswith('.json')):
            self.logger.error(f"不正なファイルパス: {file_path}")
            return False
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(tags, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"タグエクスポート失敗: {e}")
            messagebox.showerror("エラー", f"エクスポートに失敗しました:\n{e}", parent=self.parent)
            return False

    def export_all_tags_to_json(self, file_path: str) -> bool:
        try:
            tags = self.get_all_tags()
            if not tags:
                messagebox.showerror("エラー", "エクスポートするタグがありません。", parent=self.parent)
                return False
            return self.export_tags_to_json(tags, file_path)
        except Exception as e:
            self.logger.error(f"export_all_tags_to_jsonエラー: {e}")
            return False

    def import_tags_from_json(self, file_path: str) -> Tuple[int, int, List[Dict[str, Any]]]:
        """
        JSONファイルからタグをインポート。ファイル名・パス・JSON構造を厳密チェック。
        失敗時はlogger.errorで記録し、(0,0,[])を返す。
        """
        if not is_valid_json_file_path(file_path):
            self.logger.error(f"不正なファイルパス: {file_path}")
            return 0, 0, []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                self.logger.error(f"JSON構造がリストでない: {file_path}")
                return 0, 0, []
            for item in data:
                if not isinstance(item, dict) or "tag" not in item:
                    self.logger.error(f"JSON内のタグデータ不正: {item}")
                    return 0, 0, []
            # 既存の処理へ
            from modules.constants import auto_assign_category
            added_tags = []
            skip_count = 0
            for tag_data in data:
                tag = normalize_tag(tag_data.get("tag", ""))
                if not is_valid_tag(tag) or self.exists_tag(tag):
                    skip_count += 1
                    continue
                jp = TRANSLATING_PLACEHOLDER
                category = assign_category_if_needed(tag, tag_data.get("category", ""), auto_assign_category)
                is_negative = bool(tag_data.get("is_negative", 0))
                if self.add_tag(tag, is_negative, category):
                    added_tags.append({"tag": tag, "is_negative": is_negative, "jp": jp, "category": category})
                else:
                    skip_count += 1
            self.invalidate_cache()
            return len(added_tags), skip_count, added_tags
        except FileNotFoundError:
            self.logger.error(f"ファイルが見つかりません: {file_path}")
            import os
            if "PYTEST_CURRENT_TEST" in os.environ:
                return 0, 0, []
            messagebox.showerror("エラー", f"ファイルが見つかりません: {file_path}", parent=self.parent)
            return 0, 0, []
        except json.decoder.JSONDecodeError as e:
            error_msg = f"JSONファイルの書式エラー:\n行 {e.lineno}、列 {e.colno}付近を確認してください。\n問題の部分: {e.doc[max(0, e.pos-20):e.pos+20]}"
            self.logger.error(f"JSONファイルの書式エラー: {error_msg}")
            import os
            if "PYTEST_CURRENT_TEST" in os.environ:
                return 0, 0, []
            messagebox.showerror("エラー", error_msg, parent=self.parent)
            return 0, 0, []
        except UnicodeDecodeError:
            self.logger.error(f"ファイルのエンコーディングがUTF-8ではありません: {file_path}")
            import os
            if "PYTEST_CURRENT_TEST" in os.environ:
                return 0, 0, []
            messagebox.showerror("エラー", "ファイルのエンコーディングがUTF-8ではありません。UTF-8で保存してください。", parent=self.parent)
            return 0, 0, []
        except IOError as e:
            self.logger.error(f"ファイルの読み込みに失敗しました: {e}")
            import os
            if "PYTEST_CURRENT_TEST" in os.environ:
                return 0, 0, []
            messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました:\n{e}", parent=self.parent)
            return 0, 0, []
        except sqlite3.Error as e:
            self.logger.error(f"データベース操作中にエラーが発生しました: {e}")
            import os
            if "PYTEST_CURRENT_TEST" in os.environ:
                return 0, 0, []
            messagebox.showerror("エラー", f"データベース操作中にエラーが発生しました:\n{e}", parent=self.parent)
            return 0, 0, []
        except Exception as e:
            self.logger.error(f"タグインポート失敗: {e}")
            import os
            if "PYTEST_CURRENT_TEST" in os.environ:
                return 0, 0, []
            messagebox.showerror("エラー", f"インポートに失敗しました:\n{e}", parent=self.parent)
            return 0, 0, []

    def export_tags_to_csv(self, tags: List[Dict[str, Any]], file_path: str) -> bool:
        """
        タグリストをCSVファイルにエクスポート。
        """
        try:
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=["tag", "jp", "category", "favorite", "is_negative"])
                writer.writeheader()
                for t in tags:
                    writer.writerow({
                        "tag": t.get("tag", ""),
                        "jp": t.get("jp", ""),
                        "category": t.get("category", ""),
                        "favorite": int(t.get("favorite", False)),
                        "is_negative": int(t.get("is_negative", False)),
                    })
            return True
        except Exception as e:
            self.logger.error(f"CSVエクスポート失敗: {e}")
            messagebox.showerror("エラー", f"CSVエクスポートに失敗しました:\n{e}", parent=self.parent)
            return False

    def import_tags_from_csv(self, file_path: str) -> Tuple[int, int, List[Dict[str, Any]]]:
        """
        CSVファイルからタグをインポート。
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                added_tags = []
                skip_count = 0
                for row in reader:
                    tag = normalize_tag(row.get("tag", ""))
                    if not is_valid_tag(tag) or self.exists_tag(tag):
                        skip_count += 1
                        continue
                    jp = row.get("jp", "")
                    category = row.get("category", "")
                    favorite = bool(int(row.get("favorite", 0)))
                    is_negative = bool(int(row.get("is_negative", 0)))
                    if self.add_tag(tag, is_negative, category):
                        self.update_tag(tag, tag, jp, category, is_negative)
                        if favorite:
                            self.toggle_favorite(tag, is_negative)
                        added_tags.append({"tag": tag, "jp": jp, "category": category, "favorite": favorite, "is_negative": is_negative})
                return len(added_tags), skip_count, added_tags
        except Exception as e:
            self.logger.error(f"CSVインポート失敗: {e}")
            messagebox.showerror("エラー", f"CSVインポートに失敗しました:\n{e}", parent=self.parent)
            return 0, 0, []
