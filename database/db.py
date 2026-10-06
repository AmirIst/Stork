import random
import logging
from typing import Optional, Dict, Any, List, Tuple
import aiosqlite
from config import DB_PATH, DEFAULT_LANGUAGE
from database.words_data import INITIAL_WORDS, CATEGORY_METADATA

logger = logging.getLogger(__name__)

async def init_db():
    """Инициализация базы данных SQLite, миграции и синхронизация словаря"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            native_lang TEXT DEFAULT 'ru',
            selected_level TEXT DEFAULT 'ALL',
            selected_category TEXT DEFAULT 'ALL',
            score INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL UNIQUE,
            article TEXT NOT NULL,
            plural TEXT,
            level TEXT DEFAULT 'A1',
            category TEXT,
            example_de TEXT
        );
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS word_translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER NOT NULL,
            lang TEXT NOT NULL,
            translation TEXT NOT NULL,
            example_tr TEXT,
            FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE,
            UNIQUE(word_id, lang)
        );
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_progress (
            user_id INTEGER NOT NULL,
            word_id INTEGER NOT NULL,
            status TEXT DEFAULT 'learning',
            correct_count INTEGER DEFAULT 0,
            wrong_count INTEGER DEFAULT 0,
            last_reviewed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(user_id, word_id)
        );
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS ai_chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_chat_user ON ai_chat_history(user_id);")

        # Миграция: проверяем колонки в users
        async with db.execute("PRAGMA table_info(users)") as cursor:
            user_cols = [row[1] for row in await cursor.fetchall()]
            if "selected_level" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN selected_level TEXT DEFAULT 'ALL'")
            if "selected_category" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN selected_category TEXT DEFAULT 'ALL'")

        # Миграция: проверяем наличие столбца status в user_progress
        async with db.execute("PRAGMA table_info(user_progress)") as cursor:
            prog_cols = [row[1] for row in await cursor.fetchall()]
            if "status" not in prog_cols:
                await db.execute("ALTER TABLE user_progress ADD COLUMN status TEXT DEFAULT 'learning'")

        await db.commit()

        # Синхронизация слов из INITIAL_WORDS
        logger.info(f"Синхронизация {len(INITIAL_WORDS)} слов с базой данных...")
        for item in INITIAL_WORDS:
            async with db.execute("SELECT id FROM words WHERE word = ?", (item["word"],)) as cursor:
                row = await cursor.fetchone()

            if not row:
                async with db.execute(
                    "INSERT INTO words (word, article, plural, level, category, example_de) VALUES (?, ?, ?, ?, ?, ?)",
                    (item["word"], item["article"], item["plural"], item["level"], item["category"], item["example_de"])
                ) as cursor:
                    word_id = cursor.lastrowid
            else:
                word_id = row[0]
                # Обновляем метаданные если изменились
                await db.execute(
                    "UPDATE words SET article = ?, plural = ?, level = ?, category = ?, example_de = ? WHERE id = ?",
                    (item["article"], item["plural"], item["level"], item["category"], item["example_de"], word_id)
                )

            for lang, tr_data in item.get("translations", {}).items():
                await db.execute("""
                    INSERT INTO word_translations (word_id, lang, translation, example_tr)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(word_id, lang) DO UPDATE SET
                        translation = excluded.translation,
                        example_tr = excluded.example_tr
                """, (word_id, lang, tr_data["tr"], tr_data["example_tr"]))

        await db.commit()
        logger.info(f"Словарь Stork ({len(INITIAL_WORDS)} слов) успешно синхронизирован с базой данных.")

async def get_or_create_user(user_id: int, username: Optional[str], first_name: Optional[str]) -> Dict[str, Any]:
    """Получить или зарегистрировать пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)

        await db.execute(
            "INSERT INTO users (user_id, username, first_name, native_lang, selected_level, selected_category) VALUES (?, ?, ?, ?, 'ALL', 'ALL')",
            (user_id, username or "", first_name or "", DEFAULT_LANGUAGE)
        )
        await db.commit()
        return {
            "user_id": user_id,
            "username": username or "",
            "first_name": first_name or "",
            "native_lang": DEFAULT_LANGUAGE,
            "selected_level": "ALL",
            "selected_category": "ALL",
            "score": 0,
            "streak": 0
        }

async def update_user_lang(user_id: int, lang: str):
    """Обновить язык интерфейса пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET native_lang = ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
            (lang, user_id)
        )
        await db.commit()

async def get_user_lang(user_id: int) -> str:
    """Получить язык интерфейса пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT native_lang FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0]
    return DEFAULT_LANGUAGE

async def get_user_filters(user_id: int) -> Tuple[str, str]:
    """Получить текущие фильтры пользователя: (level, category)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT selected_level, selected_category FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return (row[0] or "ALL", row[1] or "ALL")
    return ("ALL", "ALL")

async def set_user_level(user_id: int, level: str):
    """Установить фильтр по уровню сложности (ALL, A1, A2, B1)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET selected_level = ? WHERE user_id = ?", (level, user_id))
        await db.commit()

async def set_user_category(user_id: int, category: str):
    """Установить фильтр по категории слов (ALL или название категории)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET selected_category = ? WHERE user_id = ?", (category, user_id))
        await db.commit()

async def get_categories_stats(level: str = "ALL") -> List[Dict[str, Any]]:
    """Получить список всех категорий и количество слов в каждой"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT category, COUNT(*) as cnt FROM words"
        params = []
        if level != "ALL":
            query += " WHERE level = ?"
            params.append(level)
        query += " GROUP BY category ORDER BY cnt DESC"

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def add_user_score(user_id: int, points: int = 1) -> Tuple[int, int]:
    """Добавить очки и увеличить серию (streak)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users 
            SET score = score + ?, streak = streak + 1, last_active = CURRENT_TIMESTAMP 
            WHERE user_id = ?
        """, (points, user_id))
        await db.commit()
        async with db.execute("SELECT score, streak FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return (row[0], row[1]) if row else (0, 0)

async def reset_streak(user_id: int):
    """Сбросить streak при ошибке"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET streak = 0 WHERE user_id = ?", (user_id,))
        await db.commit()

async def set_word_status(user_id: int, word_id: int, status: str) -> None:
    """Установить статус слова в стиле Anki (known, review, learning)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO user_progress (user_id, word_id, status, last_reviewed)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, word_id) DO UPDATE SET
                status = excluded.status,
                last_reviewed = CURRENT_TIMESTAMP
        """, (user_id, word_id, status))
        
        if status == "known":
            await db.execute("UPDATE users SET score = score + 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_word_user_status(user_id: int, word_id: int) -> Optional[str]:
    """Получить текущий статус слова для пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT status FROM user_progress WHERE user_id = ? AND word_id = ?",
            (user_id, word_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def get_user_stats(user_id: int) -> Dict[str, Any]:
    """Получить расширенную статистику пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()

        async with db.execute("SELECT COUNT(*) FROM words") as cursor:
            total_words = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND status = 'known'",
            (user_id,)
        ) as cursor:
            known_words = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND status = 'review'",
            (user_id,)
        ) as cursor:
            review_words = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND status = 'learning'",
            (user_id,)
        ) as cursor:
            learning_words = (await cursor.fetchone())[0]

        return {
            "score": user["score"] if user else 0,
            "streak": user["streak"] if user else 0,
            "native_lang": user["native_lang"] if user else DEFAULT_LANGUAGE,
            "selected_level": user["selected_level"] if user else "ALL",
            "selected_category": user["selected_category"] if user else "ALL",
            "first_name": user["first_name"] if user else "Друг",
            "total_words": total_words,
            "known_words": known_words,
            "review_words": review_words,
            "learning_words": learning_words
        }

async def get_random_word(
    lang: str = "ru",
    level: Optional[str] = None,
    category: Optional[str] = None,
    exclude_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """Получить случайное слово с учетом фильтрации по уровню и категории"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT w.id, w.word, w.article, w.plural, w.level, w.category, w.example_de,
                   COALESCE(wt.translation, '') AS translation,
                   COALESCE(wt.example_tr, '') AS example_tr
            FROM words w
            LEFT JOIN word_translations wt ON w.id = wt.word_id AND wt.lang = ?
            WHERE 1=1
        """
        params = [lang]

        if level and level != "ALL":
            query += " AND w.level = ?"
            params.append(level)

        if category and category != "ALL":
            query += " AND w.category = ?"
            params.append(category)

        if exclude_id is not None:
            query += " AND w.id != ?"
            params.append(exclude_id)

        query += " ORDER BY RANDOM() LIMIT 1"

        async with db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                if not data["translation"]:
                    async with db.execute(
                        "SELECT translation, example_tr FROM word_translations WHERE word_id = ? LIMIT 1",
                        (data["id"],)
                    ) as fb_cursor:
                        fb = await fb_cursor.fetchone()
                        if fb:
                            data["translation"] = fb["translation"]
                            data["example_tr"] = fb["example_tr"]
                return data

        # Если с жестким фильтром слово не найдено (например, категория пуста на данном уровне), ослабляем фильтр
        if category and category != "ALL":
            return await get_random_word(lang=lang, level="ALL", category=category, exclude_id=exclude_id)
        if level and level != "ALL":
            return await get_random_word(lang=lang, level="ALL", category="ALL", exclude_id=exclude_id)

    return None

async def get_word_by_id(word_id: int, lang: str = "ru") -> Optional[Dict[str, Any]]:
    """Получить информацию о слове по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT w.id, w.word, w.article, w.plural, w.level, w.category, w.example_de,
                   COALESCE(wt.translation, '') AS translation,
                   COALESCE(wt.example_tr, '') AS example_tr
            FROM words w
            LEFT JOIN word_translations wt ON w.id = wt.word_id AND wt.lang = ?
            WHERE w.id = ?
        """, (lang, word_id)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
    return None

async def get_translation_quiz_data(
    lang: str = "ru",
    level: Optional[str] = None,
    category: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Подготовить данные для квиза с учетом фильтрации"""
    target_word = await get_random_word(lang=lang, level=level, category=category)
    if not target_word:
        return None

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT wt.translation 
            FROM word_translations wt
            WHERE wt.lang = ? AND wt.word_id != ? AND wt.translation != ''
            ORDER BY RANDOM() LIMIT 3
        """, (lang, target_word["id"])) as cursor:
            distractors = [row["translation"] for row in await cursor.fetchall()]

    options = distractors + [target_word["translation"]]
    random.shuffle(options)

    return {
        "word": target_word,
        "options": options,
        "correct_answer": target_word["translation"]
    }

async def record_user_answer(user_id: int, word_id: int, is_correct: bool):
    """Записать результат ответа пользователя по конкретному слову"""
    async with aiosqlite.connect(DB_PATH) as db:
        if is_correct:
            await db.execute("""
                INSERT INTO user_progress (user_id, word_id, status, correct_count, wrong_count, last_reviewed)
                VALUES (?, ?, 'learning', 1, 0, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, word_id) DO UPDATE SET
                    correct_count = correct_count + 1,
                    last_reviewed = CURRENT_TIMESTAMP
            """, (user_id, word_id))
        else:
            await db.execute("""
                INSERT INTO user_progress (user_id, word_id, status, correct_count, wrong_count, last_reviewed)
                VALUES (?, ?, 'learning', 0, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, word_id) DO UPDATE SET
                    wrong_count = wrong_count + 1,
                    status = 'learning',
                    last_reviewed = CURRENT_TIMESTAMP
            """, (user_id, word_id))
        await db.commit()

async def add_chat_message(user_id: int, role: str, message: str):
    """Сохранить реплику диалога в историю"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ai_chat_history (user_id, role, message) VALUES (?, ?, ?)",
            (user_id, role, message)
        )
        await db.commit()

async def get_chat_history(user_id: int, limit: int = 6) -> List[Dict[str, str]]:
    """Получить последние сообщения диалога в хронологическом порядке"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT role, message 
            FROM ai_chat_history 
            WHERE user_id = ? 
            ORDER BY id DESC 
            LIMIT ?
        """, (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [{"role": r["role"], "message": r["message"]} for r in reversed(rows)]

async def clear_chat_history(user_id: int):
    """Очистить историю диалога пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM ai_chat_history WHERE user_id = ?", (user_id,))
        await db.commit()

async def has_chat_history(user_id: int) -> bool:
    """Проверить, есть ли сохраненная история диалога"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM ai_chat_history WHERE user_id = ? LIMIT 1",
            (user_id,)
        ) as cursor:
            return (await cursor.fetchone()) is not None
