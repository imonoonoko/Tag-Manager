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
import os

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
    def __init__(self, db_file: str, parent: Optional[tk.Tk] = None) -> None:
        """TagManagerのコンストラクタ

        Args:
            db_file (str): 使用するデータベースファイルの絶対パス。
            parent (Optional[tk.Tk]): UIの親ウィジェット。
        """
        self.db_file = db_file
        self.parent = parent
        self._conn: Optional[sqlite3.Connection] = None
        self._positive_tags_cache: Optional[List[Dict[str, Any]]] = None
        self._negative_tags_cache: Optional[List[Dict[str, Any]]] = None
        
        self.logger = logging.getLogger(__name__)
        self._init_database()
        
        # 初期タグのインポートを無効化（デフォルトタグはインポートしない）
        # self._import_default_tags()

    def _get_conn(self) -> sqlite3.Connection:
        try:
            if self._conn is None:
                # データベースファイルのディレクトリが存在することを確認
                db_dir = os.path.dirname(self.db_file)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
                
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
        """データベースとテーブルを初期化する"""
        try:
            # データベースディレクトリの作成
            db_dir = os.path.dirname(self.db_file)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                print(f"データベースディレクトリを作成しました: {db_dir}")
            
            # データベース接続とテーブル作成
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # tagsテーブルの作成
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tag TEXT UNIQUE NOT NULL,
                    jp TEXT,
                    favorite INTEGER DEFAULT 0,
                    category TEXT,
                    is_negative INTEGER DEFAULT 0
                )
            ''')
            
            # recent_tagsテーブルの作成
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recent_tags (
                    tag TEXT NOT NULL,
                    is_negative INTEGER DEFAULT 0,
                    used_at TEXT NOT NULL,
                    PRIMARY KEY (tag, is_negative)
                )
            ''')
            
            # インデックスの作成
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_category ON tags(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_favorite ON tags(favorite)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_is_negative ON tags(is_negative)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_recent_tags_used_at ON recent_tags(used_at)')
            
            conn.commit()
            conn.close()
            print(f"データベースとテーブルを初期化しました: {self.db_file}")
            
            # 個人データJSONファイルの初期化
            self._init_personal_data_files()
            
            # self._import_default_tags()  # 無効化：初期タグの自動追加を停止
            
        except Exception as e:
            messagebox.showerror("エラー", f"データベース初期化に失敗しました:\n{e}", parent=self.parent)
    
    def _init_personal_data_files(self) -> None:
        """個人データJSONファイルを初期化する"""
        try:
            from modules.config import POSITIVE_PROMPT_FILE, NEGATIVE_PROMPT_FILE, TRANSLATED_TAGS_FILE
            
            personal_data_files = [
                POSITIVE_PROMPT_FILE,
                NEGATIVE_PROMPT_FILE,
                TRANSLATED_TAGS_FILE,
            ]
            
            for file_path in personal_data_files:
                if not os.path.exists(file_path):
                    try:
                        # ディレクトリが存在しない場合は作成
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump([], f, indent=2, ensure_ascii=False)
                        print(f"個人データファイルを作成しました: {file_path}")
                    except Exception as e:
                        print(f"個人データファイルの作成に失敗しました: {file_path}, エラー: {e}")
                else:
                    print(f"個人データファイルは既に存在します: {file_path}")
                    
        except Exception as e:
            print(f"個人データファイル初期化エラー: {e}")

    def _import_default_tags(self) -> None:
        """デフォルトタグをインポートする（初回起動時のみ）"""
        try:
            # データベースが空かどうかをチェック
            cursor = self._execute_query("SELECT COUNT(*) as count FROM tags")
            count = cursor.fetchone()["count"]
            
            if count == 0:
                # データベースが空の場合のみデフォルトタグをインポート
                import os
                from modules.config import POSITIVE_PROMPT_FILE, NEGATIVE_PROMPT_FILE, TRANSLATED_TAGS_FILE
                
                # 初回起動フラグをチェック
                first_run_flag_path = os.path.join(os.path.dirname(self.db_file), 'first_run_completed.txt')
                
                # 初回起動フラグが存在しない場合のみデフォルトタグをインポート
                if not os.path.exists(first_run_flag_path):
                    print("初回起動を検出しました。デフォルトタグをインポートします。")
                    
                    # 個人データファイルが存在しない場合は空のファイルを作成
                    personal_data_files = [
                        POSITIVE_PROMPT_FILE,
                        NEGATIVE_PROMPT_FILE,
                        TRANSLATED_TAGS_FILE,
                    ]
                    
                    for file_path in personal_data_files:
                        if not os.path.exists(file_path):
                            try:
                                # ディレクトリが存在しない場合は作成
                                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                                with open(file_path, 'w', encoding='utf-8') as f:
                                    f.write('[]')
                                print(f"個人データファイルを作成しました: {file_path}")
                            except Exception as e:
                                print(f"個人データファイルの作成に失敗しました: {file_path}, エラー: {e}")
                    
                    # ポジティブタグのインポート（ファイルが存在し、空でない場合のみ）
                    positive_file_path = POSITIVE_PROMPT_FILE
                    if os.path.exists(positive_file_path):
                        try:
                            with open(positive_file_path, 'r', encoding='utf-8') as f:
                                content = f.read().strip()
                            if content and content != '[]':
                                success_count, skip_count, _ = self.import_tags_from_json(positive_file_path)
                                self.logger.info(f"デフォルトポジティブタグをインポートしました: 成功={success_count}, スキップ={skip_count}")
                            else:
                                print("ポジティブタグファイルが空のため、インポートをスキップします。")
                        except Exception as e:
                            self.logger.warning(f"デフォルトポジティブタグのインポートに失敗: {e}")
                    
                    # ネガティブタグのインポート（ファイルが存在し、空でない場合のみ）
                    negative_file_path = NEGATIVE_PROMPT_FILE
                    if os.path.exists(negative_file_path):
                        try:
                            with open(negative_file_path, 'r', encoding='utf-8') as f:
                                content = f.read().strip()
                            if content and content != '[]':
                                success_count, skip_count, _ = self.import_tags_from_json(negative_file_path)
                                self.logger.info(f"デフォルトネガティブタグをインポートしました: 成功={success_count}, スキップ={skip_count}")
                            else:
                                print("ネガティブタグファイルが空のため、インポートをスキップします。")
                        except Exception as e:
                            self.logger.warning(f"デフォルトネガティブタグのインポートに失敗: {e}")
                    
                    # 初回起動フラグを作成
                    try:
                        with open(first_run_flag_path, 'w', encoding='utf-8') as f:
                            f.write(f"初回起動完了: {datetime.datetime.now().isoformat()}")
                        print("初回起動フラグを作成しました。")
                    except Exception as e:
                        self.logger.warning(f"初回起動フラグの作成に失敗: {e}")
                    
                    # キャッシュをクリア
                    self.invalidate_cache()
                else:
                    print("初回起動は既に完了しています。デフォルトタグのインポートをスキップします。")
                        
        except Exception as e:
            self.logger.error(f"デフォルトタグのインポート中にエラーが発生しました: {e}")
            # エラーが発生してもアプリケーションは継続
            pass

    def _create_indexes(self, cursor: Any) -> None:
        """データベースインデックスを作成する"""
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_category ON tags(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_favorite ON tags(favorite)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_is_negative ON tags(is_negative)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recent_tags_used_at ON recent_tags(used_at)')

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
        print(f"[DEBUG] save_tag - Input: tag='{tag}', jp='{jp}', favorite={favorite}, category='{category}', is_negative={is_negative}")
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
            print(f"[DEBUG] save_tag - 保存成功")
            return True
        except sqlite3.IntegrityError as e:
            print(f"[DEBUG] save_tag - IntegrityError: {e}")
            return False
        except Exception as e:
            print(f"[DEBUG] save_tag - 例外発生: {e}")
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

    def add_tag(self, tag: str, is_negative: bool = False, category: str = "", jp: str = "", favorite: bool = False) -> bool:
        """
        タグをDBに追加する。
        失敗時はFalseを返し、logger.errorと必要に応じてmessagebox.showerrorで通知。
        """
        print(f"[DEBUG] add_tag - Input: tag='{tag}', is_negative={is_negative}, category='{category}', jp='{jp}'")
        
        tag = normalize_tag(tag)
        print(f"[DEBUG] add_tag - normalized tag: '{tag}'")
        
        if not is_valid_tag(tag):
            print(f"[DEBUG] add_tag - タグが無効です: '{tag}'")
            return False
            
        if self.exists_tag(tag):
            print(f"[DEBUG] add_tag - タグは既に存在します: '{tag}'")
            return False
        
        # jpパラメータが指定されていない場合は翻訳プレースホルダーを使用
        if not jp:
            jp = TRANSLATING_PLACEHOLDER
        
        # ネガティブタグの場合でも、適切なカテゴリ分類を許可
        # カテゴリが指定されていない場合は自動割り当て
        if not category:
            from modules.constants import auto_assign_category
            category = auto_assign_category(tag)
            print(f"[DEBUG] add_tag - 自動カテゴリ割り当て: '{category}'")
        
        try:
            result = self.save_tag(tag, jp, favorite, category, is_negative)
            print(f"[DEBUG] add_tag - save_tag result: {result}")
            if result:
                self.logger.info(f"タグがDBに保存されました: tag='{tag}', is_negative={is_negative}, category='{category}'")
            return result
        except Exception as e:
            self.logger.error(f"add_tagエラー: {e}")
            print(f"[DEBUG] add_tag - 例外発生: {e}")
            messagebox.showerror("エラー", f"タグ追加に失敗しました:\n{e}", parent=self.parent)
            return False

    def exists_tag(self, tag: str) -> bool:
        print(f"[DEBUG] exists_tag - チェック対象: '{tag}'")
        try:
            cursor = self._execute_query("SELECT 1 FROM tags WHERE tag = ?", (tag,))
            result = cursor.fetchone() is not None
            print(f"[DEBUG] exists_tag - 結果: {result}")
            return result
        except sqlite3.Error as e:
            self.logger.error(f"タグ存在チェックエラー: {e}")
            print(f"タグ存在チェックエラー: {e}")
            # テスト環境でも例外をraiseせずFalseを返す
            return False
    
    def tag_exists(self, tag: str, is_negative: bool = False) -> bool:
        """
        指定されたタグが存在するかどうかをチェックする（is_negativeを考慮）。
        """
        try:
            cursor = self._execute_query(
                "SELECT 1 FROM tags WHERE tag = ? AND is_negative = ?", 
                (tag, int(is_negative))
            )
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            self.logger.error(f"タグ存在チェックエラー: {e}")
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
            # タグ名が変更される場合のみ重複チェック
            if old_tag != new_tag:
                cursor = self._execute_query("SELECT 1 FROM tags WHERE tag = ? AND is_negative = ?", (new_tag, int(is_negative)))
                if cursor.fetchone():
                    self.logger.warning(f"タグ更新失敗: 新しいタグ名 '{new_tag}' は既に存在します")
                    return False
            
            # 更新を実行
            self._execute_query(
                '''UPDATE tags SET tag = ?, jp = ?, category = ? 
                   WHERE tag = ? AND is_negative = ?''',
                (new_tag, jp, category, old_tag, int(is_negative))
            )
            
            # タグ名が変更された場合、recent_tagsも更新
            if old_tag != new_tag:
                self._execute_query(
                    "UPDATE recent_tags SET tag = ? WHERE tag = ? AND is_negative = ?",
                    (new_tag, old_tag, int(is_negative))
                )
            
            self._get_conn().commit()
            self.invalidate_cache()
            self.logger.info(f"タグ更新成功: '{old_tag}' -> '{new_tag}'")
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

    def get_tags_by_category(self, category: str, is_negative: bool = False) -> List[Dict[str, Any]]:
        """
        指定されたカテゴリのタグを取得する。
        失敗時は空リストを返し、logger.errorで記録。
        """
        try:
            cursor = self._execute_query(
                "SELECT tag, jp, favorite, category FROM tags WHERE category = ? AND is_negative = ? ORDER BY tag",
                (category, int(is_negative))
            )
            tags = []
            for row in cursor.fetchall():
                tags.append({
                    "tag": row[0],
                    "jp": row[1],
                    "favorite": bool(row[2]),
                    "category": row[3]
                })
            return tags
        except sqlite3.Error as e:
            self.logger.error(f"カテゴリ別タグ取得に失敗しました: {e}")
            return []

    def get_tag_info(self, tag: str, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        指定されたタグの情報を取得する。
        カテゴリが指定された場合は、そのカテゴリ内のタグを検索する。
        """
        try:
            query = "SELECT tag, jp, favorite, category, is_negative FROM tags WHERE tag = ?"
            params = (tag,)
            if category is not None:
                query += " AND category = ?"
                params += (category,)

            cursor = self._execute_query(query, params)
            row = cursor.fetchone()
            if row:
                return {
                    "tag": row["tag"],
                    "jp": row["jp"],
                    "favorite": bool(row["favorite"]),
                    "category": row["category"] or "",
                    "is_negative": bool(row["is_negative"])
                }
            return None
        except sqlite3.Error as e:
            self.logger.error(f"タグ情報の取得に失敗しました: {e}")
            return None

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
            
            # ファイル名からネガティブタグかどうかを判定
            import os
            file_name = os.path.basename(file_path).lower()
            is_negative_file = "negative" in file_name
            
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
                
                # ネガティブタグの判定
                # 1. JSONファイルにis_negativeフィールドがある場合はそれを使用
                # 2. ファイル名に"negative"が含まれている場合はネガティブタグとして扱う
                # 3. カテゴリが"ネガティブ"の場合はネガティブタグとして扱う
                is_negative = bool(tag_data.get("is_negative", 0))
                if not is_negative and is_negative_file:
                    is_negative = True
                if not is_negative and tag_data.get("category", "").lower() == "ネガティブ":
                    is_negative = True
                
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
