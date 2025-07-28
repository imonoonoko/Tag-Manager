"""
プロンプト翻訳機能のテスト
"""
import sys
import pytest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from modules.prompt_translator import PromptTranslator, prompt_translator

class TestPromptTranslator:
    """PromptTranslatorクラスのテスト"""
    
    def setup_method(self):
        """各テストメソッドの前処理"""
        # 一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        
        # テスト用の翻訳キャッシュファイルとカスタム翻訳ファイルを作成
        self.cache_file = os.path.join(self.temp_dir, "translation_cache.json")
        self.custom_file = os.path.join(self.temp_dir, "custom_translations.json")
        
        # テスト用のキャッシュデータ
        test_cache = {
            "テスト": "test",
            "翻訳": "translation"
        }
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(test_cache, f, ensure_ascii=False, indent=2)
        
        # テスト用のカスタム翻訳データ
        test_custom = {
            "カスタム": "custom",
            "翻訳": "custom_translation"
        }
        with open(self.custom_file, 'w', encoding='utf-8') as f:
            json.dump(test_custom, f, ensure_ascii=False, indent=2)
    
    def teardown_method(self):
        """各テストメソッドの後処理"""
        # 一時ディレクトリを削除
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """初期化のテスト"""
        translator = PromptTranslator()
        assert translator is not None
        assert hasattr(translator, 'translation_cache')
        assert hasattr(translator, 'custom_translations')
        assert hasattr(translator, 'prompt_rules')
    
    def test_prompt_rules(self):
        """プロンプトルールのテスト"""
        translator = PromptTranslator()
        # 基本的なプロンプトルールが存在することを確認
        assert "高画質" in translator.prompt_rules
        assert translator.prompt_rules["高画質"] == "high quality"
        assert "アニメ風" in translator.prompt_rules
        assert translator.prompt_rules["アニメ風"] == "anime style"
        assert "黒髪" in translator.prompt_rules
        assert translator.prompt_rules["黒髪"] == "black hair"
    
    def test_translate_prompt_with_rules(self):
        """プロンプトルールを使用した翻訳テスト"""
        translator = PromptTranslator()
        result = translator.translate_prompt("高画質", use_cache=False)
        assert result == "high quality"
    
    @patch('modules.prompt_translator.GoogleTranslator')
    def test_translate_prompt_with_google(self, mock_translator):
        """Google翻訳を使用した翻訳テスト"""
        # モックの設定
        mock_instance = MagicMock()
        mock_instance.translate.return_value = "google_translation"
        mock_translator.return_value = mock_instance
        
        translator = PromptTranslator()
        result = translator.translate_prompt("新しいテキスト", use_cache=False)
        assert result == "google_translation"
        mock_instance.translate.assert_called_once_with("新しいテキスト")
    
    def test_translate_prompt_empty_input(self):
        """空の入力に対する翻訳テスト"""
        translator = PromptTranslator()
        result = translator.translate_prompt("", use_cache=False)
        assert result == ""
        
        result = translator.translate_prompt("   ", use_cache=False)
        assert result == ""
    
    def test_translate_prompt_with_analysis(self):
        """分析付き翻訳テスト"""
        translator = PromptTranslator()
        result = translator.translate_prompt_with_analysis("高画質")
        
        assert result["original"] == "高画質"
        assert result["translated"] == "high quality"
        assert result["translation_method"] == "prompt_rule"
        assert result["confidence"] == 0.9
        assert isinstance(result["suggestions"], list)
        assert isinstance(result["warnings"], list)
    
    def test_add_custom_translation(self):
        """カスタム翻訳の追加テスト"""
        translator = PromptTranslator()
        
        # 新しいカスタム翻訳を追加
        result = translator.add_custom_translation("新しい", "new")
        assert result is True
        
        # 追加されたことを確認
        assert "新しい" in translator.custom_translations
        assert translator.custom_translations["新しい"] == "new"
        
        # 翻訳で使用できることを確認
        translated = translator.translate_prompt("新しい", use_cache=False)
        assert translated == "new"
    
    def test_remove_custom_translation(self):
        """カスタム翻訳の削除テスト"""
        translator = PromptTranslator()
        
        # まずカスタム翻訳を追加
        translator.add_custom_translation("テスト削除", "test_delete")
        assert "テスト削除" in translator.custom_translations
        
        # 存在するカスタム翻訳を削除
        result = translator.remove_custom_translation("テスト削除")
        assert result is True
        
        # 削除されたことを確認
        assert "テスト削除" not in translator.custom_translations
        
        # 存在しないカスタム翻訳を削除
        result = translator.remove_custom_translation("存在しない")
        assert result is False
    
    def test_get_custom_translations(self):
        """カスタム翻訳の取得テスト"""
        translator = PromptTranslator()
        
        # テスト用のカスタム翻訳を追加
        translator.add_custom_translation("テスト取得", "test_get")
        
        custom_translations = translator.get_custom_translations()
        
        assert isinstance(custom_translations, dict)
        assert "テスト取得" in custom_translations
        assert custom_translations["テスト取得"] == "test_get"
        
        # 元の辞書を変更しても影響されないことを確認
        custom_translations["テスト"] = "test"
        assert "テスト" not in translator.custom_translations
    
    def test_batch_translate(self):
        """一括翻訳テスト"""
        translator = PromptTranslator()
        japanese_list = ["テスト", "カスタム", "高画質"]
        
        results = translator.batch_translate(japanese_list)
        
        assert len(results) == 3
        assert results[0]["translated"] == "test"
        assert results[1]["translated"] == "custom"
        assert results[2]["translated"] == "high quality"
    
    def test_clear_cache(self):
        """キャッシュクリアテスト"""
        translator = PromptTranslator()
        
        # キャッシュが存在することを確認
        assert len(translator.translation_cache) > 0
        
        # キャッシュをクリア
        result = translator.clear_cache()
        assert result is True
        
        # キャッシュが空になったことを確認
        assert len(translator.translation_cache) == 0
    
    def test_get_cache_stats(self):
        """キャッシュ統計の取得テスト"""
        translator = PromptTranslator()
        stats = translator.get_cache_stats()
        
        assert isinstance(stats, dict)
        assert "cache_size" in stats
        assert "custom_translations" in stats
        assert "prompt_rules" in stats
        
        assert isinstance(stats["cache_size"], int)
        assert isinstance(stats["custom_translations"], int)
        assert isinstance(stats["prompt_rules"], int)
    
    def test_generate_suggestions(self):
        """提案生成のテスト"""
        translator = PromptTranslator()
        
        # 画質関連の提案（画質という単語が含まれている場合）
        suggestions = translator._generate_suggestions("高画質の美しい絵", "beautiful art")
        assert any("高画質" in suggestion for suggestion in suggestions)
        
        # masterpiece関連の提案
        suggestions = translator._generate_suggestions("傑作", "masterpiece")
        assert len(suggestions) == 0  # 既にmasterpieceが含まれているため提案なし
        
        # 美しいという単語でmasterpiece提案
        suggestions = translator._generate_suggestions("美しい絵", "beautiful art")
        assert any("masterpiece" in suggestion for suggestion in suggestions)
        
        # アニメ関連の提案
        suggestions = translator._generate_suggestions("アニメイラスト", "anime illustration")
        assert len(suggestions) == 0  # 既にanimeが含まれているため提案なし
    
    @patch('modules.prompt_translator.GoogleTranslator')
    def test_translate_prompt_error_handling(self, mock_translator):
        """翻訳エラーハンドリングのテスト"""
        # モックでエラーを発生させる
        mock_instance = MagicMock()
        mock_instance.translate.side_effect = Exception("Translation error")
        mock_translator.return_value = mock_instance
        
        translator = PromptTranslator()
        result = translator.translate_prompt("エラーテスト", use_cache=False)
        
        # エラー時は元のテキストを返す
        assert result == "エラーテスト"
    
    def test_translate_prompt_with_analysis_error_handling(self):
        """分析付き翻訳のエラーハンドリングテスト"""
        translator = PromptTranslator()
        
        # 空の入力
        result = translator.translate_prompt_with_analysis("")
        assert result["original"] == ""
        assert result["translated"] == ""
        assert result["confidence"] == 0.0
        
        # 翻訳エラー
        with patch.object(translator, 'translator') as mock_translator:
            mock_translator.translate.side_effect = Exception("Translation error")
            result = translator.translate_prompt_with_analysis("エラーテスト")
            
            assert result["original"] == "エラーテスト"
            assert result["translated"] == "エラーテスト"
            assert result["translation_method"] == "fallback"
            assert result["confidence"] == 0.0
            assert len(result["warnings"]) > 0

class TestPromptTranslatorIntegration:
    """統合テスト"""
    
    def test_prompt_translator_singleton(self):
        """シングルトンパターンのテスト"""
        from modules.prompt_translator import prompt_translator
        translator1 = prompt_translator
        translator2 = prompt_translator
        
        assert translator1 is translator2
    
    def test_translation_priority(self):
        """翻訳優先順位のテスト"""
        translator = PromptTranslator()
        
        # カスタム翻訳が最優先
        translator.add_custom_translation("高画質", "custom_high_quality")
        result = translator.translate_prompt("高画質", use_cache=False)
        assert result == "custom_high_quality"
        
        # カスタム翻訳を削除するとプロンプトルールが使用される
        translator.remove_custom_translation("高画質")
        result = translator.translate_prompt("高画質", use_cache=False)
        assert result == "high quality" 