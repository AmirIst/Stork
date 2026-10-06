"""
Сервис синтеза речи (Text-to-Speech) для немецкого языка.
Использует высококачественные нейронные голоса Microsoft Edge (edge-tts).
Не требует API-ключей, работает асинхронно с кэшированием в оперативной памяти.
"""
import re
import logging
from typing import Optional, Dict
import edge_tts

logger = logging.getLogger(__name__)

# Рекомендуемые студийные нейронные голоса немецкого языка
VOICE_MALE = "de-DE-KillianNeural"      # Четкий мужской голос (стандартный Hochdeutsch)
VOICE_FEMALE = "de-DE-KatjaNeural"     # Мягкий женский голос

# Оперативный кэш аудиобайтов (текст -> bytes), чтобы не синтезировать частые слова повторно
_AUDIO_CACHE: Dict[str, bytes] = {}
MAX_CACHE_ENTRIES = 500

async def synthesize_speech(text: str, voice: str = VOICE_MALE) -> Optional[bytes]:
    """
    Синтезирует речь для заданного текста на немецком языке.
    Возвращает байты MP3 аудио или None в случае ошибки.
    """
    cleaned_text = text.strip()
    if not cleaned_text:
        return None

    cache_key = f"{voice}:{cleaned_text}"
    if cache_key in _AUDIO_CACHE:
        return _AUDIO_CACHE[cache_key]

    try:
        communicate = edge_tts.Communicate(cleaned_text, voice=voice)
        audio_stream = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.extend(chunk["data"])

        if audio_stream:
            audio_bytes = bytes(audio_stream)
            if len(_AUDIO_CACHE) < MAX_CACHE_ENTRIES:
                _AUDIO_CACHE[cache_key] = audio_bytes
            return audio_bytes
    except Exception as e:
        logger.error(f"Ошибка синтеза речи через edge-tts: {e}")

    return None

async def synthesize_word_audio(article: str, word: str, example_de: Optional[str] = None) -> Optional[bytes]:
    """
    Синтезирует произношение карточки:
    Сначала артикль и слово с небольшой паузой, затем пример предложения.
    Например: "der Apfel. ... Der Apfel ist rot und süß."
    """
    parts = []
    if article:
        parts.append(f"{article} {word}.")
    else:
        parts.append(f"{word}.")

    if example_de:
        parts.append(example_de)

    full_text = " ".join(parts)
    return await synthesize_speech(full_text)

def extract_german_for_voice(ai_response: str) -> str:
    """
    Извлекает немецкий текст из 4-блочного ответа ИИ Stork для озвучки.
    Убирает русский перевод в скобках, разбор и служебные значки.
    """
    lines = [line.strip() for line in ai_response.split("\n") if line.strip()]
    german_parts = []

    for line in lines:
        # Извлекаем строку "Auf Deutsch: ..."
        if "Auf Deutsch:" in line:
            clean = line.split("Auf Deutsch:")[-1].strip()
            # Убираем перевод в скобках если есть
            clean = re.sub(r"\(.*?\)", "", clean).strip()
            if clean:
                german_parts.append(clean)
            continue

        # Пропускаем разбор на русском ("💡 Разбор:")
        if line.startswith("💡") or line.startswith("Разбор:"):
            continue

        # Пропускаем чисто русские реплики Stork в начале
        if line.startswith("🪶 Stork:") or line.startswith("Ой,"):
            continue

        # Проверяем строки, содержащие немецкий текст с переводом в скобках
        # Например: "Ich bin ein Sprachmodell... (Я языковая модель...)"
        # Берем только часть до скобок
        if "(" in line and ")" in line:
            # Извлекаем все фразы до круглых скобок
            clean_line = re.sub(r"^[🪶✅*_\-•]+\s*", "", line).strip()
            parts_before_paren = re.findall(r"([^()]+)(?:\(.*?\))?", clean_line)
            filtered = [p.strip() for p in parts_before_paren if p.strip()]
            for p in filtered:
                # Если в строке латинские буквы (немецкий)
                if re.search(r"[a-zA-ZäöüÄÖÜß]", p) and not re.search(r"[а-яА-ЯёЁ]", p):
                    german_parts.append(p)
        else:
            # Если вся строка на латинице (немецкий) без кириллицы
            if re.search(r"[a-zA-ZäöüÄÖÜß]", line) and not re.search(r"[а-яА-ЯёЁ]", line):
                clean = re.sub(r"^[🪶✅*_\-•]+\s*", "", line).strip()
                if clean:
                    german_parts.append(clean)

    if german_parts:
        return " ".join(german_parts)

    # Fallback: если специфичные блоки не найдены, берем текст без кириллицы
    no_cyrillic = re.sub(r"[а-яА-ЯёЁ]", "", ai_response)
    clean_fallback = re.sub(r"[\(\)💡🪶*_\n]+", " ", no_cyrillic).strip()
    return clean_fallback if len(clean_fallback) > 3 else "Guten Tag! Ich lerne Deutsch mit Stork."
