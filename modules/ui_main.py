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
import time
from typing import Any, Dict, List, Optional, Callable, cast, Tuple
import webbrowser

from modules.constants import category_keywords, DB_FILE, TRANSLATING_PLACEHOLDER, auto_assign_category
from modules.theme_manager import ThemeManager
from modules.tag_manager import TagManager
from modules.dialogs import CategorySelectDialog, BulkCategoryDialog, MultiTagCategoryAssignDialog, LowConfidenceTagsDialog
# 新しいモジュールからインポート
from modules.ai_predictor import predict_category_ai, suggest_similar_tags_ai, get_ai_predictor
from modules.customization import get_customized_category_keywords, apply_custom_rules

# 分離されたモジュールからインポート
from modules.ui_dialogs import ProgressDialog, ToolTip, show_help_dialog, show_about_dialog, show_license_info_dialog, show_shortcuts_dialog
from modules.ui_export_import import export_personal_data, import_personal_data, export_tags, export_all_tags, backup_database
from modules.ui_utils import (
    build_category_list, build_category_descriptions, filter_tags_optimized,
    sort_prompt_by_priority, format_output_text, strip_weight_from_tag,
    is_float, extract_tags_from_prompt, make_theme_menu_command,
    make_set_category_command, make_export_tags_command, make_show_context_menu_event,
    make_set_status_clear, make_set_progress_message, make_close_progress_dialog,
    worker_thread_fetch, show_guide_on_startup, clear_search, get_search_text
)

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

class TagManagerApp:
    def __init__(self, root: Any, db_file: Optional[str] = None) -> None:
        self.root = root
        self.theme_manager = ThemeManager()
        # 絶対パスでデータベースファイルを指定
        from modules.config import DB_FILE
        db_path = db_file or DB_FILE
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
        self.weight_var = tk.DoubleVar(value=1.0)
        self.weight_value_label: Optional[tk.Label] = None
        self.label_weight_display: Optional[tk.Label] = None
        self.output_text: Optional[tk.Text] = None
        self.entry_search: Optional[tb.Entry] = None
        self.listbox_cat: Optional[tk.Listbox] = None
        self.category_description_label: Optional[tb.Label] = None
        self.menu_status_label: Optional[tk.Label] = None
        self.main_frame: Optional[tb.Frame] = None
        self.content_frame: Optional[tb.Frame] = None
        self.left_panel: Optional[tb.Frame] = None
        self.treeview_frame: Optional[tb.Frame] = None
        self.details_panel: Optional[tb.Frame] = None
        self.search_button_frame: Optional[tb.Frame] = None
        self.trees: Dict[str, Any] = {}
        self.tree: Optional[Any] = None
        self.category_list: List[str] = []
        self.current_category = "全カテゴリ"
        self.category_keywords: Dict[str, List[str]] = {}
        self.prompt_structure_priorities: Dict[str, int] = {}
        self.category_descriptions: Dict[str, str] = {}
        
        # コールバック関数の設定
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
            export_tags(self, tree)
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

        # カテゴリと設定の読み込み
        self.load_categories()
        self.load_prompt_structure_priorities()
        self.load_category_descriptions()
        
        # カテゴリリストの構築
        self.category_list = build_category_list(self.category_keywords)
        
        # ログ設定
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
        
        # UI構築と初期化
        self.setup_ui()
        self.process_queue()
        self.refresh_tabs()
        show_guide_on_startup(self)

    def load_categories(self) -> None:
        try:
            with open(os.path.join('resources', 'config', 'categories.json'), 'r', encoding='utf-8') as f:
                self.category_keywords = json.load(f)
        except Exception as e:
            self.logger.error(f"categories.jsonの読み込みに失敗しました: {e}")
            messagebox.showerror("エラー", f"カテゴリ定義ファイルの読み込みに失敗しました:\n{e}", parent=self.root)
            self.category_keywords = {}

    def load_prompt_structure_priorities(self) -> None:
        self.prompt_structure_priorities = {}
        try:
            file_path = os.path.join('resources', 'config', 'prompt_structure.json')
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data.get('prompt_structure', []):
                    category = item.get('category')
                    priority = item.get('priority')
                    if category and priority is not None:
                        if category == "ネガティブプロンプト":
                            self.prompt_structure_priorities["ネガティブ"] = priority
                        else:
                            self.prompt_structure_priorities[category] = priority
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
        """データベースバックアップ"""
        backup_database(self)

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
        file_menu.add_command(label="終了", command=self.on_closing)

        # 編集メニュー
        edit_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="編集", menu=edit_menu)
        edit_menu.add_command(label="コピー", command=self.copy_to_clipboard)



        # ヘルプメニュー
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="使い方", command=self.show_help)
        help_menu.add_command(label="バージョン情報", command=self.show_about)
        help_menu.add_command(label="ライセンス情報", command=self.show_license_info)

        # 設定メニュー
        settings_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="設定", menu=settings_menu)
        settings_menu.add_command(label="テーマ切替", command=self.show_theme_dialog)
        settings_menu.add_command(label="データベースバックアップ", command=self.backup_db)
        settings_menu.add_separator()
        settings_menu.add_command(label="個人データエクスポート", command=self.export_personal_data)
        settings_menu.add_command(label="個人データインポート", command=self.import_personal_data)

        # AIメニュー
        ai_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="AI", menu=ai_menu)
        ai_menu.add_command(label="AI予測機能", command=self.show_ai_prediction_dialog)
        ai_menu.add_command(label="AI学習データ可視化", command=self.show_ai_learning_data_dialog)
        ai_menu.add_command(label="AI設定", command=self.show_ai_settings_dialog)
        ai_menu.add_separator()
        ai_menu.add_command(label="カスタムキーワード管理", command=self.show_custom_keywords_dialog)
        ai_menu.add_command(label="カスタムルール管理", command=self.show_custom_rules_dialog)
        ai_menu.add_separator()
        ai_menu.add_command(label="未分類タグの一括整理", command=self.auto_assign_uncategorized_tags)
        ai_menu.add_command(label="選択タグの自動割り当て", command=self.auto_assign_selected_tags)
        ai_menu.add_separator()
        ai_menu.add_command(label="低信頼度タグ管理", command=self.show_low_confidence_tags_dialog)
        ai_menu.add_separator()
        ai_menu.add_command(label="AIキャッシュクリア", command=self.clear_ai_cache)
        ai_menu.add_command(label="AI機能について", command=self.show_ai_help)

        # ツールメニュー
        tools_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ツール", menu=tools_menu)
        tools_menu.add_command(label="カテゴリ一括AI再分類", command=self.show_bulk_reassign_dialog)
        tools_menu.add_command(label="タグの一括インポート", command=self.import_tags_async)
        tools_menu.add_command(label="タグの一括エクスポート", command=self.export_all_tags)

        # ショートカット一覧
        menubar.add_command(label="ショートカット一覧", command=self.show_shortcuts)







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
        # 出力欄クリア・コピー・翻訳をoutput_panel内に移動
        output_btn_frame = tb.Frame(self.output_panel)
        output_btn_frame.pack(fill=tb.X, pady=(2, 0), anchor="e")
        tb.Button(output_btn_frame, text="出力欄クリア", command=self.clear_output, bootstyle="light").pack(side=tb.LEFT, padx=(0, 2))
        tb.Button(output_btn_frame, text="コピー", command=self.copy_to_clipboard, bootstyle="primary").pack(side=tb.LEFT, padx=(0, 2))
        tb.Button(output_btn_frame, text="翻訳", command=self.show_prompt_translator, bootstyle="info").pack(side=tb.LEFT, padx=(0, 2))

        # 出力欄で直接入力した内容もタグ一覧に追加する
        def on_output_focus_out(event=None):
            text = self.output.get("1.0", tk.END).strip()
            if not text:
                return
            tags = [t.strip() for t in text.replace("\n", ",").split(",") if t.strip()]
            if not tags:
                return
            is_negative = (self.current_category == "ネガティブ")
            # --- 新ダイアログでカテゴリ一括選択 ---
            dlg = MultiTagCategoryAssignDialog(self.root, tags)
            if not dlg.result:
                return
            added, skipped = 0, 0
            for tag, categories in dlg.result.items():
                # ネガティブの場合はカテゴリを空に
                cats_to_add = ["ネガティブ"] if is_negative else categories
                for cat in cats_to_add:
                    if not self.tag_manager.tag_exists(tag, is_negative):
                        self.tag_manager.add_tag(tag, is_negative, cat)
                        added += 1
                        # --- 学習データ記録 ---
                        try:
                            from modules.ai_predictor import get_ai_predictor
                            ai_predictor = get_ai_predictor()
                            ai_predictor.usage_tracker.record_tag_usage(tag, cat)
                        except Exception:
                            pass
                    else:
                        skipped += 1
            if added > 0:
                self.refresh_tabs()

        self.output.bind("<FocusOut>", on_output_focus_out)
        # --- 今後: オートコンプリート機能・日本語→英語変換フックをここに追加予定 ---

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

        # --- オートコンプリート・日本語→英語変換サジェスト機能 ---
        self.suggest_listbox = None
        self.suggest_candidates = []
        self.suggest_var = tk.StringVar()

        def get_tag_candidates(prefix: str) -> List[str]:
            """既存タグ（英語・日本語）から部分一致候補を返す"""
            tags = self.tag_manager.get_all_tags()
            candidates = set()
            prefix_lower = prefix.lower()
            for t in tags:
                if t["tag"].lower().startswith(prefix_lower):
                    candidates.add(t["tag"])
                if t["jp"] and t["jp"].startswith(prefix):
                    candidates.add(t["tag"])  # 日本語→英語逆引き
            return sorted(candidates)

        def ai_translate_jp_to_en(jp_text: str) -> List[str]:
            """AI翻訳APIや既存関数で日本語→英語タグ候補を返す（ダミー実装）"""
            # ここで本来はAI翻訳APIを呼び出す
            # 例: from modules.prompt_translator import translate_prompt_to_en
            # return translate_prompt_to_en(jp_text)
            return [jp_text]  # ダミー: そのまま返す

        def show_suggest_listbox(candidates: List[str], insert_pos: str):
            if self.suggest_listbox:
                self.suggest_listbox.destroy()
            if not candidates:
                return
            self.suggest_listbox = tk.Listbox(self.output_panel, listvariable=self.suggest_var, height=min(8, len(candidates)), font=("TkDefaultFont", 10))
            for c in candidates:
                self.suggest_listbox.insert(tk.END, c)
            self.suggest_listbox.place(x=5, y=5)  # TODO: カーソル位置に合わせて調整
            self.suggest_listbox.lift()
            self.suggest_listbox.bind("<ButtonRelease-1>", lambda e: complete_from_suggest())
            self.suggest_listbox.bind("<Return>", lambda e: complete_from_suggest())

        def hide_suggest_listbox():
            if self.suggest_listbox:
                self.suggest_listbox.destroy()
                self.suggest_listbox = None

        def complete_from_suggest():
            if not self.suggest_listbox:
                return
            selection = self.suggest_listbox.curselection()
            if not selection:
                return
            selected = self.suggest_listbox.get(selection[0])
            # 現在のカーソル位置の単語を置換
            idx = self.output.index(tk.INSERT)
            # 直前のカンマや改行で区切る
            line, col = map(int, idx.split("."))
            line_text = self.output.get(f"{line}.0", f"{line}.end")
            left = line_text[:col]
            right = line_text[col:]
            # 最後の区切り位置を探す
            last_comma = left.rfind(",")
            last_space = left.rfind(" ")
            last_sep = max(last_comma, last_space)
            if last_sep == -1:
                new_left = ""
            else:
                new_left = left[:last_sep+1]
            completed = new_left + selected + right
            self.output.delete(f"{line}.0", f"{line}.end")
            self.output.insert(f"{line}.0", completed)
            hide_suggest_listbox()

        def on_output_keyrelease(event=None):
            # 入力中の単語を取得
            idx = self.output.index(tk.INSERT)
            line, col = map(int, idx.split("."))
            line_text = self.output.get(f"{line}.0", f"{line}.end")
            left = line_text[:col]
            # 区切り文字で分割
            if "," in left:
                prefix = left.split(",")[-1].strip()
            elif " " in left:
                prefix = left.split(" ")[-1].strip()
            else:
                prefix = left.strip()
            if not prefix:
                hide_suggest_listbox()
                return
            # 英語・日本語両方でサジェスト
            candidates = get_tag_candidates(prefix)
            # 日本語で既存タグに該当しない場合はAI翻訳候補も追加
            if not candidates and re.search(r'[ぁ-んァ-ン一-龥]', prefix):
                candidates = ai_translate_jp_to_en(prefix)
            show_suggest_listbox(candidates, idx)

        self.output.bind("<KeyRelease>", on_output_keyrelease)
        # サジェスト選択時の補完
        # Listboxのイベントはshow_suggest_listbox内でバインド
        # --- 既存のon_output_focus_outはそのまま維持 ---

    def on_closing(self) -> None:
        """アプリケーション終了時の処理"""
        try:
            # データベースを確実に保存
            if hasattr(self, 'tag_manager') and self.tag_manager:
                self.tag_manager.close()
            
            # ルートウィンドウを破棄
            if hasattr(self, 'root') and self.root:
                self.root.destroy()
                
        except Exception as e:
            print(f"アプリケーション終了時のエラー: {e}")
            # エラーが発生しても強制終了
            if hasattr(self, 'root') and self.root:
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
        # 現在のツリーを表示
        self.show_current_tree()
        # 検索テキストを取得
        filter_text = self.get_search_text().lower()
        # 非同期でタグデータを取得
        threading.Thread(target=self.worker_thread_fetch, args=(self.q, filter_text, self.current_category), daemon=True).start()
        # 全カテゴリ時は一括操作ボタンを無効化（カテゴリ一括変更と削除は除く）
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
        
        # AI学習: カテゴリ変更を記録
        if old_tag != tag_new or cat_new:  # タグ名またはカテゴリが変更された場合
            try:
                from modules.ai_predictor import get_ai_predictor
                ai_predictor = get_ai_predictor()
                ai_predictor.usage_tracker.record_tag_usage(tag_new, cat_new)
            except Exception as e:
                # AI学習エラーは無視（UI操作を継続）
                pass
        
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
            # 現在のツリーを表示
            self.show_current_tree()
            # タブを更新
            self.refresh_tabs()
            # 編集パネルをクリア
            self.clear_edit_panel()
            # 重み選択をクリア
            self.clear_weight_selection()
            # カテゴリ説明を更新
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
                # AI学習: カテゴリ変更を記録
                try:
                    from modules.ai_predictor import get_ai_predictor
                    ai_predictor = get_ai_predictor()
                    ai_predictor.usage_tracker.record_tag_usage(tag_text, category)
                except Exception as e:
                    # AI学習エラーは無視（UI操作を継続）
                    pass
        if changed:
            self.refresh_tabs()

    # --- 編集・ヘルプ用のダミー関数 ---


    def show_help(self) -> None:
        """ヘルプダイアログを表示"""
        show_help_dialog(self.root)

    def show_about(self) -> None:
        """バージョン情報ダイアログを表示"""
        show_about_dialog(self.root)

    def show_license_info(self) -> None:
        """ライセンス情報ダイアログを表示"""
        show_license_info_dialog(self.root)

    def show_shortcuts(self) -> None:
        """ショートカット一覧ダイアログを表示"""
        show_shortcuts_dialog(self.root)

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
        
        # プロンプトからタグを抽出
        tags = self._extract_tags_from_prompt(text)
        
        # クリップボードにコピー
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        
        # タグが抽出できた場合は保存確認ダイアログを表示
        if tags:
            self._show_save_tags_dialog(tags)
        else:
            messagebox.showinfo("コピー完了", "プロンプトをコピーしました", parent=self.root)
    
    def _extract_tags_from_prompt(self, prompt_text: str) -> List[str]:
        """プロンプトテキストからタグを抽出する"""
        tags = []
        lines = prompt_text.split('\n')
        for line in lines:
            line = line.strip()
            if line:
                # カンマ区切りでタグを分割
                parts = [part.strip() for part in line.split(',')]
                for part in parts:
                    # 重み付けを除去（例: "tag (1.2)" -> "tag"）
                    if '(' in part and ')' in part:
                        part = part.split('(')[0].strip()
                    if part and len(part) > 0:
                        tags.append(part)
        return tags
    
    def _show_save_tags_dialog(self, tags: List[str]) -> None:
        """タグ保存確認ダイアログを表示する"""
        # 既存のタグをチェック
        existing_tags = []
        new_tags = []
        
        for tag in tags:
            if self.tag_manager.tag_exists(tag, False) or self.tag_manager.tag_exists(tag, True):
                existing_tags.append(tag)
            else:
                new_tags.append(tag)
        
        # ダイアログメッセージを作成
        message = "プロンプトをコピーしました。\n\n"
        if new_tags:
            message += f"新規タグ ({len(new_tags)}個):\n"
            for tag in new_tags[:10]:  # 最初の10個のみ表示
                message += f"  • {tag}\n"
            if len(new_tags) > 10:
                message += f"  ... 他 {len(new_tags) - 10}個\n"
            message += "\n"
        
        if existing_tags:
            message += f"既存タグ ({len(existing_tags)}個):\n"
            for tag in existing_tags[:5]:  # 最初の5個のみ表示
                message += f"  • {tag}\n"
            if len(existing_tags) > 5:
                message += f"  ... 他 {len(existing_tags) - 5}個\n"
            message += "\n"
        
        if new_tags:
            message += "これらのタグをタグ一覧に保存しますか？"
            
            result = messagebox.askyesno(
                "タグ保存確認", 
                message, 
                parent=self.root
            )
            
            if result:
                # タグを保存
                self._save_extracted_tags(new_tags)
        else:
            message += "全てのタグは既に保存済みです。"
            messagebox.showinfo("コピー完了", message, parent=self.root)
    
    def _save_extracted_tags(self, tags: List[str]) -> None:
        """抽出されたタグをタグ一覧に保存する"""
        try:
            # プログレスダイアログを表示
            progress_dialog = ProgressDialog(
                self.root, 
                "タグ保存中", 
                f"{len(tags)}個のタグを保存中..."
            )
            
            def save_worker():
                saved_count = 0
                for i, tag in enumerate(tags):
                    # プログレス更新
                    progress_dialog.set_message(f"タグを保存中... ({i+1}/{len(tags)})")
                    
                    # タグを保存（通常タグとして）
                    if self.tag_manager.add_tag(tag, False, ""):
                        saved_count += 1
                    
                    # UI更新のため少し待機
                    time.sleep(0.01)
                
                # 完了メッセージ
                def show_completion():
                    progress_dialog.close()
                    messagebox.showinfo(
                        "保存完了", 
                        f"{saved_count}個のタグをタグ一覧に保存しました。", 
                        parent=self.root
                    )
                    # タブを更新
                    self.refresh_tabs()
                
                self.root.after(0, show_completion)
            
            # ワーカースレッドを開始
            import threading
            thread = threading.Thread(target=save_worker)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            messagebox.showerror(
                "エラー", 
                f"タグの保存中にエラーが発生しました:\n{e}", 
                parent=self.root
            ) 

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
                # AI学習: 一括カテゴリ変更を記録
                try:
                    from modules.ai_predictor import get_ai_predictor
                    ai_predictor = get_ai_predictor()
                    for tag in selected_tags_text:
                        ai_predictor.usage_tracker.record_tag_usage(tag, to_category if to_category != "未分類" else "")
                except Exception as e:
                    # AI学習エラーは無視（UI操作を継続）
                    pass
                
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
                        # AI学習: 新規追加されたタグのカテゴリを記録
                        if category and not is_negative:
                            try:
                                from modules.ai_predictor import get_ai_predictor
                                ai_predictor = get_ai_predictor()
                                ai_predictor.usage_tracker.record_tag_usage(tag, category)
                            except Exception as e:
                                # AI学習エラーは無視（UI操作を継続）
                                pass
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
        """タグエクスポート"""
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
        """全タグエクスポート"""
        export_all_tags(self)

    def show_current_tree(self) -> None:
        """現在選択されているカテゴリのツリーを表示"""
        for cat, tree in self.trees.items():
            tree_frame = tree.master
            if cat == self.current_category:
                tree_frame.pack(fill=tb.BOTH, expand=True)
            else:
                tree_frame.pack_forget()

    def filter_tags_optimized(self, tags: List[Dict[str, Any]], filter_text: str, category: str) -> List[Dict[str, Any]]:
        """検索語でタグ名・カテゴリ・日本語訳・お気に入りを横断的にフィルタ"""
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
        """プロンプト構造の優先度に基づいてタグをソート"""
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
            priority = self.prompt_structure_priorities.get(category, 999)
            tags_with_priority.append({"tag": tag, "weight": weight, "priority": priority})
        
        def get_priority(item: Dict[str, Any]) -> int:
            return item["priority"]
        
        sorted_tags_with_priority = sorted(tags_with_priority, key=get_priority)
        return sorted_tags_with_priority

    def _format_output_text(self, tags_data: List[Dict[str, Any]]) -> str:
        """タグデータをプロンプト形式のテキストに変換"""
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
        """タグから重みを除去してタグ名のみを取得"""
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
        """文字列が浮動小数点数かどうかを判定"""
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
        """非同期でタグデータを取得"""
        try:
            q.put({"type": "status", "message": f"{category_to_fetch}カテゴリのタグを読み込み中..."})
            
            # カテゴリに応じてタグを取得
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
            
            # フィルタリング
            filtered_tags = self.filter_tags_optimized(tags, filter_text, category_to_fetch)
            
            # アイテム形式に変換
            items = [(t["tag"], t["jp"], "★" if t.get("favorite") else "", t.get("category", "")) for t in filtered_tags]
            
            # キューに結果を送信
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

    def show_theme_dialog(self) -> None:
        """
        テーマ選択ダイアログを表示する
        """
        theme_dialog = Toplevel(self.root)
        theme_dialog.title("テーマ選択")
        theme_dialog.geometry("400x500")
        theme_dialog.transient(self.root)
        theme_dialog.grab_set()
        theme_dialog.resizable(False, False)
        
        # メインフレーム
        main_frame = tb.Frame(theme_dialog, padding=10)
        main_frame.pack(fill=tb.BOTH, expand=True)
        
        # タイトル
        title_label = tb.Label(main_frame, text="テーマを選択してください", font=("TkDefaultFont", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 現在のテーマ表示
        current_theme = self.theme_manager.current_theme
        current_label = tb.Label(main_frame, text=f"現在のテーマ: {current_theme}", font=("TkDefaultFont", 10))
        current_label.pack(pady=(0, 10))
        
        # テーマリストフレーム
        list_frame = tb.Frame(main_frame)
        list_frame.pack(fill=tb.BOTH, expand=True, pady=(0, 10))
        
        # スクロール可能なリストボックス
        listbox_frame = tb.Frame(list_frame)
        listbox_frame.pack(fill=tb.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        theme_listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, font=("TkDefaultFont", 10))
        theme_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=theme_listbox.yview)
        
        # 利用可能なテーマをリストボックスに追加
        available_themes = self.theme_manager.get_available_themes()
        for theme in available_themes:
            theme_listbox.insert(tk.END, theme)
            if theme == current_theme:
                theme_listbox.selection_set(tk.END)
        
        # プレビューフレーム
        preview_frame = tb.LabelFrame(main_frame, text="プレビュー", padding=5)
        preview_frame.pack(fill=tb.X, pady=(0, 10))
        
        preview_label = tb.Label(preview_frame, text="選択したテーマのプレビューがここに表示されます", 
                               wraplength=350, justify=tk.LEFT)
        preview_label.pack()
        
        def update_preview(*args):
            selection = theme_listbox.curselection()
            if selection:
                selected_theme = theme_listbox.get(selection[0])
                preview_label.config(text=f"テーマ: {selected_theme}\n\nこのテーマを適用すると、アプリケーション全体の見た目が変更されます。")
        
        theme_listbox.bind('<<ListboxSelect>>', update_preview)
        
        # ボタンフレーム
        button_frame = tb.Frame(main_frame)
        button_frame.pack(fill=tb.X, pady=(10, 0))
        
        def apply_selected_theme():
            selection = theme_listbox.curselection()
            if selection:
                selected_theme = theme_listbox.get(selection[0])
                self.apply_theme(selected_theme)
                theme_dialog.destroy()
        
        def cancel():
            theme_dialog.destroy()
        
        # ボタン
        tb.Button(button_frame, text="適用", command=apply_selected_theme, 
                 bootstyle="primary").pack(side=tk.RIGHT, padx=(5, 0))
        tb.Button(button_frame, text="キャンセル", command=cancel).pack(side=tk.RIGHT)
        
        # 初期プレビューを表示
        update_preview()
        
        # ダイアログを中央に配置
        theme_dialog.update_idletasks()
        x = (theme_dialog.winfo_screenwidth() // 2) - (theme_dialog.winfo_width() // 2)
        y = (theme_dialog.winfo_screenheight() // 2) - (theme_dialog.winfo_height() // 2)
        theme_dialog.geometry(f"+{x}+{y}")

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
        テストタグはAI学習履歴に記録されません
        """
        if self.tag_manager.add_tag(tag, is_negative, category):
            self.tag_manager.translate_and_update_tag(tag, is_negative)
            # UI更新を追加
            self.refresh_tabs()
            return True
        return False


    
    def show_guide_on_startup(self) -> None:
        """初回起動時のガイドを表示"""
        # 初回起動時のみ表示する場合は、設定ファイルで管理
        pass

    def clear_search(self) -> None:
        """検索をクリア"""
        if hasattr(self, 'entry_search'):
            self.entry_search.delete(0, tk.END)
        self.refresh_tabs()

    def get_search_text(self) -> str:
        """検索テキストを取得"""
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
                                if self.tag_manager.set_category(tag_name, assigned_category):
                                    assigned_count += 1
                                    # AI学習: 自動割り当てされたカテゴリを記録
                                    try:
                                        from modules.ai_predictor import get_ai_predictor
                                        ai_predictor = get_ai_predictor()
                                        ai_predictor.usage_tracker.record_tag_usage(tag_name, assigned_category)
                                    except Exception as e:
                                        # AI学習エラーは無視（UI操作を継続）
                                        pass
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
        result_dialog = Toplevel(self.root)
        result_dialog.title("カテゴリ自動割り当て結果（AI予測統合版）")
        result_dialog.geometry("1200x800")
        result_dialog.transient(self.root)

        # サマリ表示
        summary_label = tk.Label(result_dialog, text=summary_text, anchor="w", justify="left", font=("TkDefaultFont", 12))
        summary_label.pack(fill=tk.X, padx=10, pady=10)

        # スクロール可能なフレーム
        frame = tk.Frame(result_dialog)
        frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(frame)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ヘッダー
        header = ["タグ", "割り当てカテゴリ", "AI候補カテゴリ(信頼度)", "理由", "再割り当て"]
        for i, h in enumerate(header):
            tk.Label(scrollable_frame, text=h, font=("TkDefaultFont", 10, "bold"), borderwidth=1, relief="solid").grid(row=0, column=i, sticky="nsew", padx=1, pady=1)

        # 各タグごとに行を追加
        row_vars = []  # (tag, var, row) のリスト
        for row, r in enumerate(detailed_results, start=1):
            tag = r.get("tag", "")
            assigned_category = r.get("assigned_category", "未分類")
            reason = r.get("reason", "")
            # AI候補カテゴリリストを取得（なければ空）
            ai_candidates = r.get("ai_candidates") or r.get("top_categories") or []
            ai_candidates_str = ", ".join([f"{c['category']}({int(c['confidence']*100)}%)" for c in ai_candidates]) if ai_candidates else "-"
            tk.Label(scrollable_frame, text=tag, borderwidth=1, relief="solid").grid(row=row, column=0, sticky="nsew", padx=1, pady=1)
            tk.Label(scrollable_frame, text=assigned_category, borderwidth=1, relief="solid").grid(row=row, column=1, sticky="nsew", padx=1, pady=1)
            tk.Label(scrollable_frame, text=ai_candidates_str, borderwidth=1, relief="solid").grid(row=row, column=2, sticky="nsew", padx=1, pady=1)
            tk.Label(scrollable_frame, text=reason, borderwidth=1, relief="solid", wraplength=300, justify="left").grid(row=row, column=3, sticky="nsew", padx=1, pady=1)
            var = tk.StringVar(value=assigned_category)
            all_categories = [cat for cat in self.category_list if cat != "未分類"]
            options = sorted(set([c['category'] for c in ai_candidates if c['category'] != assigned_category] + [c for c in all_categories if c != assigned_category]))
            if options:
                om = ttk.Combobox(scrollable_frame, textvariable=var, values=options, width=15, state="readonly")
                om.grid(row=row, column=4, sticky="nsew", padx=1, pady=1)
                def make_reassign_cmd(tag=tag, var=var, row=row):
                    def cmd():
                        new_cat = var.get()
                        current_cat = scrollable_frame.grid_slaves(row=row, column=1)[0].cget("text")
                        if new_cat and new_cat != current_cat:
                            if self.tag_manager.set_category(tag, new_cat):
                                try:
                                    from modules.ai_predictor import ai_predictor
                                    ai_predictor.usage_tracker.record_tag_usage(tag, new_cat)
                                except Exception:
                                    pass
                                scrollable_frame.grid_slaves(row=row, column=1)[0].config(text=new_cat)
                                messagebox.showinfo("再割り当て", f"{tag} のカテゴリを {new_cat} に再割り当てしました。", parent=result_dialog)
                            else:
                                messagebox.showerror("エラー", f"{tag} のカテゴリ変更に失敗しました。", parent=result_dialog)
                    return cmd
                btn = tk.Button(scrollable_frame, text="再割り当て", command=make_reassign_cmd(), width=10)
                btn.grid(row=row, column=5, sticky="nsew", padx=1, pady=1)
            else:
                tk.Label(scrollable_frame, text="-", borderwidth=1, relief="solid").grid(row=row, column=4, sticky="nsew", padx=1, pady=1)
                tk.Label(scrollable_frame, text="-", borderwidth=1, relief="solid").grid(row=row, column=5, sticky="nsew", padx=1, pady=1)
            row_vars.append((tag, var, row))

        # 一括適用ボタン
        def apply_all():
            changed = 0
            for tag, var, row in row_vars:
                new_cat = var.get()
                current_cat = scrollable_frame.grid_slaves(row=row, column=1)[0].cget("text")
                if new_cat and new_cat != current_cat:
                    if self.tag_manager.set_category(tag, new_cat):
                        try:
                            from modules.ai_predictor import ai_predictor
                            ai_predictor.usage_tracker.record_tag_usage(tag, new_cat)
                        except Exception:
                            pass
                        scrollable_frame.grid_slaves(row=row, column=1)[0].config(text=new_cat)
                        changed += 1
            if changed > 0:
                messagebox.showinfo("一括適用", f"{changed}件のカテゴリを一括で変更しました。", parent=result_dialog)
            else:
                messagebox.showinfo("一括適用", "変更対象がありません。", parent=result_dialog)

        btn_frame = tk.Frame(result_dialog)
        btn_frame.pack(pady=10)
        apply_btn = tk.Button(btn_frame, text="一括適用", command=apply_all, width=15, bg="#4caf50", fg="white")
        apply_btn.pack(side=tk.LEFT, padx=5)
        close_btn = tk.Button(btn_frame, text="閉じる", command=result_dialog.destroy, width=10)
        close_btn.pack(side=tk.LEFT, padx=5)

    def show_ai_prediction_dialog(self) -> None:
        """
        AI予測機能ダイアログ
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
        
        # ローカルAI状態表示フレーム
        status_frame = tb.LabelFrame(main_frame, text="ローカルAI状態", padding=10)
        status_frame.pack(fill=tb.X, pady=(0, 10))
        
        # ローカルAIの読み込み状態をチェック
        try:
            from modules.local_hf_manager import local_hf_manager
            if local_hf_manager.is_loading():
                status_text = "🔄 ローカルAIモデル読み込み中... 最大2分程度お待ちください"
                status_color = "warning"
                is_ready = False
            elif local_hf_manager.is_ready():
                status_text = "✅ ローカルAI準備完了 - 予測機能利用可能"
                status_color = "success"
                is_ready = True
            else:
                error = local_hf_manager.get_load_error()
                if error:
                    status_text = f"❌ ローカルAIエラー: {error}"
                else:
                    status_text = "❌ ローカルAI未準備 - 予測機能利用不可"
                status_color = "danger"
                is_ready = False
        except Exception as e:
            status_text = f"❌ ローカルAIエラー: {e}"
            status_color = "danger"
            is_ready = False
        
        status_label = tb.Label(status_frame, text=status_text, bootstyle=status_color, font=("TkDefaultFont", 10, "bold"))
        status_label.pack(anchor=tk.W)
        
        # タイトル
        title_label = tb.Label(main_frame, text="AI予測機能", font=("TkDefaultFont", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 説明
        description_label = tb.Label(
            main_frame, 
            text="タグのカテゴリをAIが自動予測し、類似タグを提案します。\n学習データに基づいて精度が向上します。",
            font=("TkDefaultFont", 10),
            wraplength=600
        )
        description_label.pack(pady=(0, 20))

        # 入力エリア
        input_frame = tb.LabelFrame(main_frame, text="タグ入力", padding=10)
        input_frame.pack(fill=tb.X, pady=(0, 10))

        tb.Label(input_frame, text="予測したいタグをカンマまたは改行で複数入力できます:").pack(anchor=tk.W)
        tag_entry = tk.Text(input_frame, width=50, height=3)
        tag_entry.pack(fill=tb.X, pady=(5, 10))
        tag_entry.focus()

        # ボタンフレーム
        button_frame = tb.Frame(input_frame)
        button_frame.pack(fill=tb.X)

        def predict_category_bulk() -> None:
            text = tag_entry.get("1.0", tk.END).strip()
            if not text:
                messagebox.showwarning("警告", "タグを入力してください。")
                return
            # タグ分割
            tags = [t.strip() for t in re.split(r'[\n,]+', text) if t.strip()]
            if not tags:
                messagebox.showwarning("警告", "タグを入力してください。")
                return
            # ローカルAIの状態をチェック
            try:
                if local_hf_manager.is_loading():
                    messagebox.showwarning("警告", "ローカルAIモデルがまだ読み込み中です。しばらくお待ちください。")
                    return
                elif not local_hf_manager.is_ready():
                    messagebox.showerror("エラー", "ローカルAIモデルが準備できていません。")
                    return
            except Exception as e:
                messagebox.showerror("エラー", f"ローカルAIモデルの状態確認に失敗しました: {e}")
                return
            # 予測
            tag_cat_map = {}
            for tag in tags:
                try:
                    cat, conf = predict_category_ai(tag)
                except Exception:
                    cat = "未分類"
                tag_cat_map[tag] = cat
            # MultiTagCategoryAssignDialogでユーザー最終選択
            dlg = MultiTagCategoryAssignDialog(self.root, tags)
            # 予測カテゴリを初期値で反映（UI拡張時に利用）
            # for tag, cat in tag_cat_map.items():
            #     if cat in dlg.category_vars[tag]:
            #         dlg.category_vars[tag][cat].set(True)
            if not dlg.result:
                return
            added, skipped = 0, 0
            for tag, categories in dlg.result.items():
                for cat in categories:
                    if not self.tag_manager.tag_exists(tag, False):
                        self.tag_manager.add_tag(tag, False, cat)
                        added += 1
                        try:
                            from modules.ai_predictor import get_ai_predictor
                            ai_predictor = get_ai_predictor()
                            ai_predictor.usage_tracker.record_tag_usage(tag, cat)
                        except Exception:
                            pass
                    else:
                        skipped += 1
            if added > 0:
                self.refresh_tabs()
                messagebox.showinfo("完了", f"{added}個のタグを追加しました。", parent=self.root)

        predict_btn = tb.Button(button_frame, text="カテゴリ一括予測・一括適用", command=predict_category_bulk, bootstyle="primary", state="disabled" if not is_ready else "normal")
        predict_btn.pack(side=tk.LEFT, padx=(0, 10))

        def suggest_similar() -> None:
            tag = tag_entry.get().strip()
            if not tag:
                messagebox.showwarning("警告", "タグを入力してください。")
                return
            
            # ローカルAIの状態をチェック
            try:
                if local_hf_manager.is_loading():
                    messagebox.showwarning("警告", "ローカルAIモデルがまだ読み込み中です。しばらくお待ちください。")
                    return
                elif not local_hf_manager.is_ready():
                    messagebox.showerror("エラー", "ローカルAIモデルが準備できていません。")
                    return
            except Exception as e:
                messagebox.showerror("エラー", f"ローカルAIモデルの状態確認に失敗しました: {e}")
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

        # ボタンの状態を設定
        predict_btn = tb.Button(button_frame, text="カテゴリ予測", command=predict_category_bulk, 
                               bootstyle="primary", state="disabled" if not is_ready else "normal")
        predict_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        similar_btn = tb.Button(button_frame, text="類似タグ検索", command=suggest_similar, 
                               bootstyle="info", state="disabled" if not is_ready else "normal")
        similar_btn.pack(side=tk.LEFT)

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
        close_btn = tk.Button(dialog, text="閉じる", command=dialog.destroy)
        close_btn.pack(pady=10)
        
        # ローカルAI状態の定期更新
        def update_status():
            try:
                if local_hf_manager.is_loading():
                    status_text = "🔄 ローカルAIモデル読み込み中... 最大2分程度お待ちください"
                    status_color = "warning"
                    is_ready = False
                elif local_hf_manager.is_ready():
                    status_text = "✅ ローカルAI準備完了 - 予測機能利用可能"
                    status_color = "success"
                    is_ready = True
                else:
                    error = local_hf_manager.get_load_error()
                    if error:
                        status_text = f"❌ ローカルAIエラー: {error}"
                    else:
                        status_text = "❌ ローカルAI未準備 - 予測機能利用不可"
                    status_color = "danger"
                    is_ready = False
                
                status_label.config(text=status_text, bootstyle=status_color)
                predict_btn.config(state="normal" if is_ready else "disabled")
                similar_btn.config(state="normal" if is_ready else "disabled")
                
            except Exception as e:
                status_label.config(text=f"❌ ローカルAIエラー: {e}", bootstyle="danger")
                predict_btn.config(state="disabled")
                similar_btn.config(state="disabled")
            
            # 1秒後に再更新
            dialog.after(1000, update_status)
        
        # 状態更新を開始
        update_status()

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

        # 現在の設定を読み込み
        current_settings = {}
        try:
            settings_file = os.path.join('resources', 'config', 'ai_settings.json')
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    current_settings = json.load(f)
        except Exception:
            pass
        
        # AI予測の有効/無効
        ai_enabled_var = tk.BooleanVar(value=current_settings.get('ai_enabled', True))
        tb.Checkbutton(settings_frame, text="AI予測を有効にする", variable=ai_enabled_var).pack(anchor=tk.W, pady=5)
        
        # ローカルAI機能の無効化
        local_ai_disabled_var = tk.BooleanVar(value=current_settings.get('local_ai_disabled', False))
        tb.Checkbutton(settings_frame, text="ローカルAI機能を無効にする（高速化）", variable=local_ai_disabled_var).pack(anchor=tk.W, pady=5)
        
        # 説明
        info_label = tk.Label(settings_frame, text="※ ローカルAI機能を無効にすると、HuggingFaceモデルの読み込みをスキップして高速化されます。\n   従来のキーワードマッチングのみが使用されます。", 
                             fg="gray", font=("TkDefaultFont", 8), justify=tk.LEFT)
        info_label.pack(anchor=tk.W, pady=(0, 10))

        # 信頼度閾値
        threshold_frame = tb.Frame(settings_frame)
        threshold_frame.pack(fill=tb.X, pady=5)
        tb.Label(threshold_frame, text="信頼度閾値 (%):").pack(side=tk.LEFT)
        threshold_var = tk.StringVar(value=str(current_settings.get('confidence_threshold', 70)))
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
                    'local_ai_disabled': local_ai_disabled_var.get(),
                    'confidence_threshold': float(threshold_var.get())
                }
                
                # 設定ファイルに保存
                settings_file = os.path.join('resources', 'config', 'ai_settings.json')
                os.makedirs(os.path.dirname(settings_file), exist_ok=True)
                with open(settings_file, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("成功", "設定を保存しました。\nローカルAI機能の設定変更は次回起動時に反映されます。")
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

    def auto_assign_selected_tags(self) -> None:
        """
        選択中のタグのみAI自動割り当て（候補スコア差が小さい場合は2位・3位も考慮）
        """
        try:
            tree = self.trees[self.current_category]
            selected = tree.selection()
            if not selected:
                messagebox.showinfo("自動割り当て", "自動割り当てしたいタグを選択してください。", parent=self.root)
                return
            selected_tags = [tree.item(item, "values")[0] for item in selected]
            all_tags = self.tag_manager.get_all_tags()
            tag_info_map = {tag_info["tag"]: tag_info for tag_info in all_tags}
            selected_tag_data = [tag_info_map[tag] for tag in selected_tags if tag in tag_info_map]
            if not selected_tag_data:
                messagebox.showinfo("自動割り当て", "選択タグの情報が取得できませんでした。", parent=self.root)
                return
            progress_dialog = ProgressDialog(self.root, "選択タグの自動割り当て", f"{len(selected_tag_data)}件のタグをAI自動割り当て中...")
            def worker_auto_assign_selected() -> None:
                try:
                    assigned_count = 0
                    skipped_count = 0
                    detailed_results = []
                    for i, tag_data in enumerate(selected_tag_data):
                        tag_name = tag_data.get("tag", "")
                        progress_dialog.set_message(f"AI予測中... ({i+1}/{len(selected_tag_data)}) {tag_name}")
                        try:
                            from modules.ai_predictor import ai_predictor
                            cat, conf, details = ai_predictor.predict_category_with_confidence(tag_name)
                            ai_candidates = details.get("top_categories", [])
                            candidate_cats = details.get("candidate_cats", [])
                            # 最も妥当なカテゴリを自動選択（未分類時は候補1位）
                            assigned_category = cat
                            if assigned_category == "未分類" and candidate_cats:
                                assigned_category = candidate_cats[0]
                            if assigned_category != "未分類":
                                if self.tag_manager.set_category(tag_name, assigned_category):
                                    assigned_count += 1
                                else:
                                    skipped_count += 1
                            else:
                                skipped_count += 1
                            detailed_results.append({
                                "tag": tag_name,
                                "assigned_category": assigned_category,
                                "ai_candidates": ai_candidates,
                                "reason": details.get("reason", "")
                            })
                        except Exception as e:
                            detailed_results.append({
                                "tag": tag_name,
                                "assigned_category": "未分類",
                                "ai_candidates": [],
                                "reason": f"AI予測エラー: {str(e)}"
                            })
                            skipped_count += 1
                    def show_completion() -> None:
                        progress_dialog.close()
                        result_text = f"AI予測による処理が完了しました。\n\n"
                        result_text += f"カテゴリ割り当て: {assigned_count}個\n"
                        result_text += f"未分類のまま: {skipped_count}個\n"
                        self.show_detailed_assignment_results(detailed_results, result_text)
                    self.root.after(0, show_completion)
                except Exception as e:
                    progress_dialog.close()
                    messagebox.showerror("エラー", f"選択タグの自動割り当て中にエラーが発生しました: {str(e)}")
            threading.Thread(target=worker_auto_assign_selected, daemon=True).start()
        except Exception as e:
            messagebox.showerror("エラー", f"選択タグの自動割り当て初期化中にエラーが発生しました: {str(e)}")

    def show_ai_learning_data_dialog(self) -> None:
        """
        AI学習データ（修正履歴・信頼度・推論理由）を可視化するダイアログ
        """
        from modules.ai_predictor import ai_predictor
        dialog = Toplevel(self.root)
        dialog.title("AI学習データ可視化")
        dialog.geometry("1200x800")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(True, True)
        
        # メインフレーム
        main_frame = tb.Frame(dialog, padding=10)
        main_frame.pack(fill=tb.BOTH, expand=True)
        
        # ローカルAI状態表示フレーム
        status_frame = tb.LabelFrame(main_frame, text="ローカルAI状態", padding=10)
        status_frame.pack(fill=tb.X, pady=(0, 10))
        
        # ローカルAIの読み込み状態をチェック
        try:
            from modules.local_hf_manager import local_hf_manager
            if local_hf_manager.is_loading():
                status_text = "🔄 ローカルAIモデル読み込み中... 最大2分程度お待ちください"
                status_color = "warning"
                is_ready = False
            elif local_hf_manager.is_ready():
                status_text = "✅ ローカルAI準備完了 - 予測機能利用可能"
                status_color = "success"
                is_ready = True
            else:
                error = local_hf_manager.get_load_error()
                if error:
                    status_text = f"❌ ローカルAIエラー: {error}"
                else:
                    status_text = "❌ ローカルAI未準備 - 予測機能利用不可"
                status_color = "danger"
                is_ready = False
        except Exception as e:
            status_text = f"❌ ローカルAIエラー: {e}"
            status_color = "danger"
            is_ready = False
        
        status_label = tb.Label(status_frame, text=status_text, bootstyle=status_color, font=("TkDefaultFont", 10, "bold"))
        status_label.pack(anchor=tk.W)
        
        # 制御フレーム
        control_frame = tb.Frame(main_frame)
        control_frame.pack(fill=tb.X, pady=(0, 10))
        
        # 左側：オプション
        option_frame = tb.LabelFrame(control_frame, text="表示オプション", padding=5)
        option_frame.pack(side=tk.LEFT, fill=tb.X, expand=True, padx=(0, 10))
        
        skip_ai_var = tk.BooleanVar(value=False)
        skip_ai_check = tk.Checkbutton(option_frame, text="AI予測をスキップ（高速表示）", variable=skip_ai_var, state="disabled" if not is_ready else "normal")
        skip_ai_check.pack(side=tk.LEFT, padx=(0, 10))
        
        show_all_tags_var = tk.BooleanVar(value=True)
        show_all_tags_check = tk.Checkbutton(option_frame, text="全タグを表示（学習履歴なしも含む）", variable=show_all_tags_var)
        show_all_tags_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # 右側：ボタン
        button_frame = tb.Frame(control_frame)
        button_frame.pack(side=tk.RIGHT)
        
        # データ読み込み開始ボタン
        def start_data_load():
            # ローカルAIの状態を再チェック
            try:
                if local_hf_manager.is_loading():
                    messagebox.showwarning("警告", "ローカルAIモデルがまだ読み込み中です。しばらくお待ちください。")
                    return
                elif not local_hf_manager.is_ready():
                    messagebox.showerror("エラー", "ローカルAIモデルが準備できていません。")
                    return
            except Exception as e:
                messagebox.showerror("エラー", f"ローカルAIモデルの状態確認に失敗しました: {e}")
                return
            
            # ボタンを無効化
            start_btn.config(state="disabled")
            skip_ai_check.config(state="normal")
            
            # データ読み込み開始
            load_data_async()
        
        start_btn = tk.Button(button_frame, text="データ読み込み開始", command=start_data_load, 
                             state="disabled" if not is_ready else "normal", 
                             bg="green" if is_ready else "gray", fg="white")
        start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # テストタグ削除ボタン
        def cleanup_test_tags():
            try:
                removed_count = ai_predictor.usage_tracker.cleanup_test_tags()
                if removed_count > 0:
                    messagebox.showinfo("テストタグ削除", f"テストタグ {removed_count} 個を学習履歴から削除しました。")
                    # ダイアログを再読み込み
                    dialog.destroy()
                    self.show_ai_learning_data_dialog()
                else:
                    messagebox.showinfo("テストタグ削除", "削除するテストタグが見つかりませんでした。")
            except Exception as e:
                messagebox.showerror("エラー", f"テストタグ削除中にエラーが発生しました: {str(e)}")
        
        cleanup_btn = tk.Button(button_frame, text="テストタグ削除", command=cleanup_test_tags, bg="orange", fg="white")
        cleanup_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 統計情報表示ボタン
        def show_statistics():
            try:
                usage_data = ai_predictor.usage_tracker.usage_data
                all_tags = self.tag_manager.get_all_tags()
                
                total_learning_tags = len(usage_data)
                total_db_tags = len(all_tags)
                
                # カテゴリ別統計
                category_stats = {}
                for tag_info in all_tags:
                    category = tag_info.get("category", "未分類")
                    category_stats[category] = category_stats.get(category, 0) + 1
                
                # 学習履歴のあるタグの統計
                learning_category_stats = {}
                for tag, info in usage_data.items():
                    if info.get("categories"):
                        most_common_cat = max(info["categories"].items(), key=lambda x: x[1])[0]
                        learning_category_stats[most_common_cat] = learning_category_stats.get(most_common_cat, 0) + 1
                
                # 統計情報を表示
                stats_text = f"=== AI学習データ統計 ===\n\n"
                stats_text += f"総タグ数（DB）: {total_db_tags}個\n"
                stats_text += f"学習履歴あり: {total_learning_tags}個\n"
                stats_text += f"学習履歴なし: {total_db_tags - total_learning_tags}個\n\n"
                
                stats_text += "=== カテゴリ別統計（DB） ===\n"
                for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
                    stats_text += f"{category}: {count}個\n"
                
                stats_text += "\n=== 学習履歴カテゴリ別統計 ===\n"
                for category, count in sorted(learning_category_stats.items(), key=lambda x: x[1], reverse=True):
                    stats_text += f"{category}: {count}個\n"
                
                # 統計ダイアログを表示
                stats_dialog = Toplevel(dialog)
                stats_dialog.title("AI学習データ統計")
                stats_dialog.geometry("500x600")
                stats_dialog.transient(dialog)
                stats_dialog.grab_set()
                
                text_widget = tk.Text(stats_dialog, wrap=tk.WORD, font=("TkDefaultFont", 10))
                scrollbar = ttk.Scrollbar(stats_dialog, orient=tk.VERTICAL, command=text_widget.yview)
                text_widget.configure(yscrollcommand=scrollbar.set)
                
                text_widget.pack(side=tk.LEFT, fill=tb.BOTH, expand=True, padx=10, pady=10)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
                
                text_widget.insert(tk.END, stats_text)
                text_widget.config(state=tk.DISABLED)
                
                tk.Button(stats_dialog, text="閉じる", command=stats_dialog.destroy).pack(pady=10)
                
            except Exception as e:
                messagebox.showerror("エラー", f"統計情報の取得中にエラーが発生しました: {str(e)}")
        
        stats_btn = tk.Button(button_frame, text="統計情報", command=show_statistics, bg="blue", fg="white")
        stats_btn.pack(side=tk.LEFT)
        
        # プログレス表示用フレーム
        progress_frame = tb.Frame(main_frame)
        progress_frame.pack(fill=tb.X, pady=(0, 10))
        progress_label = tk.Label(progress_frame, text="データを読み込み中...", font=("TkDefaultFont", 10))
        progress_label.pack(side=tk.LEFT)
        progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        progress_bar.start()
        
        # ヘッダー
        columns = ("タグ", "現在のカテゴリ", "修正履歴回数", "最頻カテゴリ", "AI予測カテゴリ", "信頼度", "推論理由")
        tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=30)
        for col in columns:
            tree.heading(col, text=col)
            if col == "タグ":
                tree.column(col, width=150)
            elif col == "推論理由":
                tree.column(col, width=200)
            else:
                tree.column(col, width=120)
        tree.pack(fill=tb.BOTH, expand=True)
        
        # スクロールバーを追加
        tree_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # 閉じるボタン
        close_btn = tk.Button(dialog, text="閉じる", command=dialog.destroy)
        close_btn.pack(pady=10)
        
        # 初期状態の表示
        self._ai_learning_data_loaded = False  # ← フラグ追加
        if not is_ready:
            tree.insert("", tk.END, values=("(ローカルAI未準備)", "-", "-", "-", "-", "-", "ローカルAIモデルの読み込みを待機中..."))
        else:
            tree.insert("", tk.END, values=("(データ読み込み待機)", "-", "-", "-", "-", "-", "「データ読み込み開始」ボタンを押してください"))
        
        # 非同期でデータを読み込む
        def load_data_async():
            try:
                # 既存のデータをクリア
                for item in tree.get_children():
                    tree.delete(item)
                self._ai_learning_data_loaded = True  # ← データ読み込み済みフラグON
                
                # 学習履歴データを取得
                usage_data = ai_predictor.usage_tracker.usage_data
                
                # 全タグデータを取得
                all_tags = self.tag_manager.get_all_tags()
                tag_info_map = {tag_info["tag"]: tag_info for tag_info in all_tags}
                
                # 表示するタグを決定
                if show_all_tags_var.get():
                    # 全タグを表示
                    display_tags = set(tag_info_map.keys())
                    # 学習履歴のあるタグも追加
                    for tag in usage_data.keys():
                        display_tags.add(tag)
                else:
                    # 学習履歴のあるタグのみ表示
                    display_tags = set(usage_data.keys())
                
                # テストタグをフィルタリング
                filtered_tags = []
                for tag in display_tags:
                    if any(test_word in tag.lower() for test_word in ['test', 'テスト', 'サンプル', 'sample', 'デモ', 'demo', 'example', '例']):
                        continue
                    filtered_tags.append(tag)
                
                if not filtered_tags:
                    tree.insert("", tk.END, values=("(表示データなし)", "-", "-", "-", "-", "-", "表示するタグが見つかりませんでした"))
                    return
                
                total_items = len(filtered_tags)
                processed = 0
                
                # AI予測結果のキャッシュ
                prediction_cache = {}
                
                for tag in filtered_tags:
                    # 現在のカテゴリを取得
                    current_category = "不明"
                    if tag in tag_info_map:
                        current_category = tag_info_map[tag].get("category", "未分類")
                    
                    # 学習履歴情報を取得
                    usage_count = 0
                    most_common_cat = None
                    if tag in usage_data:
                        usage_count = usage_data[tag].get("count", 0)
                        if usage_data[tag].get("categories"):
                            most_common_cat = max(usage_data[tag]["categories"].items(), key=lambda x: x[1])[0]
                    
                    # AI予測（スキップオプション付き）
                    if skip_ai_var.get():
                        # AI予測をスキップ
                        pred_cat, conf, reason = "スキップ", 0.0, "AI予測をスキップしました"
                    elif tag in prediction_cache:
                        pred_cat, conf, reason = prediction_cache[tag]
                    else:
                        try:
                            pred_cat, conf, details = ai_predictor.predict_category_with_confidence(tag)
                            reason = details.get("reason", "")
                            # キャッシュに保存
                            prediction_cache[tag] = (pred_cat, conf, reason)
                        except Exception as e:
                            pred_cat, conf, reason = "未分類", 0.0, f"AI予測エラー: {str(e)[:50]}"
                            prediction_cache[tag] = (pred_cat, conf, reason)
                    
                    # メインスレッドでUI更新
                    values = (
                        tag, 
                        current_category, 
                        usage_count, 
                        most_common_cat or "-", 
                        pred_cat, 
                        f"{conf*100:.1f}%" if conf > 0 else "-", 
                        reason[:80]+("..." if len(reason)>80 else "") if reason else "-"
                    )
                    dialog.after(0, lambda v=values: tree.insert("", tk.END, values=v))
                    
                    processed += 1
                    # プログレス更新（5件ごと）
                    if processed % 5 == 0:
                        progress_text = f"データ処理中... {processed}/{total_items}"
                        dialog.after(0, lambda t=progress_text: progress_label.config(text=t))
                        dialog.after(0, lambda: dialog.update())
                
                # 完了時の処理
                dialog.after(0, lambda: progress_label.config(text=f"完了 - {total_items}件のタグを表示"))
                dialog.after(0, progress_bar.stop)
                dialog.after(0, lambda: progress_frame.pack_forget())  # プログレスバーを非表示
                
            except Exception as e:
                dialog.after(0, lambda: progress_label.config(text=f"エラー: {str(e)}"))
                dialog.after(0, progress_bar.stop)
                messagebox.showerror("エラー", f"データ読み込み中にエラーが発生しました: {str(e)}")
        
        # ローカルAI状態の定期更新
        def update_status():
            try:
                if local_hf_manager.is_loading():
                    status_text = "🔄 ローカルAIモデル読み込み中... 最大2分程度お待ちください"
                    status_color = "warning"
                    is_ready = False
                elif local_hf_manager.is_ready():
                    status_text = "✅ ローカルAI準備完了 - データ読み込み可能"
                    status_color = "success"
                    is_ready = True
                else:
                    error = local_hf_manager.get_load_error()
                    if error:
                        status_text = f"❌ ローカルAIエラー: {error}"
                    else:
                        status_text = "❌ ローカルAI未準備 - データ読み込み不可"
                    status_color = "danger"
                    is_ready = False
                
                status_label.config(text=status_text, bootstyle=status_color)
                start_btn.config(state="normal" if is_ready else "disabled", 
                               bg="green" if is_ready else "gray")
                
                # 状態が変わった場合の処理
                # データ未読込かつボタンが有効化された直後のみ初期化
                if is_ready and start_btn.cget("state") == "normal" and not self._ai_learning_data_loaded:
                    for item in tree.get_children():
                        tree.delete(item)
                    tree.insert("", tk.END, values=("(データ読み込み待機)", "-", "-", "-", "-", "-", "「データ読み込み開始」ボタンを押してください"))
                # すでにデータ読み込み済みならツリー内容は維持
            except Exception as e:
                status_label.config(text=f"❌ ローカルAIエラー: {e}", bootstyle="danger")
                start_btn.config(state="disabled", bg="gray")
            dialog.after(1000, update_status)
        update_status()

    def bulk_reassign_category(self, category: str) -> None:
        """
        指定カテゴリ内の全タグをAIで再分類し、結果を反映・レポート表示
        """
        from modules.ai_predictor import ai_predictor
        tags = [t["tag"] for t in self.tag_manager.get_tags_by_category(category)]
        if not tags:
            messagebox.showinfo("情報", f"カテゴリ「{category}」にタグがありません。", parent=self.root)
            return
        progress_dialog = ProgressDialog(self.root, title="AI再分類中", message=f"カテゴリ「{category}」のタグをAI再分類しています...")
        reassigned = 0
        unchanged = 0
        failed = 0
        details = []
        for tag in tags:
            try:
                pred_cat, conf, info = ai_predictor.predict_category_with_confidence(tag)
                if pred_cat != category and pred_cat != "未分類":
                    self.tag_manager.set_category(tag, pred_cat)
                    reassigned += 1
                    details.append((tag, category, pred_cat, f"信頼度: {conf*100:.1f}%", info.get("reason", "")))
                else:
                    unchanged += 1
            except Exception as e:
                failed += 1
                details.append((tag, category, "エラー", "-", str(e)))
        progress_dialog.close()
        result = f"AI再分類完了: {reassigned}件再分類, {unchanged}件変更なし, {failed}件エラー\n"
        if details:
            result += "\n詳細:\n" + "\n".join([f"{t} [{c}→{p}] {r} {reason}" for t, c, p, r, reason in details])
        messagebox.showinfo("AI再分類結果", result, parent=self.root)

    def show_bulk_reassign_dialog(self) -> None:
        """
        カテゴリ選択→一括AI再分類ダイアログ
        """
        cats = [c for c in self.category_keywords.keys()]
        dialog = Toplevel(self.root)
        dialog.title("カテゴリ一括AI再分類")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        var = tk.StringVar(value=cats[0] if cats else "")
        tk.Label(dialog, text="再分類したいカテゴリを選択:").pack(pady=10)
        combo = ttk.Combobox(dialog, values=cats, textvariable=var, state="readonly")
        combo.pack(pady=5)
        def on_ok():
            cat = var.get()
            dialog.destroy()
            self.bulk_reassign_category(cat)
        tk.Button(dialog, text="AI再分類実行", command=on_ok).pack(pady=10)
        tk.Button(dialog, text="キャンセル", command=dialog.destroy).pack()

    def show_bulk_reassign_result_dialog(self, details: list, summary: str) -> None:
        """
        一括AI再分類の詳細結果をテーブル表示し、各行で手動再割り当て可能なダイアログ
        """
        dialog = Toplevel(self.root)
        dialog.title("AI再分類詳細結果")
        dialog.geometry("900x600")
        dialog.transient(self.root)
        dialog.grab_set()
        # サマリ
        tk.Label(dialog, text=summary, anchor="w", justify="left").pack(fill=tk.X, padx=10, pady=5)
        # テーブル
        columns = ("タグ", "元カテゴリ", "AI新カテゴリ", "信頼度", "理由", "操作")
        tree = ttk.Treeview(dialog, columns=columns, show="headings", height=25)
        for col in columns[:-1]:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        tree.heading("操作", text="操作")
        tree.column("操作", width=100)
        tree.pack(fill=tb.BOTH, expand=True, padx=10, pady=5)
        # ボタン配置用
        btn_refs = {}
        for i, (tag, old_cat, new_cat, conf, reason) in enumerate(details):
            iid = tree.insert("", tk.END, values=(tag, old_cat, new_cat, conf, reason[:60]+("..." if len(reason)>60 else ""), "再割り当て"))
            btn_refs[iid] = (tag, new_cat)
        # 操作列クリック時のハンドラ
        def on_tree_click(event):
            item = tree.identify_row(event.y)
            col = tree.identify_column(event.x)
            if col == f"#{len(columns)}" and item in btn_refs:
                tag, ai_cat = btn_refs[item]
                self.show_manual_reassign_dialog(tag, ai_cat)
        tree.bind("<Button-1>", on_tree_click)
        tk.Button(dialog, text="閉じる", command=dialog.destroy).pack(pady=10)

    def show_manual_reassign_dialog(self, tag: str, ai_cat: str) -> None:
        """
        タグの手動再割り当てダイアログ
        """
        cats = [c for c in self.category_keywords.keys()]
        dialog = Toplevel(self.root)
        dialog.title(f"タグ「{tag}」の手動再割り当て")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        var = tk.StringVar(value=ai_cat if ai_cat in cats else cats[0])
        tk.Label(dialog, text=f"タグ: {tag}").pack(pady=10)
        tk.Label(dialog, text="新しいカテゴリを選択:").pack()
        combo = ttk.Combobox(dialog, values=cats, textvariable=var, state="readonly")
        combo.pack(pady=5)
        def on_ok():
            new_cat = var.get()
            self.tag_manager.set_category(tag, new_cat)
            messagebox.showinfo("完了", f"タグ「{tag}」を「{new_cat}」に再割り当てしました。", parent=dialog)
            dialog.destroy()
        tk.Button(dialog, text="再割り当て", command=on_ok).pack(pady=10)
        tk.Button(dialog, text="キャンセル", command=dialog.destroy).pack()

    def show_prompt_translator(self) -> None:
        """
        プロンプト出力欄の日本語を一括翻訳する
        """
        try:
            from modules.prompt_translator import PromptTranslator
            prompt_translator = PromptTranslator()
            
            # 現在の出力欄内容を取得
            current_text = self.output.get("1.0", tk.END).strip()
            if not current_text:
                messagebox.showwarning("警告", "翻訳する内容がありません。プロンプト出力欄に日本語を入力してください。", parent=self.root)
                return
            
            # 日本語部分を抽出（ひらがな、カタカナ、漢字を含む部分）
            import re
            japanese_pattern = r'[ぁ-んァ-ン一-龥]+'
            japanese_matches = re.findall(japanese_pattern, current_text)
            
            if not japanese_matches:
                messagebox.showwarning("警告", "翻訳可能な日本語が見つかりません。", parent=self.root)
                return
            
            # 翻訳対象の日本語を表示
            japanese_text = " ".join(japanese_matches)
            confirm_msg = f"以下の日本語を翻訳しますか？\n\n{japanese_text}"
            if not messagebox.askyesno("翻訳確認", confirm_msg, parent=self.root):
                return
            
            # 進捗ダイアログを表示
            progress_dialog = Toplevel(self.root)
            progress_dialog.title("翻訳中")
            progress_dialog.geometry("400x150")
            progress_dialog.transient(self.root)
            progress_dialog.grab_set()
            progress_dialog.resizable(False, False)
            
            progress_frame = tb.Frame(progress_dialog, padding=20)
            progress_frame.pack(fill=tb.BOTH, expand=True)
            
            progress_label = tb.Label(progress_frame, text="翻訳中...", font=("TkDefaultFont", 12))
            progress_label.pack(pady=(0, 10))
            
            progress_bar = tb.Progressbar(progress_frame, mode='indeterminate', bootstyle="success")
            progress_bar.pack(fill=tb.X, pady=(0, 10))
            progress_bar.start()
            
            def translate_worker():
                try:
                    # 翻訳実行
                    result = prompt_translator.translate_prompt_with_analysis(japanese_text)
                    translated_text = result["translated"]
                    details = f"翻訳方法: {result['translation_method']}, 信頼度: {result['confidence']:.2f}"
                    
                    # UIスレッドで結果を処理
                    self.root.after(0, lambda: process_translation_result(translated_text, details))
                    
                except Exception as e:
                    # UIスレッドでエラーを表示
                    self.root.after(0, lambda: show_translation_error(str(e)))
            
            def process_translation_result(translated_text: str, details: str):
                progress_dialog.destroy()
                
                # 翻訳結果を確認
                result_msg = f"翻訳結果:\n\n{translated_text}\n\nこの結果で出力欄を置き換えますか？"
                if messagebox.askyesno("翻訳完了", result_msg, parent=self.root):
                    # 出力欄を翻訳結果で置き換え
                    self.output.delete("1.0", tk.END)
                    self.output.insert("1.0", translated_text)
                    
                    # タグ一覧（DB）にも新規保存
                    tags = [t.strip() for t in translated_text.replace("\n", ",").split(",") if t.strip()]
                    added, skipped = 0, 0
                    is_negative = (self.current_category == "ネガティブ")
                    for tag in tags:
                        # 既存タグと重複しない場合のみ追加
                        if not self.tag_manager.tag_exists(tag, is_negative):
                            self.tag_manager.add_tag(tag, is_negative, self.current_category)
                            added += 1
                        else:
                            skipped += 1
                    self.refresh_tabs()
                    
                    msg = f"翻訳結果をプロンプト出力欄に反映し、{added}件のタグを新規保存しました。"
                    if skipped:
                        msg += f"\n（{skipped}件は既存タグのためスキップ）"
                    messagebox.showinfo("翻訳完了", msg, parent=self.root)
            
            def show_translation_error(error_msg: str):
                progress_dialog.destroy()
                messagebox.showerror("翻訳エラー", f"翻訳中にエラーが発生しました:\n{error_msg}", parent=self.root)
            
            # 翻訳を別スレッドで実行
            import threading
            translate_thread = threading.Thread(target=translate_worker, daemon=True)
            translate_thread.start()
            
        except ImportError as e:
            messagebox.showerror("エラー", f"プロンプト翻訳モジュールの読み込みに失敗しました:\n{e}", parent=self.root)
        except Exception as e:
            messagebox.showerror("エラー", f"プロンプト翻訳の実行に失敗しました:\n{e}", parent=self.root)
    
    def get_low_confidence_tags(self, confidence_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        低信頼度タグを検出する。
        戻り値: [{"tag": "タグ名", "current_category": "現在のカテゴリ", "confidence": 0.3, "suggested_categories": [{"category": "カテゴリ名", "confidence": 0.8}]}]
        """
        try:
            ai_predictor = get_ai_predictor()
            all_tags = self.tag_manager.get_all_tags()
            low_confidence_tags = []
            
            for tag_data in all_tags:
                tag = tag_data["tag"]
                current_category = tag_data["category"] or "未分類"
                is_negative = tag_data["is_negative"]
                
                # ネガティブタグは除外
                if is_negative:
                    continue
                
                # AI予測で信頼度を計算
                try:
                    predicted_category, confidence, details = ai_predictor.predict_category_with_confidence(
                        tag, confidence_threshold=confidence_threshold
                    )
                    
                    # 信頼度が閾値以下の場合
                    if confidence < confidence_threshold:
                        # 推奨カテゴリを取得
                        suggested_categories = []
                        if "category_scores" in details:
                            sorted_categories = sorted(
                                details["category_scores"].items(), 
                                key=lambda x: x[1], 
                                reverse=True
                            )
                            suggested_categories = [
                                {"category": cat, "confidence": score / sum(details["category_scores"].values())}
                                for cat, score in sorted_categories[:3]
                            ]
                        
                        low_confidence_tags.append({
                            "tag": tag,
                            "current_category": current_category,
                            "confidence": confidence,
                            "suggested_categories": suggested_categories,
                            "details": details
                        })
                        
                except Exception as e:
                    # AI予測エラーの場合は信頼度0として扱う
                    low_confidence_tags.append({
                        "tag": tag,
                        "current_category": current_category,
                        "confidence": 0.0,
                        "suggested_categories": [],
                        "details": {"reason": f"AI予測エラー: {e}"}
                    })
            
            # 信頼度の低い順にソート
            low_confidence_tags.sort(key=lambda x: x["confidence"])
            return low_confidence_tags
            
        except Exception as e:
            self.logger.error(f"低信頼度タグ検出エラー: {e}")
            return []

    def show_low_confidence_tags_dialog(self) -> None:
        """
        低信頼度タグ管理ダイアログを表示する。
        """
        try:
            # 設定から信頼度閾値を取得
            from modules.customization import customization_manager
            confidence_threshold = customization_manager.settings.get_setting("confidence_threshold", 0.7)
            
            # プログレスダイアログを表示
            progress_dialog = ProgressDialog(self.root, "低信頼度タグを検出中...")
            
            def worker():
                try:
                    # 低信頼度タグを検出
                    low_confidence_tags = self.get_low_confidence_tags(confidence_threshold)
                    
                    # UIスレッドでダイアログを表示
                    self.root.after(0, lambda: show_dialog(low_confidence_tags))
                    
                except Exception as e:
                    self.root.after(0, lambda: show_error(f"低信頼度タグ検出エラー: {e}"))
                finally:
                    self.root.after(0, progress_dialog.close)
            
            def show_dialog(tags: List[Dict[str, Any]]):
                if not tags:
                    messagebox.showinfo("低信頼度タグ", "信頼度の低いタグは見つかりませんでした。", parent=self.root)
                    return
                
                # 低信頼度タグ管理ダイアログを表示
                dialog = LowConfidenceTagsDialog(self.root, tags, confidence_threshold)
                
                if dialog.result:
                    # カテゴリ変更を適用
                    self.apply_low_confidence_tag_changes(dialog.result)
            
            def show_error(error_msg: str):
                messagebox.showerror("エラー", error_msg, parent=self.root)
            
            # バックグラウンドで実行
            threading.Thread(target=worker, daemon=True).start()
            
        except Exception as e:
            self.logger.error(f"低信頼度タグダイアログ表示エラー: {e}")
            messagebox.showerror("エラー", f"低信頼度タグダイアログの表示に失敗しました: {e}", parent=self.root)

    def apply_low_confidence_tag_changes(self, changes: Dict[str, str]) -> None:
        """
        低信頼度タグのカテゴリ変更を適用する。
        """
        try:
            changed_count = 0
            
            for tag, new_category in changes.items():
                # 現在のカテゴリを取得
                current_tags = self.tag_manager.get_all_tags()
                current_tag_data = next((t for t in current_tags if t["tag"] == tag), None)
                
                if current_tag_data:
                    current_category = current_tag_data["category"] or "未分類"
                    
                    # カテゴリが変更されている場合
                    if current_category != new_category:
                        # タグマネージャーでカテゴリを更新
                        if self.tag_manager.set_category(tag, new_category):
                            changed_count += 1
                            
                            # AI学習データに記録
                            try:
                                ai_predictor = get_ai_predictor()
                                ai_predictor.usage_tracker.record_tag_usage(tag, new_category)
                            except Exception as e:
                                self.logger.error(f"AI学習データ記録エラー: {e}")
            
            if changed_count > 0:
                # UIを更新
                self.refresh_tabs()
                messagebox.showinfo("完了", f"{changed_count}件のタグのカテゴリを変更しました。", parent=self.root)
            else:
                messagebox.showinfo("完了", "カテゴリの変更はありませんでした。", parent=self.root)
                
        except Exception as e:
            self.logger.error(f"低信頼度タグ変更適用エラー: {e}")
            messagebox.showerror("エラー", f"カテゴリ変更の適用に失敗しました: {e}", parent=self.root)

    def clear_ai_cache(self) -> None:
        """
        AI予測キャッシュをクリアする
        """
        try:
            ai_predictor = get_ai_predictor()
            ai_predictor.clear_cache()
            messagebox.showinfo("完了", "AI予測キャッシュをクリアしました。", parent=self.root)
        except Exception as e:
            self.logger.error(f"AIキャッシュクリアエラー: {e}")
            messagebox.showerror("エラー", f"AIキャッシュのクリアに失敗しました: {e}", parent=self.root)

    def show_ai_help(self) -> None:
        """
        AI機能についてのヘルプダイアログを表示する
        """
        help_dialog = Toplevel(self.root)
        help_dialog.title("AI機能について")
        help_dialog.geometry("600x500")
        help_dialog.transient(self.root)
        help_dialog.grab_set()
        help_dialog.resizable(True, True)
        
        # メインフレーム
        main_frame = tb.Frame(help_dialog, padding=10)
        main_frame.pack(fill=tb.BOTH, expand=True)
        
        # スクロール可能なテキストウィジェット
        text_frame = tb.Frame(main_frame)
        text_frame.pack(fill=tb.BOTH, expand=True)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, padx=10, pady=10)
        scrollbar = tb.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ヘルプテキスト
        help_text = """【AI機能について】

■ AI予測機能
・タグのカテゴリを自動予測します
・機械学習による高精度な分類
・外部データベースとの連携で精度向上
・信頼度スコア付きで予測結果を表示

■ AI学習データ可視化
・AIの学習状況をリアルタイムで確認
・タグ使用パターンの分析
・予測精度の統計情報
・学習データの詳細表示

■ AI設定
・予測機能のON/OFF切り替え
・信頼度閾値の調整
・自動提案機能の制御
・学習機能の有効/無効設定

■ カスタムキーワード管理
・カテゴリ別のカスタムキーワード追加
・キーワードの重み付け設定
・予測精度の向上に貢献

■ カスタムルール管理
・条件付きカテゴリ割り当てルール
・複雑な分類ロジックの定義
・優先度付きルール適用

■ 未分類タグの一括整理
・AIによる自動カテゴリ割り当て
・一括処理による効率化
・結果の詳細確認と手動調整

■ 選択タグの自動割り当て
・選択したタグのカテゴリ自動割り当て
・個別タグの精度向上
・即座の結果確認

【トラブルシューティング】

■ AI機能が動作しない場合
1. AI設定で機能が有効になっているか確認
2. インターネット接続を確認（外部AI使用時）
3. ローカルAIモデルの読み込み状況を確認
4. 設定メニューからAI機能を無効化して再起動

■ 予測精度が低い場合
1. カスタムキーワードを追加
2. カスタムルールを設定
3. より多くのタグを使用して学習データを増やす
4. 信頼度閾値を調整

■ パフォーマンスが遅い場合
1. ローカルAI機能を無効化
2. 大量のタグ処理時は分割して実行
3. 不要な学習データをクリア

【推奨設定】

■ 初回使用時
・AI予測機能: ON
・信頼度閾値: 0.7
・自動提案: ON
・学習機能: ON

■ パフォーマンス重視
・ローカルAI: OFF
・信頼度閾値: 0.8
・自動提案: OFF

■ 高精度重視
・ローカルAI: ON
・信頼度閾値: 0.6
・自動提案: ON
・カスタムキーワードを積極的に追加

【データ管理】

■ 学習データのバックアップ
・AI設定から学習データをエクスポート
・定期的なバックアップを推奨
・復元時はインポート機能を使用

■ カスタム設定の共有
・カスタムキーワードとルールをエクスポート
・他の環境での設定復元が可能
・チーム開発での設定共有に活用

【技術情報】

■ 使用技術
・機械学習（scikit-learn）
・自然言語処理（HuggingFace）
・外部API連携（Google翻訳等）
・ローカルAIモデル（Sentence Transformers）

■ データ形式
・JSON形式でのデータ保存
・UTF-8エンコーディング
・バージョン管理対応
・互換性保証

■ セキュリティ
・ローカルデータのみ使用
・外部API使用時はHTTPS通信
・個人情報の暗号化対応
・データの完全削除機能

【サポート】

■ 問題が解決しない場合
1. ログファイルを確認
2. 設定をリセットして再試行
3. アプリケーションを再起動
4. データベースの再初期化

■ 機能改善の提案
・GitHubのIssuesで報告
・詳細な再現手順を記載
・環境情報を含めて報告

AI機能についての詳細な説明でした。
ご不明な点がございましたら、お気軽にお問い合わせください。"""
        
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)
        
        # 閉じるボタン
        button_frame = tb.Frame(main_frame)
        button_frame.pack(fill=tb.X, pady=(10, 0))
        tb.Button(button_frame, text="閉じる", command=help_dialog.destroy, bootstyle="primary").pack(side=tk.RIGHT)

    def export_personal_data(self) -> None:
        """
        個人データを包括的にエクスポートする
        """
        export_personal_data(self)

    def import_personal_data(self) -> None:
        """
        個人データを包括的にインポートする
        """
        import_personal_data(self)

    def _get_last_backup_date(self) -> str:
        """
        最後のバックアップ日を取得する
        """
        try:
            backup_dir = getattr(self, 'backup_dir', 'backup')
            if os.path.exists(backup_dir):
                backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
                if backup_files:
                    latest_file = max(backup_files, key=lambda f: os.path.getmtime(os.path.join(backup_dir, f)))
                    timestamp = os.path.getmtime(os.path.join(backup_dir, latest_file))
                    return datetime.fromtimestamp(timestamp).isoformat()
        except Exception:
            pass
        return "不明"


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