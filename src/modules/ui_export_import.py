# -*- coding: utf-8 -*-
"""
UIエクスポート・インポート機能モジュール
"""
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import simpledialog, messagebox, Menu, filedialog, Toplevel
import tkinter as tk
from tkinter import ttk
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
import time
from typing import Any, Dict, List, Optional, Callable, cast, Tuple
import webbrowser

from modules.ui_dialogs import ProgressDialog

def get_safe_path(base_path: str, relative_path: str) -> str:
    """
    安全なパスを生成する関数
    
    Args:
        base_path: ベースパス
        relative_path: 相対パス
        
    Returns:
        安全な絶対パス
    """
    try:
        # 相対パスを正規化
        normalized_path = os.path.normpath(os.path.join(base_path, relative_path))
        # ベースパス内にあるかチェック
        if os.path.commonpath([base_path, normalized_path]) == os.path.commonpath([base_path]):
            return normalized_path
        else:
            # ベースパス外の場合はベースパスを返す
            return base_path
    except Exception:
        return base_path

def export_personal_data(app_instance: Any) -> None:
    """個人データ包括的エクスポート機能"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"personal_data_export_{timestamp}.json"
        
        # 安全なデフォルトディレクトリを設定
        default_dir = get_safe_path(os.getcwd(), "exports")
        if not os.path.exists(default_dir):
            os.makedirs(default_dir, exist_ok=True)
        
        file_path = filedialog.asksaveasfilename(
            title="個人データをエクスポート",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=default_filename,
            initialdir=default_dir
        )
        
        if not file_path:
            return
        
        # プログレスダイアログを表示
        progress_dialog = ProgressDialog(
            app_instance.root,
            "個人データエクスポート中",
            "データを収集しています..."
        )
        
        def export_worker():
            try:
                # エクスポートデータの構造
                export_data = {
                    "version": "1.0",
                    "export_date": datetime.datetime.now().isoformat(),
                    "app_version": "Tag Manager Nightly",
                    "data": {}
                }
                
                # 1. タグデータ
                progress_dialog.set_message("タグデータを収集中...")
                try:
                    all_tags = app_instance.tag_manager.get_all_tags()
                    export_data["data"]["tags"] = {
                        "positive_tags": [t for t in all_tags if not t.get("is_negative", False)],
                        "negative_tags": [t for t in all_tags if t.get("is_negative", False)],
                        "recent_tags": app_instance.tag_manager.get_recent_tags()
                    }
                except Exception as e:
                    app_instance.logger.error(f"タグデータ収集エラー: {e}")
                    export_data["data"]["tags"] = {"error": str(e)}
                
                # 2. AI学習データ
                progress_dialog.set_message("AI学習データを収集中...")
                try:
                    from modules.ai_predictor import get_ai_predictor
                    ai_predictor = get_ai_predictor()
                    if hasattr(ai_predictor, 'usage_tracker'):
                        export_data["data"]["ai_learning"] = {
                            "usage_data": dict(ai_predictor.usage_tracker.usage_data),
                            "learning_history": getattr(ai_predictor, 'learning_history', {})
                        }
                    else:
                        export_data["data"]["ai_learning"] = {"error": "AI predictor not available"}
                except Exception as e:
                    app_instance.logger.error(f"AI学習データ収集エラー: {e}")
                    export_data["data"]["ai_learning"] = {"error": str(e)}
                
                # 3. カスタム設定
                progress_dialog.set_message("カスタム設定を収集中...")
                try:
                    from modules.customization import customization_manager
                    export_data["data"]["customization"] = {
                        "user_settings": customization_manager.user_settings.settings,
                        "custom_keywords": customization_manager.keyword_manager.custom_keywords,
                        "custom_rules": customization_manager.rule_manager.custom_rules
                    }
                except Exception as e:
                    app_instance.logger.error(f"カスタム設定収集エラー: {e}")
                    export_data["data"]["customization"] = {"error": str(e)}
                
                # 4. テーマ設定
                progress_dialog.set_message("テーマ設定を収集中...")
                try:
                    export_data["data"]["theme"] = {
                        "current_theme": app_instance.theme_manager.current_theme,
                        "available_themes": app_instance.theme_manager.get_available_themes()
                    }
                except Exception as e:
                    app_instance.logger.error(f"テーマ設定収集エラー: {e}")
                    export_data["data"]["theme"] = {"error": str(e)}
                
                # 5. カテゴリ設定
                progress_dialog.set_message("カテゴリ設定を収集中...")
                try:
                    export_data["data"]["categories"] = {
                        "category_keywords": getattr(app_instance, 'category_keywords', {}),
                        "category_descriptions": getattr(app_instance, 'category_descriptions', {}),
                        "prompt_structure_priorities": getattr(app_instance, 'prompt_structure_priorities', {})
                    }
                except Exception as e:
                    app_instance.logger.error(f"カテゴリ設定収集エラー: {e}")
                    export_data["data"]["categories"] = {"error": str(e)}
                
                # 6. 統計情報
                progress_dialog.set_message("統計情報を収集中...")
                try:
                    all_tags = app_instance.tag_manager.get_all_tags()
                    export_data["data"]["statistics"] = {
                        "total_tags": len(all_tags),
                        "positive_tags_count": len([t for t in all_tags if not t.get("is_negative", False)]),
                        "negative_tags_count": len([t for t in all_tags if t.get("is_negative", False)]),
                        "favorite_tags_count": len([t for t in all_tags if t.get("favorite", False)]),
                        "categories_count": len(set(t.get("category", "") for t in all_tags if t.get("category")))
                    }
                except Exception as e:
                    app_instance.logger.error(f"統計情報収集エラー: {e}")
                    export_data["data"]["statistics"] = {"error": str(e)}
                
                # 7. メタデータ
                progress_dialog.set_message("メタデータを収集中...")
                try:
                    export_data["data"]["metadata"] = {
                        "database_file": getattr(app_instance.tag_manager, 'db_file', ''),
                        "backup_directory": getattr(app_instance, 'backup_dir', ''),
                        "last_backup": _get_last_backup_date(app_instance)
                    }
                except Exception as e:
                    app_instance.logger.error(f"メタデータ収集エラー: {e}")
                    export_data["data"]["metadata"] = {"error": str(e)}
                
                # ファイルに保存
                progress_dialog.set_message("ファイルに保存中...")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                
                # 完了メッセージを表示
                app_instance.root.after(0, lambda: show_completion())
                
            except Exception as e:
                app_instance.logger.error(f"エクスポート処理エラー: {e}")
                app_instance.root.after(0, lambda: show_error(str(e)))
        
        def show_completion():
            progress_dialog.close()
            messagebox.showinfo(
                "エクスポート完了",
                f"個人データのエクスポートが完了しました。\n\n"
                f"保存先: {file_path}",
                parent=app_instance.root
            )
        
        def show_error(error_msg: str):
            progress_dialog.close()
            messagebox.showerror(
                "エクスポートエラー",
                f"個人データのエクスポート中にエラーが発生しました。\n\n"
                f"エラー: {error_msg}",
                parent=app_instance.root
            )
        
        # ワーカースレッドを開始
        thread = threading.Thread(target=export_worker, daemon=True)
        thread.start()
        
    except Exception as e:
        app_instance.logger.error(f"エクスポート初期化エラー: {e}")
        messagebox.showerror(
            "エクスポートエラー",
            f"エクスポート機能の初期化中にエラーが発生しました。\n\n"
            f"エラー: {e}",
            parent=app_instance.root
        )

def import_personal_data(app_instance: Any) -> None:
    """個人データ包括的インポート機能"""
    try:
        # 安全なデフォルトディレクトリを設定
        default_dir = get_safe_path(os.getcwd(), "exports")
        if not os.path.exists(default_dir):
            os.makedirs(default_dir, exist_ok=True)
        
        file_path = filedialog.askopenfilename(
            title="個人データをインポート",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=default_dir
        )
        
        if not file_path:
            return
        
        try:
            # ファイルを読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
        except Exception as e:
            messagebox.showerror(
                "ファイル読み込みエラー",
                f"ファイルの読み込みに失敗しました。\n\n"
                f"エラー: {e}",
                parent=app_instance.root
            )
            return
        
        # バージョンチェック
        if import_data.get("version") != "1.0":
            messagebox.showwarning(
                "バージョン警告",
                f"このファイルは異なるバージョン（{import_data.get('version', '不明')}）で作成されています。\n"
                "互換性の問題が発生する可能性があります。",
                parent=app_instance.root
            )
        
        # 確認ダイアログ
        result = messagebox.askyesno(
            "インポート確認",
            f"以下の個人データをインポートしますか？\n\n"
            f"ファイル: {os.path.basename(file_path)}\n"
            f"エクスポート日: {import_data.get('export_date', '不明')}\n"
            f"アプリバージョン: {import_data.get('app_version', '不明')}\n\n"
            f"現在のデータは上書きされます。",
            parent=app_instance.root
        )
        
        if not result:
            return
        
        # プログレスダイアログを表示
        progress_dialog = ProgressDialog(
            app_instance.root,
            "個人データインポート中",
            "データを読み込み中..."
        )
        
        def import_worker():
            try:
                data = import_data.get("data", {})
                import_errors = []
                
                # 1. タグデータのインポート
                progress_dialog.set_message("タグデータをインポート中...")
                if "tags" in data and "error" not in data["tags"]:
                    try:
                        tags_data = data["tags"]
                        # ポジティブタグのインポート
                        for tag_info in tags_data.get("positive_tags", []):
                            try:
                                app_instance.tag_manager.add_tag(
                                    tag_info["tag"], 
                                    is_negative=False,
                                    category=tag_info.get("category", ""),
                                    jp=tag_info.get("jp", ""),
                                    favorite=tag_info.get("favorite", False)
                                )
                            except Exception as e:
                                import_errors.append(f"ポジティブタグ '{tag_info.get('tag', '')}' のインポートエラー: {e}")
                        
                        # ネガティブタグのインポート
                        for tag_info in tags_data.get("negative_tags", []):
                            try:
                                app_instance.tag_manager.add_tag(
                                    tag_info["tag"], 
                                    is_negative=True,
                                    category=tag_info.get("category", ""),
                                    jp=tag_info.get("jp", ""),
                                    favorite=tag_info.get("favorite", False)
                                )
                            except Exception as e:
                                import_errors.append(f"ネガティブタグ '{tag_info.get('tag', '')}' のインポートエラー: {e}")
                    except Exception as e:
                        import_errors.append(f"タグデータインポートエラー: {e}")
                
                # 2. AI学習データのインポート
                progress_dialog.set_message("AI学習データをインポート中...")
                if "ai_learning" in data and "error" not in data["ai_learning"]:
                    try:
                        from modules.ai_predictor import get_ai_predictor
                        ai_predictor = get_ai_predictor()
                        if hasattr(ai_predictor, 'usage_tracker'):
                            ai_predictor.usage_tracker.usage_data.update(data["ai_learning"].get("usage_data", {}))
                            if hasattr(ai_predictor, 'learning_history'):
                                ai_predictor.learning_history.update(data["ai_learning"].get("learning_history", {}))
                        else:
                            import_errors.append("AI predictor not available")
                    except Exception as e:
                        import_errors.append(f"AI学習データインポートエラー: {e}")
                
                # 3. カスタム設定のインポート
                progress_dialog.set_message("カスタム設定をインポート中...")
                if "customization" in data and "error" not in data["customization"]:
                    try:
                        from modules.customization import customization_manager
                        customization_manager.user_settings.settings.update(data["customization"].get("user_settings", {}))
                        customization_manager.keyword_manager.custom_keywords.update(data["customization"].get("custom_keywords", {}))
                        customization_manager.rule_manager.custom_rules.update(data["customization"].get("custom_rules", {}))
                    except Exception as e:
                        import_errors.append(f"カスタム設定インポートエラー: {e}")
                
                # 4. テーマ設定のインポート
                progress_dialog.set_message("テーマ設定をインポート中...")
                if "theme" in data and "error" not in data["theme"]:
                    try:
                        theme_data = data["theme"]
                        if "current_theme" in theme_data:
                            app_instance.theme_manager.current_theme = theme_data["current_theme"]
                            app_instance.apply_theme(theme_data["current_theme"])
                    except Exception as e:
                        import_errors.append(f"テーマ設定インポートエラー: {e}")
                
                # 5. カテゴリ設定のインポート
                progress_dialog.set_message("カテゴリ設定をインポート中...")
                if "categories" in data and "error" not in data["categories"]:
                    try:
                        categories_data = data["categories"]
                        if "category_keywords" in categories_data:
                            app_instance.category_keywords.update(categories_data["category_keywords"])
                        if "category_descriptions" in categories_data:
                            app_instance.category_descriptions.update(categories_data["category_descriptions"])
                        if "prompt_structure_priorities" in categories_data:
                            app_instance.prompt_structure_priorities.update(categories_data["prompt_structure_priorities"])
                    except Exception as e:
                        import_errors.append(f"カテゴリ設定インポートエラー: {e}")
                
                # UIの更新をメインスレッドで実行
                progress_dialog.set_message("UIを更新中...")
                app_instance.root.after(0, lambda: update_ui_and_complete(import_errors))
                
            except Exception as e:
                app_instance.logger.error(f"インポート処理エラー: {e}")
                app_instance.root.after(0, lambda: show_error(str(e)))
        
        def update_ui_and_complete(import_errors: List[str]):
            """UIを更新して完了処理を実行"""
            try:
                # 各タブの更新を個別に実行
                if hasattr(app_instance, 'refresh_tabs'):
                    app_instance.refresh_tabs()
                
                # カテゴリリストの更新
                if hasattr(app_instance, 'update_category_list'):
                    app_instance.update_category_list()
                
                # タグリストの更新
                if hasattr(app_instance, 'refresh_tag_list'):
                    app_instance.refresh_tag_list()
                
                # 完了メッセージを表示
                show_completion(import_errors)
                
            except Exception as e:
                import_errors.append(f"UI更新エラー: {e}")
                # エラーが発生しても完了メッセージを表示
                show_completion(import_errors)
        
        def show_completion(import_errors: List[str]):
            progress_dialog.close()
            if import_errors:
                error_message = "\n".join(import_errors[:10])  # 最初の10個のエラーのみ表示
                if len(import_errors) > 10:
                    error_message += f"\n... 他 {len(import_errors) - 10} 個のエラー"
                
                messagebox.showwarning(
                    "インポート完了（一部エラー）",
                    f"個人データのインポートが完了しましたが、一部のデータでエラーが発生しました。\n\n"
                    f"エラー詳細:\n{error_message}",
                    parent=app_instance.root
                )
            else:
                messagebox.showinfo(
                    "インポート完了",
                    "個人データのインポートが正常に完了しました。",
                    parent=app_instance.root
                )
        
        def show_error(error_msg: str):
            progress_dialog.close()
            messagebox.showerror(
                "インポートエラー",
                f"個人データのインポート中にエラーが発生しました。\n\n"
                f"エラー: {error_msg}",
                parent=app_instance.root
            )
        
        # ワーカースレッドを開始
        thread = threading.Thread(target=import_worker, daemon=True)
        thread.start()
        
    except Exception as e:
        messagebox.showerror(
            "エラー",
            f"インポートファイルの読み込みに失敗しました:\n{str(e)}",
            parent=app_instance.root
        )

def _get_last_backup_date(app_instance: Any) -> str:
    """最終バックアップ日を取得"""
    try:
        backup_dir = getattr(app_instance, 'backup_dir', 'backup')
        if os.path.exists(backup_dir):
            backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
            if backup_files:
                # 最新のバックアップファイルの日時を取得
                latest_backup = max(backup_files, key=lambda f: os.path.getmtime(os.path.join(backup_dir, f)))
                timestamp = os.path.getmtime(os.path.join(backup_dir, latest_backup))
                return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        app_instance.logger.error(f"バックアップ日取得エラー: {e}")
    return "不明"

def export_tags(app_instance: Any, tree: Any) -> None:
    """選択したタグをエクスポート"""
    selected_items = tree.selection()
    if not selected_items:
        messagebox.showwarning("警告", "エクスポートするタグを選択してください。", parent=app_instance.root)
        return
    
    file_path = filedialog.asksaveasfilename(
        title="タグをエクスポート",
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")]
    )
    
    if not file_path:
        return
    
    try:
        # 選択されたタグの情報を取得
        tags_data = []
        for item in selected_items:
            values = tree.item(item, "values")
            if len(values) >= 4:
                tags_data.append({
                    "tag": values[0],
                    "jp": values[1],
                    "favorite": values[2] == "★",
                    "category": values[3]
                })
        
        # ファイル形式に応じて保存
        if file_path.lower().endswith('.csv'):
            import csv
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Tag', 'Japanese', 'Favorite', 'Category'])
                for tag_info in tags_data:
                    writer.writerow([
                        tag_info['tag'],
                        tag_info['jp'],
                        '★' if tag_info['favorite'] else '',
                        tag_info['category']
                    ])
        else:
            # JSON形式で保存
            export_data = {
                "export_date": datetime.datetime.now().isoformat(),
                "tags": tags_data
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        messagebox.showinfo(
            "エクスポート完了",
            f"{len(tags_data)}個のタグをエクスポートしました。\n保存先: {file_path}",
            parent=app_instance.root
        )
        
    except Exception as e:
        messagebox.showerror(
            "エクスポートエラー",
            f"タグのエクスポート中にエラーが発生しました:\n{str(e)}",
            parent=app_instance.root
        )

def export_all_tags(app_instance: Any) -> None:
    """全タグをエクスポート"""
    file_path = filedialog.asksaveasfilename(
        title="全タグをエクスポート",
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")]
    )
    
    if not file_path:
        return
    
    try:
        # 全タグの情報を取得
        all_tags = app_instance.tag_manager.get_all_tags()
        
        # ファイル形式に応じて保存
        if file_path.lower().endswith('.csv'):
            import csv
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Tag', 'Japanese', 'Favorite', 'Category', 'IsNegative'])
                for tag_info in all_tags:
                    writer.writerow([
                        tag_info['tag'],
                        tag_info.get('jp', ''),
                        '★' if tag_info.get('favorite', False) else '',
                        tag_info.get('category', ''),
                        'Yes' if tag_info.get('is_negative', False) else 'No'
                    ])
        else:
            # JSON形式で保存
            export_data = {
                "export_date": datetime.datetime.now().isoformat(),
                "total_tags": len(all_tags),
                "tags": all_tags
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        messagebox.showinfo(
            "エクスポート完了",
            f"{len(all_tags)}個のタグをエクスポートしました。\n保存先: {file_path}",
            parent=app_instance.root
        )
        
    except Exception as e:
        messagebox.showerror(
            "エクスポートエラー",
            f"全タグのエクスポート中にエラーが発生しました:\n{str(e)}",
            parent=app_instance.root
        )

def backup_database(app_instance: Any) -> None:
    """データベースバックアップ機能"""
    from modules.constants import DB_FILE
    
    if not os.path.exists(DB_FILE):
        messagebox.showerror("エラー", "データベースファイルが見つかりません。", parent=app_instance.root)
        return
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join('backup', f"tags_backup_{timestamp}.db")
    
    try:
        # バックアップディレクトリが存在しない場合は作成
        os.makedirs('backup', exist_ok=True)
        shutil.copy(DB_FILE, backup_file)
        messagebox.showinfo(
            "バックアップ完了", 
            f"バックアップを作成しました：\n{backup_file}", 
            parent=app_instance.root
        )
    except (IOError, shutil.Error) as e:
        app_instance.logger.error(f"バックアップに失敗しました: {e}")
        messagebox.showerror(
            "エラー", 
            f"バックアップに失敗しました：{e}", 
            parent=app_instance.root
        ) 