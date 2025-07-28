#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI機能テストスクリプト
ローカルAI機能の動作確認とパフォーマンステスト
"""

import sys
import os
import time
import json
from typing import List, Dict, Any

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ai_predictor():
    """AI予測機能のテスト"""
    print("=== AI予測機能テスト ===")
    
    try:
        from modules.ai_predictor import get_ai_predictor
        
        # AI予測器を取得
        ai_predictor = get_ai_predictor()
        print("✓ AI予測器の初期化完了")
        
        # テストタグ
        test_tags = [
            "beautiful", "landscape", "portrait", "anime", "realistic",
            "watercolor", "oil painting", "digital art", "photography",
            "night", "sunset", "forest", "mountain", "ocean"
        ]
        
        print(f"\nテストタグ数: {len(test_tags)}")
        
        # 予測テスト
        results = []
        start_time = time.time()
        
        for tag in test_tags:
            try:
                category, confidence, details = ai_predictor.predict_category_with_confidence(tag)
                results.append({
                    "tag": tag,
                    "category": category,
                    "confidence": confidence,
                    "reason": details.get("reason", "不明")
                })
                print(f"✓ {tag} -> {category} (信頼度: {confidence:.2f})")
            except Exception as e:
                print(f"✗ {tag} -> エラー: {e}")
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"\n=== テスト結果 ===")
        print(f"処理時間: {elapsed_time:.2f}秒")
        print(f"平均処理時間: {elapsed_time/len(test_tags):.3f}秒/タグ")
        
        # 結果の統計
        categories = {}
        confidences = []
        
        for result in results:
            cat = result["category"]
            categories[cat] = categories.get(cat, 0) + 1
            confidences.append(result["confidence"])
        
        print(f"\nカテゴリ分布:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat}: {count}件")
        
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            print(f"\n平均信頼度: {avg_confidence:.3f}")
            print(f"最高信頼度: {max(confidences):.3f}")
            print(f"最低信頼度: {min(confidences):.3f}")
        
        return True
        
    except Exception as e:
        print(f"✗ AI予測機能テストエラー: {e}")
        return False

def test_huggingface_manager():
    """Hugging Face Managerのテスト"""
    print("\n=== Hugging Face Managerテスト ===")
    
    try:
        from modules.huggingface_manager import HuggingFaceManager
        
        # マネージャーを初期化
        hf_manager = HuggingFaceManager()
        print("✓ Hugging Face Manager初期化完了")
        
        # モデル読み込み待機
        print("モデル読み込み中...")
        if hf_manager.wait_for_load(timeout=60.0):
            print("✓ モデル読み込み完了")
        else:
            print("✗ モデル読み込みタイムアウト")
            return False
        
        # 類似度計算テスト
        test_pairs = [
            ("beautiful", "gorgeous"),
            ("landscape", "scenery"),
            ("portrait", "face"),
            ("anime", "cartoon"),
            ("realistic", "photorealistic")
        ]
        
        print(f"\n類似度計算テスト:")
        for tag1, tag2 in test_pairs:
            try:
                similarity = hf_manager.calculate_similarity(tag1, tag2)
                print(f"✓ {tag1} - {tag2}: {similarity:.3f}")
            except Exception as e:
                print(f"✗ {tag1} - {tag2}: エラー - {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Hugging Face Managerテストエラー: {e}")
        return False

def test_local_hf_manager():
    """ローカルHF Managerのテスト"""
    print("\n=== ローカルHF Managerテスト ===")
    
    try:
        from modules.local_hf_manager import LocalHuggingFaceManager
        
        # マネージャーを初期化
        local_hf_manager = LocalHuggingFaceManager()
        print("✓ ローカルHF Manager初期化完了")
        
        # モデル読み込み待機
        print("ローカルモデル読み込み中...")
        if local_hf_manager.wait_for_load(timeout=120.0):
            print("✓ ローカルモデル読み込み完了")
        else:
            print("✗ ローカルモデル読み込みタイムアウト")
            return False
        
        # 埋め込み計算テスト
        test_tags = ["beautiful", "landscape", "portrait"]
        
        print(f"\n埋め込み計算テスト:")
        for tag in test_tags:
            try:
                embedding = local_hf_manager.get_tag_embedding(tag)
                if embedding is not None:
                    print(f"✓ {tag}: 埋め込みベクトル取得成功 ({len(embedding)}次元)")
                else:
                    print(f"✗ {tag}: 埋め込みベクトル取得失敗")
            except Exception as e:
                print(f"✗ {tag}: エラー - {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ ローカルHF Managerテストエラー: {e}")
        return False

def test_ai_settings():
    """AI設定のテスト"""
    print("\n=== AI設定テスト ===")
    
    try:
        settings_file = os.path.join('resources', 'config', 'ai_settings.json')
        
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            print("✓ AI設定ファイル読み込み完了")
            print(f"ローカルAI無効化: {settings.get('local_ai_disabled', '未設定')}")
            print(f"GPU使用: {settings.get('use_gpu', '未設定')}")
            print(f"モデル名: {settings.get('model_name', '未設定')}")
            print(f"信頼度閾値: {settings.get('confidence_threshold', '未設定')}")
            
            return True
        else:
            print("✗ AI設定ファイルが見つかりません")
            return False
            
    except Exception as e:
        print(f"✗ AI設定テストエラー: {e}")
        return False

def main():
    """メイン関数"""
    print("AI機能テスト開始")
    print("=" * 50)
    
    # テスト実行
    tests = [
        ("AI設定", test_ai_settings),
        ("AI予測機能", test_ai_predictor),
        ("Hugging Face Manager", test_huggingface_manager),
        ("ローカルHF Manager", test_local_hf_manager)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"✗ {test_name}テストで予期しないエラー: {e}")
            results[test_name] = False
    
    # 結果サマリー
    print("\n" + "=" * 50)
    print("テスト結果サマリー")
    print("=" * 50)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✓ 成功" if result else "✗ 失敗"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n成功率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 全てのテストが成功しました！")
    else:
        print("⚠️  一部のテストが失敗しました。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 