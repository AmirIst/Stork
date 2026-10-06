import asyncio
import logging
import base64
import httpx
from typing import Optional, List, Dict
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

STORK_SYSTEM_PROMPT_RU = """
Ты: Stork (Аист) 🪶, персональный дружелюбный наставник немецкого языка.
Твоя цель: обучать языку в живом и непринужденном диалоге.

ОБЯЗАТЕЛЬНЫЙ 4-БЛОЧНЫЙ ФОРМАТ ДЛЯ ЛЮБОГО НЕ-НЕМЕЦКОГО ЯЗЫКА (РУССКИЙ, АНГЛИЙСКИЙ И ДР.):
Если пользователь пишет НЕ на немецком языке (на русском, английском или любом другом):
Всегда строй свой ответ строго из 4 аккуратных блоков:

1. Перевод фразы пользователя на немецкий:
🇩🇪 Auf Deutsch: <точный и естественный перевод>

2. Полезный разбор:
💡 Разбор: <кратко разбери 1-2 ключевых слова, артикль der/die/das или грамматику на понятном пользователю языке>

3. Твой дружелюбный ответ на вопрос или реплику пользователя:
<ответ на немецком языке> (<перевод на язык пользователя в скобках>)

4. Встречный вопрос для продолжения тренировки:
<простой вопрос на немецком уровня A1-A2> (<перевод на язык пользователя в скобках>)

ЕСЛИ ПОЛЬЗОВАТЕЛЬ ПИШЕТ НА НЕМЕЦКОМ:
1. Исправь ошибки (если есть) или похвали за правильную речь: ✅ Richtig: ... (с кратким пояснением правила).
2. Ответь по-немецки, в скобках дай перевод на родной язык пользователя и задай встречный вопрос на немецком.

ВАЖНО ПРО ПОВСЕДНЕВНЫЙ ДИАЛОГ:
Любые приветствия, знакомство, вопросы о тебе, делах, погоде, планах, городах, настроении (например: "Привет", "Как дела?", "Сколько тебе лет?", "Лондон", "Что делаешь?") — это ВАЖНЕЙШАЯ РАЗГОВОРНАЯ ПРАКТИКА!
Всегда охотно поддерживай такие темы по 4-блочному формату выше.

СТРОГИЕ РАМКИ:
Блокируй ТОЛЬКО полностью чуждые темы (написание кода, политика, новости мира, медицина):
"🪶 Я создан исключительно для изучения немецкого языка и не могу говорить на такие темы. Давай лучше потренируем полезные фразы, разберем грамматику или переведем твою мысль на немецкий!"

ПРАВИЛА ОФОРМЛЕНИЯ:
- Не используй длинные тире (em-dash). Заменяй на дефис или двоеточие.
- Ответ должен быть емким, живым и легким для чтения.
"""

STORK_SYSTEM_PROMPT_EN = """
You are Stork 🪶, a personal and encouraging German language tutor.
Your mission: teach German through lively, interactive dialogue.

MANDATORY 4-BLOCK FORMAT FOR ANY NON-GERMAN LANGUAGE (ENGLISH, RUSSIAN, SPANISH, ETC.):
Whenever the user writes in English, Russian, or any language other than German:
Always structure your reply strictly into these 4 clean blocks:

1. Natural German translation of user's phrase:
🇩🇪 Auf Deutsch: <accurate and natural German translation>

2. Vocabulary or grammar insight:
💡 Insight: <briefly explain 1-2 key words, articles der/die/das, or structure in the user's language>

3. Your friendly answer to the user's message/question:
<response in German> (<English translation in parentheses>)

4. Follow-up practice question:
<easy question in German A1-A2 level> (<English translation in parentheses>)

WHEN USER WRITES IN GERMAN:
1. Correct any mistakes or praise accuracy: ✅ Richtig: ... (with a brief explanation).
2. Reply in German, provide English translation in parentheses, and ask a follow-up question in German.

CASUAL TALK IS WELCOME:
Everyday questions, greetings, small talk, questions about you, cities, hobbies (e.g., "Hello", "How are you?", "London", "How old are you?", "What's up?") are ESSENTIAL language practice!
Always encourage these topics using the 4-block format above.

STRICT GUARDRAILS:
Reject ONLY completely foreign topics (writing software code, politics, world news, medical advice):
"🪶 I am dedicated exclusively to teaching German and cannot discuss such topics. Let's focus on practicing useful phrases, reviewing grammar, or translating your thoughts into German!"

FORMATTING RULES:
- Never use long em-dashes.
- Keep responses concise and encouraging.
"""

# Пул постоянных HTTP-соединений для минимальной задержки
_client: Optional[httpx.AsyncClient] = None

def get_ai_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=15.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=60.0),
            headers={"Content-Type": "application/json"}
        )
    return _client

# Модели в порядке приоритета: быстрые и с высокими квотами первыми
MODELS_CASCADE = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash"
]

async def execute_gemini_request(payload: dict) -> Optional[str]:
    """
    Выполнение запроса с моментальным каскадным переключением на запасные модели
    при исчерпании суточных квот (429) или пиках нагрузки (503).
    """
    client = get_ai_client()
    
    for model_name in MODELS_CASCADE:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][-1]["text"]
                return text
            elif response.status_code == 429:
                # Лимит модели исчерпан (наприм. 20 RPD на 2.5-flash), мгновенно переключаемся на следующую модель
                logger.warning(f"Модель {model_name} вернула 429 (лимит квоты исчерпан). Переключаемся на запасную...")
                continue
            elif response.status_code == 503:
                # Временный пик нагрузки на конкретной модели, пробуем следующую
                logger.warning(f"Модель {model_name} временно перегружена (503). Переключаемся на запасную...")
                continue
            else:
                logger.error(f"Gemini API error ({model_name}): {response.status_code} - {response.text}")
                continue
        except Exception as e:
            logger.warning(f"Сетевая ошибка при обращении к {model_name}: {e}. Пробуем следующую модель...")
            continue
            
    return None

async def get_ai_tutor_reply(
    user_message: str, 
    native_lang: str = "ru",
    history: Optional[list] = None
) -> str:
    """
    Отправить сообщение ученика ИИ-Аисту с контекстом предыдущих сообщений,
    отключенным thinkingBudget (для молниеносного ответа) и надежным лимитом токенов.
    """
    if not GEMINI_API_KEY:
        if native_lang == "ru":
            return (
                "🪶 *Аист слушает тебя!* (Оффлайн-режим)\n\n"
                f"Ты написал: _{user_message}_\n\n"
                "💡 *Совет от Аиста:* Чтобы включить режим живого диалога и перевод любых фраз, "
                "добавь ключ `GEMINI_API_KEY` в файл `.env` проекта.\n\n"
                "А пока ты можешь учить слова по категориям и тренировать артикли в меню! 🎯"
            )
        else:
            return (
                "🪶 *Stork is listening!* (Offline mode)\n\n"
                f"You wrote: _{user_message}_\n\n"
                "💡 *Stork's Tip:* To enable live AI conversation and translation, "
                "add your `GEMINI_API_KEY` to the `.env` file.\n\n"
                "In the meantime, feel free to explore categories and article trainer in the menu! 🎯"
            )

    system_instruction = STORK_SYSTEM_PROMPT_RU if native_lang == "ru" else STORK_SYSTEM_PROMPT_EN

    # Формируем цепочку сообщений для сохранения контекста разговора
    contents = []
    if history:
        for turn in history:
            role = "model" if turn.get("role") in ("model", "assistant") else "user"
            contents.append({
                "role": role,
                "parts": [{"text": turn.get("message", "")}]
            })

    # Добавляем свежее сообщение ученика
    contents.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    # Используем 800 токенов и каскад скоростных моделей
    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.6,
            "maxOutputTokens": 800
        }
    }

    raw_text = await execute_gemini_request(payload)
    if raw_text:
        clean_text = raw_text.replace("—", "-").replace("–", "-")
        return f"🪶 *Stork:*\n\n{clean_text}"

    # Если все попытки и запасные модели были временно недоступны
    if native_lang == "ru":
        return "🪶 У серверов Google сейчас временный пик нагрузки. Пожалуйста, напиши еще разок через несколько секунд!"
    else:
        return "🪶 Google servers are experiencing a temporary spike in traffic. Please try again in a few seconds!"

async def get_ai_tutor_voice_reply(
    audio_bytes: bytes,
    mime_type: str = "audio/ogg",
    native_lang: str = "ru",
    history: Optional[list] = None
) -> str:
    """
    Обработка входящего голосового сообщения от ученика.
    Gemini слушает аудио, транскрибирует, комментирует речь и отвечает по правилам Stork.
    """
    if not GEMINI_API_KEY:
        if native_lang == "ru":
            return "🪶 Голосовой режим требует подключения `GEMINI_API_KEY` в файле `.env`."
        else:
            return "🪶 Voice mode requires `GEMINI_API_KEY` configured in `.env`."

    system_instruction = STORK_SYSTEM_PROMPT_RU if native_lang == "ru" else STORK_SYSTEM_PROMPT_EN
    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")

    contents = []
    if history:
        for turn in history:
            role = "model" if turn.get("role") in ("model", "assistant") else "user"
            contents.append({
                "role": role,
                "parts": [{"text": turn.get("message", "")}]
            })

    audio_prompt_text = (
        "Послушай это аудиосообщение ученика. Обязательно начни ответ с точной расшифровки сказанного: "
        "🎙️ *Ты сказал:* «...» (если говорил по-немецки, то: 🎙️ *Du hast gesagt:* «...»). "
        "Далее разбери ошибки или похвали за речь, переведи и ответь по 4-блочному стандарту наставника Stork."
        if native_lang == "ru"
        else "Listen to this audio from the student. Always start with an exact transcription: "
        "🎙️ *You said:* \"...\" (or if in German: 🎙️ *Du hast gesagt:* \"...\"). "
        "Then evaluate mistakes or praise pronunciation, translate, and reply following Stork's 4-block format."
    )

    contents.append({
        "role": "user",
        "parts": [
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": b64_audio
                }
            },
            {
                "text": audio_prompt_text
            }
        ]
    })

    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.6,
            "maxOutputTokens": 800
        }
    }

    raw_text = await execute_gemini_request(payload)
    if raw_text:
        clean_text = raw_text.replace("—", "-").replace("–", "-")
        return f"🪶 *Stork:*\n\n{clean_text}"

    if native_lang == "ru":
        return "🪶 У серверов Google сейчас временный пик нагрузки. Пожалуйста, отправь голосовое еще разок через несколько секунд!"
    else:
        return "🪶 Google servers are experiencing high traffic. Please send your voice note again in a few moments!"

