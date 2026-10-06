import json
import pytest
from pathlib import Path
from services.tts import extract_german_for_voice
from database.words_data import CATEGORY_METADATA

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def test_words_1000_integrity():
    words_file = DATA_DIR / "words_1000.json"
    assert words_file.exists(), "data/words_1000.json does not exist"

    with open(words_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == 1000, f"Expected 1000 words, got {len(data)}"
    
    unique_words = set()
    for item in data:
        w = item["word"]
        assert w not in unique_words, f"Duplicate word found: {w}"
        unique_words.add(w)

        assert item["article"] in ("der", "die", "das"), f"Invalid article for {w}: {item['article']}"
        assert item["level"] in ("A1", "A2", "B1"), f"Invalid level for {w}: {item['level']}"
        assert item["category"] in CATEGORY_METADATA, f"Unknown category for {w}: {item['category']}"
        assert len(item["example_de"]) > 3, f"Short German example for {w}"
        
        ru_tr = item["translations"].get("ru", {})
        en_tr = item["translations"].get("en", {})
        assert ru_tr.get("tr"), f"Missing Russian translation for {w}"
        assert ru_tr.get("example_tr"), f"Missing Russian example translation for {w}"
        assert en_tr.get("tr"), f"Missing English translation for {w}"
        assert en_tr.get("example_tr"), f"Missing English example translation for {w}"

def test_extract_german_for_voice():
    sample_text = """
🪶 Stork:

🇩🇪 Auf Deutsch: Wie alt bist du?

💡 Разбор: alt означает 'старый'.

🪶 Ich bin ein Sprachmodell, ich habe kein Alter. (Я языковая модель, у меня нет возраста.)

Und wie geht es dir heute? (А как у тебя сегодня дела?)
"""
    german = extract_german_for_voice(sample_text)
    assert "Wie alt bist du?" in german
    assert "Ich bin ein Sprachmodell" in german
    assert "Und wie geht es dir heute?" in german
    assert "Разбор" not in german
    assert "языковая модель" not in german

@pytest.mark.anyio
async def test_db_random_word_fetch():
    from database import db
    await db.init_db()
    word = await db.get_random_word(lang="ru")
    assert word is not None
    assert word["word"]
    assert word["article"] in ("der", "die", "das")
    assert word["translation"]

