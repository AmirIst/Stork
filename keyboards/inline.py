import urllib.parse
from typing import List, Dict, Any, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from locales.manager import i18n
from database.words_data import CATEGORY_METADATA
from premium_config import PREMIUM_PLANS, get_plan_price, REFERRAL_CONFIG

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора языка"""
    languages = i18n.get_available_languages()
    buttons = []
    for code, info in languages.items():
        text = f"{info['flag']} {info['name']}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"set_lang:{code}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_onboarding_language_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура первого выбора языка при онбординге нового пользователя"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="onboarding_lang:en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="onboarding_lang:ru")
        ]
    ])

def get_onboarding_welcome_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура после выбора языка: предложить пройти тест или войти в главное меню"""
    test_btn = "🎓 Пройти тест на уровень (~2 мин)" if lang == "ru" else "🎓 Take Level Test (~2 min)"
    menu_btn = i18n.get("btn_main_menu", lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=test_btn, callback_data="placement_start")],
        [InlineKeyboardButton(text=menu_btn, callback_data="back_to_menu")]
    ])

def get_main_menu_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Главное меню бота Stork: компактное, интуитивное и удобное"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=i18n.get("btn_hub_training", lang), callback_data="hub_training"),
            InlineKeyboardButton(text=i18n.get("btn_hub_vocab", lang), callback_data="hub_vocab")
        ],
        [
            InlineKeyboardButton(text=i18n.get("btn_hub_exams", lang), callback_data="hub_exams"),
            InlineKeyboardButton(text=i18n.get("btn_ai_tutor", lang), callback_data="menu_ai")
        ],
        [
            InlineKeyboardButton(text=i18n.get("btn_stats", lang), callback_data="menu_stats"),
            InlineKeyboardButton(text=i18n.get("btn_premium", lang), callback_data="menu_premium")
        ],
        [
            InlineKeyboardButton(text=i18n.get("btn_hub_settings", lang), callback_data="hub_settings")
        ]
    ])

def get_training_hub_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Подменю: Тренировка и практика"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_articles", lang), callback_data="menu_articles")],
        [InlineKeyboardButton(text=i18n.get("btn_verbs_sprint", lang), callback_data="menu_verbs_sprint")],
        [InlineKeyboardButton(text=i18n.get("btn_roleplay", lang), callback_data="menu_roleplay")],
        [InlineKeyboardButton(text=i18n.get("btn_quiz", lang), callback_data="menu_quiz")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_vocab_hub_keyboard(lang: str = "ru", review_count: int = 0, level: str = "ALL", category: str = "ALL") -> InlineKeyboardMarkup:
    """Подменю: Словарь, карточки и умное повторение"""
    level_label = "Все уровни" if level == "ALL" else level
    if lang != "ru" and level == "ALL":
        level_label = "All levels"
        
    cat_label = "Все темы" if category == "ALL" else CATEGORY_METADATA.get(category, {}).get(lang, category)
    if lang != "ru" and category == "ALL":
        cat_label = "All topics"

    if lang == "ru":
        topics_btn_text = f"🎯 Темы и сложность: {level_label} • {cat_label}"
        review_btn_text = f"🔄 Умное повторение ({review_count})" if review_count > 0 else "🔄 Умное повторение слов"
    else:
        topics_btn_text = f"🎯 Level & Topics: {level_label} • {cat_label}"
        review_btn_text = f"🔄 Smart Review ({review_count})" if review_count > 0 else "🔄 Smart Vocabulary Review"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_cards", lang), callback_data="menu_cards")],
        [InlineKeyboardButton(text=review_btn_text, callback_data="menu_smart_review")],
        [InlineKeyboardButton(text=topics_btn_text, callback_data="open_filters")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_exams_hub_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Подменю: Экзамены и сертификация"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_exam_trainer", lang), callback_data="menu_exam")],
        [InlineKeyboardButton(text=i18n.get("btn_exam_sprechen", lang), callback_data="menu_sprechen")],
        [InlineKeyboardButton(text=i18n.get("btn_exam_listening", lang), callback_data="menu_listening")],
        [InlineKeyboardButton(text=i18n.get("btn_placement_test", lang), callback_data="menu_placement")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_settings_hub_keyboard(lang: str = "ru", notifications_enabled: bool = True) -> InlineKeyboardMarkup:
    """Подменю: Настройки"""
    notif_btn_text = i18n.get("btn_toggle_reminders_on" if notifications_enabled else "btn_toggle_reminders_off", lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_settings", lang), callback_data="menu_lang")],
        [InlineKeyboardButton(text=notif_btn_text, callback_data="toggle_notif")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_filters_keyboard(current_level: str, current_category: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Меню настройки тем и сложности"""
    level_label = "Все уровни" if current_level == "ALL" else current_level
    if lang != "ru" and current_level == "ALL":
        level_label = "All levels"

    cat_label = "Все темы" if current_category == "ALL" else CATEGORY_METADATA.get(current_category, {}).get(lang, current_category)
    if lang != "ru" and current_category == "ALL":
        cat_label = "All topics"

    btn_lvl_text = f"📶 Сложность: [{level_label}]" if lang == "ru" else f"📶 Level: [{level_label}]"
    btn_cat_text = f"📂 Тема: [{cat_label}]" if lang == "ru" else f"📂 Topic: [{cat_label}]"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_lvl_text, callback_data="choose_level")],
        [InlineKeyboardButton(text=btn_cat_text, callback_data="choose_category")],
        [InlineKeyboardButton(text="🔄 Сбросить выбор (Все слова)" if lang == "ru" else "🔄 Reset to all words", callback_data="reset_filters")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_level_selection_keyboard(current_level: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура выбора уровня сложности (A1, A2, B1, ALL)"""
    levels = [
        ("ALL", "🌟 Все уровни" if lang == "ru" else "🌟 All levels"),
        ("A1", "A1 (Начальный)" if lang == "ru" else "A1 (Beginner)"),
        ("A2", "A2 (Элементарный)" if lang == "ru" else "A2 (Elementary)"),
        ("B1", "B1 (Средний)" if lang == "ru" else "B1 (Intermediate)")
    ]

    buttons = []
    for code, label in levels:
        mark = " ✅" if code == current_level else ""
        buttons.append([InlineKeyboardButton(text=f"{label}{mark}", callback_data=f"set_lvl:{code}")])

    back_text = "⬅️ Назад к темам" if lang == "ru" else "⬅️ Back"
    buttons.append([InlineKeyboardButton(text=back_text, callback_data="open_filters")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_category_selection_keyboard(current_category: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура выбора категории слов"""
    buttons = []
    
    all_label = "🌟 Все темы (Все слова)" if lang == "ru" else "🌟 All Topics"
    all_mark = " ✅" if current_category == "ALL" else ""
    buttons.append([InlineKeyboardButton(text=f"{all_label}{all_mark}", callback_data="set_cat:ALL")])

    row = []
    for cat_key, meta in CATEGORY_METADATA.items():
        title = meta.get(lang, cat_key)
        mark = " ✅" if cat_key == current_category else ""
        btn = InlineKeyboardButton(text=f"{title}{mark}", callback_data=f"set_cat:{cat_key}")
        row.append(btn)
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    back_text = "⬅️ Назад к темам" if lang == "ru" else "⬅️ Back"
    buttons.append([InlineKeyboardButton(text=back_text, callback_data="open_filters")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_article_keyboard(word_id: int, lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопки выбора артикля: der, die, das"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔵 der", callback_data=f"art:{word_id}:der"),
            InlineKeyboardButton(text="🔴 die", callback_data=f"art:{word_id}:die"),
            InlineKeyboardButton(text="🟢 das", callback_data=f"art:{word_id}:das")
        ],
        [
            InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")
        ]
    ])

def get_next_article_keyboard(word_id: Optional[int] = None, lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопка перехода к следующему слову в тренажере артиклей с озвучкой"""
    buttons = []
    row = [InlineKeyboardButton(text=i18n.get("btn_next", lang), callback_data="next_article")]
    if word_id:
        voice_text = "🔊 Озвучить" if lang == "ru" else "🔊 Listen"
        row.append(InlineKeyboardButton(text=voice_text, callback_data=f"voice_word:{word_id}"))
    buttons.append(row)
    buttons.append([InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_card_keyboard(word_id: int, lang: str = "ru", is_revealed: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура карточки слов в стиле Anki с озвучкой"""
    buttons = []
    voice_text = "🔊 Озвучить" if lang == "ru" else "🔊 Listen"
    if not is_revealed:
        buttons.append([
            InlineKeyboardButton(text=i18n.get("btn_reveal", lang), callback_data=f"card_rev:{word_id}"),
            InlineKeyboardButton(text=voice_text, callback_data=f"voice_word:{word_id}")
        ])
        buttons.append([InlineKeyboardButton(text=i18n.get("btn_next", lang), callback_data="next_card")])
    else:
        buttons.append([InlineKeyboardButton(text=voice_text, callback_data=f"voice_word:{word_id}")])
        buttons.append([
            InlineKeyboardButton(text=i18n.get("btn_rate_learning", lang), callback_data=f"rate:{word_id}:learning"),
            InlineKeyboardButton(text=i18n.get("btn_rate_review", lang), callback_data=f"rate:{word_id}:review"),
            InlineKeyboardButton(text=i18n.get("btn_rate_known", lang), callback_data=f"rate:{word_id}:known")
        ])
        buttons.append([InlineKeyboardButton(text=i18n.get("btn_next", lang), callback_data="next_card")])

    buttons.append([InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_card_rated_keyboard(word_id: Optional[int] = None, lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопки после сохранения оценки карточки"""
    buttons = []
    row = [InlineKeyboardButton(text=i18n.get("btn_next", lang), callback_data="next_card")]
    if word_id:
        voice_text = "🔊 Озвучить" if lang == "ru" else "🔊 Listen"
        row.append(InlineKeyboardButton(text=voice_text, callback_data=f"voice_word:{word_id}"))
    buttons.append(row)
    buttons.append([InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_quiz_keyboard(word_id: int, options: List[str], correct_answer: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопки вариантов ответов для квиза на перевод"""
    buttons = []
    for opt in options:
        is_cor = "1" if opt == correct_answer else "0"
        buttons.append([InlineKeyboardButton(text=opt, callback_data=f"qz:{word_id}:{is_cor}")])
    buttons.append([InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_next_quiz_keyboard(word_id: Optional[int] = None, lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопка перехода к следующему вопросу квиза"""
    buttons = []
    row = [InlineKeyboardButton(text=i18n.get("btn_next", lang), callback_data="next_quiz")]
    if word_id:
        voice_text = "🔊 Озвучить" if lang == "ru" else "🔊 Listen"
        row.append(InlineKeyboardButton(text=voice_text, callback_data=f"voice_word:{word_id}"))
    buttons.append(row)
    buttons.append([InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_to_menu_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопка быстрого возврата в главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_stats_keyboard(lang: str = "ru", notifications_enabled: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура экрана статистики с кнопками управления профилем и напоминаниями"""
    test_btn_text = "🎓 Пройти тест на уровень" if lang == "ru" else "🎓 Take Level Placement Test"
    achieve_btn_text = i18n.get("btn_achievements", lang)
    notif_btn_text = i18n.get("btn_toggle_reminders_on" if notifications_enabled else "btn_toggle_reminders_off", lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=achieve_btn_text, callback_data="menu_achievements")],
        [InlineKeyboardButton(text=test_btn_text, callback_data="menu_placement")],
        [
            InlineKeyboardButton(text=i18n.get("btn_premium", lang), callback_data="menu_premium"),
            InlineKeyboardButton(text=notif_btn_text, callback_data="toggle_notif")
        ],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_achievements_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура витрины достижений"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_back_to_stats", lang), callback_data="menu_stats")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_premium_keyboard(
    lang: str = "ru",
    is_active: bool = False,
    trial_available: bool = True,
    has_discount: bool = False
) -> InlineKeyboardMarkup:
    """Клавиатура оформления и управления тарифом Stork Premium"""
    buttons = []
    if trial_available:
        buttons.append([InlineKeyboardButton(text=i18n.get("btn_premium_trial", lang), callback_data="premium_trial")])

    plan_btn_title = "⭐️ Тарифы подписки (скидка 50% 🔥)" if (has_discount and lang == "ru") else (
        "⭐️ Plans (50% OFF 🔥)" if has_discount else i18n.get("btn_premium_plans", lang)
    )
    buttons.append([InlineKeyboardButton(text=plan_btn_title, callback_data="premium_plans")])
    buttons.append([InlineKeyboardButton(text=i18n.get("btn_referrals", lang), callback_data="menu_referrals")])
    buttons.append([InlineKeyboardButton(text=i18n.get("btn_premium_promo", lang), callback_data="premium_promo")])
    buttons.append([InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_premium_plans_keyboard(lang: str = "ru", has_discount: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифов Stork Premium из premium_config.py"""
    buttons = []
    for plan in PREMIUM_PLANS:
        price = get_plan_price(plan, has_discount=has_discount)
        title = plan["title_ru"] if lang == "ru" else plan["title_en"]
        if has_discount and plan.get("is_monthly"):
            text = f"⭐️ {title} — {price} Stars (-50% 🔥)"
        else:
            text = f"⭐️ {title} — {price} Stars"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"buy_plan:{plan['id']}")])

    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад в Премиум" if lang == "ru" else "⬅️ Back to Premium", callback_data="menu_premium"),
        InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_referral_keyboard(referral_link: str, lang: str = "ru", has_discount: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура реферальной программы со ссылкой поделиться"""
    share_text = (
        "Учи немецкий язык с умным ботом Stork! 🇩🇪🪶 Присоединяйся по ссылке:"
        if lang == "ru"
        else "Learn German with smart AI tutor Stork! 🇩🇪🪶 Join via my link:"
    )
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(referral_link)}&text={urllib.parse.quote(share_text)}"

    buttons = [
        [InlineKeyboardButton(text="🚀 Поделиться с другом" if lang == "ru" else "🚀 Share with Friends", url=share_url)],
        [InlineKeyboardButton(
            text="⭐️ Тарифы со скидкой 50% 🔥" if has_discount else ("⭐️ Оформить Premium" if lang == "ru" else "⭐️ Get Premium"),
            callback_data="premium_plans"
        )],
        [
            InlineKeyboardButton(text="⬅️ Назад в Премиум" if lang == "ru" else "⬅️ Back to Premium", callback_data="menu_premium"),
            InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_quota_exceeded_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура при исчерпании дневного бесплатного лимита запросов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_premium", lang), callback_data="menu_premium")],
        [InlineKeyboardButton(text=i18n.get("btn_premium_trial", lang), callback_data="premium_trial")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_reminder_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура для уведомления-напоминания о серии занятий"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_quick_train", lang), callback_data="menu_cards")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])



def get_ai_dialog_welcome_keyboard(lang: str = "ru", has_history: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура входа в режим ИИ-собеседника (с кнопками продолжения или очистки)"""
    buttons = []
    if has_history:
        buttons.append([InlineKeyboardButton(text=i18n.get("btn_ai_continue", lang), callback_data="ai_resume")])
        buttons.append([InlineKeyboardButton(text=i18n.get("btn_ai_clear", lang), callback_data="ai_clear")])
    buttons.append([InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_ai_in_chat_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура под ответом ИИ: озвучить немецкую часть, завершить сессию, очистить контекст или выйти в меню"""
    voice_text = "🔊 Озвучить по-немецки" if lang == "ru" else "🔊 Listen in German"
    finish_text = "🏁 Завершить сессию" if lang == "ru" else "🏁 Finish session"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=voice_text, callback_data="ai_voice_last")],
        [
            InlineKeyboardButton(text=finish_text, callback_data="ai_finish"),
            InlineKeyboardButton(text="🔄 Очистить" if lang == "ru" else "🔄 Clear", callback_data="ai_clear")
        ],
        [
            InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")
        ]
    ])

def get_exam_levels_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура выбора уровня для экзаменационного тренажера"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_exam_lvl_a1", lang), callback_data="exam_lvl:A1")],
        [InlineKeyboardButton(text=i18n.get("btn_exam_lvl_a2", lang), callback_data="exam_lvl:A2")],
        [InlineKeyboardButton(text=i18n.get("btn_exam_lvl_b1", lang), callback_data="exam_lvl:B1")],
        [InlineKeyboardButton(text=i18n.get("btn_exam_lvl_random", lang), callback_data="exam_lvl:RANDOM")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_exam_task_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура при активном экзаменационном задании"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_exam_new_task", lang), callback_data="exam_new_task")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_exam_result_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура после проверки экзаменационной работы"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_exam_sample_voice", lang), callback_data="exam_voice_sample")],
        [InlineKeyboardButton(text=i18n.get("btn_exam_next", lang), callback_data="menu_exam")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_placement_welcome_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура перед началом теста на уровень"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_start_placement", lang), callback_data="placement_start")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_placement_question_keyboard(q_index: int, options: List[str], lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура с 4 вариантами ответа на вопрос теста на уровень"""
    buttons = []
    for opt_idx, opt_text in enumerate(options):
        buttons.append([InlineKeyboardButton(text=opt_text, callback_data=f"pq:{q_index}:{opt_idx}")])
    buttons.append([InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")] )
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_placement_result_keyboard(level: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура сертификата с кнопкой применения уровня"""
    apply_text = i18n.get("btn_apply_placement_level", lang, level=level)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=apply_text, callback_data=f"set_lvl:{level}")],
        [InlineKeyboardButton(text=i18n.get("btn_retake_placement", lang), callback_data="placement_start")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_verbs_sprint_keyboard(options: List[str], correct_answer: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура вариантов ответа для спринта глаголов и предлогов"""
    buttons = []
    for opt in options:
        is_cor = "1" if opt == correct_answer else "0"
        btn_data = f"vs:{is_cor}:{opt[:18]}"
        buttons.append([InlineKeyboardButton(text=opt, callback_data=btn_data)])
    buttons.append([InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_next_verbs_sprint_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопка перехода к следующему вопросу спринта глаголов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_next", lang), callback_data="menu_verbs_sprint")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_sprechen_levels_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура выбора уровня для устного экзамена Sprechen"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_exam_lvl_a1", lang), callback_data="spr_lvl:A1")],
        [InlineKeyboardButton(text=i18n.get("btn_exam_lvl_a2", lang), callback_data="spr_lvl:A2")],
        [InlineKeyboardButton(text=i18n.get("btn_exam_lvl_b1", lang), callback_data="spr_lvl:B1")],
        [InlineKeyboardButton(text=i18n.get("btn_exam_lvl_random", lang), callback_data="spr_lvl:RANDOM")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_sprechen_task_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура при активном билете устного экзамена"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_exam_new_task", lang), callback_data="spr_new_task")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_sprechen_result_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура после оценки устного экзамена"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔊 Озвучить эталон (Musterantwort)" if lang == "ru" else "🔊 Listen to Model Answer", callback_data="spr_voice_sample")],
        [InlineKeyboardButton(text="🎙️ Следующий билет" if lang == "ru" else "🎙️ Next Task", callback_data="menu_sprechen")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_listening_levels_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура выбора уровня для тренажера аудирования"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_exam_lvl_a1", lang), callback_data="hv_lvl:A1")],
        [InlineKeyboardButton(text=i18n.get("btn_exam_lvl_a2", lang), callback_data="hv_lvl:A2")],
        [InlineKeyboardButton(text=i18n.get("btn_exam_lvl_b1", lang), callback_data="hv_lvl:B1")],
        [InlineKeyboardButton(text=i18n.get("btn_exam_lvl_random", lang), callback_data="hv_lvl:RANDOM")],
        [InlineKeyboardButton(text=i18n.get("btn_hub_exams", lang), callback_data="hub_exams")]
    ])

def get_listening_question_keyboard(task_id: str, options: List[str], lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура с 4 вариантами ответа на вопрос аудирования"""
    buttons = []
    for idx, opt in enumerate(options):
        buttons.append([InlineKeyboardButton(text=opt, callback_data=f"hv_ans:{task_id}:{idx}")])
    buttons.append([InlineKeyboardButton(text=i18n.get("btn_hub_exams", lang), callback_data="hub_exams")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_listening_result_keyboard(level: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура после ответа на вопрос аудирования"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_listening_next", lang), callback_data=f"hv_next:{level}")],
        [InlineKeyboardButton(text=i18n.get("btn_hub_exams", lang), callback_data="hub_exams")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])

def get_roleplay_scenarios_keyboard(scenarios: List[Dict[str, Any]], lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура выбора сценария ролевой игры"""
    buttons = []
    for s in scenarios:
        title = s["title"].get(lang, s["title"]["ru"])
        btn_text = f"{s['icon']} {title}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"rp_start:{s['id']}")])
    buttons.append([InlineKeyboardButton(text=i18n.get("btn_hub_training", lang), callback_data="hub_training")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_roleplay_in_dialog_keyboard(scenario_id: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура во время активного ролевого диалога"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=i18n.get("btn_rp_hint", lang), callback_data=f"rp_hint:{scenario_id}"),
            InlineKeyboardButton(text=i18n.get("btn_rp_voice", lang), callback_data="rp_voice_last")
        ],
        [
            InlineKeyboardButton(text=i18n.get("btn_rp_finish", lang), callback_data="rp_finish"),
            InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")
        ]
    ])

def get_roleplay_result_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура после завершения ролевого диалога и получения оценки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_rp_next", lang), callback_data="menu_roleplay")],
        [InlineKeyboardButton(text=i18n.get("btn_hub_training", lang), callback_data="hub_training")],
        [InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")]
    ])




