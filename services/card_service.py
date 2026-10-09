import os
import io
import urllib.parse
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

def get_font(size: int, bold: bool = False):
    """Попытка загрузить системный шрифт или стандартный Pillow шрифт"""
    font_names = [
        "arialbd.ttf" if bold else "arial.ttf",
        "seguiemj.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "calibrib.ttf" if bold else "calibri.ttf"
    ]
    for name in font_names:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None

def draw_rounded_rect(draw: ImageDraw.ImageDraw, xy, radius: int, fill, outline=None, width=1):
    """Рисует скругленный прямоугольник"""
    try:
        draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
    except Exception:
        draw.rectangle(xy, fill=fill, outline=outline, width=width)

def generate_profile_card_image(user_data: Dict[str, Any]) -> bytes:
    """
    Генерирует графическую карточку ученика (Passport / Profile Card) 1080x600 пикселей.
    """
    width, height = 1080, 600
    
    # Цветовая палитра: глубокий премиальный темно-синий градиент
    bg_color = (15, 23, 42)      # Slate 900
    card_bg = (30, 41, 59)       # Slate 800
    accent_gold = (245, 158, 11) # Amber 500
    accent_cyan = (56, 189, 248) # Sky 400
    text_white = (255, 255, 255)
    text_muted = (148, 163, 184)
    border_color = (51, 65, 85)

    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # 1. Внешняя фоновая карточка с легкой рамкой
    draw_rounded_rect(draw, [30, 30, width - 30, height - 30], radius=24, fill=card_bg, outline=border_color, width=2)

    # Шрифты
    title_font = get_font(36, bold=True)
    subtitle_font = get_font(22, bold=False)
    stat_val_font = get_font(42, bold=True)
    stat_lbl_font = get_font(20, bold=False)
    footer_font = get_font(20, bold=False)

    # 2. Верхняя шапка: логотип и заголовок
    # Акцентная полоса сверху
    draw.rectangle([60, 60, 66, 130], fill=accent_gold)
    
    name = user_data.get("first_name") or "Ученик"
    username = user_data.get("username")
    uname_str = f"@{username}" if username else f"ID: {user_data.get('user_id', '')}"
    
    draw.text((85, 60), f"STORK GERMAN PASSPORT", fill=accent_gold, font=title_font)
    draw.text((85, 105), f"{name} ({uname_str})", fill=text_white, font=subtitle_font)

    # Бейдж статуса справа
    is_vip = user_data.get("is_lifetime_vip") or user_data.get("is_premium")
    badge_text = "⭐️ LIFETIME VIP" if user_data.get("is_lifetime_vip") else ("⭐️ PREMIUM" if is_vip else "FREE STUDENT")
    badge_bg = (180, 83, 9) if is_vip else (71, 85, 105)
    
    badge_w, badge_h = 220, 44
    badge_x = width - 80 - badge_w
    draw_rounded_rect(draw, [badge_x, 75, badge_x + badge_w, 75 + badge_h], radius=12, fill=badge_bg)
    draw.text((badge_x + 25, 85), badge_text, fill=text_white, font=get_font(20, bold=True))

    # Разделительная линия
    draw.line([(60, 160), (width - 60, 160)], fill=border_color, width=1)

    # 3. 4 блока ключевой статистики в сетке 2x2
    stats = [
        {"val": str(user_data.get("placement_level") or "A1"), "lbl": "УРОВЕНЬ CEFR", "color": accent_cyan},
        {"val": f"{user_data.get('known_words', 0)} / 3000", "lbl": "СЛОВАРНЫЙ ЗАПАС", "color": (52, 211, 153)}, # Emerald
        {"val": f"🔥 {user_data.get('streak', 0)} дн.", "lbl": "СЕРИЯ ДНЕЙ", "color": (251, 146, 60)}, # Orange
        {"val": f"⭐️ {user_data.get('score', 0)}", "lbl": "БАЛЛЫ ОПЫТА (XP)", "color": accent_gold},
    ]

    box_w = 440
    box_h = 130
    coords = [
        (60, 190),                 # Top Left
        (width - 60 - box_w, 190), # Top Right
        (60, 350),                 # Bottom Left
        (width - 60 - box_w, 350)  # Bottom Right
    ]

    for (bx, by), stat in zip(coords, stats):
        draw_rounded_rect(draw, [bx, by, bx + box_w, by + box_h], radius=16, fill=(15, 23, 42), outline=border_color, width=1)
        # Маленькая акцентная полоска слева у каждого блока
        draw.rectangle([bx, by + 20, bx + 6, by + box_h - 20], fill=stat["color"])
        draw.text((bx + 30, by + 25), stat["val"], fill=stat["color"], font=stat_val_font)
        draw.text((bx + 30, by + 80), stat["lbl"], fill=text_muted, font=stat_lbl_font)

    # 4. Подвал: реферальная плашка
    draw.line([(60, 515), (width - 60, 515)], fill=border_color, width=1)
    draw.text((60, 535), "🪶 Бот для изучения немецкого: t.me/stork_learn_german_bot", fill=text_muted, font=footer_font)
    draw.text((width - 340, 535), "Учи немецкий каждый день!", fill=accent_gold, font=footer_font)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.getvalue()

def generate_diagnostic_card_image(exam_data: Dict[str, Any]) -> bytes:
    """
    Генерирует сертификат готовности к экзамену (Goethe B1 / Telc B1) 1080x600 пикселей.
    """
    width, height = 1080, 600
    
    bg_color = (15, 23, 42)
    card_bg = (30, 41, 59)
    accent_emerald = (16, 185, 129)
    accent_gold = (245, 158, 11)
    text_white = (255, 255, 255)
    text_muted = (148, 163, 184)
    border_color = (51, 65, 85)

    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    draw_rounded_rect(draw, [30, 30, width - 30, height - 30], radius=24, fill=card_bg, outline=accent_emerald, width=2)

    title_font = get_font(34, bold=True)
    subtitle_font = get_font(22, bold=False)
    score_font = get_font(72, bold=True)
    stat_lbl_font = get_font(20, bold=False)
    footer_font = get_font(20, bold=False)

    exam_title = exam_data.get("exam_title", "Goethe / telc B1")
    draw.text((60, 60), f"CERTIFICATE OF EXAM READINESS", fill=accent_emerald, font=title_font)
    draw.text((60, 105), f"Экзаменационный тренажер Stork • {exam_title}", fill=text_muted, font=subtitle_font)

    draw.line([(60, 160), (width - 60, 160)], fill=border_color, width=1)

    # Центральный круглый блок с общим баллом
    overall = exam_data.get("overall_score", 0)
    status_text = exam_data.get("status_text", "ГОТОВ К ЭКЗАМЕНУ")
    cefr = exam_data.get("estimated_cefr", "B1")

    draw.text((60, 200), f"{overall}%", fill=accent_emerald, font=score_font)
    draw.text((60, 290), f"УРОВЕНЬ ГОТОВНОСТИ: {status_text} ({cefr})", fill=text_white, font=get_font(26, bold=True))

    # Сетка навыков справа
    skills = [
        {"name": "📖 Чтение (Lesen)", "score": f"{exam_data.get('lesen_score', 0)}%"},
        {"name": "🎧 Аудирование (Hören)", "score": f"{exam_data.get('hoeren_score', 0)}%"},
        {"name": "✍️ Письмо (Schreiben)", "score": f"{exam_data.get('schreiben_score', 0)}%"},
        {"name": "🗣 Говорение (Sprechen)", "score": f"{exam_data.get('sprechen_score', 0)}%"},
    ]

    sx = 560
    sy = 190
    for i, sk in enumerate(skills):
        y = sy + (i * 65)
        draw_rounded_rect(draw, [sx, y, sx + 440, y + 55], radius=10, fill=(15, 23, 42), outline=border_color, width=1)
        draw.text((sx + 20, y + 15), sk["name"], fill=text_white, font=subtitle_font)
        draw.text((sx + 360, y + 15), sk["score"], fill=accent_gold, font=get_font(22, bold=True))

    draw.line([(60, 515), (width - 60, 515)], fill=border_color, width=1)
    draw.text((60, 535), "🪶 Проверь свой немецкий: t.me/stork_learn_german_bot", fill=text_muted, font=footer_font)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.getvalue()

def get_profile_card_share_content(user_data: Dict[str, Any], lang: str = "ru") -> Tuple[str, str]:
    """
    Формирует текст карточки ученика и готовую ссылку для Telegram Share.
    """
    name = user_data.get("first_name") or "Ученик"
    level = user_data.get("placement_level") or "A1"
    score = user_data.get("score") or 0
    streak = user_data.get("streak") or 0
    words = user_data.get("known_words") or 0
    user_id = user_data.get("user_id")
    ref_link = f"https://t.me/stork_learn_german_bot?start=ref_{user_id}"

    if lang == "ru":
        text = (
            f"🪶 *Карточка ученика Stork*\n\n"
            f"👤 *Ученик:* {name}\n"
            f"🎓 *Уровень немецкого:* *{level}*\n"
            f"📚 *Словарный запас:* *{words}* из 3000 слов\n"
            f"🔥 *Серия занятий:* *{streak}* дн. подряд\n"
            f"⭐️ *Очки опыта:* *{score}* XP\n\n"
            f"Учу немецкий в интерактивном Telegram-боте *Stork*! Присоединяйся:"
        )
        share_msg = f"Я учу немецкий в боте Stork! Мой уровень: {level}, выучено {words} слов. Попробуй и ты!"
    else:
        text = (
            f"🪶 *Stork Student Passport*\n\n"
            f"👤 *Student:* {name}\n"
            f"🎓 *German Level:* *{level}*\n"
            f"📚 *Vocabulary:* *{words}* / 3000 words\n"
            f"🔥 *Daily Streak:* *{streak}* days\n"
            f"⭐️ *Experience:* *{score}* XP\n\n"
            f"Learning German with AI tutor *Stork*! Join me:"
        )
        share_msg = f"I'm learning German with Stork! My level is {level}, {words} words mastered. Check it out!"

    share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote(share_msg)}"
    return text, share_url

def get_diagnostic_share_content(exam_data: Dict[str, Any], lang: str = "ru") -> Tuple[str, str]:
    """
    Формирует текст для шеринга сертификата готовности к экзамену.
    """
    overall = exam_data.get("overall_score", 0)
    cefr = exam_data.get("estimated_cefr", "B1")
    exam_title = exam_data.get("exam_title", "Goethe / telc B1")
    user_id = exam_data.get("user_id", "")
    ref_link = f"https://t.me/stork_learn_german_bot?start=ref_{user_id}"

    if lang == "ru":
        text = (
            f"🏆 *Сертификат готовности к экзамену Stork*\n\n"
            f"🎯 *Экзамен:* {exam_title}\n"
            f"📊 *Результат диагностики:* *{overall}% готовности*\n"
            f"🎓 *Подтвержденный уровень:* *{cefr}*\n\n"
            f"Пройди бесплатный тест на готовность к экзамену в Stork:"
        )
        share_msg = f"Я прошел диагностику {exam_title} в боте Stork с результатом {overall}% ({cefr})! Проверь свой уровень:"
    else:
        text = (
            f"🏆 *Stork Exam Readiness Certificate*\n\n"
            f"🎯 *Exam:* {exam_title}\n"
            f"📊 *Score:* *{overall}% readiness*\n"
            f"🎓 *Level:* *{cefr}*\n\n"
            f"Test your German exam readiness for free with Stork:"
        )
        share_msg = f"I completed the {exam_title} readiness test in Stork: {overall}% ({cefr})! Check yours:"

    share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote(share_msg)}"
    return text, share_url
