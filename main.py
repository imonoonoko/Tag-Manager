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

from modules.ui_main import TagManagerApp

if __name__ == "__main__":
    def global_exception_hook(exctype, value, traceback):
        import tkinter.messagebox as mb
        logging.getLogger(__name__).error(f"予期せぬ例外: {exctype.__name__}: {value}")
        mb.showerror("予期せぬエラー", f"{exctype.__name__}: {value}")
    sys.excepthook = global_exception_hook
    root = tb.Window()
    app = TagManagerApp(root)
    root.mainloop()