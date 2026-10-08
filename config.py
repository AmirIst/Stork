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

# Telegram ID администраторов бота для доступа к панели управления
_raw_admins = os.getenv("ADMIN_IDS", "6725392176,190417869")
ADMIN_IDS = [int(x.strip()) for x in _raw_admins.split(",") if x.strip().isdigit()]

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором бота"""
    return user_id in ADMIN_IDS
