"""
プロンプト翻訳モジュール
プロンプト出力欄に日本語で直接入力して英語に変換する機能
"""
import re
import json
import os
import logging
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from deep_translator import GoogleTranslator
from .config import BACKUP_DIR

# 翻訳キャッシュファイル
TRANSLATION_CACHE_FILE = os.path.join(BACKUP_DIR, "translation_cache.json")
# カスタム翻訳辞書ファイル
CUSTOM_TRANSLATION_FILE = os.path.join(BACKUP_DIR, "custom_translations.json")

class PromptTranslator:
    """
    プロンプト翻訳機能を提供するクラス
    日本語のプロンプトを英語に変換し、AI画像生成用のプロンプトとして最適化
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.translation_cache = self._load_translation_cache()
        self.custom_translations = self._load_custom_translations()
        self.translator = GoogleTranslator(source='ja', target='en')
        
        # プロンプト用の特殊翻訳ルール
        self.prompt_rules = {
            # 画質・品質関連
            "高画質": "high quality",
            "超高画質": "ultra high quality",
            "最高画質": "best quality",
            "マスタークオリティ": "masterpiece",
            "傑作": "masterpiece",
            "美しい": "beautiful",
            "美しい絵": "beautiful art",
            
            # スタイル関連
            "アニメ風": "anime style",
            "マンガ風": "manga style",
            "イラスト風": "illustration",
            "油絵風": "oil painting",
            "水彩画風": "watercolor",
            "デジタルアート": "digital art",
            "写真風": "photorealistic",
            "リアル": "realistic",
            
            # キャラクター関連
            "女の子": "girl",
            "男の子": "boy",
            "女性": "woman",
            "男性": "man",
            "少女": "young girl",
            "少年": "young boy",
            "美少女": "beautiful girl",
            "美少年": "beautiful boy",
            
            # 髪型・髪色
            "黒髪": "black hair",
            "茶髪": "brown hair",
            "金髪": "blonde hair",
            "銀髪": "silver hair",
            "青髪": "blue hair",
            "緑髪": "green hair",
            "赤髪": "red hair",
            "ピンク髪": "pink hair",
            "紫髪": "purple hair",
            "白髪": "white hair",
            "ロングヘア": "long hair",
            "ショートヘア": "short hair",
            "ツインテール": "twin tails",
            "ポニーテール": "ponytail",
            "ボブヘア": "bob hair",
            
            # 表情・感情
            "笑顔": "smile",
            "微笑み": "gentle smile",
            "笑い": "laughing",
            "泣き": "crying",
            "怒り": "angry",
            "悲しい": "sad",
            "驚き": "surprised",
            "困惑": "confused",
            "恥ずかしい": "embarrassed",
            "眠そう": "sleepy",
            "真剣": "serious",
            
            # 服装
            "制服": "uniform",
            "私服": "casual clothes",
            "ドレス": "dress",
            "ワンピース": "one-piece dress",
            "スカート": "skirt",
            "パンツ": "pants",
            "ジーンズ": "jeans",
            "セーター": "sweater",
            "シャツ": "shirt",
            "Tシャツ": "t-shirt",
            "コート": "coat",
            "ジャケット": "jacket",
            
            # 背景・環境
            "室内": "indoor",
            "屋外": "outdoor",
            "部屋": "room",
            "学校": "school",
            "公園": "park",
            "街": "city",
            "森": "forest",
            "海": "ocean",
            "山": "mountain",
            "空": "sky",
            "夕日": "sunset",
            "朝日": "sunrise",
            "夜": "night",
            "昼": "day",
            
            # 照明・色調
            "明るい": "bright",
            "暗い": "dark",
            "暖かい": "warm",
            "冷たい": "cold",
            "柔らかい光": "soft lighting",
            "強い光": "strong lighting",
            "逆光": "backlighting",
            "サイドライト": "side lighting",
            
            # 構図・カメラ
            "正面": "front view",
            "横顔": "profile",
            "後ろ姿": "back view",
            "上半身": "upper body",
            "全身": "full body",
            "クローズアップ": "close-up",
            "アップショット": "close-up shot",
            "ロングショット": "long shot",
            "バストショット": "bust shot",
            
            # ネガティブプロンプト
            "低画質": "low quality",
            "劣化": "degraded",
            "ぼやけ": "blurry",
            "ノイズ": "noise",
            "歪み": "distortion",
            "変形": "deformation",
            "不自然": "unnatural",
            "醜い": "ugly",
            "汚い": "dirty",
            "破損": "damaged",
            "不完全": "incomplete",
            "重複": "duplicate",
            "エラー": "error",
            "テキスト": "text",
            "署名": "signature",
            "透かし": "watermark",
            "ロゴ": "logo",
            "ブランド": "brand",
            "著作権": "copyright",
            "トレース": "tracing",
            "コピー": "copy",
            "盗作": "plagiarism"
        }
    
    def _load_translation_cache(self) -> Dict[str, str]:
        """翻訳キャッシュを読み込む"""
        try:
            if os.path.exists(TRANSLATION_CACHE_FILE):
                with open(TRANSLATION_CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"翻訳キャッシュの読み込みに失敗: {e}")
        return {}
    
    def _save_translation_cache(self) -> None:
        """翻訳キャッシュを保存する"""
        try:
            os.makedirs(os.path.dirname(TRANSLATION_CACHE_FILE), exist_ok=True)
            with open(TRANSLATION_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.translation_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"翻訳キャッシュの保存に失敗: {e}")
    
    def _load_custom_translations(self) -> Dict[str, str]:
        """カスタム翻訳辞書を読み込む"""
        try:
            if os.path.exists(CUSTOM_TRANSLATION_FILE):
                with open(CUSTOM_TRANSLATION_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"カスタム翻訳辞書の読み込みに失敗: {e}")
        return {}
    
    def _save_custom_translations(self) -> None:
        """カスタム翻訳辞書を保存する"""
        try:
            os.makedirs(os.path.dirname(CUSTOM_TRANSLATION_FILE), exist_ok=True)
            with open(CUSTOM_TRANSLATION_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.custom_translations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"カスタム翻訳辞書の保存に失敗: {e}")
    
    def add_custom_translation(self, japanese: str, english: str) -> bool:
        """
        カスタム翻訳を追加する
        
        Args:
            japanese: 日本語のテキスト
            english: 英語の翻訳
            
        Returns:
            bool: 追加成功時True
        """
        try:
            self.custom_translations[japanese.strip()] = english.strip()
            self._save_custom_translations()
            return True
        except Exception as e:
            self.logger.error(f"カスタム翻訳の追加に失敗: {e}")
            return False
    
    def remove_custom_translation(self, japanese: str) -> bool:
        """
        カスタム翻訳を削除する
        
        Args:
            japanese: 削除する日本語のテキスト
            
        Returns:
            bool: 削除成功時True
        """
        try:
            if japanese in self.custom_translations:
                del self.custom_translations[japanese]
                self._save_custom_translations()
                return True
            return False
        except Exception as e:
            self.logger.error(f"カスタム翻訳の削除に失敗: {e}")
            return False
    
    def get_custom_translations(self) -> Dict[str, str]:
        """カスタム翻訳辞書を取得する"""
        return self.custom_translations.copy()
    
    def translate_prompt(self, japanese_text: str, use_cache: bool = True) -> str:
        """
        日本語のプロンプトを英語に翻訳する
        
        Args:
            japanese_text: 翻訳する日本語テキスト
            use_cache: キャッシュを使用するかどうか
            
        Returns:
            str: 翻訳された英語テキスト
        """
        if not japanese_text.strip():
            return ""
        
        # キャッシュチェック
        if use_cache and japanese_text in self.translation_cache:
            return self.translation_cache[japanese_text]
        
        # カスタム翻訳チェック
        if japanese_text in self.custom_translations:
            result = self.custom_translations[japanese_text]
            if use_cache:
                self.translation_cache[japanese_text] = result
                self._save_translation_cache()
            return result
        
        # プロンプトルールチェック
        if japanese_text in self.prompt_rules:
            result = self.prompt_rules[japanese_text]
            if use_cache:
                self.translation_cache[japanese_text] = result
                self._save_translation_cache()
            return result
        
        # Google翻訳APIを使用
        try:
            result = self.translator.translate(japanese_text)
            if use_cache:
                self.translation_cache[japanese_text] = result
                self._save_translation_cache()
            return result
        except Exception as e:
            self.logger.error(f"翻訳に失敗: {e}")
            return japanese_text  # 翻訳失敗時は元のテキストを返す
    
    def translate_prompt_with_analysis(self, japanese_text: str) -> Dict[str, Any]:
        """
        日本語のプロンプトを英語に翻訳し、分析結果も返す
        
        Args:
            japanese_text: 翻訳する日本語テキスト
            
        Returns:
            Dict[str, Any]: 翻訳結果と分析情報
        """
        result = {
            "original": japanese_text,
            "translated": "",
            "translation_method": "",
            "confidence": 0.0,
            "suggestions": [],
            "warnings": []
        }
        
        if not japanese_text.strip():
            return result
        
        # 翻訳方法の決定
        if japanese_text in self.custom_translations:
            result["translated"] = self.custom_translations[japanese_text]
            result["translation_method"] = "custom"
            result["confidence"] = 1.0
        elif japanese_text in self.prompt_rules:
            result["translated"] = self.prompt_rules[japanese_text]
            result["translation_method"] = "prompt_rule"
            result["confidence"] = 0.9
        elif japanese_text in self.translation_cache:
            result["translated"] = self.translation_cache[japanese_text]
            result["translation_method"] = "cache"
            result["confidence"] = 0.8
        else:
            # Google翻訳を使用
            try:
                result["translated"] = self.translator.translate(japanese_text)
                result["translation_method"] = "google_translate"
                result["confidence"] = 0.7
                
                # キャッシュに保存
                self.translation_cache[japanese_text] = result["translated"]
                self._save_translation_cache()
            except Exception as e:
                result["translated"] = japanese_text
                result["translation_method"] = "fallback"
                result["confidence"] = 0.0
                result["warnings"].append(f"翻訳に失敗しました: {e}")
        
        # 提案の生成
        result["suggestions"] = self._generate_suggestions(japanese_text, result["translated"])
        
        return result
    
    def _generate_suggestions(self, original: str, translated: str) -> List[str]:
        """翻訳結果に対する提案を生成する"""
        suggestions = []
        
        # プロンプト用の改善提案
        if "quality" not in translated.lower() and "画質" in original:
            suggestions.append("高画質の指定を追加することをお勧めします")
        
        if "masterpiece" not in translated.lower() and any(word in original for word in ["傑作", "美しい", "最高"]):
            suggestions.append("masterpieceタグの追加を検討してください")
        
        if "anime" not in translated.lower() and any(word in original for word in ["アニメ", "マンガ", "イラスト"]):
            suggestions.append("アニメ風の指定を追加することをお勧めします")
        
        return suggestions
    
    def batch_translate(self, japanese_list: List[str]) -> List[Dict[str, Any]]:
        """
        複数の日本語テキストを一括翻訳する
        
        Args:
            japanese_list: 翻訳する日本語テキストのリスト
            
        Returns:
            List[Dict[str, Any]]: 各テキストの翻訳結果
        """
        results = []
        for text in japanese_list:
            results.append(self.translate_prompt_with_analysis(text))
        return results
    
    def clear_cache(self) -> bool:
        """翻訳キャッシュをクリアする"""
        try:
            self.translation_cache = {}
            if os.path.exists(TRANSLATION_CACHE_FILE):
                os.remove(TRANSLATION_CACHE_FILE)
            return True
        except Exception as e:
            self.logger.error(f"キャッシュクリアに失敗: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, int]:
        """キャッシュ統計を取得する"""
        return {
            "cache_size": len(self.translation_cache),
            "custom_translations": len(self.custom_translations),
            "prompt_rules": len(self.prompt_rules)
        }

# グローバルインスタンス
prompt_translator = PromptTranslator() 