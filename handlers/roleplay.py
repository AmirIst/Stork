import io
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import db
from locales.manager import i18n
from services.roleplay_service import (
    ROLEPLAY_SCENARIOS,
    get_roleplay_scenario,
    generate_roleplay_reply,
    evaluate_roleplay_session
)
from services.ai_tutor import transcribe_voice
from services.tts import synthesize_speech
from services.ui_helper import show_or_update_window, mark_voice_sent
from keyboards.inline import (
    get_roleplay_scenarios_keyboard,
    get_roleplay_in_dialog_keyboard,
    get_roleplay_result_keyboard
)

logger = logging.getLogger(__name__)
router = Router()

class RoleplayState(StatesGroup):
    in_dialog = State()

@router.callback_query(F.data == "menu_roleplay")
async def cb_menu_roleplay(callback: CallbackQuery, state: FSMContext):
    """Выбор сценария ролевой игры"""
    await state.clear()
    lang = await db.get_user_lang(callback.from_user.id)
    text = i18n.get("roleplay_welcome", lang)
    kb = get_roleplay_scenarios_keyboard(ROLEPLAY_SCENARIOS, lang=lang)
    await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("rp_start:"))
async def cb_start_scenario(callback: CallbackQuery, state: FSMContext):
    """Запуск выбранного сценария и реплика собеседника"""
    scenario_id = callback.data.split(":")[1]
    scenario = get_roleplay_scenario(scenario_id)
    if not scenario:
        await callback.answer("Сценарий не найден", show_alert=True)
        return

    lang = await db.get_user_lang(callback.from_user.id)
    character_name = scenario["character"].get(lang, scenario["character"]["ru"])
    title = scenario["title"].get(lang, scenario["title"]["ru"])
    goal = scenario["goal"].get(lang, scenario["goal"]["ru"])
    starter_tr = scenario["starter_tr"].get(lang, scenario["starter_tr"]["ru"])

    # Сохраняем в контекст состояние и стартовую историю
    await state.set_state(RoleplayState.in_dialog)
    await state.update_data(
        scenario_id=scenario_id,
        history=[{"role": character_name, "message": scenario["starter_de"]}],
        last_reply_de=scenario["starter_de"]
    )

    intro_text = (
        f"🎭 *Сценарий:* {scenario['icon']} {title}\n"
        f"👤 *Собеседник:* {character_name}\n"
        f"🎯 *Цель:* {goal}\n\n"
        f"────────────────────\n"
        f"🇩🇪 *{character_name}:*\n"
        f"«{scenario['starter_de']}»\n\n"
        f"💬 _{starter_tr}_\n"
        f"────────────────────\n\n"
        f"👉 _Напиши ответ на немецком или надиктуй голосовое сообщение прямо сейчас!_"
    )

    kb = get_roleplay_in_dialog_keyboard(scenario_id, lang=lang)
    await show_or_update_window(callback, intro_text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("rp_hint:"))
async def cb_roleplay_hint(callback: CallbackQuery):
    """Всплывающая подсказка с фразами для ответа"""
    scenario_id = callback.data.split(":")[1]
    scenario = get_roleplay_scenario(scenario_id)
    if not scenario:
        await callback.answer()
        return

    lang = await db.get_user_lang(callback.from_user.id)
    hints = scenario["hints"].get(lang, scenario["hints"]["ru"])
    hint_text = "💡 Полезные фразы:\n\n" + "\n\n".join([f"• {h}" for h in hints])
    await callback.answer(hint_text, show_alert=True)

@router.callback_query(F.data == "rp_voice_last")
async def cb_roleplay_voice_last(callback: CallbackQuery, state: FSMContext):
    """Озвучка последней реплики немецкого собеседника"""
    data = await state.get_data()
    last_de = data.get("last_reply_de", "")
    if not last_de:
        await callback.answer("Нет реплики для озвучки", show_alert=True)
        return

    await callback.answer("Озвучиваю реплику собеседника...")
    await callback.message.bot.send_chat_action(chat_id=callback.message.chat.id, action="record_voice")

    audio_bytes = await synthesize_speech(last_de)
    if audio_bytes:
        voice_file = BufferedInputFile(audio_bytes, filename="roleplay_partner.mp3")
        await callback.message.answer_voice(
            voice=voice_file,
            caption=f"🗣️ *Реплика:* _{last_de}_",
            parse_mode="Markdown"
        )
        mark_voice_sent(callback.from_user.id)

@router.message(RoleplayState.in_dialog, F.voice)
async def handle_roleplay_voice_message(message: Message, state: FSMContext):
    """Обработка голосового сообщения ученика в ролевом диалоге"""
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)

    await message.bot.send_chat_action(chat_id=message.chat.id, action="record_voice")

    try:
        file_info = await message.bot.get_file(message.voice.file_id)
        voice_stream = io.BytesIO()
        await message.bot.download_file(file_info.file_path, destination=voice_stream)
        audio_bytes = voice_stream.getvalue()

        transcribed = await transcribe_voice(audio_bytes, mime_type="audio/ogg")
        if not transcribed:
            err_msg = "🪶 Не удалось разобрать аудио. Попробуй сказать еще раз или напиши текстом!" if lang == "ru" else "Could not transcribe audio. Please try again!"
            await message.answer(err_msg)
            return

        # Показываем распознанный текст ответа
        await message.answer(f"🗣️ *Твой ответ (распознано):*\n_{transcribed}_", parse_mode="Markdown")
        await process_roleplay_turn(message, state, user_text=transcribed, lang=lang)
    except Exception as e:
        logger.error(f"Ошибка в аудио ролевого диалога: {e}")
        await message.answer("Ошибка при обработке голоса. Напиши ответ текстом!")

@router.message(RoleplayState.in_dialog, F.text)
async def handle_roleplay_text_message(message: Message, state: FSMContext):
    """Обработка текстового сообщения ученика в ролевом диалоге"""
    if message.text.startswith("/"):
        await state.clear()
        return

    lang = await db.get_user_lang(message.from_user.id)
    await process_roleplay_turn(message, state, user_text=message.text, lang=lang)

async def process_roleplay_turn(message: Message, state: FSMContext, user_text: str, lang: str):
    """Генерация ответа собеседника и продвижение диалога"""
    data = await state.get_data()
    scenario_id = data.get("scenario_id", "cafe_a1")
    scenario = get_roleplay_scenario(scenario_id)
    history = data.get("history", [])

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    reply_data = await generate_roleplay_reply(
        scenario=scenario,
        history=history,
        user_message=user_text,
        native_lang=lang
    )

    character_name = scenario["character"].get(lang, scenario["character"]["ru"])
    history.append({"role": "Lernender", "message": user_text})
    history.append({"role": character_name, "message": reply_data["reply_de"]})

    await state.update_data(
        history=history,
        last_reply_de=reply_data["reply_de"]
    )

    hint_str = f"\n\n💡 _Подсказка:_ `{reply_data['hint']}`" if reply_data.get("hint") else ""
    response_text = (
        f"🇩🇪 *{character_name}:*\n"
        f"«{reply_data['reply_de']}»\n\n"
        f"💬 _{reply_data['reply_tr']}_{hint_str}"
    )

    kb = get_roleplay_in_dialog_keyboard(scenario_id, lang=lang)
    await message.answer(response_text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "rp_finish")
async def cb_roleplay_finish(callback: CallbackQuery, state: FSMContext):
    """Завершение ролевой игры и получение оценки от преподавателя"""
    data = await state.get_data()
    scenario_id = data.get("scenario_id", "cafe_a1")
    scenario = get_roleplay_scenario(scenario_id)
    history = data.get("history", [])

    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)

    await callback.answer("Аист анализирует диалог и готовит разбор..." if lang == "ru" else "Analyzing dialogue...")
    await callback.message.bot.send_chat_action(chat_id=callback.message.chat.id, action="typing")

    evaluation = await evaluate_roleplay_session(
        scenario=scenario,
        history=history,
        native_lang=lang
    )

    # Награждаем ученика ачивкой "Мастер ролевой игры"
    await db.unlock_achievement(user_id, "roleplay_master")
    await db.update_daily_streak(user_id)
    await db.add_user_score(user_id, points=2)

    await state.clear()

    full_result = (
        f"🏁 *Ролевой диалог завершен!*\n\n"
        f"{evaluation}"
    )

    kb = get_roleplay_result_keyboard(lang=lang)
    await show_or_update_window(callback, full_result, reply_markup=kb, parse_mode="Markdown")
