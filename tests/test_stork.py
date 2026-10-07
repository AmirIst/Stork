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

def test_extract_german_for_voice_new_format():
    ru_reply = """
🪶 Stork:

🇩🇪 Перевод фразы на немецком: Wie viel Uhr ist es?
💡 Полезный разбор: Слово Uhr означает часы или время.
💬 Ответ на сообщение: Es ist jetzt genau fünfzehn Uhr. (Сейчас ровно 15:00.)
❓ Встречный вопрос: Wann hast du Feierabend? (Когда у тебя заканчивается рабочий день?)
"""
    ru_extracted = extract_german_for_voice(ru_reply)
    assert "Wie viel Uhr ist es?" in ru_extracted
    assert "Es ist jetzt genau fünfzehn Uhr." in ru_extracted
    assert "Wann hast du Feierabend?" in ru_extracted
    assert "Полезный разбор" not in ru_extracted
    assert "Сейчас ровно" not in ru_extracted

    en_reply = """
🪶 Stork:

🇩🇪 German translation: Wie viel Uhr ist es?
💡 Useful breakdown: The word Uhr means clock or time.
💬 Reply to your message: Es ist jetzt genau fünfzehn Uhr. (It is 3 pm right now.)
❓ Follow-up question: Wann hast du Feierabend? (When do you finish work?)
"""
    en_extracted = extract_german_for_voice(en_reply)
    assert "Wie viel Uhr ist es?" in en_extracted
    assert "Es ist jetzt genau fünfzehn Uhr." in en_extracted
    assert "Wann hast du Feierabend?" in en_extracted
    assert "Useful breakdown" not in en_extracted
    assert "finish work" not in en_extracted

def test_extract_musterloesung_for_voice():
    from services.tts import extract_musterloesung_for_voice
    sample_review = """
🪶 *Экзаменационная оценка Stork (A1):*

📊 Оценка экзаменатора: 90/100 • Bestanden
📏 Объем текста: 32 слова

🌟 Идеальный образец ответа (Musterlösung):
Lieber Markus, ich lade dich herzlich zu meiner Geburtstagsparty ein. Die Party beginnt am Samstag um 18 Uhr. Ich koche Pasta, aber bring bitte Getränke mit. (Дорогой Маркус, сердечно приглашаю тебя...)

💡 Экзаменационный совет от Stork:
Не забывай про вежливые обращения в начале и в конце письма.
"""
    sample_de = extract_musterloesung_for_voice(sample_review)
    assert "Lieber Markus, ich lade dich herzlich" in sample_de
    assert "Die Party beginnt am Samstag" in sample_de
    assert "Дорогой Маркус" not in sample_de
    assert "Экзаменационный совет" not in sample_de

def test_exam_tasks_structure():
    from services.exam_service import EXAM_TASKS
    assert len(EXAM_TASKS) >= 6
    for t in EXAM_TASKS:
        assert t["id"]
        assert t["level"] in ("A1", "A2", "B1")
        assert "ru" in t["title"] and "en" in t["title"]
        assert "ru" in t["situation"] and "en" in t["situation"]
        assert len(t["points"]["ru"]) >= 3
        assert len(t["points"]["en"]) >= 3
        assert "ru" in t["starter_hint"] and "en" in t["starter_hint"]

def test_locales_exam_keys():
    ru_path = DATA_DIR.parent / "locales" / "ru.json"
    en_path = DATA_DIR.parent / "locales" / "en.json"
    with open(ru_path, "r", encoding="utf-8") as f:
        ru = json.load(f)
    with open(en_path, "r", encoding="utf-8") as f:
        en = json.load(f)

    for key in ["btn_exam_trainer", "exam_welcome", "btn_exam_lvl_a1", "btn_exam_lvl_a2", "btn_exam_lvl_b1", "btn_exam_lvl_random", "btn_exam_new_task", "btn_exam_sample_voice", "btn_exam_next", "exam_evaluating"]:
        assert key in ru, f"Missing key {key} in ru.json"
        assert key in en, f"Missing key {key} in en.json"

@pytest.mark.anyio
async def test_db_random_word_fetch():
    from database import db
    await db.init_db()
    word = await db.get_random_word(lang="ru")
    assert word is not None
    assert word["word"]
    assert word["article"] in ("der", "die", "das")
    assert word["translation"]

def test_ui_helper_flag_lifecycle():
    from services.ui_helper import mark_voice_sent, has_voice_pending, clear_voice_pending
    user_id = 999888
    clear_voice_pending(user_id)
    assert not has_voice_pending(user_id)
    mark_voice_sent(user_id)
    assert has_voice_pending(user_id)
    clear_voice_pending(user_id)
    assert not has_voice_pending(user_id)

@pytest.mark.anyio
async def test_show_or_update_window_repost_behavior():
    from unittest.mock import AsyncMock, MagicMock
    from services.ui_helper import mark_voice_sent, show_or_update_window, has_voice_pending

    user_id = 777666
    cb = MagicMock()
    cb.from_user.id = user_id
    cb.message = MagicMock()
    cb.message.delete = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.message.edit_text = AsyncMock()

    # 1. При наличии отправленного голосового сообщения -> удаляет старое и шлет новое вниз
    mark_voice_sent(user_id)
    assert has_voice_pending(user_id)
    await show_or_update_window(cb, text="Hello bottom", force_repost=False)
    cb.message.delete.assert_called_once()
    cb.message.answer.assert_called_once_with(text="Hello bottom", reply_markup=None, parse_mode="Markdown")
    cb.message.edit_text.assert_not_called()
    assert not has_voice_pending(user_id)

    # 2. При обычном переходе (без голоса) -> быстро редактирует на месте
    cb.message.delete.reset_mock()
    cb.message.answer.reset_mock()
    cb.message.edit_text.reset_mock()

    await show_or_update_window(cb, text="Hello edit", force_repost=False)
    cb.message.edit_text.assert_called_once_with(text="Hello edit", reply_markup=None, parse_mode="Markdown")
    cb.message.delete.assert_not_called()
    cb.message.answer.assert_not_called()

def test_placement_questions_integrity():
    from services.placement_test import PLACEMENT_QUESTIONS
    assert len(PLACEMENT_QUESTIONS) == 12
    for q in PLACEMENT_QUESTIONS:
        assert q["id"]
        assert q["level"] in ("A1", "A2", "B1")
        assert "ru" in q["topic"] and "en" in q["topic"]
        assert q["question"]
        assert len(q["options"]) == 4
        assert 0 <= q["correct_index"] < 4
        assert "ru" in q["explanation"] and "en" in q["explanation"]

def test_placement_evaluation_logic():
    from services.placement_test import evaluate_placement_test, get_level_description
    # 1. Все 12 верных -> B1
    perfect_answers = [0] * 12
    lvl, score, breakdown = evaluate_placement_test(perfect_answers)
    assert lvl == "B1"
    assert score == 12
    assert breakdown["A1"] == (4, 4)
    assert breakdown["A2"] == (4, 4)
    assert breakdown["B1"] == (4, 4)

    # 2. 6 верных -> A2
    mid_answers = [0] * 6 + [1] * 6
    lvl, score, _ = evaluate_placement_test(mid_answers)
    assert lvl == "A2"
    assert score == 6

    # 3. 2 верных -> A1
    low_answers = [0, 0] + [1] * 10
    lvl, score, _ = evaluate_placement_test(low_answers)
    assert lvl == "A1"
    assert score == 2

    # Описания
    desc_ru = get_level_description("A2", lang="ru")
    assert "A2" in desc_ru["name"]
    assert desc_ru["title"]
    assert desc_ru["tip"]

    desc_en = get_level_description("B1", lang="en")
    assert "B1" in desc_en["name"]
    assert desc_en["title"]

def test_locales_placement_keys():
    ru_path = DATA_DIR.parent / "locales" / "ru.json"
    en_path = DATA_DIR.parent / "locales" / "en.json"
    import json
    with open(ru_path, "r", encoding="utf-8") as f:
        ru = json.load(f)
    with open(en_path, "r", encoding="utf-8") as f:
        en = json.load(f)

    for k in ["btn_placement_test", "placement_welcome", "btn_start_placement", "btn_apply_placement_level", "btn_retake_placement", "placement_level_applied"]:
        assert k in ru, f"Missing {k} in ru.json"
        assert k in en, f"Missing {k} in en.json"

def test_locales_premium_and_reminder_keys():
    ru_path = DATA_DIR.parent / "locales" / "ru.json"
    en_path = DATA_DIR.parent / "locales" / "en.json"
    with open(ru_path, "r", encoding="utf-8") as f:
        ru = json.load(f)
    with open(en_path, "r", encoding="utf-8") as f:
        en = json.load(f)

    keys = [
        "btn_premium", "btn_premium_trial", "btn_premium_buy_stars", "btn_premium_promo",
        "btn_toggle_reminders_on", "btn_toggle_reminders_off", "premium_info",
        "premium_trial_activated", "premium_already_active", "promo_prompt",
        "promo_success", "promo_invalid", "ai_quota_exceeded", "exam_quota_exceeded",
        "reminder_text", "btn_quick_train", "reminder_toggled_on", "reminder_toggled_off"
    ]
    for k in keys:
        assert k in ru, f"Missing {k} in ru.json"
        assert k in en, f"Missing {k} in en.json"

@pytest.mark.anyio
async def test_quota_and_premium_logic():
    import random
    from database import db
    await db.init_db()

    test_uid = random.randint(100000000, 999999999)
    # 1. Новый пользователь
    await db.get_or_create_user(test_uid, "test_user", "Tester")

    # Проверка бесплатной квоты ИИ (10)
    allowed, used, limit = await db.check_ai_quota(test_uid)
    assert allowed is True
    assert limit == 10

    # Проверка бесплатной квоты экзамена (3)
    allowed, used, limit = await db.check_exam_quota(test_uid)
    assert allowed is True
    assert limit == 3

    # Исчерпание квоты ИИ
    for _ in range(10):
        await db.increment_ai_quota(test_uid)
    allowed, used, limit = await db.check_ai_quota(test_uid)
    assert allowed is False
    assert used >= 10

    # Активация Premium снимает все лимиты
    exp_date = await db.activate_premium(test_uid, days=7)
    assert exp_date is not None
    is_prem, until = await db.is_user_premium(test_uid)
    assert is_prem is True

    # Теперь ИИ-квота безлимитна (limit == -1)
    allowed_prem, _, limit_prem = await db.check_ai_quota(test_uid)
    assert allowed_prem is True
    assert limit_prem == -1

@pytest.mark.anyio
async def test_daily_streak_and_notification_toggle():
    import random
    from database import db
    await db.init_db()

    test_uid = random.randint(100000000, 999999999)
    await db.get_or_create_user(test_uid, "streak_tester", "StreakUser")

    # Обновление серии занятий
    streak = await db.update_daily_streak(test_uid)
    assert streak >= 1

    # Повторное занятие в тот же день не увеличивает стрик дважды
    streak2 = await db.update_daily_streak(test_uid)
    assert streak2 == streak

    # Переключение уведомлений
    status1 = await db.toggle_user_notifications(test_uid)
    status2 = await db.toggle_user_notifications(test_uid)
    assert status1 != status2

def test_hub_locales_keys():
    ru_path = DATA_DIR.parent / "locales" / "ru.json"
    en_path = DATA_DIR.parent / "locales" / "en.json"
    with open(ru_path, "r", encoding="utf-8") as f:
        ru = json.load(f)
    with open(en_path, "r", encoding="utf-8") as f:
        en = json.load(f)

    keys = [
        "btn_hub_training", "btn_hub_vocab", "btn_hub_exams", "btn_hub_settings",
        "hub_training_title", "hub_vocab_title", "hub_exams_title", "hub_settings_title",
        "btn_smart_review", "btn_verbs_sprint", "btn_exam_sprechen",
        "smart_review_empty"
    ]
    for k in keys:
        assert k in ru, f"Missing key {k} in ru.json"
        assert k in en, f"Missing key {k} in en.json"

def test_verbs_sprint_service():
    from services.verbs_service import GERMAN_VERBS_DATA, generate_verb_sprint_question
    assert len(GERMAN_VERBS_DATA) >= 20
    q = generate_verb_sprint_question(lang="ru")
    assert "prompt" in q
    assert "options" in q
    assert len(q["options"]) == 4
    assert "correct" in q
    assert q["correct"] in q["options"]
    assert "explanation" in q

    q_en = generate_verb_sprint_question(lang="en")
    assert "prompt" in q_en
    assert len(q_en["options"]) == 4
    assert q_en["correct"] in q_en["options"]

def test_sprechen_tasks_and_musterantwort():
    from services.sprechen_service import SPRECHEN_TASKS, get_sprechen_task, extract_sprechen_musterantwort
    assert len(SPRECHEN_TASKS) >= 6
    for t in SPRECHEN_TASKS:
        assert t["level"] in ("A1", "A2", "B1")
        assert "ru" in t["title"] and "en" in t["title"]
        assert "ru" in t["instructions"] and "en" in t["instructions"]
        assert "starter_hint" in t

    task_a1 = get_sprechen_task("A1")
    assert task_a1["level"] == "A1"

    sample_review = """
🎯 **Оценка: 88 / 100 (B1)**

**Разбор:**
Хороший темп речи.

---
🌟 **Musterantwort:**
Guten Tag! Ich möchte gern einen Termin für nächste Woche vereinbaren. Passt es Ihnen am Mittwoch um 10 Uhr? Vielen Dank!
---
"""
    clean_audio_text = extract_sprechen_musterantwort(sample_review)
    assert "Guten Tag! Ich möchte gern einen Termin" in clean_audio_text
    assert "Оценка" not in clean_audio_text

@pytest.mark.anyio
async def test_db_smart_review():
    from database import db
    import random
    await db.init_db()

    test_uid = random.randint(100000000, 999999999)
    await db.get_or_create_user(test_uid, "review_test", "ReviewTester")

    # Изначально список повторения пуст
    count = await db.get_review_words_count(test_uid)
    assert count == 0

    # Добавляем слово со статусом 'learning'
    word = await db.get_random_word(lang="ru")
    assert word is not None
    await db.set_word_status(test_uid, word["id"], "learning")

    count_after = await db.get_review_words_count(test_uid)
    assert count_after == 1

    words_to_rev = await db.get_words_for_review(test_uid, lang="ru", limit=5)
    assert len(words_to_rev) == 1
    assert words_to_rev[0]["id"] == word["id"]

def test_achievements_locales_keys():
    ru_path = DATA_DIR.parent / "locales" / "ru.json"
    en_path = DATA_DIR.parent / "locales" / "en.json"
    with open(ru_path, "r", encoding="utf-8") as f:
        ru = json.load(f)
    with open(en_path, "r", encoding="utf-8") as f:
        en = json.load(f)

    keys = [
        "btn_achievements", "btn_back_to_stats", "achievements_title",
        "achievements_unlocked_header", "achievements_locked_header", "achievement_unlocked_toast"
    ]
    for k in keys:
        assert k in ru, f"Missing key {k} in ru.json"
        assert k in en, f"Missing key {k} in en.json"

def test_achievements_registry_integrity():
    from database.db import ACHIEVEMENTS_REGISTRY
    assert len(ACHIEVEMENTS_REGISTRY) >= 10
    for b_id, meta in ACHIEVEMENTS_REGISTRY.items():
        assert meta["icon"]
        assert "ru" in meta["title"] and "en" in meta["title"]
        assert "ru" in meta["desc"] and "en" in meta["desc"]

@pytest.mark.anyio
async def test_db_achievements_unlock_and_grant():
    from database import db
    import random
    await db.init_db()

    test_uid = random.randint(100000000, 999999999)
    await db.get_or_create_user(test_uid, "achieve_test", "Achiever")

    # 1. Первый шаг выдается автоматически
    newly = await db.check_and_grant_achievements(test_uid)
    assert any(a["id"] == "first_step" for a in newly)

    # 2. Повторная проверка не дублирует ачивки
    newly_again = await db.check_and_grant_achievements(test_uid)
    assert len(newly_again) == 0

    # 3. Ручное открытие
    granted = await db.unlock_achievement(test_uid, "verbs_sprinter")
    assert granted is not None
    assert granted["id"] == "verbs_sprinter"

    # Повторное ручное открытие возвращает None
    granted_dup = await db.unlock_achievement(test_uid, "verbs_sprinter")
    assert granted_dup is None

    # 4. Проверка получения списка
    unlocked = await db.get_user_unlocked_achievements(test_uid)
    unlocked_ids = [a["id"] for a in unlocked]
    assert "first_step" in unlocked_ids
    assert "verbs_sprinter" in unlocked_ids

def test_listening_tasks_integrity():
    from services.listening_service import LISTENING_TASKS, get_listening_task
    assert len(LISTENING_TASKS) >= 8
    for t in LISTENING_TASKS:
        assert t["id"]
        assert t["level"] in ("A1", "A2", "B1")
        assert len(t["audio_text"]) > 20
        assert "ru" in t["question"] and "en" in t["question"]
        assert len(t["options"]["ru"]) == 4 and len(t["options"]["en"]) == 4
        assert t["correct_index"] in (0, 1, 2, 3)
        assert "ru" in t["explanation"] and "en" in t["explanation"]
        assert "ru" in t["transcript_tr"] and "en" in t["transcript_tr"]

    task_a1 = get_listening_task("A1")
    assert task_a1["level"] == "A1"

    task_b1 = get_listening_task("B1")
    assert task_b1["level"] == "B1"

    task_by_id = get_listening_task(task_id="hv_a1_1")
    assert task_by_id["id"] == "hv_a1_1"

def test_locales_listening_keys():
    ru_path = DATA_DIR.parent / "locales" / "ru.json"
    en_path = DATA_DIR.parent / "locales" / "en.json"
    with open(ru_path, "r", encoding="utf-8") as f:
        ru = json.load(f)
    with open(en_path, "r", encoding="utf-8") as f:
        en = json.load(f)

    keys = [
        "btn_exam_listening", "listening_welcome", "listening_listen_prompt",
        "listening_correct", "listening_wrong", "listening_transcript_header",
        "btn_listening_next"
    ]
    for k in keys:
        assert k in ru, f"Missing key {k} in ru.json"
        assert k in en, f"Missing key {k} in en.json"

def test_roleplay_scenarios_integrity():
    from services.roleplay_service import ROLEPLAY_SCENARIOS, get_roleplay_scenario
    assert len(ROLEPLAY_SCENARIOS) >= 5
    for s in ROLEPLAY_SCENARIOS:
        assert s["id"]
        assert s["level"] in ("A1", "A2", "B1")
        assert s["icon"]
        assert "ru" in s["title"] and "en" in s["title"]
        assert "ru" in s["character"] and "en" in s["character"]
        assert "ru" in s["goal"] and "en" in s["goal"]
        assert len(s["starter_de"]) > 10
        assert "ru" in s["starter_tr"] and "en" in s["starter_tr"]
        assert len(s["hints"]["ru"]) >= 2

    cafe = get_roleplay_scenario("cafe_a1")
    assert cafe is not None
    assert cafe["level"] == "A1"

    hotel = get_roleplay_scenario("hotel_b1")
    assert hotel is not None
    assert hotel["level"] == "B1"

def test_locales_roleplay_keys():
    ru_path = DATA_DIR.parent / "locales" / "ru.json"
    en_path = DATA_DIR.parent / "locales" / "en.json"
    with open(ru_path, "r", encoding="utf-8") as f:
        ru = json.load(f)
    with open(en_path, "r", encoding="utf-8") as f:
        en = json.load(f)

    keys = [
        "btn_roleplay", "roleplay_welcome", "btn_rp_hint",
        "btn_rp_voice", "btn_rp_finish", "btn_rp_next"
    ]
    for k in keys:
        assert k in ru, f"Missing key {k} in ru.json"
        assert k in en, f"Missing key {k} in en.json"

    from database.db import ACHIEVEMENTS_REGISTRY
    assert "roleplay_master" in ACHIEVEMENTS_REGISTRY

def test_premium_config_integrity():
    from premium_config import (
        FREE_TRIAL_DAYS,
        PROMO_CODES,
        PREMIUM_PLANS,
        REFERRAL_CONFIG,
        get_promo_info,
        get_plan_by_id,
        get_plan_price,
    )
    assert FREE_TRIAL_DAYS == 7
    assert len(PROMO_CODES) >= 5
    for code, data in PROMO_CODES.items():
        assert "days" in data and data["days"] > 0
        assert "description" in data

    assert len(PREMIUM_PLANS) >= 3
    plan_ids = [p["id"] for p in PREMIUM_PLANS]
    assert "plan_1d" in plan_ids
    assert "plan_10d" in plan_ids
    assert "plan_30d" in plan_ids

    # Проверка расчета цен и скидки
    monthly_plan = get_plan_by_id("plan_30d")
    assert monthly_plan is not None
    assert monthly_plan["is_monthly"] is True
    regular_price = get_plan_price(monthly_plan, has_discount=False)
    assert regular_price == 150
    discounted_price = get_plan_price(monthly_plan, has_discount=True)
    assert discounted_price == 75 # 50% скидка

    # План на 1 день не получает скидку
    daily_plan = get_plan_by_id("plan_1d")
    assert get_plan_price(daily_plan, has_discount=True) == daily_plan["stars"]

    # Проверка реферального конфига
    assert REFERRAL_CONFIG["days_per_invite"] == 1
    assert REFERRAL_CONFIG["milestone_invites"] == 10
    assert REFERRAL_CONFIG["milestone_bonus_days"] == 5
    assert REFERRAL_CONFIG["milestone_discount_percent"] == 50

@pytest.mark.anyio
async def test_trial_one_time_enforcement():
    import aiosqlite
    from database import db
    await db.init_db()

    test_uid = 999111001
    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute("DELETE FROM users WHERE user_id = ?", (test_uid,))
        await conn.commit()

    await db.get_or_create_user(test_uid, "trial_user", "Tester")

    # Проверяем доступность до активации
    assert await db.is_trial_available(test_uid) is True

    # Первая активация
    ok, status, until = await db.activate_trial_if_eligible(test_uid, days=7)
    assert ok is True
    assert status == "success"
    assert until is not None

    # Теперь триал недоступен
    assert await db.is_trial_available(test_uid) is False

    # Вторая активация должна быть заблокирована
    ok2, status2, _ = await db.activate_trial_if_eligible(test_uid, days=7)
    assert ok2 is False
    assert status2 == "already_used"

@pytest.mark.anyio
async def test_promo_code_one_time_per_user():
    import aiosqlite
    from database import db
    await db.init_db()

    test_uid = 999222002
    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute("DELETE FROM users WHERE user_id = ?", (test_uid,))
        await conn.execute("DELETE FROM user_promo_activations WHERE user_id = ?", (test_uid,))
        await conn.commit()

    await db.get_or_create_user(test_uid, "promo_user", "Tester")

    # 1. Неверный промокод
    ok, status, days, _ = await db.activate_promo_code(test_uid, "INVALID_CODE_XYZ")
    assert ok is False
    assert status == "invalid_code"

    # 2. Успешная активация валидного промокода
    ok, status, days, until = await db.activate_promo_code(test_uid, "storkvip")
    assert ok is True
    assert status == "success"
    assert days == 30
    assert until is not None

    # 3. Повторная активация того же промокода должна быть отклонена
    ok_dup, status_dup, _, _ = await db.activate_promo_code(test_uid, "STORKVIP")
    assert ok_dup is False
    assert status_dup == "already_used"

@pytest.mark.anyio
async def test_referral_system_and_milestones():
    import aiosqlite
    from database import db
    await db.init_db()

    inviter_id = 999333000
    ref_uids = [999333000 + i for i in range(12)]
    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute(f"DELETE FROM users WHERE user_id IN ({','.join(map(str, ref_uids))})")
        await conn.execute(f"DELETE FROM referrals WHERE inviter_id = {inviter_id} OR referred_id IN ({','.join(map(str, ref_uids))})")
        await conn.commit()

    await db.get_or_create_user(inviter_id, "inviter", "Inviter")

    # Самореферал запрещен
    self_res = await db.register_referral(inviter_id, inviter_id)
    assert self_res is None

    # Регистрируем 9 рефералов
    for i in range(1, 10):
        ref_uid = 999333000 + i
        await db.get_or_create_user(ref_uid, f"ref_{i}", f"Ref{i}")
        res = await db.register_referral(inviter_id, ref_uid)
        assert res is not None
        assert res["success"] is True
        assert res["total_referrals"] == i
        assert res["milestone_hit"] is False
        assert res["days_granted"] == 1

    stats_9 = await db.get_referral_stats(inviter_id)
    assert stats_9["count"] == 9
    assert stats_9["days_earned"] == 9
    assert stats_9["milestone_reached"] is False
    assert stats_9["has_discount"] is False

    # 10-й реферал -> срабатывает супер-бонус (+5 дней, итого 15 дней суммарно!)
    tenth_uid = 999333010
    await db.get_or_create_user(tenth_uid, "ref_10", "Ref10")
    res_10 = await db.register_referral(inviter_id, tenth_uid)
    assert res_10 is not None
    assert res_10["total_referrals"] == 10
    assert res_10["milestone_hit"] is True
    assert res_10["days_granted"] == 6 # 1 базовый + 5 бонусных

    stats_10 = await db.get_referral_stats(inviter_id)
    assert stats_10["count"] == 10
    assert stats_10["days_earned"] == 15 # 10 * 1 + 5 = 15 дней ровно как в ТЗ!
    assert stats_10["milestone_reached"] is True
    assert stats_10["has_discount"] is True
    assert stats_10["discount_percent"] == 50

    # Повторная регистрация того же реферала отклоняется
    dup_res = await db.register_referral(inviter_id, tenth_uid)
    assert dup_res is None

def test_promo_prompt_no_example_leak():
    ru_path = DATA_DIR.parent / "locales" / "ru.json"
    en_path = DATA_DIR.parent / "locales" / "en.json"
    with open(ru_path, "r", encoding="utf-8") as f:
        ru = json.load(f)
    with open(en_path, "r", encoding="utf-8") as f:
        en = json.load(f)

    # Проверяем, что в подсказках ввода промокода нет утечки реального промокода
    assert "STORKVIP" not in ru["promo_prompt"], "STORKVIP is leaked in ru.json promo_prompt!"
    assert "STORKVIP" not in en["promo_prompt"], "STORKVIP is leaked in en.json promo_prompt!"

@pytest.mark.anyio
async def test_lifetime_vip_config_and_db():
    import aiosqlite
    from database import db
    from premium_config import is_lifetime_vip_in_config
    await db.init_db()

    # 1. Проверка через конфиг
    test_cfg_uid = 6725392176
    assert is_lifetime_vip_in_config(test_cfg_uid) is True
    assert is_lifetime_vip_in_config(999999999, "Amirist1") is True
    assert is_lifetime_vip_in_config(999999999, "random_stranger") is False

    is_prem, until = await db.is_user_premium(test_cfg_uid)
    assert is_prem is True
    assert until == "lifetime"

    # 2. Проверка через базу данных (выдача и отзыв)
    test_db_uid = 999444001
    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute("DELETE FROM users WHERE user_id = ?", (test_db_uid,))
        await conn.commit()

    await db.get_or_create_user(test_db_uid, "friend_user", "Friend")

    # Изначально не премиум
    is_p_init, _ = await db.is_user_premium(test_db_uid)
    assert is_p_init is False

    # Выдаем пожизненный VIP
    ok_grant, status_g, udata_g = await db.set_user_lifetime_vip(test_db_uid, is_vip=True)
    assert ok_grant is True
    assert status_g == "success"

    is_p_grant, until_g = await db.is_user_premium(test_db_uid)
    assert is_p_grant is True
    assert until_g == "lifetime"

    # Проверяем отображение в статистике
    stats = await db.get_user_stats(test_db_uid)
    assert stats["is_premium"] is True
    assert stats["premium_until"] == "lifetime"
    assert stats["daily_ai_limit"] == -1
    assert stats["daily_exam_limit"] == -1

    # Отзываем пожизненный VIP
    ok_revoke, status_r, _ = await db.set_user_lifetime_vip(test_db_uid, is_vip=False)
    assert ok_revoke is True
    assert status_r == "success"

    is_p_revoked, _ = await db.is_user_premium(test_db_uid)
    assert is_p_revoked is False






