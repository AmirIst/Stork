import asyncio
import os
import logging
from datetime import datetime, timezone
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import SUPER_ADMIN_IDS
from database import db
from database.db import DB_PATH

logger = logging.getLogger(__name__)
router = Router()

# ==========================================
# FSM Состояния
# ==========================================

class AdminUserState(StatesGroup):
    waiting_query = State()
    waiting_custom_days = State()

class AdminPromoState(StatesGroup):
    waiting_code = State()
    waiting_type = State()
    waiting_value = State()
    waiting_limit = State()
    waiting_expiry = State()
    waiting_desc = State()

class AdminBroadcastState(StatesGroup):
    waiting_audience = State()
    waiting_text = State()
    confirm_send = State()

class AdminManageState(StatesGroup):
    waiting_admin_query = State()

# ==========================================
# Клавиатуры админки с учетом ролей
# ==========================================

def get_admin_main_keyboard(role: str, notify_enabled: bool) -> InlineKeyboardMarkup:
    notify_text = "🔔 Оповещения об оплатах: ВКЛ" if notify_enabled else "🔕 Оповещения об оплатах: ВЫКЛ"
    buttons = []

    if role in ("super_admin", "admin"):
        buttons.append([
            InlineKeyboardButton(text="📊 Аналитика и метрики", callback_data="admin_stats"),
            InlineKeyboardButton(text="👤 Найти пользователя", callback_data="admin_user_search")
        ])
        buttons.append([
            InlineKeyboardButton(text="🎟 Промокоды", callback_data="admin_promos"),
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast_menu")
        ])
        buttons.append([
            InlineKeyboardButton(text="💾 Скачать бэкап базы данных", callback_data="admin_backup")
        ])
        if role == "super_admin":
            buttons.append([
                InlineKeyboardButton(text="👥 Управление админами", callback_data="admin_team")
            ])
    elif role == "analyst":
        buttons.append([
            InlineKeyboardButton(text="📊 Аналитика и метрики", callback_data="admin_stats")
        ])
    elif role == "broadcaster":
        buttons.append([
            InlineKeyboardButton(text="📢 Рассылка сообщений", callback_data="admin_broadcast_menu")
        ])

    buttons.append([
        InlineKeyboardButton(text=notify_text, callback_data="admin_toggle_notify")
    ])
    buttons.append([
        InlineKeyboardButton(text="❌ Закрыть панель", callback_data="admin_close")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В главное меню админки", callback_data="admin_main")]
    ])

def get_user_actions_keyboard(user_id: int, is_premium: bool) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="⭐️ +30 дней", callback_data=f"adm_grant:{user_id}:30:manual"),
            InlineKeyboardButton(text="⭐️ +90 дней", callback_data=f"adm_grant:{user_id}:90:manual")
        ],
        [
            InlineKeyboardButton(text="⭐️ +365 дней", callback_data=f"adm_grant:{user_id}:365:manual"),
            InlineKeyboardButton(text="👑 Навсегда (VIP)", callback_data=f"adm_grant:{user_id}:lifetime")
        ],
        [
            InlineKeyboardButton(text="⏳ Свой срок (дней)", callback_data=f"adm_custom:{user_id}")
        ]
    ]
    if is_premium:
        buttons.append([
            InlineKeyboardButton(text="🚫 Отозвать Premium", callback_data=f"adm_revoke:{user_id}")
        ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_promo_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_promo_create")],
        [InlineKeyboardButton(text="📋 Список всех кодов", callback_data="admin_promo_list")],
        [InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_main")]
    ])

def get_broadcast_audience_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Всем пользователям", callback_data="adm_bc_aud:all")],
        [InlineKeyboardButton(text="⭐️ Только Premium", callback_data="adm_bc_aud:premium")],
        [InlineKeyboardButton(text="🆓 Только бесплатным", callback_data="adm_bc_aud:free")],
        [InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_main")]
    ])

# ==========================================
# Главный экран /admin
# ==========================================

async def build_admin_dashboard_text(user_id: int, role: str) -> str:
    role_titles = {
        "super_admin": "👑 Владелец (Super Admin)",
        "admin": "🛠 Администратор",
        "analyst": "📊 Аналитик (просмотр статистики)",
        "broadcaster": "📢 Менеджер рассылок",
    }
    role_title = role_titles.get(role, role)
    now_str = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

    if role == "broadcaster":
        return (
            f"👑 *Панель рассылок Stork Bot*\n"
            f"👤 Ваша роль: *{role_title}*\n"
            f"🕒 Время: {now_str}\n\n"
            f"Вам доступно создание и отправка рассылок по аудитории бота (все пользователи, подписчики Premium или бесплатные пользователи).\n\n"
            f"👇 Нажмите кнопку ниже для перехода к рассылке:"
        )

    stats = await db.get_admin_stats()
    text = (
        f"👑 *Панель управления Stork Bot*\n"
        f"👤 Ваша роль: *{role_title}*\n"
        f"🕒 Данные на: {now_str}\n\n"
        f"👥 *Пользователи:*\n"
        f"• Всего зарегистрировано: *{stats['total_users']}*\n"
        f"• Новых за сегодня: *+{stats['new_today']}*\n"
        f"• Активных сегодня (DAU): *{stats['active_today']}*\n"
        f"• Активных за 7 дней (WAU): *{stats['active_7d']}*\n\n"
        f"⭐️ *Премиум подписки:*\n"
        f"• Всего активных Premium: *{stats['total_premium']}*\n"
        f"  └ 👑 Lifetime VIP: *{stats['cnt_lifetime']}*\n"
        f"  └ 1 месяц: *{stats['cnt_1m']}*\n"
        f"  └ 3 месяца: *{stats['cnt_3m']}*\n"
        f"  └ 1 год: *{stats['cnt_1y']}*\n"
        f"  └ Пробный период: *{stats['cnt_trial']}*\n"
        f"  └ Промокоды: *{stats['cnt_promo']}*\n"
        f"  └ Выдано вручную: *{stats['cnt_manual']}*\n\n"
        f"💰 *Финансы и выручка:*\n"
        f"• Успешных оплат: *{stats['total_payments_count']}*\n"
        f"• Общая выручка: *{stats['total_revenue_stars']} ⭐️* (~{stats['total_revenue_eur']} €)\n"
        f"• Ожидаемый MRR в месяц: *{stats['mrr_stars']} ⭐️* (~{stats['mrr_eur']} €)\n\n"
        f"👇 Выберите действие в меню ниже:"
    )
    return text

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Точка входа в админ-панель"""
    user_id = message.from_user.id
    role = await db.get_user_admin_role(user_id)
    if not role:
        await message.answer("⛔ Доступ ограничен. Эта команда предназначена только для администраторов бота.")
        return

    await state.clear()
    notify_enabled = (await db.get_admin_notification_status(user_id) == 1)
    dashboard_text = await build_admin_dashboard_text(user_id, role)
    await message.answer(
        dashboard_text,
        reply_markup=get_admin_main_keyboard(role, notify_enabled),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_main")
async def cb_admin_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню админки"""
    user_id = callback.from_user.id
    role = await db.get_user_admin_role(user_id)
    if not role:
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    await state.clear()
    notify_enabled = (await db.get_admin_notification_status(user_id) == 1)
    dashboard_text = await build_admin_dashboard_text(user_id, role)
    try:
        await callback.message.edit_text(
            dashboard_text,
            reply_markup=get_admin_main_keyboard(role, notify_enabled),
            parse_mode="Markdown"
        )
    except Exception:
        await callback.message.answer(
            dashboard_text,
            reply_markup=get_admin_main_keyboard(role, notify_enabled),
            parse_mode="Markdown"
        )
    await callback.answer()

@router.callback_query(F.data == "admin_toggle_notify")
async def cb_admin_toggle_notify(callback: CallbackQuery):
    """Переключение получения оповещений об оплатах (ВКЛ / ВЫКЛ)"""
    user_id = callback.from_user.id
    role = await db.get_user_admin_role(user_id)
    if not role:
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    success, new_val = await db.toggle_admin_notifications(user_id)
    notify_bool = (new_val == 1)
    toast_msg = "🔔 Оповещения об оплатах включены" if notify_bool else "🔕 Оповещения об оплатах выключены"

    kb = get_admin_main_keyboard(role, notify_bool)
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass
    await callback.answer(toast_msg)

@router.callback_query(F.data == "admin_close")
async def cb_admin_close(callback: CallbackQuery, state: FSMContext):
    """Закрытие меню админки"""
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        await callback.answer("Закрыто")

# ==========================================
# Раздел: Управление командой админов (только Super Admin)
# ==========================================

@router.callback_query(F.data == "admin_team")
async def cb_admin_team(callback: CallbackQuery):
    """Список команды администраторов (доступно только Super Admin)"""
    user_id = callback.from_user.id
    if not await db.can_manage_admins(user_id):
        await callback.answer("Управлять админами могут только главные владельцы", show_alert=True)
        return

    admins = await db.get_all_admins()
    lines = ["👥 *Управление командой администраторов Stork*\n"]
    lines.append("Ниже список пользователей с правами доступа к боту:\n")

    for a in admins:
        uid = a["user_id"]
        uname = f"@{a['username']}" if a.get("username") else f"ID: {uid}"
        role = a.get("role", "admin")
        notify_ico = "🔔" if a.get("notify_payments", 1) == 1 else "🔕"

        if role == "super_admin":
            role_badge = "👑 Главный владелец [Нельзя удалить]"
        elif role == "admin":
            role_badge = "🛠 Администратор"
        elif role == "analyst":
            role_badge = "📊 Аналитик"
        elif role == "broadcaster":
            role_badge = "📢 Рассыльщик"
        else:
            role_badge = role

        lines.append(f"• *{uname}* (`{uid}`)\n  └ {role_badge} | {notify_ico} Оповещения")

    lines.append("\n_Супер-админов удалить невозможно. Других админов можно добавлять и снимать в любой момент._")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить админа", callback_data="adm_add_admin_start")],
        [InlineKeyboardButton(text="❌ Удалить админа", callback_data="adm_remove_admin_list")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="admin_main")]
    ])

    try:
        await callback.message.edit_text("\n".join(lines), reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.answer("\n".join(lines), reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "adm_add_admin_start")
async def cb_adm_add_admin_start(callback: CallbackQuery, state: FSMContext):
    """Запрос ID или username для добавления админа"""
    user_id = callback.from_user.id
    if not await db.can_manage_admins(user_id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    await state.set_state(AdminManageState.waiting_admin_query)
    text = (
        "➕ *Добавление администратора (Шаг 1 из 2)*\n\n"
        "Отправьте Telegram ID пользователя (например: `123456789`) "
        "или его юзернейм с собачкой или без (например: `@ivan`).\n\n"
        "Пользователь должен хотя бы раз нажать /start в боте, чтобы бот мог с ним связаться."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_team")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.message(AdminManageState.waiting_admin_query, F.text)
async def process_admin_query(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not await db.can_manage_admins(user_id):
        return

    query = message.text.strip()
    if query.startswith("/"):
        await state.clear()
        return

    u_info = await db.get_user_admin_info(query)
    if u_info:
        target_uid = u_info["user_id"]
        target_uname = u_info.get("username") or ""
        target_name = f"{u_info.get('first_name', '')} {u_info.get('last_name', '')}".strip() or "Пользователь"
    elif query.isdigit():
        target_uid = int(query)
        target_uname = ""
        target_name = f"ID: {target_uid}"
    else:
        await message.answer(
            f"❌ Пользователь с запросом *{query}* не найден в базе данных.\n"
            f"Попросите его сначала отправить любое сообщение боту (например, /start), "
            f"или отправьте его чистый числовой Telegram ID.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к списку админов", callback_data="admin_team")]
            ]),
            parse_mode="Markdown"
        )
        return

    if target_uid in SUPER_ADMIN_IDS:
        await state.clear()
        await message.answer(
            f"👑 Пользователь *{target_name}* (`{target_uid}`) уже является главным владельцем бота.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 В меню команды", callback_data="admin_team")]
            ]),
            parse_mode="Markdown"
        )
        return

    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Администратор (полный доступ)", callback_data=f"adm_set_role:{target_uid}:{target_uname}:admin")],
        [InlineKeyboardButton(text="📊 Аналитик (только статистика)", callback_data=f"adm_set_role:{target_uid}:{target_uname}:analyst")],
        [InlineKeyboardButton(text="📢 Рассыльщик (только рассылка)", callback_data=f"adm_set_role:{target_uid}:{target_uname}:broadcaster")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_team")]
    ])

    uname_label = f"@{target_uname}" if target_uname else "без юзернейма"
    await message.answer(
        f"👤 Назначение роли для *{target_name}* ({uname_label}, `{target_uid}`)\n\n"
        f"Выберите уровень доступа для этого пользователя:",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("adm_set_role:"))
async def cb_adm_set_role(callback: CallbackQuery):
    caller_id = callback.from_user.id
    if not await db.can_manage_admins(caller_id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    parts = callback.data.split(":")
    target_uid = int(parts[1])
    target_uname = parts[2]
    role = parts[3]

    role_titles = {
        "admin": "🛠 Администратор",
        "analyst": "📊 Аналитик (только статистика)",
        "broadcaster": "📢 Менеджер рассылок (только рассылка)"
    }
    role_name = role_titles.get(role, role)

    success, res = await db.add_bot_admin(
        user_id=target_uid,
        username=target_uname,
        role=role,
        added_by=caller_id
    )

    if not success:
        await callback.answer("Не удалось назначить роль", show_alert=True)
        return

    try:
        notify_text = (
            f"🎉 *Вам предоставлен доступ к панели управления Stork Bot!*\n\n"
            f"• Ваша роль: *{role_name}*\n\n"
            f"Для открытия панели введите команду: /admin"
        )
        await callback.bot.send_message(target_uid, notify_text, parse_mode="Markdown")
    except Exception as e:
        logger.info(f"Не удалось отправить уведомление новому админу {target_uid}: {e}")

    await callback.answer(f"Админ успешно добавлен с ролью {role_name}!", show_alert=True)
    await cb_admin_team(callback)

@router.callback_query(F.data == "adm_remove_admin_list")
async def cb_adm_remove_admin_list(callback: CallbackQuery):
    """Список админов для удаления (кроме владельцев)"""
    caller_id = callback.from_user.id
    if not await db.can_manage_admins(caller_id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    admins = await db.get_all_admins()
    removable = [a for a in admins if a["user_id"] not in SUPER_ADMIN_IDS]

    if not removable:
        await callback.answer("Нет добавленных администраторов для удаления", show_alert=True)
        return

    lines = [
        "❌ *Удаление администратора*\n",
        "Выберите пользователя, у которого нужно отозвать доступ к админке:"
    ]
    kb_rows = []
    role_names = {
        "admin": "Админ",
        "analyst": "Аналитик",
        "broadcaster": "Рассылка"
    }

    for a in removable:
        uid = a["user_id"]
        uname = f"@{a['username']}" if a.get("username") else f"ID: {uid}"
        r_name = role_names.get(a.get("role"), a.get("role"))
        kb_rows.append([
            InlineKeyboardButton(text=f"🗑 {uname} ({r_name})", callback_data=f"adm_del_admin_confirm:{uid}")
        ])

    kb_rows.append([InlineKeyboardButton(text="🔙 Назад в меню команды", callback_data="admin_team")])

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("adm_del_admin_confirm:"))
async def cb_adm_del_admin_confirm(callback: CallbackQuery):
    caller_id = callback.from_user.id
    if not await db.can_manage_admins(caller_id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    target_uid = int(callback.data.split(":")[1])
    success, res = await db.remove_bot_admin(target_uid, removed_by=caller_id)

    if not success:
        await callback.answer("Этого администратора нельзя удалить", show_alert=True)
        return

    try:
        await callback.bot.send_message(
            target_uid,
            "ℹ️ Ваш доступ к панели администратора Stork Bot был отозван главным владельцем.",
            parse_mode="Markdown"
        )
    except Exception:
        pass

    await callback.answer(f"Администратор {target_uid} удален из команды!", show_alert=True)
    await cb_admin_team(callback)

# ==========================================
# Раздел: Аналитика и метрики
# ==========================================

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    """Подробная статистика и коэффициенты конверсии"""
    user_id = callback.from_user.id
    if not await db.can_view_stats(user_id):
        await callback.answer("У вас нет прав для просмотра аналитики", show_alert=True)
        return

    stats = await db.get_admin_stats()
    total_users = stats["total_users"]
    total_premium = stats["total_premium"]

    conversion_rate = round((total_premium / total_users * 100), 2) if total_users > 0 else 0.0
    dau_wau_ratio = round((stats["active_today"] / stats["active_7d"] * 100), 1) if stats["active_7d"] > 0 else 0.0

    text = (
        f"📊 *Детальная аналитика Stork Bot*\n\n"
        f"📈 *Показатели активности:*\n"
        f"• Всего пользователей: *{total_users}*\n"
        f"• Новые за сегодня: *+{stats['new_today']}*\n"
        f"• Активные за сутки (DAU): *{stats['active_today']}*\n"
        f"• Активные за 7 дней (WAU): *{stats['active_7d']}*\n"
        f"• Вовлеченность (DAU / WAU): *{dau_wau_ratio}%*\n\n"
        f"⭐️ *Конверсия и монетизация:*\n"
        f"• Конверсия в Premium: *{conversion_rate}%*\n"
        f"• Всего активных Premium: *{total_premium}*\n"
        f"• Платных оплат: *{stats['total_payments_count']}*\n"
        f"• Общая выручка: *{stats['total_revenue_stars']} ⭐️* (~{stats['total_revenue_eur']} €)\n"
        f"• Прогнозируемый MRR: *{stats['mrr_stars']} ⭐️* (~{stats['mrr_eur']} €)\n\n"
        f"📑 *Распределение типов Premium:*\n"
        f"• 👑 Lifetime (навсегда): *{stats['cnt_lifetime']}*\n"
        f"• 📅 1 месяц: *{stats['cnt_1m']}*\n"
        f"• 📅 3 месяца: *{stats['cnt_3m']}*\n"
        f"• 📅 1 год: *{stats['cnt_1y']}*\n"
        f"• 🎁 Бесплатный триал: *{stats['cnt_trial']}*\n"
        f"• 🎟 По промокоду: *{stats['cnt_promo']}*\n"
        f"• 🛠 Выдано вручную: *{stats['cnt_manual']}*"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🔙 В админку", callback_data="admin_main")]
    ])

    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer("Данные обновлены")

# ==========================================
# Раздел: Управление пользователем
# ==========================================

@router.callback_query(F.data == "admin_user_search")
async def cb_admin_user_search(callback: CallbackQuery, state: FSMContext):
    """Запрос ID или username для поиска"""
    user_id = callback.from_user.id
    if not await db.can_manage_users(user_id):
        await callback.answer("У вас нет прав для управления пользователями", show_alert=True)
        return

    await state.set_state(AdminUserState.waiting_query)
    text = (
        "🔍 *Поиск пользователя*\n\n"
        "Отправьте Telegram ID пользователя (например: `6725392176`) "
        "или его юзернейм с собачкой или без (например: `@Amirist1`).\n\n"
        "Для отмены нажмите кнопку ниже."
    )
    await callback.message.edit_text(text, reply_markup=get_admin_back_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.message(AdminUserState.waiting_query, F.text)
async def process_user_search_query(message: Message, state: FSMContext):
    """Поиск и вывод карточки пользователя"""
    if not await db.can_manage_users(message.from_user.id):
        return

    query = message.text.strip()
    if query.startswith("/"):
        await state.clear()
        return

    user_info = await db.get_user_admin_info(query)
    if not user_info:
        await message.answer(
            f"❌ Пользователь с запросом *{query}* не найден в базе данных бота.\n"
            f"Попробуйте еще раз или вернитесь в меню.",
            reply_markup=get_admin_back_keyboard(),
            parse_mode="Markdown"
        )
        return

    await state.clear()
    await show_user_card(message, user_info)

async def show_user_card(target_msg: Message, u: dict):
    uid = u["user_id"]
    username = f"@{u['username']}" if u.get("username") else "отсутствует"
    first_name = u.get("first_name") or ""
    last_name = u.get("last_name") or ""
    full_name = f"{first_name} {last_name}".strip() or "Пользователь"

    is_premium = bool(u.get("is_premium"))
    is_vip = bool(u.get("is_lifetime_vip"))
    prem_until = u.get("premium_until")
    sub_type = u.get("subscription_type") or "none"

    if is_vip:
        status_text = "👑 Lifetime VIP (бессрочно)"
    elif is_premium and prem_until:
        status_text = f"⭐️ Активен до {prem_until[:10]} ({prem_until[11:16]} UTC)"
    else:
        status_text = "🆓 Бесплатный тариф"

    created = u.get("created_at") or "—"
    created_str = created[:10] if len(created) >= 10 else created

    card_text = (
        f"👤 *Карточка пользователя*\n\n"
        f"• Имя: *{full_name}*\n"
        f"• User ID: `{uid}`\n"
        f"• Username: {username}\n"
        f"• Язык интерфейса: *{u.get('language', 'ru')}*\n"
        f"• Статус Premium: *{status_text}*\n"
        f"• Тип подписки: `{sub_type}`\n"
        f"• Изучено слов: *{u.get('words_learned', 0)}* из {u.get('words_total', 0)}\n"
        f"• Приглашено рефералов: *{u.get('referrals_count', 0)}*\n"
        f"• Оплат совершено: *{u.get('payments_count', 0)}* (на сумму {u.get('payments_sum', 0)} ⭐️)\n"
        f"• Дата регистрации: {created_str}\n\n"
        f"⚙️ Выберите действие для пользователя:"
    )

    await target_msg.answer(
        card_text,
        reply_markup=get_user_actions_keyboard(uid, is_premium or is_vip),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("adm_grant:"))
async def cb_adm_grant(callback: CallbackQuery):
    """Выдача Premium на фиксированный срок или Lifetime"""
    if not await db.can_manage_users(callback.from_user.id):
        await callback.answer("У вас нет прав для изменения подписок", show_alert=True)
        return

    parts = callback.data.split(":")
    uid = int(parts[1])
    duration = parts[2]
    sub_type = parts[3] if len(parts) > 3 else "manual"

    if duration == "lifetime":
        success, status, user_info, until_str = await db.grant_user_premium(uid, days=36500, sub_type="lifetime")
    else:
        days = int(duration)
        success, status, user_info, until_str = await db.grant_user_premium(uid, days=days, sub_type=sub_type)

    try:
        notify_msg = (
            "🎉 *Вам начислен Stork Premium!*\n\n"
            f"Администратор активировал для вас премиум-доступ: *{'Бессрочно' if duration == 'lifetime' else f'{duration} дней'}*.\n"
            "Приятного изучения немецкого языка с полным функционалом!"
        )
        await callback.bot.send_message(uid, notify_msg, parse_mode="Markdown")
    except Exception as e:
        logger.info(f"Не удалось отправить уведомление пользователю {uid}: {e}")

    await callback.answer("Премиум успешно выдан!")
    updated_info = await db.get_user_admin_info(uid)
    if updated_info:
        await callback.message.delete()
        await show_user_card(callback.message, updated_info)

@router.callback_query(F.data.startswith("adm_revoke:"))
async def cb_adm_revoke(callback: CallbackQuery):
    """Отзыв Premium статуса"""
    if not await db.can_manage_users(callback.from_user.id):
        await callback.answer("У вас нет прав для изменения подписок", show_alert=True)
        return

    uid = int(callback.data.split(":")[1])
    success, status, user_info = await db.revoke_user_premium(uid)

    try:
        await callback.bot.send_message(
            uid,
            "ℹ️ Действие вашей подписки Stork Premium было завершено администратором.",
            parse_mode="Markdown"
        )
    except Exception:
        pass

    await callback.answer("Premium успешно отозван!")
    updated_info = await db.get_user_admin_info(uid)
    if updated_info:
        await callback.message.delete()
        await show_user_card(callback.message, updated_info)

@router.callback_query(F.data.startswith("adm_custom:"))
async def cb_adm_custom(callback: CallbackQuery, state: FSMContext):
    """Запрос кастомного количества дней"""
    if not await db.can_manage_users(callback.from_user.id):
        await callback.answer("У вас нет прав для изменения подписок", show_alert=True)
        return

    uid = int(callback.data.split(":")[1])
    await state.set_state(AdminUserState.waiting_custom_days)
    await state.update_data(target_user_id=uid)

    await callback.message.answer(
        f"⏳ Введите количество дней Premium для пользователя `{uid}` (целое число, например: `14` или `180`):",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AdminUserState.waiting_custom_days, F.text)
async def process_custom_days(message: Message, state: FSMContext):
    """Применение кастомного срока Premium"""
    if not await db.can_manage_users(message.from_user.id):
        return

    txt = message.text.strip()
    if not txt.isdigit() or int(txt) <= 0:
        await message.answer("Пожалуйста, введите положительное целое число дней:")
        return

    days = int(txt)
    data = await state.get_data()
    uid = data.get("target_user_id")
    await state.clear()

    success, status, user_info, until_str = await db.grant_user_premium(uid, days=days, sub_type="manual")

    try:
        await message.bot.send_message(
            uid,
            f"🎉 Вам начислен Stork Premium на *{days} дней* (до {until_str[:10]})!",
            parse_mode="Markdown"
        )
    except Exception:
        pass

    await message.answer(f"✅ Успешно! Пользователю `{uid}` начислен Premium на *{days} дней* (до {until_str[:10]}).", parse_mode="Markdown")
    updated_info = await db.get_user_admin_info(uid)
    if updated_info:
        await show_user_card(message, updated_info)

# ==========================================
# Раздел: Управление промокодами
# ==========================================

@router.callback_query(F.data == "admin_promos")
async def cb_admin_promos(callback: CallbackQuery):
    """Меню промокодов"""
    if not await db.can_manage_promos(callback.from_user.id):
        await callback.answer("У вас нет прав для управления промокодами", show_alert=True)
        return

    text = (
        "🎟 *Управление промокодами Stork*\n\n"
        "Здесь вы можете создать новый промокод (на бесплатные дни Premium или скидку), "
        "а также просмотреть текущие коды и деактивировать неактуальные."
    )
    await callback.message.edit_text(text, reply_markup=get_promo_menu_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_promo_list")
async def cb_admin_promo_list(callback: CallbackQuery):
    """Список всех промокодов"""
    if not await db.can_manage_promos(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    codes = await db.get_all_db_promo_codes()
    if not codes:
        await callback.message.edit_text(
            "🎟 В базе данных пока нет созданных промокодов.",
            reply_markup=get_promo_menu_keyboard(),
            parse_mode="Markdown"
        )
        return

    lines = ["🎟 *Список промокодов в базе данных:*\n"]
    kb_rows = []

    for c in codes:
        status_ico = "🟢" if c["is_active"] else "🔴"
        val = f"{c['days']} дн." if c["promo_type"] == "days" else f"{c['discount_val']}%"
        limit = f"{c['used_count']}/{c['max_activations']}" if c["max_activations"] else f"{c['used_count']}/∞"
        expiry = c["expires_at"][:10] if c.get("expires_at") else "бессрочно"

        lines.append(
            f"{status_ico} `{c['code']}`: *{val}* | Активаций: *{limit}* | До: {expiry}"
        )
        if c["is_active"]:
            kb_rows.append([
                InlineKeyboardButton(text=f"🚫 Отключить {c['code']}", callback_data=f"adm_deact_promo:{c['code']}")
            ])

    kb_rows.append([InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_promo_create")])
    kb_rows.append([InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_main")])

    await callback.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_deact_promo:"))
async def cb_adm_deact_promo(callback: CallbackQuery):
    """Деактивация промокода"""
    if not await db.can_manage_promos(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    code = callback.data.split(":")[1]
    await db.deactivate_db_promo_code(code)
    await callback.answer(f"Промокод {code} деактивирован!", show_alert=True)
    await cb_admin_promo_list(callback)

@router.callback_query(F.data == "admin_promo_create")
async def cb_admin_promo_create(callback: CallbackQuery, state: FSMContext):
    """Старт визарда создания промокода"""
    if not await db.can_manage_promos(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    await state.set_state(AdminPromoState.waiting_code)
    text = (
        "➕ *Создание промокода (Шаг 1 из 5)*\n\n"
        "Введите кодовое слово промокода латиницей или цифрами (например: `SPRING2026` или `WELCOME100`):"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_back_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.message(AdminPromoState.waiting_code, F.text)
async def process_promo_code(message: Message, state: FSMContext):
    if not await db.can_manage_promos(message.from_user.id):
        return

    code = message.text.strip().upper()
    await state.update_data(code=code)
    await state.set_state(AdminPromoState.waiting_type)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Бесплатные дни Premium", callback_data="prm_type:days")],
        [InlineKeyboardButton(text="🏷 Скидка на тариф в %", callback_data="prm_type:discount")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_main")]
    ])

    await message.answer(
        f"Промокод: `{code}`\n\n*Шаг 2 из 5:* Выберите тип вознаграждения:",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@router.callback_query(AdminPromoState.waiting_type, F.data.startswith("prm_type:"))
async def process_promo_type(callback: CallbackQuery, state: FSMContext):
    p_type = callback.data.split(":")[1]
    await state.update_data(promo_type=p_type)
    await state.set_state(AdminPromoState.waiting_value)

    if p_type == "days":
        text = "🎁 *Шаг 3 из 5:* Сколько дней Premium дарить пользователю? (например: `30`):"
    else:
        text = "🏷 *Шаг 3 из 5:* Какой процент скидки предоставить? (например: `50`):"

    await callback.message.edit_text(text, reply_markup=get_admin_back_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.message(AdminPromoState.waiting_value, F.text)
async def process_promo_value(message: Message, state: FSMContext):
    if not await db.can_manage_promos(message.from_user.id):
        return

    txt = message.text.strip()
    if not txt.isdigit() or int(txt) <= 0:
        await message.answer("Пожалуйста, введите положительное число:")
        return

    val = int(txt)
    await state.update_data(value=val)
    await state.set_state(AdminPromoState.waiting_limit)

    await message.answer(
        "👥 *Шаг 4 из 5:* Введите лимит максимального числа активаций промокода "
        "(например: `100` для первых ста человек, или `0` для безлимита):",
        reply_markup=get_admin_back_keyboard(),
        parse_mode="Markdown"
    )

@router.message(AdminPromoState.waiting_limit, F.text)
async def process_promo_limit(message: Message, state: FSMContext):
    if not await db.can_manage_promos(message.from_user.id):
        return

    txt = message.text.strip()
    if not txt.isdigit():
        await message.answer("Пожалуйста, введите число (0 для безлимита):")
        return

    limit = int(txt) if int(txt) > 0 else None
    await state.update_data(max_activations=limit)
    await state.set_state(AdminPromoState.waiting_expiry)

    await message.answer(
        "⏳ *Шаг 5 из 5:* Срок действия промокода в днях от сегодняшней даты "
        "(например: `30` дней, или `0` если промокод действует бессрочно):",
        reply_markup=get_admin_back_keyboard(),
        parse_mode="Markdown"
    )

@router.message(AdminPromoState.waiting_expiry, F.text)
async def process_promo_expiry(message: Message, state: FSMContext):
    if not await db.can_manage_promos(message.from_user.id):
        return

    txt = message.text.strip()
    if not txt.isdigit():
        await message.answer("Пожалуйста, введите число дней (0 для бессрочного):")
        return

    expires_days = int(txt) if int(txt) > 0 else None
    data = await state.get_data()
    await state.clear()

    code = data["code"]
    p_type = data["promo_type"]
    val = data["value"]
    max_acts = data.get("max_activations")

    days = val if p_type == "days" else 0
    discount_val = val if p_type == "discount" else 0

    success, result = await db.create_db_promo_code(
        code=code,
        promo_type=p_type,
        days=days,
        discount_val=discount_val,
        max_activations=max_acts,
        expires_days=expires_days,
        description=f"Создан администратором {message.from_user.id}"
    )

    if success:
        limit_text = f"{max_acts} чел." if max_acts else "без ограничений"
        exp_text = f"{expires_days} дн." if expires_days else "бессрочно"
        val_text = f"{days} дней Premium" if p_type == "days" else f"{discount_val}% скидка"

        await message.answer(
            f"🎉 *Промокод успешно создан!*\n\n"
            f"• Код: `{code}`\n"
            f"• Награда: *{val_text}*\n"
            f"• Лимит: *{limit_text}*\n"
            f"• Срок: *{exp_text}*\n\n"
            f"Пользователи могут ввести его в боте в разделе Stork Premium -> Промокод.",
            reply_markup=get_promo_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"❌ Ошибка создания промокода: код `{code}` уже существует в базе.",
            reply_markup=get_promo_menu_keyboard(),
            parse_mode="Markdown"
        )

# ==========================================
# Раздел: Скачивание бэкапа базы данных
# ==========================================

@router.callback_query(F.data == "admin_backup")
async def cb_admin_backup(callback: CallbackQuery):
    """Моментальная выгрузка файла stork_bot.db в чат Telegram"""
    if not await db.can_download_backup(callback.from_user.id):
        await callback.answer("У вас нет прав для скачивания базы данных", show_alert=True)
        return

    if not os.path.exists(DB_PATH):
        await callback.answer("Файл базы данных не найден!", show_alert=True)
        return

    size_bytes = os.path.getsize(DB_PATH)
    size_kb = round(size_bytes / 1024, 1)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_filename = f"stork_backup_{timestamp}.db"

    await callback.answer("Формирую резервную копию...")

    try:
        input_file = FSInputFile(DB_PATH, filename=backup_filename)
        caption = (
            f"💾 *Резервная копия базы данных Stork*\n\n"
            f"• Файл: `{backup_filename}`\n"
            f"• Размер: *{size_kb} КБ*\n"
            f"• Дата выгрузки: *{datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}*\n\n"
            f"Храните этот файл в надежном месте. При необходимости его можно "
            f"скопировать на любой сервер и продолжить работу без потерь данных."
        )
        await callback.message.answer_document(
            document=input_file,
            caption=caption,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка отправки бэкапа базы данных: {e}")
        await callback.message.answer(f"❌ Ошибка отправки бэкапа: {e}")

# ==========================================
# Раздел: Рассылка сообщений пользователям
# ==========================================

@router.callback_query(F.data == "admin_broadcast_menu")
async def cb_admin_broadcast_menu(callback: CallbackQuery, state: FSMContext):
    """Выбор аудитории для рассылки"""
    if not await db.can_broadcast(callback.from_user.id):
        await callback.answer("У вас нет прав для создания рассылок", show_alert=True)
        return

    await state.set_state(AdminBroadcastState.waiting_audience)
    text = (
        "📢 *Рассылка сообщений от Stork*\n\n"
        "Выберите целевую аудиторию для отправки сообщения:"
    )
    await callback.message.edit_text(text, reply_markup=get_broadcast_audience_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(AdminBroadcastState.waiting_audience, F.data.startswith("adm_bc_aud:"))
async def process_broadcast_audience(callback: CallbackQuery, state: FSMContext):
    if not await db.can_broadcast(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    aud = callback.data.split(":")[1]
    await state.update_data(audience=aud)
    await state.set_state(AdminBroadcastState.waiting_text)

    aud_title = {
        "all": "Всем пользователям",
        "premium": "Только Premium-пользователям",
        "free": "Только бесплатным пользователям"
    }.get(aud, aud)

    user_ids = await db.get_broadcast_user_ids(aud)
    count = len(user_ids)

    text = (
        f"📢 *Аудитория:* {aud_title}\n"
        f"👥 Получателей: *{count}*\n\n"
        f"Теперь напишите текст рассылки (поддерживается разметка Markdown). "
        f"Сообщение будет отправлено от имени бота всем выбранным пользователям.\n\n"
        f"Для отмены нажмите кнопку ниже:"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_back_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.message(AdminBroadcastState.waiting_text, F.text)
async def process_broadcast_text(message: Message, state: FSMContext):
    if not await db.can_broadcast(message.from_user.id):
        return

    bc_text = message.text
    await state.update_data(broadcast_text=bc_text)
    data = await state.get_data()
    aud = data.get("audience", "all")
    user_ids = await db.get_broadcast_user_ids(aud)

    await state.set_state(AdminBroadcastState.confirm_send)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Подтвердить и отправить", callback_data="adm_bc_confirm")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_main")]
    ])

    await message.answer(
        f"Предпросмотр сообщения для *{len(user_ids)}* пользователей:\n\n"
        f"──────────\n{bc_text}\n──────────\n\n"
        f"Отправить сообщение выбранной аудитории?",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@router.callback_query(AdminBroadcastState.confirm_send, F.data == "adm_bc_confirm")
async def cb_broadcast_confirm(callback: CallbackQuery, state: FSMContext):
    if not await db.can_broadcast(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    data = await state.get_data()
    bc_text = data.get("broadcast_text", "")
    aud = data.get("audience", "all")
    await state.clear()

    user_ids = await db.get_broadcast_user_ids(aud)
    await callback.message.edit_text(f"⏳ Начинаю рассылку для {len(user_ids)} пользователей...")

    sent_count = 0
    fail_count = 0

    for uid in user_ids:
        try:
            await callback.bot.send_message(uid, bc_text, parse_mode="Markdown")
            sent_count += 1
            await asyncio.sleep(0.05)  # Защита от лимитов Telegram
        except Exception:
            fail_count += 1

    report = (
        f"✅ *Рассылка успешно завершена!*\n\n"
        f"• Успешно доставлено: *{sent_count}*\n"
        f"• Не доставлено (заблокировали бота/удалены): *{fail_count}*\n"
        f"• Всего в выборке: *{len(user_ids)}*"
    )
    await callback.message.answer(report, reply_markup=get_admin_back_keyboard(), parse_mode="Markdown")
    await callback.answer("Рассылка завершена")
