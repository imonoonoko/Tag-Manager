"""
ユーザーカスタマイズ機能
"""
import json
import os
from typing import Dict, List, Optional, Any
from .config import BACKUP_DIR
from .common_words import COMMON_WORDS

# ユーザー設定ファイル
USER_SETTINGS_FILE = os.path.join(BACKUP_DIR, "user_settings.json")
CUSTOM_KEYWORDS_FILE = os.path.join(BACKUP_DIR, "custom_keywords.json")
CUSTOM_RULES_FILE = os.path.join(BACKUP_DIR, "custom_rules.json")

class UserSettings:
    """
    ユーザー設定を管理するクラス
    """
    def __init__(self):
        self.settings = {
            "ai_prediction_enabled": True,
            "confidence_threshold": 0.7,
            "auto_suggest_enabled": True,
            "learning_enabled": True,
            "category_priorities": {},
            "custom_keywords": {},
            "custom_rules": [],
            "ui_preferences": {
                "theme": "cosmo",
                "window_size": "1200x800",
                "show_confidence": True,
                "show_suggestions": True
            }
        }
        self.load_settings()
    
    def load_settings(self):
        """
        設定を読み込む
        """
        try:
            if os.path.exists(USER_SETTINGS_FILE):
                with open(USER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # 既存の設定とマージ
                    for key, value in loaded_settings.items():
                        if key in self.settings:
                            if isinstance(self.settings[key], dict):
                                self.settings[key].update(value)
                            else:
                                self.settings[key] = value
        except Exception as e:
            print(f"設定の読み込みに失敗しました: {e}")
    
    def save_settings(self):
        """
        設定を保存する
        """
        try:
            os.makedirs(os.path.dirname(USER_SETTINGS_FILE), exist_ok=True)
            with open(USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"設定の保存に失敗しました: {e}")
            return False
    
    def get_setting(self, key: str, default=None):
        """
        設定値を取得する
        """
        keys = key.split('.')
        value = self.settings
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set_setting(self, key: str, value):
        """
        設定値を設定する
        """
        keys = key.split('.')
        target = self.settings
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.save_settings()

class CustomKeywordManager:
    """
    カスタムキーワードを管理するクラス
    """
    def __init__(self):
        self.custom_keywords = {}
        self.load_custom_keywords()
    
    def load_custom_keywords(self):
        """
        カスタムキーワードを読み込む
        """
        try:
            if os.path.exists(CUSTOM_KEYWORDS_FILE):
                with open(CUSTOM_KEYWORDS_FILE, 'r', encoding='utf-8') as f:
                    self.custom_keywords = json.load(f)
        except Exception as e:
            print(f"カスタムキーワードの読み込みに失敗しました: {e}")
    
    def save_custom_keywords(self):
        """
        カスタムキーワードを保存する
        """
        try:
            os.makedirs(os.path.dirname(CUSTOM_KEYWORDS_FILE), exist_ok=True)
            with open(CUSTOM_KEYWORDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.custom_keywords, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"カスタムキーワードの保存に失敗しました: {e}")
            return False
    
    def add_custom_keyword(self, category: str, keyword: str, weight: float = 1.0):
        """
        カスタムキーワードを追加する
        """
        # 一般的すぎる単語は追加を拒否
        if keyword.lower().strip() in COMMON_WORDS:
            return False
        
        if category not in self.custom_keywords:
            self.custom_keywords[category] = []
        
        # 既存のキーワードをチェック
        for existing in self.custom_keywords[category]:
            if existing["keyword"] == keyword:
                existing["weight"] = weight
                return self.save_custom_keywords()
        
        # 新しいキーワードを追加
        self.custom_keywords[category].append({
            "keyword": keyword,
            "weight": weight,
            "created_at": "2025-07-27"  # 実際の実装ではdatetimeを使用
        })
        
        return self.save_custom_keywords()
    
    def remove_custom_keyword(self, category: str, keyword: str):
        """
        カスタムキーワードを削除する
        """
        if category in self.custom_keywords:
            self.custom_keywords[category] = [
                kw for kw in self.custom_keywords[category] 
                if kw["keyword"] != keyword
            ]
            return self.save_custom_keywords()
        return False
    
    def get_custom_keywords(self, category: str = None):
        """
        カスタムキーワードを取得する
        """
        if category:
            return self.custom_keywords.get(category, [])
        return self.custom_keywords
    
    def get_custom_keyword_weight(self, category: str, keyword: str) -> float:
        """
        カスタムキーワードの重みを取得する
        """
        # 一般的すぎる単語は重みを1.0に固定
        if keyword.lower().strip() in COMMON_WORDS:
            return 1.0
        
        if category in self.custom_keywords:
            for kw in self.custom_keywords[category]:
                if kw["keyword"] == keyword:
                    return kw.get("weight", 1.0)
        return 1.0

class CustomRuleManager:
    """
    カスタムルールを管理するクラス
    """
    def __init__(self):
        self.custom_rules = []
        self.load_custom_rules()
    
    def load_custom_rules(self):
        """
        カスタムルールを読み込む
        """
        try:
            if os.path.exists(CUSTOM_RULES_FILE):
                with open(CUSTOM_RULES_FILE, 'r', encoding='utf-8') as f:
                    self.custom_rules = json.load(f)
        except Exception as e:
            print(f"カスタムルールの読み込みに失敗しました: {e}")
    
    def save_custom_rules(self):
        """
        カスタムルールを保存する
        """
        try:
            os.makedirs(os.path.dirname(CUSTOM_RULES_FILE), exist_ok=True)
            with open(CUSTOM_RULES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.custom_rules, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"カスタムルールの保存に失敗しました: {e}")
            return False
    
    def add_custom_rule(self, rule_type: str, condition: Dict[str, Any], action: Dict[str, Any], priority: int = 1):
        """
        カスタムルールを追加する
        """
        # 一般的すぎる単語を含むルールは追加を拒否
        if rule_type == "keyword_match":
            keyword = condition.get("keyword", "")
            if keyword.lower().strip() in COMMON_WORDS:
                return False
        
        rule = {
            "id": f"rule_{len(self.custom_rules) + 1}",
            "type": rule_type,
            "condition": condition,
            "action": action,
            "priority": priority,
            "enabled": True,
            "created_at": "2025-07-27"  # 実際の実装ではdatetimeを使用
        }
        
        self.custom_rules.append(rule)
        return self.save_custom_rules()
    
    def remove_custom_rule(self, rule_id: str):
        """
        カスタムルールを削除する
        """
        original_count = len(self.custom_rules)
        self.custom_rules = [rule for rule in self.custom_rules if rule["id"] != rule_id]
        
        # ルールが実際に削除されたかチェック
        if len(self.custom_rules) < original_count:
            return self.save_custom_rules()
        else:
            return False
    
    def get_custom_rules(self, rule_type: str = None):
        """
        カスタムルールを取得する
        """
        if rule_type:
            return [rule for rule in self.custom_rules if rule["type"] == rule_type and rule["enabled"]]
        return [rule for rule in self.custom_rules if rule["enabled"]]
    
    def evaluate_custom_rules(self, tag: str, context_tags: List[str] = None) -> Dict[str, Any]:
        """
        カスタムルールを評価する
        """
        # 一般的すぎる単語はカスタムルールを適用しない
        if tag.lower().strip() in COMMON_WORDS:
            return {}
        
        results = {}
        
        for rule in self.get_custom_rules():
            if self._evaluate_condition(rule["condition"], tag, context_tags):
                results[rule["id"]] = rule["action"]
        
        return results
    
    def _evaluate_condition(self, condition: Dict[str, Any], tag: str, context_tags: List[str] = None) -> bool:
        """
        条件を評価する
        """
        condition_type = condition.get("type", "keyword_match")
        
        if condition_type == "keyword_match":
            keyword = condition.get("keyword", "")
            # 一般的すぎる単語は条件として使用しない
            if keyword.lower().strip() in COMMON_WORDS:
                return False
            return keyword.lower() in tag.lower()
        
        elif condition_type == "context_contains":
            required_tags = condition.get("required_tags", [])
            if not context_tags:
                return False
            # 一般的すぎる単語は条件として使用しない
            filtered_tags = [tag for tag in required_tags if tag.lower().strip() not in COMMON_WORDS]
            if not filtered_tags:
                return False
            return all(tag.lower() in [ct.lower() for ct in context_tags] for tag in filtered_tags)
        
        elif condition_type == "tag_length":
            min_length = condition.get("min_length", 0)
            max_length = condition.get("max_length", 999)
            return min_length <= len(tag) <= max_length
        
        return False

class CustomizationManager:
    """
    カスタマイズ機能の統合管理クラス
    """
    def __init__(self):
        self.settings = UserSettings()
        self.keyword_manager = CustomKeywordManager()
        self.rule_manager = CustomRuleManager()
    
    def get_enhanced_category_keywords(self, base_keywords: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        カスタムキーワードを含む拡張されたカテゴリキーワードを取得する
        """
        enhanced_keywords = base_keywords.copy()
        
        for category, custom_keywords in self.keyword_manager.get_custom_keywords().items():
            if category not in enhanced_keywords:
                enhanced_keywords[category] = []
            
            for custom_kw in custom_keywords:
                # 一般的すぎる単語は除外
                if custom_kw["keyword"].lower().strip() not in COMMON_WORDS:
                    if custom_kw["keyword"] not in enhanced_keywords[category]:
                        enhanced_keywords[category].append(custom_kw["keyword"])
        
        return enhanced_keywords
    
    def apply_custom_rules_to_score(self, tag: str, category: str, base_score: float, context_tags: List[str] = None) -> float:
        """
        カスタムルールをスコアに適用する
        """
        # 一般的すぎる単語はカスタムルールを適用しない
        if tag.lower().strip() in COMMON_WORDS:
            return base_score
        
        modified_score = base_score
        rule_results = self.rule_manager.evaluate_custom_rules(tag, context_tags)
        
        for rule_id, action in rule_results.items():
            action_type = action.get("type", "boost_score")
            
            if action_type == "boost_score":
                boost = action.get("value", 0)
                modified_score += boost
            
            elif action_type == "score_multiply":
                multiplier = action.get("value", 1.0)
                modified_score *= multiplier
            
            elif action_type == "category_override":
                # カテゴリを強制的に変更
                pass  # 実装は呼び出し側で処理
        
        return modified_score
    
    def get_customization_summary(self) -> Dict[str, Any]:
        """
        カスタマイズ設定の概要を取得する
        """
        return {
            "settings": {
                "ai_prediction_enabled": self.settings.get_setting("ai_prediction_enabled"),
                "confidence_threshold": self.settings.get_setting("confidence_threshold"),
                "auto_suggest_enabled": self.settings.get_setting("auto_suggest_enabled")
            },
            "custom_keywords_count": sum(len(keywords) for keywords in self.keyword_manager.get_custom_keywords().values()),
            "custom_rules_count": len(self.rule_manager.get_custom_rules()),
            "categories_with_custom_keywords": list(self.keyword_manager.get_custom_keywords().keys())
        }

# グローバルインスタンス
customization_manager = CustomizationManager()

def get_customized_category_keywords(base_keywords: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    カスタマイズされたカテゴリキーワードを取得する（簡易版）
    """
    # 一般的すぎる単語を除外
    filtered_keywords = {}
    for category, keywords in base_keywords.items():
        filtered_keywords[category] = [kw for kw in keywords if kw.lower().strip() not in COMMON_WORDS]
    
    return customization_manager.get_enhanced_category_keywords(filtered_keywords)

def apply_custom_rules(tag: str, category: str, base_score: float, context_tags: List[str] = None) -> float:
    """
    カスタムルールを適用する（簡易版）
    """
    # 一般的すぎる単語はカスタムルールを適用しない
    if tag.lower().strip() in COMMON_WORDS:
        return base_score
    
    return customization_manager.apply_custom_rules_to_score(tag, category, base_score, context_tags)

def get_custom_category(tag: str) -> Optional[str]:
    """
    カスタムルールからカテゴリを取得する（カテゴリ判定用）
    """
    # 一般的すぎる単語はカスタムルールを適用しない
    if tag.lower().strip() in COMMON_WORDS:
        return None
    
    # カスタムルールを評価
    rule_results = customization_manager.rule_manager.evaluate_custom_rules(tag)
    
    for rule_id, action in rule_results.items():
        action_type = action.get("type", "score_boost")
        
        if action_type == "category_override":
            # カテゴリを強制的に変更
            return action.get("category", None)
    
    return None 