#!/usr/bin/env python3
"""
backup/ ディレクトリのクリーンアップスクリプト
- テスト用DB（test_やtags_backup_coverage等）はbackup/test/配下に限定
- 本番用バックアップは日付別ディレクトリまたはtags_backup_YYYYMMDD_HHMMSS.db形式のみ残す
- 30日以上前のバックアップDBは自動削除
- 不要なjsonや一時ファイルも削除
"""
import os
import re
import shutil
from datetime import datetime, timedelta

BACKUP_DIR = os.path.join(os.path.dirname(__file__), '..', 'backup')
TEST_DIR = os.path.join(BACKUP_DIR, 'test')
DAYS_KEEP = 30
now = datetime.now()

# 1. テスト用DBはtest/配下に限定
for fname in os.listdir(BACKUP_DIR):
    fpath = os.path.join(BACKUP_DIR, fname)
    if os.path.isfile(fpath):
        if re.match(r'(test_|tags_backup_coverage_|tags_backup_ui_).*\.db', fname):
            print(f"[移動] テスト用DB: {fname} → test/")
            os.makedirs(TEST_DIR, exist_ok=True)
            shutil.move(fpath, os.path.join(TEST_DIR, fname))

# 2. 30日以上前のバックアップDBを削除
for fname in os.listdir(BACKUP_DIR):
    fpath = os.path.join(BACKUP_DIR, fname)
    if re.match(r'tags_backup_\d{8}_\d{6}\.db', fname):
        dt_str = fname.replace('tags_backup_', '').replace('.db', '')
        try:
            dt = datetime.strptime(dt_str, '%Y%m%d_%H%M%S')
            if (now - dt).days > DAYS_KEEP:
                print(f"[削除] 古いバックアップ: {fname}")
                os.remove(fpath)
        except Exception:
            pass

# 3. 不要なjsonや一時ファイルを削除
for fname in os.listdir(BACKUP_DIR):
    if fname.endswith('.json') or fname.endswith('.tmp') or fname.endswith('.bak'):
        fpath = os.path.join(BACKUP_DIR, fname)
        print(f"[削除] 不要ファイル: {fname}")
        os.remove(fpath)

print("[完了] backup/ディレクトリのクリーンアップが完了しました") 