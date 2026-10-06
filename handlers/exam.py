import io
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import db
from locales.manager import i18n
from services.exam_service import get_exam_task, evaluate_student_letter
from services.ai_tutor import transcribe_voice
from services.tts import synthesize_speech, extract_musterloesung_for_voice
from keyboards.inline import (
    get_exam_levels_keyboard,
    get_exam_task_keyboard,
    get_exam_result_keyboard,
    get_back_to_menu_keyboard,
    get_quota_exceeded_keyboard
)
from services.ui_helper import show_or_update_window, mark_voice_sent

logger = logging.getLogger(__name__)
router = Router()

class ExamState(StatesGroup):
    waiting_submission = State()

def format_exam_task_message(task: dict, lang: str = "ru") -> str:
    """Форматирует текст экзаменационного задания для отправки пользователю"""
    lang_key = "ru" if lang == "ru" else "en"
    points_formatted = "\n".join([f"• {p}" for p in task["points"][lang_key]])
    hint = task.get("starter_hint", {}).get(lang_key, "")

    if lang == "ru":
        msg = (
            f"✍️ *Экзаменационное задание Goethe / Telc ({task['level']})*\n\n"
            f"📌 *Тема:* {task['title'][lang_key]}\n"
            f"🎯 *Требуемый объем:* {task['target_words']} слов\n\n"
            f"📖 *Ситуация:*\n{task['situation'][lang_key]}\n\n"
            f"📝 *Обязательные пункты (Leitpunkte):*\n{points_formatted}\n\n"
            f"💡 *Подсказка:* {hint}\n\n"
            f"👉 *Напиши свой текст или отправь голосовое сообщение:*"
        )
    else:
        msg = (
            f"✍️ *Goethe / Telc Exam Assignment ({task['level']})*\n\n"
            f"📌 *Topic:* {task['title'][lang_key]}\n"
            f"🎯 *Target word count:* {task['target_words']} words\n\n"
            f"📖 *Situation:*\n{task['situation'][lang_key]}\n\n"
            f"📝 *Mandatory Points (Leitpunkte):*\n{points_formatted}\n\n"
            f"💡 *Starter Hint:* {hint}\n\n"
            f"👉 *Send your letter as a text or voice message:*"
        )
    return msg

@router.callback_query(F.data == "menu_exam")
async def cb_menu_exam(callback: CallbackQuery, state: FSMContext):
    """Открытие меню выбора уровня экзаменационного тренажера"""
    await state.clear()
    lang = await db.get_user_lang(callback.from_user.id)
    text = i18n.get("exam_welcome", lang)
    
    await show_or_update_window(
        callback,
        text,
        reply_markup=get_exam_levels_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("exam_lvl:"))
async def cb_select_exam_level(callback: CallbackQuery, state: FSMContext):
    """Выбор уровня и генерация аутентичного экзаменационного задания"""
    level = callback.data.split(":")[1]
    lang = await db.get_user_lang(callback.from_user.id)

    task = get_exam_task(level=level)
    await state.set_state(ExamState.waiting_submission)
    await state.update_data(task_id=task["id"], level=task["level"])

    msg_text = format_exam_task_message(task, lang)
    await show_or_update_window(
        callback,
        msg_text,
        reply_markup=get_exam_task_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "exam_new_task")
async def cb_new_exam_task(callback: CallbackQuery, state: FSMContext):
    """Сгенерировать другое экзаменационное задание того же уровня"""
    data = await state.get_data()
    level = data.get("level", "A1")
    lang = await db.get_user_lang(callback.from_user.id)

    task = get_exam_task(level=level)
    await state.update_data(task_id=task["id"], level=task["level"])

    msg_text = format_exam_task_message(task, lang)
    await show_or_update_window(
        callback,
        msg_text,
        reply_markup=get_exam_task_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(ExamState.waiting_submission, F.text)
async def handle_exam_text_submission(message: Message, state: FSMContext):
    """Проверка письменной работы ученика ИИ-экзаменатором"""
    if message.text.startswith("/"):
        await state.clear()
        return

    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)

    # Проверяем дневной лимит проверки экзаменов
    allowed, count, limit = await db.check_exam_quota(user_id)
    if not allowed:
        text = i18n.get("exam_quota_exceeded", lang, count=count, limit=limit)
        await message.answer(
            text,
            reply_markup=get_quota_exceeded_keyboard(lang),
            parse_mode="Markdown"
        )
        return

    data = await state.get_data()
    task_id = data.get("task_id")
    task = get_exam_task(task_id=task_id, level=data.get("level"))

    # Показываем статус оценки работы
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    eval_status = await message.answer(
        i18n.get("exam_evaluating", lang),
        parse_mode="Markdown"
    )

    review = await evaluate_student_letter(task, message.text, native_lang=lang)
    await state.update_data(last_review=review)

    # Учитываем проверку и обновляем серию занятий
    await db.increment_exam_quota(user_id)
    await db.update_daily_streak(user_id)

    await eval_status.edit_text(
        review,
        reply_markup=get_exam_result_keyboard(lang),
        parse_mode="Markdown"
    )

@router.message(ExamState.waiting_submission, F.voice)
async def handle_exam_voice_submission(message: Message, state: FSMContext):
    """Обработка экзаменационного ответа, надиктованного голосом"""
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)

    # Проверяем дневной лимит проверки экзаменов
    allowed, count, limit = await db.check_exam_quota(user_id)
    if not allowed:
        text = i18n.get("exam_quota_exceeded", lang, count=count, limit=limit)
        await message.answer(
            text,
            reply_markup=get_quota_exceeded_keyboard(lang),
            parse_mode="Markdown"
        )
        return

    data = await state.get_data()
    task_id = data.get("task_id")
    task = get_exam_task(task_id=task_id, level=data.get("level"))

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
            f"🎙️ *Распознанный текст ответа:*\n_{transcribed_text}_\n\n{i18n.get('exam_evaluating', lang)}"
            if lang == "ru"
            else f"🎙️ *Transcribed submission:*\n_{transcribed_text}_\n\n{i18n.get('exam_evaluating', lang)}"
        )
        eval_status = await message.answer(transcript_notice, parse_mode="Markdown")

        review = await evaluate_student_letter(task, transcribed_text, native_lang=lang)
        await state.update_data(last_review=review)

        # Учитываем проверку и обновляем серию занятий
        await db.increment_exam_quota(user_id)
        await db.update_daily_streak(user_id)

        await eval_status.edit_text(
            review,
            reply_markup=get_exam_result_keyboard(lang),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка при оценке голосового экзамена: {e}")
        err_msg = (
            "🪶 Ошибка при обработке аудио. Пожалуйста, отправь ответ текстом!"
            if lang == "ru"
            else "🪶 Error processing audio. Please submit your answer via text!"
        )
        await message.answer(err_msg)

@router.callback_query(F.data == "exam_voice_sample")
async def cb_voice_exam_sample(callback: CallbackQuery, state: FSMContext):
    """Синтез эталонного образца ответа (Musterlösung) носителем языка"""
    lang = await db.get_user_lang(callback.from_user.id)
    data = await state.get_data()
    review = data.get("last_review") or (callback.message.text or "")

    german_sample = extract_musterloesung_for_voice(review)
    if not german_sample:
        msg = "Не найден образец для озвучки" if lang == "ru" else "No sample text found"
        await callback.answer(msg, show_alert=True)
        return

    await callback.message.bot.send_chat_action(chat_id=callback.message.chat.id, action="record_voice")

    audio_bytes = await synthesize_speech(german_sample)
    if not audio_bytes:
        msg = "Не удалось синтезировать голос" if lang == "ru" else "Could not synthesize voice"
        await callback.answer(msg, show_alert=True)
        return

    voice_file = BufferedInputFile(audio_bytes, filename="musterloesung.mp3")
    caption = "🪶 *Идеальный эталонный ответ (Musterlösung):*" if lang == "ru" else "🪶 *Certified Model Answer (Musterlösung):*"

    await callback.message.answer_voice(
        voice=voice_file,
        caption=caption,
        parse_mode="Markdown"
    )
    mark_voice_sent(callback.from_user.id)
    await callback.answer()
