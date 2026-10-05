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
