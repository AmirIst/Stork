import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class LocalizationManager:
    """
    Менеджер мультиязычности.
    Автоматически сканирует папку locales/ и загружает все JSON-файлы локализации.
    Позволяет легко добавлять новые языки простым созданием файла <код_языка>.json.
    """
    def __init__(self, locales_dir: Optional[Path] = None):
        self.locales_dir = locales_dir or Path(__file__).resolve().parent
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.default_lang = "ru"
        self.reload_locales()

    def reload_locales(self):
        """Перезагрузка всех файлов локализации из папки locales"""
        self.translations.clear()
        for file in self.locales_dir.glob("*.json"):
            lang_code = file.stem.lower()
            try:
                with open(file, "r", encoding="utf-8") as f:
                    self.translations[lang_code] = json.load(f)
            except Exception as e:
                logger.error(f"Ошибка при загрузке локализации {file}: {e}")

    def get_available_languages(self) -> Dict[str, Dict[str, str]]:
        """Возвращает список всех доступных языков с названиями и флагами"""
        languages = {}
        for code, data in self.translations.items():
            languages[code] = {
                "name": data.get("lang_name", code.upper()),
                "flag": data.get("lang_flag", "🌐")
            }
        return languages

    def get(self, key: str, lang: str = "ru", **kwargs) -> str:
        """
        Получить локализованный текст по ключу с подстановкой параметров.
        Если ключ не найден в выбранном языке, берется из дефолтного (ru).
        """
        lang = lang.lower() if lang else self.default_lang
        
        # Проверяем язык, если нет - берем дефолтный
        lang_dict = self.translations.get(lang, self.translations.get(self.default_lang, {}))
        text = lang_dict.get(key)
        
        if text is None:
            # Fallback на дефолтный
            text = self.translations.get(self.default_lang, {}).get(key, key)
            
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception as e:
                logger.warning(f"Ошибка форматирования ключа {key}: {e}")
                return text
        return text

# Глобальный синглтон локализации
i18n = LocalizationManager()
