"""
Сервис синтеза речи (Text-to-Speech) для немецкого языка.
Использует высококачественные нейронные голоса Microsoft Edge (edge-tts).
Не требует API-ключей, работает асинхронно с кэшированием в оперативной памяти.
"""
import re
import asyncio
import logging
from typing import Optional, Dict
import edge_tts
import httpx

logger = logging.getLogger(__name__)

# Рекомендуемые студийные нейронные голоса немецкого языка
VOICE_MALE = "de-DE-KillianNeural"      # Четкий мужской голос (стандартный Hochdeutsch)
VOICE_FEMALE = "de-DE-KatjaNeural"     # Мягкий женский голос

# Оперативный кэш аудиобайтов (текст -> bytes), чтобы не синтезировать частые слова повторно
_AUDIO_CACHE: Dict[str, bytes] = {}
MAX_CACHE_ENTRIES = 500

async def _synthesize_google_tts(text: str) -> Optional[bytes]:
    """
    Надежный резервный синтез речи через Google Translate TTS.
    Работает без ключей, гарантированно доступен на облачных серверах (Heroku, AWS).
    """
    if not text:
        return None

    clean = re.sub(r"[*_~`#]+", " ", text).strip()
    if not clean:
        return None

    sentences = re.split(r'([.!?;\n]+)', clean)
    tokens = []
    for i in range(0, len(sentences) - 1, 2):
        tokens.append(sentences[i] + sentences[i+1])
    if len(sentences) % 2 == 1 and sentences[-1]:
        tokens.append(sentences[-1])
    if not tokens:
        tokens = [clean]

    chunks = []
    current = ""
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if len(current) + len(token) + 1 <= 180:
            current = f"{current} {token}".strip()
        else:
            if current:
                chunks.append(current)
            if len(token) <= 180:
                current = token
            else:
                words = token.split()
                sub = ""
                for w in words:
                    if len(sub) + len(w) + 1 <= 180:
                        sub = f"{sub} {w}".strip()
                    else:
                        if sub:
                            chunks.append(sub)
                        sub = w
                current = sub
    if current:
        chunks.append(current)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    audio_full = bytearray()
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            for chunk in chunks:
                params = {"ie": "UTF-8", "tl": "de", "client": "tw-ob", "q": chunk}
                resp = await client.get("https://translate.google.com/translate_tts", params=params, headers=headers)
                if resp.status_code == 200 and resp.content:
                    audio_full.extend(resp.content)
                else:
                    logger.warning(f"Google TTS returned status {resp.status_code} for chunk '{chunk[:20]}'")
        if audio_full:
            return bytes(audio_full)
    except Exception as e:
        logger.error(f"Ошибка резервного синтеза речи через Google TTS: {e}")
    return None

async def synthesize_speech(text: str, voice: str = VOICE_MALE) -> Optional[bytes]:
    """
    Синтезирует речь для заданного текста на немецком языке.
    Основной движок: Microsoft Edge TTS (Killian/Katja Neural).
    Резервный движок: Google TTS (для облачных серверов с блокировкой websocket).
    """
    cleaned_text = text.strip()
    if not cleaned_text:
        return None

    cache_key = f"{voice}:{cleaned_text}"
    if cache_key in _AUDIO_CACHE:
        return _AUDIO_CACHE[cache_key]

    # 1. Попытка через Edge-TTS с таймаутом
    try:
        communicate = edge_tts.Communicate(cleaned_text, voice=voice)
        async def _collect():
            buf = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buf.extend(chunk["data"])
            return bytes(buf) if buf else None

        audio_bytes = await asyncio.wait_for(_collect(), timeout=4.0)
        if audio_bytes:
            if len(_AUDIO_CACHE) < MAX_CACHE_ENTRIES:
                _AUDIO_CACHE[cache_key] = audio_bytes
            return audio_bytes
    except Exception as e:
        logger.warning(f"edge-tts недоступен ({e}), переключаюсь на резервный Google TTS...")

    # 2. Надежный резервный синтез Google TTS
    google_audio = await _synthesize_google_tts(cleaned_text)
    if google_audio:
        if len(_AUDIO_CACHE) < MAX_CACHE_ENTRIES:
            _AUDIO_CACHE[cache_key] = google_audio
        return google_audio

    logger.error(f"Все попытки синтеза речи не удались для текста: {cleaned_text[:50]}")
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
    Извлекает все немецкие фразы из ответа ИИ Stork (перевод, ответ, встречный вопрос).
    Убирает перевод в скобках, разбор и служебные значки.
    Поддерживает как русский, так и английский форматы.
    """
    lines = [line.strip() for line in ai_response.split("\n") if line.strip()]
    german_parts = []

    for line in lines:
        # 1. Линии с переводом на немецкий
        for marker in ["Перевод фразы на немецком:", "Перевод фразы на немецкий:", "German translation:", "Auf Deutsch:"]:
            if marker in line:
                part = line.split(marker)[-1].strip()
                clean = re.sub(r"\(.*?\)", "", part).strip()
                clean = re.sub(r"^[*\s]+|[*\s]+$", "", clean)
                if clean:
                    german_parts.append(clean)
                break
        else:
            # 2. Пропускаем разбор и приветственные реплики
            if any(marker in line for marker in ["Полезный разбор:", "Useful breakdown:", "💡 Разбор:", "💡 Insight:"]):
                continue

            if line.startswith("🪶 Stork:") or line.startswith("🎙️"):
                continue

            # 3. Ответ на сообщение, встречный вопрос или проверка
            for marker in ["Ответ на сообщение:", "Reply to your message:", "Встречный вопрос:", "Follow-up question:", "Richtig:"]:
                if marker in line:
                    part = line.split(marker)[-1].strip()
                    clean = re.sub(r"\(.*?\)", "", part).strip()
                    clean = re.sub(r"^[*\s]+|[*\s]+$", "", clean)
                    if re.search(r"[a-zA-ZäöüÄÖÜß]", clean) and not re.search(r"[а-яА-ЯёЁ]", clean):
                        german_parts.append(clean)
                    break
            else:
                # 4. Общие строки с немецким текстом и переводом в скобках
                clean_line = re.sub(r"^[🪶✅💬❓*_\-•]+\s*", "", line).strip()
                if "(" in clean_line and ")" in clean_line:
                    parts_before_paren = re.findall(r"([^()]+)(?:\(.*?\))?", clean_line)
                    for p in parts_before_paren:
                        p_clean = p.strip()
                        if re.search(r"[a-zA-ZäöüÄÖÜß]", p_clean) and not re.search(r"[а-яА-ЯёЁ]", p_clean):
                            german_parts.append(p_clean)
                elif re.search(r"[a-zA-ZäöüÄÖÜß]", clean_line) and not re.search(r"[а-яА-ЯёЁ]", clean_line):
                    german_parts.append(clean_line)

    if german_parts:
        return " ".join(german_parts)

    no_cyrillic = re.sub(r"[а-яА-ЯёЁ]", "", ai_response)
    clean_fallback = re.sub(r"[\(\)💡🪶*_\n]+", " ", no_cyrillic).strip()
    return clean_fallback if len(clean_fallback) > 3 else "Guten Tag! Ich lerne Deutsch mit Stork."

def extract_musterloesung_for_voice(review_text: str) -> str:
    """
    Извлекает немецкий текст из образцового решения (Musterlösung) экзаменационного разбора.
    Удаляет перевод в скобках и оставляет только чистую немецкую речь.
    """
    marker = None
    for m in ["Идеальный образец ответа (Musterlösung):", "Model Answer (Musterlösung):", "Musterlösung:"]:
        if m in review_text:
            marker = m
            break

    if not marker:
        return extract_german_for_voice(review_text)

    sample_part = review_text.split(marker)[1]
    for next_marker in ["💡 Экзаменационный совет", "💡 Stork Exam Tip", "💡"]:
        if next_marker in sample_part:
            sample_part = sample_part.split(next_marker)[0]
            break

    clean_de = re.sub(r"\(.*?\)", "", sample_part)
    clean_de = re.sub(r"[*_#>`~]+", " ", clean_de).strip()
    return clean_de if clean_de else extract_german_for_voice(review_text)

