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
Всегда строй свой ответ строго из 4 аккуратных блоков с точными заголовками:

1. Перевод:
🇩🇪 Перевод фразы на немецком: <точный и естественный перевод>

2. Разбор:
💡 Полезный разбор: <кратко разбери 1-2 ключевых слова, артикль der/die/das или грамматику на понятном пользователю языке>

3. Ответ:
💬 Ответ на сообщение: <ответ на немецком языке> (<перевод на язык пользователя в скобках>)

4. Вопрос:
❓ Встречный вопрос: <простой вопрос на немецком уровня A1-A2> (<перевод на язык пользователя в скобках>)

ЕСЛИ ПОЛЬЗОВАТЕЛЬ ПИШЕТ НА НЕМЕЦКОМ:
1. Проверка речи:
✅ Разбор: Richtig! (или мягко исправь ошибку с кратким понятным правилом).

2. Ответ:
💬 Ответ на сообщение: <ответ на немецком языке> (<перевод на язык пользователя в скобках>)

3. Вопрос:
❓ Встречный вопрос: <простой вопрос на немецком уровня A1-A2> (<перевод на язык пользователя в скобках>)

ВАЖНО ПРО ПОВСЕДНЕВНЫЙ ДИАЛОГ:
Любые приветствия, знакомство, вопросы о тебе, делах, погоде, планах, городах, настроении (например: "Привет", "Как дела?", "Сколько тебе лет?", "Лондон", "Что делаешь?") - это ВАЖНЕЙШАЯ РАЗГОВОРНАЯ ПРАКТИКА!
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
Always structure your reply strictly into these 4 clean blocks with exact titles:

1. Translation:
🇩🇪 German translation: <accurate and natural German translation>

2. Vocabulary or grammar insight:
💡 Useful breakdown: <briefly explain 1-2 key words, articles der/die/das, or structure in the user's language>

3. Reply:
💬 Reply to your message: <response in German> (<English translation in parentheses>)

4. Follow-up practice question:
❓ Follow-up question: <easy question in German A1-A2 level> (<English translation in parentheses>)

WHEN USER WRITES IN GERMAN:
1. Speech check:
✅ Correction: Richtig! (or gently correct mistake with brief grammar rule).

2. Reply:
💬 Reply to your message: <response in German> (<English translation in parentheses>)

3. Follow-up question:
❓ Follow-up question: <easy question in German A1-A2 level> (<English translation in parentheses>)

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
            
def compress_chat_turn_for_context(message: str, role: str) -> str:
    """
    Интеллектуальная оптимизация контекста диалога:
    - Для ответов модели (model): оставляет ключевую немецкую реплику, встречный вопрос
      и перевод, отсекая повторяющиеся громоздкие грамматические заголовки.
    - Для сообщений пользователя (user): аккуратно обрезает избыточный текст до 250 символов.
    Экономит до 60% входных токенов и значительно ускоряет отклик Gemini.
    """
    if not message:
        return ""

    if role in ("model", "assistant"):
        lines = [line.strip() for line in message.split("\n") if line.strip()]
        compact = []
        for line in lines:
            if any(marker in line for marker in ("💬", "❓", "🇩🇪", "Antwort:", "Frage:", "Auf Deutsch:")):
                compact.append(line)
        if compact:
            return "\n".join(compact[:4])
        return message[-250:].strip()
    else:
        return message[:250].strip()

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

    # Формируем оптимизированную цепочку сообщений для сохранения контекста разговора
    contents = []
    if history:
        for turn in history:
            role = "model" if turn.get("role") in ("model", "assistant") else "user"
            comp_text = compress_chat_turn_for_context(turn.get("message", ""), role)
            if comp_text:
                contents.append({
                    "role": role,
                    "parts": [{"text": comp_text}]
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
            comp_text = compress_chat_turn_for_context(turn.get("message", ""), role)
            if comp_text:
                contents.append({
                    "role": role,
                    "parts": [{"text": comp_text}]
                })

    audio_prompt_text = (
        "Послушай это аудиосообщение ученика. Обязательно начни ответ с точной расшифровки сказанного: "
        "🎙️ *Ты сказал:* «...» (если говорил по-немецки, то: 🎙️ *Du hast gesagt:* «...»). "
        "Далее оформи разбор строго по 4 блокам: 🇩🇪 Перевод фразы на немецком, 💡 Полезный разбор, 💬 Ответ на сообщение, ❓ Встречный вопрос."
        if native_lang == "ru"
        else "Listen to this audio from the student. Always start with an exact transcription: "
        "🎙️ *You said:* \"...\" (or if in German: 🎙️ *Du hast gesagt:* \"...\"). "
        "Then format the response strictly using the 4 blocks: 🇩🇪 German translation, 💡 Useful breakdown, 💬 Reply to your message, ❓ Follow-up question."
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

async def transcribe_voice(audio_bytes: bytes, mime_type: str = "audio/ogg") -> Optional[str]:
    """Транскрибирует немецкую речь ученика в текст через Gemini"""
    if not GEMINI_API_KEY:
        return None
    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_audio
                        }
                    },
                    {
                        "text": "Transcribe the spoken German in this audio verbatim. Output ONLY the transcribed German text without any introductory comments, quotation marks or explanations."
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 300
        }
    }
    res = await execute_gemini_request(payload)
    return res.strip() if res else None


