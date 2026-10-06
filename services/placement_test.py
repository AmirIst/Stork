"""
Сервис комплексного теста на определение уровня немецкого языка (A1-B1).
Включает 12 верифицированных заданий по шкале CEFR (Goethe / Telc),
охватывающих грамматику, артикли, падежи, предлоги, времена и порядок слов.
"""
from typing import List, Dict, Any, Tuple

PLACEMENT_QUESTIONS: List[Dict[str, Any]] = [
    # === УРОВЕНЬ A1 (Вопросы 1 - 4) ===
    {
        "id": 1,
        "level": "A1",
        "topic": {
            "ru": "Спряжение глаголов в настоящем времени (Präsens)",
            "en": "Present tense verb conjugation (Präsens)"
        },
        "question": "Wie ___ du mit Vornamen?",
        "options": ["heißt", "heiße", "heißen", "heißt du"],
        "correct_index": 0,
        "explanation": {
            "ru": "С местоимением du глагол heißen принимает окончание -t: du heißt.",
            "en": "With the personal pronoun 'du', the verb 'heißen' takes ending -t: du heißt."
        }
    },
    {
        "id": 2,
        "level": "A1",
        "topic": {
            "ru": "Винительный падеж (Akkusativ) и артикли",
            "en": "Accusative case (Akkusativ) & articles"
        },
        "question": "Ich kaufe ___ Apfel im Supermarkt.",
        "options": ["einen", "ein", "eine", "einem"],
        "correct_index": 0,
        "explanation": {
            "ru": "Мужской род (der Apfel) в Akkusativ меняет неопределенный артикль на einen.",
            "en": "Masculine noun (der Apfel) in Accusative changes article to 'einen'."
        }
    },
    {
        "id": 3,
        "level": "A1",
        "topic": {
            "ru": "Отрицание существительных (kein vs nicht)",
            "en": "Negation (kein vs nicht)"
        },
        "question": "Das ist ___ Problem, wir haben genug Zeit!",
        "options": ["kein", "nicht", "keine", "keinen"],
        "correct_index": 0,
        "explanation": {
            "ru": "Существительное среднего рода das Problem отрицается словом kein: kein Problem.",
            "en": "Neuter noun 'das Problem' is negated using 'kein': kein Problem."
        }
    },
    {
        "id": 4,
        "level": "A1",
        "topic": {
            "ru": "Предлоги времени (Präpositionen der Zeit)",
            "en": "Prepositions of time"
        },
        "question": "Der Deutschkurs beginnt ___ 18:30 Uhr.",
        "options": ["um", "am", "im", "an"],
        "correct_index": 0,
        "explanation": {
            "ru": "Точное время в часах всегда используется с предлогом um: um 18:30 Uhr.",
            "en": "Clock times are always preceded by the preposition 'um': um 18:30 Uhr."
        }
    },

    # === УРОВЕНЬ A2 (Вопросы 5 - 8) ===
    {
        "id": 5,
        "level": "A2",
        "topic": {
            "ru": "Прошедшее время Perfekt со вспомогательным sein",
            "en": "Perfekt tense with auxiliary 'sein'"
        },
        "question": "Gestern ___ meine Schwester nach Berlin gefahren.",
        "options": ["ist", "hat", "wird", "war"],
        "correct_index": 0,
        "explanation": {
            "ru": "Глаголы движения с перемещением в пространстве (fahren) образуют Perfekt с sein: ist gefahren.",
            "en": "Verbs of motion with change of location (fahren) form Perfekt with 'sein': ist gefahren."
        }
    },
    {
        "id": 6,
        "level": "A2",
        "topic": {
            "ru": "Предлоги двойного управления (Dativ / Wo?)",
            "en": "Two-way prepositions (Dative / Where?)"
        },
        "question": "Das Buch liegt auf ___ Tisch.",
        "options": ["dem", "den", "das", "die"],
        "correct_index": 0,
        "explanation": {
            "ru": "Вопрос 'Где?' (Wo?) требует дательного падежа (Dativ). Der Tisch в Dativ -> dem Tisch.",
            "en": "Location question 'Where?' (Wo?) requires Dative. 'Der Tisch' in Dative becomes 'dem Tisch'."
        }
    },
    {
        "id": 7,
        "level": "A2",
        "topic": {
            "ru": "Модальные глаголы в прошедшем времени (Präteritum)",
            "en": "Modal verbs in simple past (Präteritum)"
        },
        "question": "Ich war gestern krank und ___ nicht zur Arbeit gehen.",
        "options": ["konnte", "kann", "gekonnt", "muss"],
        "correct_index": 0,
        "explanation": {
            "ru": "В прошедшем времени модальный глагол können имеет форму konnte (я не мог).",
            "en": "In the past tense, modal verb 'können' takes form 'konnte' (I could not)."
        }
    },
    {
        "id": 8,
        "level": "A2",
        "topic": {
            "ru": "Порядок слов в придаточных предложениях (weil)",
            "en": "Subordinate clause word order (weil)"
        },
        "question": "Ich lerne Deutsch, weil ich in Deutschland studieren ___.",
        "options": ["möchte", "möchten", "möchte ich", "will ich"],
        "correct_index": 0,
        "explanation": {
            "ru": "Союз weil отправляет спрягаемый глагол на самое последнее место в предложении.",
            "en": "Conjunction 'weil' sends the conjugated verb to the very end of the clause."
        }
    },

    # === УРОВЕНЬ B1 (Вопросы 9 - 12) ===
    {
        "id": 9,
        "level": "B1",
        "topic": {
            "ru": "Временные союзы в прошлом (als vs wenn)",
            "en": "Temporal conjunctions in the past (als vs wenn)"
        },
        "question": "___ ich ein Kind war, habe ich viel draußen gespielt.",
        "options": ["Als", "Wenn", "Wann", "Weil"],
        "correct_index": 0,
        "explanation": {
            "ru": "Для однократного периода или события в прошлом используется союз Als (когда).",
            "en": "For a single event or continuous period in the past, 'Als' (when) is required."
        }
    },
    {
        "id": 10,
        "level": "B1",
        "topic": {
            "ru": "Пассивный залог процесса (Vorgangspassiv)",
            "en": "Passive voice (Vorgangspassiv)"
        },
        "question": "Das neue Rathaus ___ gerade gebaut.",
        "options": ["wird", "ist", "hat", "wurde"],
        "correct_index": 0,
        "explanation": {
            "ru": "Настоящее время пассивного залога строится по схеме werden + Partizip II: wird gebaut.",
            "en": "Present passive is formed using 'werden' + Partizip II: wird gebaut."
        }
    },
    {
        "id": 11,
        "level": "B1",
        "topic": {
            "ru": "Сослагательное наклонение (Konjunktiv II)",
            "en": "Subjunctive mood (Konjunktiv II)"
        },
        "question": "Wenn ich mehr Geld ___, würde ich eine Weltreise machen.",
        "options": ["hätte", "habe", "hatte", "wäre"],
        "correct_index": 0,
        "explanation": {
            "ru": "Нереальное условие (если бы у меня было) выражается формой Konjunktiv II: hätte.",
            "en": "Hypothetical condition (if I had) requires Konjunktiv II: hätte."
        }
    },
    {
        "id": 12,
        "level": "B1",
        "topic": {
            "ru": "Относительные придаточные предложения с дательным падежом",
            "en": "Relative clauses with Dative case"
        },
        "question": "Das ist der Nachbar, ___ ich gestern beim Umzug geholfen habe.",
        "options": ["dem", "den", "der", "des"],
        "correct_index": 0,
        "explanation": {
            "ru": "Глагол helfen требует Dativ (helfen + Dativ). Мужской род в Dativ: dem.",
            "en": "Verb 'helfen' governs Dative. Masculine relative pronoun in Dative is 'dem'."
        }
    }
]

def evaluate_placement_test(user_answers: List[int]) -> Tuple[str, int, Dict[str, Tuple[int, int]]]:
    """
    Рассчитывает уровень CEFR по ответам пользователя:
    Возвращает:
    - result_level: 'A1', 'A2' или 'B1'
    - total_score: общее число правильных ответов (из 12)
    - level_breakdown: статистика по подуровням { 'A1': (correct, total), ... }
    """
    total_score = 0
    breakdown = {
        "A1": [0, 0],
        "A2": [0, 0],
        "B1": [0, 0]
    }

    for idx, q in enumerate(PLACEMENT_QUESTIONS):
        lvl = q["level"]
        breakdown[lvl][1] += 1
        if idx < len(user_answers) and user_answers[idx] == q["correct_index"]:
            total_score += 1
            breakdown[lvl][0] += 1

    level_dict = {
        k: (v[0], v[1]) for k, v in breakdown.items()
    }

    # Градация уровней CEFR
    if total_score >= 9:
        result_level = "B1"
    elif total_score >= 5:
        result_level = "A2"
    else:
        result_level = "A1"

    return result_level, total_score, level_dict

def get_level_description(level: str, lang: str = "ru") -> Dict[str, str]:
    """Описание подтвержденного уровня и персональная рекомендация"""
    if lang == "ru":
        data = {
            "A1": {
                "name": "A1 (Начальный)",
                "title": "🌱 Уровень A1: Ты закладываешь прочный фундамент!",
                "text": "Ты понимаешь базовые фразы, артикли и простое настоящее время. Сейчас идеальный момент расширять словарный запас и довести артикли до автоматизма.",
                "tip": "Тренируй существительные темы «Еда» и «Дом», а также тренажер артиклей der/die/das."
            },
            "A2": {
                "name": "A2 (Элементарный / Разговорный)",
                "title": "🌿 Уровень A2: Уверенная базовая речь!",
                "text": "Ты отлично ориентируешься в бытовых темах, понимаешь прошедшее время Perfekt и предлоги Dativ. Твоя следующая цель: освоить сложноподчиненные предложения и модальные глаголы.",
                "tip": "Подключай тренажер экзаменательных писем A2 и регулярный диалог с ИИ-Аистом."
            },
            "B1": {
                "name": "B1 (Средний / Самостоятельное владение)",
                "title": "🌳 Уровень B1: Сильный средний уровень!",
                "text": "Ты уверенно владеешь сложными конструкциями: пассивный залог, Konjunktiv II, относительные местоимения и временные союзы. Ты готов к сдаче официальных экзаменов Goethe / Telc B1!",
                "tip": "Тренируй расширенные эссе на форумах в тренажере Schreiben B1 и учи специализированные темы."
            }
        }
    else:
        data = {
            "A1": {
                "name": "A1 (Beginner)",
                "title": "🌱 Level A1: Laying a strong foundation!",
                "text": "You understand fundamental phrases, basic articles, and present tense. Now is the perfect time to build vocabulary and master articles.",
                "tip": "Practice words in 'Food' and 'Home' topics, and drill der/die/das in the Article Trainer."
            },
            "A2": {
                "name": "A2 (Elementary)",
                "title": "🌿 Level A2: Confident everyday conversational German!",
                "text": "You navigate everyday situations with ease, understand Perfekt past tense and Dative prepositions. Next goal: master subordinate clauses and modal verbs.",
                "tip": "Try writing assignments in the A2 Exam Simulator and have daily conversations with AI Stork."
            },
            "B1": {
                "name": "B1 (Intermediate)",
                "title": "🌳 Level B1: Independent language mastery!",
                "text": "You confidently handle complex German syntax: passive voice, Konjunktiv II, relative pronouns, and conjunctions. You are well prepared for official Goethe / Telc B1 exams!",
                "tip": "Focus on B1 forum discussions in the Exam Writing Simulator and expand advanced vocabulary."
            }
        }
    return data.get(level, data["A1"])
