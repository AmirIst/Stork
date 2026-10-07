import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext

from database import db
from locales.manager import i18n
from services.listening_service import get_listening_task
from services.tts import synthesize_speech
from services.ui_helper import show_or_update_window, mark_voice_sent
from keyboards.inline import (
    get_listening_levels_keyboard,
    get_listening_question_keyboard,
    get_listening_result_keyboard
)

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "menu_listening")
async def cb_menu_listening(callback: CallbackQuery):
    """Экран выбора уровня для аудирования Goethe & Telc"""
    lang = await db.get_user_lang(callback.from_user.id)
    text = i18n.get("listening_welcome", lang)
    await show_or_update_window(callback, text, reply_markup=get_listening_levels_keyboard(lang), parse_mode="Markdown")
    await callback.answer()

async def send_listening_challenge(callback: CallbackQuery, level: str, lang: str):
    """Синтез аудио и отправка задания по аудированию"""
    task = get_listening_task(level=level)
    user_id = callback.from_user.id

    await callback.answer("Генерирую немецкую аудиозапись..." if lang == "ru" else "Generating German audio...")
    await callback.message.bot.send_chat_action(chat_id=callback.message.chat.id, action="record_voice")

    audio_bytes = await synthesize_speech(task["audio_text"])
    if not audio_bytes:
        err_msg = "Не удалось сгенерировать аудиозапись" if lang == "ru" else "Could not generate audio"
        await callback.message.answer(err_msg)
        return

    # 1. Отправляем голосовое сообщение
    voice_file = BufferedInputFile(audio_bytes, filename=f"listening_{task['id']}.mp3")
    title_text = task["title"].get(lang, task["title"]["ru"])
    caption = f"🎧 *Goethe & Telc Hörverstehen ({task['level']})*\n_{title_text}_"

    await callback.message.answer_voice(
        voice=voice_file,
        caption=caption,
        parse_mode="Markdown"
    )

    # Отмечаем, что голосовое отправлено, чтобы следующее окно открылось внизу
    mark_voice_sent(user_id)

    # 2. Отправляем интерактивную карточку с вопросом
    q_text = task["question"].get(lang, task["question"]["ru"])
    options = task["options"].get(lang, task["options"]["ru"])
    prompt = i18n.get("listening_listen_prompt", lang, question=q_text)

    await show_or_update_window(
        callback,
        prompt,
        reply_markup=get_listening_question_keyboard(task["id"], options, lang=lang),
        parse_mode="Markdown",
        force_repost=True
    )

@router.callback_query(F.data.startswith("hv_lvl:"))
async def cb_choose_listening_level(callback: CallbackQuery):
    """Выбор уровня и генерация первого аудио-задания"""
    level = callback.data.split(":")[1]
    lang = await db.get_user_lang(callback.from_user.id)
    await send_listening_challenge(callback, level, lang)

@router.callback_query(F.data.startswith("hv_next:"))
async def cb_next_listening_challenge(callback: CallbackQuery):
    """Следующее аудио-задание"""
    level = callback.data.split(":")[1]
    lang = await db.get_user_lang(callback.from_user.id)
    await send_listening_challenge(callback, level, lang)

@router.callback_query(F.data.startswith("hv_ans:"))
async def cb_check_listening_answer(callback: CallbackQuery):
    """Проверка ответа на вопрос аудирования"""
    parts = callback.data.split(":")
    task_id = parts[1]
    chosen_idx = int(parts[2])

    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)
    task = get_listening_task(task_id=task_id)

    is_correct = (chosen_idx == task["correct_index"])
    correct_opt = task["options"].get(lang, task["options"]["ru"])[task["correct_index"]]

    if is_correct:
        score, streak = await db.add_user_score(user_id, points=1)
        await db.update_daily_streak(user_id)
        await db.unlock_achievement(user_id, "listening_ear")
        header = f"{i18n.get('listening_correct', lang)} 🔥 {streak}"
    else:
        await db.reset_streak(user_id)
        await db.update_daily_streak(user_id)
        header = i18n.get("listening_wrong", lang, correct=correct_opt)

    explanation = task["explanation"].get(lang, task["explanation"]["ru"])
    tr_text = task["transcript_tr"].get(lang, task["transcript_tr"]["ru"])
    header_tr = i18n.get("listening_transcript_header", lang)

    explanation_label = "Разбор:" if lang == "ru" else "Explanation:"
    response_text = (
        f"{header}\n\n"
        f"💡 *{explanation_label}* {explanation}\n\n"
        f"{header_tr}\n"
        f"🇩🇪 _{task['audio_text']}_\n\n"
        f"💬 _{tr_text}_"
    )

    await show_or_update_window(
        callback,
        response_text,
        reply_markup=get_listening_result_keyboard(task["level"], lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()
