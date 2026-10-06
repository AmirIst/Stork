import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import db
from locales.manager import i18n
from keyboards.inline import (
    get_article_keyboard,
    get_next_article_keyboard
)

logger = logging.getLogger(__name__)
router = Router()

async def send_article_challenge(callback: CallbackQuery, lang: str):
    """Отправка нового вопроса на угадывание артикля"""
    level, category = await db.get_user_filters(callback.from_user.id)
    word_data = await db.get_random_word(lang=lang, level=level, category=category)
    if not word_data:
        await callback.message.edit_text("По выбранным фильтрам слов не найдено.", parse_mode="Markdown")
        return

    text = i18n.get(
        "article_quiz_title",
        lang,
        word=word_data["word"],
        translation=word_data["translation"] or "..."
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_article_keyboard(word_data["id"], lang=lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "menu_articles")
async def cb_start_articles(callback: CallbackQuery):
    """Запуск тренажера артиклей из меню"""
    lang = await db.get_user_lang(callback.from_user.id)
    await send_article_challenge(callback, lang)
    await callback.answer()

@router.callback_query(F.data == "next_article")
async def cb_next_article(callback: CallbackQuery):
    """Следующее слово в тренажере артиклей"""
    lang = await db.get_user_lang(callback.from_user.id)
    await send_article_challenge(callback, lang)
    await callback.answer()

@router.callback_query(F.data.startswith("art:"))
async def cb_check_article(callback: CallbackQuery):
    """Проверка выбранного артикля"""
    parts = callback.data.split(":")
    word_id = int(parts[1])
    chosen_article = parts[2]

    lang = await db.get_user_lang(callback.from_user.id)
    word_data = await db.get_word_by_id(word_id, lang=lang)

    if not word_data:
        await callback.answer("Слово не найдено", show_alert=True)
        return

    correct_article = word_data["article"].lower()
    is_correct = (chosen_article.lower() == correct_article)

    if is_correct:
        score, streak = await db.add_user_score(callback.from_user.id, points=1)
        await db.record_user_answer(callback.from_user.id, word_id, True)
        result_header = f"{i18n.get('article_correct', lang)} 🔥 {streak}"
    else:
        await db.reset_streak(callback.from_user.id)
        await db.record_user_answer(callback.from_user.id, word_id, False)
        result_header = i18n.get("article_wrong", lang, correct_article=word_data["article"])

    details = i18n.get(
        "article_card_detail",
        lang,
        article=word_data["article"],
        word=word_data["word"],
        plural=word_data["plural"] or "",
        translation=word_data["translation"] or "",
        example_de=word_data["example_de"] or "",
        example_tr=word_data["example_tr"] or ""
    )

    full_response = f"{result_header}\n\n{details}"

    await callback.message.edit_text(
        full_response,
        reply_markup=get_next_article_keyboard(word_id=word_id, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()
