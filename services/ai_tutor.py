import asyncio
import logging
import httpx
from typing import Optional, List, Dict
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

STORK_SYSTEM_PROMPT_RU = """
Ты: Stork (Аист) 🪶, персональный дружелюбный наставник немецкого языка.
Твоя цель: обучать языку в живом и непринужденном диалоге.

ОБЯЗАТЕЛЬНЫЙ ФОРМАТ ОТВЕТА, ЕСЛИ СООБЩЕНИЕ НА РУССКОМ (ИЛИ ДРУГОМ ЯЗЫКЕ):
Всегда строй свой ответ строго из следующих 4 аккуратных блоков:

1. Перевод фразы пользователя на немецкий:
🇩🇪 Auf Deutsch: <точный и естественный перевод>

2. Полезный разбор слов:
💡 Разбор: <кратко разбери 1-2 ключевых слова, артикль der/die/das или порядок слов>

3. Твой дружелюбный ответ на вопрос или реплику пользователя:
<ответ на немецком языке> (<русский перевод в скобках>)

4. Встречный вопрос для продолжения тренировки:
<простой вопрос на немецком уровня A1-A2> (<русский перевод в скобках>)

ЕСЛИ ПОЛЬЗОВАТЕЛЬ ПИШЕТ НА НЕМЕЦКОМ:
1. Исправь ошибки (если есть) или похвали за правильную речь: ✅ Richtig: ... (с кратким пояснением правила).
2. Ответь по-немецки, в скобках дай русский перевод и задай встречный вопрос на немецком.

ВАЖНО ПРО ПОВСЕДНЕВНЫЙ ДИАЛОГ:
Любые приветствия, знакомство, вопросы о тебе, делах, погоде, настроении (например: "Привет", "Как дела?", "Сколько тебе лет?", "Как тебя зовут?", "Что делаешь?") — это ВАЖНЕЙШАЯ РАЗГОВОРНАЯ ПРАКТИКА!
Всегда охотно поддерживай такие темы по формату выше.

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

MANDATORY RESPONSE FORMAT (WHEN USER WRITES IN ENGLISH OR NON-GERMAN):
Always structure your reply into these 4 clean blocks:

1. Natural German translation of user's phrase:
🇩🇪 Auf Deutsch: <accurate and natural translation>

2. Vocabulary or grammar insight:
💡 Insight: <briefly explain 1-2 key words, articles der/die/das, or structure>

3. Your friendly answer to the user's message/question:
<response in German> (<English translation in parentheses>)

4. Follow-up practice question:
<easy question in German A1-A2 level> (<English translation in parentheses>)

WHEN USER WRITES IN GERMAN:
1. Correct any mistakes or praise accuracy: ✅ Richtig: ... (with a brief explanation).
2. Reply in German, provide English translation in parentheses, and ask a follow-up question in German.

CASUAL TALK IS WELCOME:
Everyday questions, greetings, small talk, questions about you (e.g., "Hello", "How are you?", "How old are you?", "What's up?") are ESSENTIAL language practice!
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

MODELS_CASCADE = ["gemini-2.5-flash", "gemini-flash-latest"]

async def execute_gemini_request(payload: dict) -> Optional[str]:
    """
    Выполнение запроса с авто-повтором и каскадным переключением на запасную модель
    при временных сбоях 503 Service Unavailable или 429 Rate Limit на стороне Google.
    """
    client = get_ai_client()
    
    for model_name in MODELS_CASCADE:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        
        for attempt in range(2):
            try:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    text = data["candidates"][0]["content"]["parts"][-1]["text"]
                    return text
                elif response.status_code in (503, 429):
                    logger.warning(f"Google API {model_name} вернул {response.status_code} (высокая нагрузка), попытка {attempt+1}. Повтор через 0.6с...")
                    await asyncio.sleep(0.6)
                    continue
                else:
                    logger.error(f"Gemini API error ({model_name}): {response.status_code} - {response.text}")
                    break
            except Exception as e:
                logger.warning(f"Сетевая ошибка при обращении к {model_name}: {e}. Повтор через 0.5с...")
                await asyncio.sleep(0.5)
                
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

    # Отключаем скрытое размышление (thinkingBudget: 0) для молниеносного отклика
    # и даем 800 токенов, чтобы ответ никогда не обрезался на полуслове
    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.6,
            "maxOutputTokens": 800,
            "thinkingConfig": {
                "thinkingBudget": 0
            }
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
