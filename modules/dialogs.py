import tkinter as tk
import ttkbootstrap as tb
from tkinter import simpledialog, messagebox
from ttkbootstrap.constants import *
from modules.constants import category_keywords
import logging
from typing import Any, List, Optional, Dict, Union
from tkinter import Event

def get_category_choices(category_keywords: Dict[str, List[str]]) -> List[str]:
    """
    カテゴリ選択肢リストを返す純粋関数。
    """
    return list(category_keywords.keys()) + ["未分類"]

def validate_bulk_category_action(action: str, to_category: str) -> bool:
    """
    一括カテゴリ変更ダイアログの入力値バリデーション。
    """
    if action == "change" and not to_category:
        return False
    return True

# --- 純粋関数: バリデーション（例外時logger出力） ---
def safe_validate_bulk_category_action(action: str, to_category: str, logger: Optional[logging.Logger] = None) -> bool:
    """
    一括カテゴリ変更バリデーション。例外時はlogger.error出力しFalseを返す。
    """
    try:
        return validate_bulk_category_action(action, to_category)
    except Exception as e:
        if logger:
            logger.error(f"バリデーション例外: {e}")
        return False

class CategorySelectDialog(simpledialog.Dialog):
    def __init__(self, parent: tk.Tk, categories: List[str]) -> None:
        """
        カテゴリ選択ダイアログ。
        失敗時はlogger.errorで記録し、必要に応じてmessagebox.showerrorで通知。
        戻り値: self.result
        """
        super().__init__(parent)
        self.title("カテゴリ選択")
        self.result: Optional[str] = None
        self.categories = categories
        self.logger = logging.getLogger(__name__)

        self.label = tb.Label(self, text="カテゴリを選択してください:")
        self.label.pack(padx=10, pady=5)

        self.category_var = tk.StringVar()
        self.combobox = tb.Combobox(self, textvariable=self.category_var, values=self.categories)
        self.combobox.pack(padx=10, pady=5)
        self.combobox.current(0)

        btn_frame = tb.Frame(self)
        btn_frame.pack(pady=10)
        btn_ok = tb.Button(btn_frame, text="OK", command=self.ok)
        btn_cancel = tb.Button(btn_frame, text="キャンセル", command=self.cancel)
        btn_ok.pack(side=tk.LEFT, padx=5)
        btn_cancel.pack(side=tk.LEFT, padx=5)

        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.transient(parent)
        self.grab_set()
        self.wait_window()

    def ok(self, event: Optional[Event] = None) -> None:
        category = self.category_var.get()
        self.result = category
        self.destroy()

    def cancel(self, event: Optional[Event] = None) -> None:
        self.result = None
        self.destroy()

class BulkCategoryDialog:
    def __init__(self, parent: tk.Tk, tags: List[str]) -> None:
        """
        カテゴリ一括変更ダイアログ。
        失敗時はlogger.errorで記録し、必要に応じてmessagebox.showerrorで通知。
        戻り値: self.result
        """
        self.parent = parent
        self.selected_tags = tags
        self.logger = logging.getLogger(__name__)
        self.result: Optional[Dict[str, str]] = None
        
        # Toplevelウィンドウを作成
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("カテゴリ一括変更")
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)
        
        # メインコンテンツ
        main_frame = tb.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.label = tb.Label(main_frame, text=f"選択中のタグ数: {len(self.selected_tags)}")
        self.label.pack(pady=5)

        # 変数を先に初期化
        self.action_var = tk.StringVar(value="change")
        self.category_var = tk.StringVar()

        rb_change = tb.Radiobutton(main_frame, text="カテゴリを変更する", variable=self.action_var, value="change")
        rb_remove = tb.Radiobutton(main_frame, text="カテゴリを削除する（未分類にする）", variable=self.action_var, value="remove")
        rb_change.pack(anchor="w", pady=2)
        rb_remove.pack(anchor="w", pady=2)

        self.combobox = tb.Combobox(main_frame, textvariable=self.category_var, 
                                   values=list(category_keywords.keys()) + ["未分類"])
        self.combobox.pack(pady=10, fill=tk.X)
        self.combobox.current(0)

        def on_action_change(*args: Any) -> None:
            if self.action_var.get() == "change":
                self.combobox.config(state="normal")
            else:
                self.combobox.set("未分類")
                self.combobox.config(state="disabled")
        self.action_var.trace_add("write", on_action_change)
        on_action_change()

        btn_frame = tb.Frame(main_frame)
        btn_frame.pack(pady=20)
        btn_ok = tb.Button(btn_frame, text="OK", command=self.ok)
        btn_cancel = tb.Button(btn_frame, text="キャンセル", command=self.cancel)
        btn_ok.pack(side=tk.LEFT, padx=5)
        btn_cancel.pack(side=tk.LEFT, padx=5)

        # ダイアログの設定
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        
        # モーダルダイアログとして表示
        self.dialog.focus_set()
        self.dialog.wait_window()

    def ok(self) -> None:
        action = self.action_var.get()
        to_category = self.category_var.get()
        if action == "change":
            if not safe_validate_bulk_category_action(action, to_category, self.logger):
                messagebox.showerror("エラー", "カテゴリ名を入力してください。", parent=self.dialog)
                return
        else:
            to_category = "未分類"
        self.result = {"action": action, "to_category": to_category}
        self.dialog.destroy()

    def cancel(self) -> None:
        self.result = None
        self.dialog.destroy()
