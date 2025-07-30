"""
基本設定とファイルパス定数

このモジュールは、アプリケーションの設定とファイルパスを一元管理します。
.exe実行時とスクリプト実行時で、データの保存場所を自動的に切り替えます。

- .exe実行時: 全ての書き込みデータは、ユーザーのAppData\Roaming\AppNameフォルダに保存されます。
- スクリプト実行時: データはプロジェクト内の各ディレクトリに保存されます。
"""
import os
import sys
import json

# --- 基本設定 ---
APP_NAME = "Tag Manager"
VERSION = "1.0.0"

# --- パス設定 ---
def get_app_data_path(subfolder: str = "") -> str:
    """AppData\Roaming\AppName\subfolder のパスを返す"""
    path = os.path.join(os.getenv('APPDATA'), APP_NAME)
    if subfolder:
        path = os.path.join(path, subfolder)
    return path

if getattr(sys, 'frozen', False):
    # .exe実行時のパス設定: .exeと同じディレクトリにデータを保存
    APP_DIR = os.path.dirname(sys.executable)
    RESOURCE_DIR = os.path.dirname(sys.executable)
    print(f"[INFO] .exe実行モードを検出")
    print(f"[INFO] データ保存先 (APP_DIR): {APP_DIR}")
    print(f"[INFO] リソース読み込み元 (RESOURCE_DIR): {RESOURCE_DIR}")
else:
    # スクリプト実行時のパス設定
    # プロジェクトルートを基準とする
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RESOURCE_DIR = APP_DIR
    print(f"[INFO] スクリプト実行モードを検出")
    print(f"[INFO] データ/リソースの場所 (APP_DIR): {APP_DIR}")

# --- 書き込み対象パス (APP_DIR基準) ---
DB_FILE = os.path.join(APP_DIR, "data", "tags.db")
THEME_FILE = os.path.join(APP_DIR, "data", "theme_settings.json")
POSITIVE_PROMPT_FILE = os.path.join(APP_DIR, "data", "tags.json")
NEGATIVE_PROMPT_FILE = os.path.join(APP_DIR, "data", "negative_tags.json")
TRANSLATED_TAGS_FILE = os.path.join(APP_DIR, "data", "translated_tags.json")
AI_SETTINGS_FILE = os.path.join(APP_DIR, "data", "ai_settings.json")
BACKUP_DIR = os.path.join(APP_DIR, "backup")
LOG_DIR = os.path.join(APP_DIR, "logs")
TEST_DB_FILE = os.path.join(BACKUP_DIR, "test", "test_tags.db")

# --- 読み取り専用パス (RESOURCE_DIR基準) ---
CATEGORY_KEYWORDS_FILE = os.path.join(RESOURCE_DIR, "resources", "config", "category_keywords.json")
CATEGORY_DESCRIPTIONS_FILE = os.path.join(RESOURCE_DIR, "resources", "config", "category_descriptions.json")

# --- 定数 ---
TRANSLATING_PLACEHOLDER = "翻訳中..."
BACKUP_PREFIX = 'tags_backup_'
LOG_FILE = os.path.join(LOG_DIR, 'app.log')
LOG_LEVEL = 'INFO'
DEFAULT_THEME = "darkly"
DEFAULT_CATEGORY = "未分類"
DEFAULT_WEIGHT = 1.0
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

def get_full_path(relative_path: str) -> str:
    """相対パスを絶対パスに変換（後方互換性のため）"""
    return os.path.join(APP_DIR, relative_path)

def ensure_data_directories():
    """書き込みに必要なディレクトリと空のファイルを確実に作成する"""
    print("--- [INFO] データディレクトリの確認/作成を開始 ---")
    # 作成が必要なディレクトリリスト
    dirs_to_create = [
        os.path.dirname(DB_FILE), # data
        BACKUP_DIR,
        LOG_DIR,
        os.path.join(BACKUP_DIR, 'test')
    ]
    for d in dirs_to_create:
        try:
            if not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
                print(f"[SUCCESS] ディレクトリを作成しました: {d}")
        except OSError as e:
            print(f"[ERROR] ディレクトリ作成に失敗: {d}, {e}", file=sys.stderr)

    # 作成が必要な空のファイルリスト (ファイルパス, デフォルトの内容)
    files_to_create = [
        (THEME_FILE, '{}'),
        (POSITIVE_PROMPT_FILE, '[]'),
        (NEGATIVE_PROMPT_FILE, '[]'),
        (TRANSLATED_TAGS_FILE, '[]'),
        (AI_SETTINGS_FILE, json.dumps({"first_run": True, "models_downloaded": False}, indent=2))
    ]
    for file_path, default_content in files_to_create:
        try:
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(default_content)
                print(f"[SUCCESS] デフォルトファイルを作成しました: {file_path}")
        except IOError as e:
            print(f"[ERROR] デフォルトファイルの作成に失敗: {file_path}, {e}", file=sys.stderr)
    print("--- [INFO] データディレクトリの確認/作成が完了 ---")

# --- 起動時処理 ---
ensure_data_directories()

# --- デバッグ用: 全パスを出力 ---
print("--- [Path Debug] --- Configured Paths ---")
all_vars = {key: value for key, value in globals().items() if not key.startswith('__') and isinstance(value, str)}
path_vars = {k: v for k, v in all_vars.items() if k.endswith(('_DIR', '_FILE'))}
for name, path in sorted(path_vars.items()):
    print(f"{name}: {path}")
print("--- [Path Debug] --- End of Paths ---")