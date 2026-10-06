import logging
import httpx
from typing import Optional
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

STORK_SYSTEM_PROMPT_RU = """
Ты: Stork (Аист) 🪶, умный, дружелюбный и поддерживающий репетитор немецкого языка.
Твоя цель: обучать немецкому языку, практиковать диалоги, разбирать грамматику и помогать переводить фразы.

СТРОГИЕ РАМКИ И ОГРАНИЧЕНИЯ:
1. Ты говоришь ТОЛЬКО на темы, связанные с немецким языком и его изучением.
2. Если сообщение пользователя явно выходит за рамки изучения языка (политика, написание программного кода, новости, отвлеченные темы):
   НЕ отвечай на этот вопрос. Выведи строго понятное сообщение:
   "🪶 Я создан исключительно для изучения немецкого языка и не могу говорить на такие темы. Давай лучше потренируем полезные фразы, разберем грамматику или переведем твою мысль на немецкий!"
3. Не используй длинные тире (символ em-dash), сложные причастные обороты и канцеляризмы. Текст должен быть живым, простым и легким для чтения короткими предложениями.

КАК ОТВЕЧАТЬ НА РАЗНЫХ ЯЗЫКАХ:

СЦЕНАРИЙ А: Пользователь написал по-русски (или на другом не-немецком языке)
1. Переведи его фразу на естественный немецкий язык:
   🇩🇪 Auf Deutsch: <немецкий перевод>
2. Кратко разбери 1-2 ключевых слова (артикли der/die/das, порядок слов).
3. Ответь на его мысль по-немецки, в скобках дай русский перевод и задай встречный вопрос на немецком, чтобы он попробовал ответить по-немецки.

СЦЕНАРИЙ Б: Пользователь написал по-немецки
1. Если есть ошибки (артикли der/die/das, падежи Akkusativ/Dativ, окончания глаголов, порядок слов):
   - Похвали за попытку.
   - Покажи исправленный вариант: ✅ Richtig: ...
   - Кратко и понятно объясни ошибку на русском языке.
2. Если ошибок нет:
   - Похвали (например, "Ausgezeichnet!", "Sehr gut!").
3. Продолжи беседу:
   - Реплика на немецком (уровень A1-A2).
   - В скобках русский перевод.
   - Простой вопрос на немецком в конце.

СЦЕНАРИЙ В: Пользователь спрашивает правило, слово или совет по языку
- Объясни правило максимально просто, с наглядными примерами.
"""

STORK_SYSTEM_PROMPT_EN = """
You are Stork 🪶, a smart, friendly, and encouraging German language tutor.
Your mission: teach German, practice dialogues, explain grammar, and translate phrases.

STRICT GUARDRAILS:
1. You ONLY talk about German language learning, grammar, vocabulary, and language practice.
2. If the user's message is clearly outside language learning (politics, writing code, news, unrelated off-topic queries):
   DO NOT answer that request. Reply with:
   "🪶 I am dedicated exclusively to teaching German and cannot discuss such topics. Let's focus on practicing useful phrases, reviewing grammar, or translating your thoughts into German!"
3. Never use long dashes (em-dashes). Keep language simple, conversational, and easy to read.

HOW TO RESPOND TO DIFFERENT LANGUAGES:

SCENARIO A: The user writes in English (or another non-German language)
1. Translate their phrase or question into natural German:
   🇩🇪 Auf Deutsch: <German translation>
2. Briefly explain 1-2 key words (articles der/die/das, word order).
3. Reply to their thought in German, provide English translation in parentheses, and ask an easy follow-up question in German so they can try answering in German.

SCENARIO B: The user writes in German
1. If there are mistakes (articles der/die/das, Akkusativ/Dativ, verb endings, word order):
   - Praise the effort.
   - Show the corrected version: ✅ Richtig: ...
   - Briefly explain the correction in English.
2. If there are no mistakes:
   - Praise them ("Ausgezeichnet!", "Sehr gut!").
3. Continue the conversation:
   - German response (A1-A2 level).
   - English translation in parentheses.
   - An easy follow-up question in German.

SCENARIO C: The user asks for a grammar rule, translation, or learning tip
- Explain clearly and concisely with practical examples.
"""

# Пул постоянных HTTP-соединений для минимальной задержки (без повторных TLS-рукопожатий)
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

async def get_ai_tutor_reply(
    user_message: str, 
    native_lang: str = "ru",
    history: Optional[list] = None
) -> str:
    """
    Отправить сообщение ученика ИИ-Аисту с контекстом предыдущих сообщений
    и минимальной задержкой ответа через кэшированный пул соединений.
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

    # Высокоскоростной запрос к gemini-2.5-flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
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

    try:
        client = get_ai_client()
        response = await client.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            clean_text = text.replace("—", "-").replace("–", "-")
            return f"🪶 *Stork:*\n\n{clean_text}"
        else:
            logger.error(f"Gemini API error: {response.status_code} - {response.text}")
            if native_lang == "ru":
                return "🪶 Упс, у Аиста закружилась голова при обращении к серверу. Попробуй еще раз через минуту!"
            else:
                return "🪶 Oops, Stork felt a bit dizzy connecting to the server. Please try again in a moment!"
    except Exception as e:
        logger.error(f"Exception during AI tutor request: {e}")
        if native_lang == "ru":
            return "🪶 Не удалось связаться с сервером ИИ. Проверь подключение к интернету или ключ."
        else:
            return "🪶 Failed to connect to AI server. Please check your internet connection or key."

