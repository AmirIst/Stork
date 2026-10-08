import io
import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import db
from locales.manager import i18n
from services.ai_tutor import get_ai_tutor_reply, get_ai_tutor_voice_reply
from services.tts import synthesize_speech, extract_german_for_voice
from keyboards.inline import (
    get_back_to_menu_keyboard,
    get_ai_dialog_welcome_keyboard,
    get_ai_in_chat_keyboard,
    get_quota_exceeded_keyboard
)
from services.ui_helper import show_or_update_window

logger = logging.getLogger(__name__)
router = Router()

class AIConversationState(StatesGroup):
    in_conversation = State()

@router.callback_query(F.data == "menu_ai")
async def cb_enter_ai_mode(callback: CallbackQuery, state: FSMContext):
    """Вход в режим диалога с Аистом с проверкой наличия предыдущей истории"""
    await state.set_state(AIConversationState.in_conversation)
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)
    has_history = await db.has_chat_history(user_id)

    if has_history:
        text = i18n.get("ai_tutor_resume_prompt", lang)
    else:
        text = i18n.get("ai_tutor_welcome", lang)

    await show_or_update_window(
        callback,
        text,
        reply_markup=get_ai_dialog_welcome_keyboard(lang, has_history=has_history),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "ai_resume")
async def cb_ai_resume(callback: CallbackQuery, state: FSMContext):
    """Продолжить беседу с того же места"""
    await state.set_state(AIConversationState.in_conversation)
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)
    history = await db.get_chat_history(user_id, limit=2)
    
    last_context_hint = ""
    if history:
        last_turn = history[-1]["message"]
        # Обрезаем длинный текст для превью
        short_preview = (last_turn[:90] + "...") if len(last_turn) > 90 else last_turn
        if lang == "ru":
            last_context_hint = f"\n\n💬 *Последнее сообщение:* _{short_preview}_"
        else:
            last_context_hint = f"\n\n💬 *Last message:* _{short_preview}_"

    if lang == "ru":
        msg = f"▶️ *Продолжаем беседу!* Я помню всё, о чем мы говорили.{last_context_hint}\n\nНапиши мне что-нибудь:"
    else:
        msg = f"▶️ *Resuming conversation!* I remember our previous topic.{last_context_hint}\n\nType your message below:"

    await show_or_update_window(
        callback,
        msg,
        reply_markup=get_ai_in_chat_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "ai_clear")
async def cb_ai_clear(callback: CallbackQuery, state: FSMContext):
    """Очистить историю диалога и начать с чистого листа"""
    user_id = callback.from_user.id
    await db.clear_chat_history(user_id)
    await state.set_state(AIConversationState.in_conversation)
    lang = await db.get_user_lang(user_id)
    
    text = i18n.get("ai_history_cleared", lang)
    await show_or_update_window(
        callback,
        text,
        reply_markup=get_ai_dialog_welcome_keyboard(lang, has_history=False),
        parse_mode="Markdown"
    )
    await callback.answer("Диалог очищен!" if lang == "ru" else "Chat cleared!")

@router.callback_query(F.data == "ai_finish")
async def cb_ai_finish(callback: CallbackQuery, state: FSMContext):
    """Завершение текущей разговорной сессии с фиксацией прогресса"""
    await state.clear()
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)
    stats = await db.get_user_stats(user_id)

    if lang == "ru":
        text = (
            "🏁 *Разговорная практика завершена!*\n\n"
            f"🔥 Твой текущий ударный режим (страйк): *{stats['streak']} дн.*\n"
            "💬 Отличная работа! Все разобранные фразы и слова сохранены в твоем профиле.\n\n"
            "Возвращайся к диалогу в любое время или закрепи лексику в карточках 👇"
        )
    else:
        text = (
            "🏁 *Speaking practice completed!*\n\n"
            f"🔥 Your current streak: *{stats['streak']} days*\n"
            "💬 Great job! All practiced vocabulary and insights are saved in your profile.\n\n"
            "Resume your conversation anytime or reinforce vocabulary with flashcards 👇"
        )

    await show_or_update_window(
        callback,
        text,
        reply_markup=get_ai_dialog_welcome_keyboard(lang, has_history=True),
        parse_mode="Markdown"
    )
    await callback.answer("Сессия завершена!" if lang == "ru" else "Session finished!")

@router.message(AIConversationState.in_conversation, F.text)
async def handle_ai_message(message: Message, state: FSMContext):
    """Обработка текстовых реплик с сохранением контекста и минимальной задержкой"""
    if message.text.startswith("/"):
        # Если пришла команда, сбрасываем состояние диалога
        await state.clear()
        return

    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)

    # Проверяем дневной лимит бесплатных запросов
    allowed, count, limit = await db.check_ai_quota(user_id)
    if not allowed:
        text = i18n.get("ai_quota_exceeded", lang, count=count, limit=limit)
        await message.answer(
            text,
            reply_markup=get_quota_exceeded_keyboard(lang),
            parse_mode="Markdown"
        )
        return

    # Мгновенно отправляем индикатор набора текста для идеального отклика
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    # Получаем последние 6 сообщений контекста
    history = await db.get_chat_history(user_id, limit=6)

    # Выполняем высокоскоростной запрос через пул соединений
    reply = await get_ai_tutor_reply(message.text, native_lang=lang, history=history)

    # Учитываем использование квоты и обновляем серию занятий
    await db.increment_ai_quota(user_id)
    await db.update_daily_streak(user_id)

    # Сохраняем ход беседы в базу данных
    await db.add_chat_message(user_id, "user", message.text)
    clean_model_reply = reply.replace("🪶 *Stork:*\n\n", "").strip()
    await db.add_chat_message(user_id, "model", clean_model_reply)

    await message.answer(
        reply,
        reply_markup=get_ai_in_chat_keyboard(lang),
        parse_mode="Markdown"
    )

@router.message(AIConversationState.in_conversation, F.voice)
@router.message(StateFilter(None), F.voice)
async def handle_ai_voice(message: Message, state: FSMContext):
    """Обработка голосовых сообщений ученика с анализом речи и голосовым ответом"""
    await state.set_state(AIConversationState.in_conversation)
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)

    # Проверяем дневной лимит бесплатных запросов
    allowed, count, limit = await db.check_ai_quota(user_id)
    if not allowed:
        text = i18n.get("ai_quota_exceeded", lang, count=count, limit=limit)
        await message.answer(
            text,
            reply_markup=get_quota_exceeded_keyboard(lang),
            parse_mode="Markdown"
        )
        return

    # Информируем пользователя о прослушивании
    await message.bot.send_chat_action(chat_id=message.chat.id, action="record_voice")

    try:
        # Скачиваем голосовой файл Telegram
        file_info = await message.bot.get_file(message.voice.file_id)
        voice_stream = io.BytesIO()
        await message.bot.download_file(file_info.file_path, destination=voice_stream)
        audio_bytes = voice_stream.getvalue()

        # История диалога
        history = await db.get_chat_history(user_id, limit=6)

        # Обработка через Gemini с распознаванием и анализом
        reply = await get_ai_tutor_voice_reply(audio_bytes, mime_type="audio/ogg", native_lang=lang, history=history)

        # Учитываем использование квоты и обновляем серию занятий
        await db.increment_ai_quota(user_id)
        await db.update_daily_streak(user_id)

        # Сохранение в историю
        clean_model_reply = reply.replace("🪶 *Stork:*\n\n", "").strip()
        await db.add_chat_message(user_id, "user", "[🎙️ Голосовое сообщение]")
        await db.add_chat_message(user_id, "model", clean_model_reply)

        # Отправка подробного текстового разбора с кнопкой озвучки
        await message.answer(
            reply,
            reply_markup=get_ai_in_chat_keyboard(lang),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка обработки голосового сообщения: {e}")
        err_msg = (
            "🪶 Не удалось обработать аудио. Попробуй еще раз или напиши текстом!"
            if lang == "ru"
            else "🪶 Could not process audio. Please try again or type a text message!"
        )
        await message.answer(err_msg)

