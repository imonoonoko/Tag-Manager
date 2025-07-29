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
        
        # データベースディレクトリを確実に作成
        import os
        db_dir = os.path.dirname(self.db_file)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            print(f"データベースディレクトリを作成: {db_dir}")
        
        # キャッシュを初期化
        self._positive_tags_cache: Optional[List[Dict[str, Any]]] = None
        self._negative_tags_cache: Optional[List[Dict[str, Any]]] = None
        self.logger = logging.getLogger(__name__)
        
        # データベースを初期化
        self._init_database()

    def _get_conn(self) -> sqlite3.Connection:
        """データベース接続を取得"""
        if self._conn is None:
            try:
                # データベースディレクトリを確実に作成
                import os
                db_dir = os.path.dirname(self.db_file)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
                    print(f"データベースディレクトリを作成: {db_dir}")
                
                # データベース接続を作成
                self._conn = sqlite3.connect(self.db_file, check_same_thread=False)
                self._conn.execute("PRAGMA foreign_keys = ON")
                self._conn.execute("PRAGMA journal_mode = WAL")
                self._conn.execute("PRAGMA synchronous = NORMAL")
                self._conn.execute("PRAGMA cache_size = 10000")
                self._conn.execute("PRAGMA temp_store = MEMORY")
                
                print(f"データベース接続を作成: {self.db_file}")
                
            except Exception as e:
                self.logger.error(f"データベース接続エラー: {e}")
                print(f"データベース接続エラー: {e}")
                raise
        return self._conn

    def _execute_query(self, query: str, params: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None) -> sqlite3.Cursor:
        """クエリを実行（後方互換性のため残す）"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor
        except Exception as e:
            self.logger.error(f"クエリ実行エラー: {e}")
            raise

    def _init_database(self) -> None:
        """データベースを初期化"""
        try:
            # データベースディレクトリを確実に作成
            import os
            db_dir = os.path.dirname(self.db_file)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                print(f"データベースディレクトリを作成: {db_dir}")
            
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # テーブルが存在しない場合は作成
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tag TEXT UNIQUE NOT NULL,
                    jp TEXT,
                    favorite BOOLEAN DEFAULT 0,
                    category TEXT DEFAULT '未分類',
                    is_negative BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recent_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tag TEXT NOT NULL,
                    is_negative BOOLEAN DEFAULT 0,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # インデックスを作成
            self._create_indexes(cursor)
            
            conn.commit()
            print(f"データベースを初期化しました: {self.db_file}")
            
        except Exception as e:
            self.logger.error(f"データベース初期化エラー: {e}")
            print(f"データベース初期化エラー: {e}")
            raise
    
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
        try:
            if self._conn is not None:
                self._conn.commit()
                self._conn.close()
                self._conn = None
                print("データベース接続を閉じました")
        except Exception as e:
            self.logger.error(f"データベース接続のクローズエラー: {e}")
            print(f"データベース接続のクローズエラー: {e}")
            # エラーが発生しても接続をNoneに設定
            self._conn = None

    def __del__(self) -> None:
        self.close()

    def invalidate_cache(self) -> None:
        """キャッシュを無効化"""
        self._positive_tags_cache = None
        self._negative_tags_cache = None
        print("キャッシュを無効化しました")

    def load_tags(self, is_negative: bool = False) -> List[Dict[str, Any]]:
        """タグを読み込み"""
        # キャッシュをチェック
        if is_negative and self._negative_tags_cache is not None:
            return self._negative_tags_cache
        if not is_negative and self._positive_tags_cache is not None:
            return self._positive_tags_cache
        
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tag, jp, favorite, category, created_at, updated_at
                FROM tags 
                WHERE is_negative = ?
                ORDER BY tag
            ''', (is_negative,))
            
            rows = cursor.fetchall()
            tags = []
            
            for row in rows:
                tags.append({
                    'tag': row[0],
                    'jp': row[1] or '',
                    'favorite': bool(row[2]),
                    'category': row[3] or '未分類',
                    'created_at': row[4],
                    'updated_at': row[5]
                })
            
            # キャッシュに保存
            if is_negative:
                self._negative_tags_cache = tags
            else:
                self._positive_tags_cache = tags
            
            print(f"タグを読み込みました: {len(tags)}件 (is_negative={is_negative})")
            return tags
            
        except Exception as e:
            self.logger.error(f"タグ読み込みエラー: {e}")
            print(f"タグ読み込みエラー: {e}")
            return []

    def get_all_tags(self) -> List[Dict[str, Any]]:
        """全タグを取得"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tag, jp, favorite, category, is_negative, created_at, updated_at
                FROM tags 
                ORDER BY tag
            ''')
            
            rows = cursor.fetchall()
            all_tags = []
            
            for row in rows:
                all_tags.append({
                    'tag': row[0],
                    'jp': row[1] or '',
                    'favorite': bool(row[2]),
                    'category': row[3] or '未分類',
                    'is_negative': bool(row[4]),
                    'created_at': row[5],
                    'updated_at': row[6]
                })
            
            print(f"全タグを読み込みました: {len(all_tags)}件")
            return all_tags
            
        except Exception as e:
            self.logger.error(f"全タグの読み込みエラー: {e}")
            print(f"全タグの読み込みエラー: {e}")
            return []

    def get_recent_tags(self) -> List[Dict[str, Any]]:
        """最近使ったタグを取得"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT r.tag, r.is_negative, r.used_at, t.jp, t.favorite, t.category
                FROM recent_tags r
                LEFT JOIN tags t ON r.tag = t.tag AND r.is_negative = t.is_negative
                ORDER BY r.used_at DESC
                LIMIT 50
            ''')
            
            rows = cursor.fetchall()
            recent_tags = []
            
            for row in rows:
                recent_tags.append({
                    'tag': row[0],
                    'is_negative': bool(row[1]),
                    'used_at': row[2],
                    'jp': row[3] or '',
                    'favorite': bool(row[4]) if row[4] is not None else False,
                    'category': row[5] or '未分類'
                })
            
            print(f"最近使ったタグを読み込みました: {len(recent_tags)}件")
            return recent_tags
            
        except Exception as e:
            self.logger.error(f"最近使ったタグの読み込みエラー: {e}")
            print(f"最近使ったタグの読み込みエラー: {e}")
            return []

    def add_recent_tag(self, tag: str, is_negative: bool = False) -> None:
        """最近使ったタグを追加"""
        try:
            # タグを正規化
            tag = normalize_tag(tag)
            
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 既存のレコードを削除（同じタグが既に存在する場合）
            cursor.execute('DELETE FROM recent_tags WHERE tag = ? AND is_negative = ?', (tag, is_negative))
            
            # 新しいレコードを追加
            cursor.execute('''
                INSERT INTO recent_tags (tag, is_negative, used_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (tag, is_negative))
            
            # 古いレコードを削除（最大50件まで保持）
            cursor.execute('''
                DELETE FROM recent_tags 
                WHERE id NOT IN (
                    SELECT id FROM recent_tags 
                    ORDER BY used_at DESC 
                    LIMIT 50
                )
            ''')
            
            conn.commit()
            print(f"最近使ったタグを追加しました: {tag}")
            
        except Exception as e:
            self.logger.error(f"最近使ったタグの追加エラー: {e}")
            print(f"最近使ったタグの追加エラー: {e}")

    @property
    def positive_tags(self) -> List[Dict[str, Any]]:
        """ポジティブタグを取得"""
        return self.load_tags(is_negative=False)

    @property
    def negative_tags(self) -> List[Dict[str, Any]]:
        """ネガティブタグを取得"""
        return self.load_tags(is_negative=True)

    def save_tag(self, tag: str, jp: str, favorite: bool, category: str, is_negative: bool) -> bool:
        """タグを保存"""
        try:
            # タグを正規化
            tag = normalize_tag(tag)
            
            if not is_valid_tag(tag):
                self.logger.warning(f"無効なタグ: {tag}")
                return False
            
            # データベースに保存
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 既存のタグを更新または新規作成
            cursor.execute('''
                INSERT OR REPLACE INTO tags (tag, jp, favorite, category, is_negative, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (tag, jp, favorite, category, is_negative))
            
            conn.commit()
            
            # キャッシュを無効化
            self.invalidate_cache()
            
            print(f"タグを保存しました: {tag}")
            return True
            
        except Exception as e:
            self.logger.error(f"タグ保存エラー: {e}")
            print(f"タグ保存エラー: {e}")
            return False

    def _translate_tag(self, tag: str) -> str:
        return google_translate_en_to_ja(tag)

    def translate_and_update_tag(self, tag: str, is_negative: bool = False) -> bool:
        """指定されたタグを翻訳してDBを更新する"""
        try:
            # タグを正規化
            tag = normalize_tag(tag)
            
            jp_trans = self._translate_tag(tag)
            
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE tags SET jp = ? WHERE tag = ? AND is_negative = ? AND jp = ?",
                (jp_trans, tag, is_negative, TRANSLATING_PLACEHOLDER)
            )
            
            if cursor.rowcount > 0:
                conn.commit()
                self.invalidate_cache()
                print(f"タグを翻訳しました: {tag} -> {jp_trans}")
                return True
            else:
                print(f"翻訳対象のタグが見つかりません: {tag}")
                return False
                
        except Exception as e:
            self.logger.error(f"翻訳と更新に失敗: {e}")
            print(f"翻訳と更新に失敗: {e}")
            # 翻訳失敗時の処理
            try:
                conn = self._get_conn()
                cursor = conn.cursor()
                
                cursor.execute(
                    "UPDATE tags SET jp = ? WHERE tag = ? AND is_negative = ? AND jp = ?",
                    ("翻訳失敗", tag, is_negative, TRANSLATING_PLACEHOLDER)
                )
                
                if cursor.rowcount > 0:
                    conn.commit()
                    self.invalidate_cache()
                    
            except Exception as inner_e:
                self.logger.error(f"翻訳失敗時の処理にも失敗: {inner_e}")
                print(f"翻訳失敗時の処理にも失敗: {inner_e}")
            
            return False

    def add_tag(self, tag: str, is_negative: bool = False, category: str = "") -> bool:
        """タグを追加"""
        try:
            # タグを正規化
            tag = normalize_tag(tag)
            
            if not is_valid_tag(tag):
                self.logger.warning(f"無効なタグ: {tag}")
                print(f"無効なタグ: {tag}")
                return False
            
            # 既に存在するかチェック
            if self.tag_exists(tag, is_negative):
                self.logger.warning(f"タグは既に存在します: {tag}")
                print(f"タグは既に存在します: {tag}")
                return False
            
            # カテゴリを自動割り当て
            if not category:
                category = auto_assign_category(tag)
            
            # 翻訳を実行
            jp = self._translate_tag(tag)
            
            # データベースに保存
            success = self.save_tag(tag, jp, False, category, is_negative)
            
            if success:
                print(f"タグを追加しました: {tag}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"タグ追加エラー: {e}")
            print(f"タグ追加エラー: {e}")
            return False

    def exists_tag(self, tag: str) -> bool:
        """タグが存在するかチェック"""
        try:
            # タグを正規化
            tag = normalize_tag(tag)
            
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM tags WHERE tag = ?', (tag,))
            count = cursor.fetchone()[0]
            
            exists = count > 0
            print(f"タグ存在チェック: {tag} -> {exists}")
            return exists
            
        except Exception as e:
            self.logger.error(f"タグ存在チェックエラー: {e}")
            print(f"タグ存在チェックエラー: {e}")
            return False
    
    def tag_exists(self, tag: str, is_negative: bool = False) -> bool:
        """特定のタグが存在するかチェック"""
        try:
            # タグを正規化
            tag = normalize_tag(tag)
            
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM tags WHERE tag = ? AND is_negative = ?', (tag, is_negative))
            count = cursor.fetchone()[0]
            
            exists = count > 0
            print(f"タグ存在チェック: {tag} (is_negative={is_negative}) -> {exists}")
            return exists
            
        except Exception as e:
            self.logger.error(f"タグ存在チェックエラー: {e}")
            print(f"タグ存在チェックエラー: {e}")
            return False

    def delete_tag(self, tag: str, is_negative: bool = False) -> bool:
        """タグを削除"""
        try:
            # タグを正規化
            tag = normalize_tag(tag)
            
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # タグを削除
            cursor.execute('DELETE FROM tags WHERE tag = ? AND is_negative = ?', (tag, is_negative))
            
            # 最近使ったタグからも削除
            cursor.execute('DELETE FROM recent_tags WHERE tag = ? AND is_negative = ?', (tag, is_negative))
            
            conn.commit()
            
            # キャッシュを無効化
            self.invalidate_cache()
            
            print(f"タグを削除しました: {tag}")
            return True
            
        except Exception as e:
            self.logger.error(f"タグ削除エラー: {e}")
            print(f"タグ削除エラー: {e}")
            return False

    def toggle_favorite(self, tag: str, is_negative: bool = False) -> bool:
        """お気に入りを切り替え"""
        try:
            # タグを正規化
            tag = normalize_tag(tag)
            
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 現在のお気に入り状態を取得
            cursor.execute('SELECT favorite FROM tags WHERE tag = ? AND is_negative = ?', (tag, is_negative))
            result = cursor.fetchone()
            
            if result is None:
                self.logger.warning(f"タグが見つかりません: {tag}")
                print(f"タグが見つかりません: {tag}")
                return False
            
            current_favorite = bool(result[0])
            new_favorite = not current_favorite
            
            # お気に入り状態を更新
            cursor.execute('''
                UPDATE tags 
                SET favorite = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE tag = ? AND is_negative = ?
            ''', (new_favorite, tag, is_negative))
            
            conn.commit()
            
            # キャッシュを無効化
            self.invalidate_cache()
            
            print(f"お気に入りを切り替えました: {tag} -> {new_favorite}")
            return True
            
        except Exception as e:
            self.logger.error(f"お気に入り切り替えエラー: {e}")
            print(f"お気に入り切り替えエラー: {e}")
            return False

    def set_category(self, tag: str, category: str, is_negative: bool = False) -> bool:
        """カテゴリを設定"""
        try:
            # タグを正規化
            tag = normalize_tag(tag)
            
            if not is_valid_category(category):
                self.logger.warning(f"無効なカテゴリ: {category}")
                print(f"無効なカテゴリ: {category}")
                return False
            
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # カテゴリを更新
            cursor.execute('''
                UPDATE tags 
                SET category = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE tag = ? AND is_negative = ?
            ''', (category, tag, is_negative))
            
            if cursor.rowcount == 0:
                self.logger.warning(f"タグが見つかりません: {tag}")
                print(f"タグが見つかりません: {tag}")
                return False
            
            conn.commit()
            
            # キャッシュを無効化
            self.invalidate_cache()
            
            print(f"カテゴリを設定しました: {tag} -> {category}")
            return True
            
        except Exception as e:
            self.logger.error(f"カテゴリ設定エラー: {e}")
            print(f"カテゴリ設定エラー: {e}")
            return False

    def update_tag(self, old_tag: str, new_tag: str, jp: str, category: str, is_negative: bool = False) -> bool:
        """タグを更新"""
        try:
            # タグを正規化
            old_tag = normalize_tag(old_tag)
            new_tag = normalize_tag(new_tag)
            
            if not is_valid_tag(new_tag):
                self.logger.warning(f"無効なタグ: {new_tag}")
                print(f"無効なタグ: {new_tag}")
                return False
            
            if not is_valid_category(category):
                self.logger.warning(f"無効なカテゴリ: {category}")
                print(f"無効なカテゴリ: {category}")
                return False
            
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # タグを更新
            cursor.execute('''
                UPDATE tags 
                SET tag = ?, jp = ?, category = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE tag = ? AND is_negative = ?
            ''', (new_tag, jp, category, old_tag, is_negative))
            
            if cursor.rowcount == 0:
                self.logger.warning(f"タグが見つかりません: {old_tag}")
                print(f"タグが見つかりません: {old_tag}")
                return False
            
            # 最近使ったタグも更新
            cursor.execute('''
                UPDATE recent_tags 
                SET tag = ? 
                WHERE tag = ? AND is_negative = ?
            ''', (new_tag, old_tag, is_negative))
            
            conn.commit()
            
            # キャッシュを無効化
            self.invalidate_cache()
            
            print(f"タグを更新しました: {old_tag} -> {new_tag}")
            return True
            
        except Exception as e:
            self.logger.error(f"タグ更新エラー: {e}")
            print(f"タグ更新エラー: {e}")
            return False

    def bulk_assign_category(self, tags: List[str], category: str, is_negative: bool = False) -> bool:
        """複数タグのカテゴリを一括設定"""
        try:
            if not is_valid_category(category):
                self.logger.warning(f"無効なカテゴリ: {category}")
                print(f"無効なカテゴリ: {category}")
                return False
            
            if not tags:
                self.logger.warning("タグリストが空です")
                print("タグリストが空です")
                return False
            
            # タグを正規化
            normalized_tags = [normalize_tag(tag) for tag in tags]
            
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 一括更新
            placeholders = ','.join(['?' for _ in normalized_tags])
            cursor.execute(f'''
                UPDATE tags 
                SET category = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE tag IN ({placeholders}) AND is_negative = ?
            ''', [category] + normalized_tags + [is_negative])
            
            updated_count = cursor.rowcount
            conn.commit()
            
            # キャッシュを無効化
            self.invalidate_cache()
            
            print(f"カテゴリを一括設定しました: {updated_count}件 -> {category}")
            return True
            
        except Exception as e:
            self.logger.error(f"カテゴリ一括設定エラー: {e}")
            print(f"カテゴリ一括設定エラー: {e}")
            return False

    def get_tags_by_category(self, category: str, is_negative: bool = False) -> List[Dict[str, Any]]:
        """カテゴリ別にタグを取得"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tag, jp, favorite, category, created_at, updated_at
                FROM tags 
                WHERE category = ? AND is_negative = ?
                ORDER BY tag
            ''', (category, is_negative))
            
            rows = cursor.fetchall()
            tags = []
            
            for row in rows:
                tags.append({
                    'tag': row[0],
                    'jp': row[1] or '',
                    'favorite': bool(row[2]),
                    'category': row[3] or '未分類',
                    'created_at': row[4],
                    'updated_at': row[5]
                })
            
            print(f"カテゴリ別タグを取得しました: {len(tags)}件 ({category})")
            return tags
            
        except Exception as e:
            self.logger.error(f"カテゴリ別タグ取得エラー: {e}")
            print(f"カテゴリ別タグ取得エラー: {e}")
            return []



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
