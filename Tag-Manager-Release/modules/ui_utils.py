# -*- coding: utf-8 -*-
"""
UIユーティリティ機能モジュール
"""
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import simpledialog, messagebox, Menu, filedialog, Toplevel
import tkinter as tk
from tkinter import ttk
import threading
import os
import json
import re
import time
from typing import Any, Dict, List, Optional, Callable, cast, Tuple
import queue

# --- テスト容易化のためのロジック分離 ---
def build_category_list(category_keywords: Dict[str, List[str]]) -> List[str]:
    """
    カテゴリキーワード辞書から、全カテゴリリストを生成する純粋関数。
    """
    return ["全カテゴリ", "お気に入り", "最近使った", "未分類"] + list(category_keywords.keys())

def build_category_descriptions() -> Dict[str, str]:
    """
    全カテゴリの説明辞書を返す純粋関数。
    """
    return {
        "全カテゴリ": "全てのタグを一覧表示します。",
        "お気に入り": "お気に入りに登録されたタグが表示されます。",
        "最近使った": "最近使用したタグが表示されます。",
        "未分類": "どのカテゴリにも属さないタグが表示されます。",
        "品質・画質指定": "画像全体のクオリティや精細さを決定する要素。最初に指定することで、モデルが高品質な出力を目指す。",
        "スタイル・技法": "アートの雰囲気や描画技法を指定する。作品の世界観やジャンルを決定づける。",
        "キャラクター設定": "主役となる人物やキャラクターの基本属性（年齢、性別、種族など）を定義する。",
        "ポーズ・動作": "キャラクターの姿勢や動き。動的な表現や構図に影響する。",
        "服装・ファッション": "キャラクターの衣装やスタイルを指定。時代背景やジャンル感を強調できる。",
        "髪型・髪色": "髪の形状や色を指定。キャラクターの個性や印象に直結する。",
        "表情・感情": "キャラクターの顔の表情や感情を表現。感情的な深みを加える。",
        "背景・環境": "シーンの舞台や周囲の環境を指定。物語性や空間の広がりを演出する。",
        "照明・色調": "光源や色彩のトーンを指定。雰囲気や時間帯の表現に影響する。",
        "小物・アクセサリー": "キャラクターが身につける装飾品や持ち物。細部の演出や個性付けに有効。",
        "特殊効果・フィルター": "画像に加える視覚的エフェクト。幻想的な演出や動きの表現に活用。",
        "構図・カメラ視点": "視点や構図の指定。画面の切り取り方や印象を左右する。",
        "ネガティブ": "生成時に避けたい要素を指定。品質向上や意図しない出力の防止に役立つ。"
    }

def filter_tags_optimized(tags: List[Dict[str, Any]], filter_text: str, category: str) -> List[Dict[str, Any]]:
    """
    検索語でタグ名・カテゴリ・日本語訳・お気に入りを横断的にフィルタ
    """
    if not filter_text:
        return tags
    
    filter_lower = filter_text.lower()
    
    def match(t: Dict[str, Any]) -> bool:
        tag_lower = t.get("tag", "").lower()
        jp_lower = t.get("jp", "").lower()
        category_lower = t.get("category", "").lower()
        favorite = "★" if t.get("favorite", False) else ""
        
        return (filter_lower in tag_lower or 
                filter_lower in jp_lower or 
                filter_lower in category_lower or
                filter_lower in favorite)
    
    return [t for t in tags if match(t)]

def sort_prompt_by_priority(tags_data: List[Dict[str, Any]], prompt_structure_priorities: Dict[str, int]) -> List[Dict[str, Any]]:
    """プロンプト構造の優先度に基づいてタグをソート"""
    if not tags_data:
        return []
    
    tags_with_priority = []
    for item in tags_data:
        tag = item["tag"]
        weight = item["weight"]
        category = item.get("category", "")
        priority = prompt_structure_priorities.get(category, 999)
        tags_with_priority.append({"tag": tag, "weight": weight, "priority": priority})
    
    def get_priority(item: Dict[str, Any]) -> int:
        return item["priority"]
    
    sorted_tags_with_priority = sorted(tags_with_priority, key=get_priority)
    return sorted_tags_with_priority

def format_output_text(tags_data: List[Dict[str, Any]]) -> str:
    """タグデータをプロンプト形式のテキストに変換"""
    parts = []
    for item in tags_data:
        tag = item["tag"]
        weight = item["weight"]
        if weight == 1.0:
            parts.append(tag)
        else:
            parts.append(f"({tag}:{weight:.1f})")
    return ", ".join(parts)

def strip_weight_from_tag(tag: str) -> List[str]:
    """タグから重みを除去してタグ名のみを取得"""
    if tag.startswith("(") and tag.endswith(")") and ":" in tag:
        content_inside_paren = tag[1:-1]
        parts = content_inside_paren.split(":")
        if len(parts) == 2:
            tags_part = parts[0].strip()
            weight_part = parts[1].strip()
            if is_float(weight_part):
                cleaned_tags = [t.strip() for t in tags_part.split(",") if t.strip()]
                return cleaned_tags
    return [tag.strip()]

def is_float(value: str) -> bool:
    """文字列が浮動小数点数かどうかを判定"""
    try:
        float(value)
        return True
    except ValueError:
        return False

def extract_tags_from_prompt(prompt_text: str) -> List[str]:
    """プロンプトテキストからタグを抽出"""
    if not prompt_text.strip():
        return []
    
    # カンマで分割
    tags = [tag.strip() for tag in prompt_text.split(",") if tag.strip()]
    
    # 重み付きタグの処理
    extracted_tags = []
    for tag in tags:
        if tag.startswith("(") and tag.endswith(")") and ":" in tag:
            # 重み付きタグの場合
            content = tag[1:-1]
            parts = content.split(":")
            if len(parts) == 2:
                tag_name = parts[0].strip()
                weight = parts[1].strip()
                if is_float(weight):
                    extracted_tags.append(tag_name)
                else:
                    extracted_tags.append(tag)
        else:
            extracted_tags.append(tag)
    
    return extracted_tags

def make_theme_menu_command(app_instance: Any, theme_name: str) -> Callable[[], None]:
    """テーマメニューコマンドを生成"""
    def cmd() -> None:
        app_instance.apply_theme(theme_name)
    return cmd

def make_set_category_command(app_instance: Any, category: str) -> Callable[[], None]:
    """カテゴリ設定コマンドを生成"""
    def cmd() -> None:
        app_instance.set_category_from_menu(category)
    return cmd

def make_export_tags_command(app_instance: Any, tree: Any) -> Callable[[], None]:
    """タグエクスポートコマンドを生成"""
    def cmd() -> None:
        from .ui_export_import import export_tags
        export_tags(app_instance, tree)
    return cmd

def make_show_context_menu_event(app_instance: Any, tree: Any) -> Callable[[Any], None]:
    """コンテキストメニューイベントハンドラーを生成"""
    def handler(event: Any) -> None:
        app_instance.show_context_menu(event, tree)
    return handler

def make_set_status_clear(app_instance: Any) -> Callable[[], None]:
    """ステータスクリアコマンドを生成"""
    def clear() -> None:
        app_instance.status_var.set("")
    return clear

def make_set_progress_message(app_instance: Any, msg: str) -> Callable[[], None]:
    """プログレスメッセージ設定コマンドを生成"""
    def set_msg() -> None:
        if hasattr(app_instance, "progress_dialog"):
            app_instance.progress_dialog.set_message(msg)
    return set_msg

def make_close_progress_dialog(app_instance: Any) -> Callable[[], None]:
    """プログレスダイアログ閉じるコマンドを生成"""
    def close() -> None:
        if hasattr(app_instance, "progress_dialog"):
            app_instance.progress_dialog.close()
    return close

def worker_thread_fetch(app_instance: Any, q: queue.Queue[Any], filter_text: str, category_to_fetch: str) -> None:
    """非同期でタグデータを取得"""
    try:
        q.put({"type": "status", "message": f"{category_to_fetch}カテゴリのタグを読み込み中..."})
        
        if category_to_fetch == "最近使った":
            tags = app_instance.tag_manager.get_recent_tags()
        elif category_to_fetch == "ネガティブ":
            tags = app_instance.tag_manager.negative_tags
        elif category_to_fetch == "未分類":
            tags = [t for t in app_instance.tag_manager.get_all_tags() if not t.get("category") or t.get("category") == "未分類"]
        elif category_to_fetch == "全カテゴリ":
            tags = app_instance.tag_manager.get_all_tags()
        else:
            tags = app_instance.tag_manager.positive_tags
        
        filtered_tags = filter_tags_optimized(tags, filter_text, category_to_fetch)
        items = [(t["tag"], t["jp"], "★" if t.get("favorite") else "", t.get("category", "")) for t in filtered_tags]
        
        q.put({"type": "update_tree", "items": items, "category": category_to_fetch})
        q.put({"type": "status", "message": "準備完了"})
        
    except Exception as e:
        q.put({"type": "error", "message": f"エラー: {str(e)}"})

def show_guide_on_startup(app_instance: Any) -> None:
    """起動時のガイド表示"""
    # 初回起動時のみガイドを表示する場合はここに実装
    pass

def clear_search(app_instance: Any) -> None:
    """検索をクリア"""
    if hasattr(app_instance, 'search_var'):
        app_instance.search_var.set("")
        app_instance.on_search_change()

def get_search_text(app_instance: Any) -> str:
    """検索テキストを取得"""
    if hasattr(app_instance, 'search_var'):
        return app_instance.search_var.get()
    return "" 