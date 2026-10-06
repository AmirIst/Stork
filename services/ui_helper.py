"""
Сервис управления отображением окон интерфейса Stork в Telegram.
Обеспечивает естественный и чистый UX:
1. В обычном режиме окна редактируются бесшовно на месте (edit_text), сохраняя чистоту чата.
2. Когда бот отправил голосовое сообщение, при следующем любом взаимодействии с окном
   (кнопки «Следующее слово», «Главное меню», «Показать перевод», «Оценка» и др.)
   старое окно выше аудиозаписи удаляется, а новое действие выводится ВНИЗУ чата.
"""
import logging
from typing import Set, Optional
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

# Множество ID пользователей, которым было отправлено голосовое сообщение ниже текущего окна
_USERS_WITH_PENDING_VOICE: Set[int] = set()

def mark_voice_sent(user_id: int):
    """Пометить, что пользователю отправлено голосовое сообщение ниже текущего окна"""
    _USERS_WITH_PENDING_VOICE.add(user_id)

def has_voice_pending(user_id: int) -> bool:
    """Проверить, было ли отправлено голосовое сообщение ниже текущего окна"""
    return user_id in _USERS_WITH_PENDING_VOICE

def clear_voice_pending(user_id: int):
    """Сбросить флаг ожидания переноса окна вниз"""
    _USERS_WITH_PENDING_VOICE.discard(user_id)

async def show_or_update_window(
    callback: CallbackQuery,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "Markdown",
    force_repost: bool = False
) -> Message:
    """
    Интеллектуальное обновление окна Stork:
    - Если ниже окна есть голосовые сообщения (или force_repost=True),
      удаляет старое окно выше голосовых и отправляет новое действие ВНИЗУ чата.
    - В обычном режиме быстро и без мерцания редактирует сообщение на месте (edit_text).
    """
    user_id = callback.from_user.id
    need_repost = force_repost or has_voice_pending(user_id)

    if need_repost:
        clear_voice_pending(user_id)
        try:
            await callback.message.delete()
        except Exception as e:
            logger.debug(f"Не удалось удалить предыдущее окно: {e}")

        return await callback.message.answer(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    else:
        try:
            return await callback.message.edit_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except Exception:
            return await callback.message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
