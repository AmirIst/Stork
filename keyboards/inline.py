from typing import List, Dict, Any, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from locales.manager import i18n
from database.words_data import CATEGORY_METADATA

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора языка"""
    languages = i18n.get_available_languages()
    buttons = []
    for code, info in languages.items():
        text = f"{info['flag']} {info['name']}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"set_lang:{code}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_main_menu_keyboard(lang: str = "ru", level: str = "ALL", category: str = "ALL") -> InlineKeyboardMarkup:
    """Главное меню бота Stork с понятными кнопками без англицизмов"""
    level_label = "Все уровни" if level == "ALL" else level
    if lang != "ru" and level == "ALL":
        level_label = "All levels"
        
    cat_label = "Все темы" if category == "ALL" else CATEGORY_METADATA.get(category, {}).get(lang, category)
    if lang != "ru" and category == "ALL":
        cat_label = "All topics"

    if lang == "ru":
        topics_btn_text = f"🎯 Темы и уровень: {level_label} • {cat_label}"
    else:
        topics_btn_text = f"🎯 Level & Topics: {level_label} • {cat_label}"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.get("btn_articles", lang), callback_data="menu_articles")],
        [InlineKeyboardButton(text=i18n.get("btn_cards", lang), callback_data="menu_cards")],
        [InlineKeyboardButton(text=i18n.get("btn_quiz", lang), callback_data="menu_quiz")],
        [InlineKeyboardButton(text=i18n.get("btn_exam_trainer", lang), callback_data="menu_exam")],
        [InlineKeyboardButton(text=i18n.get("btn_ai_tutor", lang), callback_data="menu_ai")],
        [InlineKeyboardButton(text=topics_btn_text, callback_data="open_filters")],
        [
            InlineKeyboardButton(text=i18n.get("btn_stats", lang), callback_data="menu_stats"),
            InlineKeyboardButton(text=i18n.get("btn_settings", lang), callback_data="menu_lang")
        ]
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

def get_ai_dialog_welcome_keyboard(lang: str = "ru", has_history: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура входа в режим ИИ-собеседника (с кнопками продолжения или очистки)"""
    buttons = []
    if has_history:
        buttons.append([InlineKeyboardButton(text=i18n.get("btn_ai_continue", lang), callback_data="ai_resume")])
        buttons.append([InlineKeyboardButton(text=i18n.get("btn_ai_clear", lang), callback_data="ai_clear")])
    buttons.append([InlineKeyboardButton(text=i18n.get("btn_main_menu", lang), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_ai_in_chat_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура под ответом ИИ: озвучить немецкую часть, очистить контекст или выйти в меню"""
    voice_text = "🔊 Озвучить по-немецки" if lang == "ru" else "🔊 Listen in German"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=voice_text, callback_data="ai_voice_last")],
        [
            InlineKeyboardButton(text="🔄 Очистить чат" if lang == "ru" else "🔄 Clear chat", callback_data="ai_clear"),
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


