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
        カテゴリ一括変更ダイアログ（テーブル＋一括適用UI版）
        self.result: Optional[Dict[str, str]] = {tag: 選択カテゴリ}
        """
        self.parent = parent
        self.selected_tags = tags
        self.logger = logging.getLogger(__name__)
        self.result: Optional[Dict[str, str]] = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("カテゴリ一括変更")
        self.dialog.geometry(f"{min(600, 200 + 30*len(tags))}x{200 + 30*len(tags)}")
        self.dialog.resizable(True, True)

        main_frame = tb.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ヘッダー
        header = ["タグ", "カテゴリ選択"]
        for i, h in enumerate(header):
            tk.Label(main_frame, text=h, font=("TkDefaultFont", 10, "bold"), borderwidth=1, relief="solid").grid(row=0, column=i, sticky="nsew", padx=1, pady=1)

        # 各タグごとに行を追加
        self.tag_vars = {}  # tag: tk.StringVar
        for row, tag in enumerate(tags, start=1):
            tk.Label(main_frame, text=tag, borderwidth=1, relief="solid").grid(row=row, column=0, sticky="nsew", padx=1, pady=1)
            var = tk.StringVar(value="未分類")
            combobox = tb.Combobox(main_frame, textvariable=var, values=list(category_keywords.keys()) + ["未分類"], width=20, state="readonly")
            combobox.grid(row=row, column=1, sticky="nsew", padx=1, pady=1)
            self.tag_vars[tag] = var

        # 一括適用・キャンセルボタン
        btn_frame = tb.Frame(self.dialog)
        btn_frame.pack(pady=10)
        btn_ok = tb.Button(btn_frame, text="一括適用", command=self.ok, bootstyle="success")
        btn_cancel = tb.Button(btn_frame, text="キャンセル", command=self.cancel)
        btn_ok.pack(side=tk.LEFT, padx=5)
        btn_cancel.pack(side=tk.LEFT, padx=5)

        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        self.dialog.focus_set()
        self.dialog.wait_window()

    def ok(self) -> None:
        result = {tag: var.get() for tag, var in self.tag_vars.items()}
        if not all(result.values()):
            messagebox.showerror("エラー", "全てのタグのカテゴリを選択してください。", parent=self.dialog)
            return
        self.result = result
        self.dialog.destroy()

    def cancel(self) -> None:
        self.result = None
        self.dialog.destroy()

class MultiTagCategoryAssignDialog:
    def __init__(self, parent: tk.Tk, tags: List[str], category_choices: Optional[List[str]] = None):
        """
        複数タグ＋各タグごとのカテゴリ（複数可）を一括で適用できるダイアログ。
        self.result: Dict[str, List[str]] 形式で返す。
        """
        self.parent = parent
        self.tags = tags
        self.category_choices = category_choices or list(category_keywords.keys()) + ["未分類"]
        self.result: Optional[Dict[str, List[str]]] = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("タグごとのカテゴリ一括適用")
        self.dialog.geometry(f"{min(600, 200 + 30*len(tags))}x{150 + 40*len(tags)}")
        self.dialog.resizable(True, True)

        main_frame = tb.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.category_vars: Dict[str, Dict[str, tk.BooleanVar]] = {}
        for tag in tags:
            row = tb.Frame(main_frame)
            row.pack(fill=tk.X, pady=2)
            tb.Label(row, text=tag, width=16, anchor="w").pack(side=tk.LEFT)
            self.category_vars[tag] = {}
            cat_frame = tb.Frame(row)
            cat_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            for cat in self.category_choices:
                var = tk.BooleanVar()
                chk = tb.Checkbutton(cat_frame, text=cat, variable=var, bootstyle="info")
                chk.pack(side=tk.LEFT, padx=2)
                self.category_vars[tag][cat] = var

        btn_frame = tb.Frame(main_frame)
        btn_frame.pack(pady=10)
        btn_ok = tb.Button(btn_frame, text="一括適用", command=self.ok, bootstyle="success")
        btn_cancel = tb.Button(btn_frame, text="キャンセル", command=self.cancel)
        btn_ok.pack(side=tk.LEFT, padx=5)
        btn_cancel.pack(side=tk.LEFT, padx=5)

        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        self.dialog.focus_set()
        self.dialog.wait_window()

    def ok(self) -> None:
        result: Dict[str, List[str]] = {}
        for tag, cat_vars in self.category_vars.items():
            selected = [cat for cat, var in cat_vars.items() if var.get()]
            result[tag] = selected
        self.result = result
        self.dialog.destroy()

    def cancel(self) -> None:
        self.result = None
        self.dialog.destroy()

class LowConfidenceTagsDialog:
    def __init__(self, parent: tk.Tk, low_confidence_tags: List[Dict[str, Any]], confidence_threshold: float = 0.5):
        """
        低信頼度タグ管理ダイアログ。
        low_confidence_tags: [{"tag": "タグ名", "current_category": "現在のカテゴリ", "confidence": 0.3, "suggested_categories": [{"category": "カテゴリ名", "confidence": 0.8}]}]
        self.result: Optional[Dict[str, str]] = {tag: 選択されたカテゴリ}
        """
        self.parent = parent
        self.low_confidence_tags = low_confidence_tags
        self.confidence_threshold = confidence_threshold
        self.result: Optional[Dict[str, str]] = None
        self.logger = logging.getLogger(__name__)

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"低信頼度タグ管理 (信頼度閾値: {confidence_threshold:.1%})")
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)

        main_frame = tb.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ヘッダー説明
        header_frame = tb.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        tb.Label(header_frame, text=f"AI予測の信頼度が低いタグ ({len(low_confidence_tags)}件)", 
                font=("TkDefaultFont", 12, "bold")).pack(anchor="w")
        tb.Label(header_frame, text="各タグの適切なカテゴリを選択してください", 
                font=("TkDefaultFont", 9)).pack(anchor="w")

        # スクロール可能なフレーム
        canvas = tk.Canvas(main_frame)
        scrollbar = tb.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tb.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # テーブルヘッダー
        header_frame = tb.Frame(scrollable_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        headers = ["タグ", "現在のカテゴリ", "信頼度", "推奨カテゴリ", "手動選択"]
        for i, header in enumerate(headers):
            tb.Label(header_frame, text=header, font=("TkDefaultFont", 10, "bold"), 
                    borderwidth=1, relief="solid", width=15).grid(row=0, column=i, sticky="nsew", padx=1, pady=1)

        # 各タグの行
        self.tag_vars: Dict[str, tk.StringVar] = {}
        for row, tag_data in enumerate(low_confidence_tags, start=1):
            tag = tag_data["tag"]
            current_category = tag_data["current_category"]
            confidence = tag_data["confidence"]
            suggested_categories = tag_data.get("suggested_categories", [])

            # タグ名
            tb.Label(header_frame, text=tag, borderwidth=1, relief="solid", 
                    width=15, anchor="w").grid(row=row, column=0, sticky="nsew", padx=1, pady=1)
            
            # 現在のカテゴリ
            tb.Label(header_frame, text=current_category, borderwidth=1, relief="solid", 
                    width=15, anchor="w").grid(row=row, column=1, sticky="nsew", padx=1, pady=1)
            
            # 信頼度
            confidence_text = f"{confidence:.1%}"
            confidence_color = "red" if confidence < 0.3 else "orange" if confidence < 0.5 else "yellow"
            tb.Label(header_frame, text=confidence_text, borderwidth=1, relief="solid", 
                    width=15, anchor="w", foreground=confidence_color).grid(row=row, column=2, sticky="nsew", padx=1, pady=1)
            
            # 推奨カテゴリ
            if suggested_categories:
                suggested_text = ", ".join([f"{cat['category']}({cat['confidence']:.1%})" 
                                          for cat in suggested_categories[:2]])
            else:
                suggested_text = "なし"
            tb.Label(header_frame, text=suggested_text, borderwidth=1, relief="solid", 
                    width=15, anchor="w").grid(row=row, column=3, sticky="nsew", padx=1, pady=1)
            
            # 手動選択（コンボボックス）
            var = tk.StringVar(value=current_category)
            category_choices = list(category_keywords.keys()) + ["未分類"]
            if suggested_categories:
                # 推奨カテゴリを最初に追加
                suggested_cats = [cat["category"] for cat in suggested_categories if cat["category"] in category_choices]
                category_choices = suggested_cats + [cat for cat in category_choices if cat not in suggested_cats]
            
            combobox = tb.Combobox(header_frame, textvariable=var, values=category_choices, 
                                  width=13, state="readonly")
            combobox.grid(row=row, column=4, sticky="nsew", padx=1, pady=1)
            self.tag_vars[tag] = var

        # スクロール設定
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ボタンフレーム
        btn_frame = tb.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        # 推奨カテゴリを適用ボタン
        btn_apply_suggested = tb.Button(btn_frame, text="推奨カテゴリを適用", 
                                       command=self.apply_suggested_categories, bootstyle="info")
        btn_apply_suggested.pack(side=tk.LEFT, padx=5)
        
        # 一括適用ボタン
        btn_apply = tb.Button(btn_frame, text="選択したカテゴリを適用", 
                             command=self.ok, bootstyle="success")
        btn_apply.pack(side=tk.LEFT, padx=5)
        
        # キャンセルボタン
        btn_cancel = tb.Button(btn_frame, text="キャンセル", command=self.cancel)
        btn_cancel.pack(side=tk.LEFT, padx=5)

        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        self.dialog.focus_set()
        self.dialog.wait_window()

    def apply_suggested_categories(self) -> None:
        """推奨カテゴリを各タグに適用"""
        for tag_data in self.low_confidence_tags:
            tag = tag_data["tag"]
            suggested_categories = tag_data.get("suggested_categories", [])
            if suggested_categories:
                best_suggestion = suggested_categories[0]["category"]
                if tag in self.tag_vars:
                    self.tag_vars[tag].set(best_suggestion)

    def ok(self) -> None:
        """選択したカテゴリを適用"""
        result = {tag: var.get() for tag, var in self.tag_vars.items()}
        if not all(result.values()):
            messagebox.showerror("エラー", "全てのタグのカテゴリを選択してください。", parent=self.dialog)
            return
        self.result = result
        self.dialog.destroy()

    def cancel(self) -> None:
        """キャンセル"""
        self.result = None
        self.dialog.destroy()
