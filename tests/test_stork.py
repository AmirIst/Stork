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

def test_roleplay_bilingual_intro_and_localization():
    """Проверка разделения языков в карточке ролевой игры: английский без русских слов и наоборот"""
    from services.roleplay_service import get_roleplay_scenario

    scenario = get_roleplay_scenario("buergeramt_b1")
    assert scenario is not None

    # Английская локализация
    lang_en = "en"
    char_en = scenario["character"].get(lang_en)
    title_en = scenario["title"].get(lang_en)
    goal_en = scenario["goal"].get(lang_en)
    starter_tr_en = scenario["starter_tr"].get(lang_en)

    intro_en = (
        f"🎭 *Scenario:* {scenario['icon']} {title_en}\n"
        f"👤 *Conversation Partner:* {char_en}\n"
        f"🎯 *Goal:* {goal_en}\n\n"
        f"────────────────────\n"
        f"🇩🇪 *{char_en}:*\n"
        f"«{scenario['starter_de']}»\n\n"
        f"💬 _{starter_tr_en}_\n"
        f"────────────────────\n\n"
        f"👉 _Reply in German by text or voice message right now!_"
    )
    # Проверяем, что в английском тексте нет русских служебных меток
    assert "Сценарий" not in intro_en
    assert "Собеседник" not in intro_en
    assert "Цель" not in intro_en
    assert "Напиши ответ" not in intro_en
    assert "Scenario:" in intro_en
    assert "Conversation Partner:" in intro_en
    assert "Goal:" in intro_en

    # Русская локализация
    lang_ru = "ru"
    char_ru = scenario["character"].get(lang_ru)
    title_ru = scenario["title"].get(lang_ru)
    goal_ru = scenario["goal"].get(lang_ru)
    starter_tr_ru = scenario["starter_tr"].get(lang_ru)

    intro_ru = (
        f"🎭 *Сценарий:* {scenario['icon']} {title_ru}\n"
        f"👤 *Собеседник:* {char_ru}\n"
        f"🎯 *Цель:* {goal_ru}\n\n"
        f"────────────────────\n"
        f"🇩🇪 *{char_ru}:*\n"
        f"«{scenario['starter_de']}»\n\n"
        f"💬 _{starter_tr_ru}_\n"
        f"────────────────────\n\n"
        f"👉 _Напиши ответ на немецком или надиктуй голосовое сообщение прямо сейчас!_"
    )
    assert "Сценарий:" in intro_ru
    assert "Собеседник:" in intro_ru
    assert "Цель:" in intro_ru
    assert "Scenario:" not in intro_ru


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

@pytest.mark.anyio
async def test_onboarding_language_flow():
    """Тест первичного онбординга с выбором языка и фото/интро"""
    from unittest.mock import AsyncMock, MagicMock
    from keyboards.inline import get_onboarding_language_keyboard
    from handlers.common import cmd_start, cb_onboarding_lang
    from database import db
    import aiosqlite

    # 1. Проверяем клавиатуру онбординга
    kb = get_onboarding_language_keyboard()
    callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "onboarding_lang:en" in callbacks
    assert "onboarding_lang:ru" in callbacks

    # 2. Создаем нового пользователя
    test_user_id = 888777123
    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute("DELETE FROM users WHERE user_id = ?", (test_user_id,))
        await conn.commit()

    u = await db.get_or_create_user(test_user_id, "onboard_tester", "Alex")
    assert u.get("lang_selected") == 0

    # 3. Запуск /start для нового пользователя -> должен показать интро и выбор языка
    msg = MagicMock()
    msg.from_user.id = test_user_id
    msg.from_user.username = "onboard_tester"
    msg.from_user.first_name = "Alex"
    msg.text = "/start"
    msg.bot = MagicMock()
    msg.answer_photo = AsyncMock()
    msg.answer = AsyncMock()
    state = AsyncMock()

    await cmd_start(msg, state)

    # Проверяем, что отправлено приветствие с выбором языка (фото или текст)
    if msg.answer_photo.called:
        args, kwargs = msg.answer_photo.call_args
        caption = kwargs.get("caption", "")
        reply_kb = kwargs.get("reply_markup")
    else:
        assert msg.answer.called
        args, kwargs = msg.answer.call_args
        caption = kwargs.get("text", "")
        reply_kb = kwargs.get("reply_markup")

    assert "Welcome to Stork!" in caption
    assert "Добро пожаловать в Stork!" in caption
    assert "Please select your language" in caption
    onboard_callbacks = [btn.callback_data for row in reply_kb.inline_keyboard for btn in row]
    assert "onboarding_lang:en" in onboard_callbacks

    # 4. Пользователь выбирает English
    cb = MagicMock()
    cb.from_user.id = test_user_id
    cb.from_user.first_name = "Alex"
    cb.data = "onboarding_lang:en"
    cb.message = MagicMock()
    cb.message.photo = [MagicMock()] # имитируем сообщение с фото
    cb.message.edit_caption = AsyncMock()
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.answer = AsyncMock()

    await cb_onboarding_lang(cb, state)

    # Проверяем, что язык сохранился
    lang_after = await db.get_user_lang(test_user_id)
    assert lang_after == "en"

    # Проверяем, что отредактирован caption с предложением пройти тест
    cb.message.edit_caption.assert_called_once()
    caption_call = cb.message.edit_caption.call_args[1]["caption"]
    assert "Welcome, Alex! I am Stork" in caption_call
    onboard_reply_kb = cb.message.edit_caption.call_args[1]["reply_markup"]
    btn_callbacks = [btn.callback_data for row in onboard_reply_kb.inline_keyboard for btn in row]
    assert "placement_start" in btn_callbacks
    assert "back_to_menu" in btn_callbacks
    cb.answer.assert_called_once()

    # 5. Повторный вызов /start для вернувшегося пользователя
    msg.answer_photo.reset_mock()
    msg.answer.reset_mock()
    await cmd_start(msg, state)

    # Уже не должен показывать интро с выбором языка, а сразу выдать главное меню на English
    msg.answer_photo.assert_not_called()
    msg.answer.assert_called_once()
    returning_text = msg.answer.call_args[1].get("text") if "text" in msg.answer.call_args[1] else msg.answer.call_args[0][0]
    assert "Hello, Alex! I am Stork" in returning_text

def test_placement_pool_and_session():
    """Тест пула из 60 вопросов и генерации случайной сессии из 20 вопросов"""
    from services.placement_test import PLACEMENT_QUESTION_POOL, generate_placement_session, get_question_by_id

    # 1. Проверяем пул из 60 вопросов
    assert len(PLACEMENT_QUESTION_POOL) == 60
    a1_qs = [q for q in PLACEMENT_QUESTION_POOL if q["level"] == "A1"]
    a2_qs = [q for q in PLACEMENT_QUESTION_POOL if q["level"] == "A2"]
    b1_qs = [q for q in PLACEMENT_QUESTION_POOL if q["level"] == "B1"]
    assert len(a1_qs) == 20
    assert len(a2_qs) == 20
    assert len(b1_qs) == 20

    # 2. Генерируем 20 вопросов для сессии
    session = generate_placement_session(count=20, a1_count=7, a2_count=7, b1_count=6)
    assert len(session) == 20
    unique_ids = {q["id"] for q in session}
    assert len(unique_ids) == 20  # Все вопросы в рамках сессии уникальны!

    # Проверяем структуру: 7 A1, затем 7 A2, затем 6 B1
    assert [q["level"] for q in session[:7]] == ["A1"] * 7
    assert [q["level"] for q in session[7:14]] == ["A2"] * 7
    assert [q["level"] for q in session[14:]] == ["B1"] * 6

    # 3. Проверяем get_question_by_id
    q1 = get_question_by_id(1)
    assert q1["id"] == 1
    assert q1["level"] == "A1"

def test_evaluate_20_question_placement():
    """Тест оценки уровня для расширенной сессии из 20 вопросов"""
    from services.placement_test import generate_placement_session, evaluate_placement_test

    session = generate_placement_session(count=20)
    session_q_ids = [q["id"] for q in session]

    # Идеальный результат (20 из 20) -> B1
    perfect_answers = [q["correct_index"] for q in session]
    lvl, score, breakdown = evaluate_placement_test(perfect_answers, question_ids=session_q_ids)
    assert lvl == "B1"
    assert score == 20
    assert breakdown["A1"] == (7, 7)
    assert breakdown["A2"] == (7, 7)
    assert breakdown["B1"] == (6, 6)

    # 12 правильных ответов (60%) -> A2
    mid_answers = [session[i]["correct_index"] if i < 12 else (session[i]["correct_index"] + 1) % 4 for i in range(20)]
    lvl_mid, score_mid, _ = evaluate_placement_test(mid_answers, question_ids=session_q_ids)
    assert lvl_mid == "A2"
    assert score_mid == 12

    # 5 правильных ответов (25%) -> A1
    low_answers = [session[i]["correct_index"] if i < 5 else (session[i]["correct_index"] + 1) % 4 for i in range(20)]
    lvl_low, score_low, _ = evaluate_placement_test(low_answers, question_ids=session_q_ids)
    assert lvl_low == "A1"
    assert score_low == 5

def test_compress_chat_turn_for_context():
    """Тест сжатия истории диалога для оптимизации токенов и ускорения ответа"""
    from services.ai_tutor import compress_chat_turn_for_context

    # 1. Длинный ответ модели с грамматическими разборами и заголовками
    long_model_reply = """
🇩🇪 Перевод фразы на немецком: Guten Morgen, wie geht es dir?
💡 Полезный разбор: Слово Morgen с большой буквы, это существительное мужского рода der Morgen.
💬 Ответ на сообщение: Mir geht es blendend, danke der Nachfrage! (У меня все отлично, спасибо что спросил!)
❓ Встречный вопрос: Was hast du heute Schönes vor? (Что у тебя сегодня хорошего в планах?)
"""
    compressed = compress_chat_turn_for_context(long_model_reply, role="model")
    assert "🇩🇪" in compressed
    assert "💬" in compressed
    assert "❓" in compressed
    # Проверяем, что избыточный разбор отсечен для экономии контекста
    assert "Полезный разбор" not in compressed

    # 2. Длинное сообщение пользователя
    very_long_user_msg = "Привет Аист! " * 50
    user_compressed = compress_chat_turn_for_context(very_long_user_msg, role="user")
    assert len(user_compressed) <= 250

def test_placement_share_certificate_keyboard():
    """Тест генерации кнопки поделиться сертификатом с реферальной ссылкой"""
    from keyboards.inline import get_placement_result_keyboard

    ref_link = "https://t.me/stork_bot?start=ref_999111"

    # Русская локаль
    kb_ru = get_placement_result_keyboard(level="A2", score=16, total=20, referral_link=ref_link, lang="ru")
    first_btn = kb_ru.inline_keyboard[0][0]
    assert "Поделиться" in first_btn.text
    assert first_btn.url is not None
    assert "t.me/share/url" in first_btn.url
    assert "ref_999111" in first_btn.url
    assert "A2" in first_btn.url

    # Английская локаль
    kb_en = get_placement_result_keyboard(level="B1", score=19, total=20, referral_link=ref_link, lang="en")
    first_btn_en = kb_en.inline_keyboard[0][0]
    assert "Share Certificate" in first_btn_en.text
    assert first_btn_en.url is not None
    assert "B1" in first_btn_en.url


def test_tribute_config_and_keyboard():
    """Тест работы конфигурации Tribute и отображения кнопок оплаты картой"""
    import premium_config
    from keyboards.inline import get_premium_plans_keyboard

    # 1. По умолчанию ссылки None, кнопки не отображаются (только Stars и навигация)
    premium_config.TRIBUTE_CONFIG["plan_10d_url"] = None
    premium_config.TRIBUTE_CONFIG["plan_30d_url"] = None
    premium_config.TRIBUTE_CONFIG["plan_30d_discount_url"] = None

    kb = get_premium_plans_keyboard(lang="ru")
    all_texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert not any("картой" in t.lower() for t in all_texts)

    # 2. Устанавливаем тестовые ссылки Tribute
    premium_config.TRIBUTE_CONFIG["plan_10d_url"] = "https://t.me/tribute/app?startapp=p10d"
    premium_config.TRIBUTE_CONFIG["plan_30d_url"] = "https://t.me/tribute/app?startapp=p30d"
    premium_config.TRIBUTE_CONFIG["plan_30d_discount_url"] = "https://t.me/tribute/app?startapp=p30d_sale"

    # Обычный пользователь (без скидки)
    kb_with_cards = get_premium_plans_keyboard(lang="ru", has_discount=False)
    card_buttons = [btn for row in kb_with_cards.inline_keyboard for btn in row if "картой" in btn.text.lower()]
    assert len(card_buttons) == 2
    assert card_buttons[0].url == "https://t.me/tribute/app?startapp=p10d"
    assert card_buttons[1].url == "https://t.me/tribute/app?startapp=p30d"

    # Пользователь со скидкой 50%
    kb_discount = get_premium_plans_keyboard(lang="ru", has_discount=True)
    card_buttons_disc = [btn for row in kb_discount.inline_keyboard for btn in row if "картой" in btn.text.lower()]
    assert len(card_buttons_disc) == 2
    assert card_buttons_disc[1].url == "https://t.me/tribute/app?startapp=p30d_sale"
    assert "-50%" in card_buttons_disc[1].text

    # Английская локаль
    kb_en = get_premium_plans_keyboard(lang="en", has_discount=False)
    card_buttons_en = [btn for row in kb_en.inline_keyboard for btn in row if "card" in btn.text.lower()]
    assert len(card_buttons_en) == 2

    # Очищаем обратно на None
    premium_config.TRIBUTE_CONFIG["plan_10d_url"] = None
    premium_config.TRIBUTE_CONFIG["plan_30d_url"] = None
    premium_config.TRIBUTE_CONFIG["plan_30d_discount_url"] = None

@pytest.mark.anyio
async def test_db_user_cache_and_pragmas():
    """Тест оперативного in-memory кэширования языка и фильтров, а также PRAGMA SQLite"""
    from database import db
    import aiosqlite
    from config import DB_PATH

    # Инициализация БД для применения PRAGMA и индексов
    await db.init_db()

    # Сброс кэша
    db.clear_user_cache()

    # Проверка работы кэша языка
    test_uid = 999888777
    await db.update_user_lang(test_uid, "en")
    assert db._USER_LANG_CACHE.get(test_uid) == "en"

    # get_user_lang возвращает значение из кэша мгновенно
    lang = await db.get_user_lang(test_uid)
    assert lang == "en"

    # Проверка работы кэша фильтров
    await db.set_user_level(test_uid, "B1")
    await db.set_user_category(test_uid, "food")
    lvl, cat = await db.get_user_filters(test_uid)
    assert lvl == "B1"
    assert cat == "food"
    assert db._USER_FILTERS_CACHE.get(test_uid) == ("B1", "food")

    # Проверка WAL-режима SQLite
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("PRAGMA journal_mode;") as cursor:
            row = await cursor.fetchone()
            assert row[0].lower() == "wal"

        # Проверка наличия оптимизирующих индексов
        async with conn.execute("SELECT name FROM sqlite_master WHERE type='index';") as cursor:
            indexes = [r[0] for r in await cursor.fetchall()]
            assert "idx_words_level_cat" in indexes
            assert "idx_progress_user_status_rev" in indexes
            assert "idx_translations_lang" in indexes








