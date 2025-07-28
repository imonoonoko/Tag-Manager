#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動バックアップスクリプト
データベースと設定ファイルの自動バックアップ機能
"""

import os
import sys
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class AutoBackupManager:
    """自動バックアップ管理クラス"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = self.project_root / "backup"
        self.data_dir = self.project_root / "data"
        self.resources_dir = self.project_root / "resources"
        
        # バックアップ対象ファイル
        self.backup_targets = [
            self.data_dir / "tags.db",
            self.resources_dir / "config" / "theme_settings.json",
            self.resources_dir / "config" / "category_keywords.json",
            self.resources_dir / "config" / "category_descriptions.json",
            self.project_root / "theme_settings.json"
        ]
        
        # バックアップ設定
        self.max_backups = 10  # 最大バックアップ数
        self.backup_interval_hours = 24  # バックアップ間隔（時間）
        
    def create_backup_directory(self, backup_name: str) -> Path:
        """バックアップディレクトリを作成"""
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)
        return backup_path
        
    def backup_file(self, source_path: Path, backup_path: Path) -> bool:
        """ファイルをバックアップ"""
        try:
            if source_path.exists():
                shutil.copy2(source_path, backup_path)
                print(f"✅ {source_path.name} をバックアップしました")
                return True
            else:
                print(f"⚠️  {source_path.name} が見つかりません")
                return False
        except Exception as e:
            print(f"❌ {source_path.name} のバックアップに失敗: {e}")
            return False
            
    def backup_database(self, backup_path: Path) -> bool:
        """データベースをバックアップ"""
        db_file = self.data_dir / "tags.db"
        if not db_file.exists():
            print("⚠️  データベースファイルが見つかりません")
            return False
            
        try:
            # SQLiteデータベースの安全なバックアップ
            import sqlite3
            
            # 元のDBに接続
            conn = sqlite3.connect(db_file)
            
            # バックアップDBを作成
            backup_db = backup_path / "tags.db"
            backup_conn = sqlite3.connect(backup_db)
            
            # データをコピー
            conn.backup(backup_conn)
            
            conn.close()
            backup_conn.close()
            
            print("✅ データベースをバックアップしました")
            return True
            
        except Exception as e:
            print(f"❌ データベースのバックアップに失敗: {e}")
            return False
            
    def create_backup_metadata(self, backup_path: Path, backup_files: List[str]) -> None:
        """バックアップメタデータを作成"""
        metadata = {
            "backup_date": datetime.now().isoformat(),
            "backup_files": backup_files,
            "project_version": self.get_project_version(),
            "backup_type": "auto"
        }
        
        metadata_file = backup_path / "backup_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
            
    def get_project_version(self) -> str:
        """プロジェクトバージョンを取得"""
        try:
            # main.pyからバージョン情報を取得
            main_file = self.project_root / "main.py"
            if main_file.exists():
                with open(main_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # バージョン情報を検索
                    import re
                    version_match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
                    if version_match:
                        return version_match.group(1)
        except Exception:
            pass
            
        return "unknown"
        
    def cleanup_old_backups(self) -> None:
        """古いバックアップを削除"""
        try:
            backup_dirs = [d for d in self.backup_dir.iterdir() if d.is_dir()]
            backup_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 最大バックアップ数を超えた分を削除
            if len(backup_dirs) > self.max_backups:
                for old_backup in backup_dirs[self.max_backups:]:
                    shutil.rmtree(old_backup)
                    print(f"🗑️  古いバックアップを削除: {old_backup.name}")
                    
        except Exception as e:
            print(f"⚠️  古いバックアップの削除中にエラー: {e}")
            
    def should_create_backup(self) -> bool:
        """バックアップを作成すべきかチェック"""
        try:
            # 最新のバックアップを確認
            backup_dirs = [d for d in self.backup_dir.iterdir() if d.is_dir()]
            if not backup_dirs:
                return True
                
            latest_backup = max(backup_dirs, key=lambda x: x.stat().st_mtime)
            latest_time = datetime.fromtimestamp(latest_backup.stat().st_mtime)
            current_time = datetime.now()
            
            # バックアップ間隔をチェック
            time_diff = current_time - latest_time
            return time_diff.total_seconds() > (self.backup_interval_hours * 3600)
            
        except Exception as e:
            print(f"⚠️  バックアップ間隔チェック中にエラー: {e}")
            return True
            
    def create_backup(self, backup_name: Optional[str] = None) -> bool:
        """バックアップを作成"""
        if backup_name is None:
            backup_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            
        print(f"🚀 バックアップを作成中: {backup_name}")
        
        try:
            # バックアップディレクトリを作成
            backup_path = self.create_backup_directory(backup_name)
            
            # データベースをバックアップ
            db_success = self.backup_database(backup_path)
            
            # その他のファイルをバックアップ
            backup_files = []
            for target in self.backup_targets:
                if target.exists():
                    backup_file = backup_path / target.name
                    if self.backup_file(target, backup_file):
                        backup_files.append(target.name)
                        
            # メタデータを作成
            self.create_backup_metadata(backup_path, backup_files)
            
            # 古いバックアップを削除
            self.cleanup_old_backups()
            
            print(f"🎉 バックアップ完了: {backup_name}")
            return True
            
        except Exception as e:
            print(f"❌ バックアップ作成中にエラー: {e}")
            return False
            
    def restore_backup(self, backup_name: str) -> bool:
        """バックアップを復元"""
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            print(f"❌ バックアップ {backup_name} が見つかりません")
            return False
            
        print(f"🔄 バックアップを復元中: {backup_name}")
        
        try:
            # データベースを復元
            backup_db = backup_path / "tags.db"
            if backup_db.exists():
                target_db = self.data_dir / "tags.db"
                shutil.copy2(backup_db, target_db)
                print("✅ データベースを復元しました")
                
            # その他のファイルを復元
            for target in self.backup_targets:
                backup_file = backup_path / target.name
                if backup_file.exists():
                    shutil.copy2(backup_file, target)
                    print(f"✅ {target.name} を復元しました")
                    
            print(f"🎉 復元完了: {backup_name}")
            return True
            
        except Exception as e:
            print(f"❌ 復元中にエラー: {e}")
            return False
            
    def list_backups(self) -> List[Dict]:
        """バックアップ一覧を取得"""
        backups = []
        
        try:
            for backup_dir in self.backup_dir.iterdir():
                if backup_dir.is_dir():
                    metadata_file = backup_dir / "backup_metadata.json"
                    metadata = {}
                    
                    if metadata_file.exists():
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            
                    backup_info = {
                        "name": backup_dir.name,
                        "date": datetime.fromtimestamp(backup_dir.stat().st_mtime).isoformat(),
                        "metadata": metadata
                    }
                    backups.append(backup_info)
                    
        except Exception as e:
            print(f"⚠️  バックアップ一覧取得中にエラー: {e}")
            
        return sorted(backups, key=lambda x: x["date"], reverse=True)

def main():
    """メイン関数"""
    backup_manager = AutoBackupManager()
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python auto_backup.py create [backup_name]  # バックアップ作成")
        print("  python auto_backup.py restore <backup_name>  # バックアップ復元")
        print("  python auto_backup.py list                   # バックアップ一覧")
        print("  python auto_backup.py auto                   # 自動バックアップ")
        sys.exit(1)
        
    command = sys.argv[1]
    
    try:
        if command == "create":
            backup_name = sys.argv[2] if len(sys.argv) > 2 else None
            success = backup_manager.create_backup(backup_name)
            sys.exit(0 if success else 1)
            
        elif command == "restore":
            if len(sys.argv) < 3:
                print("❌ 復元するバックアップ名を指定してください")
                sys.exit(1)
            backup_name = sys.argv[2]
            success = backup_manager.restore_backup(backup_name)
            sys.exit(0 if success else 1)
            
        elif command == "list":
            backups = backup_manager.list_backups()
            print("📋 バックアップ一覧:")
            for backup in backups:
                print(f"  {backup['name']} - {backup['date']}")
                
        elif command == "auto":
            if backup_manager.should_create_backup():
                success = backup_manager.create_backup()
                sys.exit(0 if success else 1)
            else:
                print("⏰ バックアップ間隔が経過していません")
                
        else:
            print(f"❌ 不明なコマンド: {command}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  バックアップが中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 