import io
import logging
from typing import Optional, Dict, Any, List

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import db
from locales.manager import i18n
from services.diagnostic_service import (
    EXPRESS_QUESTIONS,
    evaluate_express_diagnostic,
    GOETHE_B1_LESEN_TASKS,
    score_lesen_module,
    GOETHE_B1_HOEREN_TASKS,
    score_hoeren_module,
    GOETHE_B1_SCHREIBEN_PROMPT,
    evaluate_schreiben_module,
    GOETHE_B1_SPRECHEN_TASKS,
    evaluate_sprechen_module,
    calculate_readiness_overall,
    build_recommendations_and_actions,
    EXPRESS_VERSION,
    GOETHE_B1_VERSION,
    RUBRIC_WRITING_VERSION,
    RUBRIC_SPEAKING_VERSION,
    TELC_B1_VERSION,
    RUBRIC_TELC_WRITING_VERSION,
    RUBRIC_TELC_SPEAKING_VERSION,
    TELC_B1_LESEN_TASKS,
    score_telc_lesen_module,
    TELC_B1_SPRACHBAUSTEINE_INTRO,
    TELC_B1_SPRACHBAUSTEINE_TASKS,
    score_telc_sprachbausteine_module,
    TELC_B1_HOEREN_TASKS,
    score_telc_hoeren_module,
    TELC_B1_SCHREIBEN_PROMPT,
    evaluate_telc_schreiben_module,
    TELC_B1_SPRECHEN_TASKS,
    evaluate_telc_sprechen_module,
    calculate_telc_readiness_overall
)
from services.ai_tutor import transcribe_voice
from services.tts import synthesize_speech, VOICE_MALE
from services.ui_helper import show_or_update_window, mark_voice_sent
from keyboards.inline import (
    get_diagnostic_choice_keyboard,
    get_express_question_keyboard,
    get_express_result_keyboard,
    get_goethe_intro_keyboard,
    get_goethe_question_keyboard,
    get_goethe_cancel_keyboard,
    get_telc_intro_keyboard,
    get_telc_question_keyboard,
    get_telc_cancel_keyboard,
    get_diagnostic_recommendations_keyboard,
    get_main_menu_keyboard
)

logger = logging.getLogger(__name__)
router = Router()

class DiagnosticState(StatesGroup):
    express_testing = State()
    goethe_intro = State()
    goethe_lesen = State()
    goethe_hoeren = State()
    goethe_schreiben = State()
    goethe_sprechen_part1 = State()
    goethe_sprechen_part2 = State()
    goethe_sprechen_part3 = State()
    goethe_evaluating = State()
    telc_intro = State()
    telc_lesen = State()
    telc_sprachbausteine = State()
    telc_hoeren = State()
    telc_schreiben = State()
    telc_sprechen_part1 = State()
    telc_sprechen_part2 = State()
    telc_sprechen_part3 = State()
    telc_evaluating = State()

def get_mini_progress(current: int, total: int) -> str:
    filled = min(total, max(1, current))
    empty = max(0, total - filled)
    return f"{'🟩' * filled}{'⬜' * empty} ({current}/{total})"


# ==============================================================================
# ХАБ ДИАГНОСТИКИ И ВХОДНЫЕ ТОЧКИ (/test, diag_hub, menu_placement)
# ==============================================================================

@router.message(Command("test"))
async def cmd_diagnostic_test(message: Message, state: FSMContext):
    """Команда /test: переход в диагностический центр"""
    await state.clear()
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)
    latest = await db.get_latest_diagnostic(user_id)

    text = i18n.get("diagnostic_hub_title", lang)
    if latest:
        prev_lvl = latest.get("cefr_estimate", "B1")
        prev_score = latest.get("overall_diagnostic_score", 0)
        status = latest.get("readiness_status", "NOT_READY")
        if lang == "ru":
            text += f"\n\n📌 *Твой последний результат:* {prev_lvl} • {prev_score}/100 (статус: {status})"
        else:
            text += f"\n\n📌 *Your last diagnostic:* {prev_lvl} • {prev_score}/100 (status: {status})"

    kb = get_diagnostic_choice_keyboard(lang=lang, has_history=(latest is not None))
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.in_(["diag_hub", "menu_placement"]))
async def cb_diagnostic_hub(callback: CallbackQuery, state: FSMContext):
    """Вход в диагностический центр через меню"""
    await state.clear()
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)
    latest = await db.get_latest_diagnostic(user_id)

    text = i18n.get("diagnostic_hub_title", lang)
    if latest:
        prev_lvl = latest.get("cefr_estimate", "B1")
        prev_score = latest.get("overall_diagnostic_score", 0)
        status = latest.get("readiness_status", "NOT_READY")
        if lang == "ru":
            text += f"\n\n📌 *Твой последний результат:* {prev_lvl} • {prev_score}/100 (статус: {status})"
        else:
            text += f"\n\n📌 *Your last diagnostic:* {prev_lvl} • {prev_score}/100 (status: {status})"

    kb = get_diagnostic_choice_keyboard(lang=lang, has_history=(latest is not None))
    await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "diag_cancel")
async def cb_diagnostic_cancel(callback: CallbackQuery, state: FSMContext):
    """Прерывание теста и возврат в хаб диагностики"""
    await state.clear()
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)
    latest = await db.get_latest_diagnostic(user_id)

    cancel_msg = (
        "🛑 Тест прерван. Ты можешь вернуться к нему в любой момент!"
        if lang == "ru"
        else "🛑 Test cancelled. You can return anytime!"
    )
    await callback.answer(cancel_msg, show_alert=True)

    text = i18n.get("diagnostic_hub_title", lang)
    kb = get_diagnostic_choice_keyboard(lang=lang, has_history=(latest is not None))
    await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")


# ==============================================================================
# ПРОСМОТР ПРОФИЛЯ ДИАГНОСТИКИ (diag_my_profile)
# ==============================================================================

@router.callback_query(F.data == "diag_my_profile")
async def cb_my_diagnostic_profile(callback: CallbackQuery):
    """Экран с сохраненными результатами и персональным планом"""
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)
    latest = await db.get_latest_diagnostic(user_id)

    if not latest:
        msg = (
            "У тебя пока нет пройденных тестов. Пройди экспресс-тест, Goethe B1 или telc B1!"
            if lang == "ru"
            else "You haven't completed any diagnostics yet. Try Express Check, Goethe B1, or telc B1!"
        )
        await callback.answer(msg, show_alert=True)
        return

    exam_type = latest.get("exam_type", "goethe_b1")
    status = latest.get("readiness_status", "NOT_READY")
    cefr = latest.get("cefr_estimate", "B1")
    overall = latest.get("overall_diagnostic_score", 0)
    les = latest.get("lesen_score", 0)
    hoe = latest.get("hoeren_score", 0)
    sch = latest.get("schreiben_score", 0)
    spr = latest.get("sprechen_score", 0)
    sb = latest.get("sprachbausteine_score", 0)

    status_labels_ru = {
        "STRONG": "🟢 Готов к экзамену (Отличный результат)",
        "LIKELY_READY": "🟢 Высокие шансы сдать B1",
        "NEAR_PASS": "🟡 На грани сдачи (нужна точечная доработка)",
        "NOT_READY": "🔴 Требуется серьезная подготовка"
    }
    status_labels_en = {
        "STRONG": "🟢 Exam Ready (Strong Performance)",
        "LIKELY_READY": "🟢 Likely to Pass B1",
        "NEAR_PASS": "🟡 Borderline (Targeted Practice Needed)",
        "NOT_READY": "🔴 Not Ready Yet (Intensive Practice Needed)"
    }
    status_label = status_labels_ru.get(status, status) if lang == "ru" else status_labels_en.get(status, status)

    weak_points = latest.get("weak_points", [])
    raw_rubric = latest.get("raw_rubric_scores", {})

    if exam_type == "telc_b1":
        schriftlich = les + sb + hoe + sch
        muendlich = spr
        total_pts = schriftlich + muendlich
        telc_grade = raw_rubric.get("telc_grade", "Ausreichend")

        if lang == "ru":
            text = (
                f"📊 *Твой диагностический профиль telc Deutsch B1*\n\n"
                f"🎯 *Оценка уровня:* {cefr}\n"
                f"🏆 *Официальная оценка telc:* {telc_grade}\n"
                f"📌 *Статус готовности:* {status_label}\n"
                f"📈 *Общий балл:* {total_pts}/300 (индекс: {overall}/100)\n\n"
                f"📝 *Schriftliche Prüfung:* {schriftlich}/225 {'✅' if schriftlich >= 135 else '❌'}\n"
                f"• 📖 Lesen: *{les}/75*\n"
                f"• 🧩 Sprachbausteine: *{sb}/30*\n"
                f"• 🎧 Hören: *{hoe}/75*\n"
                f"• ✍️ Brief: *{sch}/45*\n\n"
                f"🗣️ *Mündliche Prüfung:* {muendlich}/75 {'✅' if muendlich >= 45 else '❌'}\n"
                f"• Sprechen: *{spr}/75*\n\n"
            )
            if weak_points:
                text += "🔍 *Обнаруженные слабые места:*\n"
                for wp in weak_points[:3]:
                    exp = wp.get("explanation_ru") or wp.get("topic") or ""
                    text += f"• {exp}\n"
                text += "\n"
            text += "👉 Нажми на кнопку ниже, чтобы перейти сразу к нужной тренировке:"
        else:
            text = (
                f"📊 *Your telc Deutsch B1 Diagnostic Profile*\n\n"
                f"🎯 *Estimated CEFR:* {cefr}\n"
                f"🏆 *Official telc Grade:* {telc_grade}\n"
                f"📌 *Readiness Status:* {status_label}\n"
                f"📈 *Total Score:* {total_pts}/300 (Index: {overall}/100)\n\n"
                f"📝 *Schriftliche Prüfung:* {schriftlich}/225 {'✅' if schriftlich >= 135 else '❌'}\n"
                f"• 📖 Lesen: *{les}/75*\n"
                f"• 🧩 Sprachbausteine: *{sb}/30*\n"
                f"• 🎧 Hören: *{hoe}/75*\n"
                f"• ✍️ Brief: *{sch}/45*\n\n"
                f"🗣️ *Mündliche Prüfung:* {muendlich}/75 {'✅' if muendlich >= 45 else '❌'}\n"
                f"• Sprechen: *{spr}/75*\n\n"
            )
            if weak_points:
                text += "🔍 *Detected Weak Points:*\n"
                for wp in weak_points[:3]:
                    exp = wp.get("explanation_en") or wp.get("topic") or ""
                    text += f"• {exp}\n"
                text += "\n"
            text += "👉 Tap a button below to jump straight to targeted practice:"

        scores = {
            "lesen": round((les / 75.0) * 100),
            "sprachbausteine": round((sb / 30.0) * 100),
            "hoeren": round((hoe / 75.0) * 100),
            "schreiben": round((sch / 45.0) * 100),
            "sprechen": round((spr / 75.0) * 100)
        }
        actions = build_recommendations_and_actions(weak_points, scores, native_lang=lang)
        kb = get_diagnostic_recommendations_keyboard(actions, lang=lang, exam_type="telc_b1")
    else:
        if lang == "ru":
            text = (
                f"📊 *Твой диагностический профиль Goethe B1*\n\n"
                f"🎯 *Оценка уровня:* {cefr}\n"
                f"🏆 *Диагностический балл Stork:* {overall}/100\n"
                f"📌 *Статус готовности:* {status_label}\n\n"
                f"📋 *Баллы по модулям (порог сдачи: от 60/100):*\n"
                f"• 📖 Lesen: *{les}/100* {'✅' if les >= 60 else '❌'}\n"
                f"• 🎧 Hören: *{hoe}/100* {'✅' if hoe >= 60 else '❌'}\n"
                f"• ✍️ Schreiben: *{sch}/100* {'✅' if sch >= 60 else '❌'}\n"
                f"• 🗣️ Sprechen: *{spr}/100* {'✅' if spr >= 60 else '❌'}\n\n"
            )
            if weak_points:
                text += "🔍 *Обнаруженные слабые места:*\n"
                for wp in weak_points[:3]:
                    exp = wp.get("explanation_ru") or wp.get("topic") or ""
                    text += f"• {exp}\n"
                text += "\n"
            text += "👉 Нажми на кнопку ниже, чтобы перейти сразу к нужной тренировке:"
        else:
            text = (
                f"📊 *Your Goethe B1 Diagnostic Profile*\n\n"
                f"🎯 *Estimated CEFR:* {cefr}\n"
                f"🏆 *Stork Diagnostic Score:* {overall}/100\n"
                f"📌 *Readiness Status:* {status_label}\n\n"
                f"📋 *Module Scores (Pass threshold: 60/100 each):*\n"
                f"• 📖 Lesen: *{les}/100* {'✅' if les >= 60 else '❌'}\n"
                f"• 🎧 Hören: *{hoe}/100* {'✅' if hoe >= 60 else '❌'}\n"
                f"• ✍️ Schreiben: *{sch}/100* {'✅' if sch >= 60 else '❌'}\n"
                f"• 🗣️ Sprechen: *{spr}/100* {'✅' if spr >= 60 else '❌'}\n\n"
            )
            if weak_points:
                text += "🔍 *Detected Weak Points:*\n"
                for wp in weak_points[:3]:
                    exp = wp.get("explanation_en") or wp.get("topic") or ""
                    text += f"• {exp}\n"
                text += "\n"
            text += "👉 Tap a button below to jump straight to targeted practice:"

        scores = {"lesen": les, "hoeren": hoe, "schreiben": sch, "sprechen": spr}
        actions = build_recommendations_and_actions(weak_points, scores, native_lang=lang)
        kb = get_diagnostic_recommendations_keyboard(actions, lang=lang, exam_type="goethe_b1")

    await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("diag_share_card"))
async def cb_diag_share_card(callback: CallbackQuery):
    """Генерация и отправка сертификата готовности к экзамену"""
    await callback.answer("Генерирую сертификат готовности...")
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)
    latest = await db.get_latest_diagnostic(user_id)

    if not latest:
        await callback.answer("Сначала пройдите диагностику!", show_alert=True)
        return

    from services.card_service import generate_diagnostic_card_image, get_diagnostic_share_content
    from keyboards.inline import get_diagnostic_card_keyboard
    from aiogram.types import BufferedInputFile

    exam_type = latest.get("exam_type", "goethe_b1")
    exam_title = "Goethe-Zertifikat B1" if exam_type == "goethe_b1" else ("telc Deutsch B1" if exam_type == "telc_b1" else "CEFR Placement")

    exam_data = {
        "user_id": user_id,
        "exam_title": exam_title,
        "overall_score": latest.get("overall_diagnostic_score", 0),
        "status_text": latest.get("readiness_status", "ГОТОВ К ЭКЗАМЕНУ"),
        "estimated_cefr": latest.get("cefr_estimate", "B1"),
        "lesen_score": latest.get("lesen_score", 0),
        "hoeren_score": latest.get("hoeren_score", 0),
        "schreiben_score": latest.get("schreiben_score", 0),
        "sprechen_score": latest.get("sprechen_score", 0),
    }

    caption, share_url = get_diagnostic_share_content(exam_data, lang)

    try:
        card_png = generate_diagnostic_card_image(exam_data)
        photo_file = BufferedInputFile(card_png, filename=f"stork_certificate_{user_id}.png")
        await callback.message.answer_photo(
            photo=photo_file,
            caption=caption,
            reply_markup=get_diagnostic_card_keyboard(share_url, lang),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка отправки сертификата: {e}")
        await callback.message.answer(
            caption,
            reply_markup=get_diagnostic_card_keyboard(share_url, lang),
            parse_mode="Markdown"
        )

# ==============================================================================
# ЭКСПРЕСС-ТЕСТ УРОВНЯ (⚡ 2-3 минуты, 8 вопросов)
# ==============================================================================

async def render_express_question_screen(callback: CallbackQuery, q_idx: int, lang: str):
    """Отображение текущего вопроса экспресс-теста"""
    total = len(EXPRESS_QUESTIONS)
    q = EXPRESS_QUESTIONS[q_idx]
    progress = get_mini_progress(q_idx + 1, total)

    lvl_emoji = "🌱" if q["level"] == "A1" else ("🌿" if q["level"] == "A2" else "🌳")
    if lang == "ru":
        text = (
            f"⚡ *Экспресс-проверка уровня: Вопрос {q_idx + 1} из {total}*\n"
            f"{progress}\n\n"
            f"📌 *{lvl_emoji} Сложность:* {q['level']}\n\n"
            f"🇩🇪 *{q['question']}*\n\n"
            f"Выбери правильный ответ ниже 👇"
        )
    else:
        text = (
            f"⚡ *Express Level Check: Question {q_idx + 1} of {total}*\n"
            f"{progress}\n\n"
            f"📌 *{lvl_emoji} Level:* {q['level']}\n\n"
            f"🇩🇪 *{q['question']}*\n\n"
            f"Select the correct answer below 👇"
        )

    kb = get_express_question_keyboard(q_idx, q["options"], lang=lang)
    await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "diag_express_start")
async def cb_start_express(callback: CallbackQuery, state: FSMContext):
    """Старт экспресс-диагностики"""
    await state.set_state(DiagnosticState.express_testing)
    await state.update_data(current_idx=0, user_answers=[])
    lang = await db.get_user_lang(callback.from_user.id)
    await render_express_question_screen(callback, q_idx=0, lang=lang)
    await callback.answer()

@router.callback_query(F.data.startswith("exp_ans:"))
async def cb_answer_express(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа на вопрос экспресс-теста"""
    data = await state.get_data()
    current_idx = data.get("current_idx", 0)
    user_answers: List[int] = data.get("user_answers", [])

    parts = callback.data.split(":")
    q_idx = int(parts[1])
    opt_idx = int(parts[2])

    # Защита от двойного клика по старому вопросу
    if q_idx != current_idx:
        await callback.answer()
        return

    user_answers.append(opt_idx)
    next_idx = current_idx + 1
    lang = await db.get_user_lang(callback.from_user.id)

    if next_idx < len(EXPRESS_QUESTIONS):
        await state.update_data(current_idx=next_idx, user_answers=user_answers)
        await render_express_question_screen(callback, q_idx=next_idx, lang=lang)
        await callback.answer()
    else:
        # Завершение экспресс-теста
        await state.clear()
        res = evaluate_express_diagnostic(user_answers)
        user_id = callback.from_user.id

        # Сохраняем результат в базу данных
        await db.save_diagnostic_result(
            user_id=user_id,
            exam_type="express",
            exam_version=EXPRESS_VERSION,
            diagnostic_type="express",
            cefr_estimate=res["estimated_cefr"],
            readiness_status="NEAR_PASS" if res["estimated_cefr"] == "B1" else "NOT_READY",
            overall_diagnostic_score=res["score_pct"],
            weak_points=res["weaknesses"]
        )

        cefr = res["estimated_cefr"]
        correct = res["correct"]
        total = res["total"]
        score_pct = res["score_pct"]
        weaknesses = res["weaknesses"]

        if lang == "ru":
            desc_map = {
                "B1": "Отличная база! Твой уровень близок к B1. Самое время проверить готовность к экзамену в полном тесте Goethe B1.",
                "A2": "У тебя уверенный уровень A2. Для свободного B1 нужно закрепить порядок слов и сложные союзы.",
                "A1": "Начальный уровень A1. Рекомендуем начать с тренировки артиклей, базовых глаголов и карточек слов."
            }
            text = (
                f"⚡ *Результат экспресс-диагностики!*\n\n"
                f"🎯 *Ориентировочный уровень:* *{cefr}*\n"
                f"📊 *Правильных ответов:* {correct} из {total} ({score_pct}%)\n\n"
                f"💬 {desc_map.get(cefr, '')}\n\n"
            )
            if weaknesses:
                text += "🔍 *Темы, где были допущены ошибки:*\n"
                for w in weaknesses:
                    text += f"• _{w.get('explanation', '')}_\n"
                text += "\n"
            text += "👉 Что делаем дальше? Выбери действие:"
        else:
            desc_map = {
                "B1": "Great foundation! Your level is close to B1. Check your readiness in the full Goethe B1 test.",
                "A2": "Solid A2 level. To reach confident B1, practice sentence structures and subordinate clauses.",
                "A1": "Starting A1 level. We recommend focusing on articles, basic verb conjugations, and vocabulary."
            }
            text = (
                f"⚡ *Express Level Check Result!*\n\n"
                f"🎯 *Estimated Level:* *{cefr}*\n"
                f"📊 *Correct answers:* {correct} of {total} ({score_pct}%)\n\n"
                f"💬 {desc_map.get(cefr, '')}\n\n"
            )
            if weaknesses:
                text += "🔍 *Areas for improvement:*\n"
                for w in weaknesses:
                    text += f"• _{w.get('explanation', '')}_\n"
                text += "\n"
            text += "👉 What next? Choose an option below:"

        kb = get_express_result_keyboard(lang=lang)
        await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")
        await callback.answer()


# ==============================================================================
# ПОЛНЫЙ GOETHE B1 READINESS TEST (~25-30 минут, 4 модуля)
# ==============================================================================

@router.callback_query(F.data == "diag_goethe_start")
async def cb_start_goethe_readiness(callback: CallbackQuery, state: FSMContext):
    """Вводный экран перед началом полного теста Goethe B1"""
    await state.set_state(DiagnosticState.goethe_intro)
    lang = await db.get_user_lang(callback.from_user.id)

    if lang == "ru":
        text = (
            "🎯 *Goethe B1 Readiness Test: Проверка готовности* 🇩🇪🪶\n\n"
            "Этот тест объективно оценит твои шансы сдать официальный Goethe-Zertifikat B1.\n\n"
            "📋 *Структура экзамена (4 модуля):*\n"
            "1. 📖 *Lesen (Чтение)*: 4 оригинальных задания на понимание аутентичных текстов.\n"
            "2. 🎧 *Hören (Аудирование)*: 2 аудиоситуации с немецким диктором.\n"
            "3. ✍️ *Schreiben (Письмо)*: ответ на письмо коллеги (40-70 слов). ИИ проверит работу по официальной 4-критериальной шкале.\n"
            "4. 🗣️ *Sprechen (Говорение)*: 3 устных ответа голосовыми сообщениями прямо в чат.\n\n"
            "⏱️ *Длительность:* ~25-30 минут в спокойном темпе.\n"
            "🎯 *Ориентир сдачи:* каждый модуль оценивается до 100 баллов. Официальный порог сдачи: от 60/100 по каждому модулю отдельно.\n\n"
            "Готов проверить свои силы?"
        )
    else:
        text = (
            "🎯 *Goethe B1 Readiness Test* 🇩🇪🪶\n\n"
            "This test provides a realistic assessment of your readiness for Goethe-Zertifikat B1.\n\n"
            "📋 *Exam Structure (4 modules):*\n"
            "1. 📖 *Lesen (Reading)*: 4 authentic text comprehension tasks.\n"
            "2. 🎧 *Hören (Listening)*: 2 real-life audio scenarios with native German speech.\n"
            "3. ✍️ *Schreiben (Writing)*: reply to a colleague's email (40-70 words). Evaluated via strict 4-criteria rubric.\n"
            "4. 🗣️ *Sprechen (Speaking)*: 3 spoken responses recorded via voice messages.\n\n"
            "⏱️ *Estimated duration:* ~25-30 minutes at your own pace.\n"
            "🎯 *Passing threshold:* each module scored up to 100 points, passing mark is 60/100 per module.\n\n"
            "Ready to test yourself?"
        )

    kb = get_goethe_intro_keyboard(lang=lang)
    await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


# ----------------- МОДУЛЬ 1: LESEN (Чтение) -----------------

async def render_goethe_lesen_screen(callback: CallbackQuery, task_idx: int, lang: str):
    """Отображение текущего задания модуля Lesen"""
    task = GOETHE_B1_LESEN_TASKS[task_idx]
    total = len(GOETHE_B1_LESEN_TASKS)
    progress = get_mini_progress(task_idx + 1, total)

    if lang == "ru":
        text = (
            f"📖 *Модуль 1: Lesen (Чтение)* • Задание {task_idx + 1} из {total}\n"
            f"{progress}\n\n"
            f"📌 *{task['title']}*\n\n"
            f"{task['text']}\n\n"
            f"❓ *{task['question']}*\n\n"
            f"Выбери правильный ответ ниже 👇"
        )
    else:
        text = (
            f"📖 *Module 1: Lesen (Reading)* • Task {task_idx + 1} of {total}\n"
            f"{progress}\n\n"
            f"📌 *{task['title']}*\n\n"
            f"{task['text']}\n\n"
            f"❓ *{task['question']}*\n\n"
            f"Select the correct answer below 👇"
        )

    kb = get_goethe_question_keyboard("les", task_idx, task["options"], lang=lang)
    await show_or_update_window(callback, text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "gb1_start_lesen")
async def cb_start_goethe_lesen(callback: CallbackQuery, state: FSMContext):
    """Старт модуля 1: Lesen"""
    await state.set_state(DiagnosticState.goethe_lesen)
    await state.update_data(
        lesen_current=0,
        lesen_answers=[],
        hoeren_current=0,
        hoeren_answers=[],
        sprechen_parts={}
    )
    lang = await db.get_user_lang(callback.from_user.id)
    await render_goethe_lesen_screen(callback, task_idx=0, lang=lang)
    await callback.answer()

@router.callback_query(F.data.startswith("gb1_les:"))
async def cb_answer_goethe_lesen(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа на задание Lesen"""
    data = await state.get_data()
    current_idx = data.get("lesen_current", 0)
    lesen_answers: List[int] = data.get("lesen_answers", [])

    parts = callback.data.split(":")
    task_idx = int(parts[1])
    opt_idx = int(parts[2])
    lang = await db.get_user_lang(callback.from_user.id)

    # Если пришел ответ на устаревший вопрос, принудительно обновляем окно до актуального вопроса
    if task_idx != current_idx:
        if current_idx < len(GOETHE_B1_LESEN_TASKS):
            await render_goethe_lesen_screen(callback, task_idx=current_idx, lang=lang)
        await callback.answer()
        return

    lesen_answers.append(opt_idx)
    next_idx = current_idx + 1

    if next_idx < len(GOETHE_B1_LESEN_TASKS):
        await state.update_data(lesen_current=next_idx, lesen_answers=lesen_answers)
        await render_goethe_lesen_screen(callback, task_idx=next_idx, lang=lang)
        await callback.answer()
    else:
        # Переход к Модулю 2: Hören
        await state.update_data(lesen_answers=lesen_answers, hoeren_current=0)
        await state.set_state(DiagnosticState.goethe_hoeren)
        transition_text = (
            "✅ *Модуль 1 (Lesen) завершен!*\n\nПереходим к *Модулю 2: Hören (Аудирование)* 👇"
            if lang == "ru"
            else "✅ *Module 1 (Lesen) completed!*\n\nMoving to *Module 2: Hören (Listening)* 👇"
        )
        try:
            await callback.message.edit_text(transition_text, reply_markup=None, parse_mode="Markdown")
        except Exception:
            pass
        await callback.answer("Модуль Lesen завершен! Переходим к Hören." if lang == "ru" else "Lesen completed! Moving to Hören.")
        await send_goethe_hoeren_task(callback.message, state, task_idx=0, lang=lang)


# ----------------- МОДУЛЬ 2: HÖREN (Аудирование) -----------------

async def send_goethe_hoeren_task(message: Message, state: FSMContext, task_idx: int, lang: str):
    """Синтезирует аудио и отправляет голосовую запись с вопросом для модуля Hören"""
    task = GOETHE_B1_HOEREN_TASKS[task_idx]
    total = len(GOETHE_B1_HOEREN_TASKS)
    progress = get_mini_progress(task_idx + 1, total)

    # Информируем пользователя о генерации аудио
    await message.bot.send_chat_action(chat_id=message.chat.id, action="record_voice")

    audio_bytes = await synthesize_speech(task["audio_script"], voice=VOICE_MALE)
    if not audio_bytes:
        logger.error(f"Не удалось синтезировать аудио для Hören task {task['id']}")
        # Если синтез не удался, отправляем текстовую транскрипцию в качестве аварийного режима
        audio_bytes = b""

    voice_caption = (
        f"🎧 *Модуль 2: Hören (Аудирование)* • Задание {task_idx + 1} из {total}\n"
        f"📌 *{task['title']}*\n\n"
        f"Внимательно прослушай запись диктора!"
        if lang == "ru"
        else
        f"🎧 *Module 2: Hören (Listening)* • Task {task_idx + 1} of {total}\n"
        f"📌 *{task['title']}*\n\n"
        f"Listen carefully to the audio recording!"
    )

    if audio_bytes:
        voice_file = BufferedInputFile(audio_bytes, filename=f"hoeren_{task['id']}.mp3")
        await message.answer_voice(voice=voice_file, caption=voice_caption, parse_mode="Markdown")
        mark_voice_sent(message.chat.id)
    else:
        await message.answer(f"{voice_caption}\n\n_{task['audio_script']}_", parse_mode="Markdown")

    q_text = (
        f"❓ *Вопрос к аудиозаписи:*\n\n"
        f"*{task['question']}*\n\n"
        f"Выбери правильный ответ ниже 👇"
        if lang == "ru"
        else
        f"❓ *Question:*\n\n"
        f"*{task['question']}*\n\n"
        f"Select the correct answer below 👇"
    )
    kb = get_goethe_question_keyboard("hoe", task_idx, task["options"], lang=lang)
    await message.answer(q_text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("gb1_hoe:"))
async def cb_answer_goethe_hoeren(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа на задание Hören"""
    data = await state.get_data()
    current_idx = data.get("hoeren_current", 0)
    hoeren_answers: List[int] = data.get("hoeren_answers", [])

    parts = callback.data.split(":")
    task_idx = int(parts[1])
    opt_idx = int(parts[2])

    if task_idx != current_idx:
        await callback.answer()
        return

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    hoeren_answers.append(opt_idx)
    next_idx = current_idx + 1
    lang = await db.get_user_lang(callback.from_user.id)

    if next_idx < len(GOETHE_B1_HOEREN_TASKS):
        await state.update_data(hoeren_current=next_idx, hoeren_answers=hoeren_answers)
        await callback.answer()
        await send_goethe_hoeren_task(callback.message, state, task_idx=next_idx, lang=lang)
    else:
        # Переход к Модулю 3: Schreiben
        await state.update_data(hoeren_answers=hoeren_answers)
        await state.set_state(DiagnosticState.goethe_schreiben)
        transition_text = (
            "✅ *Модуль 2 (Hören) завершен!*\n\nПереходим к *Модулю 3: Schreiben (Письменная часть)* 👇"
            if lang == "ru"
            else "✅ *Module 2 (Hören) completed!*\n\nMoving to *Module 3: Schreiben (Writing)* 👇"
        )
        try:
            await callback.message.edit_text(transition_text, reply_markup=None, parse_mode="Markdown")
        except Exception:
            pass
        await callback.answer("Модуль Hören завершен! Переходим к Schreiben." if lang == "ru" else "Hören completed! Moving to Schreiben.")
        await render_goethe_schreiben_screen(callback.message, lang=lang)


# ----------------- МОДУЛЬ 3: SCHREIBEN (Письмо) -----------------

async def render_goethe_schreiben_screen(message: Message, lang: str):
    """Отображение письменного задания модуля Schreiben"""
    prompt_info = GOETHE_B1_SCHREIBEN_PROMPT

    if lang == "ru":
        text = (
            "✍️ *Модуль 3: Schreiben (Письменная часть)*\n\n"
            "📌 *Задание: Ответ на приглашение*\n\n"
            f"{prompt_info['prompt_de']}\n\n"
            f"🎯 *Объем:* {prompt_info['target_words']}\n\n"
            "👉 *Напиши свой ответ на немецком прямо в чат обычным сообщением:*"
        )
    else:
        text = (
            "✍️ *Module 3: Schreiben (Writing Section)*\n\n"
            "📌 *Task: Reply to Invitation*\n\n"
            f"{prompt_info['prompt_de']}\n\n"
            f"🎯 *Target length:* {prompt_info['target_words']}\n\n"
            "👉 *Send your German written response directly in the chat:*"
        )

    kb = get_goethe_cancel_keyboard(lang=lang)
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.message(DiagnosticState.goethe_schreiben, F.text)
async def handle_goethe_schreiben_text(message: Message, state: FSMContext):
    """Прием и проверка письменного ответа через фиксированную рубрику в Gemini"""
    user_text = message.text.strip()
    lang = await db.get_user_lang(message.from_user.id)

    # Проверка на слишком короткий текст
    words = user_text.split()
    if len(words) < 10:
        warning = (
            "⚠️ Текст слишком короткий (меньше 10 слов). Пожалуйста, напиши хотя бы 30-40 слов, "
            "чтобы ИИ мог объективно оценить грамматику и раскрытие пунктов письма!"
            if lang == "ru"
            else
            "⚠️ The text is too short (fewer than 10 words). Please write at least 30-40 words "
            "so the diagnostic rubric can properly evaluate grammar and task completion!"
        )
        await message.answer(warning)
        return

    status_msg = (
        "⏳ *Твой текст принят!* Оцениваем выполнение задачи, грамматику, порядок слов и словарный запас..."
        if lang == "ru"
        else
        "⏳ *Text received!* Evaluating task completion, grammar, word order, and vocabulary..."
    )
    status_notice = await message.answer(status_msg, parse_mode="Markdown")

    schreiben_res = await evaluate_schreiben_module(user_text, native_lang=lang)
    await state.update_data(schreiben_res=schreiben_res, user_schreiben_text=user_text)

    try:
        await status_notice.delete()
    except Exception:
        pass

    # Переход к Модулю 4: Sprechen
    await state.set_state(DiagnosticState.goethe_sprechen_part1)
    await render_goethe_sprechen_screen(message, part_num=1, lang=lang)


# ----------------- МОДУЛЬ 4: SPRECHEN (Говорение) -----------------

async def render_goethe_sprechen_screen(message: Message, part_num: int, lang: str):
    """Отображение заданий устного модуля Sprechen (3 части)"""
    part_key = f"part{part_num}"
    part_task = GOETHE_B1_SPRECHEN_TASKS[part_key]

    if lang == "ru":
        text = (
            f"🗣️ *Модуль 4: Sprechen (Устная часть)* • Часть {part_num} из 3\n\n"
            f"📌 *{part_task['title']}*\n\n"
            f"🇩🇪 *{part_task['prompt_de']}*\n\n"
            f"⏱️ *Формат ответа:* {part_task['target']}\n\n"
            f"👉 *Запиши голосовое сообщение со своим ответом (или отправь текстом):*"
        )
    else:
        text = (
            f"🗣️ *Module 4: Sprechen (Speaking Section)* • Part {part_num} of 3\n\n"
            f"📌 *{part_task['title']}*\n\n"
            f"🇩🇪 *{part_task['prompt_de']}*\n\n"
            f"⏱️ *Format:* {part_task['target']}\n\n"
            f"👉 *Record a voice message with your response (or send text):*"
        )

    kb = get_goethe_cancel_keyboard(lang=lang)
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

async def process_sprechen_input(message: Message, state: FSMContext, part_num: int):
    """Универсальная обработка голосового или текстового ответа в устном модуле"""
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)
    transcribed_text = ""

    if message.voice:
        try:
            file_info = await message.bot.get_file(message.voice.file_id)
            voice_stream = io.BytesIO()
            await message.bot.download_file(file_info.file_path, destination=voice_stream)
            audio_bytes = voice_stream.getvalue()
            transcribed_text = await transcribe_voice(audio_bytes, mime_type="audio/ogg")
        except Exception as e:
            logger.error(f"Ошибка транскрибации голосового сообщения в Goethe Sprechen: {e}")

        if not transcribed_text:
            err_msg = (
                "🪶 Не удалось разобрать запись. Пожалуйста, надиктуй еще раз погромче или напиши текстом!"
                if lang == "ru"
                else "🪶 Could not transcribe audio clearly. Please record again or submit via text!"
            )
            await message.answer(err_msg)
            return
    elif message.text:
        transcribed_text = message.text.strip()
    else:
        await message.answer("Пожалуйста, отправь голосовое сообщение или текст!" if lang == "ru" else "Please send a voice note or text!")
        return

    data = await state.get_data()
    sprechen_parts = data.get("sprechen_parts", {})
    sprechen_parts[f"part{part_num}"] = transcribed_text
    await state.update_data(sprechen_parts=sprechen_parts)

    if part_num == 1:
        await state.set_state(DiagnosticState.goethe_sprechen_part2)
        await render_goethe_sprechen_screen(message, part_num=2, lang=lang)
    elif part_num == 2:
        await state.set_state(DiagnosticState.goethe_sprechen_part3)
        await render_goethe_sprechen_screen(message, part_num=3, lang=lang)
    else:
        # Все 3 устные части сданы: финальная оценка и калькуляция
        await state.set_state(DiagnosticState.goethe_evaluating)
        await finalize_goethe_readiness_test(message, state, lang=lang)

@router.message(DiagnosticState.goethe_sprechen_part1, F.voice | F.text)
async def handle_sprechen_part1(message: Message, state: FSMContext):
    await process_sprechen_input(message, state, part_num=1)

@router.message(DiagnosticState.goethe_sprechen_part2, F.voice | F.text)
async def handle_sprechen_part2(message: Message, state: FSMContext):
    await process_sprechen_input(message, state, part_num=2)

@router.message(DiagnosticState.goethe_sprechen_part3, F.voice | F.text)
async def handle_sprechen_part3(message: Message, state: FSMContext):
    await process_sprechen_input(message, state, part_num=3)


# ----------------- ФИНАЛИЗАЦИЯ И РАСЧЕТ РЕЗУЛЬТАТОВ -----------------

async def finalize_goethe_readiness_test(message: Message, state: FSMContext, lang: str):
    """Итоговая оценка всех 4 модулей, сохранение в БД и показ диагностического отчета"""
    user_id = message.from_user.id
    data = await state.get_data()

    status_wait = (
        "⏳ *Идет комплексный расчет готовности к экзамену Goethe B1...*\n\n"
        "Нейросеть оценивает беглость речи, точность грамматики и словарный запас устной части..."
        if lang == "ru"
        else
        "⏳ *Computing comprehensive Goethe B1 Readiness assessment...*\n\n"
        "AI is evaluating oral fluency, grammatical accuracy, and vocabulary..."
    )
    status_msg = await message.answer(status_wait, parse_mode="Markdown")

    lesen_answers = data.get("lesen_answers", [])
    hoeren_answers = data.get("hoeren_answers", [])
    schreiben_res = data.get("schreiben_res", {})
    sprechen_parts = data.get("sprechen_parts", {})

    # Оценка устного модуля
    sprechen_res = await evaluate_sprechen_module(sprechen_parts, native_lang=lang)

    # Детерминированный подсчет объективных блоков
    score_lesen, lesen_errs = score_lesen_module(lesen_answers)
    score_hoeren, hoeren_errs = score_hoeren_module(hoeren_answers)
    score_schreiben = int(schreiben_res.get("score", 50))
    score_sprechen = int(sprechen_res.get("score", 50))

    readiness_status, overall_score, failed_count, weakest_mod = calculate_readiness_overall(
        lesen_score=score_lesen,
        hoeren_score=score_hoeren,
        schreiben_score=score_schreiben,
        sprechen_score=score_sprechen
    )

    # Оценка общего уровня CEFR по результатам
    if overall_score >= 70 and failed_count == 0:
        cefr_estimate = "B1"
    elif overall_score >= 55:
        cefr_estimate = "B1" if failed_count <= 1 else "A2"
    elif overall_score >= 40:
        cefr_estimate = "A2"
    else:
        cefr_estimate = "A1"

    # Сбор всех слабых мест и сильных сторон
    all_weak_points: List[Dict[str, Any]] = []
    all_weak_points.extend(lesen_errs)
    all_weak_points.extend(hoeren_errs)
    all_weak_points.extend(schreiben_res.get("weak_points", []))
    all_weak_points.extend(sprechen_res.get("weak_points", []))

    all_strengths: List[str] = []
    str_key = "strengths_ru" if lang == "ru" else "strengths_en"
    all_strengths.extend(schreiben_res.get(str_key, []))
    all_strengths.extend(sprechen_res.get(str_key, []))

    scores = {
        "lesen": score_lesen,
        "hoeren": score_hoeren,
        "schreiben": score_schreiben,
        "sprechen": score_sprechen
    }

    raw_rubric = {
        "writing": schreiben_res.get("criteria", {}),
        "speaking": sprechen_res.get("criteria", {}),
        "rubric_writing_version": RUBRIC_WRITING_VERSION,
        "rubric_speaking_version": RUBRIC_SPEAKING_VERSION
    }

    actions = build_recommendations_and_actions(all_weak_points, scores, native_lang=lang)

    # Сохранение в базу данных
    await db.save_diagnostic_result(
        user_id=user_id,
        exam_type="goethe_b1",
        exam_version=GOETHE_B1_VERSION,
        diagnostic_type="readiness",
        cefr_estimate=cefr_estimate,
        readiness_status=readiness_status,
        overall_diagnostic_score=overall_score,
        lesen_score=score_lesen,
        hoeren_score=score_hoeren,
        schreiben_score=score_schreiben,
        sprechen_score=score_sprechen,
        raw_rubric_scores=raw_rubric,
        module_results=scores,
        weak_points=all_weak_points,
        strengths=all_strengths,
        recommendations=actions,
        speaking_profile=sprechen_res.get("speaking_profile", {}),
        writing_profile=schreiben_res.get("writing_profile", {})
    )

    await state.clear()

    # Формирование итогового экрана
    status_titles_ru = {
        "STRONG": "🟢 Готов к экзамену B1 (Отличный результат)",
        "LIKELY_READY": "🟢 Высокие шансы сдать B1 (Likely Pass)",
        "NEAR_PASS": "🟡 На грани сдачи (требуется точечная доработка)",
        "NOT_READY": "🔴 Пока не готов (требуется подготовка)"
    }
    status_titles_en = {
        "STRONG": "🟢 Goethe B1 Ready (Strong Performance)",
        "LIKELY_READY": "🟢 Likely to Pass B1",
        "NEAR_PASS": "🟡 Near Pass Threshold (Borderline)",
        "NOT_READY": "🔴 Below Pass Threshold (Preparation Needed)"
    }
    status_title = status_titles_ru.get(readiness_status, readiness_status) if lang == "ru" else status_titles_en.get(readiness_status, readiness_status)

    w_crit = schreiben_res.get("criteria", {})
    s_crit = sprechen_res.get("criteria", {})

    if lang == "ru":
        report_text = (
            f"🎯 *Итоговый отчет: Goethe B1 Readiness Test*\n\n"
            f"📌 *Статус готовности:* {status_title}\n"
            f"🏆 *Диагностический балл Stork:* {overall_score}/100\n\n"
            f"📋 *Результаты по 4 модулям (порог сдачи: от 60/100):*\n"
            f"• 📖 *Lesen:* {score_lesen}/100 {'✅ Сдано' if score_lesen >= 60 else '❌ Ниже порога 60'}\n"
            f"• 🎧 *Hören:* {score_hoeren}/100 {'✅ Сдано' if score_hoeren >= 60 else '❌ Ниже порога 60'}\n"
            f"• ✍️ *Schreiben:* {score_schreiben}/100 {'✅ Сдано' if score_schreiben >= 60 else '❌ Ниже порога 60'}\n"
            f"  └ Задание: {w_crit.get('task_completion', 0)}/25 • Грамматика: {w_crit.get('grammar', 0)}/25 • Лексика: {w_crit.get('vocabulary', 0)}/25 • Структура: {w_crit.get('organization', 0)}/25\n"
            f"• 🗣️ *Sprechen:* {score_sprechen}/100 {'✅ Сдано' if score_sprechen >= 60 else '❌ Ниже порога 60'}\n"
            f"  └ Задание: {s_crit.get('task_completion', 0)}/25 • Беглость: {s_crit.get('fluency', 0)}/25 • Грамматика: {s_crit.get('grammar', 0)}/25 • Произношение: {s_crit.get('vocabulary_pronunciation', 0)}/25\n\n"
        )
        if failed_count > 0:
            report_text += f"⚠️ *Внимание:* {failed_count} из 4 модулей пока ниже проходного балла (60). Экзамен считается сданным только при успешной сдаче всех модулей!\n\n"
        else:
            report_text += "🎉 *Поздравляем!* Все 4 модуля преодолели официальный проходной порог 60 баллов!\n\n"

        if all_weak_points:
            report_text += "🔍 *Главные точки роста:*\n"
            for wp in all_weak_points[:3]:
                exp = wp.get("explanation_ru") or wp.get("topic") or ""
                report_text += f"• {exp}\n"
            report_text += "\n"

        report_text += (
            "ℹ️ _Это внутренняя диагностика Stork AI на основе официального формата Goethe B1. "
            "Каждый модуль оценивается независимо, результат не является официальным сертификатом Goethe-Institut._\n\n"
            "👉 *Твой персональный план тренировок:* выбери кнопку ниже, чтобы устранить ошибки прямо сейчас 👇"
        )
    else:
        report_text = (
            f"🎯 *Goethe B1 Readiness Test Report*\n\n"
            f"📌 *Readiness Status:* {status_title}\n"
            f"🏆 *Stork Diagnostic Score:* {overall_score}/100\n\n"
            f"📋 *Results across 4 modules (Pass threshold: 60/100 each):*\n"
            f"• 📖 *Lesen:* {score_lesen}/100 {'✅ Passed' if score_lesen >= 60 else '❌ Below 60 threshold'}\n"
            f"• 🎧 *Hören:* {score_hoeren}/100 {'✅ Passed' if score_hoeren >= 60 else '❌ Below 60 threshold'}\n"
            f"• ✍️ *Schreiben:* {score_schreiben}/100 {'✅ Passed' if score_schreiben >= 60 else '❌ Below 60 threshold'}\n"
            f"  └ Task: {w_crit.get('task_completion', 0)}/25 • Grammar: {w_crit.get('grammar', 0)}/25 • Vocab: {w_crit.get('vocabulary', 0)}/25 • Structure: {w_crit.get('organization', 0)}/25\n"
            f"• 🗣️ *Sprechen:* {score_sprechen}/100 {'✅ Passed' if score_sprechen >= 60 else '❌ Below 60 threshold'}\n"
            f"  └ Task: {s_crit.get('task_completion', 0)}/25 • Fluency: {s_crit.get('fluency', 0)}/25 • Grammar: {s_crit.get('grammar', 0)}/25 • Pronunciation: {s_crit.get('vocabulary_pronunciation', 0)}/25\n\n"
        )
        if failed_count > 0:
            report_text += f"⚠️ *Note:* {failed_count} of 4 modules are below the pass mark (60). To pass Goethe B1, all modules must reach 60+ individually!\n\n"
        else:
            report_text += "🎉 *Congratulations!* All 4 modules reached or exceeded the 60 point threshold!\n\n"

        if all_weak_points:
            report_text += "🔍 *Target Weak Points:*\n"
            for wp in all_weak_points[:3]:
                exp = wp.get("explanation_en") or wp.get("topic") or ""
                report_text += f"• {exp}\n"
            report_text += "\n"

        report_text += (
            "ℹ️ _This is an internal Stork AI diagnostic based on Goethe B1 specifications. "
            "Each module is scored independently; this is not an official Goethe certificate._\n\n"
            "👉 *Your Personal Action Plan:* choose a targeted training below 👇"
        )

    kb = get_diagnostic_recommendations_keyboard(actions, lang=lang)

    try:
        await status_msg.edit_text(report_text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await message.answer(report_text, reply_markup=kb, parse_mode="Markdown")


# ==============================================================================
# TELC DEUTSCH B1 READINESS TEST (~25 минут, 300 баллов)
# ==============================================================================

@router.callback_query(F.data == "diag_telc_start")
async def cb_start_telc_diagnostic(callback: CallbackQuery, state: FSMContext):
    """Старт проверки готовности к telc Deutsch B1"""
    await state.clear()
    await state.set_state(DiagnosticState.telc_intro)
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id)

    if lang == "ru":
        intro_text = (
            "🏛️ *telc Deutsch B1: Проверка готовности*\n\n"
            "Формат полностью соответствует официальному регламенту telc B1 (300 баллов):\n\n"
            "📝 *1. Schriftliche Prüfung (максимум 225 баллов, проходной порог 135 / 60%):*\n"
            "• 📖 *Leseverstehen:* 3 задания (75 баллов)\n"
            "• 🧩 *Sprachbausteine:* 5 пропусков в письме (30 баллов)\n"
            "• 🎧 *Hörverstehen:* 2 аудиоситуации (75 баллов)\n"
            "• ✍️ *Schriftlicher Ausdruck:* полуофициальное письмо по 3 пунктам (45 баллов)\n\n"
            "🗣️ *2. Mündliche Prüfung (максимум 75 баллов, проходной порог 45 / 60%):*\n"
            "• Kontaktaufnahme, Thema präsentieren, Gemeinsam etwas planen\n\n"
            "🏆 *Общий зачет:* 300 баллов. Чтобы сдать весь экзамен, нужно набрать минимум 180 баллов и обязательно преодолеть порог в обеих частях (письменной и устной).\n"
            "⏱️ *Время:* около 25 минут.\n\n"
            "Готов проверить свои силы по официальной шкале telc?"
        )
    else:
        intro_text = (
            "🏛️ *telc Deutsch B1 Readiness Test*\n\n"
            "Structured strictly according to the official telc Deutsch B1 framework (300 pts):\n\n"
            "📝 *1. Schriftliche Prüfung (max 225 pts, pass mark 135 / 60%):*\n"
            "• 📖 *Leseverstehen:* 3 tasks (75 pts)\n"
            "• 🧩 *Sprachbausteine:* cloze letter with 5 gaps (30 pts)\n"
            "• 🎧 *Hörverstehen:* 2 audio recordings (75 pts)\n"
            "• ✍️ *Schriftlicher Ausdruck:* letter covering 3 guiding points (45 pts)\n\n"
            "🗣️ *2. Mündliche Prüfung (max 75 pts, pass mark 45 / 60%):*\n"
            "• Kontaktaufnahme, Topic presentation, Planning together\n\n"
            "🏆 *Total Score:* 300 pts. To receive a certificate, you must score 180+ pts and pass both written and oral sections.\n"
            "⏱️ *Duration:* ~25 minutes.\n\n"
            "Ready to test your readiness against the official telc standard?"
        )

    kb = get_telc_intro_keyboard(lang=lang)
    await show_or_update_window(callback, intro_text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


# ----------------- TELC БЛОК 1: LESEVERSTEHEN (75 баллов) -----------------

@router.callback_query(F.data == "tb1_start_lesen")
async def cb_telc_start_lesen(callback: CallbackQuery, state: FSMContext):
    """Старт модуля 1: telc Leseverstehen"""
    await state.set_state(DiagnosticState.telc_lesen)
    await state.update_data(
        telc_lesen_current=0,
        telc_lesen_answers=[]
    )
    await callback.answer()
    lang = await db.get_user_lang(callback.from_user.id)
    await send_telc_lesen_task(callback.message, state, task_idx=0, lang=lang)

async def send_telc_lesen_task(message: Message, state: FSMContext, task_idx: int, lang: str):
    """Отправка задания модуля telc Lesen"""
    total = len(TELC_B1_LESEN_TASKS)
    task = TELC_B1_LESEN_TASKS[task_idx]
    progress = get_mini_progress(task_idx + 1, total)

    if lang == "ru":
        text = (
            f"📖 *telc B1: Leseverstehen* • Задание {task_idx + 1} из {total}\n"
            f"{progress}\n\n"
            f"📌 *{task['title']}* (25 баллов)\n\n"
            f"_{task['text']}_\n\n"
            f"❓ *Вопрос:* {task['question']}\n\n"
            f"Выбери правильный вариант ответа ниже 👇"
        )
    else:
        text = (
            f"📖 *telc B1: Leseverstehen* • Task {task_idx + 1} of {total}\n"
            f"{progress}\n\n"
            f"📌 *{task['title']}* (25 pts)\n\n"
            f"_{task['text']}_\n\n"
            f"❓ *Question:* {task['question']}\n\n"
            f"Select the correct answer below 👇"
        )

    kb = get_telc_question_keyboard("les", task_idx, task["options"], lang=lang)
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("tb1_les:"))
async def cb_answer_telc_lesen(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа на задание Leseverstehen"""
    data = await state.get_data()
    current_idx = data.get("telc_lesen_current", 0)
    lesen_answers: List[int] = data.get("telc_lesen_answers", [])

    parts = callback.data.split(":")
    task_idx = int(parts[1])
    opt_idx = int(parts[2])

    if task_idx != current_idx:
        await callback.answer()
        return

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    lesen_answers.append(opt_idx)
    next_idx = current_idx + 1
    lang = await db.get_user_lang(callback.from_user.id)

    if next_idx < len(TELC_B1_LESEN_TASKS):
        await state.update_data(telc_lesen_current=next_idx, telc_lesen_answers=lesen_answers)
        await callback.answer()
        await send_telc_lesen_task(callback.message, state, task_idx=next_idx, lang=lang)
    else:
        # Переход к Блоку 2: Sprachbausteine
        await state.update_data(
            telc_lesen_answers=lesen_answers,
            telc_sb_current=0,
            telc_sb_answers=[]
        )
        await state.set_state(DiagnosticState.telc_sprachbausteine)
        transition_text = (
            "✅ *Блок Leseverstehen завершен!*\n\n"
            "Переходим к фирменному разделу telc: *Sprachbausteine (Грамматика и связность в письме)* 👇"
            if lang == "ru"
            else "✅ *Leseverstehen completed!*\n\nMoving to *Sprachbausteine (Grammar & Vocabulary in Context)* 👇"
        )
        try:
            await callback.message.edit_text(transition_text, reply_markup=None, parse_mode="Markdown")
        except Exception:
            pass
        await callback.answer("Lesen завершено! Переходим к Sprachbausteine." if lang == "ru" else "Lesen completed! Moving to Sprachbausteine.")
        await send_telc_sprachbausteine_task(callback.message, state, task_idx=0, lang=lang)


# ----------------- TELC БЛОК 2: SPRACHBAUSTEINE (30 баллов) -----------------

async def send_telc_sprachbausteine_task(message: Message, state: FSMContext, task_idx: int, lang: str):
    """Отправка задания telc Sprachbausteine"""
    total = len(TELC_B1_SPRACHBAUSTEINE_TASKS)
    task = TELC_B1_SPRACHBAUSTEINE_TASKS[task_idx]
    progress = get_mini_progress(task_idx + 1, total)

    if lang == "ru":
        text = (
            f"🧩 *telc B1: Sprachbausteine* • Пропуск {task_idx + 1} из {total}\n"
            f"{progress}\n\n"
            f"📌 *Текст письма:*\n"
            f"_{TELC_B1_SPRACHBAUSTEINE_INTRO}_\n\n"
            f"❓ *{task['prompt']}* (6 баллов)\n\n"
            f"Выбери подходящее слово для этого пропуска 👇"
        )
    else:
        text = (
            f"🧩 *telc B1: Sprachbausteine* • Gap {task_idx + 1} of {total}\n"
            f"{progress}\n\n"
            f"📌 *Letter text:*\n"
            f"_{TELC_B1_SPRACHBAUSTEINE_INTRO}_\n\n"
            f"❓ *{task['prompt']}* (6 pts)\n\n"
            f"Select the correct option for this gap 👇"
        )

    kb = get_telc_question_keyboard("sb", task_idx, task["options"], lang=lang)
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("tb1_sb:"))
async def cb_answer_telc_sprachbausteine(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа на пропуск Sprachbausteine"""
    data = await state.get_data()
    current_idx = data.get("telc_sb_current", 0)
    sb_answers: List[int] = data.get("telc_sb_answers", [])

    parts = callback.data.split(":")
    task_idx = int(parts[1])
    opt_idx = int(parts[2])

    if task_idx != current_idx:
        await callback.answer()
        return

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    sb_answers.append(opt_idx)
    next_idx = current_idx + 1
    lang = await db.get_user_lang(callback.from_user.id)

    if next_idx < len(TELC_B1_SPRACHBAUSTEINE_TASKS):
        await state.update_data(telc_sb_current=next_idx, telc_sb_answers=sb_answers)
        await callback.answer()
        await send_telc_sprachbausteine_task(callback.message, state, task_idx=next_idx, lang=lang)
    else:
        # Переход к Блоку 3: Hörverstehen
        await state.update_data(
            telc_sb_answers=sb_answers,
            telc_hoe_current=0,
            telc_hoe_answers=[]
        )
        await state.set_state(DiagnosticState.telc_hoeren)
        transition_text = (
            "✅ *Блок Sprachbausteine завершен!*\n\n"
            "Переходим к аудированию: *Hörverstehen (75 баллов)* 👇"
            if lang == "ru"
            else "✅ *Sprachbausteine completed!*\n\nMoving to *Hörverstehen (Listening, 75 pts)* 👇"
        )
        try:
            await callback.message.edit_text(transition_text, reply_markup=None, parse_mode="Markdown")
        except Exception:
            pass
        await callback.answer("Sprachbausteine завершено! Переходим к Hören." if lang == "ru" else "Sprachbausteine completed! Moving to Hören.")
        await send_telc_hoeren_task(callback.message, state, task_idx=0, lang=lang)


# ----------------- TELC БЛОК 3: HÖRVERSTEHEN (75 баллов) -----------------

async def send_telc_hoeren_task(message: Message, state: FSMContext, task_idx: int, lang: str):
    """Отправка аудирования telc Hören с Edge-TTS озвучкой"""
    total = len(TELC_B1_HOEREN_TASKS)
    task = TELC_B1_HOEREN_TASKS[task_idx]

    try:
        audio_bytes = await synthesize_speech(task["audio_script"], voice=VOICE_MALE)
    except Exception as e:
        logger.error(f"Ошибка озвучки аудиофайла для telc Hören {task['id']}: {e}")
        audio_bytes = b""

    voice_caption = (
        f"🎧 *telc B1: Hörverstehen* • Аудио {task_idx + 1} из {total}\n"
        f"📌 *{task['title']}* ({task['points']} баллов)\n\n"
        f"Внимательно прослушай запись диктора!"
        if lang == "ru"
        else
        f"🎧 *telc B1: Hörverstehen* • Audio {task_idx + 1} of {total}\n"
        f"📌 *{task['title']}* ({task['points']} pts)\n\n"
        f"Listen carefully to the recording!"
    )

    if audio_bytes:
        voice_file = BufferedInputFile(audio_bytes, filename=f"telc_hoeren_{task['id']}.mp3")
        await message.answer_voice(voice=voice_file, caption=voice_caption, parse_mode="Markdown")
        mark_voice_sent(message.chat.id)
    else:
        await message.answer(f"{voice_caption}\n\n_{task['audio_script']}_", parse_mode="Markdown")

    q_text = (
        f"❓ *Вопрос к аудиозаписи:*\n\n"
        f"*{task['question']}*\n\n"
        f"Выбери правильный ответ ниже 👇"
        if lang == "ru"
        else
        f"❓ *Question:*\n\n"
        f"*{task['question']}*\n\n"
        f"Select the correct answer below 👇"
    )
    kb = get_telc_question_keyboard("hoe", task_idx, task["options"], lang=lang)
    await message.answer(q_text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("tb1_hoe:"))
async def cb_answer_telc_hoeren(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа на задание Hörverstehen"""
    data = await state.get_data()
    current_idx = data.get("telc_hoe_current", 0)
    hoe_answers: List[int] = data.get("telc_hoe_answers", [])

    parts = callback.data.split(":")
    task_idx = int(parts[1])
    opt_idx = int(parts[2])

    if task_idx != current_idx:
        await callback.answer()
        return

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    hoe_answers.append(opt_idx)
    next_idx = current_idx + 1
    lang = await db.get_user_lang(callback.from_user.id)

    if next_idx < len(TELC_B1_HOEREN_TASKS):
        await state.update_data(telc_hoe_current=next_idx, telc_hoe_answers=hoe_answers)
        await callback.answer()
        await send_telc_hoeren_task(callback.message, state, task_idx=next_idx, lang=lang)
    else:
        # Переход к Блоку 4: Schriftlicher Ausdruck
        await state.update_data(telc_hoe_answers=hoe_answers)
        await state.set_state(DiagnosticState.telc_schreiben)
        transition_text = (
            "✅ *Блок Hörverstehen завершен!*\n\n"
            "Переходим к письму: *Schriftlicher Ausdruck (Brief, 45 баллов)* 👇"
            if lang == "ru"
            else "✅ *Hörverstehen completed!*\n\nMoving to *Schriftlicher Ausdruck (Letter, 45 pts)* 👇"
        )
        try:
            await callback.message.edit_text(transition_text, reply_markup=None, parse_mode="Markdown")
        except Exception:
            pass
        await callback.answer("Hören завершено! Переходим к Schreiben." if lang == "ru" else "Hören completed! Moving to Schreiben.")
        await render_telc_schreiben_screen(callback.message, lang=lang)


# ----------------- TELC БЛОК 4: SCHRIFTLICHER AUSDRUCK (45 баллов) -----------------

async def render_telc_schreiben_screen(message: Message, lang: str):
    """Отображение письменного задания telc (полуофициальное письмо)"""
    prompt_info = TELC_B1_SCHREIBEN_PROMPT

    if lang == "ru":
        text = (
            "✍️ *telc B1: Schriftlicher Ausdruck (Brief)*\n\n"
            "📌 *Задание: Полуофициальное письмо*\n\n"
            f"{prompt_info['prompt_de']}\n\n"
            f"🎯 *Максимум:* 45 баллов (по официальной шкале telc)\n"
            f"📝 *Объем:* {prompt_info['target_words']}\n\n"
            "👉 *Напиши письмо на немецком прямо в ответном сообщении:*"
        )
    else:
        text = (
            "✍️ *telc B1: Schriftlicher Ausdruck (Letter)*\n\n"
            "📌 *Task: Semi-formal Letter*\n\n"
            f"{prompt_info['prompt_de']}\n\n"
            f"🎯 *Maximum score:* 45 pts (official telc rubric)\n"
            f"📝 *Length:* {prompt_info['target_words']}\n\n"
            "👉 *Send your letter in German directly in the chat:*"
        )

    kb = get_telc_cancel_keyboard(lang=lang)
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.message(DiagnosticState.telc_schreiben, F.text)
async def handle_telc_schreiben_text(message: Message, state: FSMContext):
    """Прием и проверка письменной работы telc B1 через Gemini"""
    user_text = message.text.strip()
    lang = await db.get_user_lang(message.from_user.id)

    words = user_text.split()
    if len(words) < 10:
        warning = (
            "⚠️ Текст слишком короткий (меньше 10 слов). Пожалуйста, напиши хотя бы 30-40 слов, "
            "чтобы экзаменатор мог оценить раскрытие всех 3 пунктов, грамматику и оформление письма!"
            if lang == "ru"
            else
            "⚠️ The letter is too short (fewer than 10 words). Please write at least 30-40 words "
            "so the telc rubric can assess task completion, grammar, and layout!"
        )
        await message.answer(warning)
        return

    status_msg = (
        "⏳ *Письмо принято!* Проверяем раскрытие 3 пунктов, грамматику и оформление по 45-балльной шкале telc..."
        if lang == "ru"
        else
        "⏳ *Letter received!* Evaluating all 3 Leitpunkte, grammar, and layout on the 45-point telc rubric..."
    )
    status_notice = await message.answer(status_msg, parse_mode="Markdown")

    schreiben_res = await evaluate_telc_schreiben_module(user_text, native_lang=lang)
    await state.update_data(telc_schreiben_res=schreiben_res, telc_user_schreiben_text=user_text)

    try:
        await status_notice.delete()
    except Exception:
        pass

    # Переход к Mündliche Prüfung: Sprechen
    await state.set_state(DiagnosticState.telc_sprechen_part1)
    await render_telc_sprechen_screen(message, part_num=1, lang=lang)


# ----------------- TELC БЛОК 5: MÜNDLICHE PRÜFUNG (75 баллов) -----------------

async def render_telc_sprechen_screen(message: Message, part_num: int, lang: str):
    """Отображение заданий устной части telc (3 части)"""
    part_key = f"part{part_num}"
    part_task = TELC_B1_SPRECHEN_TASKS[part_key]

    if lang == "ru":
        text = (
            f"🗣️ *telc B1: Mündliche Prüfung (Говорение)* • Часть {part_num} из 3\n\n"
            f"📌 *{part_task['title']}* ({part_task['points']} баллов)\n\n"
            f"🇩🇪 *{part_task['prompt_de']}*\n\n"
            f"⏱️ *Формат ответа:* {part_task['target']}\n\n"
            f"👉 *Запиши голосовое сообщение со своим ответом (или напечатай текст):*"
        )
    else:
        text = (
            f"🗣️ *telc B1: Mündliche Prüfung (Speaking)* • Part {part_num} of 3\n\n"
            f"📌 *{part_task['title']}* ({part_task['points']} pts)\n\n"
            f"🇩🇪 *{part_task['prompt_de']}*\n\n"
            f"⏱️ *Format:* {part_task['target']}\n\n"
            f"👉 *Record a voice message with your response (or submit text):*"
        )

    kb = get_telc_cancel_keyboard(lang=lang)
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

async def process_telc_sprechen_input(message: Message, state: FSMContext, part_num: int):
    """Обработка голосового или текстового ответа в устной части telc"""
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)
    transcribed_text = ""

    if message.voice:
        try:
            file_info = await message.bot.get_file(message.voice.file_id)
            voice_stream = io.BytesIO()
            await message.bot.download_file(file_info.file_path, destination=voice_stream)
            audio_bytes = voice_stream.getvalue()
            transcribed_text = await transcribe_voice(audio_bytes, mime_type="audio/ogg")
        except Exception as e:
            logger.error(f"Ошибка транскрибации голосового в telc Sprechen: {e}")

        if not transcribed_text:
            err_msg = (
                "🪶 Не удалось разобрать запись. Пожалуйста, надиктуй еще раз погромче или напиши текстом!"
                if lang == "ru"
                else "🪶 Could not transcribe audio clearly. Please record again or submit text!"
            )
            await message.answer(err_msg)
            return
    elif message.text:
        transcribed_text = message.text.strip()
    else:
        await message.answer("Пожалуйста, отправь голосовое сообщение или текст!" if lang == "ru" else "Please send a voice note or text!")
        return

    data = await state.get_data()
    sprechen_parts = data.get("telc_sprechen_parts", {})
    sprechen_parts[f"part{part_num}"] = transcribed_text
    await state.update_data(telc_sprechen_parts=sprechen_parts)

    if part_num == 1:
        await state.set_state(DiagnosticState.telc_sprechen_part2)
        await render_telc_sprechen_screen(message, part_num=2, lang=lang)
    elif part_num == 2:
        await state.set_state(DiagnosticState.telc_sprechen_part3)
        await render_telc_sprechen_screen(message, part_num=3, lang=lang)
    else:
        # Все 3 части сданы, переходим к финализации
        await state.set_state(DiagnosticState.telc_evaluating)
        await finalize_telc_readiness_test(message, state, lang=lang)

@router.message(DiagnosticState.telc_sprechen_part1, F.voice | F.text)
async def handle_telc_sprechen_part1(message: Message, state: FSMContext):
    await process_telc_sprechen_input(message, state, part_num=1)

@router.message(DiagnosticState.telc_sprechen_part2, F.voice | F.text)
async def handle_telc_sprechen_part2(message: Message, state: FSMContext):
    await process_telc_sprechen_input(message, state, part_num=2)

@router.message(DiagnosticState.telc_sprechen_part3, F.voice | F.text)
async def handle_telc_sprechen_part3(message: Message, state: FSMContext):
    await process_telc_sprechen_input(message, state, part_num=3)


# ----------------- ИТОГОВАЯ ФИНАЛИЗАЦИЯ TELC B1 -----------------

async def finalize_telc_readiness_test(message: Message, state: FSMContext, lang: str):
    """Итоговая оценка telc B1 по официальной 300-балльной системе и сохранение в БД"""
    user_id = message.from_user.id
    data = await state.get_data()

    status_wait = (
        "⏳ *Идет расчет готовности к экзамену telc Deutsch B1...*\n\n"
        "Оцениваем устную часть по критериям telc (выражение мыслей, решение задач, грамматика, произношение)..."
        if lang == "ru"
        else
        "⏳ *Computing official telc Deutsch B1 Readiness assessment...*\n\n"
        "AI is evaluating oral performance on official telc criteria (expression, tasks, grammar, pronunciation)..."
    )
    status_msg = await message.answer(status_wait, parse_mode="Markdown")

    lesen_answers = data.get("telc_lesen_answers", [])
    sb_answers = data.get("telc_sb_answers", [])
    hoe_answers = data.get("telc_hoe_answers", [])
    schreiben_res = data.get("telc_schreiben_res", {})
    sprechen_parts = data.get("telc_sprechen_parts", {})

    sprechen_res = await evaluate_telc_sprechen_module(sprechen_parts, native_lang=lang)

    score_lesen, lesen_errs = score_telc_lesen_module(lesen_answers)
    score_sb, sb_errs = score_telc_sprachbausteine_module(sb_answers)
    score_hoe, hoe_errs = score_telc_hoeren_module(hoe_answers)
    score_schreiben = int(schreiben_res.get("score", 25))
    score_sprechen = int(sprechen_res.get("score", 45))

    status, schriftlich_score, muendlich_score, total_points, grade_label, weakest = calculate_telc_readiness_overall(
        lesen_score=score_lesen,
        sprachbausteine_score=score_sb,
        hoeren_score=score_hoe,
        schreiben_score=score_schreiben,
        sprechen_score=score_sprechen
    )

    overall_100 = round((total_points / 300.0) * 100)

    if total_points >= 210 and schriftlich_score >= 135 and muendlich_score >= 45:
        cefr_estimate = "B1"
    elif total_points >= 180 and (schriftlich_score >= 135 or muendlich_score >= 45):
        cefr_estimate = "B1"
    elif total_points >= 120:
        cefr_estimate = "A2"
    else:
        cefr_estimate = "A1"

    all_weak_points: List[Dict[str, Any]] = []
    all_weak_points.extend(lesen_errs)
    all_weak_points.extend(sb_errs)
    all_weak_points.extend(hoe_errs)
    all_weak_points.extend(schreiben_res.get("weak_points", []))
    all_weak_points.extend(sprechen_res.get("weak_points", []))

    all_strengths: List[str] = []
    str_key = "strengths_ru" if lang == "ru" else "strengths_en"
    all_strengths.extend(schreiben_res.get(str_key, []))
    all_strengths.extend(sprechen_res.get(str_key, []))

    scores = {
        "lesen": score_lesen,
        "sprachbausteine": score_sb,
        "hoeren": score_hoe,
        "schreiben": score_schreiben,
        "sprechen": score_sprechen,
        "schriftlich_total": schriftlich_score,
        "muendlich_total": muendlich_score,
        "telc_total": total_points
    }

    raw_rubric = {
        "writing": schreiben_res.get("criteria", {}),
        "speaking": sprechen_res.get("criteria", {}),
        "telc_grade": grade_label,
        "schriftlich_score": schriftlich_score,
        "muendlich_score": muendlich_score,
        "total_points": total_points,
        "rubric_writing_version": RUBRIC_TELC_WRITING_VERSION,
        "rubric_speaking_version": RUBRIC_TELC_SPEAKING_VERSION
    }

    pct_scores = {
        "lesen": round((score_lesen / 75.0) * 100),
        "sprachbausteine": round((score_sb / 30.0) * 100),
        "hoeren": round((score_hoe / 75.0) * 100),
        "schreiben": round((score_schreiben / 45.0) * 100),
        "sprechen": round((score_sprechen / 75.0) * 100)
    }
    actions = build_recommendations_and_actions(all_weak_points, pct_scores, native_lang=lang)

    await db.save_diagnostic_result(
        user_id=user_id,
        exam_type="telc_b1",
        exam_version=TELC_B1_VERSION,
        diagnostic_type="readiness",
        cefr_estimate=cefr_estimate,
        readiness_status=status,
        overall_diagnostic_score=overall_100,
        lesen_score=score_lesen,
        hoeren_score=score_hoe,
        schreiben_score=score_schreiben,
        sprechen_score=score_sprechen,
        sprachbausteine_score=score_sb,
        raw_rubric_scores=raw_rubric,
        module_results=scores,
        weak_points=all_weak_points,
        strengths=all_strengths,
        recommendations=actions,
        speaking_profile=sprechen_res.get("speaking_profile", {}),
        writing_profile=schreiben_res.get("writing_profile", {})
    )

    await state.clear()

    schriftlich_pass = schriftlich_score >= 135
    muendlich_pass = muendlich_score >= 45
    w_crit = schreiben_res.get("criteria", {})
    s_crit = sprechen_res.get("criteria", {})

    status_titles_ru = {
        "STRONG": "🟢 Полная готовность к telc B1 (Отличный результат)",
        "LIKELY_READY": "🟢 Высокие шансы сдать telc B1 (Bestanden)",
        "NEAR_PASS": "🟡 Частичная сдача (одна из частей требует доработки)",
        "NOT_READY": "🔴 Ниже проходного балла (требуется подготовка)"
    }
    status_titles_en = {
        "STRONG": "🟢 telc B1 Ready (Strong Performance)",
        "LIKELY_READY": "🟢 Likely to Pass telc B1",
        "NEAR_PASS": "🟡 Partial Pass (One section needs targeted work)",
        "NOT_READY": "🔴 Below Pass Threshold (Preparation Needed)"
    }
    status_title = status_titles_ru.get(status, status) if lang == "ru" else status_titles_en.get(status, status)

    if lang == "ru":
        report_text = (
            f"🏛️ *Итоговый отчет: telc Deutsch B1 Readiness Test*\n\n"
            f"📌 *Статус:* {status_title}\n"
            f"🏆 *Официальная оценка telc:* {grade_label}\n"
            f"📊 *Сумма баллов:* {total_points}/300 (индекс: {overall_100}/100)\n\n"
            f"📝 *1. Schriftliche Prüfung:* {schriftlich_score}/225 {'✅ Сдано' if schriftlich_pass else '❌ Ниже порога 135'}\n"
            f"• 📖 Leseverstehen: {score_lesen}/75\n"
            f"• 🧩 Sprachbausteine: {score_sb}/30\n"
            f"• 🎧 Hörverstehen: {score_hoe}/75\n"
            f"• ✍️ Brief: {score_schreiben}/45\n"
            f"  └ Пункты: {w_crit.get('leitpunkte', 0)}/15 • Грамматика: {w_crit.get('korrektheit', 0)}/15 • Структура: {w_crit.get('gestaltung', 0)}/15\n\n"
            f"🗣️ *2. Mündliche Prüfung:* {muendlich_score}/75 {'✅ Сдано' if muendlich_pass else '❌ Ниже порога 45'}\n"
            f"• Sprechen: {score_sprechen}/75\n"
            f"  └ Выражение мыслей: {s_crit.get('ausdruck', 0)}/15 • Задачи: {s_crit.get('aufgabenbewaeltigung', 0)}/20 • Грамматика: {s_crit.get('formale_richtigkeit', 0)}/20 • Произношение: {s_crit.get('aussprache', 0)}/20\n\n"
        )
        if schriftlich_pass and muendlich_pass:
            report_text += "🎉 *Отличная работа!* Обе части (письменная и устная) успешно преодолели порог 60%!\n\n"
        elif schriftlich_pass and not muendlich_pass:
            report_text += "⚠️ *По правилам telc:* письменная часть сдана, но устную часть необходимо пересдать (минимум 45 баллов).\n\n"
        elif muendlich_pass and not schriftlich_pass:
            report_text += "⚠️ *По правилам telc:* устная часть сдана, но письменную часть необходимо подтянуть (минимум 135 баллов).\n\n"
        else:
            report_text += "⚠️ Обе части пока ниже минимального порога сдачи. Требуется комплексная подготовка!\n\n"

        if all_weak_points:
            report_text += "🔍 *Главные точки роста:*\n"
            for wp in all_weak_points[:3]:
                exp = wp.get("explanation_ru") or wp.get("topic") or ""
                report_text += f"• {exp}\n"
            report_text += "\n"

        report_text += (
            "ℹ️ _Это диагностика Stork AI по официальному регламенту telc Deutsch B1 (300 баллов). "
            "Результат не является официальным сертификатом telc gGmbH._\n\n"
            "👉 *Твой план тренировок:* выбери кнопку ниже, чтобы подтянуть слабые места 👇"
        )
    else:
        report_text = (
            f"🏛️ *Official Report: telc Deutsch B1 Readiness Test*\n\n"
            f"📌 *Status:* {status_title}\n"
            f"🏆 *Official telc Grade:* {grade_label}\n"
            f"📊 *Total Score:* {total_points}/300 (Diagnostic Index: {overall_100}/100)\n\n"
            f"📝 *1. Schriftliche Prüfung:* {schriftlich_score}/225 {'✅ Passed' if schriftlich_pass else '❌ Below 135 threshold'}\n"
            f"• 📖 Leseverstehen: {score_lesen}/75\n"
            f"• 🧩 Sprachbausteine: {score_sb}/30\n"
            f"• 🎧 Hörverstehen: {score_hoe}/75\n"
            f"• ✍️ Brief: {score_schreiben}/45\n"
            f"  └ Content: {w_crit.get('leitpunkte', 0)}/15 • Grammar: {w_crit.get('korrektheit', 0)}/15 • Style: {w_crit.get('gestaltung', 0)}/15\n\n"
            f"🗣️ *2. Mündliche Prüfung:* {muendlich_score}/75 {'✅ Passed' if muendlich_pass else '❌ Below 45 threshold'}\n"
            f"• Sprechen: {score_sprechen}/75\n"
            f"  └ Expression: {s_crit.get('ausdruck', 0)}/15 • Task: {s_crit.get('aufgabenbewaeltigung', 0)}/20 • Grammar: {s_crit.get('formale_richtigkeit', 0)}/20 • Pronunciation: {s_crit.get('aussprache', 0)}/20\n\n"
        )
        if schriftlich_pass and muendlich_pass:
            report_text += "🎉 *Congratulations!* Both written and oral sections exceeded the 60% passing mark!\n\n"
        elif schriftlich_pass and not muendlich_pass:
            report_text += "⚠️ *Under telc regulations:* written exam passed, oral exam needs a re-sit (>= 45 pts required).\n\n"
        elif muendlich_pass and not schriftlich_pass:
            report_text += "⚠️ *Under telc regulations:* oral exam passed, written exam needs a re-sit (>= 135 pts required).\n\n"
        else:
            report_text += "⚠️ Both sections are currently below the passing score. Comprehensive preparation needed!\n\n"

        if all_weak_points:
            report_text += "🔍 *Target Areas for Improvement:*\n"
            for wp in all_weak_points[:3]:
                exp = wp.get("explanation_en") or wp.get("topic") or ""
                report_text += f"• {exp}\n"
            report_text += "\n"

        report_text += (
            "ℹ️ _This is an internal Stork AI diagnostic modeled on the official telc Deutsch B1 300-point framework. "
            "It is not an official certificate from telc gGmbH._\n\n"
            "👉 *Your Action Plan:* choose targeted exercises below 👇"
        )

    kb = get_diagnostic_recommendations_keyboard(actions, lang=lang, exam_type="telc_b1")

    try:
        await status_msg.edit_text(report_text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await message.answer(report_text, reply_markup=kb, parse_mode="Markdown")
