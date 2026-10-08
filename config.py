import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные из .env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

DB_PATH = BASE_DIR / "stork_bot.db"

# Доступные языки интерфейса и изучения
SUPPORTED_LANGUAGES = {
    "ru": {"name": "Русский", "flag": "🇷🇺"},
    "en": {"name": "English", "flag": "🇬🇧"}
}
DEFAULT_LANGUAGE = "ru"

# Маскот и оформление
BOT_NAME = "Stork"
BOT_ICON = "🪶"

# Два постоянных аккаунта владельца (главные супер-админы, которых нельзя удалить)
SUPER_ADMIN_IDS = [6725392176, 190417869]

# Список администраторов бота для доступа к панели управления
_raw_admins = os.getenv("ADMIN_IDS", "6725392176,190417869")
ADMIN_IDS = [int(x.strip()) for x in _raw_admins.split(",") if x.strip().isdigit()]
for _sa in SUPER_ADMIN_IDS:
    if _sa not in ADMIN_IDS:
        ADMIN_IDS.append(_sa)

def is_super_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь главным супер-админом (владельцем)"""
    return user_id in SUPER_ADMIN_IDS

def is_admin(user_id: int) -> bool:
    """Синхронная базовая проверка наличия доступа к админ-панели"""
    return user_id in SUPER_ADMIN_IDS or user_id in ADMIN_IDS

