import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import db
from locales.manager import i18n
from keyboards.inline import (
    get_card_keyboard,
    get_card_rated_keyboard
)
from services.ui_helper import show_or_update_window

logger = logging.getLogger(__name__)
router = Router()

async def send_flashcard(callback: CallbackQuery, lang: str):
    """Показать новую карточку слова"""
    level, category = await db.get_user_filters(callback.from_user.id)
    word_data = await db.get_random_word(lang=lang, level=level, category=category)
    if not word_data:
        await show_or_update_window(callback, "По выбранным фильтрам слов не найдено.", parse_mode="Markdown")
        return

    plural_str = f"({word_data['plural']})" if word_data.get("plural") else ""
    user_status = await db.get_word_user_status(callback.from_user.id, word_data["id"])

    status_badge = ""
    if user_status == "known":
        status_badge = " [🟢 Знаю]" if lang == "ru" else " [🟢 Known]"
    elif user_status == "review":
        status_badge = " [🟡 Повторение]" if lang == "ru" else " [🟡 In Review]"
    elif user_status == "learning":
        status_badge = " [🔴 Учу]" if lang == "ru" else " [🔴 Learning]"

    text = (
        f"{i18n.get('card_title', lang, level=word_data['level'])}{status_badge}\n\n"
        f"🇩🇪 *{word_data['article']} {word_data['word']}* {plural_str}\n\n"
        f"{i18n.get('card_prompt_recall', lang)}"
    )

    await show_or_update_window(
        callback,
        text,
        reply_markup=get_card_keyboard(word_data["id"], lang=lang, is_revealed=False),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "menu_cards")
async def cb_menu_cards(callback: CallbackQuery):
    """Открытие карточек из главного меню"""
    lang = await db.get_user_lang(callback.from_user.id)
    await send_flashcard(callback, lang)
    await callback.answer()

@router.callback_query(F.data == "next_card")
async def cb_next_card(callback: CallbackQuery):
    """Переход к следующей карточке"""
    lang = await db.get_user_lang(callback.from_user.id)
    await send_flashcard(callback, lang)
    await callback.answer()

@router.callback_query(F.data.startswith("card_rev:"))
async def cb_reveal_card(callback: CallbackQuery):
    """Показать перевод и кнопки оценки Anki"""
    word_id = int(callback.data.split(":")[1])
    lang = await db.get_user_lang(callback.from_user.id)
    word_data = await db.get_word_by_id(word_id, lang=lang)

    if not word_data:
        await callback.answer("Слово не найдено", show_alert=True)
        return

    plural_str = f"({word_data['plural']})" if word_data.get("plural") else ""
    card_content = i18n.get(
        "card_word",
        lang,
        article=word_data["article"],
        word=word_data["word"],
        plural=plural_str,
        translation=word_data["translation"],
        example_de=word_data["example_de"],
        example_tr=word_data["example_tr"]
    )
    
    rate_prompt = i18n.get("card_prompt_rate", lang)
    text = (
        f"{i18n.get('card_title', lang, level=word_data['level'])}\n\n"
        f"{card_content}\n\n"
        f"_{rate_prompt}_"
    )

    await show_or_update_window(
        callback,
        text,
        reply_markup=get_card_keyboard(word_data["id"], lang=lang, is_revealed=True),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("rate:"))
async def cb_rate_card(callback: CallbackQuery):
    """Сохранение оценки карточки в стиле Anki (знаю, повторить, учу)"""
    parts = callback.data.split(":")
    word_id = int(parts[1])
    status = parts[2]

    await db.set_word_status(callback.from_user.id, word_id, status)
    lang = await db.get_user_lang(callback.from_user.id)
    word_data = await db.get_word_by_id(word_id, lang=lang)

    if not word_data:
        await callback.answer()
        return

    status_msg = i18n.get(f"status_marked_{status}", lang)

    plural_str = f"({word_data['plural']})" if word_data.get("plural") else ""
    card_content = i18n.get(
        "card_word",
        lang,
        article=word_data["article"],
        word=word_data["word"],
        plural=plural_str,
        translation=word_data["translation"],
        example_de=word_data["example_de"],
        example_tr=word_data["example_tr"]
    )

    text = (
        f"{status_msg}\n\n"
        f"🇩🇪 *{word_data['article']} {word_data['word']}* {plural_str}\n"
        f"💬 {word_data['translation']}"
    )

    await show_or_update_window(
        callback,
        text,
        reply_markup=get_card_rated_keyboard(word_id=word_id, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()
