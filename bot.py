import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import BOT_TOKEN
from database.db import init_db
from handlers import admin, common, workout, articles, cards, quiz, placement, exam, ai_chat, filters, voice, premium, verbs, sprechen, listening, roleplay, diagnostic
from services.reminder_service import run_daily_reminder_worker

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def setup_bot_commands(bot: Bot):
    """Регистрация команд в меню Telegram"""
    commands = [
        BotCommand(command="start", description="Запустить бота / Start"),
        BotCommand(command="menu", description="Главное меню / Main menu"),
        BotCommand(command="workout", description="Тренировка дня / Daily Workout"),
        BotCommand(command="test", description="Тест и готовность к Goethe B1 / Test"),
        BotCommand(command="lang", description="Сменить язык / Change language")
    ]
    await bot.set_my_commands(commands)

async def main():
    if not BOT_TOKEN:
        logger.error("ОШИБКА: BOT_TOKEN не указан в файле .env!")
        print("\nПожалуйста, укажите токен бота в файле .env (BOT_TOKEN=...)\n")
        return

    logger.info("Инициализация базы данных Stork...")
    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация маршрутизаторов (роутеров)
    dp.include_router(admin.router)
    dp.include_router(common.router)
    dp.include_router(workout.router)
    dp.include_router(diagnostic.router)
    dp.include_router(roleplay.router)
    dp.include_router(sprechen.router)
    dp.include_router(articles.router)
    dp.include_router(cards.router)
    dp.include_router(quiz.router)
    dp.include_router(placement.router)
    dp.include_router(exam.router)
    dp.include_router(verbs.router)
    dp.include_router(listening.router)
    dp.include_router(ai_chat.router)
    dp.include_router(filters.router)
    dp.include_router(voice.router)
    dp.include_router(premium.router)

    await setup_bot_commands(bot)

    # Запуск фонового планировщика ежедневных напоминаний
    reminder_task = asyncio.create_task(run_daily_reminder_worker(bot))

    logger.info("Бот Stork (Аист) успешно запущен и готов к работе!")
    
    # Удаляем вебхуки и запускаем polling с автоматическим переподключением
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        while True:
            try:
                await dp.start_polling(bot)
                break
            except (KeyboardInterrupt, SystemExit):
                logger.info("Получен сигнал остановки бота.")
                break
            except Exception as e:
                logger.error(f"Временный сбой соединения Telegram: {e}. Автоматическое переподключение через 3 секунды...")
                await asyncio.sleep(3)
    finally:
        reminder_task.cancel()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот Stork остановлен.")
