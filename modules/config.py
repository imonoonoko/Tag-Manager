"""
基本設定とファイルパス定数
"""
import os
from typing import Dict, List

# 基本設定
APP_NAME = "Tag Manager"
VERSION = "1.0.0"

# ファイルパス設定
DB_FILE = os.path.join('data', "tags.db")
THEME_FILE = os.path.join('resources', 'config', 'theme_settings.json')
CATEGORY_KEYWORDS_FILE = os.path.join('resources', 'config', 'category_keywords.json')
CATEGORY_DESCRIPTIONS_FILE = os.path.join('resources', 'config', 'category_descriptions.json')

# 後方互換性のための設定
POSITIVE_PROMPT_FILE = os.path.join('resources', 'config', "translated_tags.json")
NEGATIVE_PROMPT_FILE = os.path.join('resources', 'config', "negative_tags.json")
TRANSLATING_PLACEHOLDER = "翻訳中..."

# バックアップ設定
BACKUP_DIR = 'backup'
BACKUP_PREFIX = 'tags_backup_'

# ログ設定
LOG_DIR = 'logs'
LOG_FILE = os.path.join(LOG_DIR, 'app.log')
LOG_LEVEL = 'INFO'

# テスト設定
TEST_DB_FILE = os.path.join('backup', 'test', 'test_tags.db')

# 基本設定値
DEFAULT_THEME = "darkly"
DEFAULT_CATEGORY = "未分類"
DEFAULT_WEIGHT = 1.0

# ログ設定
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_FILE = os.path.join('logs', 'app.log')

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