"""
Сервис экзаменационного тренажера письма (Schreiben) для Goethe-Zertifikat и Telc.
Генерирует официальные сценарии заданий уровней A1, A2, B1 и проводит детальную оценку
текста ученика по критериям экзаменационной комиссии с образцовым ответом (Musterlösung).
"""
import random
import logging
from typing import Dict, Any, Optional
from services.ai_tutor import execute_gemini_request

logger = logging.getLogger(__name__)

EXAM_TASKS = [
    # === УРОВЕНЬ A1 (30-40 слов) ===
    {
        "id": "a1_party",
        "level": "A1",
        "title": {
            "ru": "Приглашение на день рождения (Einladung)",
            "en": "Birthday Party Invitation (Einladung)"
        },
        "target_words": "30-40",
        "min_words": 25,
        "max_words": 45,
        "situation": {
            "ru": "Вы празднуете свой день рождения в следующую субботу и хотите пригласить вашего друга / подругу Маркуса (Markus).",
            "en": "You are celebrating your birthday next Saturday and want to invite your friend Markus."
        },
        "points": {
            "ru": [
                "Пригласите Маркуса на праздник (день и время начала).",
                "Напишите, что вы приготовите еду, но попросите его принести напитки.",
                "Спросите, сможет ли он прийти, и попросите ответить до четверга."
            ],
            "en": [
                "Invite Markus to your party (day and starting time).",
                "Mention that you will cook food, but ask him to bring drinks.",
                "Ask if he can come and request an answer by Thursday."
            ]
        },
        "starter_hint": {
            "ru": "Обращение: *Lieber Markus,* ... Окончание: *Viele Grüße, [Твое имя]*",
            "en": "Salutation: *Lieber Markus,* ... Closing: *Viele Grüße, [Your name]*"
        }
    },
    {
        "id": "a1_hotel",
        "level": "A1",
        "title": {
            "ru": "Бронирование номера в отеле (Hotelreservierung)",
            "en": "Hotel Room Reservation (Hotelreservierung)"
        },
        "target_words": "30-40",
        "min_words": 25,
        "max_words": 45,
        "situation": {
            "ru": "Вы едете в Берлин и хотите забронировать номер в отеле 'Sonne'.",
            "en": "You are traveling to Berlin and want to book a room at Hotel Sonne."
        },
        "points": {
            "ru": [
                "Укажите даты проживания (со 2 по 4 ноября) и тип номера (одноместный).",
                "Сообщите, что вы приедете поздно вечером (около 22:00).",
                "Спросите, включен ли завтрак в стоимость."
            ],
            "en": [
                "State dates of stay (Nov 2 - Nov 4) and room type (single room).",
                "Inform them that you will arrive late in the evening (around 10 pm).",
                "Ask if breakfast is included in the price."
            ]
        },
        "starter_hint": {
            "ru": "Обращение: *Sehr geehrte Damen und Herren,* ... Окончание: *Mit freundlichen Grüßen, [Твое имя]*",
            "en": "Salutation: *Sehr geehrte Damen und Herren,* ... Closing: *Mit freundlichen Grüßen, [Your name]*"
        }
    },
    # === УРОВЕНЬ A2 (40-50 слов) ===
    {
        "id": "a2_repair",
        "level": "A2",
        "title": {
            "ru": "Сломалось отопление (Heizung kaputt)",
            "en": "Broken Heating Complaint (Heizung kaputt)"
        },
        "target_words": "40-50",
        "min_words": 35,
        "max_words": 60,
        "situation": {
            "ru": "В вашей арендованной квартире не работает отопление, а на улице зима. Напишите вашему арендодателю господину Веберу (Herr Weber).",
            "en": "The heating in your rented apartment is broken during winter. Write an email to your landlord, Herr Weber."
        },
        "points": {
            "ru": [
                "Опишите проблему (отопление не работает со вчерашнего дня, в квартире холодно).",
                "Попросите срочно прислать мастера (Handwerker).",
                "Укажите, в какое время вы бываете дома (после 17:00).",
                "Оставьте номер телефона для быстрой связи."
            ],
            "en": [
                "Describe the issue (heating broken since yesterday, very cold).",
                "Ask him to send a repairman urgently.",
                "Specify when you are at home (after 5 pm).",
                "Provide your phone number for quick contact."
            ]
        },
        "starter_hint": {
            "ru": "Обращение: *Sehr geehrter Herr Weber,* ... Окончание: *Mit freundlichen Grüßen, [Твое имя]*",
            "en": "Salutation: *Sehr geehrter Herr Weber,* ... Closing: *Mit freundlichen Grüßen, [Your name]*"
        }
    },
    {
        "id": "a2_doctor",
        "level": "A2",
        "title": {
            "ru": "Перенос приема у врача (Terminabsage)",
            "en": "Rescheduling Doctor Appointment (Terminabsage)"
        },
        "target_words": "40-50",
        "min_words": 35,
        "max_words": 60,
        "situation": {
            "ru": "У вас назначен прием у врача на завтра, но вы вынуждены срочно задержаться на работе.",
            "en": "You have a doctor's appointment tomorrow, but you must work overtime urgently."
        },
        "points": {
            "ru": [
                "Извинитесь и сообщите, что не можете прийти завтра.",
                "Назовите причину (срочная работа / совещание).",
                "Попросите перенести запись на следующую неделю.",
                "Спросите, есть ли свободное время во вторник после обеда."
            ],
            "en": [
                "Apologize and state you cannot make it tomorrow.",
                "Give your reason (urgent work / meeting).",
                "Ask to reschedule the appointment for next week.",
                "Inquire if there is free time on Tuesday afternoon."
            ]
        },
        "starter_hint": {
            "ru": "Обращение: *Sehr geehrte Damen und Herren,* или *Liebes Praxis-Team,* ... Окончание: *Mit freundlichen Grüßen, [Твое имя]*",
            "en": "Salutation: *Sehr geehrte Damen und Herren,* or *Liebes Praxis-Team,* ... Closing: *Mit freundlichen Grüßen, [Your name]*"
        }
    },
    # === УРОВЕНЬ B1 (80-100 слов) ===
    {
        "id": "b1_homeoffice",
        "level": "B1",
        "title": {
            "ru": "Мнение на форуме: Удаленная работа (Homeoffice)",
            "en": "Forum Post: Working from Home (Homeoffice)"
        },
        "target_words": "80-100",
        "min_words": 70,
        "max_words": 120,
        "situation": {
            "ru": "В интернет-журнале идет дискуссия на тему: 'Homeoffice: мечта или стресс?'. Напишите ваш пост в ветку обсуждения.",
            "en": "An online magazine is hosting a discussion: 'Working from home: Dream or stress?'. Write your contribution to the forum."
        },
        "points": {
            "ru": [
                "Выразите свое общее отношение к удаленной работе.",
                "Назовите преимущества (экономия времени на дорогу, гибкость).",
                "Назовите недостатки (нехватка живого общения с коллегами, сложно разделить работу и отдых).",
                "Опишите личный опыт или ситуацию в вашей стране."
            ],
            "en": [
                "State your general view on remote work.",
                "Name advantages (no commute time, flexibility).",
                "Name disadvantages (lack of personal contact, boundary between work and private life).",
                "Share personal experience or situation in your home country."
            ]
        },
        "starter_hint": {
            "ru": "Начало: *Hallo zusammen, ich möchte auch etwas zum Thema Homeoffice schreiben...*",
            "en": "Opening: *Hallo zusammen, ich möchte auch etwas zum Thema Homeoffice schreiben...*"
        }
    },
    {
        "id": "a1_course_excuse",
        "level": "A1",
        "title": {
            "ru": "Пропуск занятия на языковых курсах (Entschuldigung)",
            "en": "Missing German Class Note (Entschuldigung)"
        },
        "target_words": "30-40",
        "min_words": 25,
        "max_words": 45,
        "situation": {
            "ru": "Вы заболели и не можете прийти на урок немецкого языка сегодня вечером. Напишите преподавателю господину Мюллеру (Herr Müller).",
            "en": "You are sick and cannot attend your German class this evening. Write a note to your teacher, Herr Müller."
        },
        "points": {
            "ru": [
                "Сообщите, почему вы не можете прийти на занятие (простуда / грипп).",
                "Спросите про домашнее задание на следующий урок.",
                "Напишите, когда вы снова будете на занятиях (в следующий понедельник)."
            ],
            "en": [
                "Explain why you cannot come to class (flu / cold).",
                "Ask about homework for the next lesson.",
                "Mention when you will be back in class (next Monday)."
            ]
        },
        "starter_hint": {
            "ru": "Обращение: *Sehr geehrter Herr Müller,* ... Окончание: *Mit freundlichen Grüßen, [Твое имя]*",
            "en": "Salutation: *Sehr geehrter Herr Müller,* ... Closing: *Mit freundlichen Grüßen, [Your name]*"
        }
    },
    {
        "id": "a2_invitation_decline",
        "level": "A2",
        "title": {
            "ru": "Вежливый отказ от приглашения (Absage)",
            "en": "Polite Dinner Invitation Decline (Absage)"
        },
        "target_words": "40-50",
        "min_words": 35,
        "max_words": 60,
        "situation": {
            "ru": "Ваша подруга Лиза (Lisa) пригласила вас в субботу на новоселье, но вы не можете прийти.",
            "en": "Your friend Lisa invited you to her housewarming party this Saturday, but you cannot attend."
        },
        "points": {
            "ru": [
                "Поблагодарите за приглашение и поздравьте с новой квартирой.",
                "Объясните, почему не можете прийти в субботу (семейный праздник / поездка к родителям).",
                "Предложите встретиться на следующей неделе за чашкой кофе."
            ],
            "en": [
                "Thank her for the invitation and congratulate on the new flat.",
                "Explain why you cannot come on Saturday (family event / visiting parents).",
                "Suggest meeting next week for coffee instead."
            ]
        },
        "starter_hint": {
            "ru": "Обращение: *Liebe Lisa,* ... Окончание: *Liebe Grüße, [Твое имя]*",
            "en": "Salutation: *Liebe Lisa,* ... Closing: *Liebe Grüße, [Your name]*"
        }
    },
    {
        "id": "b1_travel_complaint",
        "level": "B1",
        "title": {
            "ru": "Жалоба в турфирму на отпуск (Beschwerde)",
            "en": "Vacation Complaint Letter to Agency (Beschwerde)"
        },
        "target_words": "80-100",
        "min_words": 70,
        "max_words": 120,
        "situation": {
            "ru": "Вы провели отпуск в отеле на море, организованный турагентством 'ReiseGlück'. Реальные условия в отеле оказались значительно хуже описания в каталоге.",
            "en": "You spent your summer holiday at a seaside hotel arranged by 'ReiseGlück' travel agency. The conditions were far worse than promised."
        },
        "points": {
            "ru": [
                "Укажите номер бронирования и цель вашего письма (жалоба).",
                "Опишите конкретные проблемы (шум от стройки рядом, не работал кондиционер, грязный пляж).",
                "Напомните, что на месте администратор отеля не помог решить проблему.",
                "Потребуйте соразмерной денежной компенсации или возврата 30% стоимости тура."
            ],
            "en": [
                "State your booking number and purpose of writing (formal complaint).",
                "Describe specific problems (construction noise, broken AC, unclean beach).",
                "Note that hotel reception on site refused to help.",
                "Demand reasonable monetary compensation or a 30% refund."
            ]
        },
        "starter_hint": {
            "ru": "Обращение: *Sehr geehrte Damen und Herren,* ... Окончание: *Mit freundlichen Grüßen, [Твое имя]*",
            "en": "Salutation: *Sehr geehrte Damen und Herren,* ... Closing: *Mit freundlichen Grüßen, [Your name]*"
        }
    }
]

def get_exam_task(task_id: Optional[str] = None, level: Optional[str] = None) -> Dict[str, Any]:
    """Получить экзаменационное задание по ID или случайное заданного уровня"""
    if task_id:
        for t in EXAM_TASKS:
            if t["id"] == task_id:
                return t
    
    candidates = EXAM_TASKS
    if level and level != "ALL":
        filtered = [t for t in EXAM_TASKS if t["level"] == level]
        if filtered:
            candidates = filtered

    return random.choice(candidates)

async def evaluate_student_letter(task: Dict[str, Any], student_text: str, native_lang: str = "ru") -> str:
    """
    Проверка письма ученика сертифицированным ИИ-экзаменатором Goethe/Telc.
    Возвращает структурированный разбор: баллы, ошибки, подсчет слов, образец.
    """
    word_count = len([w for w in student_text.split() if any(c.isalnum() for c in w)])
    lang_key = "ru" if native_lang == "ru" else "en"

    situation_text = task["situation"][lang_key]
    points_list = "\n".join([f"- {p}" for p in task["points"][lang_key]])

    if native_lang == "ru":
        prompt = f"""
Ты: Сертифицированный экзаменатор немецкого языка Goethe-Zertifikat и Telc.
Твоя задача: профессионально, строго, но доброжелательно оценить письменную работу (Schreiben) ученика.

ЗАДАНИЕ ЭКЗАМЕНА (Уровень {task["level"]}):
Ситуация: {situation_text}
Обязательные пункты (Leitpunkte):
{points_list}
Требуемый объем слов: {task["target_words"]} слов.

ТЕКСТ УЧЕНИКА:
\"\"\"
{student_text}
\"\"\"

Фактическое количество слов в тексте ученика: {word_count}.

ТРЕБОВАНИЯ К ОЦЕНКЕ:
Оформи разбор строго на русском языке со следующей структурой:

📊 Оценка экзаменатора: [Балл из 100, например 85/100] • [Статус: Bestanden (Сдано) или Nicht bestanden (Не сдано)]
📏 Объем текста: [Написано {word_count} слов при норме {task["target_words"]}. Краткий комментарий.]

🎯 Выполнение пунктов задания (Inhalt):
[По каждому из пунктов задания напиши кратко: раскрыт ли он полностью, частично или пропущен]

🔍 Разбор ошибок и грамматика:
[Укажи конкретные ошибки в тексте ученика (порядок слов, артикли, падежи, окончания) с исправлением: было -> стало, и кратким понятным правилом]

🌟 Идеальный образец ответа (Musterlösung):
[Напиши идеальный эталонный текст письма на немецком языке уровня {task["level"]}, полностью соответствующий ситуации и всем пунктам, с переводом на русский язык в скобках]

💡 Экзаменационный совет от Stork:
[1 практический совет, который поможет получить максимальный балл на реальном экзамене]

ПРАВИЛА ОФОРМЛЕНИЯ:
- Не используй длинные тире (em-dash), заменяй на дефис или двоеточие.
- Будь поддерживающим и конструктивным.
"""
    else:
        prompt = f"""
You are: A certified Goethe-Zertifikat and Telc German language examiner.
Your task: Professionally, strictly yet encouragingly assess a student's writing assignment (Schreiben).

EXAM TASK (Level {task["level"]}):
Situation: {situation_text}
Mandatory Points (Leitpunkte):
{points_list}
Target Word Count: {task["target_words"]} words.

STUDENT'S SUBMISSION:
\"\"\"
{student_text}
\"\"\"

Actual word count in student's text: {word_count}.

ASSESSMENT REQUIREMENTS:
Format the review strictly in English using the following structure:

📊 Examiner Score: [Score out of 100, e.g. 85/100] • [Status: Bestanden (Passed) or Nicht bestanden (Failed)]
📏 Word Count: [Written {word_count} words (target {task["target_words"]}). Brief comment.]

🎯 Content Completion (Inhalt):
[For each mandatory point, write briefly whether it was fully covered, partially covered, or missed]

🔍 Error Analysis & Grammar:
[Highlight specific errors in the student's text (word order, articles, cases, endings) with corrections: was -> becomes, and concise explanations]

🌟 Model Answer (Musterlösung):
[Provide an ideal German model letter suitable for level {task["level"]}, fully meeting the situation and all points, with English translation in parentheses]

💡 Stork Exam Tip:
[1 actionable tip that helps secure top marks in the real exam]

FORMATTING RULES:
- Never use em-dashes (—), replace them with hyphens (-) or colons (:).
- Be supportive and constructive.
"""

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 1000
        }
    }

    result = await execute_gemini_request(payload)
    if result:
        clean_text = result.replace("—", "-").replace("–", "-")
        header = f"🪶 *Экзаменационная оценка Stork ({task['level']}):*" if native_lang == "ru" else f"🪶 *Stork Exam Assessment ({task['level']}):*"
        return f"{header}\n\n{clean_text}"

    if native_lang == "ru":
        return "🪶 Экзаменатор Stork временно недоступен из-за пика нагрузки. Пожалуйста, отправь текст еще раз через несколько секунд!"
    else:
        return "🪶 Stork Exam Examiner is temporarily busy. Please resubmit your text in a few moments!"
