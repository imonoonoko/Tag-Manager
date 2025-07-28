"""
context_analyzer.pyのテスト
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from modules.context_analyzer import (
    analyze_tag_context,
    calculate_context_boost,
    get_synonyms,
    has_negation,
    has_modifier,
    extract_color_keywords,
    extract_style_keywords,
    get_context_rules_for_category,
    SYNONYM_MAPPING,
    CONTEXT_BOOST_RULES,
    NEGATION_WORDS,
    MODIFIER_WORDS
)
from modules.common_words import COMMON_WORDS


class TestContextAnalyzer:
    """コンテキスト分析機能のテスト"""
    
    def test_analyze_tag_context_with_common_word(self):
        """一般的すぎる単語のコンテキスト分析テスト"""
        common_word = list(COMMON_WORDS)[0]
        result = analyze_tag_context(common_word)
        
        assert result["has_negation"] is False
        assert result["has_modifier"] is False
        assert result["color_keywords"] == []
        assert result["style_keywords"] == []
        assert result["synonyms"] == []
    
    def test_analyze_tag_context_with_color(self):
        """色キーワードを含むタグのコンテキスト分析テスト"""
        result = analyze_tag_context("blue hair")
        
        assert result["has_negation"] is False
        assert result["has_modifier"] is False
        assert "blue" in result["color_keywords"]
        assert result["style_keywords"] == []
        assert len(result["synonyms"]) > 0
    
    def test_analyze_tag_context_with_style(self):
        """スタイルキーワードを含むタグのコンテキスト分析テスト"""
        result = analyze_tag_context("long dress")
        
        assert result["has_negation"] is False
        assert result["has_modifier"] is False
        assert result["color_keywords"] == []
        assert "long" in result["style_keywords"]
        assert len(result["synonyms"]) > 0
    
    def test_analyze_tag_context_with_negation(self):
        """否定語を含むタグのコンテキスト分析テスト"""
        result = analyze_tag_context("no glasses")
        
        assert result["has_negation"] is True
        assert result["has_modifier"] is False
        assert result["color_keywords"] == []
        assert result["style_keywords"] == []
    
    def test_analyze_tag_context_with_modifier(self):
        """修飾語を含むタグのコンテキスト分析テスト"""
        result = analyze_tag_context("very beautiful")
        
        assert result["has_negation"] is False
        assert result["has_modifier"] is True
        assert result["color_keywords"] == []
        assert result["style_keywords"] == []
    
    def test_analyze_tag_context_complex(self):
        """複雑なタグのコンテキスト分析テスト"""
        result = analyze_tag_context("very long blue hair")
        
        assert result["has_negation"] is False
        assert result["has_modifier"] is True
        assert "blue" in result["color_keywords"]
        assert "long" in result["style_keywords"]
        assert len(result["synonyms"]) > 0
    
    def test_calculate_context_boost_with_common_word(self):
        """一般的すぎる単語のコンテキストブーストテスト"""
        common_word = list(COMMON_WORDS)[0]
        boost = calculate_context_boost(common_word, "髪型・髪色", ["test"])
        
        assert boost == 0
    
    def test_calculate_context_boost_with_matching_tags(self):
        """マッチングするタグのコンテキストブーストテスト"""
        boost = calculate_context_boost(
            "long hair", 
            "髪型・髪色", 
            ["long hair", "blue"]
        )
        
        # ブーストスコアが計算されることを確認
        assert boost >= 0
    
    def test_calculate_context_boost_no_matching_tags(self):
        """マッチングしないタグのコンテキストブーストテスト"""
        boost = calculate_context_boost(
            "long hair", 
            "髪型・髪色", 
            ["test", "example"]
        )
        
        assert boost == 0
    
    def test_get_synonyms_existing_word(self):
        """存在する単語の同義語取得テスト"""
        synonyms = get_synonyms("hair")
        
        assert isinstance(synonyms, list)
        assert len(synonyms) > 0
        assert "long hair" in synonyms
    
    def test_get_synonyms_nonexistent_word(self):
        """存在しない単語の同義語取得テスト"""
        synonyms = get_synonyms("nonexistent")
        
        assert synonyms == []
    
    def test_has_negation_with_negation(self):
        """否定語を含むタグのテスト"""
        assert has_negation("no glasses") is True
        assert has_negation("not wearing") is True
        assert has_negation("without hat") is True
    
    def test_has_negation_without_negation(self):
        """否定語を含まないタグのテスト"""
        assert has_negation("blue hair") is False
        assert has_negation("long dress") is False
    
    def test_has_negation_with_common_word(self):
        """一般的すぎる単語の否定語チェックテスト"""
        common_word = list(COMMON_WORDS)[0]
        assert has_negation(common_word) is False
    
    def test_has_modifier_with_modifier(self):
        """修飾語を含むタグのテスト"""
        assert has_modifier("very beautiful") is True
        assert has_modifier("extremely cute") is True
        assert has_modifier("slightly sad") is True
    
    def test_has_modifier_without_modifier(self):
        """修飾語を含まないタグのテスト"""
        assert has_modifier("blue hair") is False
        assert has_modifier("long dress") is False
    
    def test_has_modifier_with_common_word(self):
        """一般的すぎる単語の修飾語チェックテスト"""
        common_word = list(COMMON_WORDS)[0]
        assert has_modifier(common_word) is False
    
    def test_extract_color_keywords_with_colors(self):
        """色キーワードを含むタグのテスト"""
        colors = extract_color_keywords("blue hair red dress")
        
        assert "blue" in colors
        assert "red" in colors
        assert len(colors) == 2
    
    def test_extract_color_keywords_without_colors(self):
        """色キーワードを含まないタグのテスト"""
        colors = extract_color_keywords("long hair")
        
        assert colors == []
    
    def test_extract_color_keywords_with_common_word(self):
        """一般的すぎる単語の色キーワード抽出テスト"""
        common_word = list(COMMON_WORDS)[0]
        colors = extract_color_keywords(common_word)
        
        assert colors == []
    
    def test_extract_style_keywords_with_styles(self):
        """スタイルキーワードを含むタグのテスト"""
        styles = extract_style_keywords("long hair short dress")
        
        assert "long" in styles
        assert "short" in styles
        assert len(styles) == 2
    
    def test_extract_style_keywords_without_styles(self):
        """スタイルキーワードを含まないタグのテスト"""
        styles = extract_style_keywords("blue hair")
        
        assert styles == []
    
    def test_extract_style_keywords_with_common_word(self):
        """一般的すぎる単語のスタイルキーワード抽出テスト"""
        common_word = list(COMMON_WORDS)[0]
        styles = extract_style_keywords(common_word)
        
        assert styles == []
    
    def test_get_context_rules_for_category_existing(self):
        """存在するカテゴリのコンテキストルール取得テスト"""
        rules = get_context_rules_for_category("髪型・ヘアスタイル")
        
        assert isinstance(rules, list)
        assert len(rules) > 0
    
    def test_get_context_rules_for_category_nonexistent(self):
        """存在しないカテゴリのコンテキストルール取得テスト"""
        rules = get_context_rules_for_category("nonexistent")
        
        assert rules == []
    
    def test_synonym_mapping_structure(self):
        """同義語マッピングの構造テスト"""
        assert isinstance(SYNONYM_MAPPING, dict)
        assert len(SYNONYM_MAPPING) > 0
        
        for base_word, synonyms in SYNONYM_MAPPING.items():
            assert isinstance(base_word, str)
            assert isinstance(synonyms, list)
            assert len(synonyms) > 0
    
    def test_context_boost_rules_structure(self):
        """コンテキストブーストルールの構造テスト"""
        assert isinstance(CONTEXT_BOOST_RULES, dict)
        assert len(CONTEXT_BOOST_RULES) > 0
        
        for (cat1, cat2), rule in CONTEXT_BOOST_RULES.items():
            assert isinstance(cat1, str)
            assert isinstance(cat2, str)
            assert isinstance(rule, dict)
            assert "boost_score" in rule
            assert "examples" in rule
    
    def test_negation_words_structure(self):
        """否定語リストの構造テスト"""
        assert isinstance(NEGATION_WORDS, list)
        assert len(NEGATION_WORDS) > 0
        assert all(isinstance(word, str) for word in NEGATION_WORDS)
    
    def test_modifier_words_structure(self):
        """修飾語リストの構造テスト"""
        assert isinstance(MODIFIER_WORDS, list)
        assert len(MODIFIER_WORDS) > 0
        assert all(isinstance(word, str) for word in MODIFIER_WORDS)
    
    def test_case_insensitive_analysis(self):
        """大文字小文字を区別しない分析テスト"""
        result1 = analyze_tag_context("BLUE HAIR")
        result2 = analyze_tag_context("blue hair")
        
        assert result1["color_keywords"] == result2["color_keywords"]
        assert result1["style_keywords"] == result2["style_keywords"]
    
    def test_empty_string_analysis(self):
        """空文字列の分析テスト"""
        result = analyze_tag_context("")
        
        assert result["has_negation"] is False
        assert result["has_modifier"] is False
        assert result["color_keywords"] == []
        assert result["style_keywords"] == []
        assert result["synonyms"] == []
    
    def test_whitespace_only_analysis(self):
        """空白のみの文字列の分析テスト"""
        result = analyze_tag_context("   ")
        
        assert result["has_negation"] is False
        assert result["has_modifier"] is False
        assert result["color_keywords"] == []
        assert result["style_keywords"] == []
        assert result["synonyms"] == [] 