import logging
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import db
from locales.manager import i18n
from services.workout_service import get_daily_question, evaluate_daily_workout_answer
from services.tts import synthesize_speech
from services.ai_tutor import transcribe_voice
from services.ui_helper import show_or_update_window, mark_voice_sent
from keyboards.inline import (
    get_workout_welcome_keyboard,
    get_workout_word_keyboard,
    get_workout_article_keyboard,
    get_workout_next_article_keyboard,
    get_workout_question_keyboard,
    get_workout_finish_keyboard
)

logger = logging.getLogger(__name__)
router = Router()

class WorkoutState(StatesGroup):
    in_words = State()
    in_articles = State()
    waiting_question_reply = State()

@router.message(Command("workout"))
@router.callback_query(F.data == "daily_workout")
async def start_daily_workout_entry(event: Message | CallbackQuery, state: FSMContext):
    """Точка входа в ежедневную тренировку дня"""
    user_id = event.from_user.id
    lang = await db.get_user_lang(user_id)
    await state.clear()

    already_done = await db.is_daily_workout_completed(user_id)
    user = await db.get_user(user_id)
    streak = user.get("streak", 0) if user else 0

    if already_done:
        if lang == "ru":
            text = (
                f"🎉 *Ты уже выполнил сегодняшнюю тренировку дня!*\n\n"
                f"🔥 Твой ударный режим: *{streak} дн. подряд*\n"
                f"⭐️ Опыт за сегодня уже получен (*+50 XP*).\n\n"
                f"Ты можешь пройти тренировку повторно для закрепления слов и грамматики, "
                f"или продолжить занятия в других разделах меню."
            )
        else:
            text = (
                f"🎉 *You have already completed today's workout!*\n\n"
                f"🔥 Your streak: *{streak} days in a row*\n"
                f"⭐️ Today's bonus is secured (*+50 XP*).\n\n"
                f"You can repeat today's session for extra practice, "
                f"or explore other sections in the menu."
            )
    else:
        if lang == "ru":
            text = (
                f"⚡️ *Ежедневная тренировка дня Stork* (~3 мин)\n\n"
                f"Три быстрых шага, чтобы держать немецкий в тонусе:\n"
                f"1. 📚 *5 новых слов* твоего уровня\n"
                f"2. 🎯 *5 блиц-вопросов* на артикли (der/die/das)\n"
                f"3. 💬 *1 вопрос дня от Аиста* (ответь текстом или голосом)\n\n"
                f"🎁 Награда: *+50 XP* и сохранение ударного режима 🔥"
            )
        else:
            text = (
                f"⚡️ *Stork Daily Workout* (~3 min)\n\n"
                f"Three quick steps to keep your German sharp:\n"
                f"1. 📚 *5 vocabulary words* for your level\n"
                f"2. 🎯 *5 blitz article drills* (der/die/das)\n"
                f"3. 💬 *1 question of the day from Stork* (reply via text or voice)\n\n"
                f"🎁 Reward: *+50 XP* and streak progression 🔥"
            )

    kb = get_workout_welcome_keyboard(lang=lang, already_done=already_done)
    if isinstance(event, CallbackQuery):
        await show_or_update_window(event, text, reply_markup=kb, parse_mode="Markdown")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "wo_start_step1")
async def cb_start_step1(callback: CallbackQuery, state: FSMContext):
    """Инициализация данных и показ первого слова дня"""
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)

    words, articles = await db.get_workout_words_and_quiz(user_id, lang=lang, count=5)
    if not words or not articles:
        await callback.answer("Ошибка загрузки слов. Попробуйте еще раз.", show_alert=True)
        return

    # Вопрос дня детерминирован номером дня в году
    day_num = int(datetime.now(timezone.utc).strftime("%j"))
    question = get_daily_question(day_seed=day_num)

    await state.set_state(WorkoutState.in_words)
    await state.update_data(
        words=words,
        word_idx=0,
        articles=articles,
        art_idx=0,
        art_correct=0,
        question=question
    )

    await show_word_card(callback, words[0], 1, len(words), lang)
    await callback.answer()

async def show_word_card(callback: CallbackQuery, word_data: dict, current_idx: int, total: int, lang: str):
    """Отрисовка карточки слова дня (Шаг 1)"""
    w_de = word_data.get("word", "")
    art = word_data.get("article", "")
    pl = word_data.get("plural", "")
    pl_str = f", die {pl}" if pl and pl != "-" else ""
    art_str = f"*{art}* " if art and art != "-" else ""
    
    tr = word_data.get("translation", "")
    ex_de = word_data.get("example_de", "")
    ex_tr = word_data.get("example_tr", "")

    if lang == "ru":
        text = (
            f"📚 *Шаг 1 из 3: Слова дня ({current_idx}/{total})*\n\n"
            f"🇩🇪 {art_str}*{w_de}*{pl_str}\n"
            f"🇷🇺 *{tr}*\n\n"
            f"📖 _{ex_de}_\n"
            f"💬 _{ex_tr}_"
        )
    else:
        text = (
            f"📚 *Step 1 of 3: Daily Vocabulary ({current_idx}/{total})*\n\n"
            f"🇩🇪 {art_str}*{w_de}*{pl_str}\n"
            f"🇬🇧 *{tr}*\n\n"
            f"📖 _{ex_de}_\n"
            f"💬 _{ex_tr}_"
        )

    kb = get_workout_word_keyboard(current_idx, total, word_data.get("id", 0), lang=lang)
    await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("wo_voice:"))
async def cb_workout_voice(callback: CallbackQuery):
    """Озвучка слова в тренировке дня"""
    word_id = int(callback.data.split(":")[1])
    word_data = await db.get_word_by_id(word_id)
    if not word_data:
        await callback.answer("Слово не найдено")
        return

    full_phrase = f"{word_data['article']} {word_data['word']}" if word_data.get("article") else word_data["word"]
    audio_bytes = await synthesize_speech(full_phrase)
    if audio_bytes:
        voice_file = BufferedInputFile(audio_bytes, filename=f"word_{word_id}.ogg")
        await callback.message.answer_voice(voice=voice_file, caption=f"🗣 {full_phrase}")
        await mark_voice_sent(callback.message.chat.id, callback.message.message_id)
        await callback.answer("Озвучено!")
    else:
        await callback.answer("Ошибка синтеза речи", show_alert=True)

@router.callback_query(F.data == "wo_next_word")
async def cb_next_word(callback: CallbackQuery, state: FSMContext):
    """Переход к следующему слову дня или к шагу 2 (артикли)"""
    data = await state.get_data()
    words = data.get("words", [])
    idx = data.get("word_idx", 0) + 1
    lang = await db.get_user_lang(callback.from_user.id)

    if idx < len(words):
        await state.update_data(word_idx=idx)
        await show_word_card(callback, words[idx], idx + 1, len(words), lang)
        await callback.answer()
    else:
        # Переход к шагу 2: Блиц-артикли
        await state.set_state(WorkoutState.in_articles)
        articles = data.get("articles", [])
        await show_article_question(callback, articles[0], 1, len(articles), lang)
        await callback.answer()

async def show_article_question(callback: CallbackQuery, art_data: dict, current_idx: int, total: int, lang: str):
    """Отрисовка вопроса на артикль (Шаг 2)"""
    w_de = art_data.get("word", "")
    tr = art_data.get("translation", "")

    if lang == "ru":
        text = (
            f"🎯 *Шаг 2 из 3: Блиц-артикли ({current_idx}/{total})*\n\n"
            f"Какой артикль у этого существительного?\n\n"
            f"🇩🇪 *... {w_de}*\n"
            f"🇷🇺 _{tr}_\n\n"
            f"Выбери правильный вариант ниже 👇"
        )
    else:
        text = (
            f"🎯 *Step 2 of 3: Article Blitz ({current_idx}/{total})*\n\n"
            f"Which article belongs to this noun?\n\n"
            f"🇩🇪 *... {w_de}*\n"
            f"🇬🇧 _{tr}_\n\n"
            f"Select the correct option below 👇"
        )

    kb = get_workout_article_keyboard(art_data.get("id", 0), lang=lang)
    await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("wo_art:"))
async def cb_answer_article(callback: CallbackQuery, state: FSMContext):
    """Проверка ответа на артикль"""
    parts = callback.data.split(":")
    word_id = int(parts[1])
    choice = parts[2]

    data = await state.get_data()
    articles = data.get("articles", [])
    art_idx = data.get("art_idx", 0)
    art_correct = data.get("art_correct", 0)
    lang = await db.get_user_lang(callback.from_user.id)

    curr_art = articles[art_idx]
    correct_art = curr_art.get("article", "").lower().strip()
    is_correct = (choice.lower().strip() == correct_art)

    if is_correct:
        art_correct += 1
        await state.update_data(art_correct=art_correct)
        result_header = "✅ *Верно!*" if lang == "ru" else "✅ *Correct!*"
    else:
        result_header = (
            f"❌ *Неверно.* Правильно: *{correct_art} {curr_art['word']}*"
            if lang == "ru"
            else f"❌ *Incorrect.* Correct: *{correct_art} {curr_art['word']}*"
        )

    w_de = curr_art.get("word", "")
    tr = curr_art.get("translation", "")

    text = (
        f"🎯 *Шаг 2 из 3: Блиц-артикли ({art_idx + 1}/{len(articles)})*\n\n"
        f"{result_header}\n\n"
        f"🇩🇪 *{correct_art} {w_de}*\n"
        f"💬 _{tr}_"
    )

    kb = get_workout_next_article_keyboard(art_idx + 1, len(articles), lang=lang)
    await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer("Верно!" if is_correct else "Ошибка!")

@router.callback_query(F.data == "wo_next_art")
async def cb_next_art(callback: CallbackQuery, state: FSMContext):
    """Переход к следующему артиклю или к шагу 3 (вопрос дня)"""
    data = await state.get_data()
    articles = data.get("articles", [])
    idx = data.get("art_idx", 0) + 1
    lang = await db.get_user_lang(callback.from_user.id)

    if idx < len(articles):
        await state.update_data(art_idx=idx)
        await show_article_question(callback, articles[idx], idx + 1, len(articles), lang)
        await callback.answer()
    else:
        # Переход к шагу 3: Вопрос дня от Аиста
        await state.set_state(WorkoutState.waiting_question_reply)
        question = data.get("question", {})
        q_de = question.get("de", "")
        q_tr = question.get(lang, question.get("ru", ""))

        if lang == "ru":
            text = (
                f"💬 *Шаг 3 из 3: Вопрос дня от Аиста*\n\n"
                f"🇩🇪 *«{q_de}»*\n"
                f"🇷🇺 _{q_tr}_\n\n"
                f"👉 *Ответь прямо сейчас текстом или голосовым сообщением на немецком!*\n\n"
                f"Аист разберет твою грамматику, подскажет естественные фразы и начислит победные очки."
            )
        else:
            text = (
                f"💬 *Step 3 of 3: Question of the Day from Stork*\n\n"
                f"🇩🇪 *«{q_de}»*\n"
                f"🇬🇧 _{q_tr}_\n\n"
                f"👉 *Reply right now with text or a voice message in German!*\n\n"
                f"Stork will review your grammar, share feedback, and award your daily bonus."
            )

        kb = get_workout_question_keyboard(lang=lang)
        await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")
        await callback.answer()

@router.callback_query(F.data == "wo_q_hint")
async def cb_workout_q_hint(callback: CallbackQuery, state: FSMContext):
    """Всплывающая подсказка для ответа на вопрос дня"""
    data = await state.get_data()
    question = data.get("question", {})
    lang = await db.get_user_lang(callback.from_user.id)
    hint = question.get("hint_" + lang, question.get("hint_ru", ""))
    await callback.answer(hint, show_alert=True)

@router.message(WorkoutState.waiting_question_reply, F.voice)
@router.message(WorkoutState.waiting_question_reply, F.text)
async def process_workout_reply(message: Message, state: FSMContext):
    """Обработка текстового или голосового ответа на вопрос дня"""
    data = await state.get_data()
    question = data.get("question", {})
    art_correct = data.get("art_correct", 0)
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)

    # 1. Получение текста (голос или текст)
    if message.voice:
        status_msg = await message.answer("🎧 Распознаю твою голосовую реплику...")
        voice_text = await transcribe_voice(message.bot, message.voice.file_id)
        try:
            await status_msg.delete()
        except Exception:
            pass

        if not voice_text:
            await message.answer(
                "Не удалось расслышать голосовое сообщение. Пожалуйста, повтори еще раз или напиши текстом:"
            )
            return
        user_text = voice_text
    else:
        user_text = message.text.strip()
        if user_text.startswith("/"):
            await state.clear()
            return

    status_msg = await message.answer("🪶 Аист анализирует твой ответ...")

    # 2. Оценка ответа через ИИ
    evaluation = await evaluate_daily_workout_answer(question, user_text, lang=lang)

    # 3. Фиксация завершения тренировки дня в БД
    res = await db.complete_daily_workout(user_id, xp=50)
    streak = res.get("streak", 1)
    total_score = res.get("total_score", 50)

    try:
        await status_msg.delete()
    except Exception:
        pass

    await state.clear()

    # 4. Итоговый победный экран
    if lang == "ru":
        finish_text = (
            f"🎉 *Тренировка дня успешно завершена!*\n\n"
            f"🗣 *Твой ответ:* _{user_text}_\n\n"
            f"🤖 *Разбор от Аиста:*\n{evaluation}\n\n"
            f"────────────────────\n"
            f"📊 *Результаты сегодняшней тренировки:*\n"
            f"• Слова дня: *5/5 изучено* 📚\n"
            f"• Блиц-артикли: *{art_correct}/5 верных* 🎯\n"
            f"• Награда: *+50 XP* ⭐️ (Всего: *{total_score} XP*)\n"
            f"• Ударный режим: *{streak} дн. подряд* 🔥\n\n"
            f"Отличная работа! Возвращайся завтра за новой порцией немецкого."
        )
    else:
        finish_text = (
            f"🎉 *Daily Workout Completed!*\n\n"
            f"🗣 *Your Answer:* _{user_text}_\n\n"
            f"🤖 *Stork's Feedback:*\n{evaluation}\n\n"
            f"────────────────────\n"
            f"📊 *Today's Results:*\n"
            f"• Vocabulary: *5/5 mastered* 📚\n"
            f"• Articles Blitz: *{art_correct}/5 correct* 🎯\n"
            f"• Reward: *+50 XP* ⭐️ (Total: *{total_score} XP*)\n"
            f"• Daily Streak: *{streak} days in a row* 🔥\n\n"
            f"Great job! See you tomorrow for the next workout."
        )

    kb = get_workout_finish_keyboard(lang=lang)
    await message.answer(finish_text, reply_markup=kb, parse_mode="Markdown")
