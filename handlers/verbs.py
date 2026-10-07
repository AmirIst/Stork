import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import db
from locales.manager import i18n
from services.verbs_service import generate_verb_sprint_question
from keyboards.inline import (
    get_verbs_sprint_keyboard,
    get_next_verbs_sprint_keyboard
)
from services.ui_helper import show_or_update_window

logger = logging.getLogger(__name__)
router = Router()

class VerbsSprintState(StatesGroup):
    answering = State()

async def send_verb_question(callback: CallbackQuery, lang: str, state: FSMContext):
    """Отправка вопроса спринта глаголов и предлогов"""
    q_data = generate_verb_sprint_question(lang=lang)
    await state.set_state(VerbsSprintState.answering)
    await state.update_data(
        correct=q_data["correct"],
        explanation=q_data["explanation"]
    )

    kb = get_verbs_sprint_keyboard(q_data["options"], q_data["correct"], lang=lang)
    await show_or_update_window(callback, q_data["prompt"], reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "menu_verbs_sprint")
async def cb_menu_verbs_sprint(callback: CallbackQuery, state: FSMContext):
    """Вход в спринт глаголов и предлогов"""
    await callback.answer()
    lang = await db.get_user_lang(callback.from_user.id)
    await send_verb_question(callback, lang, state)

@router.callback_query(F.data.startswith("vs:"))
async def cb_check_verb_answer(callback: CallbackQuery, state: FSMContext):
    """Проверка ответа в спринте глаголов"""
    await callback.answer()
    parts = callback.data.split(":")
    is_correct = (parts[1] == "1")
    lang = await db.get_user_lang(callback.from_user.id)
    data = await state.get_data()
    correct_ans = data.get("correct", "")
    explanation = data.get("explanation", "")

    if is_correct:
        score, streak = await db.add_user_score(callback.from_user.id, points=1)
        header = f"{i18n.get('verbs_sprint_correct', lang)} 🔥 {streak}"
        await db.unlock_achievement(callback.from_user.id, "verbs_sprinter")
    else:
        await db.reset_streak(callback.from_user.id)
        header = i18n.get("verbs_sprint_wrong", lang, correct=correct_ans)

    await db.update_daily_streak(callback.from_user.id)

    full_text = f"{header}\n\n{explanation}"
    await show_or_update_window(
        callback,
        full_text,
        reply_markup=get_next_verbs_sprint_keyboard(lang),
        parse_mode="Markdown"
    )
