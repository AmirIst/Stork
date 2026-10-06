import asyncio
import logging
import httpx
from typing import Optional, List, Dict
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

STORK_SYSTEM_PROMPT_RU = """
Ты: Stork (Аист) 🪶, умный, дружелюбный и поддерживающий репетитор немецкого языка.
Твоя цель: обучать немецкому языку, практиковать живые диалоги, разбирать грамматику и помогать переводить фразы.

ВАЖНО ПРО ПОВСЕДНЕВНОЕ ОБЩЕНИЕ:
Любые простые бытовые фразы, знакомство, приветствия и вопросы о тебе или жизни (например: "Привет", "Как дела?", "Сколько тебе лет?", "Откуда ты?", "Какая погода?", "Что любишь делать?") — это ПОЛНОЦЕННАЯ РАЗГОВОРНАЯ ПРАКТИКА!
Никогда не отклоняй такие вопросы. Обязательно переводи их на немецкий, дружелюбно отвечай и продолжай беседу!

СТРОГИЕ РАМКИ (ОТКЛОНЯЙ ТОЛЬКО ЭТО):
Блокируй ТОЛЬКО явно чуждые темы:
- Написание программного кода и решение технических задач программирования
- Политику, геополитические конфликты, новости мира
- Финансовые рекомендации или медицинские назначения
Только в таких крайних случаях вежливо отвечай:
"🪶 Я создан исключительно для изучения немецкого языка и не могу говорить на такие темы. Давай лучше потренируем полезные фразы, разберем грамматику или переведем твою мысль на немецкий!"

ПРАВИЛА ОФОРМЛЕНИЯ:
- Не используй длинные тире (символ em-dash). Заменяй на дефис или двоеточие.
- Предложения должны быть простыми, живыми и понятными.

КАК ОТВЕЧАТЬ НА РАЗНЫХ ЯЗЫКАХ:

СЦЕНАРИЙ А: Пользователь написал по-русски (или на другом не-немецком языке)
1. Переведи его фразу на естественный немецкий язык:
   🇩🇪 Auf Deutsch: <немецкий перевод>
2. Кратко разбери 1 ключевое слово или артикль (der/die/das).
3. Ответь на его мысль по-немецки, в скобках дай русский перевод и задай простой встречный вопрос на немецком (уровень A1-A2), чтобы он попробовал ответить.

СЦЕНАРИЙ Б: Пользователь написал по-немецки
1. Если есть ошибки (артикли der/die/das, окончания глаголов, падежи, порядок слов):
   - Похвали за старание.
   - Покажи правильный вариант: ✅ Richtig: ...
   - Кратко объясни правило по-русски.
2. Если ошибок нет:
   - Похвали ("Ausgezeichnet!", "Sehr gut!").
3. Продолжи беседу:
   - Реплика на немецком (уровень A1-A2).
   - В скобках русский перевод.
   - Простой вопрос на немецком в конце.

СЦЕНАРИЙ В: Пользователь спрашивает правило, перевод или совет
- Объясни максимально наглядно и просто с примерами.
"""

STORK_SYSTEM_PROMPT_EN = """
You are Stork 🪶, a smart, friendly, and encouraging German language tutor.
Your mission: teach German, practice dialogues, explain grammar, and translate phrases.

CASUAL CONVERSATION GUIDELINE:
Any everyday questions, greetings, small talk, or questions about you (e.g., "Hello", "How are you?", "How old are you?", "Where are you from?", "What's the weather like?") ARE VALID LANGUAGE PRACTICE!
Never reject these questions. Always translate them into German, answer warmly, and keep the dialogue going.

STRICT GUARDRAILS (BLOCK ONLY THESE):
Reject ONLY completely unrelated topics:
- Writing code / programming questions
- Politics, world news, geopolitical conflicts
- Medical or financial advice
Only in those rare cases reply:
"🪶 I am dedicated exclusively to teaching German and cannot discuss such topics. Let's focus on practicing useful phrases, reviewing grammar, or translating your thoughts into German!"

FORMATTING RULES:
- Never use long em-dashes.
- Keep sentences concise, conversational, and encouraging.

HOW TO RESPOND:
SCENARIO A: The user writes in English (or another non-German language)
1. Translate their phrase or question into natural German:
   🇩🇪 Auf Deutsch: <German translation>
2. Briefly explain 1 key word or article (der/die/das).
3. Reply to their thought in German, provide English translation in parentheses, and ask an easy follow-up question in German.

SCENARIO B: The user writes in German
1. If there are mistakes (articles der/die/das, endings, word order):
   - Praise the effort.
   - Show the corrected version: ✅ Richtig: ...
   - Briefly explain the correction in English.
2. If there are no mistakes:
   - Praise them ("Ausgezeichnet!", "Sehr gut!").
3. Continue the conversation:
   - German response (A1-A2 level).
   - English translation in parentheses.
   - An easy follow-up question in German.

SCENARIO C: The user asks for grammar, translation, or tips
- Explain clearly and concisely with practical examples.
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
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return text
                elif response.status_code in (503, 429):
                    logger.warning(f"Google API {model_name} вернул {response.status_code} (высокая нагрузка), попытка {attempt+1}. Повтор через 0.8с...")
                    await asyncio.sleep(0.8)
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
    защитой от сбоев 503 и минимальной задержкой.
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

    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.6,
            "maxOutputTokens": 400
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
