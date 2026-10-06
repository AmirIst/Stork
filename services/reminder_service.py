import asyncio
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Bot
from database import db
from locales.manager import i18n
from keyboards.inline import get_reminder_keyboard

logger = logging.getLogger(__name__)

async def send_daily_reminders_batch(bot: Bot, force: bool = False) -> int:
    """
    Отправляет напоминания о сохранении серии занятий тем ученикам,
    которые еще не открывали сегодня тренировки.
    """
    now_utc = datetime.now(timezone.utc)
    today_str = now_utc.strftime("%Y-%m-%d")
    
    # Московское / европейское вечернее время (UTC+3)
    local_hour = (now_utc.hour + 3) % 24

    # Напоминаем только в вечернее окно (19:00 - 21:00) или если передан force=True
    if not force and not (19 <= local_hour <= 21):
        return 0

    users_to_remind = await db.get_users_for_daily_reminder(today_str)
    if not users_to_remind:
        return 0

    logger.info(f"Запуск отправки вечерних напоминаний для {len(users_to_remind)} пользователей...")
    sent_count = 0

    for user in users_to_remind:
        user_id = user["user_id"]
        lang = user.get("native_lang") or "ru"
        streak = user.get("streak") or 0

        text = i18n.get("reminder_text", lang, streak=streak)
        kb = get_reminder_keyboard(lang)

        try:
            await bot.send_message(chat_id=user_id, text=text, reply_markup=kb, parse_mode="Markdown")
            await db.mark_user_reminded(user_id, today_str)
            sent_count += 1
            await asyncio.sleep(0.05)  # Защита от Telegram rate limit
        except Exception as e:
            logger.warning(f"Не удалось отправить напоминание пользователю {user_id}: {e}")
            # Помечаем, чтобы не застревать на недоступных пользователях
            await db.mark_user_reminded(user_id, today_str)

    logger.info(f"Вечерние напоминания успешно отправлены: {sent_count} сообщений.")
    return sent_count

async def run_daily_reminder_worker(bot: Bot):
    """
    Фоновый воркер, проверяющий расписание каждые 30 минут.
    """
    logger.info("Фоновый планировщик напоминаний Stork запущен.")
    while True:
        try:
            await send_daily_reminders_batch(bot)
        except Exception as e:
            logger.error(f"Ошибка в фоновом воркере напоминаний: {e}")
        # Проверка каждые 30 минут
        await asyncio.sleep(1800)
