import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import db
from locales.manager import i18n
from services.ai_tutor import get_ai_tutor_reply
from keyboards.inline import get_back_to_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()

class AIConversationState(StatesGroup):
    in_conversation = State()

@router.callback_query(F.data == "menu_ai")
async def cb_enter_ai_mode(callback: CallbackQuery, state: FSMContext):
    """Вход в режим диалога с Аистом"""
    await state.set_state(AIConversationState.in_conversation)
    lang = await db.get_user_lang(callback.from_user.id)
    text = i18n.get("ai_tutor_welcome", lang)

    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_menu_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AIConversationState.in_conversation, F.text)
async def handle_ai_message(message: Message, state: FSMContext):
    """Обработка текстовых реплик ученика в режиме ИИ-собеседника"""
    if message.text.startswith("/"):
        # Если пришла команда, сбрасываем состояние диалога
        await state.clear()
        return

    lang = await db.get_user_lang(message.from_user.id)

    # Отправляем индикатор набора текста
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    reply = await get_ai_tutor_reply(message.text, native_lang=lang)

    await message.answer(
        reply,
        reply_markup=get_back_to_menu_keyboard(lang),
        parse_mode="Markdown"
    )
