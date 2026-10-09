import logging
import random
from typing import Dict, Any, Optional
from services.ai_tutor import execute_gemini_request

logger = logging.getLogger(__name__)

# Пул вопросов дня для шага 3 тренировки (актуальные бытовые и разговорные темы)
DAILY_QUESTIONS = [
    {
        "id": "q1",
        "de": "Wie war dein Tag heute und was hast du gemacht?",
        "ru": "Как прошел твой день и что ты сегодня делал?",
        "en": "How was your day and what did you do today?",
        "hint_de": "Z.B.: Mein Tag war gut. Ich habe gearbeitet und gelernt.",
        "hint_ru": "Например: Mein Tag war gut. Ich habe gearbeitet und gelernt.",
        "hint_en": "E.g.: Mein Tag war gut. Ich habe gearbeitet und gelernt."
    },
    {
        "id": "q2",
        "de": "Was isst und trinkst du am liebsten zum Frühstück?",
        "ru": "Что ты больше всего любишь есть и пить на завтрак?",
        "en": "What do you like to eat and drink for breakfast the most?",
        "hint_de": "Z.B.: Zum Frühstück esse ich gern Brot mit Käse und trinke Kaffee.",
        "hint_ru": "Например: Zum Frühstück esse ich gern Brot mit Käse und trinke Kaffee.",
        "hint_en": "E.g.: Zum Frühstück esse ich gern Brot mit Käse und trinke Kaffee."
    },
    {
        "id": "q3",
        "de": "Wie ist das Wetter heute bei dir und magst du dieses Wetter?",
        "ru": "Какая сегодня погода у тебя и нравится ли тебе такая погода?",
        "en": "How is the weather today where you are and do you like it?",
        "hint_de": "Z.B.: Das Wetter ist heute sonnig und warm / bewölkt und kalt.",
        "hint_ru": "Например: Das Wetter ist heute sonnig und warm / bewölkt und kalt.",
        "hint_en": "E.g.: Das Wetter ist heute sonnig und warm / bewölkt und kalt."
    },
    {
        "id": "q4",
        "de": "Was machst du am kommenden Wochenende?",
        "ru": "Что ты будешь делать на следующих выходных?",
        "en": "What are you doing this upcoming weekend?",
        "hint_de": "Z.B.: Am Wochenende treffe ich Freunde und mache Sport.",
        "hint_ru": "Например: Am Wochenende treffe ich Freunde und mache Sport.",
        "hint_en": "E.g.: Am Wochenende treffe ich Freunde und mache Sport."
    },
    {
        "id": "q5",
        "de": "Warum lernst du Deutsch und was gefällt dir an der Sprache?",
        "ru": "Почему ты учишь немецкий и что тебе нравится в этом языке?",
        "en": "Why are you learning German and what do you like about the language?",
        "hint_de": "Z.B.: Ich lerne Deutsch für meinen Beruf / für das Leben in Deutschland.",
        "hint_ru": "Например: Ich lerne Deutsch для работы / жизни.",
        "hint_en": "E.g.: I am learning German for work / life."
    },
    {
        "id": "q6",
        "de": "Welche Stadt oder welches Land möchtest du bald besuchen?",
        "ru": "Какой город или страну ты хочешь скоро посетить?",
        "en": "Which city or country would you like to visit soon?",
        "hint_de": "Z.B.: Ich möchte gern Berlin oder Wien besuchen.",
        "hint_ru": "Например: Ich möchte gern Berlin oder Wien besuchen.",
        "hint_en": "E.g.: Ich möchte gern Berlin oder Wien besuchen."
    },
    {
        "id": "q7",
        "de": "Was ist dein Lieblingshobby in deiner Freizeit?",
        "ru": "Какое твое любимое хобби в свободное время?",
        "en": "What is your favorite hobby in your free time?",
        "hint_de": "Z.B.: In meiner Freizeit lese ich gern Bücher und mache Sport.",
        "hint_ru": "Например: In meiner Freizeit lese ich gern Bücher und mache Sport.",
        "hint_en": "E.g.: In meiner Freizeit lese ich gern Bücher und mache Sport."
    }
]

def get_daily_question(day_seed: Optional[int] = None) -> Dict[str, Any]:
    """Возвращает вопрос дня (детерминированно по дню или случайно)"""
    if day_seed is not None:
        idx = day_seed % len(DAILY_QUESTIONS)
        return DAILY_QUESTIONS[idx]
    return random.choice(DAILY_QUESTIONS)

async def evaluate_daily_workout_answer(question: Dict[str, Any], user_text: str, lang: str = "ru") -> str:
    """
    Оценивает ответ ученика на вопрос дня с помощью Gemini.
    Формирует дружелюбный, ободряющий и конструктивный ответ с разбором.
    """
    q_de = question.get("de", "")
    target_lang = "русском" if lang == "ru" else "английском"

    prompt = (
        f"Ты — Stork (Аист), дружелюбный преподаватель немецкого языка в Telegram.\n"
        f"Ученик выполняет 'Тренировку дня' и ответил на твой вопрос.\n\n"
        f"Вопрос дня: «{q_de}»\n"
        f"Ответ ученика: «{user_text}»\n\n"
        f"Твоя задача:\n"
        f"1. Напиши ответ на {target_lang} языке.\n"
        f"2. Похвали ученика за старание и ответь по смыслу на его реплику (1-2 предложения).\n"
        f"3. Если есть грамматические ошибки: покажи идеальный естественный вариант на немецком и кратко объясни правило простыми словами без воды.\n"
        f"4. Если ошибок нет: напиши 'Отличная грамматика, звучит очень естественно!'.\n"
        f"5. Текст должен быть коротким (3-4 предложения), живым, без длинных тире (—) и канцеляризмов."
    )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 400
        }
    }

    try:
        reply = await execute_gemini_request(payload)
        if reply:
            return reply.strip().replace("—", "-")
    except Exception as e:
        logger.error(f"Ошибка проверки ответа тренировки дня: {e}")

    if lang == "ru":
        return "Отличный ответ! Ты выразил мысль понятно и уверенно. Продолжай тренироваться каждый день!"
    else:
        return "Great answer! You expressed your thoughts clearly. Keep practicing every day!"
