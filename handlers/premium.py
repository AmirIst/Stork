import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import db
from locales.manager import i18n
from keyboards.inline import get_premium_keyboard, get_back_to_menu_keyboard
from services.ui_helper import show_or_update_window

logger = logging.getLogger(__name__)
router = Router()

class PremiumPromoState(StatesGroup):
    waiting_code = State()

VALID_PROMO_CODES = {"STORKVIP", "STORK2026", "AMIR", "DEUTSCH", "FREEDOM"}

@router.callback_query(F.data == "menu_premium")
async def cb_menu_premium(callback: CallbackQuery, state: FSMContext):
    """Экран описания и подключения Stork Premium"""
    await state.clear()
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)
    is_active, until_date = await db.is_user_premium(user_id)

    if is_active and until_date:
        active_notice = i18n.get("premium_already_active", lang, until_date=until_date[:10])
        full_text = f"{active_notice}\n\n{i18n.get('premium_info', lang)}"
    else:
        full_text = i18n.get("premium_info", lang)

    await show_or_update_window(
        callback,
        full_text,
        reply_markup=get_premium_keyboard(lang, is_active=is_active),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "premium_trial")
async def cb_premium_trial(callback: CallbackQuery):
    """Активация бесплатного 7-дневного пробного периода Stork Premium"""
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)
    is_active, until_date = await db.is_user_premium(user_id)

    if is_active and until_date:
        text = i18n.get("premium_already_active", lang, until_date=until_date[:10])
    else:
        until_date = await db.activate_premium(user_id, days=7)
        text = i18n.get("premium_trial_activated", lang, until_date=until_date[:10])

    await show_or_update_window(
        callback,
        text,
        reply_markup=get_back_to_menu_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer("Premium активирован!" if lang == "ru" else "Premium activated!")

@router.callback_query(F.data == "premium_promo")
async def cb_premium_promo(callback: CallbackQuery, state: FSMContext):
    """Запрос на ввод промокода"""
    await state.set_state(PremiumPromoState.waiting_code)
    lang = await db.get_user_lang(callback.from_user.id)
    text = i18n.get("promo_prompt", lang)
    
    await show_or_update_window(
        callback,
        text,
        reply_markup=get_back_to_menu_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(PremiumPromoState.waiting_code, F.text)
async def handle_promo_code_input(message: Message, state: FSMContext):
    """Проверка и применение промокода"""
    if message.text.startswith("/"):
        await state.clear()
        return

    code = message.text.strip().upper()
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)

    if code in VALID_PROMO_CODES:
        until_date = await db.activate_premium(user_id, days=30)
        await state.clear()
        text = i18n.get("promo_success", lang, until_date=until_date[:10])
        await message.answer(text, reply_markup=get_back_to_menu_keyboard(lang), parse_mode="Markdown")
    else:
        text = i18n.get("promo_invalid", lang)
        await message.answer(text, reply_markup=get_back_to_menu_keyboard(lang), parse_mode="Markdown")

@router.callback_query(F.data == "premium_buy_stars")
async def cb_premium_buy_stars(callback: CallbackQuery):
    """Покупка Stork Premium через Telegram Stars"""
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)

    try:
        prices = [LabeledPrice(label="Stork Premium (30 дней)", amount=150)]
        title = "⭐️ Stork Premium (30 дней)" if lang == "ru" else "⭐️ Stork Premium (30 days)"
        description = (
            "Безлимитный ИИ-собеседник, проверка экзаменационных писем Goethe & Telc, приоритетный отклик."
            if lang == "ru"
            else "Unlimited AI conversation, Goethe & Telc exam review, priority response speed."
        )
        await callback.message.answer_invoice(
            title=title,
            description=description,
            payload=f"premium_30_{user_id}",
            currency="XTR",
            prices=prices,
            provider_token=""
        )
        await callback.answer()
    except Exception as e:
        logger.warning(f"Telegram Stars invoice warning: {e}. Предоставляем моментальную активацию для тестирования.")
        # Если Telegram Stars недоступен в среде бота без настроек платежей, активируем 30 дней для тестов
        until_date = await db.activate_premium(user_id, days=30)
        fallback_msg = (
            f"🎉 *Тестовый режим:* Подписка *Stork Premium ⭐️* успешно оформлена на 30 дней до *{until_date[:10]}*!"
            if lang == "ru"
            else f"🎉 *Demo mode:* Subscription *Stork Premium ⭐️* activated for 30 days until *{until_date[:10]}*!"
        )
        await show_or_update_window(
            callback,
            fallback_msg,
            reply_markup=get_back_to_menu_keyboard(lang),
            parse_mode="Markdown"
        )
        await callback.answer()

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Подтверждение готовности принять оплату Telegram Stars"""
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """Обработка успешной оплаты Telegram Stars"""
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)
    until_date = await db.activate_premium(user_id, days=30)
    
    text = (
        f"🎉 *Оплата 150 Stars прошла успешно!*\n\nТвой тариф *Stork Premium ⭐️* активен до *{until_date[:10]}*. Спасибо за поддержку проекта!"
        if lang == "ru"
        else f"🎉 *Payment of 150 Stars confirmed!*\n\nYour *Stork Premium ⭐️* plan is active until *{until_date[:10]}*. Thank you for supporting Stork!"
    )
    await message.answer(text, reply_markup=get_back_to_menu_keyboard(lang), parse_mode="Markdown")
