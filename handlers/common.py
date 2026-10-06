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
    get_stats_keyboard
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
    level, category = await db.get_user_filters(message.from_user.id)

    text = i18n.get("welcome", lang, name=message.from_user.first_name or "Freund")
    await message.answer(text, reply_markup=get_main_menu_keyboard(lang, level, category), parse_mode="Markdown")

@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    """Команда /menu: возврат в главное меню"""
    await state.clear()
    lang = await db.get_user_lang(message.from_user.id)
    level, category = await db.get_user_filters(message.from_user.id)
    text = i18n.get("menu_title", lang)
    await message.answer(text, reply_markup=get_main_menu_keyboard(lang, level, category), parse_mode="Markdown")

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
    level, category = await db.get_user_filters(callback.from_user.id)
    text = i18n.get("menu_title", lang)
    kb = get_main_menu_keyboard(lang, level, category)
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
        reply_markup=get_main_menu_keyboard(selected_lang, level, category),
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

    full_stats_text = f"{text}{level_info}"
    
    await show_or_update_window(
        callback,
        full_stats_text,
        reply_markup=get_stats_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()
