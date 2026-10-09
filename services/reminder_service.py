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

_last_backup_date = ""

async def check_and_send_daily_backup(bot: Bot, force: bool = False) -> bool:
    """
    Автоматическая ежедневная выгрузка базы данных в резервный канал или супер-админу.
    Запускается ночью (03:00 - 05:00 UTC) 1 раз в сутки.
    """
    global _last_backup_date
    import os
    from config import SUPER_ADMIN_IDS
    from aiogram.types import FSInputFile

    now_utc = datetime.now(timezone.utc)
    today_str = now_utc.strftime("%Y-%m-%d")

    if not force:
        if _last_backup_date == today_str:
            return False
        if not (3 <= now_utc.hour <= 5):
            return False

    db_chat = await db.get_system_setting("backup_chat_id")
    backup_chat_raw = (db_chat or os.getenv("BACKUP_CHAT_ID", "")).strip()
    target_chat = int(backup_chat_raw) if (backup_chat_raw and backup_chat_raw.lstrip("-").isdigit()) else SUPER_ADMIN_IDS[0]

    try:
        logger.info(f"Формирование автоматического резервного бэкапа для чата {target_chat}...")
        backup_path = await db.export_database_backup()
        backup_filename = os.path.basename(backup_path)
        size_kb = round(os.path.getsize(backup_path) / 1024, 1)

        input_file = FSInputFile(backup_path, filename=backup_filename)
        caption = (
            f"📦 *Автоматический суточный бэкап Stork*\n\n"
            f"• Файл: `{backup_filename}`\n"
            f"• Размер: *{size_kb} КБ*\n"
            f"• Дата выгрузки: *{now_utc.strftime('%d.%m.%Y %H:%M UTC')}*\n"
            f"• Источник: *Turso Cloud*\n\n"
            f"Резервная копия сформирована планировщиком без прерывания работы бота."
        )
        await bot.send_document(chat_id=target_chat, document=input_file, caption=caption, parse_mode="Markdown")
        _last_backup_date = today_str
        logger.info(f"Автоматический бэкап успешно отправлен в {target_chat}.")

        try:
            if os.path.exists(backup_path) and "stork_backup_" in backup_path:
                os.remove(backup_path)
        except Exception:
            pass
        return True
    except Exception as e:
        logger.error(f"Ошибка автоматической выгрузки бэкапа: {e}")
        return False

async def run_daily_reminder_worker(bot: Bot):
    """
    Фоновый воркер, проверяющий расписание каждые 30 минут:
    1. Вечерние напоминания ученикам (сохранение серии занятий).
    2. Ночная авто-выгрузка бэкапа базы данных.
    """
    logger.info("Фоновый планировщик напоминаний и авто-бэкапов Stork запущен.")
    while True:
        try:
            await send_daily_reminders_batch(bot)
            await check_and_send_daily_backup(bot)
        except Exception as e:
            logger.error(f"Ошибка в фоновом воркере напоминаний/бэкапов: {e}")
        # Проверка каждые 30 минут
        await asyncio.sleep(1800)
