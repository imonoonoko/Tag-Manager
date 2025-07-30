"""
プロンプト翻訳ダイアログ
プロンプト出力欄に日本語で直接入力して英語に変換するUI
"""
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox, scrolledtext
from typing import Any, Dict, List, Optional, Callable
import threading
import time

from modules.prompt_translator import PromptTranslator
prompt_translator = PromptTranslator()

class PromptTranslatorDialog:
    """
    プロンプト翻訳ダイアログクラス
    日本語のプロンプトを英語に翻訳するためのUI
    """
    
    def __init__(self, parent: Any, callback: Optional[Callable[[str], None]] = None):
        """
        初期化
        
        Args:
            parent: 親ウィンドウ
            callback: 翻訳結果を受け取るコールバック関数
        """
        self.parent = parent
        self.callback = callback
        self.result = None
        
        # ダイアログウィンドウの作成
        self.dialog = tb.Toplevel(parent)
        self.dialog.title("プロンプト翻訳")
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # ダイアログが閉じられた時の処理
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        self.setup_ui()
        self.load_custom_translations()
    
    def setup_ui(self):
        """UIの構築"""
        # メインフレーム
        main_frame = tb.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = tb.Label(main_frame, text="日本語プロンプト翻訳", 
                              font=("TkDefaultFont", 16, "bold"), bootstyle="primary")
        title_label.pack(pady=(0, 10))
        
        # 入力エリア
        input_frame = tb.LabelFrame(main_frame, text="日本語入力", padding=10)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 日本語入力テキストエリア
        self.japanese_input = scrolledtext.ScrolledText(
            input_frame, height=8, wrap=tk.WORD, font=("TkDefaultFont", 11)
        )
        self.japanese_input.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 翻訳ボタン
        button_frame = tb.Frame(input_frame)
        button_frame.pack(fill=tk.X)
        
        self.translate_button = tb.Button(
            button_frame, text="翻訳実行", command=self.translate_text,
            bootstyle="success", width=15
        )
        self.translate_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clear_button = tb.Button(
            button_frame, text="クリア", command=self.clear_input,
            bootstyle="light", width=10
        )
        self.clear_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 翻訳結果エリア
        result_frame = tb.LabelFrame(main_frame, text="翻訳結果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 翻訳結果テキストエリア
        self.result_text = scrolledtext.ScrolledText(
            result_frame, height=8, wrap=tk.WORD, font=("TkDefaultFont", 11),
            state=tk.DISABLED
        )
        self.result_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 結果ボタン
        result_button_frame = tb.Frame(result_frame)
        result_button_frame.pack(fill=tk.X)
        
        self.copy_button = tb.Button(
            result_button_frame, text="コピー", command=self.copy_result,
            bootstyle="info", width=10
        )
        self.copy_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.use_result_button = tb.Button(
            result_button_frame, text="結果を使用", command=self.use_result,
            bootstyle="primary", width=12
        )
        self.use_result_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 詳細情報エリア
        details_frame = tb.LabelFrame(main_frame, text="翻訳詳細", padding=10)
        details_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.details_text = scrolledtext.ScrolledText(
            details_frame, height=4, wrap=tk.WORD, font=("TkDefaultFont", 9),
            state=tk.DISABLED
        )
        self.details_text.pack(fill=tk.BOTH, expand=True)
        
        # カスタム翻訳管理エリア
        custom_frame = tb.LabelFrame(main_frame, text="カスタム翻訳管理", padding=10)
        custom_frame.pack(fill=tk.X, pady=(0, 10))
        
        # カスタム翻訳入力
        custom_input_frame = tb.Frame(custom_frame)
        custom_input_frame.pack(fill=tk.X, pady=(0, 5))
        
        tb.Label(custom_input_frame, text="日本語:").pack(side=tk.LEFT)
        self.custom_japanese = tb.Entry(custom_input_frame, width=20)
        self.custom_japanese.pack(side=tk.LEFT, padx=(5, 10))
        
        tb.Label(custom_input_frame, text="英語:").pack(side=tk.LEFT)
        self.custom_english = tb.Entry(custom_input_frame, width=20)
        self.custom_english.pack(side=tk.LEFT, padx=(5, 10))
        
        self.add_custom_button = tb.Button(
            custom_input_frame, text="追加", command=self.add_custom_translation,
            bootstyle="success", width=8
        )
        self.add_custom_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # カスタム翻訳一覧
        custom_list_frame = tb.Frame(custom_frame)
        custom_list_frame.pack(fill=tk.BOTH, expand=True)
        
        # カスタム翻訳リストボックス
        list_frame = tb.Frame(custom_list_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tb.Label(list_frame, text="カスタム翻訳一覧:").pack(anchor=tk.W)
        
        self.custom_listbox = tk.Listbox(list_frame, height=6, font=("TkDefaultFont", 9))
        self.custom_listbox.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # カスタム翻訳操作ボタン
        custom_ops_frame = tb.Frame(custom_list_frame)
        custom_ops_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        self.remove_custom_button = tb.Button(
            custom_ops_frame, text="削除", command=self.remove_custom_translation,
            bootstyle="danger", width=10
        )
        self.remove_custom_button.pack(pady=(0, 5))
        
        self.clear_cache_button = tb.Button(
            custom_ops_frame, text="キャッシュクリア", command=self.clear_cache,
            bootstyle="warning", width=10
        )
        self.clear_cache_button.pack(pady=(0, 5))
        
        # 統計情報
        self.stats_label = tb.Label(custom_ops_frame, text="", font=("TkDefaultFont", 8))
        self.stats_label.pack(pady=(10, 0))
        
        # 下部ボタン
        bottom_frame = tb.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.cancel_button = tb.Button(
            bottom_frame, text="キャンセル", command=self.on_cancel,
            bootstyle="light", width=10
        )
        self.cancel_button.pack(side=tk.RIGHT)
        
        # 初期フォーカス
        self.japanese_input.focus_set()
        
        # 統計情報の更新
        self.update_stats()
    
    def translate_text(self):
        """テキストを翻訳する"""
        japanese_text = self.japanese_input.get("1.0", tk.END).strip()
        if not japanese_text:
            messagebox.showwarning("警告", "翻訳するテキストを入力してください。", parent=self.dialog)
            return
        
        # 翻訳ボタンを無効化
        self.translate_button.config(state=tk.DISABLED, text="翻訳中...")
        self.dialog.update()
        
        # 別スレッドで翻訳実行
        def translate_thread():
            try:
                # 行ごとに翻訳
                lines = japanese_text.split('\n')
                translated_lines = []
                details_lines = []
                
                for i, line in enumerate(lines):
                    if line.strip():
                        result = prompt_translator.translate_prompt_with_analysis(line.strip())
                        translated_lines.append(result["translated"])
                        
                        # 詳細情報
                        detail = f"行{i+1}: {line.strip()} → {result['translated']}"
                        detail += f" (方法: {result['translation_method']}, 信頼度: {result['confidence']:.1f})"
                        if result['suggestions']:
                            detail += f" [提案: {', '.join(result['suggestions'])}]"
                        details_lines.append(detail)
                    else:
                        translated_lines.append("")
                
                # UI更新（メインスレッドで実行）
                self.dialog.after(0, lambda: self.update_translation_result(
                    '\n'.join(translated_lines), '\n'.join(details_lines)
                ))
                
            except Exception as e:
                self.dialog.after(0, lambda: messagebox.showerror(
                    "エラー", f"翻訳中にエラーが発生しました:\n{e}", parent=self.dialog
                ))
            finally:
                # 翻訳ボタンを再有効化
                self.dialog.after(0, lambda: self.translate_button.config(
                    state=tk.NORMAL, text="翻訳実行"
                ))
        
        threading.Thread(target=translate_thread, daemon=True).start()
    
    def update_translation_result(self, translated_text: str, details_text: str):
        """翻訳結果を更新する"""
        # 結果テキストエリアを更新
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", translated_text)
        self.result_text.config(state=tk.DISABLED)
        
        # 詳細情報を更新
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert("1.0", details_text)
        self.details_text.config(state=tk.DISABLED)
        
        # 結果を保存
        self.result = translated_text
    
    def clear_input(self):
        """入力をクリアする"""
        self.japanese_input.delete("1.0", tk.END)
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.config(state=tk.DISABLED)
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete("1.0", tk.END)
        self.details_text.config(state=tk.DISABLED)
        self.result = None
    
    def copy_result(self):
        """結果をクリップボードにコピーする"""
        if self.result:
            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(self.result)
            messagebox.showinfo("コピー完了", "翻訳結果をクリップボードにコピーしました。", parent=self.dialog)
        else:
            messagebox.showwarning("警告", "コピーする結果がありません。", parent=self.dialog)
    
    def use_result(self):
        """結果を使用する"""
        if self.result and self.callback:
            self.callback(self.result)
            self.dialog.destroy()
        elif self.result:
            messagebox.showinfo("完了", "結果が設定されました。", parent=self.dialog)
            self.dialog.destroy()
        else:
            messagebox.showwarning("警告", "使用する結果がありません。", parent=self.dialog)
    
    def load_custom_translations(self):
        """カスタム翻訳を読み込む"""
        self.custom_listbox.delete(0, tk.END)
        custom_translations = prompt_translator.get_custom_translations()
        for japanese, english in custom_translations.items():
            self.custom_listbox.insert(tk.END, f"{japanese} → {english}")
    
    def add_custom_translation(self):
        """カスタム翻訳を追加する"""
        japanese = self.custom_japanese.get().strip()
        english = self.custom_english.get().strip()
        
        if not japanese or not english:
            messagebox.showwarning("警告", "日本語と英語の両方を入力してください。", parent=self.dialog)
            return
        
        if prompt_translator.add_custom_translation(japanese, english):
            self.load_custom_translations()
            self.update_stats()
            self.custom_japanese.delete(0, tk.END)
            self.custom_english.delete(0, tk.END)
            messagebox.showinfo("追加完了", "カスタム翻訳を追加しました。", parent=self.dialog)
        else:
            messagebox.showerror("エラー", "カスタム翻訳の追加に失敗しました。", parent=self.dialog)
    
    def remove_custom_translation(self):
        """カスタム翻訳を削除する"""
        selection = self.custom_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "削除する項目を選択してください。", parent=self.dialog)
            return
        
        index = selection[0]
        custom_translations = list(prompt_translator.get_custom_translations().items())
        if index < len(custom_translations):
            japanese = custom_translations[index][0]
            if prompt_translator.remove_custom_translation(japanese):
                self.load_custom_translations()
                self.update_stats()
                messagebox.showinfo("削除完了", "カスタム翻訳を削除しました。", parent=self.dialog)
            else:
                messagebox.showerror("エラー", "カスタム翻訳の削除に失敗しました。", parent=self.dialog)
    
    def clear_cache(self):
        """翻訳キャッシュをクリアする"""
        if messagebox.askyesno("確認", "翻訳キャッシュをクリアしますか？", parent=self.dialog):
            if prompt_translator.clear_cache():
                self.update_stats()
                messagebox.showinfo("完了", "翻訳キャッシュをクリアしました。", parent=self.dialog)
            else:
                messagebox.showerror("エラー", "キャッシュのクリアに失敗しました。", parent=self.dialog)
    
    def update_stats(self):
        """統計情報を更新する"""
        stats = prompt_translator.get_cache_stats()
        stats_text = f"キャッシュ: {stats['cache_size']}\n"
        stats_text += f"カスタム: {stats['custom_translations']}\n"
        stats_text += f"ルール: {stats['prompt_rules']}"
        self.stats_label.config(text=stats_text)
    
    def on_cancel(self):
        """キャンセル処理"""
        self.dialog.destroy()
    
    def show(self):
        """ダイアログを表示する"""
        self.dialog.wait_window()
        return self.result

def show_prompt_translator_dialog(parent: Any, callback: Optional[Callable[[str], None]] = None) -> Optional[str]:
    """
    プロンプト翻訳ダイアログを表示する
    
    Args:
        parent: 親ウィンドウ
        callback: 翻訳結果を受け取るコールバック関数
        
    Returns:
        Optional[str]: 翻訳結果（キャンセル時はNone）
    """
    dialog = PromptTranslatorDialog(parent, callback)
    return dialog.show() 