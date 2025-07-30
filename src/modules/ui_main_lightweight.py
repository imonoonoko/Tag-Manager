# -*- coding: utf-8 -*-
"""
軽量化されたメインUIモジュール
"""
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import simpledialog, messagebox, Menu, filedialog, Toplevel
import tkinter as tk
from tkinter import ttk
import threading
import os
import json
import time
import logging
from typing import Any, Dict, List, Optional, Callable, cast, Tuple
import queue

from modules.constants import category_keywords, DB_FILE, TRANSLATING_PLACEHOLDER, auto_assign_category
from modules.theme_manager import ThemeManager
from modules.tag_manager import TagManager
from modules.dialogs import CategorySelectDialog, BulkCategoryDialog
from modules.ai_predictor import predict_category_ai, suggest_similar_tags_ai
from modules.customization import get_customized_category_keywords, apply_custom_rules

# 分離されたモジュールからインポート
from modules.ui_dialogs import ProgressDialog, ToolTip, show_help_dialog, show_about_dialog, show_license_info_dialog, show_shortcuts_dialog
from modules.ui_export_import import export_personal_data, import_personal_data, export_tags, export_all_tags, backup_database
from modules.ui_ai_features import (
    show_ai_prediction_dialog, show_ai_settings_dialog, show_custom_keywords_dialog,
    show_custom_rules_dialog, show_ai_learning_data_dialog, show_ai_help_dialog,
    auto_assign_selected_tags, auto_assign_uncategorized_tags
)
from modules.ui_utils import (
    build_category_list, build_category_descriptions, filter_tags_optimized,
    sort_prompt_by_priority, format_output_text, strip_weight_from_tag,
    is_float, extract_tags_from_prompt, make_theme_menu_command,
    make_set_category_command, make_export_tags_command, make_show_context_menu_event,
    make_set_status_clear, make_set_progress_message, make_close_progress_dialog,
    worker_thread_fetch, show_guide_on_startup, clear_search, get_search_text
)

class TagManagerApp:
    def __init__(self, root: Any, db_file: Optional[str] = None) -> None:
        self.root = root
        self.theme_manager = ThemeManager()
        
        # 絶対パスでデータベースファイルを指定
        db_path = db_file or os.path.join(os.path.dirname(__file__), '..', 'data', 'tags.db')
        self.tag_manager = TagManager(db_file=db_path, parent=self.root)
        self.tag_manager.invalidate_cache()
        
        # 基本変数の初期化
        self.q: queue.Queue[Any] = queue.Queue()
        self.search_timer: Optional[str] = None
        self.refresh_debounce_id: Optional[str] = None
        self.status_var = tk.StringVar(value="準備完了")
        self.output_tags_data: List[Dict[str, Any]] = []
        self.selected_tags: List[str] = []
        self.weight_values: Dict[str, float] = {}
        self.newly_added_tags: List[str] = []
        
        # カテゴリと設定の読み込み
        self.load_categories()
        self.load_prompt_structure_priorities()
        self.load_category_descriptions()
        
        # カテゴリリストの構築
        self.category_list = build_category_list(self.category_keywords)
        self.current_category = "全カテゴリ"
        
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
        
        # コールバック関数の設定
        self.setup_callbacks()
        
        # UI構築と初期化
        self.setup_ui()
        self.process_queue()
        self.refresh_tabs()
        show_guide_on_startup(self)

    def setup_callbacks(self) -> None:
        """コールバック関数を設定"""
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

    def load_categories(self) -> None:
        """カテゴリを読み込み"""
        try:
            with open(os.path.join('resources', 'config', 'categories.json'), 'r', encoding='utf-8') as f:
                self.category_keywords = json.load(f)
        except Exception as e:
            self.logger.error(f"categories.jsonの読み込みに失敗しました: {e}")
            messagebox.showerror("エラー", f"カテゴリ定義ファイルの読み込みに失敗しました:\n{e}", parent=self.root)
            self.category_keywords = {}

    def load_prompt_structure_priorities(self) -> None:
        """プロンプト構造優先度を読み込み"""
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
        """カテゴリ説明を読み込み"""
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

    def setup_ui(self) -> None:
        """UIを構築"""
        self.trees = {}
        self.root.title("タグ管理ツール")
        self.root.geometry("1200x600")
        self.root.resizable(True, True)
        self.root.minsize(1200, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # テーマの適用
        style = tb.Style()
        style.theme_use(self.theme_manager.current_theme)

        # メニューバーの構築
        self.setup_menubar()
        
        # メインUIの構築
        self.setup_main_ui()

    def setup_menubar(self) -> None:
        """メニューバーを構築"""
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        # ファイルメニュー
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="終了", command=self.on_closing)

        # 編集メニュー
        edit_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="編集", menu=edit_menu)
        edit_menu.add_command(label="コピー", command=self.copy_to_clipboard)

        # AIメニュー
        ai_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="AI", menu=ai_menu)
        ai_menu.add_command(label="AI予測機能", command=self.show_ai_prediction_dialog)
        ai_menu.add_command(label="AI学習データ可視化", command=self.show_ai_learning_data_dialog)
        ai_menu.add_command(label="AI設定", command=self.show_ai_settings_dialog)
        ai_menu.add_command(label="カスタムキーワード", command=self.show_custom_keywords_dialog)
        ai_menu.add_command(label="カスタムルール", command=self.show_custom_rules_dialog)
        ai_menu.add_separator()
        ai_menu.add_command(label="選択タグをAI自動割り当て", command=self.auto_assign_selected_tags)
        ai_menu.add_command(label="未分類タグを一括自動割り当て", command=self.auto_assign_uncategorized_tags)
        ai_menu.add_command(label="AI機能について", command=self.show_ai_help)

        # ツールメニュー
        tools_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ツール", menu=tools_menu)
        tools_menu.add_command(label="プロンプト翻訳", command=self.show_prompt_translator)
        tools_menu.add_command(label="ショートカット一覧", command=lambda: show_shortcuts_dialog(self.root))

        # 設定メニュー
        settings_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="設定", menu=settings_menu)
        settings_menu.add_command(label="テーマ切替", command=self.show_theme_dialog)
        settings_menu.add_command(label="データベースバックアップ", command=lambda: backup_database(self))
        settings_menu.add_separator()
        settings_menu.add_command(label="個人データエクスポート", command=lambda: export_personal_data(self))
        settings_menu.add_command(label="個人データインポート", command=lambda: import_personal_data(self))

        # ヘルプメニュー
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="使い方", command=lambda: show_help_dialog(self.root))
        help_menu.add_command(label="バージョン情報", command=lambda: show_about_dialog(self.root))
        help_menu.add_command(label="ライセンス情報", command=lambda: show_license_info_dialog(self.root))

    def setup_main_ui(self) -> None:
        """メインUIを構築"""
        # メインフレーム
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左側のパネル
        left_panel = tk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 検索フレーム
        search_frame = tk.Frame(left_panel)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(search_frame, text="検索:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(5, 5))
        search_entry.bind('<KeyRelease>', self.on_search_change)
        
        # カテゴリ選択
        tk.Label(search_frame, text="カテゴリ:").pack(side=tk.LEFT, padx=(10, 0))
        self.category_var = tk.StringVar(value="全カテゴリ")
        category_combo = ttk.Combobox(search_frame, textvariable=self.category_var, values=self.category_list, width=15)
        category_combo.pack(side=tk.LEFT, padx=(5, 0))
        category_combo.bind('<<ComboboxSelected>>', self.on_category_select)
        
        # タグ一覧
        self.setup_tag_tree(left_panel)
        
        # 右側のパネル
        right_panel = tk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        
        # プロンプト出力エリア
        self.setup_output_area(right_panel)
        
        # 重み設定エリア
        self.setup_weight_area(right_panel)
        
        # ボタンエリア
        self.setup_button_area(right_panel)

    def setup_tag_tree(self, parent: Any) -> None:
        """タグツリーを設定"""
        tree_frame = tk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview
        columns = ("タグ", "日本語", "お気に入り", "カテゴリ")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        
        # スクロールバー
        tree_scrollbar = tk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # イベントバインド
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.tree.bind('<Double-1>', self.on_tree_double_click)
        self.tree.bind('<Button-3>', lambda e: self.show_context_menu(e, self.tree))

    def setup_output_area(self, parent: Any) -> None:
        """出力エリアを設定"""
        output_frame = tk.LabelFrame(parent, text="プロンプト出力", padx=5, pady=5)
        output_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.output_text = tk.Text(output_frame, wrap=tk.WORD, height=15)
        output_scrollbar = tk.Scrollbar(output_frame, orient=tk.VERTICAL, command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=output_scrollbar.set)
        
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        output_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_weight_area(self, parent: Any) -> None:
        """重み設定エリアを設定"""
        weight_frame = tk.LabelFrame(parent, text="重み設定", padx=5, pady=5)
        weight_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(weight_frame, text="重み:").pack(side=tk.LEFT)
        self.weight_var = tk.DoubleVar(value=1.0)
        weight_scale = tk.Scale(weight_frame, from_=0.1, to=2.0, resolution=0.1, 
                               orient=tk.HORIZONTAL, variable=self.weight_var, 
                               command=self.update_weight, length=200)
        weight_scale.pack(side=tk.LEFT, padx=(5, 10))
        
        self.weight_value_label = tk.Label(weight_frame, text="1.0")
        self.weight_value_label.pack(side=tk.LEFT)
        
        self.label_weight_display = tk.Label(weight_frame, text="", fg="gray")
        self.label_weight_display.pack(side=tk.LEFT, padx=(10, 0))

    def setup_button_area(self, parent: Any) -> None:
        """ボタンエリアを設定"""
        button_frame = tk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 基本操作ボタン
        basic_frame = tk.Frame(button_frame)
        basic_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Button(basic_frame, text="追加", command=self.add_to_output).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(basic_frame, text="クリア", command=self.clear_output).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(basic_frame, text="コピー", command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=(0, 5))
        
        # タグ操作ボタン
        tag_frame = tk.Frame(button_frame)
        tag_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Button(tag_frame, text="お気に入り", command=self.toggle_favorite).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(tag_frame, text="削除", command=self.delete_tag).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(tag_frame, text="カテゴリ変更", command=self.bulk_category_change).pack(side=tk.LEFT, padx=(0, 5))
        
        # ステータスバー
        status_frame = tk.Frame(parent)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = tk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X)

    # イベントハンドラー
    def on_closing(self) -> None:
        """アプリケーション終了時の処理"""
        self.root.destroy()

    def on_search_change(self, *args: Any) -> None:
        """検索テキスト変更時の処理"""
        if self.search_timer:
            self.root.after_cancel(self.search_timer)
        
        def delayed_search():
            filter_text = self.search_var.get()
            category = self.category_var.get()
            self.refresh_tabs()
        
        self.search_timer = self.root.after(300, delayed_search)

    def on_category_select(self, event: Any) -> None:
        """カテゴリ選択時の処理"""
        self.current_category = self.category_var.get()
        self.refresh_tabs()

    def on_tree_select(self, event: Any) -> None:
        """ツリー選択時の処理"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            tag = item['values'][0]
            self.selected_tags = [tag]
            self.status_var.set(f"選択: {tag}")

    def on_tree_double_click(self, event: Any) -> None:
        """ツリーダブルクリック時の処理"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            tag = item['values'][0]
            self.add_to_output()

    # 基本機能
    def refresh_tabs(self) -> None:
        """タブを更新"""
        filter_text = self.search_var.get()
        category = self.category_var.get()
        
        # 非同期でタグを取得
        thread = threading.Thread(
            target=worker_thread_fetch,
            args=(self, self.q, filter_text, category)
        )
        thread.daemon = True
        thread.start()

    def add_to_output(self, event: Optional[Any] = None) -> None:
        """出力に追加"""
        if not self.selected_tags:
            return
        
        tag = self.selected_tags[0]
        weight = self.weight_var.get()
        
        # 重複チェック
        for item in self.output_tags_data:
            if item["tag"] == tag:
                item["weight"] = weight
                break
        else:
            self.output_tags_data.append({
                "tag": tag,
                "weight": weight,
                "category": self.current_category
            })
        
        # 出力テキストを更新
        sorted_data = sort_prompt_by_priority(self.output_tags_data, self.prompt_structure_priorities)
        output_text = format_output_text(sorted_data)
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(1.0, output_text)
        
        self.refresh_weight_display()

    def clear_output(self) -> None:
        """出力をクリア"""
        self.output_text.delete(1.0, tk.END)
        self.output_tags_data.clear()
        self.selected_tags.clear()
        self.weight_values.clear()
        self.label_weight_display.config(text="")

    def copy_to_clipboard(self) -> None:
        """クリップボードにコピー"""
        text = self.output_text.get(1.0, tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_var.set("クリップボードにコピーしました")

    def update_weight(self, value: str) -> None:
        """重みを更新"""
        self.weight_value_label.config(text=f"{float(value):.1f}")
        if self.selected_tags:
            self.weight_values[self.selected_tags[-1]] = float(value)
            self.refresh_weight_display()

    def refresh_weight_display(self) -> None:
        """重み表示を更新"""
        if not self.weight_values:
            self.label_weight_display.config(text="")
            return
        parts = [f"({t}:{w:.1f})" if w != 1.0 else t for t, w in self.weight_values.items()]
        display_text = ", ".join(parts)
        if len(display_text) > 100:
            display_text = display_text[:97] + "..."
        self.label_weight_display.config(text=f"仮表示: {display_text}")

    def process_queue(self) -> None:
        """キューを処理"""
        try:
            while True:
                item = self.q.get_nowait()
                if item["type"] == "update_tree":
                    self.update_tree_with_items(item["items"], item["category"])
                elif item["type"] == "status":
                    self.status_var.set(item["message"])
                elif item["type"] == "error":
                    messagebox.showerror("エラー", item["message"], parent=self.root)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def update_tree_with_items(self, items: List[Tuple[str, str, str, str]], category: str) -> None:
        """ツリーをアイテムで更新"""
        self.tree.delete(*self.tree.get_children())
        for item in items:
            self.tree.insert("", tk.END, values=item)

    # ダイアログ表示メソッド（プレースホルダー）
    def show_theme_dialog(self) -> None:
        """テーマダイアログを表示"""
        # 簡易実装
        themes = ["cosmo", "flatly", "journal", "litera", "lumen", "minty", "pulse", "sandstone", "yeti"]
        theme = simpledialog.askstring("テーマ選択", f"利用可能なテーマ: {', '.join(themes)}\nテーマ名を入力してください:")
        if theme and theme in themes:
            self.apply_theme(theme)

    def show_ai_prediction_dialog(self) -> None:
        """AI予測ダイアログを表示"""
        show_ai_prediction_dialog(self)

    def show_ai_settings_dialog(self) -> None:
        """AI設定ダイアログを表示"""
        show_ai_settings_dialog(self)

    def show_custom_keywords_dialog(self) -> None:
        """カスタムキーワードダイアログを表示"""
        show_custom_keywords_dialog(self)

    def show_custom_rules_dialog(self) -> None:
        """カスタムルールダイアログを表示"""
        show_custom_rules_dialog(self)

    def show_ai_learning_data_dialog(self) -> None:
        """AI学習データダイアログを表示"""
        show_ai_learning_data_dialog(self)

    def show_ai_help(self) -> None:
        """AIヘルプダイアログを表示"""
        show_ai_help_dialog(self)

    def show_prompt_translator(self) -> None:
        """プロンプト翻訳ダイアログを表示"""
        messagebox.showinfo("プロンプト翻訳", "プロンプト翻訳機能は現在開発中です。")

    def auto_assign_selected_tags(self) -> None:
        """選択タグを自動割り当て"""
        auto_assign_selected_tags(self)

    def auto_assign_uncategorized_tags(self) -> None:
        """未分類タグを一括自動割り当て"""
        auto_assign_uncategorized_tags(self)

    def apply_theme(self, theme_name: str) -> None:
        """テーマを適用"""
        self.theme_manager.current_theme = theme_name
        style = tb.Style()
        style.theme_use(theme_name)

    def toggle_favorite(self) -> None:
        """お気に入りを切り替え"""
        if not self.selected_tags:
            return
        tag = self.selected_tags[0]
        # 簡易実装
        messagebox.showinfo("お気に入り", f"タグ '{tag}' のお気に入り状態を切り替えました。")

    def delete_tag(self) -> None:
        """タグを削除"""
        if not self.selected_tags:
            return
        tag = self.selected_tags[0]
        if messagebox.askyesno("削除確認", f"タグ '{tag}' を削除しますか？"):
            # 簡易実装
            messagebox.showinfo("削除完了", f"タグ '{tag}' を削除しました。")

    def bulk_category_change(self) -> None:
        """一括カテゴリ変更"""
        if not self.selected_tags:
            messagebox.showwarning("警告", "変更するタグを選択してください。")
            return
        # 簡易実装
        messagebox.showinfo("一括変更", "一括カテゴリ変更機能は現在開発中です。")

    def show_context_menu(self, event: Any, tree: Any) -> None:
        """コンテキストメニューを表示"""
        # 簡易実装
        pass

    def set_category_from_menu(self, category: str) -> None:
        """メニューからカテゴリを設定"""
        self.category_var.set(category)
        self.on_category_select(None)

    def select_tag_in_tree(self, tag_to_select: str) -> None:
        """ツリーでタグを選択"""
        # 簡易実装
        pass

    def copy_selected_tags(self) -> None:
        """選択したタグをコピー"""
        if self.selected_tags:
            self.root.clipboard_clear()
            self.root.clipboard_append(", ".join(self.selected_tags))
            self.status_var.set("選択したタグをコピーしました")

    def prompt_and_add_tags(self, is_negative: bool = False) -> None:
        """プロンプトからタグを追加"""
        # 簡易実装
        messagebox.showinfo("タグ追加", "プロンプトからのタグ追加機能は現在開発中です。") 