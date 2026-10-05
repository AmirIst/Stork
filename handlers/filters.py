import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import db
from database.words_data import CATEGORY_METADATA
from keyboards.inline import (
    get_filters_keyboard,
    get_level_selection_keyboard,
    get_category_selection_keyboard
)

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "open_filters")
async def cb_open_filters(callback: CallbackQuery):
    """Открыть меню выбора уровня и категорий"""
    lang = await db.get_user_lang(callback.from_user.id)
    level, category = await db.get_user_filters(callback.from_user.id)

    title = "🎯 *Настройка тем и уровня сложности*" if lang == "ru" else "🎯 *Learning Level and Topic Settings*"
    desc = (
        "Здесь ты можешь выбрать желаемый уровень сложности (A1, A2, B1) "
        "и конкретную тему слов для тренировок.\n\n"
        "Выбранные настройки автоматически применяются к карточкам, квизу и тренажеру артиклей!"
        if lang == "ru" else
        "Choose your target difficulty level (A1, A2, B1) "
        "and specific topic of words to practice.\n\n"
        "These settings automatically apply to Flashcards, Quiz, and Article Trainer!"
    )

    await callback.message.edit_text(
        f"{title}\n\n{desc}",
        reply_markup=get_filters_keyboard(level, category, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "choose_level")
async def cb_choose_level(callback: CallbackQuery):
    """Показать список уровней сложности"""
    lang = await db.get_user_lang(callback.from_user.id)
    level, _ = await db.get_user_filters(callback.from_user.id)

    title = "📶 *Выбери уровень сложности:*" if lang == "ru" else "📶 *Select difficulty level:*"
    await callback.message.edit_text(
        title,
        reply_markup=get_level_selection_keyboard(level, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("set_lvl:"))
async def cb_set_level(callback: CallbackQuery):
    """Установить выбранный уровень"""
    lvl_code = callback.data.split(":")[1]
    await db.set_user_level(callback.from_user.id, lvl_code)

    lang = await db.get_user_lang(callback.from_user.id)
    _, category = await db.get_user_filters(callback.from_user.id)

    msg = f"Уровень изменен на: {lvl_code}" if lang == "ru" else f"Level changed to: {lvl_code}"
    await callback.answer(msg)

    title = "🎯 *Настройка тем и уровня сложности*" if lang == "ru" else "🎯 *Learning Level and Topic Settings*"
    await callback.message.edit_text(
        title,
        reply_markup=get_filters_keyboard(lvl_code, category, lang=lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "choose_category")
async def cb_choose_category(callback: CallbackQuery):
    """Показать список категорий слов"""
    lang = await db.get_user_lang(callback.from_user.id)
    _, category = await db.get_user_filters(callback.from_user.id)

    title = "📂 *Выбери тему слов:*" if lang == "ru" else "📂 *Select word topic:*"
    await callback.message.edit_text(
        title,
        reply_markup=get_category_selection_keyboard(category, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("set_cat:"))
async def cb_set_category(callback: CallbackQuery):
    """Установить выбранную категорию"""
    cat_code = callback.data.split(":")[1]
    await db.set_user_category(callback.from_user.id, cat_code)

    lang = await db.get_user_lang(callback.from_user.id)
    level, _ = await db.get_user_filters(callback.from_user.id)

    cat_name = CATEGORY_METADATA.get(cat_code, {}).get(lang, "Все темы" if lang == "ru" else "All topics")
    msg = f"Тема изменена на: {cat_name}" if lang == "ru" else f"Topic changed to: {cat_name}"
    await callback.answer(msg)

    title = "🎯 *Настройка тем и уровня сложности*" if lang == "ru" else "🎯 *Learning Level and Topic Settings*"
    await callback.message.edit_text(
        title,
        reply_markup=get_filters_keyboard(level, cat_code, lang=lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "reset_filters")
async def cb_reset_filters(callback: CallbackQuery):
    """Сбросить настройки на все слова"""
    await db.set_user_level(callback.from_user.id, "ALL")
    await db.set_user_category(callback.from_user.id, "ALL")

    lang = await db.get_user_lang(callback.from_user.id)
    msg = "Выбраны все слова и уровни!" if lang == "ru" else "All words and levels selected!"
    await callback.answer(msg)

    title = "🎯 *Настройка тем и уровня сложности*" if lang == "ru" else "🎯 *Learning Level and Topic Settings*"
    await callback.message.edit_text(
        title,
        reply_markup=get_filters_keyboard("ALL", "ALL", lang=lang),
        parse_mode="Markdown"
    )
