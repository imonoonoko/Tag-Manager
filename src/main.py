import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import simpledialog, messagebox, Menu, filedialog
import tkinter as tk
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

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)

# グローバル例外ハンドラー
def global_exception_hook(exctype, value, traceback):
    import tkinter.messagebox as mb
    error_msg = f"{exctype.__name__}: {value}"
    logging.getLogger(__name__).error(f"予期せぬ例外: {error_msg}")
    
    # Hugging Face関連のエラーは軽量モードで動作
    if "transformers" in str(value).lower() or "doge" in str(value).lower():
        logging.info("Hugging Face関連のエラーを検出。軽量モードで動作します。")
        return
    
    # その他のエラーはユーザーに通知
    try:
        mb.showerror("予期せぬエラー", error_msg)
    except:
        print(f"エラー通知に失敗: {error_msg}")

if __name__ == "__main__":
    # グローバル例外ハンドラーを設定
    sys.excepthook = global_exception_hook
    
    try:
        from modules.ui_main import TagManagerApp
        root = tb.Window()
        app = TagManagerApp(root)
        root.mainloop()
    except Exception as e:
        logging.error(f"アプリケーション起動エラー: {e}")
        print(f"アプリケーション起動エラー: {e}")
        input("Enterキーを押して終了してください...")