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

from .ui_dialogs import ProgressDialog

def export_personal_data(app_instance: Any) -> None:
    """個人データ包括的エクスポート機能"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    default_filename = f"personal_data_export_{timestamp}.json"
    
    file_path = filedialog.asksaveasfilename(
        title="個人データをエクスポート",
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        initialfile=default_filename
    )
    
    if not file_path:
        return
    
    try:
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
                all_tags = app_instance.tag_manager.get_all_tags()
                export_data["data"]["tags"] = {
                    "positive_tags": [t for t in all_tags if not t.get("is_negative", False)],
                    "negative_tags": [t for t in all_tags if t.get("is_negative", False)],
                    "recent_tags": app_instance.tag_manager.get_recent_tags()
                }
                
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
                except Exception as e:
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
                    export_data["data"]["customization"] = {"error": str(e)}
                
                # 4. テーマ設定
                progress_dialog.set_message("テーマ設定を収集中...")
                export_data["data"]["theme"] = {
                    "current_theme": app_instance.theme_manager.current_theme,
                    "available_themes": app_instance.theme_manager.get_available_themes()
                }
                
                # 5. カテゴリ設定
                progress_dialog.set_message("カテゴリ設定を収集中...")
                export_data["data"]["categories"] = {
                    "category_keywords": app_instance.category_keywords,
                    "category_descriptions": app_instance.category_descriptions,
                    "prompt_structure_priorities": app_instance.prompt_structure_priorities
                }
                
                # 6. 統計情報
                progress_dialog.set_message("統計情報を収集中...")
                export_data["data"]["statistics"] = {
                    "total_tags": len(all_tags),
                    "positive_tags_count": len([t for t in all_tags if not t.get("is_negative", False)]),
                    "negative_tags_count": len([t for t in all_tags if t.get("is_negative", False)]),
                    "favorite_tags_count": len([t for t in all_tags if t.get("favorite", False)]),
                    "categories_count": len(set(t.get("category", "") for t in all_tags if t.get("category")))
                }
                
                # 7. メタデータ
                progress_dialog.set_message("メタデータを収集中...")
                export_data["data"]["metadata"] = {
                    "database_file": app_instance.tag_manager.db_file,
                    "backup_directory": getattr(app_instance, 'backup_dir', ''),
                    "last_backup": _get_last_backup_date(app_instance)
                }
                
                # データをJSONファイルに保存
                progress_dialog.set_message("ファイルに保存中...")
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                
                def show_completion():
                    progress_dialog.close()
                    messagebox.showinfo(
                        "エクスポート完了",
                        f"個人データのエクスポートが完了しました。\n\n保存先: {file_path}\n\nエクスポート内容:\n"
                        f"・タグデータ: {len(export_data['data']['tags']['positive_tags'])}個のポジティブタグ, "
                        f"{len(export_data['data']['tags']['negative_tags'])}個のネガティブタグ\n"
                        f"・AI学習データ: {'含む' if 'error' not in export_data['data']['ai_learning'] else 'エラー'}\n"
                        f"・カスタム設定: {'含む' if 'error' not in export_data['data']['customization'] else 'エラー'}\n"
                        f"・テーマ設定: {export_data['data']['theme']['current_theme']}\n"
                        f"・カテゴリ設定: {len(export_data['data']['categories']['category_keywords'])}個のカテゴリ",
                        parent=app_instance.root
                    )
                app_instance.root.after(0, show_completion)
                
            except Exception as e:
                error_message = str(e)
                def show_error():
                    progress_dialog.close()
                    messagebox.showerror(
                        "エクスポートエラー",
                        f"個人データのエクスポート中にエラーが発生しました:\n{error_message}",
                        parent=app_instance.root
                    )
                app_instance.root.after(0, show_error)
        
        # 非同期でエクスポート実行
        export_thread = threading.Thread(target=export_worker)
        export_thread.daemon = True
        export_thread.start()
        
    except Exception as e:
        messagebox.showerror(
            "エラー",
            f"エクスポートの開始に失敗しました:\n{str(e)}",
            parent=app_instance.root
        )

def import_personal_data(app_instance: Any) -> None:
    """個人データ包括的インポート機能"""
    file_path = filedialog.askopenfilename(
        title="個人データをインポート",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    
    if not file_path:
        return
    
    try:
        # ファイルを読み込み
        with open(file_path, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
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
                
                # 1. タグデータのインポート
                progress_dialog.set_message("タグデータをインポート中...")
                if "tags" in data:
                    tags_data = data["tags"]
                    # ポジティブタグのインポート
                    for tag_info in tags_data.get("positive_tags", []):
                        app_instance.tag_manager.add_tag(
                            tag_info["tag"], 
                            is_negative=False,
                            category=tag_info.get("category", ""),
                            jp=tag_info.get("jp", ""),
                            favorite=tag_info.get("favorite", False)
                        )
                    
                    # ネガティブタグのインポート
                    for tag_info in tags_data.get("negative_tags", []):
                        app_instance.tag_manager.add_tag(
                            tag_info["tag"], 
                            is_negative=True,
                            category=tag_info.get("category", ""),
                            jp=tag_info.get("jp", ""),
                            favorite=tag_info.get("favorite", False)
                        )
                
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
                    except Exception as e:
                        app_instance.logger.error(f"AI学習データのインポートエラー: {e}")
                
                # 3. カスタム設定のインポート
                progress_dialog.set_message("カスタム設定をインポート中...")
                if "customization" in data and "error" not in data["customization"]:
                    try:
                        from modules.customization import customization_manager
                        customization_manager.user_settings.settings.update(data["customization"].get("user_settings", {}))
                        customization_manager.keyword_manager.custom_keywords.update(data["customization"].get("custom_keywords", {}))
                        customization_manager.rule_manager.custom_rules.update(data["customization"].get("custom_rules", {}))
                    except Exception as e:
                        app_instance.logger.error(f"カスタム設定のインポートエラー: {e}")
                
                # 4. テーマ設定のインポート
                progress_dialog.set_message("テーマ設定をインポート中...")
                if "theme" in data:
                    theme_data = data["theme"]
                    if theme_data.get("current_theme"):
                        app_instance.theme_manager.current_theme = theme_data["current_theme"]
                        app_instance.apply_theme(theme_data["current_theme"])
                
                # 5. カテゴリ設定のインポート
                progress_dialog.set_message("カテゴリ設定をインポート中...")
                if "categories" in data:
                    categories_data = data["categories"]
                    if "category_keywords" in categories_data:
                        app_instance.category_keywords.update(categories_data["category_keywords"])
                    if "category_descriptions" in categories_data:
                        app_instance.category_descriptions.update(categories_data["category_descriptions"])
                    if "prompt_structure_priorities" in categories_data:
                        app_instance.prompt_structure_priorities.update(categories_data["prompt_structure_priorities"])
                
                # UIの更新
                progress_dialog.set_message("UIを更新中...")
                app_instance.refresh_tabs()
                
                def show_completion():
                    progress_dialog.close()
                    messagebox.showinfo(
                        "インポート完了",
                        f"個人データのインポートが完了しました。\n\n"
                        f"インポート内容:\n"
                        f"・タグデータ: {'含む' if 'tags' in data else 'なし'}\n"
                        f"・AI学習データ: {'含む' if 'ai_learning' in data and 'error' not in data['ai_learning'] else 'なし'}\n"
                        f"・カスタム設定: {'含む' if 'customization' in data and 'error' not in data['customization'] else 'なし'}\n"
                        f"・テーマ設定: {'含む' if 'theme' in data else 'なし'}\n"
                        f"・カテゴリ設定: {'含む' if 'categories' in data else 'なし'}",
                        parent=app_instance.root
                    )
                app_instance.root.after(0, show_completion)
                
            except Exception as e:
                error_message = str(e)
                def show_error():
                    progress_dialog.close()
                    messagebox.showerror(
                        "インポートエラー",
                        f"個人データのインポート中にエラーが発生しました:\n{error_message}",
                        parent=app_instance.root
                    )
                app_instance.root.after(0, show_error)
        
        # 非同期でインポート実行
        import_thread = threading.Thread(target=import_worker)
        import_thread.daemon = True
        import_thread.start()
        
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