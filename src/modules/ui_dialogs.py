# -*- coding: utf-8 -*-
"""
UIダイアログ関連機能モジュール
"""
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import simpledialog, messagebox, Menu, filedialog, Toplevel
import tkinter as tk
from tkinter import ttk
import threading
import os
import json
import logging
from typing import Any, Dict, List, Optional, Callable, cast, Tuple
import webbrowser

class ProgressDialog:
    """プログレスダイアログクラス"""
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

class ToolTip:
    """ツールチップクラス"""
    def __init__(self, widget: Any, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)
    
    def show_tip(self, event: Optional[Any] = None) -> None:
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tooltip = Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1)
        label.pack()
    
    def hide_tip(self, event: Optional[Any] = None) -> None:
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

def show_help_dialog(parent: Any) -> None:
    """ヘルプダイアログを表示"""
    help_text = """
【タグ管理ツール 使い方】

■ 基本操作
・タグをクリック：プロンプト出力欄に追加
・ダブルクリック：タグを編集
・右クリック：コンテキストメニュー

■ カテゴリ機能
・カテゴリ選択：タグをカテゴリ別に表示
・一括変更：選択したタグのカテゴリを一括変更
・自動割り当て：AIがタグのカテゴリを自動判定

■ 検索・フィルタ
・検索ボックス：タグ名・日本語訳・カテゴリで検索
・お気に入り：★マークでお気に入り登録
・最近使った：最近使用したタグを表示

■ エクスポート・インポート
・個人データエクスポート：全設定とデータをバックアップ
・個人データインポート：バックアップから復元
・タグエクスポート：選択したタグをJSON/CSVで出力

■ AI機能
・AI予測：タグのカテゴリをAIが予測
・カスタムキーワード：独自のキーワードを追加
・カスタムルール：独自の分類ルールを設定

■ その他
・テーマ切替：UIの見た目を変更
・プロンプト翻訳：日本語を英語に翻訳
・データベースバックアップ：DBファイルをバックアップ

■ ライセンス・商用利用
・MITライセンスで商用利用可能
・全てのライブラリ・モデルが商用利用可能
・詳細は「ライセンス情報」ボタンから確認
"""
    
    dialog = Toplevel(parent)
    dialog.title("使い方")
    dialog.geometry("500x450")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(True, True)
    
    # メインフレーム
    main_frame = tk.Frame(dialog)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # スクロール可能なテキストエリア
    text_widget = tk.Text(main_frame, wrap=tk.WORD, font=("TkDefaultFont", 10))
    scrollbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)
    
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    text_widget.insert(tk.END, help_text)
    text_widget.config(state=tk.DISABLED)
    
    # ボタンフレーム
    button_frame = tk.Frame(dialog)
    button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
    
    # ライセンス情報ボタン
    def show_license():
        dialog.destroy()  # 現在のダイアログを閉じる
        show_license_info_dialog(parent)  # ライセンス情報ダイアログを表示
    
    tk.Button(button_frame, text="ライセンス情報", command=show_license).pack(side=tk.LEFT, padx=(0, 10))
    
    # ショートカット一覧ボタン
    def show_shortcuts():
        dialog.destroy()  # 現在のダイアログを閉じる
        show_shortcuts_dialog(parent)  # ショートカット一覧ダイアログを表示
    
    tk.Button(button_frame, text="ショートカット一覧", command=show_shortcuts).pack(side=tk.LEFT, padx=(0, 10))
    
    # 閉じるボタン
    tk.Button(button_frame, text="閉じる", command=dialog.destroy).pack(side=tk.RIGHT)

def show_about_dialog(parent: Any) -> None:
    """バージョン情報ダイアログを表示"""
    about_text = """
タグ管理ツール Nightly

バージョン: 1.0.0
開発者: AI Assistant
ライセンス: MIT License

機能:
・タグ管理・分類
・AI予測機能
・カスタマイズ機能
・プロンプト翻訳
・データエクスポート・インポート

このツールは、AI画像生成のための
プロンプトタグを効率的に管理する
ことを目的としています。

商用利用: 可能
全てのライブラリ・モデルが商用利用可能な
オープンソースライセンスを使用しています。
"""
    
    dialog = Toplevel(parent)
    dialog.title("バージョン情報")
    dialog.geometry("450x350")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)
    
    # メインフレーム
    main_frame = tk.Frame(dialog)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    text_widget = tk.Text(main_frame, wrap=tk.WORD, font=("TkDefaultFont", 10))
    text_widget.pack(fill=tk.BOTH, expand=True)
    
    text_widget.insert(tk.END, about_text)
    text_widget.config(state=tk.DISABLED)
    
    # ボタンフレーム
    button_frame = tk.Frame(dialog)
    button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
    
    # ライセンス情報ボタン
    def show_license():
        dialog.destroy()  # 現在のダイアログを閉じる
        show_license_info_dialog(parent)  # ライセンス情報ダイアログを表示
    
    tk.Button(button_frame, text="ライセンス情報", command=show_license).pack(side=tk.LEFT, padx=(0, 10))
    
    # 閉じるボタン
    tk.Button(button_frame, text="閉じる", command=dialog.destroy).pack(side=tk.RIGHT)

def show_license_info_dialog(parent: Any) -> None:
    """ライセンス情報ダイアログを表示"""
    license_text = """
【タグ管理ツール ライセンス情報】

■ プロジェクトライセンス
MIT License

Copyright (c) 2025 Tag Manager Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

■ 主要ライブラリライセンス

【MIT License】
• ttkbootstrap >= 1.10.1
• deep-translator >= 1.11.4
• pytest >= 7.0.0
• mypy >= 1.0.0

【BSD-3-Clause】
• psutil >= 5.9.0
• numpy >= 1.24.0
• torch >= 2.0.0
• scikit-learn >= 1.3.0
• pandas >= 2.0.0
• joblib >= 1.3.0

【Apache-2.0】
• requests >= 2.31.0
• transformers >= 4.30.0
• sentence-transformers >= 2.2.0

■ 使用AIモデルライセンス

【Apache-2.0】
• sentence-transformers/all-MiniLM-L6-v2
• sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
• sentence-transformers/all-mpnet-base-v2
• sentence-transformers/paraphrase-multilingual-mpnet-base-v2
• pkshatech/GLuCoSE-base-ja

■ 商用利用について

✅ 全てのライブラリ・モデルが商用利用可能
✅ オープンソースライセンス（MIT, BSD-3-Clause, Apache-2.0）
✅ 制限なしの商用利用・再配布・修正が可能

■ 表示義務

本ソフトウェアを使用する際は、以下のライセンス情報を表示する必要があります：

1. プロジェクトライセンス: MIT License - Copyright (c) 2025 Tag Manager Project
2. 主要ライブラリ: ttkbootstrap (MIT), transformers (Apache-2.0), torch (BSD-3-Clause)
3. 使用モデル: sentence-transformers/all-MiniLM-L6-v2 (Apache-2.0) 等

■ 詳細情報

詳細なライセンス情報は以下のファイルで確認できます：
• LICENSE - プロジェクトライセンス
• THIRD_PARTY_LICENSES.txt - 第三者ライセンス詳細
• README.md - ライセンス概要

■ 免責事項

• 各ライブラリ・モデルのライセンスは変更される可能性があります
• 商用利用前は最新のライセンス情報を確認してください
• 法的責任は利用者にあります
"""
    
    dialog = Toplevel(parent)
    dialog.title("ライセンス情報")
    dialog.geometry("600x500")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(True, True)
    
    # スクロール可能なテキストエリア
    frame = tk.Frame(dialog)
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    text_widget = tk.Text(frame, wrap=tk.WORD, font=("TkDefaultFont", 9))
    scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)
    
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    text_widget.insert(tk.END, license_text)
    text_widget.config(state=tk.DISABLED)
    
    # ボタンフレーム
    button_frame = tk.Frame(dialog)
    button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
    
    # 詳細ファイルを開くボタン
    def open_third_party_licenses():
        try:
            third_party_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'THIRD_PARTY_LICENSES.txt')
            if os.path.exists(third_party_file):
                os.startfile(third_party_file)  # Windows
            else:
                messagebox.showinfo("情報", "THIRD_PARTY_LICENSES.txtファイルが見つかりません。", parent=dialog)
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルを開けませんでした: {e}", parent=dialog)
    
    tk.Button(button_frame, text="詳細ライセンス情報を開く", command=open_third_party_licenses).pack(side=tk.LEFT, padx=(0, 10))
    
    # 閉じるボタン
    tk.Button(button_frame, text="閉じる", command=dialog.destroy).pack(side=tk.RIGHT)

def show_shortcuts_dialog(parent: Any) -> None:
    """ショートカット一覧ダイアログを表示"""
    shortcuts_text = """
【ショートカット一覧】

■ 基本操作
Ctrl+C: 選択したタグをコピー
Ctrl+V: クリップボードから貼り付け
Delete: 選択したタグを削除
F5: タグ一覧を更新

■ 検索・フィルタ
Ctrl+F: 検索ボックスにフォーカス
Ctrl+L: 検索をクリア
Ctrl+Shift+F: お気に入りタグのみ表示

■ カテゴリ操作
Ctrl+Shift+C: カテゴリ一括変更
Ctrl+Shift+A: AI自動割り当て
Ctrl+Shift+U: 未分類タグのみ表示

■ ファイル操作
Ctrl+S: データベースバックアップ
Ctrl+E: 個人データエクスポート
Ctrl+I: 個人データインポート

■ その他
F1: ヘルプ表示
Ctrl+Shift+T: テーマ切替
Ctrl+Shift+P: プロンプト翻訳
"""
    
    dialog = Toplevel(parent)
    dialog.title("ショートカット一覧")
    dialog.geometry("500x400")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(True, True)
    
    # スクロール可能なテキストエリア
    frame = tk.Frame(dialog)
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    text_widget = tk.Text(frame, wrap=tk.WORD, font=("TkDefaultFont", 10))
    scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)
    
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    text_widget.insert(tk.END, shortcuts_text)
    text_widget.config(state=tk.DISABLED)
    
    close_button = tk.Button(dialog, text="閉じる", command=dialog.destroy)
    close_button.pack(pady=10) 