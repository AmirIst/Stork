import logging
from datetime import datetime, timezone
import aiosqlite
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import ADMIN_IDS
from database import db
from database.db import DB_PATH
from locales.manager import i18n
from keyboards.inline import (
    get_premium_keyboard,
    get_premium_plans_keyboard,
    get_referral_keyboard,
    get_back_to_menu_keyboard,
)
from services.ui_helper import show_or_update_window
from premium_config import (
    FREE_TRIAL_DAYS,
    PROMO_CODES,
    PREMIUM_PLANS,
    REFERRAL_CONFIG,
    get_plan_by_id,
    get_plan_price,
)

logger = logging.getLogger(__name__)
router = Router()

class PremiumPromoState(StatesGroup):
    waiting_code = State()

@router.callback_query(F.data == "menu_premium")
async def cb_menu_premium(callback: CallbackQuery, state: FSMContext):
    """Экран описания и подключения Stork Premium"""
    await state.clear()
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)
    is_active, until_date = await db.is_user_premium(user_id)
    trial_available = await db.is_trial_available(user_id)
    ref_stats = await db.get_referral_stats(user_id)

    if is_active and until_date:
        if until_date == "lifetime":
            active_notice = i18n.get("premium_lifetime_active", lang)
            trial_available = False
        else:
            active_notice = i18n.get("premium_already_active", lang, until_date=until_date[:10])
        full_text = f"{active_notice}\n\n{i18n.get('premium_info', lang)}"
    else:
        full_text = i18n.get("premium_info", lang)

    if ref_stats["has_discount"]:
        discount_badge = (
            "\n\n🔥 *Твой статус:* открыта скидка 50% на тариф на 1 месяц за 10 приглашенных друзей!"
            if lang == "ru"
            else "\n\n🔥 *Your status:* 50% discount unlocked for 1-month plan thanks to 10 referrals!"
        )
        full_text += discount_badge

    await show_or_update_window(
        callback,
        full_text,
        reply_markup=get_premium_keyboard(
            lang,
            is_active=is_active,
            trial_available=trial_available,
            has_discount=ref_stats["has_discount"]
        ),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "premium_trial")
async def cb_premium_trial(callback: CallbackQuery):
    """Активация бесплатного пробного периода Stork Premium (строго 1 раз)"""
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)

    success, status, until_date = await db.activate_trial_if_eligible(user_id, days=FREE_TRIAL_DAYS)

    if success and until_date:
        text = i18n.get("premium_trial_activated", lang, until_date=until_date[:10])
        toast = "7 дней Premium активировано!" if lang == "ru" else "7 days Premium activated!"
    else:
        text = i18n.get("premium_trial_already_used", lang)
        toast = "Пробный период уже использован" if lang == "ru" else "Free trial already used"

    await show_or_update_window(
        callback,
        text,
        reply_markup=get_back_to_menu_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer(toast)

@router.callback_query(F.data == "premium_plans")
async def cb_premium_plans(callback: CallbackQuery):
    """Витрина тарифов Stork Premium (Telegram Stars)"""
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)
    ref_stats = await db.get_referral_stats(user_id)
    has_discount = ref_stats["has_discount"]

    text = i18n.get("premium_plans_title", lang)
    if has_discount:
        discount_info = (
            "\n\n🔥 *У тебя действует скидка 50% на месячную подписку за 10 друзей!*"
            if lang == "ru"
            else "\n\n🔥 *50% discount applied to the 1-month plan for your 10 referrals!*"
        )
        text += discount_info

    await show_or_update_window(
        callback,
        text,
        reply_markup=get_premium_plans_keyboard(lang, has_discount=has_discount),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("buy_plan:"))
async def cb_buy_plan(callback: CallbackQuery):
    """Выставление счета Telegram Stars за выбранный тариф"""
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)
    plan_id = callback.data.split(":")[1]
    plan = get_plan_by_id(plan_id)

    if not plan:
        await callback.answer("Тариф не найден" if lang == "ru" else "Plan not found", show_alert=True)
        return

    ref_stats = await db.get_referral_stats(user_id)
    price = get_plan_price(plan, has_discount=ref_stats["has_discount"])
    days = plan["days"]
    plan_title = plan["title_ru"] if lang == "ru" else plan["title_en"]

    title = f"⭐️ Stork Premium ({plan_title})"
    description = (
        "Безлимитный немецкий 24/7: симуляторы Goethe & telc B1, 3 000 слов, живое общение голосом и проверка писем."
        if lang == "ru"
        else "Unlimited German 24/7: Goethe & telc B1 simulators, 3,000 words, live voice practice & writing review."
    )

    try:
        prices = [LabeledPrice(label=f"Stork Premium ({plan_title})", amount=price)]
        await callback.message.answer_invoice(
            title=title,
            description=description,
            payload=f"premium_{plan_id}_{user_id}",
            currency="XTR",
            prices=prices,
            provider_token=""
        )
        await callback.answer()
    except Exception as e:
        if plan.get("is_lifetime") or plan_id == "plan_lifetime":
            await db.set_user_lifetime_vip(user_id, is_vip=True)
            async with aiosqlite.connect(DB_PATH) as database:
                await database.execute("UPDATE users SET subscription_type = 'lifetime' WHERE user_id = ?", (user_id,))
                await database.commit()
            until_date = "lifetime"
            fallback_msg = (
                f"🎉 *Тестовый режим:* Тариф *{plan_title}* успешно активирован бессрочно!"
                if lang == "ru"
                else f"🎉 *Demo mode:* Plan *{plan_title}* successfully activated forever!"
            )
        else:
            until_date = await db.activate_premium(user_id, days=days)
            sub_type = "1m" if days == 30 else ("3m" if days == 90 else ("1y" if days >= 365 else "other"))
            async with aiosqlite.connect(DB_PATH) as database:
                await database.execute("UPDATE users SET subscription_type = ? WHERE user_id = ?", (sub_type, user_id))
                await database.commit()
            fallback_msg = (
                f"🎉 *Тестовый режим:* Подписка *Stork Premium ⭐️ ({plan_title})* активирована на *{days} дн.* до *{until_date[:10]}*!"
                if lang == "ru"
                else f"🎉 *Demo mode:* Subscription *Stork Premium ⭐️ ({plan_title})* activated for *{days} days* until *{until_date[:10]}*!"
            )
        await show_or_update_window(
            callback,
            fallback_msg,
            reply_markup=get_back_to_menu_keyboard(lang),
            parse_mode="Markdown"
        )
        await callback.answer()

@router.callback_query(F.data == "menu_referrals")
async def cb_menu_referrals(callback: CallbackQuery):
    """Экран реферальной программы: ссылка, статистика и правила"""
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)
    ref_stats = await db.get_referral_stats(user_id)

    try:
        bot_user = await callback.bot.get_me()
        bot_username = bot_user.username or "stork_learn_german_bot"
    except Exception:
        bot_username = "stork_learn_german_bot"

    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    if ref_stats["has_discount"]:
        discount_status = "Разблокирована! (-50% на месяц) 🔥" if lang == "ru" else "Unlocked! (50% OFF monthly) 🔥"
    else:
        discount_status = (
            f"Заблокирована (осталось пригласить {ref_stats['needed_for_milestone']} чел.)"
            if lang == "ru"
            else f"Locked (invite {ref_stats['needed_for_milestone']} more)"
        )

    text = i18n.get(
        "referrals_title",
        lang,
        count=ref_stats["count"],
        days_earned=ref_stats["days_earned"],
        discount_status=discount_status,
        ref_link=ref_link
    )

    await show_or_update_window(
        callback,
        text,
        reply_markup=get_referral_keyboard(ref_link, lang, has_discount=ref_stats["has_discount"]),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "premium_promo")
async def cb_premium_promo(callback: CallbackQuery, state: FSMContext):
    """Запрос на ввод секретного промокода"""
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
    """Проверка и применение промокода с контролем одноразовости"""
    if message.text.startswith("/"):
        await state.clear()
        return

    code = message.text.strip().upper()
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)

    success, status, days, until_date = await db.activate_promo_code(user_id, code)

    if success and until_date:
        await state.clear()
        text = i18n.get("promo_success_dynamic", lang, days=days, until_date=until_date[:10])
        await message.answer(text, reply_markup=get_back_to_menu_keyboard(lang), parse_mode="Markdown")
    elif status == "already_used":
        text = i18n.get("promo_already_used", lang)
        await message.answer(text, reply_markup=get_back_to_menu_keyboard(lang), parse_mode="Markdown")
    else:
        text = i18n.get("promo_invalid", lang)
        await message.answer(text, reply_markup=get_back_to_menu_keyboard(lang), parse_mode="Markdown")

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Подтверждение готовности принять оплату Telegram Stars"""
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """Обработка успешной оплаты Telegram Stars"""
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)
    payload = message.successful_payment.invoice_payload or ""

    days = 30
    plan_title = "1 месяц" if lang == "ru" else "1 month"
    is_lifetime = False
    actual_plan_id = "plan_30d"
    sub_type = "1m"

    if payload.startswith("premium_"):
        raw_part = payload[len("premium_"):]
        extracted_plan_id = raw_part.rsplit("_", 1)[0]
        plan = get_plan_by_id(extracted_plan_id)
        if plan:
            actual_plan_id = extracted_plan_id
            days = plan["days"]
            plan_title = plan["title_ru"] if lang == "ru" else plan["title_en"]
            if plan.get("is_lifetime") or actual_plan_id == "plan_lifetime":
                is_lifetime = True
                sub_type = "lifetime"
            elif days == 30:
                sub_type = "1m"
            elif days == 90:
                sub_type = "3m"
            elif days >= 365:
                sub_type = "1y"
            else:
                sub_type = "other"

    stars_amount = message.successful_payment.total_amount

    # 1. Запись платежа в историю
    try:
        await db.record_payment(
            user_id=user_id,
            plan_id=actual_plan_id,
            plan_title=plan_title,
            stars_amount=stars_amount,
            currency="XTR",
            payment_method="telegram_stars"
        )
    except Exception as e:
        logger.error(f"Ошибка сохранения платежа: {e}")

    # 2. Обновление статуса в таблице users
    if is_lifetime:
        await db.set_user_lifetime_vip(user_id, is_vip=True)
        async with aiosqlite.connect(DB_PATH) as database:
            await database.execute("UPDATE users SET subscription_type = 'lifetime' WHERE user_id = ?", (user_id,))
            await database.commit()
        text = (
            f"🎉 *Оплата {stars_amount} Stars прошла успешно!*\n\n"
            f"Твой статус *{plan_title}* активирован бессрочно! Полный безлимитный доступ ко всем функциям навсегда. "
            f"Спасибо за поддержку проекта!"
            if lang == "ru"
            else f"🎉 *Payment of {stars_amount} Stars confirmed!*\n\n"
            f"Your *{plan_title}* plan is active forever! Full unlimited access to all features. "
            f"Thank you for supporting Stork!"
        )
    else:
        until_date = await db.activate_premium(user_id, days=days)
        async with aiosqlite.connect(DB_PATH) as database:
            await database.execute("UPDATE users SET subscription_type = ? WHERE user_id = ?", (sub_type, user_id))
            await database.commit()
        text = (
            f"🎉 *Оплата {stars_amount} Stars прошла успешно!*\n\n"
            f"Твой тариф *Stork Premium ⭐️ ({plan_title})* активен на *{days} дн.* до *{until_date[:10]}*. "
            f"Спасибо за поддержку проекта!"
            if lang == "ru"
            else f"🎉 *Payment of {stars_amount} Stars confirmed!*\n\n"
            f"Your *Stork Premium ⭐️ ({plan_title})* plan is active for *{days} days* until *{until_date[:10]}*. "
            f"Thank you for supporting Stork!"
        )

    # 3. Мгновенное оповещение администраторов (только тем, у кого включены уведомления)
    username_str = f"@{message.from_user.username}" if message.from_user.username else (message.from_user.full_name or "Без имени")
    eur_approx = round(stars_amount * 0.02, 2)
    admin_alert = (
        f"🔔 *Новая оплата в Stork Bot!*\n\n"
        f"👤 Пользователь: {username_str}\n"
        f"🆔 User ID: `{user_id}`\n"
        f"📦 Тариф: *{plan_title}*\n"
        f"⭐️ Сумма: *{stars_amount} Stars* (~{eur_approx} €)\n"
        f"📅 Время: {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}"
    )
    notify_admin_ids = await db.get_notification_admin_ids()
    for admin_id in notify_admin_ids:
        try:
            await message.bot.send_message(admin_id, admin_alert, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление админу {admin_id}: {e}")

    await message.answer(text, reply_markup=get_back_to_menu_keyboard(lang), parse_mode="Markdown")
