import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile
from database import db
from services.tts import synthesize_word_audio, synthesize_speech, extract_german_for_voice
from services.ui_helper import mark_voice_sent

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data.startswith("voice_word:"))
async def cb_voice_word(callback: CallbackQuery):
    """Озвучка немецкого слова с артиклем и примером"""
    parts = callback.data.split(":")
    word_id = int(parts[1])
    
    lang = await db.get_user_lang(callback.from_user.id)
    word_data = await db.get_word_by_id(word_id, lang=lang)
    
    if not word_data:
        await callback.answer("Слово не найдено" if lang == "ru" else "Word not found", show_alert=True)
        return

    # Сообщаем Telegram о записи аудио
    await callback.message.bot.send_chat_action(chat_id=callback.message.chat.id, action="record_voice")

    audio_bytes = await synthesize_word_audio(
        article=word_data["article"],
        word=word_data["word"],
        example_de=word_data.get("example_de")
    )

    if not audio_bytes:
        msg = "Не удалось синтезировать звук" if lang == "ru" else "Audio synthesis failed"
        await callback.answer(msg, show_alert=True)
        return

    voice_file = BufferedInputFile(audio_bytes, filename=f"{word_data['word']}.mp3")
    caption = f"🔊 *{word_data['article']} {word_data['word']}*\n_{word_data.get('example_de', '')}_"
    
    await callback.message.answer_voice(
        voice=voice_file,
        caption=caption,
        parse_mode="Markdown"
    )
    mark_voice_sent(callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data == "ai_voice_last")
async def cb_voice_ai_reply(callback: CallbackQuery):
    """Озвучка немецкой части из последнего ответа ИИ Stork"""
    text = callback.message.text or callback.message.caption or ""
    lang = await db.get_user_lang(callback.from_user.id)
    
    german_text = extract_german_for_voice(text)
    if not german_text:
        msg = "В сообщении не найден немецкий текст" if lang == "ru" else "No German text found"
        await callback.answer(msg, show_alert=True)
        return

    await callback.message.bot.send_chat_action(chat_id=callback.message.chat.id, action="record_voice")

    audio_bytes = await synthesize_speech(german_text)
    if not audio_bytes:
        msg = "Не удалось синтезировать голос" if lang == "ru" else "Could not synthesize voice"
        await callback.answer(msg, show_alert=True)
        return

    voice_file = BufferedInputFile(audio_bytes, filename="stork_voice.mp3")
    caption = "🪶 *Все немецкие фразы из ответа:*" if lang == "ru" else "🪶 *All German phrases from reply:*"
    await callback.message.answer_voice(
        voice=voice_file,
        caption=caption,
        parse_mode="Markdown"
    )
    mark_voice_sent(callback.from_user.id)
    await callback.answer()

