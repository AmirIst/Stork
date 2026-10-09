import os
import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional
from aiohttp import web
from aiogram import Bot

from database import db
from config import SUPER_ADMIN_IDS
from locales.manager import i18n

logger = logging.getLogger(__name__)

def verify_tribute_signature(body_bytes: bytes, signature_header: Optional[str], api_key: Optional[str]) -> bool:
    """Проверяет HMAC-SHA256 подпись вебхука Tribute"""
    if not api_key:
        # Если API-ключ не настроен, пропускаем для удобства первоначальной отладки
        return True
    if not signature_header:
        return False
    try:
        expected = hmac.new(api_key.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected.lower(), signature_header.lower())
    except Exception as e:
        logger.error(f"Ошибка проверки подписи Tribute: {e}")
        return False

def determine_plan_days(product_title: str) -> int:
    """Определяет количество дней премиума по названию товара в Tribute"""
    t = product_title.lower()
    if "вечный" in t or "lifetime" in t or "vip" in t:
        return 36500
    if "год" in t or "year" in t or "365" in t:
        return 365
    if "90" in t or "3 месяц" in t or "3 month" in t:
        return 90
    if "30" in t or "1 месяц" in t or "1 month" in t or "месяц" in t:
        return 30
    if "7" in t or "недел" in t or "week" in t:
        return 7
    return 30

def handle_tribute_webhook_factory(bot: Bot):
    """Фабрика обработчика вебхуков Tribute для aiohttp"""
    async def handler(request: web.Request) -> web.Response:
        api_key = os.getenv("TRIBUTE_API_KEY", "").strip()
        body_bytes = await request.read()
        sig = request.headers.get("trbt-signature") or request.headers.get("Trbt-Signature")

        if api_key and not verify_tribute_signature(body_bytes, sig, api_key):
            logger.warning("Отклонен вебхук Tribute: неверная HMAC-подпись")
            return web.Response(status=401, text="Invalid signature")

        try:
            data = json.loads(body_bytes.decode("utf-8"))
        except Exception as e:
            logger.error(f"Некорректный JSON в вебхуке Tribute: {e}")
            return web.Response(status=400, text="Invalid JSON")

        logger.info(f"Получен вебхук от Tribute: {data}")

        # Обрабатываем событие оплаты
        event_name = data.get("name") or data.get("event") or ""
        payload = data.get("payload") or data

        # Идентификатор пользователя в Telegram
        user_id = payload.get("telegram_user_id") or payload.get("user_id") or payload.get("telegram_id")
        if not user_id:
            logger.warning(f"В вебхуке Tribute отсутствует telegram_user_id: {payload}")
            return web.Response(status=200, text="OK (no user_id)")

        try:
            user_id = int(user_id)
        except Exception:
            return web.Response(status=200, text="OK (invalid user_id)")

        # Параметры товара
        product_name = payload.get("product_name") or payload.get("title") or payload.get("product_title") or "Stork Premium"
        amount = payload.get("amount") or payload.get("price") or 0
        currency = payload.get("currency") or "EUR"

        days = determine_plan_days(str(product_name))

        # Активация подписки в БД
        try:
            if days >= 36500:
                await db.set_user_lifetime_vip(user_id, is_vip=True)
                period_text = "навсегда (Вечный VIP) 👑"
            else:
                until_str = await db.activate_premium(user_id, days=days)
                period_text = f"на *{days} дней* (до {until_str[:10]}) 🚀"

            # Запись в историю платежей
            await db.record_payment(
                user_id=user_id,
                plan_id=f"tribute_{days}d",
                plan_title=str(product_name),
                stars_amount=int(amount) if isinstance(amount, (int, float)) else 0,
                currency=str(currency),
                payment_method="card_tribute"
            )

            # Сообщение пользователю в Telegram
            user_msg = (
                f"🎉 *Оплата успешно подтверждена!*\n\n"
                f"Твой доступ *Stork Premium* активирован {period_text}.\n\n"
                f"Все ограничения сняты: общайся с Аистом без лимитов, тренируй устную речь голосом "
                f"и готовься к экзаменам!\n\n"
                f"Viel Erfolg beim Deutschlernen! 🇩🇪🪶"
            )
            await bot.send_message(chat_id=user_id, text=user_msg, parse_mode="Markdown")
            logger.info(f"Премиум успешно выдан пользователю {user_id} через авто-вебхук Tribute.")

            # Уведомление администраторам
            admin_msg = (
                f"💰 *Новая авто-оплата через Tribute!*\n\n"
                f"• Покупатель: `{user_id}`\n"
                f"• Товар: *{product_name}*\n"
                f"• Сумма: *{amount} {currency}*\n"
                f"• Начислено: *{days} дн.*"
            )
            for adm in SUPER_ADMIN_IDS:
                try:
                    await bot.send_message(chat_id=adm, text=admin_msg, parse_mode="Markdown")
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Ошибка при обработке активации через Tribute: {e}")

        return web.Response(status=200, text="OK")

    return handler

async def start_tribute_web_server(bot: Bot, port: int):
    """Запускает HTTP-сервер aiohttp для приема вебхуков Tribute на порту $PORT"""
    app = web.Application()
    app.router.add_post("/webhook/tribute", handle_tribute_webhook_factory(bot))
    
    async def health(_req):
        return web.Response(text="Stork Bot Tribute Webhook is Running OK")

    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"HTTP-сервер вебхуков Tribute запущен на 0.0.0.0:{port}!")
    return runner
