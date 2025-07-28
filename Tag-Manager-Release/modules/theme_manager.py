import json
import os
from modules.constants import THEME_FILE
import logging
from typing import Dict, List, Any, Optional

class ThemeManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        settings = self._load_theme_settings()
        self.current_theme = settings.get('theme', 'darkly') if settings else 'darkly'
        
    
    def _load_theme_settings(self) -> Optional[Dict[str, Any]]:
        """
        テーマ設定ファイルを読み込む。
        失敗時は空dictを返し、logger.errorで記録。
        theme値が不正な場合は'darkly'にフォールバック。
        """
        try:
            if os.path.exists(THEME_FILE):
                with open(THEME_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    available = self.get_available_themes()
                    theme = data.get('theme', 'darkly')
                    if theme not in available:
                        self.logger.warning(f"不正なテーマ名: {theme}。'darkly'にフォールバック")
                        data['theme'] = 'darkly'
                    return data
        except Exception as e:
            self.logger.error(f"テーマ設定ファイルの読み込みに失敗: {e}")
            return {}
    
    def save_theme_settings(self, theme_name: str) -> None:
        """
        テーマ設定をファイルに保存する。
        失敗時はlogger.errorで記録。
        戻り値なし。
        """
        settings = {'theme': theme_name}
        try:
            with open(THEME_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"テーマ設定保存エラー: {e}")
    
    def set_theme(self, theme_name: str) -> None:
        self.current_theme = theme_name
        self.save_theme_settings(theme_name)

    

    def get_available_themes(self) -> List[str]:
        """
        利用可能なテーマ名リストを返す。
        失敗時はlogger.errorで記録し、空リストを返す。
        """
        try:
            # ttkbootstrapの利用可能なテーマを返す
            return ['cosmo', 'flatly', 'journal', 'litera', 'lumen', 'minty', 'pulse', 'sandstone', 'united', 'morph', 'yeti',
                    'solar', 'superhero', 'darkly', 'cyborg', 'vapor', 'simplex', 'cerculean']
        except Exception as e:
            self.logger.error(f"テーマ一覧取得エラー: {e}")
            return []

def get_available_themes_pure() -> List[str]:
    """
    利用可能なテーマ名リストを返す純粋関数。
    """
    return ['cosmo', 'flatly', 'journal', 'litera', 'lumen', 'minty', 'pulse', 'sandstone', 'united', 'morph', 'yeti',
            'solar', 'superhero', 'darkly', 'cyborg', 'vapor', 'simplex', 'cerculean']

def load_theme_settings_pure(filepath: str) -> Dict[str, Any]:
    """
    テーマ設定ファイルを読み込む純粋関数。失敗時は空dict。
    """
    import logging
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.getLogger(__name__).error(f"テーマ設定ファイルの読み込みに失敗: {e}")
    return {}

def save_theme_settings_pure(filepath: str, theme_name: str) -> bool:
    """
    テーマ設定をファイルに保存する純粋関数（副作用ありだがテストしやすい）。
    """
    settings = {'theme': theme_name}
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False