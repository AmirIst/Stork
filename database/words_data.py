"""
Словарь немецких слов с артиклями, переводом и примерами.
Загружает 500 качественных слов из data/words_500.json по категориям и уровням (A1, A2, B1).
"""
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "words_500.json"

if DATA_FILE.exists():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            INITIAL_WORDS = json.load(f)
    except Exception:
        INITIAL_WORDS = []
else:
    INITIAL_WORDS = []

# Человекочитаемые названия категорий с эмодзи
CATEGORY_METADATA = {
    "Essen": {"ru": "🍎 Еда и напитки", "en": "🍎 Food & Drinks"},
    "Zuhause": {"ru": "🏠 Дом и быт", "en": "🏠 Home & Living"},
    "Stadt": {"ru": "🚗 Город и транспорт", "en": "🚗 City & Transport"},
    "Menschen": {"ru": "👥 Люди и семья", "en": "👥 People & Family"},
    "Arbeit": {"ru": "💼 Работа и офис", "en": "💼 Work & Office"},
    "Lernen": {"ru": "📚 Учеба и знания", "en": "📚 Learning & Study"},
    "Kleidung": {"ru": "👕 Одежда и мода", "en": "👕 Clothes & Fashion"},
    "Gesundheit": {"ru": "🩺 Здоровье и тело", "en": "🩺 Health & Body"},
    "Reise": {"ru": "✈️ Путешествия", "en": "✈️ Travel & Vacation"},
    "Natur": {"ru": "🌿 Природа и животные", "en": "🌿 Nature & Animals"},
    "Zeit": {"ru": "⏰ Время и календарь", "en": "⏰ Time & Calendar"},
    "Freizeit": {"ru": "⚽ Досуг и спорт", "en": "⚽ Leisure & Sports"}
}
