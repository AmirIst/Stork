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
from handlers import common, articles, cards, quiz, exam, ai_chat, filters, voice

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
    dp.include_router(common.router)
    dp.include_router(articles.router)
    dp.include_router(cards.router)
    dp.include_router(quiz.router)
    dp.include_router(exam.router)
    dp.include_router(ai_chat.router)
    dp.include_router(filters.router)
    dp.include_router(voice.router)

    await setup_bot_commands(bot)

    logger.info("Бот Stork (Аист) успешно запущен и готов к работе!")
    
    # Удаляем вебхуки и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот Stork остановлен.")
