import os
import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from database import db
from locales.manager import i18n
from keyboards.inline import (
    get_main_menu_keyboard,
    get_language_keyboard,
    get_onboarding_language_keyboard,
    get_onboarding_welcome_keyboard,
    get_back_to_menu_keyboard,
    get_stats_keyboard,
    get_achievements_keyboard,
    get_training_hub_keyboard,
    get_vocab_hub_keyboard,
    get_exams_hub_keyboard,
    get_settings_hub_keyboard
)
from services.ui_helper import show_or_update_window
from premium_config import is_lifetime_vip_in_config

logger = logging.getLogger(__name__)
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Команда /start: приветствие и инициализация пользователя"""
    await state.clear()
    
    # Проверяем реферальный аргумент (например, /start ref_123456)
    ref_arg = None
    parts = (message.text or "").split()
    if len(parts) > 1 and parts[1].startswith("ref_"):
        ref_arg = parts[1].replace("ref_", "")

    user = await db.get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    lang = user["native_lang"]

    if user.get("is_new") and ref_arg:
        try:
            inviter_id = int(ref_arg)
            if inviter_id != message.from_user.id:
                ref_res = await db.register_referral(inviter_id, message.from_user.id)
                if ref_res and message.bot:
                    try:
                        inv_lang = await db.get_user_lang(inviter_id)
                        if ref_res.get("milestone_hit"):
                            notif = (
                                "🔥 *Супер-бонус реферальной программы!*\n\n"
                                "По твоей ссылке пришел 10-й друг! 🎉\n"
                                "Тебе начислен супер-бонус: *+5 дней* (суммарно *15 дней* премиума за 10 человек) "
                                "и навсегда открыта *скидка 50%* на месячный Stork Premium! 👑"
                                if inv_lang == "ru" else
                                "🔥 *Referral Milestone Reached!*\n\n"
                                "Your 10th friend just joined! 🎉\n"
                                "You received a super-bonus: *+5 days* (total *15 days* of Premium for 10 friends) "
                                "and unlocked a lifetime *50% discount* on monthly Stork Premium! 👑"
                            )
                        else:
                            cnt = ref_res.get("total_referrals", 1)
                            notif = (
                                f"🎉 *Новый друг в Stork!*\n\n"
                                f"По твоей ссылке зарегистрировался новый ученик! Начислен *+1 день Stork Premium* ⭐️\n"
                                f"Всего приглашено: *{cnt}/10*. Пригласи 10 друзей, чтобы получить супер-бонус и скидку 50%!"
                                if inv_lang == "ru" else
                                f"🎉 *New friend in Stork!*\n\n"
                                f"Someone just joined via your link! You received *+1 day of Stork Premium* ⭐️\n"
                                f"Total invited: *{cnt}/10*. Invite 10 friends to unlock super-bonus and 50% discount!"
                            )
                        await message.bot.send_message(inviter_id, notif, parse_mode="Markdown")
                    except Exception as e:
                        logger.info(f"Could not send referral notification to {inviter_id}: {e}")
        except ValueError:
            pass

    lang_selected = bool(user.get("lang_selected", 0))

    if not lang_selected:
        intro_caption = (
            "👋 *Welcome to Stork!* 🇩🇪🪶\n"
            "Your AI mentor for learning German.\n\n"
            "👋 *Добро пожаловать в Stork!* 🇩🇪🪶\n"
            "Твой ИИ-наставник для изучения немецкого языка.\n\n"
            "🌐 *Please select your language / Пожалуйста, выбери язык:*"
        )
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logo.jpg")
        kb = get_onboarding_language_keyboard()
        if os.path.exists(logo_path):
            await message.answer_photo(
                photo=FSInputFile(logo_path),
                caption=intro_caption,
                reply_markup=kb,
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                text=intro_caption,
                reply_markup=kb,
                parse_mode="Markdown"
            )
        return

    workout_done = await db.is_daily_workout_completed(message.from_user.id)
    text = i18n.get("welcome", lang, name=message.from_user.first_name or "Freund")
    await message.answer(text, reply_markup=get_main_menu_keyboard(lang, workout_done=workout_done), parse_mode="Markdown")

@router.callback_query(F.data.startswith("onboarding_lang:"))
async def cb_onboarding_lang(callback: CallbackQuery, state: FSMContext):
    """Первоначальный выбор языка новым пользователем при первом входе"""
    await state.clear()
    selected_lang = callback.data.split(":")[1]
    if selected_lang not in ("en", "ru"):
        selected_lang = "en"

    await db.update_user_lang(callback.from_user.id, selected_lang)
    await db.set_user_lang_selected(callback.from_user.id, True)

    welcome_name = callback.from_user.first_name or ("друг" if selected_lang == "ru" else "friend")
    if selected_lang == "ru":
        welcome_text = (
            f"👋 *Привет, {welcome_name}! Я Stork (Аист)*: твой наставник по немецкому языку! 🇩🇪🪶\n\n"
            "Чтобы подобрать для тебя правильные слова, упражнения и уровень сложности, "
            "давай сначала определим твой текущий уровень в коротком тесте (~2 минуты).\n\n"
            "Или ты можешь сразу перейти в главное меню 👇"
        )
    else:
        welcome_text = (
            f"👋 *Welcome, {welcome_name}! I am Stork*: your German tutor! 🇩🇪🪶\n\n"
            "To personalize your learning path and recommend the right words and drills, "
            "let's check your current level with a quick placement test (~2 minutes).\n\n"
            "Or you can jump straight into the Main Menu below 👇"
        )
    kb = get_onboarding_welcome_keyboard(selected_lang)

    try:
        if getattr(callback.message, "photo", None):
            await callback.message.edit_caption(
                caption=welcome_text,
                reply_markup=kb,
                parse_mode="Markdown"
            )
        else:
            await callback.message.edit_text(
                text=welcome_text,
                reply_markup=kb,
                parse_mode="Markdown"
            )
    except Exception:
        await callback.message.answer(
            text=welcome_text,
            reply_markup=kb,
            parse_mode="Markdown"
        )
    await callback.answer()

@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    """Команда /menu: возврат в главное меню"""
    await state.clear()
    lang = await db.get_user_lang(message.from_user.id)
    workout_done = await db.is_daily_workout_completed(message.from_user.id)
    text = i18n.get("menu_title", lang)
    await message.answer(text, reply_markup=get_main_menu_keyboard(lang, workout_done=workout_done), parse_mode="Markdown")

@router.message(Command("lang"))
async def cmd_language(message: Message):
    """Команда /lang: выбор языка интерфейса"""
    lang = await db.get_user_lang(message.from_user.id)
    text = i18n.get("lang_select_title", lang)
    await message.answer(text, reply_markup=get_language_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "back_to_menu")
async def cb_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню через Inline-кнопку"""
    await callback.answer()
    await state.clear()
    lang = await db.get_user_lang(callback.from_user.id)
    workout_done = await db.is_daily_workout_completed(callback.from_user.id)
    text = i18n.get("menu_title", lang)
    kb = get_main_menu_keyboard(lang, workout_done=workout_done)
    await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "hub_training")
async def cb_hub_training(callback: CallbackQuery):
    """Подменю: Раздел тренировок"""
    await callback.answer()
    lang = await db.get_user_lang(callback.from_user.id)
    text = i18n.get("hub_training_title", lang)
    await show_or_update_window(callback, text, reply_markup=get_training_hub_keyboard(lang), parse_mode="Markdown")

@router.callback_query(F.data == "hub_vocab")
async def cb_hub_vocab(callback: CallbackQuery):
    """Подменю: Словарь и темы"""
    await callback.answer()
    lang = await db.get_user_lang(callback.from_user.id)
    level, category = await db.get_user_filters(callback.from_user.id)
    review_count = await db.get_review_words_count(callback.from_user.id)
    text = i18n.get("hub_vocab_title", lang)
    kb = get_vocab_hub_keyboard(lang, review_count=review_count, level=level, category=category)
    await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "hub_exams")
async def cb_hub_exams(callback: CallbackQuery):
    """Подменю: Экзамены и тесты"""
    await callback.answer()
    lang = await db.get_user_lang(callback.from_user.id)
    text = i18n.get("hub_exams_title", lang)
    await show_or_update_window(callback, text, reply_markup=get_exams_hub_keyboard(lang), parse_mode="Markdown")

@router.callback_query(F.data == "hub_settings")
async def cb_hub_settings(callback: CallbackQuery):
    """Подменю: Настройки"""
    await callback.answer()
    lang = await db.get_user_lang(callback.from_user.id)
    notif_status = await db.get_user_notifications_status(callback.from_user.id)
    text = i18n.get("hub_settings_title", lang)
    kb = get_settings_hub_keyboard(lang, notifications_enabled=notif_status)
    await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "menu_lang")
async def cb_menu_lang(callback: CallbackQuery):
    """Кнопка смены языка в меню"""
    await callback.answer()
    lang = await db.get_user_lang(callback.from_user.id)
    text = i18n.get("lang_select_title", lang)
    await show_or_update_window(callback, text, reply_markup=get_language_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data.startswith("set_lang:"))
async def cb_set_language(callback: CallbackQuery):
    """Установка выбранного языка"""
    await callback.answer()
    selected_lang = callback.data.split(":")[1]
    await db.update_user_lang(callback.from_user.id, selected_lang)
    level, category = await db.get_user_filters(callback.from_user.id)
    
    notice = i18n.get("lang_changed", selected_lang)
    menu_text = i18n.get("menu_title", selected_lang)
    full_text = f"{notice}\n\n{menu_text}"
    
    await show_or_update_window(
        callback,
        full_text,
        reply_markup=get_main_menu_keyboard(selected_lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "menu_stats")
async def cb_menu_stats(callback: CallbackQuery):
    """Просмотр личной статистики и прогресса"""
    await callback.answer()
    lang = await db.get_user_lang(callback.from_user.id)
    stats = await db.get_user_stats(callback.from_user.id)
    lang_info = i18n.get_available_languages().get(lang, {"name": lang, "flag": ""})
    
    text = i18n.get(
        "stats_title",
        lang,
        name=callback.from_user.first_name or "Freund",
        lang_name=f"{lang_info['flag']} {lang_info['name']}",
        score=stats["score"],
        streak=stats["streak"],
        known_words=stats.get("known_words", 0),
        review_words=stats.get("review_words", 0),
        learning_words=stats.get("learning_words", 0),
        total_words=stats["total_words"]
    )

    if stats.get("placement_level"):
        lvl = stats["placement_level"]
        score_val = stats.get("placement_score", 0)
        if lang == "ru":
            level_info = f"\n\n🎓 *Подтвержденный уровень CEFR:* *{lvl}* ({score_val}/12)"
        else:
            level_info = f"\n\n🎓 *Verified CEFR Level:* *{lvl}* ({score_val}/12)"
    else:
        if lang == "ru":
            level_info = "\n\n🎓 *Уровень языка:* _еще не проверен (пройди тест ниже)_"
        else:
            level_info = "\n\n🎓 *Language Level:* _not tested yet (take test below)_"

    # Блок тарифа и дневных квот
    is_prem = stats.get("is_premium", False)
    ai_count = stats.get("daily_ai_count", 0)
    ai_limit = stats.get("daily_ai_limit", 10)
    exam_count = stats.get("daily_exam_count", 0)
    exam_limit = stats.get("daily_exam_limit", 3)
    notif_enabled = stats.get("notifications_enabled", True)

    if lang == "ru":
        if is_prem:
            if stats.get("premium_until") == "lifetime":
                tariff_title = "👑 *Тариф:* Stork Lifetime VIP (Бессрочно)"
            else:
                tariff_title = f"⭐️ *Тариф:* Stork Premium 👑 (до {stats['premium_until'][:10]})"
        else:
            tariff_title = "⭐️ *Тариф:* Бесплатный"

        ai_quota_str = "Безлимитно ⭐️" if is_prem else f"{ai_count}/{ai_limit}"
        exam_quota_str = "Безлимитно ⭐️" if is_prem else f"{exam_count}/{exam_limit}"
        quota_info = (
            f"\n\n{tariff_title}\n"
            f"🤖 *ИИ-собеседник сегодня:* {ai_quota_str}\n"
            f"✍️ *Проверка писем сегодня:* {exam_quota_str}\n"
            f"🔔 *Напоминания о серии:* {'Включены' if notif_enabled else 'Выключены'}"
        )
    else:
        if is_prem:
            if stats.get("premium_until") == "lifetime":
                tariff_title = "👑 *Plan:* Stork Lifetime VIP (Permanent)"
            else:
                tariff_title = f"⭐️ *Plan:* Stork Premium 👑 (until {stats['premium_until'][:10]})"
        else:
            tariff_title = "⭐️ *Plan:* Free"

        ai_quota_str = "Unlimited ⭐️" if is_prem else f"{ai_count}/{ai_limit}"
        exam_quota_str = "Unlimited ⭐️" if is_prem else f"{exam_count}/{exam_limit}"
        quota_info = (
            f"\n\n{tariff_title}\n"
            f"🤖 *AI chat today:* {ai_quota_str}\n"
            f"✍️ *Exam checks today:* {exam_quota_str}\n"
            f"🔔 *Streak reminders:* {'Enabled' if notif_enabled else 'Disabled'}"
        )

    # Проверяем и выдаем новые достижения
    user_id = callback.from_user.id
    await db.check_and_grant_achievements(user_id)
    unlocked = await db.get_user_unlocked_achievements(user_id)
    total_badges = len(db.ACHIEVEMENTS_REGISTRY)
    badges_icons = " ".join([a["icon"] for a in unlocked]) if unlocked else "🐣"

    if lang == "ru":
        achieve_info = f"\n\n🏆 *Достижения ({len(unlocked)} из {total_badges}):* {badges_icons}"
    else:
        achieve_info = f"\n\n🏆 *Achievements ({len(unlocked)} of {total_badges}):* {badges_icons}"

    full_stats_text = f"{text}{level_info}{achieve_info}{quota_info}"
    
    await show_or_update_window(
        callback,
        full_stats_text,
        reply_markup=get_stats_keyboard(lang, notifications_enabled=notif_enabled),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "menu_achievements")
async def cb_menu_achievements(callback: CallbackQuery):
    """Витрина достижений и наград"""
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)
    await db.check_and_grant_achievements(user_id)
    unlocked = await db.get_user_unlocked_achievements(user_id)
    unlocked_ids = {a["id"] for a in unlocked}
    total = len(db.ACHIEVEMENTS_REGISTRY)

    title = i18n.get("achievements_title", lang, unlocked=len(unlocked), total=total)

    # Список открытых наград
    unlocked_lines = []
    for a in unlocked:
        t = a["title"].get(lang, a["title"]["ru"])
        d = a["desc"].get(lang, a["desc"]["ru"])
        date_str = a.get("unlocked_at", "")[:10]
        date_suffix = f" _({date_str})_" if date_str else ""
        unlocked_lines.append(f"• {a['icon']} *{t}*{date_suffix}\n  _{d}_")

    # Список следующих целей (закрытые)
    locked_lines = []
    for b_id, a in db.ACHIEVEMENTS_REGISTRY.items():
        if b_id not in unlocked_ids:
            t = a["title"].get(lang, a["title"]["ru"])
            d = a["desc"].get(lang, a["desc"]["ru"])
            locked_lines.append(f"• 🔒 {a['icon']} *{t}*\n  _{d}_")

    sec_unlocked = i18n.get("achievements_unlocked_header", lang)
    sec_locked = i18n.get("achievements_locked_header", lang)

    parts = [title]
    if unlocked_lines:
        parts.append(f"\n{sec_unlocked}\n" + "\n".join(unlocked_lines))
    if locked_lines:
        parts.append(f"\n{sec_locked}\n" + "\n".join(locked_lines))

    full_text = "\n".join(parts)
    await show_or_update_window(
        callback,
        full_text,
        reply_markup=get_achievements_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "toggle_notif")
async def cb_toggle_notif(callback: CallbackQuery):
    """Переключение ежедневных напоминаний о серии занятий"""
    new_status = await db.toggle_user_notifications(callback.from_user.id)
    lang = await db.get_user_lang(callback.from_user.id)
    notice = i18n.get("reminder_toggled_on" if new_status else "reminder_toggled_off", lang)
    await callback.answer(notice)
    await cb_menu_stats(callback)

@router.callback_query(F.data == "show_profile_card")
async def cb_show_profile_card(callback: CallbackQuery):
    """Генерация и отправка карточки ученика Stork (Student Passport)"""
    await callback.answer("Генерирую вашу карточку ученика...")
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)
    stats = await db.get_user_stats(user_id)

    from services.card_service import generate_profile_card_image, get_profile_card_share_content
    from keyboards.inline import get_profile_card_keyboard
    from aiogram.types import BufferedInputFile

    user_data = {
        "user_id": user_id,
        "first_name": callback.from_user.first_name or "Freund",
        "username": callback.from_user.username,
        "placement_level": stats.get("placement_level") or "A1",
        "score": stats.get("score") or 0,
        "streak": stats.get("streak") or 0,
        "known_words": stats.get("known_words") or 0,
        "is_premium": stats.get("is_premium") or 0,
        "is_lifetime_vip": (stats.get("premium_until") == "lifetime")
    }

    caption, share_url = get_profile_card_share_content(user_data, lang)

    try:
        card_png = generate_profile_card_image(user_data, lang=lang)
        photo_file = BufferedInputFile(card_png, filename=f"stork_passport_{user_id}.png")
        await callback.message.answer_photo(
            photo=photo_file,
            caption=caption,
            reply_markup=get_profile_card_keyboard(share_url, lang),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка отправки карточки профиля: {e}")
        await callback.message.answer(
            caption,
            reply_markup=get_profile_card_keyboard(share_url, lang),
            parse_mode="Markdown"
        )

# ==============================================================================
# КОМАНДЫ УПРАВЛЕНИЯ ПОЖИЗНЕННЫМ VIP (ДЛЯ АДМИНИСТРАТОРА)
# ==============================================================================

async def _is_admin(user_id: int, username: str = None) -> bool:
    """Проверка прав администратора для управления VIP"""
    if user_id in (6725392176, 190417869): # ID создателя (Amir)
        return True
    return is_lifetime_vip_in_config(user_id, username)

@router.message(Command("vip"))
async def cmd_grant_vip(message: Message):
    """Команда для администратора: выдать вечный VIP пользователю (/vip 12345678 или /vip @username)"""
    if not await _is_admin(message.from_user.id, message.from_user.username):
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("ℹ️ Использование: `/vip <ID_или_username>`\nПример: `/vip 6725392176` или `/vip @username`", parse_mode="Markdown")
        return

    target = parts[1]
    ok, status, user_data = await db.set_user_lifetime_vip(target, is_vip=True)
    if ok and user_data:
        name = user_data.get("first_name") or user_data.get("username") or str(user_data["user_id"])
        uid = user_data["user_id"]
        uname = f"(@{user_data['username']})" if user_data.get("username") else ""
        await message.answer(f"👑 Пользователю *{name}* {uname} [ID: `{uid}`] успешно выдан *ПОЖИЗНЕННЫЙ VIP*!\nТеперь у него вечный премиум без каких-либо ограничений.", parse_mode="Markdown")
    else:
        await message.answer(f"❌ Пользователь `{target}` не найден в базе данных бота. Попроси его сначала нажать /start в боте или просто добавь его в список `LIFETIME_VIP_USERS` в `premium_config.py`.", parse_mode="Markdown")

@router.message(Command("unvip"))
async def cmd_revoke_vip(message: Message):
    """Команда для администратора: забрать вечный VIP у пользователя (/unvip 12345678 или /unvip @username)"""
    if not await _is_admin(message.from_user.id, message.from_user.username):
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("ℹ️ Использование: `/unvip <ID_или_username>`\nПример: `/unvip 6725392176` или `/unvip @username`", parse_mode="Markdown")
        return

    target = parts[1]
    ok, status, user_data = await db.set_user_lifetime_vip(target, is_vip=False)
    if ok and user_data:
        name = user_data.get("first_name") or user_data.get("username") or str(user_data["user_id"])
        uid = user_data["user_id"]
        await message.answer(f"🚫 Пожизненный VIP у пользователя *{name}* [ID: `{uid}`] успешно отозван.\n(Если пользователь также указан в файле `premium_config.py`, не забудь удалить его и оттуда).", parse_mode="Markdown")
    else:
        await message.answer(f"❌ Пользователь `{target}` не найден в базе данных.", parse_mode="Markdown")

@router.message(Command("viplist"))
async def cmd_list_vip(message: Message):
    """Команда для администратора: посмотреть всех пользователей с пожизненным VIP"""
    if not await _is_admin(message.from_user.id, message.from_user.username):
        return

    vip_data = await db.get_all_lifetime_vip_users()
    db_list = vip_data.get("database_vips", [])
    cfg_list = vip_data.get("config_vips", [])

    lines = ["👑 *Список пользователей с ПОЖИЗНЕННЫМ VIP:*\n"]
    if cfg_list:
        lines.append("📁 *Из файла premium_config.py:*")
        for item in cfg_list:
            lines.append(f"• `{item}`")
        lines.append("")

    if db_list:
        lines.append("💾 *Из базы данных (выдано через /vip):*")
        for u in db_list:
            uname = f"@{u['username']}" if u.get("username") else "без username"
            lines.append(f"• {u.get('first_name', 'Пользователь')} ({uname}) - ID: `{u['user_id']}`")
    else:
        lines.append("💾 В базе данных нет вручную выданных VIP.")

    await message.answer("\n".join(lines), parse_mode="Markdown")

