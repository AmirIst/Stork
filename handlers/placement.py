import logging
from typing import List
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import db
from locales.manager import i18n
from services.placement_test import (
    generate_placement_session,
    get_question_by_id,
    evaluate_placement_test,
    get_level_description
)
from services.ui_helper import show_or_update_window
from keyboards.inline import (
    get_placement_welcome_keyboard,
    get_placement_question_keyboard,
    get_placement_result_keyboard,
    get_back_to_menu_keyboard
)

logger = logging.getLogger(__name__)
router = Router()

class PlacementState(StatesGroup):
    testing = State()

def get_progress_bar(current: int, total: int = 20) -> str:
    """Генерация компактного графического прогресс-бара из 10 сегментов"""
    filled_blocks = min(10, max(1, round((current / total) * 10)))
    empty_blocks = 10 - filled_blocks
    return f"{'🟩' * filled_blocks}{'⬜' * empty_blocks} ({current}/{total})"

async def render_placement_question(callback: CallbackQuery, q_idx: int, session_q_ids: List[int], lang: str):
    """Отображение текущего вопроса теста с прогрессом и вариантами ответа"""
    q_id = session_q_ids[q_idx]
    q_data = get_question_by_id(q_id)
    q_num = q_idx + 1
    total = len(session_q_ids)

    lvl_emoji = "🌱" if q_data["level"] == "A1" else ("🌿" if q_data["level"] == "A2" else "🌳")
    lvl_label = f"{lvl_emoji} Блок {q_data['level']}" if lang == "ru" else f"{lvl_emoji} Section {q_data['level']}"
    topic_label = q_data["topic"].get(lang, q_data["topic"]["ru"])

    progress = get_progress_bar(q_num, total)

    if lang == "ru":
        text = (
            f"🎓 *Тест на уровень: Вопрос {q_num} из {total}*\n"
            f"{progress}\n\n"
            f"📌 *{lvl_label}* • _{topic_label}_\n\n"
            f"🇩🇪 *{q_data['question']}*\n\n"
            f"Выбери правильный вариант ответа ниже 👇"
        )
    else:
        text = (
            f"🎓 *Level Test: Question {q_num} of {total}*\n"
            f"{progress}\n\n"
            f"📌 *{lvl_label}* • _{topic_label}_\n\n"
            f"🇩🇪 *{q_data['question']}*\n\n"
            f"Select the correct answer option below 👇"
        )

    await show_or_update_window(
        callback,
        text,
        reply_markup=get_placement_question_keyboard(q_idx, q_data["options"], lang=lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "menu_placement")
async def cb_menu_placement(callback: CallbackQuery, state: FSMContext):
    """Приветственный экран теста на уровень немецкого языка"""
    await state.clear()
    lang = await db.get_user_lang(callback.from_user.id)
    text = i18n.get("placement_welcome", lang)

    await show_or_update_window(
        callback,
        text,
        reply_markup=get_placement_welcome_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "placement_start")
async def cb_start_placement(callback: CallbackQuery, state: FSMContext):
    """Старт теста с генерацией уникальной выборки из 20 вопросов"""
    await state.set_state(PlacementState.testing)
    session_questions = generate_placement_session(count=20, a1_count=7, a2_count=7, b1_count=6)
    session_q_ids = [q["id"] for q in session_questions]
    await state.update_data(session_q_ids=session_q_ids, current_idx=0, user_answers=[])
    lang = await db.get_user_lang(callback.from_user.id)

    await render_placement_question(callback, q_idx=0, session_q_ids=session_q_ids, lang=lang)
    await callback.answer()

@router.callback_query(F.data.startswith("pq:"))
async def cb_answer_placement_question(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа на текущий вопрос и переход к следующему"""
    parts = callback.data.split(":")
    q_idx = int(parts[1])
    opt_idx = int(parts[2])

    data = await state.get_data()
    session_q_ids = data.get("session_q_ids")
    if not session_q_ids:
        session_questions = generate_placement_session(count=20, a1_count=7, a2_count=7, b1_count=6)
        session_q_ids = [q["id"] for q in session_questions]

    answers = data.get("user_answers", [])
    answers.append(opt_idx)
    next_idx = q_idx + 1

    lang = await db.get_user_lang(callback.from_user.id)

    if next_idx < len(session_q_ids):
        await state.update_data(current_idx=next_idx, user_answers=answers, session_q_ids=session_q_ids)
        await render_placement_question(callback, q_idx=next_idx, session_q_ids=session_q_ids, lang=lang)
        await callback.answer()
    else:
        # Тест завершен! Формируем сертификат
        await state.clear()
        total_questions = len(session_q_ids)
        result_level, total_score, breakdown = evaluate_placement_test(answers, question_ids=session_q_ids)

        # Сохраняем в базу данных
        await db.save_user_placement_result(callback.from_user.id, result_level, total_score)
        await db.unlock_achievement(callback.from_user.id, "placement_certified")

        percent = int((total_score / total_questions) * 100)
        desc = get_level_description(result_level, lang=lang)

        a1_c, a1_t = breakdown["A1"]
        a2_c, a2_t = breakdown["A2"]
        b1_c, b1_t = breakdown["B1"]

        medal = "🥇" if result_level == "B1" else ("🥈" if result_level == "A2" else "🥉")

        if lang == "ru":
            cert_text = (
                f"🎓🪶 *Сертификат уровня Stork CEFR*\n\n"
                f"{medal} *Подтвержденный уровень: {desc['name']}*\n"
                f"🎯 *Результат:* {total_score} из {total_questions} правильных ({percent}%)\n\n"
                f"📊 *Детальный срез по блокам:*\n"
                f"• 🌱 Блок A1 (Основы): *{a1_c}/{a1_t}*\n"
                f"• 🌿 Блок A2 (Разговорный): *{a2_c}/{a2_t}*\n"
                f"• 🌳 Блок B1 (Продвинутый): *{b1_c}/{b1_t}*\n\n"
                f"💡 *{desc['title']}*\n"
                f"{desc['text']}\n\n"
                f"👉 *Совет от Аиста:* {desc['tip']}"
            )
        else:
            cert_text = (
                f"🎓🪶 *Stork CEFR Placement Certificate*\n\n"
                f"{medal} *Verified Level: {desc['name']}*\n"
                f"🎯 *Score:* {total_score} of {total_questions} correct ({percent}%)\n\n"
                f"📊 *Section Breakdown:*\n"
                f"• 🌱 A1 Section (Foundations): *{a1_c}/{a1_t}*\n"
                f"• 🌿 A2 Section (Conversational): *{a2_c}/{a2_t}*\n"
                f"• 🌳 B1 Section (Independent): *{b1_c}/{b1_t}*\n\n"
                f"💡 *{desc['title']}*\n"
                f"{desc['text']}\n\n"
                f"👉 *Stork's Tip:* {desc['tip']}"
            )

        await show_or_update_window(
            callback,
            cert_text,
            reply_markup=get_placement_result_keyboard(result_level, lang=lang),
            parse_mode="Markdown"
        )
        await callback.answer("Тест успешно завершен!" if lang == "ru" else "Test completed!")
