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
    get_back_to_menu_keyboard
)

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
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "menu_lang")
async def cb_menu_lang(callback: CallbackQuery):
    """Кнопка смены языка в меню"""
    lang = await db.get_user_lang(callback.from_user.id)
    text = i18n.get("lang_select_title", lang)
    await callback.message.edit_text(text, reply_markup=get_language_keyboard(), parse_mode="Markdown")
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
    
    await callback.message.edit_text(
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
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_menu_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()
