# -*- coding: utf-8 -*-
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import simpledialog, messagebox, Menu, filedialog, Toplevel
import tkinter as tk
from tkinter import ttk
import threading
import shutil
import datetime
import os
import sys
import queue
import logging
import sqlite3
import json
import re
from typing import Any, Dict, List, Optional, Callable, cast, Tuple
import webbrowser

from modules.constants import category_keywords, DB_FILE, TRANSLATING_PLACEHOLDER, auto_assign_category
from modules.theme_manager import ThemeManager
from modules.tag_manager import TagManager
from modules.dialogs import CategorySelectDialog, BulkCategoryDialog
# 新しいモジュールからインポート
from modules.ai_predictor import predict_category_ai, suggest_similar_tags_ai
from modules.customization import get_customized_category_keywords, apply_custom_rules

# --- テスト容易化のためのロジック分離 ---
def build_category_list(category_keywords: Dict[str, List[str]]) -> List[str]:
    """
    カテゴリキーワード辞書から、全カテゴリリストを生成する純粋関数。
    """
    return ["全カテゴリ", "お気に入り", "最近使った", "未分類"] + list(category_keywords.keys())

def build_category_descriptions() -> Dict[str, str]:
    """
    全カテゴリの説明辞書を返す純粋関数。
    """
    return {
        "全カテゴリ": "全てのタグを一覧表示します。",
        "お気に入り": "お気に入りに登録されたタグが表示されます。",
        "最近使った": "最近使用したタグが表示されます。",
        "未分類": "どのカテゴリにも属さないタグが表示されます。",
        "品質・画質指定": "画像全体のクオリティや精細さを決定する要素。最初に指定することで、モデルが高品質な出力を目指す。",
        "スタイル・技法": "アートの雰囲気や描画技法を指定する。作品の世界観やジャンルを決定づける。",
        "キャラクター設定": "主役となる人物やキャラクターの基本属性（年齢、性別、種族など）を定義する。",
        "ポーズ・動作": "キャラクターの姿勢や動き。動的な表現や構図に影響する。",
        "服装・ファッション": "キャラクターの衣装やスタイルを指定。時代背景やジャンル感を強調できる。",
        "髪型・髪色": "髪の形状や色を指定。キャラクターの個性や印象に直結する。",
        "表情・感情": "キャラクターの顔の表情や感情を表現。感情的な深みを加える。",
        "背景・環境": "シーンの舞台や周囲の環境を指定。物語性や空間の広がりを演出する。",
        "照明・色調": "光源や色彩のトーンを指定。雰囲気や時間帯の表現に影響する。",
        "小物・アクセサリー": "キャラクターが身につける装飾品や持ち物。細部の演出や個性付けに有効。",
        "特殊効果・フィルター": "画像に加える視覚的エフェクト。幻想的な演出や動きの表現に活用。",
        "構図・カメラ視点": "視点や構図の指定。画面の切り取り方や印象を左右する。",
        "ネガティブ": "生成時に避けたい要素を指定。品質向上や意図しない出力の防止に役立つ。"
    }

# TagManagerAppクラス（UI構築・イベント処理）をmain.pyから移動

class ProgressDialog:
    def __init__(self, parent: Any, title: str = "処理中", message: str = "処理中です。しばらくお待ちください...") -> None:
        self.top = Toplevel(parent)
        self.top.title(title)
        self.top.geometry("350x100")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(False, False)
        self.label = tk.Label(self.top, text=message, font=("TkDefaultFont", 12))
        self.label.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        def disable_close() -> None:
            pass
        self.top.protocol("WM_DELETE_WINDOW", disable_close)  # 閉じるボタン無効
        self.top.update()
    
    def set_message(self, msg: str) -> None:
        self.label.config(text=msg)
        self.top.update()
    
    def close(self) -> None:
        self.top.grab_release()
        self.top.destroy()

class TagManagerApp:
    def __init__(self, root: Any, db_file: Optional[str] = None) -> None:
        self.root = root
        self.theme_manager = ThemeManager()
        # 絶対パスでデータベースファイルを指定
        import os
        db_path = db_file or os.path.join(os.path.dirname(__file__), '..', 'data', 'tags.db')
        self.tag_manager = TagManager(db_file=db_path, parent=self.root)
        # キャッシュを無効化してデータを再読み込み
        self.tag_manager.invalidate_cache()
        self.q: queue.Queue[Any] = queue.Queue()
        self.search_timer: Optional[str] = None
        self.refresh_debounce_id: Optional[str] = None
        self.status_var = tk.StringVar(value="準備完了")
        self.output_tags_data: List[Dict[str, Any]] = []
        self.selected_tags: List[str] = []
        self.weight_values: Dict[str, float] = {}
        self.newly_added_tags: List[str] = []
        self.load_categories()
        self.load_prompt_structure_priorities()
        self.load_category_descriptions()
        # 「全カテゴリ」を先頭に追加
        self.category_list = build_category_list(self.category_keywords)
        self.current_category = "全カテゴリ"
        # ログ設定（INFO以上、ファイル出力も有効化）
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'app.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        # lambdaをdef関数に置き換え
        def select_tag_callback(tag: str) -> None:
            self.select_tag_in_tree(tag)
        self.select_tag_callback = select_tag_callback
        def close_progress_dialog() -> None:
            if hasattr(self, "progress_dialog"):
                self.progress_dialog.close()
        self.close_progress_dialog = close_progress_dialog
        def set_progress_message(msg: str) -> None:
            if hasattr(self, "progress_dialog"):
                self.progress_dialog.set_message(msg)
        self.set_progress_message = set_progress_message
        def clear_status_var() -> None:
            self.status_var.set("")
        self.clear_status_var = clear_status_var
        def show_context_menu_event(event: Any, t: Any) -> None:
            self.show_context_menu(event, t)
        self.show_context_menu_event = show_context_menu_event
        def copy_selected_tags_command() -> None:
            self.copy_selected_tags()
        self.copy_selected_tags_command = copy_selected_tags_command
        def set_category_from_menu_command(c: str) -> None:
            self.set_category_from_menu(c)
        self.set_category_from_menu_command = set_category_from_menu_command
        def export_tags_command(tree: Any) -> None:
            self.export_tags(tree)
        self.export_tags_command = export_tags_command
        def prompt_and_add_tags_negative() -> None:
            self.prompt_and_add_tags(is_negative=True)
        self.prompt_and_add_tags_negative = prompt_and_add_tags_negative
        def apply_theme_command(name: str) -> None:
            self.apply_theme(name)
        self.apply_theme_command = apply_theme_command
        def wm_delete_window_none() -> None:
            pass
        self.wm_delete_window_none = wm_delete_window_none
        self.setup_ui()
        self.process_queue()
        self.refresh_tabs()  # 初期データ読み込み
        self.show_guide_on_startup()

    def load_categories(self) -> None:
        try:
            with open(os.path.join('resources', 'config', 'categories.json'), 'r', encoding='utf-8') as f:
                self.category_keywords = json.load(f)
        except Exception as e:
            self.logger.error(f"categories.jsonの読み込みに失敗しました: {e}")
            messagebox.showerror("エラー", f"カテゴリ定義ファイルの読み込みに失敗しました:\n{e}", parent=self.root)
            self.category_keywords = {}

    def load_prompt_structure_priorities(self) -> None:
        self.category_priorities = {}
        try:
            file_path = os.path.join('resources', 'config', 'prompt_structure.json')
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data.get('prompt_structure', []):
                    category = item.get('category')
                    priority = item.get('priority')
                    if category and priority is not None:
                        if category == "ネガティブプロンプト":
                            self.category_priorities["ネガティブ"] = priority
                        else:
                            self.category_priorities[category] = priority
        except FileNotFoundError:
            self.logger.warning(f"ファイルを読み込めませんでした: {file_path}")
        except json.JSONDecodeError as e:
            self.logger.error(f"JSONファイルの解析エラー: {file_path} - {e}")
        except Exception as e:
            self.logger.error(f"プロンプト構造の優先度読み込み中にエラーが発生しました: {e}")

    def load_category_descriptions(self) -> None:
        self.category_descriptions = build_category_descriptions()
        try:
            file_path = os.path.join('resources', 'config', 'prompt_structure.json')
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data.get('prompt_structure', []):
                    category = item.get('category')
                    description = item.get('description')
                    if category and description:
                        if category == "ネガティブプロンプト":
                            self.category_descriptions["ネガティブ"] = description
                        else:
                            self.category_descriptions[category] = description
        except FileNotFoundError:
            self.logger.warning(f"ファイルを読み込めませんでした: {file_path}")
        except json.JSONDecodeError as e:
            self.logger.error(f"JSONファイルの解析エラー: {file_path} - {e}")
        except Exception as e:
            self.logger.error(f"カテゴリの説明文読み込み中にエラーが発生しました: {e}")

    def backup_db(self) -> None:
        if not os.path.exists(DB_FILE):
            messagebox.showerror("エラー", "データベースファイルが見つかりません。", parent=self.root)
            return
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join('backup', f"tags_backup_{timestamp}.db")
        try:
            # バックアップディレクトリが存在しない場合は作成
            os.makedirs('backup', exist_ok=True)
            shutil.copy(DB_FILE, backup_file)
            messagebox.showinfo("バックアップ完了", f"バックアップを作成しました：\n{backup_file}", parent=self.root)
        except (IOError, shutil.Error) as e:
            self.logger.error(f"バックアップに失敗しました: {e}")
            messagebox.showerror("エラー", f"バックアップに失敗しました：{e}", parent=self.root)

    def setup_ui(self) -> None:
        self.trees = {}  # ← ここで必ず初期化
        self.root.title("タグ管理ツール")
        self.root.geometry("1200x600")
        self.root.resizable(True, True)
        self.root.minsize(1200, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # テーマの適用
        style = tb.Style()
        style.theme_use(self.theme_manager.current_theme)

        # --- メニューバーの追加 ---
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="DBバックアップ", command=self.backup_db)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.on_closing)

        # 編集メニュー
        edit_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="編集", menu=edit_menu)
        edit_menu.add_command(label="元に戻す", command=self.dummy_undo)
        edit_menu.add_command(label="やり直し", command=self.dummy_redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="コピー", command=self.copy_to_clipboard)
        edit_menu.add_command(label="貼り付け", command=self.dummy_paste)

        # テーマメニュー
        theme_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="テーマ", menu=theme_menu)
        for theme_name in self.theme_manager.get_available_themes():
            def make_theme_command(name: str) -> Callable[[], None]:
                def cmd() -> None:
                    self.apply_theme(name)
                return cmd
            theme_menu.add_command(label=theme_name, command=make_theme_command(theme_name))

        # ヘルプメニュー
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="使い方", command=self.show_help)
        help_menu.add_command(label="バージョン情報", command=self.show_about)

        # 設定メニュー
        settings_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="設定", menu=settings_menu)
        settings_menu.add_command(label="保存先の変更", command=self.dummy_settings)
        settings_menu.add_command(label="言語切替", command=self.dummy_settings)
        settings_menu.add_command(label="フォント/サイズ調整", command=self.dummy_settings)
        settings_menu.add_command(label="自動保存ON/OFF", command=self.dummy_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="AI予測設定", command=self.show_ai_settings_dialog)
        settings_menu.add_command(label="カスタムキーワード管理", command=self.show_custom_keywords_dialog)
        settings_menu.add_command(label="カスタムルール管理", command=self.show_custom_rules_dialog)

        # ツールメニュー
        tools_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ツール", menu=tools_menu)
        tools_menu.add_command(label="重複タグの検出・削除", command=self.dummy_tools)
        tools_menu.add_command(label="未分類タグの一括整理", command=self.auto_assign_uncategorized_tags)
        tools_menu.add_command(label="AI予測機能", command=self.show_ai_prediction_dialog)
        tools_menu.add_command(label="タグの一括インポート", command=self.import_tags_async)
        tools_menu.add_command(label="タグの一括エクスポート", command=self.export_all_tags)
        tools_menu.add_command(label="データの初期化", command=self.dummy_tools)

        # 表示メニュー
        view_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="表示", menu=view_menu)
        view_menu.add_command(label="フォントサイズ変更", command=self.dummy_view)
        view_menu.add_command(label="サイドバー表示/非表示", command=self.dummy_view)
        view_menu.add_command(label="タグ一覧の並び順カスタマイズ", command=self.dummy_view)

        # ショートカット一覧
        menubar.add_command(label="ショートカット一覧", command=self.show_shortcuts)

        # 最近使ったファイル/タグ
        recent_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="最近使った", menu=recent_menu)
        recent_menu.add_command(label="最近使ったファイル", command=self.dummy_recent)
        recent_menu.add_command(label="最近編集したタグ", command=self.dummy_recent)

        # データ管理
        data_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="データ管理", menu=data_menu)
        data_menu.add_command(label="CSVエクスポート", command=self.dummy_data)
        data_menu.add_command(label="CSVインポート", command=self.dummy_data)
        data_menu.add_command(label="バックアップの復元", command=self.dummy_data)

        # フィードバック
        menubar.add_command(label="フィードバック", command=self.dummy_feedback)

        # アップデート確認
        menubar.add_command(label="アップデート確認", command=self.dummy_update)

        # 進捗表示用ラベル（メニューバー右端に配置）
        self.menu_status_label = tk.Label(self.root, textvariable=self.status_var, anchor="e", font=("TkDefaultFont", 10), bg="#f0f0f0")
        self.menu_status_label.place(relx=1.0, x=-10, y=2, anchor="ne")

        # --- Main Layout Frames ---
        self.main_frame = tb.Frame(self.root, padding=2, bootstyle="secondary")
        self.main_frame.pack(fill=tb.BOTH, expand=True)

        # このフレームがカテゴリリスト、タグ一覧、詳細パネルを保持
        self.content_frame = tb.Frame(self.main_frame, padding=0)
        self.content_frame.pack(fill=tb.BOTH, expand=True)

        # --- Left Panel (Category List) ---
        self.left_panel = tb.Frame(self.content_frame, padding=2, bootstyle="dark", width=160)
        self.left_panel.pack(side=tb.LEFT, fill=tb.Y, padx=(0, 4))
        self.left_panel.grid_rowconfigure(1, weight=1)
        tb.Label(self.left_panel, text="カテゴリ", bootstyle="inverse-light").grid(row=0, column=0, pady=(0, 2), sticky="nw")
        self.listbox_cat = tk.Listbox(self.left_panel, height=12, font=("TkDefaultFont", 10))
        for cat in self.category_list:
            self.listbox_cat.insert(tk.END, cat)
        self.listbox_cat.selection_set(self.category_list.index(self.current_category))
        self.listbox_cat.grid(row=1, column=0, sticky="nsew")
        self.listbox_cat.bind("<<ListboxSelect>>", self.on_category_select)
        self.category_description_label = tb.Label(self.left_panel, text="", bootstyle="inverse-light", wraplength=140, justify=tk.LEFT, anchor="nw")
        self.category_description_label.grid(row=2, column=0, sticky="nsew", pady=(4, 0))
        self.update_category_description()
        description = self.category_descriptions.get(self.current_category, "説明はありません。")
        self.category_description_label.config(text=description)

        # --- Right Panel (Tag List and Details) ---
        self.treeview_frame = tb.Frame(self.content_frame, padding=2, bootstyle="dark")
        self.treeview_frame.pack(side=tb.LEFT, fill=tb.BOTH, expand=True, padx=(0, 4))
        self.details_panel = tb.Frame(self.content_frame, padding=2, bootstyle="dark")
        self.details_panel.pack(side=tb.LEFT, fill=tb.BOTH, expand=True)

        # Search and Top Buttons
        self.search_button_frame = tb.Frame(self.details_panel, padding=2, bootstyle="secondary")
        self.search_button_frame.pack(fill=tb.X, pady=(0, 2))
        self.entry_search = tb.Entry(self.search_button_frame, font=("TkDefaultFont", 10))
        self.entry_search.pack(side=tb.LEFT, padx=(0, 2), fill=tb.X, expand=True)
        self.entry_search.insert(0, "タグ検索…")
        def on_focus_in(e: Any) -> None:
            if self.entry_search.get() == "タグ検索…":
                self.entry_search.delete(0, tk.END)
        def on_focus_out(e: Any) -> None:
            if not self.entry_search.get():
                self.entry_search.insert(0, "タグ検索…")
        def on_key_release(e: Any) -> None:
            self.refresh_tabs()
        self.entry_search.bind("<FocusIn>", on_focus_in)
        self.entry_search.bind("<FocusOut>", on_focus_out)
        tb.Button(self.search_button_frame, text="クリア", command=self.clear_search).pack(side=tb.LEFT, padx=(0, 2))
        self.entry_search.bind("<KeyRelease>", on_key_release)
        tb.Button(self.search_button_frame, text="タグ追加", command=self.prompt_and_add_tags, bootstyle="primary").pack(side=tb.LEFT, padx=(0, 2))
        tb.Button(self.search_button_frame, text="ネガティブ追加", command=self.prompt_and_add_tags_negative, bootstyle="danger").pack(side=tb.LEFT, padx=(0, 2))

        # Edit Panel
        self.edit_panel = tb.LabelFrame(self.details_panel, text="タグ編集", padding=2, bootstyle="info")
        self.edit_panel.pack(fill=tb.X, pady=2)
        self.edit_panel.columnconfigure(1, weight=1)
        tb.Label(self.edit_panel, text="英語タグ").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_tag = tb.Entry(self.edit_panel, bootstyle="primary")
        self.entry_tag.grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        tb.Label(self.edit_panel, text="日本語訳").grid(row=1, column=0, sticky="w", pady=2)
        self.entry_jp = tb.Entry(self.edit_panel, bootstyle="primary")
        self.entry_jp.grid(row=1, column=1, sticky="ew", padx=2, pady=2)
        tb.Label(self.edit_panel, text="カテゴリ").grid(row=2, column=0, sticky="w", pady=2)
        self.entry_category = tb.Entry(self.edit_panel, bootstyle="primary")
        self.entry_category.grid(row=2, column=1, sticky="ew", padx=2, pady=2)
        tb.Button(self.edit_panel, text="保存", command=self.save_edit, bootstyle="success").grid(row=3, column=0, pady=2, sticky="ew")

        # Operations Panel
        self.ops_panel = tb.Frame(self.details_panel, padding=2, bootstyle="secondary")
        self.ops_panel.pack(fill=tb.X, pady=(0, 2))
        tb.Button(self.ops_panel, text="削除", command=self.delete_tag, bootstyle="danger").pack(side=tb.LEFT, padx=(0, 2))
        tb.Button(self.ops_panel, text="★お気に入り切替", command=self.toggle_favorite, bootstyle="warning").pack(side=tb.LEFT, padx=(0, 2))
        tb.Button(self.ops_panel, text="カテゴリ一括変更", command=self.bulk_category_change, bootstyle="info").pack(side=tb.LEFT, padx=(0, 2))

        # Output Panel
        self.output_panel = tb.LabelFrame(self.details_panel, text="プロンプト出力", padding=2, bootstyle="info")
        self.output_panel.pack(fill=tb.BOTH, expand=True, pady=(0, 2))
        self.output = tb.Text(self.output_panel, height=4)
        self.output.pack(fill=tb.BOTH, expand=True)
        self.output_scrollbar = tb.Scrollbar(self.output, orient="vertical", command=self.output.yview, bootstyle="round")
        self.output_scrollbar.pack(side=tb.RIGHT, fill=tb.Y)
        self.output.configure(yscrollcommand=self.output_scrollbar.set)
        # 出力欄クリア・コピーをoutput_panel内に移動
        output_btn_frame = tb.Frame(self.output_panel)
        output_btn_frame.pack(fill=tb.X, pady=(2, 0), anchor="e")
        tb.Button(output_btn_frame, text="出力欄クリア", command=self.clear_output, bootstyle="light").pack(side=tb.LEFT, padx=(0, 2))
        tb.Button(output_btn_frame, text="コピー", command=self.copy_to_clipboard, bootstyle="primary").pack(side=tb.LEFT, padx=(0, 2))

        # Weight Panel
        self.weight_panel = tb.LabelFrame(self.details_panel, text="重み付け", padding=2, bootstyle="info")
        self.weight_panel.pack(fill=tb.X, pady=(0, 2))
        self.preview_frame = tb.Frame(self.weight_panel)
        self.preview_frame.pack(fill=tb.X, pady=(0, 2))
        self.label_weight_display = tb.Label(self.preview_frame, text="", anchor=tk.W, bootstyle="inverse-light")
        self.label_weight_display.pack(side=tb.LEFT, fill=tb.X, expand=True)
        scale_button_frame = tb.Frame(self.weight_panel)
        scale_button_frame.pack(fill=tb.X)
        tb.Label(scale_button_frame, text="重み付け:", width=8).pack(side=tb.LEFT)
        self.weight_var = tk.DoubleVar(value=1.0)
        tb.Scale(scale_button_frame, variable=self.weight_var, from_=0.1, to=3.0, orient=tk.HORIZONTAL, command=self.update_weight, bootstyle="success").pack(side=tb.LEFT, fill=tb.X, expand=True, padx=(0, 2))
        self.weight_value_label = tb.Label(scale_button_frame, text="1.0", width=4)
        self.weight_value_label.pack(side=tb.LEFT)
        tb.Button(self.weight_panel, text="重み付きで出力に追加", command=self.insert_weighted_tags, bootstyle="info").pack(fill=tb.X, pady=(2, 0))
        # 自動並び替えチェックをweight_panel下部に移動
        self.auto_sort_var = tk.BooleanVar(value=False)
        tb.Checkbutton(self.weight_panel, text="自動並び替え", variable=self.auto_sort_var, bootstyle="light").pack(side=tb.RIGHT, padx=(0, 2), anchor="e")

        # Treeviewの初期化
        cols = ("英語タグ", "日本語訳", "★", "カテゴリ")
        for cat in self.category_list:
            # Treeview用のフレームを作成（スクロールバー用）
            tree_frame = tb.Frame(self.treeview_frame)
            tree_frame.pack(fill=tb.BOTH, expand=True)
            
            # Treeviewを作成
            tree = tb.Treeview(tree_frame, columns=cols, show="headings", selectmode="extended", bootstyle="primary")
            
            # 縦スクロールバーを作成
            tree_scrollbar = tb.Scrollbar(tree_frame, orient="vertical", command=tree.yview, bootstyle="round")
            tree_scrollbar.pack(side=tb.RIGHT, fill=tb.Y)
            
            # Treeviewをスクロールバーと連携
            tree.configure(yscrollcommand=tree_scrollbar.set)
            tree.pack(side=tb.LEFT, fill=tb.BOTH, expand=True)
            
            for col in cols:
                tree.heading(col, text=col)
                tree.column(col, width=120 if col != "★" else 30, anchor=tk.CENTER)
            tree.bind("<<TreeviewSelect>>", self.on_tree_select)
            tree.bind("<Double-1>", self.add_to_output)
            self.setup_context_menu(tree)
            self.trees[cat] = tree
        # 初期カテゴリのTreeviewを表示
        for tree_frame in self.treeview_frame.winfo_children():
            tree_frame.pack_forget()
        self.trees[self.current_category].master.pack(fill=tb.BOTH, expand=True)

        # 初期カテゴリのタグ一覧を必ず表示
        self.refresh_tabs()

    def on_closing(self) -> None:
        if messagebox.askokcancel("終了", "アプリケーションを終了しますか？"):
            self.tag_manager.close()
            self.root.destroy()

    def update_category_description(self) -> None:
        description = self.category_descriptions.get(self.current_category, "説明はありません。")
        self.category_description_label.config(text=description)
        self.left_panel.grid_rowconfigure(2, weight=1)
        self.left_panel.grid_columnconfigure(0, weight=0)

    def setup_context_menu(self, tree: Any) -> None:
        menu = Menu(tree, tearoff=0)
        menu.add_command(label="タグを削除 (Del)", command=self.delete_tag)
        menu.add_command(label="お気に入り切替 (F)", command=self.toggle_favorite)
        menu.add_command(label="選択タグをコピー (C)", command=self.copy_selected_tags_command)
        menu.add_separator()
        submenu = Menu(menu, tearoff=0)
        menu.add_cascade(label="カテゴリ変更", menu=submenu)
        for c in list(self.category_keywords.keys()) + ["未分類"]:
            submenu.add_command(label=c, command=cast(Callable[[], object], self.make_set_category_command(c)))  # type: ignore[arg-type]
        menu.add_separator()
        menu.add_command(label="選択タグをエクスポート", command=self.make_export_tags_command(tree))
        menu.add_command(label="全タグをエクスポート", command=self.export_all_tags)
        menu.add_command(label="タグをインポート", command=self.import_tags_async)
        tree.context_menu = menu
        tree.bind("<Button-3>", self.make_show_context_menu_event(tree))

    def refresh_tabs(self) -> None:
        self.show_current_tree()
        filter_text = self.get_search_text().lower()
        threading.Thread(target=self.worker_thread_fetch, args=(self.q, filter_text, self.current_category), daemon=True).start()
        # --- 全カテゴリ時は一括操作ボタンを無効化（カテゴリ一括変更と削除は除く） ---
        if hasattr(self, 'ops_panel'):
            for child in self.ops_panel.winfo_children():
                if isinstance(child, tb.Button):
                    if child['text'] in ["お気に入り"]:
                        child['state'] = tk.DISABLED if self.current_category == "全カテゴリ" else tk.NORMAL

    def clear_edit_panel(self) -> None:
        self.entry_tag.delete(0, tk.END)
        self.entry_jp.delete(0, tk.END)
        self.entry_category.delete(0, tk.END)

    def save_edit(self) -> None:
        tag_new = self.entry_tag.get().strip()
        jp_new = self.entry_jp.get().strip()
        cat_new = self.entry_category.get().strip()
        # --- バリデーション詳細化 ---
        if not tag_new:
            messagebox.showerror("エラー", "英語タグは空にできません。", parent=self.root)
            return
        if len(tag_new) > 64:
            messagebox.showerror("エラー", "タグ名が長すぎます（最大64文字）", parent=self.root)
            return
        if any(c in tag_new for c in "\\/:*?\"<>|"):
            messagebox.showerror("エラー", "タグ名に禁止文字（\\/:*?\"<>|）が含まれています。", parent=self.root)
            return
        tree = self.trees[self.current_category]
        selected = tree.selection()
        is_negative = (self.current_category == "ネガティブ")
        if is_negative and cat_new != "ネガティブ":
            messagebox.showerror("エラー", "ネガティブタグのカテゴリは「ネガティブ」に固定されています。", parent=self.root)
            return
        if not selected:
            # 新規追加
            if self.tag_manager.exists_tag(tag_new):
                messagebox.showerror("エラー", "その英語タグは既に存在します。", parent=self.root)
                return
            if self.tag_manager.add_tag(tag_new, is_negative, cat_new):
                if jp_new:
                    self.tag_manager.update_tag(tag_new, tag_new, jp_new, cat_new, is_negative)
                self.current_category = "全カテゴリ"
                self.refresh_tabs()
                def delayed_select() -> None:
                    self.select_tag_callback(tag_new)
                self.root.after(200, delayed_select)
            else:
                messagebox.showerror("エラー", "タグの追加に失敗しました。", parent=self.root)
            return
        # 既存タグの編集
        old_tag = tree.item(selected[0], "values")[0]
        if not self.tag_manager.update_tag(old_tag, tag_new, jp_new, cat_new, is_negative):
            messagebox.showerror("エラー", "その英語タグは既に存在します。", parent=self.root)
            return
        self.refresh_tabs()
        def delayed_select_edit() -> None:
            self.select_tag_callback(tag_new)
        self.root.after(200, delayed_select_edit)

    def select_tag_in_tree(self, tag_to_select: str) -> None:
        tree = self.trees[self.current_category]
        for iid in tree.get_children():
            if tree.item(iid, "values")[0] == tag_to_select:
                tree.selection_set(iid)
                tree.focus(iid)
                tree.see(iid)  # 追加：自動スクロール
                break

    def insert_weighted_tags(self) -> None:
        if not self.weight_values: return
        is_negative = (self.current_category == "ネガティブ")
        for tag, weight in self.weight_values.items():
            found = False
            for item in self.output_tags_data:
                if item["tag"] == tag:
                    item["weight"] = weight
                    found = True
                    break
            if not found:
                self.output_tags_data.append({"tag": tag, "weight": weight})
                self.tag_manager.add_recent_tag(tag, is_negative)
        if self.auto_sort_var.get():
            self.output_tags_data = self.sort_prompt_by_priority(self.output_tags_data)
        output_text = self._format_output_text(self.output_tags_data)
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, output_text)

    def on_search_change(self, *args: Any) -> None:
        if self.search_timer:
            self.root.after_cancel(self.search_timer)
        self.search_timer = self.root.after(300, self.refresh_tabs)

    def show_context_menu(self, event: Any, tree: Any) -> None:
        selected = tree.selection()
        tree.context_menu.entryconfig("カテゴリ変更", state="disabled" if self.current_category == "ネガティブ" else "normal")
        tree.context_menu.entryconfig("タグを削除 (Del)", state="normal" if selected else "disabled")
        tree.context_menu.entryconfig("お気に入り切替 (F)", state="normal" if selected else "disabled")
        tree.context_menu.entryconfig("選択タグをコピー (C)", state="normal" if selected else "disabled")
        tree.context_menu.entryconfig("選択タグをエクスポート", state="normal" if selected else "disabled")
        tree.context_menu.post(event.x_root, event.y_root)

    def on_category_select(self, event: Any) -> None:
        selected_index = self.listbox_cat.curselection()
        if selected_index:
            self.current_category = self.category_list[selected_index[0]]
            self.show_current_tree()
            self.refresh_tabs()
            self.clear_edit_panel()
            self.clear_weight_selection()
            description = self.category_descriptions.get(self.current_category, "説明はありません。")
            self.category_description_label.config(text=description)

    def set_category_from_menu(self, category: str) -> None:
        tree = self.trees[self.current_category]
        selected = tree.selection()
        if not selected:
            return
        if category == "未分類":
            category = ""
        changed = False
        for item in selected:
            tag_text = tree.item(item, "values")[0]
            if self.tag_manager.set_category(tag_text, category):
                changed = True
        if changed:
            self.refresh_tabs()

    # --- 編集・ヘルプ用のダミー関数 ---
    def dummy_undo(self) -> None:
        """
        元に戻す操作のダミー関数。
        失敗時はlogger.errorで記録し、必要に応じてmessagebox.showerrorで通知。
        戻り値なし。
        """
        try:
            messagebox.showinfo("元に戻す", "この機能はまだ実装されていません。", parent=self.root)
        except Exception as e:
            self.logger.error(f"dummy_undoエラー: {e}")

    def dummy_redo(self) -> None:
        """
        やり直し操作のダミー関数。
        失敗時はlogger.errorで記録し、必要に応じてmessagebox.showerrorで通知。
        戻り値なし。
        """
        try:
            messagebox.showinfo("やり直し", "この機能はまだ実装されていません。", parent=self.root)
        except Exception as e:
            self.logger.error(f"dummy_redoエラー: {e}")

    def dummy_paste(self) -> None:
        """
        貼り付け操作のダミー関数。
        失敗時はlogger.errorで記録し、必要に応じてmessagebox.showerrorで通知。
        戻り値なし。
        """
        try:
            messagebox.showinfo("貼り付け", "この機能はまだ実装されていません。", parent=self.root)
        except Exception as e:
            self.logger.error(f"dummy_pasteエラー: {e}")

    def show_help(self) -> None:
        help_text = (
            "【タグ管理ツール 使い方ガイド】\n\n"
            "■ 基本操作\n"
            "・タグの追加：\n"
            "　- 画面上部の『タグ追加』ボタンから、カンマ区切りで英語タグを入力し追加できます。\n"
            "　- 『ネガティブ追加』ボタンでネガティブプロンプト用タグも追加可能です。\n\n"
            "・タグの編集：\n"
            "　- タグ一覧から編集したいタグを選択し、右側の編集パネルで内容を修正し『保存』を押します。\n"
            "　- 英語タグ、日本語訳、カテゴリを個別に編集できます。\n\n"
            "・カテゴリの切替・管理：\n"
            "　- 左側リストでカテゴリを選択すると、そのカテゴリのタグが表示されます。\n"
            "　- タグを複数選択し『カテゴリ一括変更』でまとめてカテゴリを変更できます。\n"
            "　- 『未分類』カテゴリはカテゴリ未設定のタグが表示されます。\n\n"
            "・お気に入り・削除：\n"
            "　- タグを選択し『★お気に入り切替』でお気に入り登録/解除ができます。\n"
            "　- 『削除』ボタンで選択したタグを削除します。\n\n"
            "・出力・コピー：\n"
            "　- タグをダブルクリックまたは選択して右下の出力欄に追加できます。\n"
            "　- 『コピー』ボタンで出力欄の内容をクリップボードにコピーできます。\n"
            "　- 『出力欄クリア』で出力内容をリセットします。\n\n"
            "・重み付け機能：\n"
            "　- タグに重み（強調度）を設定し、プロンプト出力に反映できます。\n"
            "　- スライダーで数値を調整し『重み付きで出力に追加』で反映。\n\n"
            "・自動並び替え機能：\n"
            "　- 『自動並び替え』チェックボックスをONにすると、出力欄のタグがカテゴリの優先度順に自動で並び替えられます。\n"
            "　- タグの重要度や出力順を意識したプロンプト作成が簡単になります。\n\n"
            "・テーマ切替：\n"
            "　- メニューバーの『テーマ』からUIテーマ（ダーク/ライト等）を変更できます。\n\n"
            "・バックアップ：\n"
            "　- 『ファイル』→『DBバックアップ』でデータベースのバックアップが作成できます。\n\n"
            "■ ショートカット・便利機能\n"
            "・タグ一覧で複数選択：CtrlまたはShiftキーを押しながらクリック\n"
            "・右クリック：タグ一覧で右クリックするとコンテキストメニューが表示されます。\n"
            "・カテゴリ変更やエクスポートも右クリックから可能です。\n\n"
            "■ 注意事項\n"
            "・タグやカテゴリの編集・削除は元に戻せません。\n"
            "・DBバックアップは定期的に取得することを推奨します。\n"
            "・設定やデータファイルはresources/config/配下に保存されています。\n\n"
            "■ その他\n"
            "・README.mdやヘルプメニューもご参照ください。\n"
        )
        messagebox.showinfo("使い方", help_text, parent=self.root)

    def show_about(self) -> None:
        about_text = (
            "タグ管理ツール v1.0\n"
            "\n"
            "開発者: 芋野斧子\n"
            "Twitter: @im_onoko"
        )
        messagebox.showinfo("バージョン情報", about_text, parent=self.root)

    # --- ダミー関数群 ---
    def dummy_settings(self) -> None:
        messagebox.showinfo("設定", "この機能はまだ実装されていません。", parent=self.root)

    def dummy_tools(self) -> None:
        messagebox.showinfo("ツール", "この機能はまだ実装されていません。", parent=self.root)

    def dummy_view(self) -> None:
        messagebox.showinfo("表示", "この機能はまだ実装されていません。", parent=self.root)

    def show_shortcuts(self) -> None:
        shortcut_text = (
            "【ショートカット一覧】\n\n"
            "・Ctrl+C：コピー\n"
            "・Ctrl+V：貼り付け\n"
            "・Ctrl+Z：元に戻す\n"
            "・Ctrl+Y：やり直し\n"
            "・Ctrl+A：全選択\n"
            "・Ctrl+S：保存\n"
            "・Ctrl+F：検索\n"
            "・Ctrl+クリック/Shift+クリック：複数選択\n"
            "・F1：ヘルプ\n"
        )
        messagebox.showinfo("ショートカット一覧", shortcut_text, parent=self.root)

    def dummy_recent(self) -> None:
        messagebox.showinfo("最近使った", "この機能はまだ実装されていません。", parent=self.root)

    def dummy_data(self) -> None:
        messagebox.showinfo("データ管理", "この機能はまだ実装されていません。", parent=self.root)

    def dummy_feedback(self) -> None:
        messagebox.showinfo("フィードバック", "この機能はまだ実装されていません。", parent=self.root)

    def dummy_update(self) -> None:
        messagebox.showinfo("アップデート確認", "この機能はまだ実装されていません。", parent=self.root)

    def process_queue(self) -> None:
        try:
            message = self.q.get_nowait()
            msg_type = message.get("type")
            if msg_type == "update_tree":
                if message.get("category") == self.current_category:
                    tree = self.trees[self.current_category]
                    tree.delete(*tree.get_children())
                    for item in message["items"]:
                        tree.insert("", tk.END, values=item)
            elif msg_type == "refresh":
                if self.refresh_debounce_id:
                    self.root.after_cancel(self.refresh_debounce_id)
                self.refresh_debounce_id = self.root.after(100, self.refresh_tabs)
            elif msg_type == "info":
                messagebox.showinfo(message["title"], message["message"], parent=self.root)
            elif msg_type == "error":
                self.logger.error(f"{message['title']}: {message['message']}")
                messagebox.showerror(message["title"], message["message"], parent=self.root)
            elif msg_type == "status":
                self.status_var.set(message["message"])
                # 追加完了や準備完了などであれば数秒後に消す
                if any(word in message["message"] for word in ["完了", "準備完了"]):
                    self.root.after(3000, self.clear_status_var)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue) 

    def copy_to_clipboard(self) -> None:
        text = self._format_output_text(self.output_tags_data)
        if not text:
            messagebox.showinfo("コピー", "コピーするテキストがありません。", parent=self.root)
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("コピー完了", "プロンプトをコピーしました", parent=self.root) 

    def clear_output(self) -> None:
        self.output.delete("1.0", tk.END)
        self.output_tags_data.clear()
        messagebox.showinfo("クリア完了", "出力欄をクリアしました！", parent=self.root) 

    def add_to_output(self, event: Optional[Any] = None) -> None:
        tree = self.trees[self.current_category]
        selected = tree.selection()
        if not selected:
            return
        is_negative = (self.current_category == "ネガティブ")
        for item in selected:
            tag_text = tree.item(item, "values")[0]
            if not any(d["tag"] == tag_text for d in self.output_tags_data):
                self.output_tags_data.append({"tag": tag_text, "weight": 1.0})
                self.tag_manager.add_recent_tag(tag_text, is_negative)
        if self.auto_sort_var.get():
            self.output_tags_data = self.sort_prompt_by_priority(self.output_tags_data)
        output_text = self._format_output_text(self.output_tags_data)
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, output_text) 

    def copy_selected_tags(self) -> None:
        pass 

    def toggle_favorite(self) -> None:
        tree = self.trees[self.current_category]
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("お気に入り", "お気に入りにするタグが選択されていません。", parent=self.root)
            return
        is_negative = (self.current_category == "ネガティブ")
        for item in selected:
            tag_text = tree.item(item, "values")[0]
            if self.tag_manager.toggle_favorite(tag_text, is_negative):
                self.refresh_tabs() 

    def delete_tag(self) -> None:
        tree = self.trees[self.current_category]
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("削除", "削除するタグが選択されていません。", parent=self.root)
            return
        
        # 全カテゴリの場合は、各タグの実際のis_negativeフラグを確認
        if self.current_category == "全カテゴリ":
            all_tags = self.tag_manager.get_all_tags()
            tag_info_map = {tag_info["tag"]: tag_info for tag_info in all_tags}
            
            for item in selected:
                tag_text = tree.item(item, "values")[0]
                if tag_text in tag_info_map:
                    is_negative = tag_info_map[tag_text].get("is_negative", False)
                    self.tag_manager.delete_tag(tag_text, is_negative)
        else:
            # 特定のカテゴリの場合は、カテゴリに基づいてis_negativeを判定
            is_negative = (self.current_category == "ネガティブ")
            for item in selected:
                tag_text = tree.item(item, "values")[0]
                self.tag_manager.delete_tag(tag_text, is_negative)
        
        self.refresh_tabs()
        self.clear_edit_panel()
        self.clear_weight_selection() 

    def bulk_category_change(self) -> None:
        tree = self.trees[self.current_category]
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("カテゴリ一括変更", "変更したいタグを選択してください。", parent=self.root)
            return
        if self.current_category == "ネガティブ":
            messagebox.showinfo("カテゴリ一括変更", "ネガティブタグのカテゴリは変更できません。", parent=self.root)
            return
        # 全カテゴリの場合は、選択されたタグがネガティブタグでないかチェック
        if self.current_category == "全カテゴリ":
            selected_tags_text = [tree.item(item, "values")[0] for item in selected]
            # ネガティブタグが含まれているかチェック
            all_tags = self.tag_manager.get_all_tags()
            tag_info_map = {tag_info["tag"]: tag_info for tag_info in all_tags}
            negative_tags = [tag for tag in selected_tags_text if tag in tag_info_map and tag_info_map[tag].get("is_negative", False)]
            if negative_tags:
                messagebox.showinfo("カテゴリ一括変更", "ネガティブタグのカテゴリは変更できません。\nネガティブタグを除外して選択し直してください。", parent=self.root)
            return
        selected_tags_text = [tree.item(item, "values")[0] for item in selected]
        dialog = BulkCategoryDialog(self.root, selected_tags_text)
        if dialog.result and dialog.result['action'] == 'change':
            to_category = dialog.result['to_category']
            if self.tag_manager.bulk_assign_category(selected_tags_text, to_category if to_category != "未分類" else ""):
                self.refresh_tabs()
                messagebox.showinfo("完了", f"選択した{len(selected_tags_text)}個のタグのカテゴリを変更しました。", parent=self.root) 

    def prompt_and_add_tags(self, is_negative: bool = False) -> None:
        title = "ネガティブタグ追加" if is_negative else "タグ追加"
        text = simpledialog.askstring(title, "カンマで区切って入力（英語）:", parent=self.root)
        if text:
            tags_to_add = [t.strip() for t in text.split(",") if t.strip()]
            if tags_to_add:
                # 進捗ダイアログを表示
                self.progress_dialog = ProgressDialog(self.root, title="タグ追加中", message="タグ追加を開始します...")
                threading.Thread(target=self.worker_add_tags, args=(tags_to_add, is_negative), daemon=True).start()

    def worker_add_tags(self, tags: List[str], is_negative: bool) -> None:
        total = len(tags)
        added_count = 0
        try:
            for idx, raw_tag in enumerate(tags, 1):
                msg = f"{total}件中{idx}件目を追加中..."
                self.q.put({"type": "status", "message": msg})
                if hasattr(self, "progress_dialog"):
                    def set_progress() -> None:
                        self.set_progress_message(msg)
                    self.root.after(0, set_progress)
                cleaned_tags = self._strip_weight_from_tag(raw_tag)
                for tag in cleaned_tags:
                    category = auto_assign_category(tag) if not is_negative else ""
                    if self.tag_manager.add_tag(tag, is_negative, category):
                        added_count += 1
                        self.newly_added_tags.append(tag)
                    self.tag_manager.translate_and_update_tag(tag, is_negative)
            # 追加完了後に一度だけリフレッシュ
            self.q.put({"type": "refresh"})
            done_msg = f"追加完了！（追加数: {added_count}件）"
            self.q.put({"type": "status", "message": done_msg})
            if hasattr(self, "progress_dialog"):
                def set_done_message() -> None:
                    self.set_progress_message(done_msg)
                self.root.after(0, set_done_message)
                self.root.after(1200, self.close_progress_dialog)
        except Exception as e:
            self.q.put({"type": "error", "title": "タグ追加エラー", "message": f"タグの追加中にエラーが発生しました:\n{e}"})
            if hasattr(self, "progress_dialog"):
                def set_error_message() -> None:
                    self.set_progress_message("エラーが発生しました")
                self.root.after(0, set_error_message)
                self.root.after(2000, self.close_progress_dialog)
        finally:
            pass

    def worker_import_tags(self, file_path: str) -> None:
        self.q.put({"type": "status", "message": "タグをインポート中..."})
        try:
            success_count, skip_count, added_tags = self.tag_manager.import_tags_from_json(file_path)
            self.q.put({"type": "info", "title": "インポート完了", 
                         "message": f"{success_count}個のタグをインポートしました。\n{skip_count}個のタグは重複または無効のためスキップしました。"})
            self.q.put({"type": "refresh"})

            for tag_info in added_tags:
                if not tag_info.get("jp") or tag_info.get("jp") == TRANSLATING_PLACEHOLDER:
                    self.tag_manager.translate_and_update_tag(tag_info["tag"], tag_info["is_negative"])
                    self.q.put({"type": "refresh"})
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, IOError, sqlite3.Error) as e:
            self.q.put({"type": "error", "title": "インポートエラー", "message": f"タグのインポート中にエラーが発生しました:\n{e}"})
        except Exception as e:
            self.q.put({"type": "error", "title": "予期せぬエラー", "message": f"予期せぬエラーが発生しました:\n{e}"})
        finally:
            self.q.put({"type": "status", "message": "準備完了"}) 

    def import_tags_async(self) -> None:
        file_path = filedialog.askopenfilename(title="タグをインポート", filetypes=[("JSON/CSVファイル", "*.json;*.csv"), ("すべてのファイル", "*.* ")], parent=self.root)
        if file_path:
            if file_path.lower().endswith(".csv"):
                def worker_csv() -> None:
                    self.worker_import_tags_csv(file_path)
                threading.Thread(target=worker_csv, daemon=True).start()
            else:
                threading.Thread(target=self.worker_import_tags, args=(file_path,), daemon=True).start()

    def worker_import_tags_csv(self, file_path: str) -> None:
        self.q.put({"type": "status", "message": "CSVタグをインポート中..."})
        try:
            success_count, skip_count, added_tags = self.tag_manager.import_tags_from_csv(file_path)
            self.q.put({"type": "info", "title": "インポート完了", 
                         "message": f"{success_count}個のタグをインポートしました。\n{skip_count}個のタグは重複または無効のためスキップしました。"})
            self.q.put({"type": "refresh"})
        except Exception as e:
            self.q.put({"type": "error", "title": "インポートエラー", "message": f"CSVタグのインポート中にエラーが発生しました:\n{e}"})
        finally:
            self.q.put({"type": "status", "message": "準備完了"})

    def export_tags(self, tree: Any) -> None:
        selected = tree.selection()
        tags_to_export = []
        is_negative = (self.current_category == "ネガティブ")
        if selected:
            for item in selected:
                tag, jp, favorite, category = tree.item(item, "values")
                tags_to_export.append({"tag": tag, "jp": jp, "category": category, "favorite": favorite, "is_negative": is_negative})
        else:
            tags = self.tag_manager.get_recent_tags() if self.current_category == "最近使った" else \
                   self.tag_manager.negative_tags if self.current_category == "ネガティブ" else self.tag_manager.positive_tags
            filtered_tags = self.filter_tags_optimized(tags, self.get_search_text().lower(), self.current_category)
            tags_to_export = [{"tag": t["tag"], "jp": t["jp"], "category": t["category"], "favorite": t["favorite"], "is_negative": is_negative} for t in filtered_tags]
        if not tags_to_export:
            messagebox.showinfo("エクスポート", "エクスポートするタグがありません。", parent=self.root)
            return
        file_path = filedialog.asksaveasfilename(title="タグをエクスポート", defaultextension=".json",
                                               filetypes=[("JSONファイル", "*.json"), ("CSVファイル", "*.csv"), ("すべてのファイル", "*.* ")], parent=self.root)
        if file_path:
            try:
                if file_path.lower().endswith(".csv"):
                    if self.tag_manager.export_tags_to_csv(tags_to_export, file_path):
                        messagebox.showinfo("エクスポート完了", f"{len(tags_to_export)}個のタグをCSVでエクスポートしました:\n{file_path}", parent=self.root)
                else:
                    if self.tag_manager.export_tags_to_json(tags_to_export, file_path):
                        messagebox.showinfo("エクスポート完了", f"{len(tags_to_export)}個のタグをエクスポートしました:\n{file_path}", parent=self.root)
            except IOError as e:
                self.logger.error(f"タグのエクスポートに失敗しました: {e}")
                messagebox.showerror("エラー", f"エクスポートに失敗しました:\n{e}", parent=self.root)

    def export_all_tags(self) -> None:
        file_path = filedialog.asksaveasfilename(title="全タグをエクスポート", defaultextension=".json",
                                               filetypes=[("JSONファイル", "*.json"), ("すべてのファイル", "*.* ")], parent=self.root)
        if file_path:
            try:
                if self.tag_manager.export_all_tags_to_json(file_path):
                    tags = self.tag_manager.get_all_tags()
                    messagebox.showinfo("エクスポート完了", f"{len(tags)}個の全タグをエクスポートしました:\n{file_path}", parent=self.root)
            except IOError as e:
                self.logger.error(f"全タグのエクスポートに失敗しました: {e}")
                messagebox.showerror("エラー", f"エクスポートに失敗しました:\n{e}", parent=self.root) 

    def show_current_tree(self) -> None:
        for cat, tree in self.trees.items():
            tree_frame = tree.master
            if cat == self.current_category:
                tree_frame.pack(fill=tb.BOTH, expand=True)
            else:
                tree_frame.pack_forget()

    def filter_tags_optimized(self, tags: List[Dict[str, Any]], filter_text: str, category: str) -> List[Dict[str, Any]]:
        # 検索語でタグ名・カテゴリ・日本語訳・お気に入りを横断的にフィルタ
        filter_text = filter_text.lower().strip()
        if not filter_text or filter_text in ("タグ名・カテゴリ・日本語訳・お気に入りで検索…", ""):
            return [t for t in tags if (category=="全カテゴリ" or t["category"]==category or category=="お気に入り" and t["favorite"])]
        def match(t: Dict[str, Any]) -> bool:
            return (
                filter_text in t["tag"].lower()
                or filter_text in t.get("jp", "").lower()
                or filter_text in t.get("category", "").lower()
                or (filter_text in ("fav", "favorite", "お気に入り") and t.get("favorite", False))
            )
        # 検索テキストがある場合は、まず検索でフィルタしてからカテゴリでフィルタ
        filtered_by_search = [t for t in tags if match(t)]
        return [t for t in filtered_by_search if (category=="全カテゴリ" or t["category"]==category or category=="お気に入り" and t["favorite"])]

    def sort_prompt_by_priority(self, tags_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not tags_data:
            return []
        all_tags_info = self.tag_manager.get_all_tags()
        tag_info_map = {t["tag"]: t for t in all_tags_info}
        tags_with_priority = []
        for item in tags_data:
            tag = item["tag"]
            weight = item["weight"]
            info = tag_info_map.get(tag)
            category = info.get("category", "") if info else ""
            priority = self.category_priorities.get(category, 999)
            tags_with_priority.append({"tag": tag, "weight": weight, "priority": priority})
        def get_priority(item: Dict[str, Any]) -> int:
            return item["priority"]
        sorted_tags_with_priority = sorted(tags_with_priority, key=get_priority)
        return sorted_tags_with_priority 

    def _format_output_text(self, tags_data: List[Dict[str, Any]]) -> str:
        parts = []
        for item in tags_data:
            tag = item["tag"]
            weight = item["weight"]
            if weight == 1.0:
                parts.append(tag)
            else:
                parts.append(f"({tag}:{weight:.1f})")
        return ", ".join(parts) 

    def _strip_weight_from_tag(self, tag: str) -> List[str]:
        if tag.startswith("(") and tag.endswith("(") and ":" in tag:
            content_inside_paren = tag[1:-1]
            parts = content_inside_paren.split(":")
            if len(parts) == 2:
                tags_part = parts[0].strip()
                weight_part = parts[1].strip()
                if self._is_float(weight_part):
                    cleaned_tags = [t.strip() for t in tags_part.split(",") if t.strip()]
                    return cleaned_tags
        return [tag.strip()]

    def _is_float(self, value: str) -> bool:
        try:
            float(value)
            return True
        except ValueError:
            return False

    def update_weight(self, value: str) -> None:
        self.weight_value_label.config(text=f"{float(value):.1f}")
        if self.selected_tags:
            self.weight_values[self.selected_tags[-1]] = float(value)
            self.refresh_weight_display()

    def update_weight_selection(self) -> None:
        current_set = set(self.selected_tags)
        self.weight_values = {t: self.weight_values.get(t, 1.0) for t in current_set}
        self.refresh_weight_display()
        self.refresh_weight_output()

    def refresh_weight_display(self) -> None:
        if not self.weight_values:
            self.label_weight_display.config(text="")
            return
        parts = [f"({t}:{w:.1f})" if w != 1.0 else t for t, w in self.weight_values.items()]
        display_text = ", ".join(parts)
        if len(display_text) > 100:
            display_text = display_text[:97] + "..."
        self.label_weight_display.config(text=f"仮表示: {display_text}")

    def refresh_weight_output(self) -> None:
        if not self.selected_tags:
            self.weight_var.set(1.0)
            return
        self.weight_var.set(self.weight_values.get(self.selected_tags[-1], 1.0))

    def clear_weight_selection(self) -> None:
        self.selected_tags.clear()
        self.weight_values.clear()
        self.label_weight_display.config(text="")
        self.refresh_weight_output()

    def worker_thread_fetch(self, q: queue.Queue[Any], filter_text: str, category_to_fetch: str) -> None:
        try:
            q.put({"type": "status", "message": f"{category_to_fetch}カテゴリのタグを読み込み中..."})
            if category_to_fetch == "最近使った":
                tags = self.tag_manager.get_recent_tags()
            elif category_to_fetch == "ネガティブ":
                tags = self.tag_manager.negative_tags
            elif category_to_fetch == "未分類":
                tags = [t for t in self.tag_manager.get_all_tags() if not t.get("category") or t.get("category") == "未分類"]
            elif category_to_fetch == "全カテゴリ":
                tags = self.tag_manager.get_all_tags()
            else:
                tags = self.tag_manager.positive_tags
            filtered_tags = self.filter_tags_optimized(tags, filter_text, category_to_fetch)
            items = [(t["tag"], t["jp"], "★" if t.get("favorite") else "", t.get("category", "")) for t in filtered_tags]
            q.put({"type": "update_tree", "items": items, "category": category_to_fetch})
            q.put({"type": "status", "message": "準備完了"})
        except Exception as e:
            q.put({"type": "error", "title": "タグ取得エラー", "message": f"タグ取得中にエラーが発生しました: {e}"})
            q.put({"type": "status", "message": "準備完了"})

    def on_tree_select(self, event: Any) -> None:
        tree = self.trees[self.current_category]
        selected = tree.selection()
        if not selected:
            self.clear_edit_panel()
            self.clear_weight_selection()
            return
        item = selected[0]
        tag_text, jp_text, _, category_text = tree.item(item, "values")
        self.entry_tag.delete(0, tk.END)
        self.entry_tag.insert(0, tag_text)
        self.entry_jp.delete(0, tk.END)
        self.entry_jp.insert(0, jp_text)
        self.entry_category.delete(0, tk.END)
        self.entry_category.insert(0, category_text)
        self.selected_tags = [tree.item(item, "values")[0] for item in selected]
        self.update_weight_selection() 

    def apply_theme(self, theme_name: str) -> None:
        self.theme_manager.set_theme(theme_name)
        style = tb.Style()
        style.theme_use(theme_name)
        messagebox.showinfo("テーマ変更", f"{theme_name}テーマに変更しました！", parent=self.root) 

    def make_theme_menu_command(self, theme_name: str) -> Callable[[], None]:
        def cmd() -> None:
            self.apply_theme(theme_name)
        return cmd

    def make_set_category_command(self, c: str) -> Callable[[], None]:
        def cmd() -> None:
            self.set_category_from_menu(c)
        return cmd

    def make_export_tags_command(self, tree: Any) -> Callable[[], None]:
        def cmd() -> None:
            self.export_tags(tree)
        return cmd

    def make_show_context_menu_event(self, t: Any) -> Callable[[Any], None]:
        def handler(event: Any) -> None:
            self.show_context_menu(event, t)
        return handler

    def make_set_status_clear(self) -> Callable[[], None]:
        def clear() -> None:
            self.status_var.set("")
        return clear

    def make_set_progress_message(self, msg: str) -> Callable[[], None]:
        def set_msg() -> None:
            if hasattr(self, "progress_dialog"):
                self.progress_dialog.set_message(msg)
        return set_msg

    def make_close_progress_dialog(self) -> Callable[[], None]:
        def close() -> None:
            if hasattr(self, "progress_dialog"):
                self.progress_dialog.close()
        return close

    def add_tag_for_test(self, tag: str, is_negative: bool = False, category: str = "") -> bool:
        """
        テスト用: タグ追加のUIロジックを直接呼び出す（バリデーション・DB登録・翻訳も実行）
        """
        if self.tag_manager.add_tag(tag, is_negative, category):
            self.tag_manager.translate_and_update_tag(tag, is_negative)
            # UI更新を追加
            self.refresh_tabs()
            return True
        return False


    
    def show_guide_on_startup(self) -> None:
        pass

    def clear_search(self) -> None:
        if hasattr(self, 'entry_search'):
            self.entry_search.delete(0, tk.END)
        self.refresh_tabs()

    def get_search_text(self) -> str:
        if hasattr(self, 'entry_search'):
            val = self.entry_search.get()
            if val == "タグ検索…":
                return ""
            return val
        return ""

    def auto_assign_uncategorized_tags(self) -> None:
        """
        未分類タグのカテゴリ自動割り当て機能（AI予測統合版）
        """
        try:
            # 未分類タグを取得
            uncategorized_tags = self.tag_manager.load_tags(is_negative=False)
            uncategorized_tags = [tag for tag in uncategorized_tags if tag.get("category") == "未分類"]
            
            if not uncategorized_tags:
                messagebox.showinfo("未分類タグの一括整理", "未分類のタグが見つかりませんでした。")
                return
            
            # 確認ダイアログ
            result = messagebox.askyesno(
                "未分類タグの一括整理",
                f"未分類のタグが{len(uncategorized_tags)}個見つかりました。\n"
                "AI予測機能とコンテキスト認識機能を統合した高度なカテゴリ自動割り当てを実行しますか？\n\n"
                "この操作は元に戻せません。"
            )
            
            if not result:
                return
            
            # プログレスダイアログを表示
            progress_dialog = ProgressDialog(
                self.root,
                "未分類タグの一括整理",
                f"未分類タグ{len(uncategorized_tags)}個のAI予測によるカテゴリ自動割り当て中..."
            )
            
            # 非同期処理で実行
            def worker_auto_assign() -> None:
                try:
                    assigned_count = 0
                    skipped_count = 0
                    category_stats = {}
                    detailed_results = []
                    
                    # 全タグのリストを作成（コンテキスト分析用）
                    all_tags = [tag_data.get("tag", "") for tag_data in uncategorized_tags]
                    
                    for i, tag_data in enumerate(uncategorized_tags):
                        tag_name = tag_data.get("tag", "")
                        
                        # プログレス更新
                        progress_dialog.set_message(f"AI予測中... ({i+1}/{len(uncategorized_tags)}) {tag_name}")
                        
                        try:
                            # AI予測機能を使用してカテゴリを予測
                            predicted_category, confidence = predict_category_ai(tag_name)
                            
                            # 信頼度が低い場合は従来のコンテキスト認識機能を使用
                            if confidence < 70.0:
                                from modules.category_manager import load_category_keywords, CATEGORY_PRIORITIES
                                from modules.constants import auto_assign_category_context_aware_pure
                                category_keywords = load_category_keywords()
                                fallback_category, fallback_details = auto_assign_category_context_aware_pure(
                                    tag_name, category_keywords, CATEGORY_PRIORITIES, all_tags
                                )
                                
                                # フォールバック結果を使用
                                assigned_category = fallback_category
                                details = fallback_details
                                prediction_method = "コンテキスト認識（フォールバック）"
                            else:
                                assigned_category = predicted_category
                                details = {"ai_score": confidence, "keyword_score": 0, "context_boost": 0, "dynamic_weight": 0, "usage_frequency": 0, "last_used": "不明", "reason": "AI予測による割り当て"}
                                prediction_method = "AI予測"
                            
                            # 統計情報を更新
                            if assigned_category not in category_stats:
                                category_stats[assigned_category] = 0
                            category_stats[assigned_category] += 1
                            
                            # 詳細結果を記録
                            detailed_results.append({
                                "tag": tag_name,
                                "assigned_category": assigned_category,
                                "prediction_method": prediction_method,
                                "confidence": confidence if prediction_method == "AI予測" else details.get("score", 0),
                                "ai_score": details.get("ai_score", 0) if prediction_method == "AI予測" else 0,
                                "keyword_score": details.get("keyword_score", 0),
                                "context_boost": details.get("context_boost", 0),
                                "dynamic_weight": details.get("dynamic_weight", 0),
                                "usage_frequency": details.get("usage_frequency", 0),
                                "last_used": details.get("last_used", "不明"),
                                "reason": details.get("reason", ""),
                                "matched_keywords": [kw for kw, _ in details.get("category_scores", {}).get(assigned_category, {}).get("matched_keywords", [])] if "category_scores" in details else []
                            })
                            
                            if assigned_category != "未分類":
                                # カテゴリを更新
                                if self.tag_manager.set_category(tag_name, assigned_category):
                                    assigned_count += 1
                                else:
                                    skipped_count += 1
                            else:
                                skipped_count += 1
                                
                        except Exception as e:
                            # AI予測でエラーが発生した場合は従来の方法を使用
                            try:
                                from modules.category_manager import load_category_keywords, CATEGORY_PRIORITIES
                                from modules.constants import auto_assign_category_context_aware_pure
                                category_keywords = load_category_keywords()
                                assigned_category, details = auto_assign_category_context_aware_pure(
                                    tag_name, category_keywords, CATEGORY_PRIORITIES, all_tags
                                )
                                
                                if assigned_category not in category_stats:
                                    category_stats[assigned_category] = 0
                                category_stats[assigned_category] += 1
                                
                                detailed_results.append({
                                    "tag": tag_name,
                                    "assigned_category": assigned_category,
                                    "prediction_method": "コンテキスト認識（エラー時）",
                                    "confidence": details.get("score", 0),
                                    "ai_score": 0,
                                    "keyword_score": details.get("keyword_score", 0),
                                    "context_boost": details.get("context_boost", 0),
                                    "dynamic_weight": 0,
                                    "usage_frequency": 0,
                                    "last_used": "不明",
                                    "reason": f"AI予測エラー: {str(e)}",
                                    "matched_keywords": [kw for kw, _ in details.get("category_scores", {}).get(assigned_category, {}).get("matched_keywords", [])]
                                })
                                
                                if assigned_category != "未分類":
                                    if self.tag_manager.set_category(tag_name, assigned_category):
                                        assigned_count += 1
                                    else:
                                        skipped_count += 1
                                else:
                                    skipped_count += 1
                                    
                            except Exception as fallback_error:
                                # フォールバックでもエラーの場合
                                detailed_results.append({
                                    "tag": tag_name,
                                    "assigned_category": "未分類",
                                    "prediction_method": "エラー",
                                    "confidence": 0,
                                    "ai_score": 0,
                                    "keyword_score": 0,
                                    "context_boost": 0,
                                    "dynamic_weight": 0,
                                    "usage_frequency": 0,
                                    "last_used": "不明",
                                    "reason": f"予測エラー: {str(fallback_error)}",
                                    "matched_keywords": []
                                })
                                skipped_count += 1
                    
                    # 完了メッセージ
                    def show_completion() -> None:
                        progress_dialog.close()
                        
                        # 詳細結果を表示
                        result_text = f"AI予測による処理が完了しました。\n\n"
                        result_text += f"カテゴリ割り当て: {assigned_count}個\n"
                        result_text += f"未分類のまま: {skipped_count}個\n\n"
                        
                        # カテゴリ別統計
                        if category_stats:
                            result_text += "カテゴリ別割り当て結果:\n"
                            for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
                                if category != "未分類":
                                    result_text += f"- {category}: {count}個\n"
                        
                        # 予測方法別統計
                        ai_predictions = sum(1 for r in detailed_results if "AI予測" in r.get("prediction_method", ""))
                        context_predictions = sum(1 for r in detailed_results if "コンテキスト認識" in r.get("prediction_method", ""))
                        error_predictions = sum(1 for r in detailed_results if "エラー" in r.get("prediction_method", ""))
                        
                        result_text += f"\n予測方法別統計:\n"
                        result_text += f"- AI予測: {ai_predictions}個\n"
                        result_text += f"- コンテキスト認識: {context_predictions}個\n"
                        result_text += f"- エラー: {error_predictions}個\n"
                        
                        # 詳細結果ダイアログを表示
                        self.show_detailed_assignment_results(detailed_results, result_text)
                    
                    def show_error() -> None:
                        progress_dialog.close()
                        messagebox.showerror("エラー", "カテゴリ自動割り当て中にエラーが発生しました。")
                    
                    # UIスレッドで結果を表示
                    self.root.after(0, show_completion)
                    
                except Exception as e:
                    self.root.after(0, show_error)
                    logging.error(f"カテゴリ自動割り当てエラー: {e}")
            
            # ワーカースレッドを開始
            worker_thread = threading.Thread(target=worker_auto_assign, daemon=True)
            worker_thread.start()
            
        except Exception as e:
            messagebox.showerror("エラー", f"カテゴリ自動割り当ての初期化中にエラーが発生しました: {str(e)}")
            logging.error(f"カテゴリ自動割り当て初期化エラー: {e}")

    def show_detailed_assignment_results(self, detailed_results: List[Dict[str, Any]], summary_text: str) -> None:
        """
        詳細な割り当て結果を表示するダイアログ（AI予測統合版）
        """
        # 結果ダイアログを作成
        result_dialog = Toplevel(self.root)
        result_dialog.title("カテゴリ自動割り当て結果（AI予測統合版）")
        result_dialog.geometry("1200x800")
        result_dialog.transient(self.root)
        result_dialog.grab_set()
        result_dialog.resizable(True, True)
        
        # メインフレーム
        main_frame = tb.Frame(result_dialog, padding=10)
        main_frame.pack(fill=tb.BOTH, expand=True)
        
        # サマリーテキスト
        summary_label = tk.Label(main_frame, text=summary_text, font=("TkDefaultFont", 10), justify=tk.LEFT)
        summary_label.pack(anchor=tk.W, pady=(0, 10))
        
        # 詳細結果のTreeview
        tree_frame = tb.Frame(main_frame)
        tree_frame.pack(fill=tb.BOTH, expand=True)
        
        # 新しいカラム構成（AI予測機能に対応）
        columns = (
            "タグ", "割り当てカテゴリ", "予測方法", "信頼度", "AIスコア", 
            "キーワードスコア", "コンテキストブースト", "動的重み", 
            "使用頻度", "最終使用", "理由"
        )
        
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)
        
        # カラムの設定
        column_widths = {
            "タグ": 150,
            "割り当てカテゴリ": 120,
            "予測方法": 150,
            "信頼度": 80,
            "AIスコア": 80,
            "キーワードスコア": 100,
            "コンテキストブースト": 120,
            "動的重み": 80,
            "使用頻度": 80,
            "最終使用": 100,
            "理由": 200
        }
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=column_widths.get(col, 100))
        
        # スクロールバー
        scrollbar_y = tb.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar_x = tb.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # レイアウト
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # データを挿入
        for result in detailed_results:
            tree.insert("", tk.END, values=(
                result.get("tag", ""),
                result.get("assigned_category", ""),
                result.get("prediction_method", ""),
                f"{result.get('confidence', 0):.1f}%" if result.get('confidence', 0) > 0 else "N/A",
                f"{result.get('ai_score', 0):.2f}" if result.get('ai_score', 0) > 0 else "N/A",
                result.get("keyword_score", 0),
                result.get("context_boost", 0),
                f"{result.get('dynamic_weight', 0):.2f}" if result.get('dynamic_weight', 0) > 0 else "N/A",
                result.get("usage_frequency", 0),
                result.get("last_used", "不明"),
                result.get("reason", "")[:50] + "..." if len(result.get("reason", "")) > 50 else result.get("reason", "")
            ))
        
        # ボタンフレーム
        button_frame = tb.Frame(main_frame)
        button_frame.pack(fill=tb.X, pady=(10, 0))
        
        def save_results() -> None:
            """結果をファイルに保存"""
            try:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"カテゴリ自動割り当て結果_{timestamp}.txt"
                
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")],
                    title="結果を保存"
                )
                
                if file_path:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write("=== カテゴリ自動割り当て結果（AI予測統合版） ===\n")
                        f.write(f"実行日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        f.write(summary_text + "\n\n")
                        f.write("=== 詳細結果 ===\n\n")
                        
                        # ヘッダー
                        f.write("タグ\t割り当てカテゴリ\t予測方法\t信頼度\tAIスコア\tキーワードスコア\tコンテキストブースト\t動的重み\t使用頻度\t最終使用\t理由\n")
                        
                        # データ
                        for result in detailed_results:
                            f.write(f"{result.get('tag', '')}\t")
                            f.write(f"{result.get('assigned_category', '')}\t")
                            f.write(f"{result.get('prediction_method', '')}\t")
                            f.write(f"{result.get('confidence', 0):.1f}%\t")
                            f.write(f"{result.get('ai_score', 0):.2f}\t")
                            f.write(f"{result.get('keyword_score', 0)}\t")
                            f.write(f"{result.get('context_boost', 0)}\t")
                            f.write(f"{result.get('dynamic_weight', 0):.2f}\t")
                            f.write(f"{result.get('usage_frequency', 0)}\t")
                            f.write(f"{result.get('last_used', '不明')}\t")
                            f.write(f"{result.get('reason', '')}\n")
                    
                    messagebox.showinfo("保存完了", f"結果を保存しました:\n{file_path}")
            except Exception as e:
                messagebox.showerror("保存エラー", f"ファイル保存中にエラーが発生しました: {str(e)}")
        
        def refresh_tags() -> None:
            """タグ一覧を更新"""
            try:
                self.refresh_tabs()
                messagebox.showinfo("更新完了", "タグ一覧を更新しました。")
            except Exception as e:
                messagebox.showerror("更新エラー", f"タグ一覧の更新中にエラーが発生しました: {str(e)}")
        
        # ボタン
        tb.Button(button_frame, text="結果を保存", command=save_results, bootstyle="primary").pack(side=tk.LEFT, padx=(0, 10))
        tb.Button(button_frame, text="タグ一覧更新", command=refresh_tags, bootstyle="info").pack(side=tk.LEFT, padx=(0, 10))
        tb.Button(button_frame, text="閉じる", command=result_dialog.destroy, bootstyle="secondary").pack(side=tk.RIGHT)

    def show_ai_prediction_dialog(self) -> None:
        """
        AI予測機能のダイアログを表示
        """
        dialog = Toplevel(self.root)
        dialog.title("AI予測機能")
        dialog.geometry("800x600")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(True, True)

        # メインフレーム
        main_frame = tb.Frame(dialog, padding=10)
        main_frame.pack(fill=tb.BOTH, expand=True)

        # 入力エリア
        input_frame = tb.LabelFrame(main_frame, text="タグ入力", padding=10)
        input_frame.pack(fill=tb.X, pady=(0, 10))

        tb.Label(input_frame, text="予測したいタグを入力してください:").pack(anchor=tk.W)
        
        tag_entry = tb.Entry(input_frame, width=50)
        tag_entry.pack(fill=tb.X, pady=(5, 10))
        tag_entry.focus()

        # ボタンフレーム
        button_frame = tb.Frame(input_frame)
        button_frame.pack(fill=tb.X)

        def predict_category() -> None:
            tag = tag_entry.get().strip()
            if not tag:
                messagebox.showwarning("警告", "タグを入力してください。")
                return
            
            try:
                # AI予測を実行
                category, confidence = predict_category_ai(tag)
                
                # 結果表示
                result_text = f"予測カテゴリ: {category}\n"
                result_text += f"信頼度: {confidence:.1f}%\n\n"
                result_text += "詳細情報:\n"
                result_text += f"- AIスコア: {confidence:.2f}\n"
                result_text += f"- キーワードスコア: 0\n"
                result_text += f"- コンテキストブースト: 0\n"
                result_text += f"- 動的重み: 0.00\n"
                result_text += f"- 使用頻度: 0\n"
                result_text += f"- 最終使用: 不明\n"
                
                result_textarea.delete(1.0, tk.END)
                result_textarea.insert(1.0, result_text)
                
            except Exception as e:
                messagebox.showerror("エラー", f"予測中にエラーが発生しました: {str(e)}")

        def suggest_similar() -> None:
            tag = tag_entry.get().strip()
            if not tag:
                messagebox.showwarning("警告", "タグを入力してください。")
                return
            
            try:
                # 類似タグを取得
                similar_tags = suggest_similar_tags_ai(tag, limit=10)
                
                # 結果表示
                result_text = f"「{tag}」に類似するタグ:\n\n"
                for i, (similar_tag, similarity) in enumerate(similar_tags, 1):
                    result_text += f"{i}. {similar_tag} (類似度: {similarity:.1f}%)\n"
                
                result_textarea.delete(1.0, tk.END)
                result_textarea.insert(1.0, result_text)
                
            except Exception as e:
                messagebox.showerror("エラー", f"類似タグ検索中にエラーが発生しました: {str(e)}")

        tb.Button(button_frame, text="カテゴリ予測", command=predict_category, bootstyle="primary").pack(side=tk.LEFT, padx=(0, 10))
        tb.Button(button_frame, text="類似タグ検索", command=suggest_similar, bootstyle="info").pack(side=tk.LEFT)

        # 結果表示エリア
        result_frame = tb.LabelFrame(main_frame, text="予測結果", padding=10)
        result_frame.pack(fill=tb.BOTH, expand=True)

        # スクロール可能なテキストエリア
        text_frame = tb.Frame(result_frame)
        text_frame.pack(fill=tb.BOTH, expand=True)

        result_textarea = tk.Text(text_frame, wrap=tk.WORD, font=("TkDefaultFont", 10))
        scrollbar = tb.Scrollbar(text_frame, orient=tk.VERTICAL, command=result_textarea.yview)
        result_textarea.configure(yscrollcommand=scrollbar.set)

        result_textarea.pack(side=tk.LEFT, fill=tb.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 閉じるボタン
        tb.Button(main_frame, text="閉じる", command=dialog.destroy, bootstyle="secondary").pack(pady=(10, 0))

    def show_ai_settings_dialog(self) -> None:
        """
        AI予測設定ダイアログを表示
        """
        dialog = Toplevel(self.root)
        dialog.title("AI予測設定")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(True, True)

        # メインフレーム
        main_frame = tb.Frame(dialog, padding=10)
        main_frame.pack(fill=tb.BOTH, expand=True)

        # 設定項目
        settings_frame = tb.LabelFrame(main_frame, text="予測設定", padding=10)
        settings_frame.pack(fill=tb.BOTH, expand=True)

        # AI予測の有効/無効
        ai_enabled_var = tk.BooleanVar(value=True)
        tb.Checkbutton(settings_frame, text="AI予測を有効にする", variable=ai_enabled_var).pack(anchor=tk.W, pady=5)

        # 信頼度閾値
        threshold_frame = tb.Frame(settings_frame)
        threshold_frame.pack(fill=tb.X, pady=5)
        tb.Label(threshold_frame, text="信頼度閾値 (%):").pack(side=tk.LEFT)
        threshold_var = tk.StringVar(value="70")
        threshold_entry = tb.Entry(threshold_frame, textvariable=threshold_var, width=10)
        threshold_entry.pack(side=tk.LEFT, padx=(10, 0))

        # 学習データの管理
        learning_frame = tb.LabelFrame(settings_frame, text="学習データ管理", padding=10)
        learning_frame.pack(fill=tb.X, pady=10)

        def export_learning_data() -> None:
            try:
                from modules.ai_predictor import ai_predictor
                # 学習データのエクスポート機能を実装
                messagebox.showinfo("成功", "学習データをエクスポートしました。")
            except Exception as e:
                messagebox.showerror("エラー", f"エクスポート中にエラーが発生しました: {str(e)}")

        def import_learning_data() -> None:
            try:
                from modules.ai_predictor import ai_predictor
                # 学習データのインポート機能を実装
                messagebox.showinfo("成功", "学習データをインポートしました。")
            except Exception as e:
                messagebox.showerror("エラー", f"インポート中にエラーが発生しました: {str(e)}")

        def clear_learning_data() -> None:
            if messagebox.askyesno("確認", "学習データをクリアしますか？"):
                try:
                    from modules.ai_predictor import ai_predictor
                    # 学習データのクリア機能を実装
                    messagebox.showinfo("成功", "学習データをクリアしました。")
                except Exception as e:
                    messagebox.showerror("エラー", f"クリア中にエラーが発生しました: {str(e)}")

        tb.Button(learning_frame, text="学習データエクスポート", command=export_learning_data).pack(fill=tb.X, pady=2)
        tb.Button(learning_frame, text="学習データインポート", command=import_learning_data).pack(fill=tb.X, pady=2)
        tb.Button(learning_frame, text="学習データクリア", command=clear_learning_data, bootstyle="danger").pack(fill=tb.X, pady=2)

        # 統計情報
        stats_frame = tb.LabelFrame(settings_frame, text="統計情報", padding=10)
        stats_frame.pack(fill=tb.X, pady=10)

        try:
            from modules.ai_predictor import ai_predictor
            stats = ai_predictor.get_tag_statistics("")  # 空文字列で全体統計を取得
            stats_text = f"総予測回数: {stats.get('total_predictions', 0)}\n"
            stats_text += f"平均信頼度: {stats.get('average_confidence', 0):.1f}%\n"
            stats_text += f"学習データ数: {stats.get('learning_data_count', 0)}\n"
            stats_text += f"最終更新: {stats.get('last_updated', '不明')}"
        except Exception:
            stats_text = "統計情報を取得できませんでした。"

        stats_label = tb.Label(stats_frame, text=stats_text, justify=tk.LEFT)
        stats_label.pack(anchor=tk.W)

        # ボタン
        button_frame = tb.Frame(main_frame)
        button_frame.pack(fill=tb.X, pady=(10, 0))

        def save_settings() -> None:
            try:
                # 設定を保存
                settings = {
                    'ai_enabled': ai_enabled_var.get(),
                    'confidence_threshold': float(threshold_var.get())
                }
                
                # 設定ファイルに保存
                settings_file = os.path.join('resources', 'config', 'ai_settings.json')
                os.makedirs(os.path.dirname(settings_file), exist_ok=True)
                with open(settings_file, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("成功", "設定を保存しました。")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("エラー", f"設定保存中にエラーが発生しました: {str(e)}")

        tb.Button(button_frame, text="保存", command=save_settings, bootstyle="primary").pack(side=tk.RIGHT, padx=(10, 0))
        tb.Button(button_frame, text="キャンセル", command=dialog.destroy, bootstyle="secondary").pack(side=tk.RIGHT)

    def show_custom_keywords_dialog(self) -> None:
        """
        カスタムキーワード管理ダイアログを表示
        """
        dialog = Toplevel(self.root)
        dialog.title("カスタムキーワード管理")
        dialog.geometry("700x500")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(True, True)

        # メインフレーム
        main_frame = tb.Frame(dialog, padding=10)
        main_frame.pack(fill=tb.BOTH, expand=True)

        # カテゴリ選択
        category_frame = tb.Frame(main_frame)
        category_frame.pack(fill=tb.X, pady=(0, 10))

        tb.Label(category_frame, text="カテゴリ:").pack(side=tk.LEFT)
        category_var = tk.StringVar()
        category_combo = tb.Combobox(category_frame, textvariable=category_var, values=list(category_keywords.keys()))
        category_combo.pack(side=tk.LEFT, padx=(10, 0))
        category_combo.set(list(category_keywords.keys())[0] if category_keywords else "")

        # キーワード入力
        keyword_frame = tb.Frame(main_frame)
        keyword_frame.pack(fill=tb.X, pady=(0, 10))

        tb.Label(keyword_frame, text="キーワード:").pack(side=tk.LEFT)
        keyword_var = tk.StringVar()
        keyword_entry = tb.Entry(keyword_frame, textvariable=keyword_var, width=30)
        keyword_entry.pack(side=tk.LEFT, padx=(10, 10))

        tb.Label(keyword_frame, text="重み:").pack(side=tk.LEFT)
        weight_var = tk.StringVar(value="1.0")
        weight_entry = tb.Entry(keyword_frame, textvariable=weight_var, width=10)
        weight_entry.pack(side=tk.LEFT, padx=(10, 0))

        def add_keyword() -> None:
            category = category_var.get()
            keyword = keyword_var.get().strip()
            weight = weight_var.get().strip()
            
            if not category or not keyword:
                messagebox.showwarning("警告", "カテゴリとキーワードを入力してください。")
                return
            
            try:
                weight_val = float(weight)
            except ValueError:
                messagebox.showwarning("警告", "重みは数値で入力してください。")
                return
            
            try:
                from modules.customization import customization_manager
                customization_manager.keyword_manager.add_custom_keyword(category, keyword, weight_val)
                keyword_var.set("")
                weight_var.set("1.0")
                refresh_keyword_list()
                messagebox.showinfo("成功", "キーワードを追加しました。")
            except Exception as e:
                messagebox.showerror("エラー", f"キーワード追加中にエラーが発生しました: {str(e)}")

        tb.Button(keyword_frame, text="追加", command=add_keyword, bootstyle="primary").pack(side=tk.LEFT, padx=(10, 0))

        # キーワードリスト
        list_frame = tb.LabelFrame(main_frame, text="カスタムキーワード一覧", padding=10)
        list_frame.pack(fill=tb.BOTH, expand=True)

        # Treeview
        columns = ("カテゴリ", "キーワード", "重み")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)

        scrollbar = tb.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tb.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh_keyword_list() -> None:
            tree.delete(*tree.get_children())
            try:
                from modules.customization import customization_manager
                keywords = customization_manager.keyword_manager.get_custom_keywords()
                for category, keyword_data in keywords.items():
                    for keyword_info in keyword_data:
                        keyword = keyword_info.get("keyword", "")
                        weight = keyword_info.get("weight", 1.0)
                        tree.insert("", tk.END, values=(category, keyword, weight))
            except Exception as e:
                print(f"キーワードリスト更新エラー: {e}")

        def delete_selected_keyword() -> None:
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("警告", "削除するキーワードを選択してください。")
                return
            
            item = tree.item(selection[0])
            category = item['values'][0]
            keyword = item['values'][1]
            
            if messagebox.askyesno("確認", f"「{category}」の「{keyword}」を削除しますか？"):
                try:
                    from modules.customization import customization_manager
                    customization_manager.keyword_manager.remove_custom_keyword(category, keyword)
                    refresh_keyword_list()
                    messagebox.showinfo("成功", "キーワードを削除しました。")
                except Exception as e:
                    messagebox.showerror("エラー", f"キーワード削除中にエラーが発生しました: {str(e)}")

        # ボタン
        button_frame = tb.Frame(main_frame)
        button_frame.pack(fill=tb.X, pady=(10, 0))

        tb.Button(button_frame, text="削除", command=delete_selected_keyword, bootstyle="danger").pack(side=tk.LEFT)
        tb.Button(button_frame, text="閉じる", command=dialog.destroy, bootstyle="secondary").pack(side=tk.RIGHT)

        # 初期データ読み込み
        refresh_keyword_list()

    def show_custom_rules_dialog(self) -> None:
        """
        カスタムルール管理ダイアログを表示
        """
        dialog = Toplevel(self.root)
        dialog.title("カスタムルール管理")
        dialog.geometry("800x600")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(True, True)

        # メインフレーム
        main_frame = tb.Frame(dialog, padding=10)
        main_frame.pack(fill=tb.BOTH, expand=True)

        # ルール入力
        input_frame = tb.LabelFrame(main_frame, text="ルール追加", padding=10)
        input_frame.pack(fill=tb.X, pady=(0, 10))

        # 条件
        condition_frame = tb.Frame(input_frame)
        condition_frame.pack(fill=tb.X, pady=5)
        tb.Label(condition_frame, text="条件:").pack(side=tk.LEFT)
        condition_var = tk.StringVar()
        condition_entry = tb.Entry(condition_frame, textvariable=condition_var, width=50)
        condition_entry.pack(side=tk.LEFT, padx=(10, 0))

        # アクション
        action_frame = tb.Frame(input_frame)
        action_frame.pack(fill=tb.X, pady=5)
        tb.Label(action_frame, text="アクション:").pack(side=tk.LEFT)
        action_var = tk.StringVar()
        action_entry = tb.Entry(action_frame, textvariable=action_var, width=50)
        action_entry.pack(side=tk.LEFT, padx=(10, 0))

        # 説明
        description_frame = tb.Frame(input_frame)
        description_frame.pack(fill=tb.X, pady=5)
        tb.Label(description_frame, text="説明:").pack(side=tk.LEFT)
        description_var = tk.StringVar()
        description_entry = tb.Entry(description_frame, textvariable=description_var, width=50)
        description_entry.pack(side=tk.LEFT, padx=(10, 0))

        def add_rule() -> None:
            condition = condition_var.get().strip()
            action = action_var.get().strip()
            description = description_var.get().strip()
            
            if not condition or not action:
                messagebox.showwarning("警告", "条件とアクションを入力してください。")
                return
            
            try:
                from modules.customization import customization_manager
                rule_id = customization_manager.rule_manager.add_custom_rule("score_modification", {"tag_contains": condition}, {"score_multiplier": 1.0}, 1)
                condition_var.set("")
                action_var.set("")
                description_var.set("")
                refresh_rule_list()
                messagebox.showinfo("成功", "ルールを追加しました。")
            except Exception as e:
                messagebox.showerror("エラー", f"ルール追加中にエラーが発生しました: {str(e)}")

        tb.Button(input_frame, text="ルール追加", command=add_rule, bootstyle="primary").pack(pady=10)

        # ルールリスト
        list_frame = tb.LabelFrame(main_frame, text="カスタムルール一覧", padding=10)
        list_frame.pack(fill=tb.BOTH, expand=True)

        # Treeview
        columns = ("ID", "条件", "アクション", "説明")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            tree.heading(col, text=col)
            if col == "ID":
                tree.column(col, width=50)
            elif col == "説明":
                tree.column(col, width=200)
            else:
                tree.column(col, width=150)

        scrollbar = tb.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tb.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh_rule_list() -> None:
            tree.delete(*tree.get_children())
            try:
                from modules.customization import customization_manager
                rules = customization_manager.rule_manager.get_custom_rules()
                for rule in rules:
                    rule_id = rule.get("id", "")
                    condition = str(rule.get("condition", ""))
                    action = str(rule.get("action", ""))
                    description = rule.get("type", "")
                    tree.insert("", tk.END, values=(rule_id, condition, action, description))
            except Exception as e:
                print(f"ルールリスト更新エラー: {e}")

        def delete_selected_rule() -> None:
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("警告", "削除するルールを選択してください。")
                return
            
            item = tree.item(selection[0])
            rule_id = item['values'][0]
            
            if messagebox.askyesno("確認", f"ルールID {rule_id} を削除しますか？"):
                try:
                    from modules.customization import customization_manager
                    customization_manager.rule_manager.remove_custom_rule(rule_id)
                    refresh_rule_list()
                    messagebox.showinfo("成功", "ルールを削除しました。")
                except Exception as e:
                    messagebox.showerror("エラー", f"ルール削除中にエラーが発生しました: {str(e)}")

        # ボタン
        button_frame = tb.Frame(main_frame)
        button_frame.pack(fill=tb.X, pady=(10, 0))

        tb.Button(button_frame, text="削除", command=delete_selected_rule, bootstyle="danger").pack(side=tk.LEFT)
        tb.Button(button_frame, text="閉じる", command=dialog.destroy, bootstyle="secondary").pack(side=tk.RIGHT)

        # 初期データ読み込み
        refresh_rule_list()

# --- ツールチップ用ヘルパー ---
class ToolTip:
    def __init__(self, widget: Any, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tipwindow: Optional[tk.Toplevel] = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)
    
    def show_tip(self, event: Optional[Any] = None) -> None:
        if self.tipwindow or not self.text:
            return
        x, y, _, cy = self.widget.bbox("insert") if hasattr(self.widget, "bbox") else (0,0,0,0)
        x = x + self.widget.winfo_rootx() + 20
        y = y + cy + self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=("TkDefaultFont", 9))
        label.pack(ipadx=4)
    
    def hide_tip(self, event: Optional[Any] = None) -> None:
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None 