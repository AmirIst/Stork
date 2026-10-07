import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import db
from locales.manager import i18n
from keyboards.inline import (
    get_quiz_keyboard,
    get_next_quiz_keyboard
)
from services.ui_helper import show_or_update_window

logger = logging.getLogger(__name__)
router = Router()

async def send_quiz_question(callback: CallbackQuery, lang: str):
    """Генерация и отправка нового вопроса квиза"""
    level, category = await db.get_user_filters(callback.from_user.id)
    quiz_data = await db.get_translation_quiz_data(lang=lang, level=level, category=category)
    if not quiz_data:
        no_words = "По выбранным фильтрам слов не найдено." if lang == "ru" else "No words found for the selected filters."
        await show_or_update_window(callback, no_words, parse_mode="Markdown")
        return

    word = quiz_data["word"]
    options = quiz_data["options"]
    correct = quiz_data["correct_answer"]

    text = i18n.get(
        "quiz_title",
        lang,
        article=word["article"],
        word=word["word"]
    )

    await show_or_update_window(
        callback,
        text,
        reply_markup=get_quiz_keyboard(word["id"], options, correct, lang=lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "menu_quiz")
async def cb_menu_quiz(callback: CallbackQuery):
    """Старт квиза из главного меню"""
    await callback.answer()
    lang = await db.get_user_lang(callback.from_user.id)
    await send_quiz_question(callback, lang)

@router.callback_query(F.data == "next_quiz")
async def cb_next_quiz(callback: CallbackQuery):
    """Следующий вопрос квиза"""
    await callback.answer()
    lang = await db.get_user_lang(callback.from_user.id)
    await send_quiz_question(callback, lang)

@router.callback_query(F.data.startswith("qz:"))
async def cb_answer_quiz(callback: CallbackQuery):
    """Проверка ответа в квизе"""
    await callback.answer()
    parts = callback.data.split(":")
    word_id = int(parts[1])
    is_correct = (parts[2] == "1")

    lang = await db.get_user_lang(callback.from_user.id)
    word_data = await db.get_word_by_id(word_id, lang=lang)

    if not word_data:
        err_msg = "Ошибка вопроса" if lang == "ru" else "Question error"
        await callback.message.answer(err_msg)
        return

    if is_correct:
        score, streak = await db.add_user_score(callback.from_user.id, points=1)
        await db.record_user_answer(callback.from_user.id, word_id, True)
        header = f"{i18n.get('quiz_correct', lang)} 🔥 {streak}"
    else:
        await db.reset_streak(callback.from_user.id)
        await db.record_user_answer(callback.from_user.id, word_id, False)
        header = i18n.get("quiz_wrong", lang, correct_tr=word_data["translation"])

    await db.update_daily_streak(callback.from_user.id)

    card = (
        f"📖 *{word_data['article']} {word_data['word']}*: {word_data['translation']}\n"
        f"💡 _{word_data['example_de']}_\n"
        f"({word_data['example_tr']})"
    )

    full_text = f"{header}\n\n{card}"

    await show_or_update_window(
        callback,
        full_text,
        reply_markup=get_next_quiz_keyboard(word_id=word_id, lang=lang),
        parse_mode="Markdown"
    )
