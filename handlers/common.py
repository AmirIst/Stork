import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import db
from locales.manager import i18n
from keyboards.inline import (
    get_main_menu_keyboard,
    get_language_keyboard,
    get_back_to_menu_keyboard,
    get_stats_keyboard,
    get_training_hub_keyboard,
    get_vocab_hub_keyboard,
    get_exams_hub_keyboard,
    get_settings_hub_keyboard
)
from services.ui_helper import show_or_update_window

logger = logging.getLogger(__name__)
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Команда /start: приветствие и инициализация пользователя"""
    await state.clear()
    user = await db.get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    lang = user["native_lang"]

    text = i18n.get("welcome", lang, name=message.from_user.first_name or "Freund")
    await message.answer(text, reply_markup=get_main_menu_keyboard(lang), parse_mode="Markdown")

@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    """Команда /menu: возврат в главное меню"""
    await state.clear()
    lang = await db.get_user_lang(message.from_user.id)
    text = i18n.get("menu_title", lang)
    await message.answer(text, reply_markup=get_main_menu_keyboard(lang), parse_mode="Markdown")

@router.message(Command("lang"))
async def cmd_language(message: Message):
    """Команда /lang: выбор языка интерфейса"""
    lang = await db.get_user_lang(message.from_user.id)
    text = i18n.get("lang_select_title", lang)
    await message.answer(text, reply_markup=get_language_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "back_to_menu")
async def cb_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню через Inline-кнопку"""
    await state.clear()
    lang = await db.get_user_lang(callback.from_user.id)
    text = i18n.get("menu_title", lang)
    kb = get_main_menu_keyboard(lang)
    await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "hub_training")
async def cb_hub_training(callback: CallbackQuery):
    """Подменю: Раздел тренировок"""
    lang = await db.get_user_lang(callback.from_user.id)
    text = i18n.get("hub_training_title", lang)
    await show_or_update_window(callback, text, reply_markup=get_training_hub_keyboard(lang), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "hub_vocab")
async def cb_hub_vocab(callback: CallbackQuery):
    """Подменю: Словарь и темы"""
    lang = await db.get_user_lang(callback.from_user.id)
    level, category = await db.get_user_filters(callback.from_user.id)
    review_count = await db.get_review_words_count(callback.from_user.id)
    text = i18n.get("hub_vocab_title", lang)
    kb = get_vocab_hub_keyboard(lang, review_count=review_count, level=level, category=category)
    await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "hub_exams")
async def cb_hub_exams(callback: CallbackQuery):
    """Подменю: Экзамены и тесты"""
    lang = await db.get_user_lang(callback.from_user.id)
    text = i18n.get("hub_exams_title", lang)
    await show_or_update_window(callback, text, reply_markup=get_exams_hub_keyboard(lang), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "hub_settings")
async def cb_hub_settings(callback: CallbackQuery):
    """Подменю: Настройки"""
    lang = await db.get_user_lang(callback.from_user.id)
    notif_status = await db.get_user_notifications_status(callback.from_user.id)
    text = i18n.get("hub_settings_title", lang)
    kb = get_settings_hub_keyboard(lang, notifications_enabled=notif_status)
    await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "menu_lang")
async def cb_menu_lang(callback: CallbackQuery):
    """Кнопка смены языка в меню"""
    lang = await db.get_user_lang(callback.from_user.id)
    text = i18n.get("lang_select_title", lang)
    await show_or_update_window(callback, text, reply_markup=get_language_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("set_lang:"))
async def cb_set_language(callback: CallbackQuery):
    """Установка выбранного языка"""
    selected_lang = callback.data.split(":")[1]
    await db.update_user_lang(callback.from_user.id, selected_lang)
    level, category = await db.get_user_filters(callback.from_user.id)
    
    notice = i18n.get("lang_changed", selected_lang)
    menu_text = i18n.get("menu_title", selected_lang)
    full_text = f"{notice}\n\n{menu_text}"
    
    await show_or_update_window(
        callback,
        full_text,
        reply_markup=get_main_menu_keyboard(selected_lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "menu_stats")
async def cb_menu_stats(callback: CallbackQuery):
    """Просмотр личной статистики и прогресса"""
    lang = await db.get_user_lang(callback.from_user.id)
    stats = await db.get_user_stats(callback.from_user.id)
    lang_info = i18n.get_available_languages().get(lang, {"name": lang, "flag": ""})
    
    text = i18n.get(
        "stats_title",
        lang,
        name=callback.from_user.first_name or "Freund",
        lang_name=f"{lang_info['flag']} {lang_info['name']}",
        score=stats["score"],
        streak=stats["streak"],
        known_words=stats.get("known_words", 0),
        review_words=stats.get("review_words", 0),
        learning_words=stats.get("learning_words", 0),
        total_words=stats["total_words"]
    )

    if stats.get("placement_level"):
        lvl = stats["placement_level"]
        score_val = stats.get("placement_score", 0)
        if lang == "ru":
            level_info = f"\n\n🎓 *Подтвержденный уровень CEFR:* *{lvl}* ({score_val}/12)"
        else:
            level_info = f"\n\n🎓 *Verified CEFR Level:* *{lvl}* ({score_val}/12)"
    else:
        if lang == "ru":
            level_info = "\n\n🎓 *Уровень языка:* _еще не проверен (пройди тест ниже)_"
        else:
            level_info = "\n\n🎓 *Language Level:* _not tested yet (take test below)_"

    # Блок тарифа и дневных квот
    is_prem = stats.get("is_premium", False)
    ai_count = stats.get("daily_ai_count", 0)
    ai_limit = stats.get("daily_ai_limit", 10)
    exam_count = stats.get("daily_exam_count", 0)
    exam_limit = stats.get("daily_exam_limit", 3)
    notif_enabled = stats.get("notifications_enabled", True)

    if lang == "ru":
        tariff_title = f"⭐️ *Тариф:* Stork Premium 👑 (до {stats['premium_until'][:10]})" if is_prem else "⭐️ *Тариф:* Бесплатный"
        ai_quota_str = "Безлимитно ⭐️" if is_prem else f"{ai_count}/{ai_limit}"
        exam_quota_str = "Безлимитно ⭐️" if is_prem else f"{exam_count}/{exam_limit}"
        quota_info = (
            f"\n\n{tariff_title}\n"
            f"🤖 *ИИ-собеседник сегодня:* {ai_quota_str}\n"
            f"✍️ *Проверка писем сегодня:* {exam_quota_str}\n"
            f"🔔 *Напоминания о серии:* {'Включены' if notif_enabled else 'Выключены'}"
        )
    else:
        tariff_title = f"⭐️ *Plan:* Stork Premium 👑 (until {stats['premium_until'][:10]})" if is_prem else "⭐️ *Plan:* Free"
        ai_quota_str = "Unlimited ⭐️" if is_prem else f"{ai_count}/{ai_limit}"
        exam_quota_str = "Unlimited ⭐️" if is_prem else f"{exam_count}/{exam_limit}"
        quota_info = (
            f"\n\n{tariff_title}\n"
            f"🤖 *AI chat today:* {ai_quota_str}\n"
            f"✍️ *Exam checks today:* {exam_quota_str}\n"
            f"🔔 *Streak reminders:* {'Enabled' if notif_enabled else 'Disabled'}"
        )

    full_stats_text = f"{text}{level_info}{quota_info}"
    
    await show_or_update_window(
        callback,
        full_stats_text,
        reply_markup=get_stats_keyboard(lang, notifications_enabled=notif_enabled),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "toggle_notif")
async def cb_toggle_notif(callback: CallbackQuery):
    """Переключение ежедневных напоминаний о серии занятий"""
    new_status = await db.toggle_user_notifications(callback.from_user.id)
    lang = await db.get_user_lang(callback.from_user.id)
    notice = i18n.get("reminder_toggled_on" if new_status else "reminder_toggled_off", lang)
    await callback.answer(notice)
    await cb_menu_stats(callback)

