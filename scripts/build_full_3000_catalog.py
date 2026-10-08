# -*- coding: utf-8 -*-
"""
Сборщик полного эталонного каталога немецких слов Stork на 3 000 слов.
Берет 1 000 базовых проверенных слов из data/words_1000.json и дополняет
их 2 000 уникальными проверенными словами из 12 модулей scripts/vocab_expansion/,
доводя каждую из 12 категорий ровно до 250 слов (12 * 250 = 3 000).
"""
import json
import logging
import sys
from collections import Counter
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = ROOT_DIR / "data"
WORDS_1000_PATH = DATA_DIR / "words_1000.json"
WORDS_3000_PATH = DATA_DIR / "words_3000.json"

from scripts.vocab_expansion.essen import WORDS_ESSEN
from scripts.vocab_expansion.zuhause import WORDS_ZUHAUSE
from scripts.vocab_expansion.stadt import WORDS_STADT
from scripts.vocab_expansion.lernen import WORDS_LERNEN
from scripts.vocab_expansion.menschen import WORDS_MENSCHEN
from scripts.vocab_expansion.kleidung import WORDS_KLEIDUNG
from scripts.vocab_expansion.reise import WORDS_REISE
from scripts.vocab_expansion.arbeit import WORDS_ARBEIT
from scripts.vocab_expansion.natur import WORDS_NATUR
from scripts.vocab_expansion.zeit import WORDS_ZEIT
from scripts.vocab_expansion.freizeit import WORDS_FREIZEIT
from scripts.vocab_expansion.gesundheit import WORDS_GESUNDHEIT


def tuple_to_dict(t):
    return {
        "word": t[0],
        "article": t[1],
        "plural": t[2],
        "level": t[3],
        "category": t[4],
        "example_de": t[5],
        "translations": {
            "ru": {
                "tr": t[6],
                "example_tr": t[7],
            },
            "en": {
                "tr": t[8],
                "example_tr": t[9],
            },
        },
    }


def main():
    logger.info("Loading base catalog from %s...", WORDS_1000_PATH)
    with open(WORDS_1000_PATH, "r", encoding="utf-8") as f:
        base_words = json.load(f)

    logger.info("Loaded %d base words.", len(base_words))

    all_words = list(base_words)
    seen_words = {w["word"] for w in base_words}

    expansion_modules = [
        ("Essen", WORDS_ESSEN),
        ("Zuhause", WORDS_ZUHAUSE),
        ("Stadt", WORDS_STADT),
        ("Lernen", WORDS_LERNEN),
        ("Menschen", WORDS_MENSCHEN),
        ("Kleidung", WORDS_KLEIDUNG),
        ("Reise", WORDS_REISE),
        ("Arbeit", WORDS_ARBEIT),
        ("Natur", WORDS_NATUR),
        ("Zeit", WORDS_ZEIT),
        ("Freizeit", WORDS_FREIZEIT),
        ("Gesundheit", WORDS_GESUNDHEIT),
    ]

    total_added = 0
    for cat_name, word_list in expansion_modules:
        logger.info("Processing expansion category %s (%d candidates)...", cat_name, len(word_list))
        cat_added = 0
        for t in word_list:
            word_str = t[0]
            if word_str in seen_words:
                raise ValueError(f"Duplicate word found across catalogs: {word_str}")
            seen_words.add(word_str)
            all_words.append(tuple_to_dict(t))
            cat_added += 1
        total_added += cat_added
        logger.info("Added %d words for %s.", cat_added, cat_name)

    logger.info("Total words assembled: %d (added %d)", len(all_words), total_added)

    # Sanity checks
    assert len(all_words) == 3000, f"Expected 3000 words, got {len(all_words)}"
    assert len(seen_words) == 3000, f"Expected 3000 unique words, got {len(seen_words)}"

    category_counts = Counter(w["category"] for w in all_words)
    logger.info("Category breakdown:")
    for cat, count in sorted(category_counts.items()):
        logger.info("  - %s: %d", cat, count)
        assert count == 250, f"Category {cat} has {count} words instead of 250!"

    # Field validations
    for idx, w in enumerate(all_words):
        assert w["article"] in ("der", "die", "das"), f"Invalid article for word {w['word']}: {w['article']}"
        assert w["level"] in ("A1", "A2", "B1"), f"Invalid level for word {w['word']}: {w['level']}"
        assert w["plural"].startswith("die "), f"Invalid plural for word {w['word']}: {w['plural']}"
        assert len(w["example_de"]) > 5, f"Example too short for word {w['word']}"
        assert "ru" in w["translations"] and "tr" in w["translations"]["ru"], f"Missing ru translation for {w['word']}"
        assert "en" in w["translations"] and "tr" in w["translations"]["en"], f"Missing en translation for {w['word']}"

    logger.info("All 3,000 words verified successfully with 100%% integrity!")

    # Save to data/words_3000.json
    logger.info("Saving to %s...", WORDS_3000_PATH)
    with open(WORDS_3000_PATH, "w", encoding="utf-8") as f:
        json.dump(all_words, f, ensure_ascii=False, indent=2)

    file_size_mb = WORDS_3000_PATH.stat().st_size / (1024 * 1024)
    logger.info("Done! Saved %d words to %s (%.2f MB).", len(all_words), WORDS_3000_PATH, file_size_mb)


if __name__ == "__main__":
    main()
