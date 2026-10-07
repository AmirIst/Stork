import io
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import db
from locales.manager import i18n
from services.sprechen_service import (
    get_sprechen_task,
    evaluate_student_speaking,
    extract_sprechen_musterantwort
)
from services.ai_tutor import transcribe_voice
from services.tts import synthesize_speech
from keyboards.inline import (
    get_sprechen_levels_keyboard,
    get_sprechen_task_keyboard,
    get_sprechen_result_keyboard,
    get_quota_exceeded_keyboard,
    get_back_to_menu_keyboard
)
from services.ui_helper import show_or_update_window, mark_voice_sent

logger = logging.getLogger(__name__)
router = Router()

class SprechenState(StatesGroup):
    waiting_submission = State()

def format_sprechen_task_message(task: dict, lang: str = "ru") -> str:
    """Форматирует карточку устного задания для ученика"""
    lang_key = "ru" if lang == "ru" else "en"
    hint = task.get("starter_hint", {}).get(lang_key, "")

    if lang == "ru":
        msg = (
            f"🎙️ *Устный экзамен Goethe / Telc ({task['level']})*\n\n"
            f"📌 *{task['teil']}*: {task['title'][lang_key]}\n"
            f"⏱️ *Длительность:* {task['target_duration']}\n\n"
            f"📝 *Инструкция для кандидата:*\n{task['instructions'][lang_key]}\n\n"
            f"💡 *Подсказка:* {hint}\n\n"
            f"👉 *Запиши голосовое сообщение с твоим ответом (или напиши текстом):*"
        )
    else:
        msg = (
            f"🎙️ *Goethe / Telc Oral Speaking Exam ({task['level']})*\n\n"
            f"📌 *{task['teil']}*: {task['title'][lang_key]}\n"
            f"⏱️ *Target length:* {task['target_duration']}\n\n"
            f"📝 *Instructions:*\n{task['instructions'][lang_key]}\n\n"
            f"💡 *Starter hint:* {hint}\n\n"
            f"👉 *Record a voice message with your spoken response (or send text):*"
        )
    return msg

@router.callback_query(F.data == "menu_sprechen")
async def cb_menu_sprechen(callback: CallbackQuery, state: FSMContext):
    """Выбор уровня сложности для устного экзамена Sprechen"""
    await state.clear()
    lang = await db.get_user_lang(callback.from_user.id)
    text = i18n.get("sprechen_welcome", lang)

    await show_or_update_window(
        callback,
        text,
        reply_markup=get_sprechen_levels_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("spr_lvl:"))
async def cb_select_sprechen_level(callback: CallbackQuery, state: FSMContext):
    """Выбор билета устного экзамена"""
    level = callback.data.split(":")[1]
    lang = await db.get_user_lang(callback.from_user.id)

    task = get_sprechen_task(level=level)
    await state.set_state(SprechenState.waiting_submission)
    await state.update_data(task_id=task["id"], level=task["level"])

    msg_text = format_sprechen_task_message(task, lang)
    await show_or_update_window(
        callback,
        msg_text,
        reply_markup=get_sprechen_task_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "spr_new_task")
async def cb_new_sprechen_task(callback: CallbackQuery, state: FSMContext):
    """Сменить билет на другой того же уровня"""
    data = await state.get_data()
    level = data.get("level", "A1")
    lang = await db.get_user_lang(callback.from_user.id)

    task = get_sprechen_task(level=level)
    await state.update_data(task_id=task["id"], level=task["level"])

    msg_text = format_sprechen_task_message(task, lang)
    await show_or_update_window(
        callback,
        msg_text,
        reply_markup=get_sprechen_task_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(SprechenState.waiting_submission, F.voice)
async def handle_sprechen_voice_submission(message: Message, state: FSMContext):
    """Обработка голосового ответа на устном экзамене"""
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)

    allowed, count, limit = await db.check_exam_quota(user_id)
    if not allowed:
        text = i18n.get("exam_quota_exceeded", lang, count=count, limit=limit)
        await message.answer(text, reply_markup=get_quota_exceeded_keyboard(lang), parse_mode="Markdown")
        return

    data = await state.get_data()
    task_id = data.get("task_id")
    task = get_sprechen_task(task_id=task_id, level=data.get("level"))

    await message.bot.send_chat_action(chat_id=message.chat.id, action="record_voice")

    try:
        file_info = await message.bot.get_file(message.voice.file_id)
        voice_stream = io.BytesIO()
        await message.bot.download_file(file_info.file_path, destination=voice_stream)
        audio_bytes = voice_stream.getvalue()

        # Транскрибируем немецкую речь
        transcribed_text = await transcribe_voice(audio_bytes, mime_type="audio/ogg")
        if not transcribed_text:
            err_msg = (
                "🪶 Не удалось разобрать аудиозапись. Попробуй надиктовать четче или отправь ответ текстом!"
                if lang == "ru"
                else "🪶 Could not transcribe audio. Please speak clearly or submit via text!"
            )
            await message.answer(err_msg)
            return

        transcript_notice = (
            f"🎙️ *Распознанный ответ кандидата:*\n_{transcribed_text}_\n\n{i18n.get('sprechen_evaluating', lang)}"
            if lang == "ru"
            else f"🎙️ *Transcribed candidate speech:*\n_{transcribed_text}_\n\n{i18n.get('sprechen_evaluating', lang)}"
        )
        eval_status = await message.answer(transcript_notice, parse_mode="Markdown")

        review = await evaluate_student_speaking(task, transcribed_text, native_lang=lang)
        await state.update_data(last_review=review)

        await db.increment_exam_quota(user_id)
        await db.update_daily_streak(user_id)

        await eval_status.edit_text(
            review,
            reply_markup=get_sprechen_result_keyboard(lang),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка при оценке устного экзамена: {e}")
        err_msg = (
            "🪶 Ошибка при обработке аудио. Попробуй еще раз!"
            if lang == "ru"
            else "🪶 Error processing audio. Please try again!"
        )
        await message.answer(err_msg)

@router.message(SprechenState.waiting_submission, F.text)
async def handle_sprechen_text_submission(message: Message, state: FSMContext):
    """Текстовая сдача ответа (с рекомендацией отправлять голосом)"""
    if message.text.startswith("/"):
        await state.clear()
        return

    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)

    allowed, count, limit = await db.check_exam_quota(user_id)
    if not allowed:
        text = i18n.get("exam_quota_exceeded", lang, count=count, limit=limit)
        await message.answer(text, reply_markup=get_quota_exceeded_keyboard(lang), parse_mode="Markdown")
        return

    data = await state.get_data()
    task_id = data.get("task_id")
    task = get_sprechen_task(task_id=task_id, level=data.get("level"))

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    eval_status = await message.answer(i18n.get("sprechen_evaluating", lang), parse_mode="Markdown")

    review = await evaluate_student_speaking(task, message.text, native_lang=lang)
    await state.update_data(last_review=review)

    await db.increment_exam_quota(user_id)
    await db.update_daily_streak(user_id)

    await eval_status.edit_text(
        review,
        reply_markup=get_sprechen_result_keyboard(lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "spr_voice_sample")
async def cb_voice_sprechen_sample(callback: CallbackQuery, state: FSMContext):
    """Озвучка идеального ответа экзаменатора (Musterantwort)"""
    data = await state.get_data()
    review = data.get("last_review", "")
    sample_text = extract_sprechen_musterantwort(review)

    if not sample_text:
        await callback.answer("Образец не найден для озвучки", show_alert=True)
        return

    await callback.answer("Генерирую голос экзаменатора...")
    audio_bytes = await synthesize_speech(sample_text)
    if audio_bytes:
        voice_file = BufferedInputFile(audio_bytes, filename="musterantwort.ogg")
        mark_voice_sent(callback.from_user.id)
        await callback.message.answer_voice(
            voice=voice_file,
            caption="🎙️ *Образец ответа экзаменатора (Musterantwort)*",
            parse_mode="Markdown"
        )
    else:
        await callback.message.answer("🪶 Не удалось синтезировать аудио.")
