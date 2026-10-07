import random
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
import aiosqlite
from config import DB_PATH, DEFAULT_LANGUAGE
from database.words_data import INITIAL_WORDS, CATEGORY_METADATA

logger = logging.getLogger(__name__)

FREE_DAILY_AI_LIMIT = 10
FREE_DAILY_EXAM_LIMIT = 3

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
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            placement_level TEXT,
            placement_score INTEGER,
            is_premium INTEGER DEFAULT 0,
            premium_until TIMESTAMP,
            daily_ai_count INTEGER DEFAULT 0,
            daily_exam_count INTEGER DEFAULT 0,
            last_usage_date TEXT DEFAULT '',
            notifications_enabled INTEGER DEFAULT 1,
            last_streak_date TEXT DEFAULT '',
            last_reminder_date TEXT DEFAULT ''
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

        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_achievements (
            user_id INTEGER NOT NULL,
            badge_id TEXT NOT NULL,
            unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(user_id, badge_id)
        );
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_achieve_user ON user_achievements(user_id);")

        # Миграция: проверяем колонки в users
        async with db.execute("PRAGMA table_info(users)") as cursor:
            user_cols = [row[1] for row in await cursor.fetchall()]
            if "selected_level" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN selected_level TEXT DEFAULT 'ALL'")
            if "selected_category" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN selected_category TEXT DEFAULT 'ALL'")
            if "placement_level" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN placement_level TEXT")
            if "placement_score" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN placement_score INTEGER")
            if "is_premium" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN is_premium INTEGER DEFAULT 0")
            if "premium_until" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN premium_until TIMESTAMP")
            if "daily_ai_count" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN daily_ai_count INTEGER DEFAULT 0")
            if "daily_exam_count" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN daily_exam_count INTEGER DEFAULT 0")
            if "last_usage_date" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN last_usage_date TEXT DEFAULT ''")
            if "notifications_enabled" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN notifications_enabled INTEGER DEFAULT 1")
            if "last_streak_date" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN last_streak_date TEXT DEFAULT ''")
            if "last_reminder_date" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN last_reminder_date TEXT DEFAULT ''")

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
    """Получить расширенную статистику пользователя с учетом квот и Premium"""
    today_str = _get_current_date_str()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()

        if user:
            user = await _ensure_daily_reset(db, user, today_str)

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

        is_prem, prem_until = await is_user_premium(user_id) if user else (False, None)

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
            "learning_words": learning_words,
            "placement_level": user["placement_level"] if user and "placement_level" in user.keys() else None,
            "placement_score": user["placement_score"] if user and "placement_score" in user.keys() else None,
            "is_premium": is_prem,
            "premium_until": prem_until,
            "daily_ai_count": user["daily_ai_count"] if user else 0,
            "daily_ai_limit": -1 if is_prem else FREE_DAILY_AI_LIMIT,
            "daily_exam_count": user["daily_exam_count"] if user else 0,
            "daily_exam_limit": -1 if is_prem else FREE_DAILY_EXAM_LIMIT,
            "notifications_enabled": bool(user["notifications_enabled"]) if user and user["notifications_enabled"] is not None else True
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

async def save_user_placement_result(user_id: int, level: str, score: int) -> None:
    """Сохранить результат теста на уровень немецкого языка"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET placement_level = ?, placement_score = ? WHERE user_id = ?",
            (level, score, user_id)
        )
        await db.commit()

async def get_user_placement_result(user_id: int) -> Tuple[Optional[str], Optional[int]]:
    """Получить результат теста на определение уровня"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT placement_level, placement_score FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0], row[1]
    return None, None

def _get_current_date_str() -> str:
    """Получить текущую дату в формате YYYY-MM-DD (UTC)"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

async def _ensure_daily_reset(db: aiosqlite.Connection, user_row: Any, today_str: str) -> Any:
    """Сбрасывает дневные счетчики, если наступил новый календарный день"""
    user_dict = dict(user_row) if user_row else {}
    last_date = user_dict.get("last_usage_date") or ""
    user_id = user_dict.get("user_id")
    if last_date != today_str and user_id:
        await db.execute(
            "UPDATE users SET daily_ai_count = 0, daily_exam_count = 0, last_usage_date = ? WHERE user_id = ?",
            (today_str, user_id)
        )
        await db.commit()
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()
    return user_row

async def update_daily_streak(user_id: int) -> int:
    """Обновить серию ежедневных занятий (Duolingo Daily Streak)"""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT streak, last_streak_date FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return 0

            current_streak = row["streak"] or 0
            last_streak_date = row["last_streak_date"] or ""

            if last_streak_date == today_str:
                return current_streak
            elif last_streak_date == yesterday_str:
                new_streak = current_streak + 1
            else:
                new_streak = 1

            await db.execute(
                "UPDATE users SET streak = ?, last_streak_date = ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
                (new_streak, today_str, user_id)
            )
            await db.commit()
            return new_streak

async def is_user_premium(user_id: int) -> Tuple[bool, Optional[str]]:
    """Проверить статус Stork Premium и дату окончания"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT is_premium, premium_until FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or not row["is_premium"]:
                return False, None

            premium_until = row["premium_until"]
            if premium_until:
                now_str = datetime.now(timezone.utc).isoformat()
                if premium_until < now_str:
                    await db.execute("UPDATE users SET is_premium = 0 WHERE user_id = ?", (user_id,))
                    await db.commit()
                    return False, None
            return True, premium_until

async def activate_premium(user_id: int, days: int = 30) -> str:
    """Активировать Stork Premium на указанное количество дней"""
    until_dt = datetime.now(timezone.utc) + timedelta(days=days)
    until_str = until_dt.isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_premium = 1, premium_until = ? WHERE user_id = ?",
            (until_str, user_id)
        )
        await db.commit()
    return until_str

async def check_ai_quota(user_id: int) -> Tuple[bool, int, int]:
    """
    Проверить доступность ИИ-собеседника.
    Возвращает (разрешено, использовано_сегодня, лимит).
    Для Premium лимит равен -1 (безлимит).
    """
    today_str = _get_current_date_str()
    is_premium, _ = await is_user_premium(user_id)
    if is_premium:
        return True, 0, -1

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return True, 0, FREE_DAILY_AI_LIMIT
            row = await _ensure_daily_reset(db, row, today_str)
            used = row["daily_ai_count"] or 0
            allowed = used < FREE_DAILY_AI_LIMIT
            return allowed, used, FREE_DAILY_AI_LIMIT

async def increment_ai_quota(user_id: int):
    """Увеличить счетчик использованных сообщений ИИ"""
    today_str = _get_current_date_str()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                await _ensure_daily_reset(db, row, today_str)
                await db.execute(
                    "UPDATE users SET daily_ai_count = daily_ai_count + 1 WHERE user_id = ?",
                    (user_id,)
                )
                await db.commit()

async def check_exam_quota(user_id: int) -> Tuple[bool, int, int]:
    """
    Проверить доступность проверки экзаменационных писем.
    Возвращает (разрешено, использовано_сегодня, лимит).
    Для Premium лимит равен -1 (безлимит).
    """
    today_str = _get_current_date_str()
    is_premium, _ = await is_user_premium(user_id)
    if is_premium:
        return True, 0, -1

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return True, 0, FREE_DAILY_EXAM_LIMIT
            row = await _ensure_daily_reset(db, row, today_str)
            used = row["daily_exam_count"] or 0
            allowed = used < FREE_DAILY_EXAM_LIMIT
            return allowed, used, FREE_DAILY_EXAM_LIMIT

async def increment_exam_quota(user_id: int):
    """Увеличить счетчик проверенных экзаменационных работ"""
    today_str = _get_current_date_str()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                await _ensure_daily_reset(db, row, today_str)
                await db.execute(
                    "UPDATE users SET daily_exam_count = daily_exam_count + 1 WHERE user_id = ?",
                    (user_id,)
                )
                await db.commit()

async def toggle_user_notifications(user_id: int) -> bool:
    """Переключить статус ежедневных напоминаний (Вкл/Выкл)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT notifications_enabled FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            current = row[0] if (row and row[0] is not None) else 1
            new_val = 0 if current == 1 else 1
            await db.execute("UPDATE users SET notifications_enabled = ? WHERE user_id = ?", (new_val, user_id))
            await db.commit()
            return bool(new_val)

async def get_user_notifications_status(user_id: int) -> bool:
    """Получить статус напоминаний"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT notifications_enabled FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] is not None:
                return bool(row[0])
            return True

async def get_users_for_daily_reminder(today_date: str) -> List[Dict[str, Any]]:
    """Получить список пользователей, которым нужно отправить напоминание о сохранении серии"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT user_id, first_name, native_lang, streak, last_streak_date 
            FROM users 
            WHERE notifications_enabled = 1 
              AND (last_streak_date IS NULL OR last_streak_date != ?) 
              AND (last_reminder_date IS NULL OR last_reminder_date != ?)
        """, (today_date, today_date)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def mark_user_reminded(user_id: int, today_date: str):
    """Отметить отправку напоминания за сегодня"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET last_reminder_date = ? WHERE user_id = ?", (today_date, user_id))
        await db.commit()

async def get_review_words_count(user_id: int) -> int:
    """Получить количество слов, требующих повторения (статусы learning или review)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND status IN ('learning', 'review')",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_words_for_review(user_id: int, lang: str = "ru", limit: int = 20) -> List[Dict[str, Any]]:
    """Получить слова для умного повторения"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT w.id, w.word, w.article, w.plural, w.level, w.category, w.example_de,
                   COALESCE(wt.translation, '') AS translation,
                   COALESCE(wt.example_tr, '') AS example_tr,
                   up.status, up.wrong_count, up.correct_count
            FROM user_progress up
            JOIN words w ON up.word_id = w.id
            LEFT JOIN word_translations wt ON w.id = wt.word_id AND wt.lang = ?
            WHERE up.user_id = ? AND up.status IN ('learning', 'review')
            ORDER BY up.last_reviewed ASC, up.wrong_count DESC
            LIMIT ?
        """
        async with db.execute(query, (lang, user_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

# ==========================================
# СИСТЕМА ДОСТИЖЕНИЙ И НАГРАД (ACHIEVEMENTS)
# ==========================================

ACHIEVEMENTS_REGISTRY: Dict[str, Dict[str, Any]] = {
    "first_step": {
        "icon": "🐣",
        "title": {"ru": "Первый шаг", "en": "First Step"},
        "desc": {"ru": "Запустить бота и начать изучение немецкого", "en": "Start the bot and begin learning German"}
    },
    "streak_3": {
        "icon": "🔥",
        "title": {"ru": "Огненный старт", "en": "Flame Starter"},
        "desc": {"ru": "Серия занятий 3 дня подряд", "en": "3-day study streak"}
    },
    "streak_7": {
        "icon": "⚡",
        "title": {"ru": "Неудержимый", "en": "Unstoppable"},
        "desc": {"ru": "Серия занятий 7 дней подряд", "en": "7-day study streak"}
    },
    "streak_30": {
        "icon": "👑",
        "title": {"ru": "Легенда привычки", "en": "Habit Legend"},
        "desc": {"ru": "Серия занятий 30 дней подряд", "en": "30-day study streak"}
    },
    "words_10": {
        "icon": "📖",
        "title": {"ru": "Первые слова", "en": "First Words"},
        "desc": {"ru": "Выучить 10 немецких слов", "en": "Learn 10 German words"}
    },
    "words_50": {
        "icon": "📚",
        "title": {"ru": "Книголюб", "en": "Word Collector"},
        "desc": {"ru": "Выучить 50 немецких слов", "en": "Learn 50 German words"}
    },
    "words_100": {
        "icon": "🧠",
        "title": {"ru": "Золотой словарь", "en": "Golden Vocabulary"},
        "desc": {"ru": "Выучить 100 немецких слов", "en": "Learn 100 German words"}
    },
    "articles_master": {
        "icon": "🎯",
        "title": {"ru": "Снайпер артиклей", "en": "Article Sniper"},
        "desc": {"ru": "Набрать 20 очков в тренажере der, die, das", "en": "Score 20 points in der/die/das trainer"}
    },
    "verbs_sprinter": {
        "icon": "⚡",
        "title": {"ru": "Мастер глаголов", "en": "Verb Master"},
        "desc": {"ru": "Успешно ответить в спринте глаголов и предлогов", "en": "Answer correctly in Verbs Sprint"}
    },
    "exam_writer": {
        "icon": "✍️",
        "title": {"ru": "Экзаменатор Schreiben", "en": "Schreiben Examiner"},
        "desc": {"ru": "Отправить письменную работу на проверку", "en": "Submit a letter for exam review"}
    },
    "exam_speaker": {
        "icon": "🎙️",
        "title": {"ru": "Оратор Sprechen", "en": "Sprechen Speaker"},
        "desc": {"ru": "Сдать устную часть экзамена голосовым сообщением", "en": "Complete oral exam part via voice"}
    },
    "placement_certified": {
        "icon": "🎓",
        "title": {"ru": "Сертификат CEFR", "en": "CEFR Certified"},
        "desc": {"ru": "Пройти тест и подтвердить свой уровень языка", "en": "Complete placement test to determine CEFR level"}
    },
    "listening_ear": {
        "icon": "🎧",
        "title": {"ru": "Чуткое ухо", "en": "Sharp Ear"},
        "desc": {"ru": "Правильно ответить в тренажере аудирования", "en": "Answer correctly in listening comprehension"}
    },
    "roleplay_master": {
        "icon": "🎭",
        "title": {"ru": "Мастер ролевой игры", "en": "Roleplay Master"},
        "desc": {"ru": "Успешно завершить ролевой диалог в Германии", "en": "Complete a German roleplay scenario"}
    }
}

async def unlock_achievement(user_id: int, badge_id: str) -> Optional[Dict[str, Any]]:
    """Разблокировать достижение для пользователя, если еще не открыто. Возвращает метаданные ачивки при новом открытии."""
    if badge_id not in ACHIEVEMENTS_REGISTRY:
        return None
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            async with db.execute(
                "SELECT 1 FROM user_achievements WHERE user_id = ? AND badge_id = ?",
                (user_id, badge_id)
            ) as cursor:
                if await cursor.fetchone():
                    return None
            await db.execute(
                "INSERT OR IGNORE INTO user_achievements (user_id, badge_id) VALUES (?, ?)",
                (user_id, badge_id)
            )
            await db.commit()
            ach = ACHIEVEMENTS_REGISTRY[badge_id].copy()
            ach["id"] = badge_id
            return ach
        except Exception as e:
            logger.error(f"Error unlocking achievement {badge_id} for user {user_id}: {e}")
            return None

async def get_user_unlocked_achievements(user_id: int) -> List[Dict[str, Any]]:
    """Получить список всех открытых достижений пользователя с датой получения"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT badge_id, unlocked_at FROM user_achievements WHERE user_id = ? ORDER BY unlocked_at ASC",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            results = []
            for r in rows:
                b_id = r["badge_id"]
                if b_id in ACHIEVEMENTS_REGISTRY:
                    item = ACHIEVEMENTS_REGISTRY[b_id].copy()
                    item["id"] = b_id
                    item["unlocked_at"] = r["unlocked_at"]
                    results.append(item)
            return results

async def check_and_grant_achievements(user_id: int) -> List[Dict[str, Any]]:
    """Проверить критерии прогресса пользователя и выдать заработанные ачивки"""
    newly_unlocked = []
    
    # 1. Всегда выдаем первый шаг
    a = await unlock_achievement(user_id, "first_step")
    if a:
        newly_unlocked.append(a)

    stats = await get_user_stats(user_id)
    streak = stats.get("streak", 0)
    score = stats.get("score", 0)
    known = stats.get("known_words", 0)
    placement = stats.get("placement_level")

    if streak >= 3:
        a = await unlock_achievement(user_id, "streak_3")
        if a: newly_unlocked.append(a)
    if streak >= 7:
        a = await unlock_achievement(user_id, "streak_7")
        if a: newly_unlocked.append(a)
    if streak >= 30:
        a = await unlock_achievement(user_id, "streak_30")
        if a: newly_unlocked.append(a)

    if known >= 10:
        a = await unlock_achievement(user_id, "words_10")
        if a: newly_unlocked.append(a)
    if known >= 50:
        a = await unlock_achievement(user_id, "words_50")
        if a: newly_unlocked.append(a)
    if known >= 100:
        a = await unlock_achievement(user_id, "words_100")
        if a: newly_unlocked.append(a)

    if score >= 20:
        a = await unlock_achievement(user_id, "articles_master")
        if a: newly_unlocked.append(a)

    if placement:
        a = await unlock_achievement(user_id, "placement_certified")
        if a: newly_unlocked.append(a)

    return newly_unlocked



