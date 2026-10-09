import random
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
import aiosqlite
import database.connection  # Активирует подключение к Turso при наличии TURSO_DATABASE_URL
from config import DB_PATH, DEFAULT_LANGUAGE, SUPER_ADMIN_IDS, ADMIN_IDS
from database.words_data import INITIAL_WORDS, CATEGORY_METADATA
from premium_config import (
    FREE_TRIAL_DAYS,
    PROMO_CODES,
    PREMIUM_PLANS,
    REFERRAL_CONFIG,
    LIFETIME_VIP_USERS,
    is_lifetime_vip_in_config,
    get_promo_info,
    get_plan_by_id,
    get_plan_price,
)

logger = logging.getLogger(__name__)

FREE_DAILY_AI_LIMIT = 5
FREE_DAILY_EXAM_LIMIT = 1
FREE_TOTAL_EXAM_LIMIT = 3
FREE_DAILY_WORDS_LIMIT = 20

async def init_db():
    """Инициализация базы данных SQLite, миграции и синхронизация словаря"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Настройки производительности SQLite (WAL-режим устраняет блокировки читателей и писателей)
        await db.execute("PRAGMA journal_mode = WAL;")
        await db.execute("PRAGMA synchronous = NORMAL;")
        await db.execute("PRAGMA busy_timeout = 5000;")
        await db.execute("PRAGMA cache_size = -64000;")
        await db.execute("PRAGMA temp_store = MEMORY;")

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
            total_exam_count INTEGER DEFAULT 0,
            daily_words_count INTEGER DEFAULT 0,
            last_usage_date TEXT DEFAULT '',
            notifications_enabled INTEGER DEFAULT 1,
            last_streak_date TEXT DEFAULT '',
            last_reminder_date TEXT DEFAULT '',
            lang_selected INTEGER DEFAULT 0
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

        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_promo_activations (
            user_id INTEGER NOT NULL,
            promo_code TEXT NOT NULL,
            activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            days_granted INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, promo_code)
        );
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_promo_user ON user_promo_activations(user_id);")

        await db.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inviter_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_ref_inviter ON referrals(inviter_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_ref_referred ON referrals(referred_id);")

        # Новые оптимизирующие индексы для мгновенной выборки слов, квизов и аналитики
        await db.execute("CREATE INDEX IF NOT EXISTS idx_words_level_cat ON words(level, category);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_words_category ON words(category);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_words_level ON words(level);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_progress_user_status_rev ON user_progress(user_id, status, last_reviewed);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_progress_user_status ON user_progress(user_id, status);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_translations_lang ON word_translations(lang);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_lang ON users(native_lang);")

        # Таблица истории диагностик и Readiness-тестов
        await db.execute("""
        CREATE TABLE IF NOT EXISTS diagnostic_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exam_type TEXT NOT NULL,
            exam_version TEXT DEFAULT 'v1',
            diagnostic_type TEXT DEFAULT 'readiness',
            cefr_estimate TEXT,
            readiness_status TEXT DEFAULT 'NOT_READY',
            overall_diagnostic_score INTEGER DEFAULT 0,
            lesen_score INTEGER DEFAULT 0,
            hoeren_score INTEGER DEFAULT 0,
            schreiben_score INTEGER DEFAULT 0,
            sprechen_score INTEGER DEFAULT 0,
            sprachbausteine_score INTEGER,
            raw_rubric_scores TEXT DEFAULT '{}',
            module_results_json TEXT DEFAULT '{}',
            weak_points_json TEXT DEFAULT '[]',
            strengths_json TEXT DEFAULT '[]',
            recommendations_json TEXT DEFAULT '[]',
            speaking_profile_json TEXT DEFAULT '{}',
            writing_profile_json TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_diag_user ON diagnostic_history(user_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_diag_type ON diagnostic_history(exam_type, diagnostic_type);")

        # Таблица персонализированного профиля обучения ученика
        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_learning_profile (
            user_id INTEGER PRIMARY KEY,
            target_exam TEXT DEFAULT 'goethe_b1',
            target_level TEXT DEFAULT 'B1',
            exam_date TEXT DEFAULT '',
            estimated_cefr TEXT DEFAULT 'A1',
            readiness_status TEXT DEFAULT 'NOT_READY',
            last_diagnostic_id INTEGER DEFAULT 0,
            weaknesses_json TEXT DEFAULT '[]',
            strengths_json TEXT DEFAULT '[]',
            recommendations_json TEXT DEFAULT '[]',
            speaking_profile_json TEXT DEFAULT '{}',
            writing_profile_json TEXT DEFAULT '{}',
            last_reassessment_at TIMESTAMP,
            next_reassessment_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            promo_type TEXT DEFAULT 'days',
            days INTEGER DEFAULT 30,
            discount_val INTEGER DEFAULT 0,
            max_activations INTEGER,
            used_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            description TEXT
        );
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS payments_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id TEXT NOT NULL,
            plan_title TEXT NOT NULL,
            stars_amount INTEGER DEFAULT 0,
            currency TEXT DEFAULT 'XTR',
            payment_method TEXT DEFAULT 'stars',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_payments_user ON payments_history(user_id);")

        await db.execute("""
        CREATE TABLE IF NOT EXISTS bot_admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            role TEXT NOT NULL DEFAULT 'admin',
            added_by INTEGER DEFAULT 0,
            notify_payments INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Главные супер-админы (владельцы) всегда имеют статус super_admin
        for sa_id in SUPER_ADMIN_IDS:
            sa_uname = "Amirist1" if sa_id == 6725392176 else "AmirIst1807"
            await db.execute("""
                INSERT INTO bot_admins (user_id, username, role, added_by, notify_payments)
                VALUES (?, ?, 'super_admin', ?, 1)
                ON CONFLICT(user_id) DO UPDATE SET role = 'super_admin'
            """, (sa_id, sa_uname, sa_id))

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
            if "trial_used" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN trial_used INTEGER DEFAULT 0")
            if "is_lifetime_vip" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN is_lifetime_vip INTEGER DEFAULT 0")
            if "subscription_type" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN subscription_type TEXT DEFAULT 'none'")
            if "daily_ai_count" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN daily_ai_count INTEGER DEFAULT 0")
            if "daily_exam_count" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN daily_exam_count INTEGER DEFAULT 0")
            if "total_exam_count" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN total_exam_count INTEGER DEFAULT 0")
            if "daily_words_count" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN daily_words_count INTEGER DEFAULT 0")
            if "last_usage_date" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN last_usage_date TEXT DEFAULT ''")
            if "notifications_enabled" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN notifications_enabled INTEGER DEFAULT 1")
            if "last_streak_date" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN last_streak_date TEXT DEFAULT ''")
            if "last_reminder_date" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN last_reminder_date TEXT DEFAULT ''")
            if "lang_selected" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN lang_selected INTEGER DEFAULT 0")

        # Миграция: проверяем наличие столбца status в user_progress
        async with db.execute("PRAGMA table_info(user_progress)") as cursor:
            prog_cols = [row[1] for row in await cursor.fetchall()]
            if "status" not in prog_cols:
                await db.execute("ALTER TABLE user_progress ADD COLUMN status TEXT DEFAULT 'learning'")

        await db.commit()

        # Синхронизация слов из INITIAL_WORDS (пропускаем, если база уже заполнена)
        async with db.execute("SELECT COUNT(*) FROM words") as cursor:
            words_cnt_row = await cursor.fetchone()
            current_words_cnt = words_cnt_row[0] if words_cnt_row else 0

        if current_words_cnt >= len(INITIAL_WORDS):
            logger.info(f"Словарь Stork ({current_words_cnt} слов) уже синхронизирован с базой данных.")
        else:
            logger.info(f"Синхронизация {len(INITIAL_WORDS)} слов с базой данных (сейчас {current_words_cnt})...")
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

        # Инициализация базовых промокодов, если таблица пуста
        async with db.execute("SELECT COUNT(*) FROM promo_codes") as cursor:
            promo_cnt = (await cursor.fetchone())[0]
            if promo_cnt == 0:
                for p_code, p_info in PROMO_CODES.items():
                    await db.execute("""
                        INSERT OR IGNORE INTO promo_codes (code, promo_type, days, description)
                        VALUES (?, 'days', ?, ?)
                    """, (p_code.upper(), int(p_info.get("days", 30)), p_info.get("description", "")))
                await db.commit()
                logger.info("Базовые промокоды Stork успешно инициализированы в таблице promo_codes.")

        # Загрузка ролей администраторов и настроек оповещений в оперативный кэш
        async with db.execute("SELECT user_id, role, notify_payments FROM bot_admins") as cursor:
            for r in await cursor.fetchall():
                _ACTIVE_ADMINS_CACHE[r[0]] = r[1]
                _ADMIN_NOTIFY_CACHE[r[0]] = r[2]
        for sa_id in SUPER_ADMIN_IDS:
            _ACTIVE_ADMINS_CACHE[sa_id] = "super_admin"
            if sa_id not in _ADMIN_NOTIFY_CACHE:
                _ADMIN_NOTIFY_CACHE[sa_id] = 1

# Быстрый оперативный кэш в памяти (In-Memory Cache) для устранения микрофризов интерфейса
_USER_LANG_CACHE: Dict[int, str] = {}
_USER_FILTERS_CACHE: Dict[int, Tuple[str, str]] = {}
_ACTIVE_ADMINS_CACHE: Dict[int, str] = {}
_ADMIN_NOTIFY_CACHE: Dict[int, int] = {}

def clear_user_cache(user_id: Optional[int] = None):
    """Сброс оперативного кэша пользователя (для тестов или сброса)"""
    if user_id is not None:
        _USER_LANG_CACHE.pop(user_id, None)
        _USER_FILTERS_CACHE.pop(user_id, None)
    else:
        _USER_LANG_CACHE.clear()
        _USER_FILTERS_CACHE.clear()
        _ACTIVE_ADMINS_CACHE.clear()
        _ADMIN_NOTIFY_CACHE.clear()
        for sa_id in SUPER_ADMIN_IDS:
            _ACTIVE_ADMINS_CACHE[sa_id] = "super_admin"
            _ADMIN_NOTIFY_CACHE[sa_id] = 1

async def get_or_create_user(user_id: int, username: Optional[str], first_name: Optional[str]) -> Dict[str, Any]:
    """Получить или зарегистрировать пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                res = dict(row)
                res["is_new"] = False
                _USER_LANG_CACHE[user_id] = res.get("native_lang") or DEFAULT_LANGUAGE
                _USER_FILTERS_CACHE[user_id] = (res.get("selected_level") or "ALL", res.get("selected_category") or "ALL")
                return res

        await db.execute(
            "INSERT INTO users (user_id, username, first_name, native_lang, selected_level, selected_category, lang_selected) VALUES (?, ?, ?, ?, 'ALL', 'ALL', 0)",
            (user_id, username or "", first_name or "", DEFAULT_LANGUAGE)
        )
        await db.commit()
        _USER_LANG_CACHE[user_id] = DEFAULT_LANGUAGE
        _USER_FILTERS_CACHE[user_id] = ("ALL", "ALL")
        return {
            "user_id": user_id,
            "username": username or "",
            "first_name": first_name or "",
            "native_lang": DEFAULT_LANGUAGE,
            "selected_level": "ALL",
            "selected_category": "ALL",
            "score": 0,
            "streak": 0,
            "trial_used": 0,
            "lang_selected": 0,
            "is_new": True
        }

async def update_user_lang(user_id: int, lang: str):
    """Обновить язык интерфейса пользователя"""
    _USER_LANG_CACHE[user_id] = lang
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET native_lang = ?, lang_selected = 1, last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
            (lang, user_id)
        )
        await db.commit()

async def set_user_lang_selected(user_id: int, selected: bool = True):
    """Отметить, что пользователь прошел выбор языка"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET lang_selected = ? WHERE user_id = ?",
            (1 if selected else 0, user_id)
        )
        await db.commit()

async def get_user_lang(user_id: int) -> str:
    """Получить язык интерфейса пользователя (сверхбыстро из памяти)"""
    if user_id in _USER_LANG_CACHE:
        return _USER_LANG_CACHE[user_id]

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT native_lang FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                _USER_LANG_CACHE[user_id] = row[0]
                return row[0]

    _USER_LANG_CACHE[user_id] = DEFAULT_LANGUAGE
    return DEFAULT_LANGUAGE

async def get_user_filters(user_id: int) -> Tuple[str, str]:
    """Получить текущие фильтры пользователя: (level, category) (сверхбыстро из памяти)"""
    if user_id in _USER_FILTERS_CACHE:
        return _USER_FILTERS_CACHE[user_id]

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT selected_level, selected_category FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                res = (row[0] or "ALL", row[1] or "ALL")
                _USER_FILTERS_CACHE[user_id] = res
                return res

    res = ("ALL", "ALL")
    _USER_FILTERS_CACHE[user_id] = res
    return res

async def set_user_level(user_id: int, level: str):
    """Установить фильтр по уровню сложности (ALL, A1, A2, B1)"""
    curr = _USER_FILTERS_CACHE.get(user_id, ("ALL", "ALL"))
    _USER_FILTERS_CACHE[user_id] = (level, curr[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET selected_level = ? WHERE user_id = ?", (level, user_id))
        await db.commit()

async def set_user_category(user_id: int, category: str):
    """Установить фильтр по категории слов (ALL или название категории)"""
    curr = _USER_FILTERS_CACHE.get(user_id, ("ALL", "ALL"))
    _USER_FILTERS_CACHE[user_id] = (curr[0], category)
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
            "total_exam_count": user["total_exam_count"] if user and "total_exam_count" in user.keys() else 0,
            "total_exam_limit": -1 if is_prem else FREE_TOTAL_EXAM_LIMIT,
            "daily_words_count": user["daily_words_count"] if user and "daily_words_count" in user.keys() else 0,
            "daily_words_limit": -1 if is_prem else FREE_DAILY_WORDS_LIMIT,
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
            "UPDATE users SET daily_ai_count = 0, daily_exam_count = 0, daily_words_count = 0, last_usage_date = ? WHERE user_id = ?",
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
    """
    Проверить статус Stork Premium и дату окончания.
    Если у пользователя активирован пожизненный VIP, возвращает (True, "lifetime").
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT username, is_premium, premium_until, is_lifetime_vip FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            if is_lifetime_vip_in_config(user_id):
                return True, "lifetime"
            return False, None

        username = row["username"]
        is_db_lifetime = bool(row["is_lifetime_vip"]) if ("is_lifetime_vip" in row.keys() and row["is_lifetime_vip"]) else False
        is_cfg_lifetime = is_lifetime_vip_in_config(user_id, username)

        if is_db_lifetime or is_cfg_lifetime:
            return True, "lifetime"

        if not row["is_premium"]:
            return False, None

        premium_until = row["premium_until"]
        if premium_until:
            now_str = datetime.now(timezone.utc).isoformat()
            if premium_until < now_str:
                await db.execute("UPDATE users SET is_premium = 0 WHERE user_id = ?", (user_id,))
                await db.commit()
                return False, None
        return True, premium_until

async def set_user_lifetime_vip(target: Any, is_vip: bool = True) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Выдать или отозвать пожизненный VIP по user_id или username.
    Возвращает (успех, статус, данные_пользователя).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        user_row = None
        target_str = str(target).strip()
        if target_str.isdigit() or isinstance(target, int):
            target_uid = int(target)
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (target_uid,)) as cursor:
                user_row = await cursor.fetchone()
        else:
            clean_name = target_str.lstrip("@")
            async with db.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (clean_name,)) as cursor:
                user_row = await cursor.fetchone()

        if not user_row:
            return False, "user_not_found", None

        uid = user_row["user_id"]
        if is_vip:
            await db.execute("UPDATE users SET is_lifetime_vip = 1, is_premium = 1 WHERE user_id = ?", (uid,))
        else:
            now_str = datetime.now(timezone.utc).isoformat()
            await db.execute("""
                UPDATE users 
                SET is_lifetime_vip = 0,
                    is_premium = CASE 
                        WHEN premium_until IS NOT NULL AND premium_until > ? THEN 1 
                        ELSE 0 
                    END
                WHERE user_id = ?
            """, (now_str, uid))
        await db.commit()

        return True, "success", dict(user_row)

async def get_all_lifetime_vip_users() -> Dict[str, Any]:
    """Получить список всех пользователей с активным вечным VIP (из базы и из конфига)"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT user_id, username, first_name, is_lifetime_vip FROM users WHERE is_lifetime_vip = 1") as cursor:
            db_vips = [dict(r) for r in await cursor.fetchall()]

    cfg_vips = []
    for item in LIFETIME_VIP_USERS:
        cfg_vips.append(item)

    return {"database_vips": db_vips, "config_vips": cfg_vips}

async def activate_premium(user_id: int, days: int = 30) -> str:
    """
    Активировать или продлить Stork Premium на указанное количество дней.
    Если у пользователя уже есть активная подписка, дни добавляются к текущему сроку.
    """
    now = datetime.now(timezone.utc)
    base_dt = now

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT premium_until FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row["premium_until"]:
                try:
                    curr_dt = datetime.fromisoformat(row["premium_until"])
                    if curr_dt.tzinfo is None:
                        curr_dt = curr_dt.replace(tzinfo=timezone.utc)
                    if curr_dt > now:
                        base_dt = curr_dt
                except Exception:
                    base_dt = now

        until_dt = base_dt + timedelta(days=days)
        until_str = until_dt.isoformat()
        await db.execute(
            "UPDATE users SET is_premium = 1, premium_until = ? WHERE user_id = ?",
            (until_str, user_id)
        )
        await db.commit()
    return until_str

async def is_trial_available(user_id: int) -> bool:
    """Проверить, доступен ли пользователю бесплатный пробный период"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT trial_used FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return False
            return True

async def activate_trial_if_eligible(user_id: int, days: int = FREE_TRIAL_DAYS) -> Tuple[bool, str, Optional[str]]:
    """
    Активировать одноразовый пробный период на days дней.
    Возвращает (успех, статус, дата_окончания).
    Статусы: 'success', 'already_used'.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT trial_used, premium_until FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row["trial_used"]:
                return False, "already_used", row["premium_until"]

        await db.execute("UPDATE users SET trial_used = 1 WHERE user_id = ?", (user_id,))
        await db.commit()

    until_str = await activate_premium(user_id, days=days)
    return True, "success", until_str

async def activate_promo_code(user_id: int, code: str) -> Tuple[bool, str, int, Optional[str]]:
    """
    Проверить и активировать промокод.
    Каждый промокод одноразовый для каждого конкретного пользователя.
    Возвращает: (успех, статус, начислено_дней, дата_окончания).
    Статусы: 'success', 'already_used', 'invalid_code', 'expired_or_inactive', 'limit_reached', 'discount'.
    """
    normalized_code = code.strip().upper()
    now_dt = datetime.now(timezone.utc)
    now_str = now_dt.isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Проверяем, активировал ли этот пользователь данный промокод ранее
        async with db.execute(
            "SELECT 1 FROM user_promo_activations WHERE user_id = ? AND promo_code = ?",
            (user_id, normalized_code)
        ) as cursor:
            if await cursor.fetchone():
                _, until_str = await is_user_premium(user_id)
                return False, "already_used", 0, until_str

        # 1. Сначала ищем промокод в базе данных
        async with db.execute("SELECT * FROM promo_codes WHERE code = ?", (normalized_code,)) as cursor:
            db_promo = await cursor.fetchone()

        if db_promo:
            if not db_promo["is_active"]:
                return False, "expired_or_inactive", 0, None
            if db_promo["expires_at"] and db_promo["expires_at"] < now_str:
                return False, "expired_or_inactive", 0, None
            if db_promo["max_activations"] is not None and db_promo["used_count"] >= db_promo["max_activations"]:
                return False, "limit_reached", 0, None

            p_type = db_promo["promo_type"]
            days = db_promo["days"] or 30

            # Фиксируем активацию
            await db.execute(
                "INSERT INTO user_promo_activations (user_id, promo_code, days_granted) VALUES (?, ?, ?)",
                (user_id, normalized_code, days if p_type != "lifetime" else 36500)
            )
            await db.execute(
                "UPDATE promo_codes SET used_count = used_count + 1 WHERE code = ?",
                (normalized_code,)
            )

            if p_type == "lifetime":
                await db.execute("UPDATE users SET is_lifetime_vip = 1, is_premium = 1, subscription_type = 'promo_lifetime' WHERE user_id = ?", (user_id,))
                await db.commit()
                return True, "success", 0, "lifetime"
            elif p_type in ("discount_percent", "discount_stars"):
                await db.commit()
                return True, "discount", db_promo["discount_val"], None
            else:
                await db.execute("UPDATE users SET subscription_type = 'promo' WHERE user_id = ?", (user_id,))
                await db.commit()
                until_str = await activate_premium(user_id, days=days)
                return True, "success", days, until_str

        # 2. Фолбэк на статический словарь в premium_config.py
        promo_info = get_promo_info(normalized_code)
        if not promo_info:
            return False, "invalid_code", 0, None

        days = int(promo_info.get("days", 30))
        await db.execute(
            "INSERT INTO user_promo_activations (user_id, promo_code, days_granted) VALUES (?, ?, ?)",
            (user_id, normalized_code, days)
        )
        await db.execute("UPDATE users SET subscription_type = 'promo' WHERE user_id = ?", (user_id,))
        await db.commit()

    until_str = await activate_premium(user_id, days=days)
    return True, "success", days, until_str

# ==============================================================================
# АДМИН-ПАНЕЛЬ: УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ, ПОДПИСКАМИ И ПРОМОКОДАМИ
# ==============================================================================

async def record_payment(
    user_id: int,
    plan_id: str,
    plan_title: str,
    stars_amount: int,
    currency: str = "XTR",
    payment_method: str = "stars"
) -> int:
    """Записать транзакцию об оплате в историю платежей"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            INSERT INTO payments_history (user_id, plan_id, plan_title, stars_amount, currency, payment_method)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, plan_id, plan_title, stars_amount, currency, payment_method)) as cur:
            row_id = cur.lastrowid
        await db.commit()
    return row_id

async def get_admin_stats() -> Dict[str, Any]:
    """Сбор расширенной статистики для админ-панели (пользователи, подписки, финансы, MRR)"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # 1. Всего пользователей
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total_users = (await cur.fetchone())[0]

        # 2. Активные за 24 часа и за 7 дней
        now_dt = datetime.now(timezone.utc)
        today_start = (now_dt - timedelta(days=1)).isoformat()
        week_start = (now_dt - timedelta(days=7)).isoformat()

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE last_active >= ?", (today_start,)
        ) as cur:
            active_today = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE last_active >= ?", (week_start,)
        ) as cur:
            active_7d = (await cur.fetchone())[0]

        # 3. Новые пользователи за сегодня (за 24ч)
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE last_active >= ?", (today_start,)
        ) as cur:
            new_today = active_today

        # 4. Активные Premium
        now_str = now_dt.isoformat()
        async with db.execute("""
            SELECT COUNT(*) FROM users 
            WHERE is_lifetime_vip = 1 OR (is_premium = 1 AND (premium_until IS NULL OR premium_until > ?))
        """, (now_str,)) as cur:
            total_premium = (await cur.fetchone())[0]

        # 5. Разбивка по типам подписки
        async with db.execute("SELECT COUNT(*) FROM users WHERE is_lifetime_vip = 1") as cur:
            cnt_lifetime = (await cur.fetchone())[0]

        async with db.execute("""
            SELECT subscription_type, COUNT(*) as cnt 
            FROM users 
            WHERE is_lifetime_vip = 0 AND is_premium = 1 AND (premium_until IS NULL OR premium_until > ?)
            GROUP BY subscription_type
        """, (now_str,)) as cur:
            type_rows = await cur.fetchall()
            types_map = {r["subscription_type"] or "other": r["cnt"] for r in type_rows}

        cnt_1m = types_map.get("plan_1m", 0)
        cnt_3m = types_map.get("plan_3m", 0)
        cnt_1y = types_map.get("plan_1y", 0)
        cnt_trial = types_map.get("trial", 0)
        cnt_promo = types_map.get("promo", 0)
        cnt_manual = types_map.get("manual", 0)
        cnt_other = sum(v for k, v in types_map.items() if k not in ("plan_1m", "plan_3m", "plan_1y", "trial", "promo", "manual"))

        # 6. Оплаты и доход
        async with db.execute(
            "SELECT COUNT(*), COALESCE(SUM(stars_amount), 0) FROM payments_history"
        ) as cur:
            p_row = await cur.fetchone()
            total_payments_count = p_row[0]
            total_revenue_stars = p_row[1]

        # 7. Ожидаемый MRR (Monthly Recurring Revenue)
        mrr_stars = int(cnt_1m * 250 + cnt_3m * (650 / 3) + cnt_1y * (1990 / 12))
        mrr_eur = round(mrr_stars * 0.02, 2)
        total_revenue_eur = round(total_revenue_stars * 0.02, 2)

        return {
            "total_users": total_users,
            "active_today": active_today,
            "active_7d": active_7d,
            "new_today": new_today,
            "total_premium": total_premium,
            "cnt_lifetime": cnt_lifetime,
            "cnt_1m": cnt_1m,
            "cnt_3m": cnt_3m,
            "cnt_1y": cnt_1y,
            "cnt_trial": cnt_trial,
            "cnt_promo": cnt_promo,
            "cnt_manual": cnt_manual,
            "cnt_other": cnt_other,
            "total_payments_count": total_payments_count,
            "total_revenue_stars": total_revenue_stars,
            "total_revenue_eur": total_revenue_eur,
            "mrr_stars": mrr_stars,
            "mrr_eur": mrr_eur,
        }

async def get_user_admin_info(target: Any) -> Optional[Dict[str, Any]]:
    """Найти пользователя по ID или username со всеми деталями для админа"""
    target_str = str(target).strip()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if target_str.isdigit() or isinstance(target, int):
            uid = int(target)
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (uid,)) as cur:
                user_row = await cur.fetchone()
        else:
            clean_name = target_str.lstrip("@")
            async with db.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (clean_name,)) as cur:
                user_row = await cur.fetchone()

        if not user_row:
            return None

        u = dict(user_row)
        user_id = u["user_id"]

        async with db.execute("SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND status = 'learned'", (user_id,)) as cur:
            u["words_learned"] = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM user_progress WHERE user_id = ?", (user_id,)) as cur:
            u["words_total"] = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM referrals WHERE inviter_id = ?", (user_id,)) as cur:
            u["referrals_count"] = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*), COALESCE(SUM(stars_amount), 0) FROM payments_history WHERE user_id = ?", (user_id,)) as cur:
            p_row = await cur.fetchone()
            u["payments_count"] = p_row[0]
            u["payments_sum"] = p_row[1]

        return u

async def grant_user_premium(
    target: Any,
    days: int = 30,
    sub_type: str = "manual"
) -> Tuple[bool, str, Optional[Dict[str, Any]], str]:
    """
    Выдать пользователю Premium вручную через админку.
    Возвращает (успех, статус, пользователь, дата_окончания).
    """
    user_info = await get_user_admin_info(target)
    if not user_info:
        return False, "user_not_found", None, ""

    uid = user_info["user_id"]
    if days >= 36500 or sub_type == "lifetime":
        await set_user_lifetime_vip(uid, True)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET subscription_type = 'lifetime' WHERE user_id = ?", (uid,))
            await db.commit()
        return True, "lifetime", user_info, "lifetime"
    else:
        until_str = await activate_premium(uid, days=days)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET subscription_type = ? WHERE user_id = ?", (sub_type, uid))
            await db.commit()
        return True, "success", user_info, until_str

async def revoke_user_premium(target: Any) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Отозвать Premium-статус у пользователя"""
    user_info = await get_user_admin_info(target)
    if not user_info:
        return False, "user_not_found", None

    uid = user_info["user_id"]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users 
            SET is_premium = 0,
                premium_until = NULL,
                is_lifetime_vip = 0,
                subscription_type = 'none'
            WHERE user_id = ?
        """, (uid,))
        await db.commit()
    return True, "revoked", user_info

async def create_db_promo_code(
    code: str,
    promo_type: str = "days",
    days: int = 30,
    discount_val: int = 0,
    max_activations: Optional[int] = None,
    expires_days: Optional[int] = None,
    description: str = ""
) -> Tuple[bool, str]:
    """Создать новый промокод в базе данных"""
    norm_code = code.strip().upper()
    expires_at = None
    if expires_days:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_days)).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM promo_codes WHERE code = ?", (norm_code,)) as cur:
            if await cur.fetchone():
                return False, "already_exists"

        await db.execute("""
            INSERT INTO promo_codes (code, promo_type, days, discount_val, max_activations, expires_at, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (norm_code, promo_type, days, discount_val, max_activations, expires_at, description))
        await db.commit()

    return True, norm_code

async def get_all_db_promo_codes() -> List[Dict[str, Any]]:
    """Получить список всех промокодов из базы данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM promo_codes ORDER BY created_at DESC") as cur:
            return [dict(r) for r in await cur.fetchall()]

async def deactivate_db_promo_code(code: str) -> bool:
    """Деактивировать промокод"""
    norm_code = code.strip().upper()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE promo_codes SET is_active = 0 WHERE code = ?", (norm_code,))
        await db.commit()
    return True

async def delete_db_promo_code(code: str) -> bool:
    """Удалить промокод из базы данных"""
    norm_code = code.strip().upper()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM promo_codes WHERE code = ?", (norm_code,))
        await db.commit()
    return True

async def get_broadcast_user_ids(audience: str = "all") -> List[int]:
    """Получить список ID пользователей для рассылки (all, premium, free)"""
    now_str = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        if audience == "premium":
            query = """
                SELECT user_id FROM users 
                WHERE is_lifetime_vip = 1 OR (is_premium = 1 AND (premium_until IS NULL OR premium_until > ?))
            """
            params = (now_str,)
        elif audience == "free":
            query = """
                SELECT user_id FROM users 
                WHERE is_lifetime_vip = 0 AND (is_premium = 0 OR (premium_until IS NOT NULL AND premium_until <= ?))
            """
            params = (now_str,)
        else:
            query = "SELECT user_id FROM users"
            params = ()

        async with db.execute(query, params) as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]


# ==============================================================================
# СИСТЕМА РОЛЕЙ И УПРАВЛЕНИЯ АДМИНИСТРАТОРАМИ
# ==============================================================================

async def get_user_admin_role(user_id: int) -> Optional[str]:
    """
    Получить роль администратора:
    - 'super_admin': Главный владелец (нельзя удалить или понизить, доступно все)
    - 'admin': Администратор (статистика, пользователи, промокоды, бэкап, рассылка)
    - 'analyst': Аналитик (только просмотр статистики)
    - 'broadcaster': Менеджер рассылок (только рассылка)
    - None: Нет доступа
    """
    if user_id in SUPER_ADMIN_IDS:
        return "super_admin"

    if user_id in _ACTIVE_ADMINS_CACHE:
        return _ACTIVE_ADMINS_CACHE[user_id]

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT role, notify_payments FROM bot_admins WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row:
                _ACTIVE_ADMINS_CACHE[user_id] = row[0]
                _ADMIN_NOTIFY_CACHE[user_id] = row[1]
                return row[0]
    return None

async def is_admin_user(user_id: int) -> bool:
    """Проверка наличия любого админского доступа"""
    role = await get_user_admin_role(user_id)
    return role is not None

async def is_super_admin_user(user_id: int) -> bool:
    """Проверка, является ли пользователь главным владельцем (Super Admin)"""
    return user_id in SUPER_ADMIN_IDS

async def can_view_stats(user_id: int) -> bool:
    """Право на просмотр аналитики и метрик"""
    role = await get_user_admin_role(user_id)
    return role in ("super_admin", "admin", "analyst")

async def can_manage_users(user_id: int) -> bool:
    """Право на поиск пользователей, выдачу и отзыв Premium"""
    role = await get_user_admin_role(user_id)
    return role in ("super_admin", "admin")

async def can_manage_promos(user_id: int) -> bool:
    """Право на создание и отключение промокодов"""
    role = await get_user_admin_role(user_id)
    return role in ("super_admin", "admin")

async def can_download_backup(user_id: int) -> bool:
    """Право на скачивание резервной копии базы данных"""
    role = await get_user_admin_role(user_id)
    return role in ("super_admin", "admin")

async def can_broadcast(user_id: int) -> bool:
    """Право на создание и отправку рассылок"""
    role = await get_user_admin_role(user_id)
    return role in ("super_admin", "admin", "broadcaster")

async def can_manage_admins(user_id: int) -> bool:
    """Право на добавление и удаление админов (строго главные супер-админы)"""
    return user_id in SUPER_ADMIN_IDS

async def get_all_admins() -> List[Dict[str, Any]]:
    """Получить список всех администраторов с ролями и статусом оповещений"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM bot_admins 
            ORDER BY CASE WHEN role = 'super_admin' THEN 0 ELSE 1 END, created_at ASC
        """) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def add_bot_admin(
    user_id: int,
    username: str = "",
    role: str = "admin",
    added_by: int = 0
) -> Tuple[bool, str]:
    """
    Добавить или изменить роль администратора.
    Строгая защита: только супер-админы могут вызывать эту функцию!
    Супер-админов изменить нельзя!
    """
    if added_by not in SUPER_ADMIN_IDS:
        return False, "permission_denied"

    if user_id in SUPER_ADMIN_IDS:
        return False, "cannot_modify_super_admin"

    if role not in ("admin", "analyst", "broadcaster"):
        return False, "invalid_role"

    clean_username = username.lstrip("@").strip()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO bot_admins (user_id, username, role, added_by, notify_payments)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                username = CASE WHEN excluded.username != '' THEN excluded.username ELSE bot_admins.username END,
                role = excluded.role,
                added_by = excluded.added_by
        """, (user_id, clean_username, role, added_by))
        await db.commit()

    _ACTIVE_ADMINS_CACHE[user_id] = role
    _ADMIN_NOTIFY_CACHE[user_id] = _ADMIN_NOTIFY_CACHE.get(user_id, 1)
    if user_id not in ADMIN_IDS:
        ADMIN_IDS.append(user_id)

    return True, role

async def remove_bot_admin(user_id: int, removed_by: int) -> Tuple[bool, str]:
    """
    Удалить администратора из команды.
    Строгая защита: двух главных супер-админов удалить невозможно ни при каких условиях!
    Только супер-админ может удалять других админов.
    """
    if removed_by not in SUPER_ADMIN_IDS:
        return False, "permission_denied"

    if user_id in SUPER_ADMIN_IDS:
        return False, "cannot_remove_super_admin"

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM bot_admins WHERE user_id = ?", (user_id,))
        await db.commit()

    _ACTIVE_ADMINS_CACHE.pop(user_id, None)
    _ADMIN_NOTIFY_CACHE.pop(user_id, None)
    if user_id in ADMIN_IDS and user_id not in SUPER_ADMIN_IDS:
        ADMIN_IDS.remove(user_id)

    return True, "removed"

async def toggle_admin_notifications(user_id: int) -> Tuple[bool, int]:
    """Переключить получение уведомлений об оплатах (ВКЛ / ВЫКЛ)"""
    current_status = await get_admin_notification_status(user_id)
    new_status = 0 if current_status == 1 else 1

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM bot_admins WHERE user_id = ?", (user_id,)) as cur:
            exists = await cur.fetchone()

        if exists:
            await db.execute("UPDATE bot_admins SET notify_payments = ? WHERE user_id = ?", (new_status, user_id))
        else:
            role = "super_admin" if user_id in SUPER_ADMIN_IDS else "admin"
            await db.execute("""
                INSERT INTO bot_admins (user_id, role, notify_payments)
                VALUES (?, ?, ?)
            """, (user_id, role, new_status))
        await db.commit()

    _ADMIN_NOTIFY_CACHE[user_id] = new_status
    return True, new_status

async def get_admin_notification_status(user_id: int) -> int:
    """Получить статус уведомлений конкретного админа (1 - вкл, 0 - выкл)"""
    if user_id in _ADMIN_NOTIFY_CACHE:
        return _ADMIN_NOTIFY_CACHE[user_id]

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT notify_payments FROM bot_admins WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row:
                _ADMIN_NOTIFY_CACHE[user_id] = row[0]
                return row[0]

    return 1

async def get_notification_admin_ids() -> List[int]:
    """Получить список ID админов, у которых включены оповещения об оплатах"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM bot_admins WHERE notify_payments = 1") as cur:
            rows = await cur.fetchall()
            ids = [r[0] for r in rows]

    if not ids:
        return [sa for sa in SUPER_ADMIN_IDS if _ADMIN_NOTIFY_CACHE.get(sa, 1) == 1]
    return ids



async def register_referral(inviter_id: int, referred_id: int) -> Optional[Dict[str, Any]]:
    """
    Зарегистрировать приглашенного пользователя.
    Начисляет инвайтеру +1 день (или по REFERRAL_CONFIG),
    а при достижении 10 рефералов дарит супер-бонус +5 дней (суммарно 15 дней).
    """
    if inviter_id == referred_id:
        return None

    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, был ли referred_id уже приглашен
        async with db.execute("SELECT 1 FROM referrals WHERE referred_id = ?", (referred_id,)) as cursor:
            if await cursor.fetchone():
                return None

        # Проверяем наличие инвайтера в базе
        async with db.execute("SELECT 1 FROM users WHERE user_id = ?", (inviter_id,)) as cursor:
            if not await cursor.fetchone():
                return None

        try:
            await db.execute(
                "INSERT INTO referrals (inviter_id, referred_id) VALUES (?, ?)",
                (inviter_id, referred_id)
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Ошибка сохранения реферала {inviter_id} -> {referred_id}: {e}")
            return None

        async with db.execute("SELECT COUNT(*) FROM referrals WHERE inviter_id = ?", (inviter_id,)) as cursor:
            row = await cursor.fetchone()
            total_count = row[0] if row else 1

    days_per_invite = REFERRAL_CONFIG.get("days_per_invite", 1)
    milestone_target = REFERRAL_CONFIG.get("milestone_invites", 10)
    milestone_bonus = REFERRAL_CONFIG.get("milestone_bonus_days", 5)

    days_to_grant = days_per_invite
    milestone_hit = False

    if total_count == milestone_target:
        days_to_grant += milestone_bonus
        milestone_hit = True

    new_until = await activate_premium(inviter_id, days=days_to_grant)

    return {
        "success": True,
        "total_referrals": total_count,
        "days_granted": days_to_grant,
        "milestone_hit": milestone_hit,
        "new_until": new_until,
    }

async def get_referral_stats(user_id: int) -> Dict[str, Any]:
    """
    Получить статистику рефералов для пользователя:
    - количество приглашенных
    - заработано дней
    - достигнута ли цель
    - активна ли скидка 50%
    """
    milestone_target = REFERRAL_CONFIG.get("milestone_invites", 10)
    days_per_invite = REFERRAL_CONFIG.get("days_per_invite", 1)
    milestone_bonus = REFERRAL_CONFIG.get("milestone_bonus_days", 5)
    discount_percent = REFERRAL_CONFIG.get("milestone_discount_percent", 50)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM referrals WHERE inviter_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            count = row[0] if row else 0

    days_earned = count * days_per_invite
    if count >= milestone_target:
        days_earned += milestone_bonus

    milestone_reached = count >= milestone_target
    needed = max(0, milestone_target - count)

    return {
        "count": count,
        "days_earned": days_earned,
        "milestone_target": milestone_target,
        "milestone_reached": milestone_reached,
        "needed_for_milestone": needed,
        "has_discount": milestone_reached and (discount_percent > 0),
        "discount_percent": discount_percent if milestone_reached else 0,
    }

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
    Проверить доступность проверки экзаменационных писем и устных ответов.
    Возвращает (разрешено, использовано_сегодня, лимит).
    Для Premium лимит равен -1 (безлимит).
    Для бесплатного тарифа: максимум 1 в день И максимум 3 суммарно на аккаунт.
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

            # Проверка суммарного лимита за всё время на бесплатном аккаунте
            total_used = row["total_exam_count"] if "total_exam_count" in row.keys() and row["total_exam_count"] is not None else 0
            if total_used >= FREE_TOTAL_EXAM_LIMIT:
                return False, total_used, FREE_TOTAL_EXAM_LIMIT

            used = row["daily_exam_count"] or 0
            allowed = used < FREE_DAILY_EXAM_LIMIT
            return allowed, used, FREE_DAILY_EXAM_LIMIT

async def increment_exam_quota(user_id: int):
    """Увеличить счетчик проверенных экзаменационных работ (дневной и общий)"""
    today_str = _get_current_date_str()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                await _ensure_daily_reset(db, row, today_str)
                await db.execute(
                    "UPDATE users SET daily_exam_count = daily_exam_count + 1, total_exam_count = COALESCE(total_exam_count, 0) + 1 WHERE user_id = ?",
                    (user_id,)
                )
                await db.commit()

async def check_words_quota(user_id: int) -> Tuple[bool, int, int]:
    """
    Проверить доступность тренировки слов и карточек.
    Возвращает (разрешено, использовано_сегодня, лимит).
    Для Premium лимит равен -1 (безлимит).
    Для бесплатного аккаунта: максимум FREE_DAILY_WORDS_LIMIT (20 слов в день).
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
                return True, 0, FREE_DAILY_WORDS_LIMIT
            row = await _ensure_daily_reset(db, row, today_str)
            used = row["daily_words_count"] if "daily_words_count" in row.keys() and row["daily_words_count"] is not None else 0
            allowed = used < FREE_DAILY_WORDS_LIMIT
            return allowed, used, FREE_DAILY_WORDS_LIMIT

async def increment_words_quota(user_id: int):
    """Увеличить дневной счетчик пройденных слов"""
    today_str = _get_current_date_str()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                await _ensure_daily_reset(db, row, today_str)
                await db.execute(
                    "UPDATE users SET daily_words_count = COALESCE(daily_words_count, 0) + 1 WHERE user_id = ?",
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

# ==========================================
# ДИАГНОСТИКА И ПРОФИЛЬ ОБУЧЕНИЯ (READINESS)
# ==========================================
import json

async def save_diagnostic_result(
    user_id: int,
    exam_type: str,
    exam_version: str = "v1",
    diagnostic_type: str = "readiness",
    cefr_estimate: str = "A2",
    readiness_status: str = "NOT_READY",
    overall_diagnostic_score: int = 0,
    lesen_score: int = 0,
    hoeren_score: int = 0,
    schreiben_score: int = 0,
    sprechen_score: int = 0,
    sprachbausteine_score: Optional[int] = None,
    raw_rubric_scores: Optional[Dict[str, Any]] = None,
    module_results: Optional[Dict[str, Any]] = None,
    weak_points: Optional[List[Any]] = None,
    strengths: Optional[List[Any]] = None,
    recommendations: Optional[List[Any]] = None,
    speaking_profile: Optional[Dict[str, Any]] = None,
    writing_profile: Optional[Dict[str, Any]] = None,
) -> int:
    """Сохранить результат диагностики и обновить профиль обучения"""
    raw_rubric_str = json.dumps(raw_rubric_scores or {}, ensure_ascii=False)
    module_res_str = json.dumps(module_results or {}, ensure_ascii=False)
    weak_pts_str = json.dumps(weak_points or [], ensure_ascii=False)
    strengths_str = json.dumps(strengths or [], ensure_ascii=False)
    recom_str = json.dumps(recommendations or [], ensure_ascii=False)
    speaking_prof_str = json.dumps(speaking_profile or {}, ensure_ascii=False)
    writing_prof_str = json.dumps(writing_profile or {}, ensure_ascii=False)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            INSERT INTO diagnostic_history (
                user_id, exam_type, exam_version, diagnostic_type, cefr_estimate,
                readiness_status, overall_diagnostic_score, lesen_score, hoeren_score,
                schreiben_score, sprechen_score, sprachbausteine_score,
                raw_rubric_scores, module_results_json, weak_points_json,
                strengths_json, recommendations_json, speaking_profile_json,
                writing_profile_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, exam_type, exam_version, diagnostic_type, cefr_estimate,
            readiness_status, overall_diagnostic_score, lesen_score, hoeren_score,
            schreiben_score, sprechen_score, sprachbausteine_score,
            raw_rubric_str, module_res_str, weak_pts_str,
            strengths_str, recom_str, speaking_prof_str,
            writing_prof_str
        )) as cursor:
            diag_id = cursor.lastrowid

        # Обновляем профиль обучения
        await db.execute("""
            INSERT INTO user_learning_profile (
                user_id, target_exam, target_level, estimated_cefr, readiness_status,
                last_diagnostic_id, weaknesses_json, strengths_json, recommendations_json,
                speaking_profile_json, writing_profile_json, last_reassessment_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                target_exam = excluded.target_exam,
                target_level = excluded.target_level,
                estimated_cefr = excluded.estimated_cefr,
                readiness_status = excluded.readiness_status,
                last_diagnostic_id = excluded.last_diagnostic_id,
                weaknesses_json = excluded.weaknesses_json,
                strengths_json = excluded.strengths_json,
                recommendations_json = excluded.recommendations_json,
                speaking_profile_json = excluded.speaking_profile_json,
                writing_profile_json = excluded.writing_profile_json,
                last_reassessment_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
        """, (
            user_id, exam_type, cefr_estimate, cefr_estimate, readiness_status,
            diag_id, weak_pts_str, strengths_str, recom_str,
            speaking_prof_str, writing_prof_str
        ))

        # Обновляем подтвержденный уровень в таблице users
        await db.execute("""
            UPDATE users SET placement_level = ?, placement_score = ? WHERE user_id = ?
        """, (cefr_estimate, overall_diagnostic_score, user_id))

        await db.commit()
        return diag_id

async def get_latest_diagnostic(user_id: int, exam_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Получить самую свежую диагностику пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM diagnostic_history WHERE user_id = ?"
        params = [user_id]
        if exam_type:
            query += " AND exam_type = ?"
            params.append(exam_type)
        query += " ORDER BY id DESC LIMIT 1"

        async with db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            data = dict(row)
            data["raw_rubric_scores"] = json.loads(data["raw_rubric_scores"] or "{}")
            data["module_results"] = json.loads(data["module_results_json"] or "{}")
            data["weak_points"] = json.loads(data["weak_points_json"] or "[]")
            data["strengths"] = json.loads(data["strengths_json"] or "[]")
            data["recommendations"] = json.loads(data["recommendations_json"] or "[]")
            data["speaking_profile"] = json.loads(data["speaking_profile_json"] or "{}")
            data["writing_profile"] = json.loads(data["writing_profile_json"] or "{}")
            return data

async def get_user_diagnostic_history(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """Получить историю диагностик для отслеживания динамики"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, exam_type, exam_version, diagnostic_type, cefr_estimate,
                   readiness_status, overall_diagnostic_score, lesen_score, hoeren_score,
                   schreiben_score, sprechen_score, created_at
            FROM diagnostic_history
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_or_create_learning_profile(user_id: int) -> Dict[str, Any]:
    """Получить или создать профиль обучения пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM user_learning_profile WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                data["weaknesses"] = json.loads(data["weaknesses_json"] or "[]")
                data["strengths"] = json.loads(data["strengths_json"] or "[]")
                data["recommendations"] = json.loads(data["recommendations_json"] or "[]")
                data["speaking_profile"] = json.loads(data["speaking_profile_json"] or "{}")
                data["writing_profile"] = json.loads(data["writing_profile_json"] or "{}")
                return data

        # Создаем профиль по умолчанию
        await db.execute("""
            INSERT INTO user_learning_profile (user_id, target_exam, target_level, estimated_cefr, readiness_status)
            VALUES (?, 'goethe_b1', 'B1', 'A1', 'NOT_READY')
        """, (user_id,))
        await db.commit()
        return {
            "user_id": user_id,
            "target_exam": "goethe_b1",
            "target_level": "B1",
            "exam_date": "",
            "estimated_cefr": "A1",
            "readiness_status": "NOT_READY",
            "last_diagnostic_id": 0,
            "weaknesses": [],
            "strengths": [],
            "recommendations": [],
            "speaking_profile": {},
            "writing_profile": {}
        }

async def update_learning_profile_goals(user_id: int, target_exam: str, target_level: str, exam_date: str = ""):
    """Обновить целевой экзамен и дату сдачи"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE user_learning_profile
            SET target_exam = ?, target_level = ?, exam_date = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (target_exam, target_level, exam_date, user_id))
        await db.commit()

async def export_database_backup(target_path: Optional[str] = None) -> str:
    """Выгружает полноценный SQLite .db файл бэкапа из Turso Cloud или локальной базы"""
    from database.connection import USE_TURSO, TURSO_URL, TURSO_TOKEN
    from pathlib import Path
    import sqlite3
    import shutil

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if not target_path:
        backups_dir = Path(DB_PATH).parent / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        target_path = str(backups_dir / f"stork_backup_{timestamp}.db")

    target_file = Path(target_path)
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if target_file.exists():
        target_file.unlink()

    if USE_TURSO and TURSO_URL and TURSO_TOKEN:
        import libsql_client
        client = libsql_client.create_client(TURSO_URL, auth_token=TURSO_TOKEN)
        dst_conn = sqlite3.connect(str(target_file))
        dst_cur = dst_conn.cursor()

        tables_res = await client.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        for t_row in tables_res.rows:
            t_name = t_row['name']
            t_sql = t_row['sql']
            if not t_sql:
                continue
            dst_cur.execute(t_sql)
            rows_res = await client.execute(f"SELECT * FROM {t_name}")
            if rows_res.rows:
                cols = rows_res.columns
                placeholders = ", ".join(["?"] * len(cols))
                insert_sql = f"INSERT INTO {t_name} VALUES ({placeholders})"
                for r in rows_res.rows:
                    dst_cur.execute(insert_sql, list(r))

        idx_res = await client.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")
        for i_row in idx_res.rows:
            if i_row['sql']:
                try:
                    dst_cur.execute(i_row['sql'])
                except Exception:
                    pass

        dst_conn.commit()
        dst_conn.close()
        await client.close()
        return str(target_file)
    else:
        # Локальный режим
        if Path(DB_PATH).exists():
            shutil.copy2(str(DB_PATH), str(target_file))
            return str(target_file)
        raise FileNotFoundError(f"Файл локальной базы данных {DB_PATH} не найден")




