"""
==============================================================================
НАСТРОЙКИ STORK PREMIUM, ПРОМОКОДОВ И РЕФЕРАЛЬНОЙ ПРОГРАММЫ
==============================================================================
Этот файл создан специально для тебя.
Здесь ты можешь в любой момент легко:
- Добавлять и удалять промокоды, менять количество дней для них.
- Менять срок бесплатного пробного периода (триала).
- Изменять цены тарифов в Telegram Stars (XTR) и добавлять новые опции.
- Настраивать условия реферальной программы (дни за друга, бонусы, скидки).

Все изменения сразу применяются в боте!
==============================================================================
"""

from typing import Dict, Any, List, Optional

# ------------------------------------------------------------------------------
# 1. БЕСПЛАТНЫЙ ПРОБНЫЙ ПЕРИОД (ТРИАЛ)
# ------------------------------------------------------------------------------
# Количество дней премиума, которое выдается каждому пользователю
# бесплатно один раз в жизни по кнопке пробного периода.
FREE_TRIAL_DAYS: int = 3


# ------------------------------------------------------------------------------
# 2. ПРОМОКОДЫ
# ------------------------------------------------------------------------------
# Список доступных промокодов. Каждый пользователь может активировать
# конкретный промокод только 1 раз (повторная активация запрещена).
#
# Как добавить новый промокод:
# Просто добавь новую строчку по образцу:
# "НОВЫЙ_КОД": {"days": 30, "description": "Подарок от партнера на 30 дней"},
PROMO_CODES: Dict[str, Dict[str, Any]] = {
    "STORKVIP": {
        "days": 30,
        "description": "VIP-доступ на 30 дней",
    },
    "STORK2026": {
        "days": 14,
        "description": "Праздничный промокод на 14 дней",
    },
    "AMIR": {
        "days": 30,
        "description": "Специальный промокод от Амира на 30 дней",
    },
    "DEUTSCH": {
        "days": 7,
        "description": "Стартовый бонус на 7 дней",
    },
    "FREEDOM": {
        "days": 30,
        "description": "Свободный доступ на 30 дней",
    },
}


# ------------------------------------------------------------------------------
# 3. ТАРИФЫ ОПЛАТЫ (TELEGRAM STARS ⭐️ И EUR)
# ------------------------------------------------------------------------------
# Список тарифов подписки, которые видит пользователь в меню оплаты.
#
# Поля:
# - id: уникальный идентификатор тарифа (plan_7d, plan_30d, plan_90d, plan_365d, plan_lifetime)
# - days: количество дней премиума
# - stars: стоимость в Telegram Stars (целое число)
# - price_eur: ориентировочная стоимость в евро
# - title_ru: название тарифа на русском
# - title_en: название тарифа на английском
# - is_monthly: True, если это месячный план
# - is_lifetime: True, если это пожизненный VIP-доступ
PREMIUM_PLANS: List[Dict[str, Any]] = [
    {
        "id": "plan_7d",
        "days": 7,
        "stars": 125,
        "price_eur": "2.50€",
        "title_ru": "7 дней (Спринт)",
        "title_en": "7 days (Sprint)",
        "is_monthly": False,
        "is_lifetime": False,
    },
    {
        "id": "plan_30d",
        "days": 30,
        "stars": 250,
        "price_eur": "5.00€",
        "title_ru": "1 месяц (Стандарт)",
        "title_en": "1 month (Standard)",
        "is_monthly": True,
        "is_lifetime": False,
    },
    {
        "id": "plan_90d",
        "days": 90,
        "stars": 600,
        "price_eur": "12.00€",
        "title_ru": "3 месяца (Интенсив)",
        "title_en": "3 months (Intensive)",
        "is_monthly": False,
        "is_lifetime": False,
    },
    {
        "id": "plan_365d",
        "days": 365,
        "stars": 1500,
        "price_eur": "30.00€",
        "title_ru": "1 год (Курс)",
        "title_en": "1 year (Full Course)",
        "is_monthly": False,
        "is_lifetime": False,
    },
    {
        "id": "plan_lifetime",
        "days": 36500,
        "stars": 2500,
        "price_eur": "50.00€",
        "title_ru": "👑 Вечный VIP (Навсегда)",
        "title_en": "👑 Lifetime VIP (Forever)",
        "is_monthly": False,
        "is_lifetime": True,
    },
]


# ------------------------------------------------------------------------------
# 4. РЕФЕРАЛЬНАЯ ПРОГРАММА (ПРИГЛАСИ ДРУГА)
# ------------------------------------------------------------------------------
# Настройки наград за приглашение друзей по персональной ссылке.
#
# - days_per_invite: сколько дней премиума дается за каждого приглашенного друга (1 день)
# - milestone_invites: цель/порог для супер-бонуса (10 человек)
# - milestone_bonus_days: дополнительный бонус в днях при достижении цели (14 дней).
#   В сумме пользователь получает 10 дней (по 1 за каждого) + 14 бонусных = 24 дня премиума за 10 человек!
# - milestone_discount_percent: процент скидки (0 = отключена пожизненная скидка)
REFERRAL_CONFIG: Dict[str, Any] = {
    "days_per_invite": 1,
    "milestone_invites": 10,
    "milestone_bonus_days": 14,         # 10 + 14 = 24 дня суммарно за 10 рефералов
    "milestone_discount_percent": 0,    # Без пожизненных скидок
}


# ------------------------------------------------------------------------------
# 5. ПОЖИЗНЕННЫЙ VIP (LIFETIME PREMIUM)
# ------------------------------------------------------------------------------
# Список Telegram ID или юзернеймов пользователей с вечным VIP-доступом.
LIFETIME_VIP_USERS: List[Any] = [
    6725392176,        # Твой основной Telegram ID (Amir)
    "@Amirist1",       # Твой юзернейм
]


# ------------------------------------------------------------------------------
# 6. ОПЛАТА КАРТОЙ ЧЕРЕЗ TRIBUTE (EUR / RUB / СБП)
# ------------------------------------------------------------------------------
# Здесь указываются прямые ссылки на оплату товаров в Tribute (https://tribute.tg).
TRIBUTE_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "plan_7d_url": None,
    "plan_30d_url": None,
    "plan_90d_url": None,
    "plan_365d_url": None,
    "plan_lifetime_url": None,
}


# ==============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С КОНФИГУРАЦИЕЙ
# ==============================================================================

def is_lifetime_vip_in_config(user_id: int, username: Optional[str] = None) -> bool:
    """Проверить, включен ли пользователь в список пожизненных VIP в конфиге"""
    if user_id in LIFETIME_VIP_USERS or str(user_id) in LIFETIME_VIP_USERS:
        return True

    if username:
        clean_user = username.lower().lstrip("@")
        for item in LIFETIME_VIP_USERS:
            if isinstance(item, str) and item.lower().lstrip("@") == clean_user:
                return True
    return False


def get_promo_info(code: Optional[str]) -> Optional[Dict[str, Any]]:
    """Найти промокод без учета регистра (STORKVIP, storkvip и т.д.)"""
    if not code:
        return None
    normalized = code.strip().upper()
    return PROMO_CODES.get(normalized)


def is_valid_promo(code: Optional[str]) -> bool:
    """Проверить, существует ли такой промокод"""
    return get_promo_info(code) is not None


def get_plan_by_id(plan_id: str) -> Optional[Dict[str, Any]]:
    """Найти тариф по идентификатору (например, plan_30d)"""
    for plan in PREMIUM_PLANS:
        if plan["id"] == plan_id:
            return plan
    return None


def get_plan_price(plan: Dict[str, Any], has_discount: bool = False) -> int:
    """
    Рассчитать цену тарифа с учетом скидки реферальной программы.
    Скидка применяется к тарифам, у которых is_monthly = True.
    """
    base_stars = int(plan.get("stars", 150))
    if has_discount and plan.get("is_monthly", False):
        discount = REFERRAL_CONFIG.get("milestone_discount_percent", 50)
        discounted = int(round(base_stars * (1.0 - discount / 100.0)))
        return max(1, discounted)
    return base_stars


def get_tribute_url(plan_id: str, has_discount: bool = False) -> Optional[str]:
    """Получить ссылку на оплату через Tribute для выбранного тарифа"""
    if not TRIBUTE_CONFIG.get("enabled", False):
        return None
    key = f"{plan_id}_url"
    return TRIBUTE_CONFIG.get(key)

