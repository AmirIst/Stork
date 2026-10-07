import random
import logging
from typing import Dict, Any, Optional
import httpx
from config import GEMINI_API_KEY
from services.ai_tutor import get_ai_client

logger = logging.getLogger(__name__)

GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash"
]

SPRECHEN_TASKS = [
    # A1 Tasks
    {
        "id": "spr_a1_1",
        "level": "A1",
        "teil": "Teil 1: Sich vorstellen",
        "title": {
            "ru": "Знакомство и рассказ о себе",
            "en": "Self-introduction"
        },
        "instructions": {
            "ru": "Представься экзаменатору на немецком языке:\n• Имя и возраст (Name, Alter)\n• Страна и город (Land, Wohnort)\n• Языки и профессия (Sprachen, Beruf)\n• Хобби (Hobbys)\n• Назови по буквам свою фамилию или продиктуй номер телефона.",
            "en": "Introduce yourself to the examiner in German:\n• Name and age\n• Country and hometown\n• Languages and profession\n• Hobbies\n• Spell your surname or dictate a phone number."
        },
        "target_duration": "30-45 сек",
        "starter_hint": {
            "ru": "Начни с: 'Guten Tag! Ich heiße... Ich bin... Jahre alt...'",
            "en": "Start with: 'Guten Tag! Ich heiße... Ich bin... Jahre alt...'"
        }
    },
    {
        "id": "spr_a1_2",
        "level": "A1",
        "teil": "Teil 2: Um Informationen bitten",
        "title": {
            "ru": "Диалог в магазине (Thema: Einkaufen)",
            "en": "Shop conversation (Shopping)"
        },
        "instructions": {
            "ru": "Экзаменатор показывает карточку со словом: *Brötchen / Brot*.\n• Поздоровайся и спроси, свежий ли хлеб.\n• Спроси цену и закажи 3 булочки.\n• Поблагодари продавца.",
            "en": "Examiner shows a word card: *Brötchen / Brot*.\n• Greet and ask if the bread is fresh.\n• Ask for the price and order 3 rolls.\n• Thank the cashier."
        },
        "target_duration": "30-45 сек",
        "starter_hint": {
            "ru": "Начни с: 'Hallo! Wie viel kosten diese Brötchen?...'",
            "en": "Start with: 'Hallo! Wie viel kosten diese Brötchen?...'"
        }
    },
    # A2 Tasks
    {
        "id": "spr_a2_1",
        "level": "A2",
        "teil": "Teil 2: Von sich erzählen",
        "title": {
            "ru": "Мой последний отпуск или поездка",
            "en": "My last vacation or trip"
        },
        "instructions": {
            "ru": "Расскажи экзаменатору о своей последней поездке:\n• Куда и с кем ты ездил (Wohin, mit wem)?\n• На каком транспорте добирался (Verkehrsmittel)?\n• Какая была погода и что ты делал (Wetter, Aktivitäten)?\n• Что понравилось больше всего?",
            "en": "Tell the examiner about your last vacation:\n• Where and with whom did you travel?\n• What transportation did you use?\n• How was the weather and what did you do?\n• What did you like the most?"
        },
        "target_duration": "60-90 сек",
        "starter_hint": {
            "ru": "Начни с: 'Letzten Sommer bin ich nach... gefahren. Ich war dort mit...'",
            "en": "Start with: 'Letzten Sommer bin ich nach... gefahren. Ich war dort mit...'"
        }
    },
    {
        "id": "spr_a2_2",
        "level": "A2",
        "teil": "Teil 3: Gemeinsam etwas planen",
        "title": {
            "ru": "Совместный подарок для коллеги",
            "en": "Planning a gift for a colleague"
        },
        "instructions": {
            "ru": "Твоя коллега Анна празднует юбилей. Спланируй подарок вместе с экзаменатором:\n• Что подарить (книга, сертификат, цветы)?\n• Сколько денег собрать?\n• Когда и где купить подарок?\n• Когда вручить?",
            "en": "Your colleague Anna is celebrating a jubilee. Plan a gift together with the examiner:\n• What to buy (book, voucher, flowers)?\n• How much money to budget?\n• When and where to shop?\n• When to present the gift?"
        },
        "target_duration": "60-90 сек",
        "starter_hint": {
            "ru": "Начни с: 'Hallo! Weißt du, dass Anna Geburtstag hat? Wollen wir ihr ein Geschenk kaufen?...'",
            "en": "Start with: 'Hallo! Weißt du, dass Anna Geburtstag hat? Wollen wir ihr ein Geschenk kaufen?...'"
        }
    },
    # B1 Tasks
    {
        "id": "spr_b1_1",
        "level": "B1",
        "teil": "Teil 2: Ein Thema präsentieren",
        "title": {
            "ru": "Нужны ли детям смартфоны в начальной школе?",
            "en": "Do children need smartphones in primary school?"
        },
        "instructions": {
            "ru": "Проведи короткую презентацию по структуре экзамена Goethe B1:\n1. Введение и личный опыт (Meine persönlichen Erfahrungen)\n2. Ситуация в твоей родной стране (Situation in meinem Heimatland)\n3. Преимущества и недостатки (Vor- und Nachteile)\n4. Свое мнение и заключение (Meine Meinung und Abschluss)",
            "en": "Give a short structured presentation for Goethe B1:\n1. Introduction & personal experience\n2. Situation in your home country\n3. Advantages and disadvantages\n4. Your opinion and conclusion"
        },
        "target_duration": "90-120 сек",
        "starter_hint": {
            "ru": "Начни с: 'Das Thema meiner Präsentation ist... Zuerst möchte ich über meine Erfahrungen sprechen...'",
            "en": "Start with: 'Das Thema meiner Präsentation ist... Zuerst möchte ich über meine Erfahrungen sprechen...'"
        }
    },
    {
        "id": "spr_b1_2",
        "level": "B1",
        "teil": "Teil 1: Gemeinsam etwas planen",
        "title": {
            "ru": "Организация вечеринки-сюрприза",
            "en": "Organizing a surprise party"
        },
        "instructions": {
            "ru": "Вы с экзаменатором готовите праздник для общего друга Маркуса:\n• Где провести (дома, в кафе или на природе)?\n• Кого пригласить и как сохранить секрет?\n• Еда и напитки (кто готовит, что купить)?\n• Музыка и развлечения.",
            "en": "You and the examiner are organizing a surprise party for Markus:\n• Location (home, café, or outdoors)?\n• Guest list and keeping it secret?\n• Food and drinks?\n• Music and activities."
        },
        "target_duration": "90-120 сек",
        "starter_hint": {
            "ru": "Начни с: 'Hallo! Ich habe eine Idee: Lass uns eine Überraschungsparty für Markus machen! Was denkst du?...'",
            "en": "Start with: 'Hallo! Ich habe eine Idee: Lass uns eine Überraschungsparty für Markus machen! Was denkst du?...'"
        }
    }
]

def get_sprechen_task(level: Optional[str] = None, task_id: Optional[str] = None) -> Dict[str, Any]:
    """Выбрать устное задание по уровню или идентификатору"""
    if task_id:
        for t in SPRECHEN_TASKS:
            if t["id"] == task_id:
                return t
    candidates = SPRECHEN_TASKS
    if level and level != "RANDOM":
        candidates = [t for t in SPRECHEN_TASKS if t["level"] == level]
    return random.choice(candidates if candidates else SPRECHEN_TASKS)

async def evaluate_student_speaking(task: Dict[str, Any], transcribed_text: str, native_lang: str = "ru") -> str:
    """Оценка устного ответа ученика официальным экзаменатором Goethe & Telc"""
    if not GEMINI_API_KEY:
        return (
            "🪶 Ответ записан, но ключ Gemini API не настроен."
            if native_lang == "ru"
            else "🪶 Audio recorded, but Gemini API key is missing."
        )

    system_instruction = f"""
Ты официальный и доброжелательный экзаменатор устной части Goethe-Zertifikat и Telc ({task['level']}).
Твоя цель: оценить устный ответ ученика (транскрипцию его речи), разобрать ошибки и дать идеальный немецкий образец ответа.

Язык анализа: {'русский' if native_lang == 'ru' else 'английский'}.
Язык примеров: немецкий.
Не используй длинные тире (—).

Структура отчета:
1. 🏆 **Итоговый балл (из 100)** и вердикт: Сдан / Не сдан (проходной балл 60/100).
2. 🗣️ **Произношение и беглость (Aussprache & Redefluss)**: как звучит речь, естественность пауз.
3. 🔍 **Грамматика и порядок слов (Satzbau & Grammatik)**: выдели ошибки в глаголах, падежах и порядке слов, покажи как правильно.
4. 📚 **Словарный запас (Wortschatz)**: разнообразие слов, связки (weil, deshalb, obwohl).
5. 🌟 **Musterantwort (Идеальный образец ответа от экзаменатора)**:
Напиши законченный образец идеального ответа на немецком языке на 40-70 слов под заголовком:
🇩🇪 **Musterantwort:**
[Здесь связный текст на немецком]
"""

    user_prompt = f"""
Экзаменационное задание:
Уровень: {task['level']}
Часть: {task['teil']}
Тема: {task['title'].get(native_lang, task['title'].get('en'))}
Инструкция: {task['instructions'].get(native_lang, task['instructions'].get('en'))}

Транскрипция устного ответа ученика:
"{transcribed_text}"

Пожалуйста, оцени ответ строго по критериям экзаменационной комиссии!
"""

    client = get_ai_client()
    for model_name in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": user_prompt}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 900}
        }
        try:
            res = await client.post(url, json=payload, timeout=16.0)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
        except Exception as e:
            logger.warning(f"Ошибка модели {model_name} для Sprechen: {e}")
            continue

    return (
        "🪶 Не удалось связаться с экзаменатором. Попробуй еще раз через минуту!"
        if native_lang == "ru"
        else "🪶 Could not connect to examiner. Please try again in a minute!"
    )

def extract_sprechen_musterantwort(review_text: str) -> str:
    """Извлечение текста Musterantwort для синтеза речи экзаменатора"""
    if "Musterantwort:" in review_text:
        parts = review_text.split("Musterantwort:")
        candidate = parts[-1].strip()
        lines = []
        for line in candidate.split("\n"):
            line_str = line.strip()
            if not line_str:
                continue
            if line_str.startswith("#") or line_str.startswith("💡") or line_str.startswith("🏆"):
                break
            lines.append(line_str)
        if lines:
            return " ".join(lines).replace("*", "").replace("_", "")
    return ""
