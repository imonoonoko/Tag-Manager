"""
基本設定とファイルパス定数
"""
import os
from typing import Dict, List
import sys # 追加: sysモジュールをインポート

# 基本設定
APP_NAME = "Tag Manager"
VERSION = "1.0.0"

# アプリケーションのルートディレクトリを取得
def get_app_root():
    """アプリケーションのルートディレクトリを取得（EXE対応）"""
    if getattr(sys, 'frozen', False):
        # PyInstallerで作成されたEXEの場合
        return os.path.dirname(sys.executable)
    else:
        # 通常のPythonスクリプトの場合
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# アプリケーションルートディレクトリ
APP_ROOT = get_app_root()

# ファイルパス設定（絶対パス）
DB_FILE = os.path.join(APP_ROOT, 'data', "tags.db")
THEME_FILE = os.path.join(APP_ROOT, 'resources', 'config', 'theme_settings.json')
CATEGORY_KEYWORDS_FILE = os.path.join(APP_ROOT, 'resources', 'config', 'category_keywords.json')
CATEGORY_DESCRIPTIONS_FILE = os.path.join(APP_ROOT, 'resources', 'config', 'category_descriptions.json')

# 後方互換性のための設定
POSITIVE_PROMPT_FILE = os.path.join(APP_ROOT, 'resources', 'config', "translated_tags.json")
NEGATIVE_PROMPT_FILE = os.path.join(APP_ROOT, 'resources', 'config', "negative_tags.json")
TRANSLATING_PLACEHOLDER = "翻訳中..."

# バックアップ設定
BACKUP_DIR = os.path.join(APP_ROOT, 'backup')
BACKUP_PREFIX = 'tags_backup_'

# ログ設定
LOG_DIR = os.path.join(APP_ROOT, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'app.log')
LOG_LEVEL = 'INFO'

# テスト設定
TEST_DB_FILE = os.path.join(BACKUP_DIR, 'test', 'test_tags.db')

# 基本設定値
DEFAULT_THEME = "darkly"
DEFAULT_CATEGORY = "未分類"
DEFAULT_WEIGHT = 1.0

# ログ設定
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_FILE = os.path.join(LOG_DIR, 'app.log')

# データベース設定
CACHE_TIMEOUT = 300  # 5分
MAX_CONCURRENT_OPERATIONS = 3
BATCH_SIZE = 100

# UI設定
DEFAULT_WINDOW_SIZE = "1200x800"
MAX_RECENT_TAGS = 50

# カテゴリ設定
DEFAULT_CATEGORIES = [
    "人物・キャラクター",
    "表情・感情", 
    "服装・ファッション",
    "髪型・ヘアスタイル",
    "ポーズ・アクション",
    "小物・アクセサリー",
    "色彩・照明",
    "背景・環境",
    "アートスタイル・技法",
    "特殊効果・フィルター",
    "未分類"
]

# ファイル拡張子
SUPPORTED_IMPORT_FORMATS = [".json", ".csv"]
SUPPORTED_EXPORT_FORMATS = [".json", ".csv", ".txt"]

# Hugging Face設定
HUGGINGFACE_ENABLED = True  # 商用利用可能なライセンスのモデルのみ
HUGGINGFACE_CACHE_TTL = 30  # キャッシュ有効期限（日）
HUGGINGFACE_MODELS = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "sentence-transformers/all-mpnet-base-v2",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
]

# 研究目的・個人利用制限
RESEARCH_ONLY_MODE = True  # 研究目的・個人利用限定
COMMERCIAL_USE_WARNING = True  # 商用利用警告 