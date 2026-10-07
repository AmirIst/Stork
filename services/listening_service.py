import random
from typing import Dict, Any, List, Optional

LISTENING_TASKS: List[Dict[str, Any]] = [
    # A1 TASKS
    {
        "id": "hv_a1_1",
        "level": "A1",
        "type": "announcement",
        "title": {
            "ru": "Объявление на вокзале (Bahnhof)",
            "en": "Train Station Announcement"
        },
        "audio_text": (
            "Achtung an Gleis 3. Der Intercity nach Berlin Hauptbahnhof, "
            "planmäßige Abfahrt um 14 Uhr 25, fährt heute ausnahmsweise von Gleis 5 ab. "
            "Ich wiederhole: von Gleis 5."
        ),
        "question": {
            "ru": "С какого пути отправляется поезд на Берлин?",
            "en": "From which platform does the train to Berlin depart?"
        },
        "options": {
            "ru": ["С пути 3", "С пути 5", "С пути 14", "С пути 25"],
            "en": ["From platform 3", "From platform 5", "From platform 14", "From platform 25"]
        },
        "correct_index": 1,
        "explanation": {
            "ru": "В объявлении говорится: 'fährt heute ausnahmsweise von Gleis 5 ab' (отправляется сегодня в виде исключения с пути 5).",
            "en": "The announcement states: 'fährt heute ausnahmsweise von Gleis 5 ab' (departs exceptionally from platform 5 today)."
        },
        "transcript_tr": {
            "ru": "Внимание на 3-м пути. Поезд Интерсити до главного вокзала Берлина, отправление по расписанию в 14:25, сегодня в виде исключения отправляется с 5-го пути. Повторяю: с 5-го пути.",
            "en": "Attention on platform 3. The Intercity to Berlin Central Station, scheduled departure at 14:25, exceptionally departs from platform 5 today. I repeat: from platform 5."
        }
    },
    {
        "id": "hv_a1_2",
        "level": "A1",
        "type": "voicemail",
        "title": {
            "ru": "Автоответчик в клинике (Arztpraxis)",
            "en": "Doctor's Practice Voicemail"
        },
        "audio_text": (
            "Guten Tag, hier ist die Praxis von Doktor Weber. "
            "Unsere Praxis ist heute wegen einer Fortbildung geschlossen. "
            "Morgen früh ab 8 Uhr sind wir wieder wie gewohnt für Sie da. "
            "In dringenden Notfällen wenden Sie sich bitte an den ärztlichen Bereitschaftsdienst."
        ),
        "question": {
            "ru": "Когда практика врача снова откроется для пациентов?",
            "en": "When will the doctor's practice reopen for patients?"
        },
        "options": {
            "ru": ["Сегодня после обеда", "Завтра в 8:00 утра", "В следующий понедельник", "Только в экстренных случаях"],
            "en": ["This afternoon", "Tomorrow at 8:00 AM", "Next Monday", "Only for emergency cases"]
        },
        "correct_index": 1,
        "explanation": {
            "ru": "Врач сообщает: 'Morgen früh ab 8 Uhr sind wir wieder wie gewohnt für Sie da' (Завтра утром с 8:00 мы снова работаем как обычно).",
            "en": "The message states: 'Morgen früh ab 8 Uhr sind wir wieder wie gewohnt für Sie da' (Tomorrow morning from 8:00 AM we are open as usual)."
        },
        "transcript_tr": {
            "ru": "Добрый день, это практика доктора Вебера. Сегодня наша практика закрыта из-за повышения квалификации. Завтра утром с 8:00 мы снова работаем для вас в обычном режиме. В экстренных случаях обращайтесь в дежурную службу.",
            "en": "Hello, this is Dr. Weber's practice. Today our practice is closed due to staff training. Tomorrow morning from 8:00 AM we will be back for you as usual. In urgent emergencies please contact the on-call medical service."
        }
    },
    {
        "id": "hv_a1_3",
        "level": "A1",
        "type": "announcement",
        "title": {
            "ru": "Скидка в супермаркете (Supermarkt)",
            "en": "Supermarket Special Offer"
        },
        "audio_text": (
            "Liebe Kundinnen und Kunden. Nutzen Sie unser heutiges Sonderangebot in der Obstabteilung: "
            "Ein Kilo frische Bio-Äpfel für nur einen Euro und neunundvierzig Cent. "
            "Greifen Sie zu, solange der Vorrat reicht!"
        ),
        "question": {
            "ru": "Какой продукт продается сегодня со скидкой?",
            "en": "Which product is offered at a special discount today?"
        },
        "options": {
            "ru": ["Свежие бананы", "Био-яблоки", "Апельсиновый сок", "Свежая клубника"],
            "en": ["Fresh bananas", "Organic apples", "Orange juice", "Fresh strawberries"]
        },
        "correct_index": 1,
        "explanation": {
            "ru": "Диктор объявляет: 'Ein Kilo frische Bio-Äpfel für nur einen Euro...' (Один килограмм свежих био-яблок всего за 1.49).",
            "en": "The announcement highlights: 'Ein Kilo frische Bio-Äpfel' (One kilogram of fresh organic apples)."
        },
        "transcript_tr": {
            "ru": "Уважаемые покупатели. Воспользуйтесь нашим сегодняшним спецпредложением в отделе фруктов: один килограмм свежих био-яблок всего за один евро и сорок девять центов. Покупайте, пока товар есть в наличии!",
            "en": "Dear customers. Take advantage of today's special offer in the fruit department: one kilo of fresh organic apples for only one euro and forty-nine cents. Grab yours while supplies last!"
        }
    },

    # A2 TASKS
    {
        "id": "hv_a2_1",
        "level": "A2",
        "type": "conversation",
        "title": {
            "ru": "Встреча в кино (Verabredung)",
            "en": "Cinema Meeting Arrangement"
        },
        "audio_text": (
            "Hallo Jan, hier ist Laura. Ich rufe wegen unseres Kinobesuchs heute Abend an. "
            "Der Film beginnt doch schon um 19 Uhr 30 und nicht erst um acht. "
            "Lass uns also am besten um 19 Uhr vor dem Kino treffen, damit wir noch Popcorn kaufen können. "
            "Ruf mich kurz zurück!"
        ),
        "question": {
            "ru": "Во сколько Лаура предлагает встретиться перед кинотеатром?",
            "en": "At what time does Laura suggest meeting in front of the cinema?"
        },
        "options": {
            "ru": ["В 19:00", "В 19:30", "В 20:00", "В 18:30"],
            "en": ["At 19:00", "At 19:30", "At 20:00", "At 18:30"]
        },
        "correct_index": 0,
        "explanation": {
            "ru": "Фильм начинается в 19:30, но встретиться Лаура предлагает ровно в 19:00 ('Lass uns also am besten um 19 Uhr vor dem Kino treffen').",
            "en": "The film starts at 19:30, but Laura proposes meeting at 19:00 sharp ('Lass uns also am besten um 19 Uhr vor dem Kino treffen')."
        },
        "transcript_tr": {
            "ru": "Привет, Ян, это Лаура. Я звоню по поводу нашего похода в кино сегодня вечером. Фильм начинается уже в 19:30, а не в восемь. Давай лучше встретимся в 19:00 перед кинотеатром, чтобы успеть купить попкорн. Перезвони мне!",
            "en": "Hi Jan, this is Laura. I'm calling about our cinema trip tonight. The film starts at 19:30 rather than eight. Let's meet at 19:00 in front of the cinema so we can get popcorn. Call me back!"
        }
    },
    {
        "id": "hv_a2_2",
        "level": "A2",
        "type": "announcement",
        "title": {
            "ru": "Прогноз погоды по радио (Wetterbericht)",
            "en": "Radio Weather Forecast"
        },
        "audio_text": (
            "Und nun das Wetter für Norddeutschland. "
            "Am Vormittag scheint überall noch die Sonne bei angenehmen zwanzig Grad. "
            "Ab dem Nachmittag ziehen jedoch dichte Wolken auf, "
            "und am Abend müssen Sie mit kräftigen Gewittern und Regen rechnen. "
            "Denken Sie also an Ihren Regenschirm!"
        ),
        "question": {
            "ru": "Какая погода ожидается сегодня вечером?",
            "en": "What weather is expected tonight?"
        },
        "options": {
            "ru": ["Яркое солнце и тепло", "Грозы и сильный дождь", "Снегопад и гололед", "Туман без осадков"],
            "en": ["Bright sun and warmth", "Thunderstorms and heavy rain", "Snowfall and ice", "Fog without rain"]
        },
        "correct_index": 1,
        "explanation": {
            "ru": "В прогнозе четко сказано: 'am Abend müssen Sie mit kräftigen Gewittern und Regen rechnen' (вечером ожидаются сильные грозы и дождь).",
            "en": "The forecast notes: 'am Abend müssen Sie mit kräftigen Gewittern und Regen rechnen' (expect strong thunderstorms and rain tonight)."
        },
        "transcript_tr": {
            "ru": "А теперь погода по северной Германии. В первой половине дня везде светит солнце при комфортных двадцати градусах. С обеда появятся плотные тучи, а вечером ожидаются сильные грозы и дождь. Не забудьте зонт!",
            "en": "And now the weather for Northern Germany. In the morning the sun shines everywhere at a pleasant 20 degrees. In the afternoon clouds gather, and in the evening expect heavy thunderstorms and rain. Remember your umbrella!"
        }
    },

    # B1 TASKS
    {
        "id": "hv_b1_1",
        "level": "B1",
        "type": "announcement",
        "title": {
            "ru": "Объявление в музее (Museum)",
            "en": "Museum Visitor Notice"
        },
        "audio_text": (
            "Sehr geehrte Besucherinnen und Besucher. "
            "Bitte beachten Sie, dass das Deutsche Technikmuseum heute aufgrund von Renovierungsarbeiten "
            "bereits um 17 Uhr statt wie üblich um 19 Uhr schließt. "
            "Die Sonderausstellung im zweiten Stock ist ab sofort für den Publikumsverkehr gesperrt. "
            "Wir bitten um Ihr Verständnis."
        ),
        "question": {
            "ru": "По какой причине музей сегодня закрывается раньше?",
            "en": "Why does the museum close earlier today?"
        },
        "options": {
            "ru": ["Государственный праздник", "Ремонтные работы", "Плохие погодные условия", "Забастовка сотрудников"],
            "en": ["Public holiday", "Renovation work", "Adverse weather", "Staff strike"]
        },
        "correct_index": 1,
        "explanation": {
            "ru": "Причина указана в тексте: 'aufgrund von Renovierungsarbeiten bereits um 17 Uhr... schließt' (из-за ремонтных работ).",
            "en": "The exact reason stated is: 'aufgrund von Renovierungsarbeiten' (due to renovation works)."
        },
        "transcript_tr": {
            "ru": "Уважаемые посетители. Обратите внимание, что Немецкий музей техники сегодня из-за ремонтных работ закрывается уже в 17:00 вместо обычных 19:00. Специальная выставка на втором этаже закрыта. Благодарим за понимание.",
            "en": "Dear visitors. Please note that the German Museum of Technology is closing at 17:00 today instead of the usual 19:00 due to renovation work. The special exhibition on the second floor is closed. Thank you for your understanding."
        }
    },
    {
        "id": "hv_b1_2",
        "level": "B1",
        "type": "voicemail",
        "title": {
            "ru": "Горячая линия сервиса (Kundenservice)",
            "en": "Customer Hotline Menu"
        },
        "audio_text": (
            "Herzlich willkommen beim Kundenservice von WohnTraum Immobilien. "
            "Wenn Sie eine Wohnung mieten möchten, drücken Sie bitte die Eins. "
            "Für Fragen zu bestehenden Mietverträgen oder Reparaturen wählen Sie die Zwei. "
            "Um mit einem Mitarbeiter unserer Buchhaltung verbunden zu werden, drücken Sie bitte die Drei."
        ),
        "question": {
            "ru": "Какую цифру нужно нажать по вопросам ремонта в арендованной квартире?",
            "en": "Which number should you press regarding repairs in a rented flat?"
        },
        "options": {
            "ru": ["Цифру 1", "Цифру 2", "Цифру 3", "Оставаться на линии"],
            "en": ["Number 1", "Number 2", "Number 3", "Stay on the line"]
        },
        "correct_index": 1,
        "explanation": {
            "ru": "Инструкция в аудио: 'Für Fragen zu bestehenden Mietverträgen oder Reparaturen wählen Sie die Zwei' (для договоров или ремонта выберите 2).",
            "en": "Voice instructions say: 'Für Fragen zu bestehenden Mietverträgen oder Reparaturen wählen Sie die Zwei' (press 2 for repairs)."
        },
        "transcript_tr": {
            "ru": "Добро пожаловать в клиентскую службу WohnTraum Недвижимость. Если вы хотите арендовать квартиру, нажмите 1. По вопросам действующих договоров аренды или ремонта нажмите 2. Для связи с бухгалтерией нажмите 3.",
            "en": "Welcome to WohnTraum Real Estate customer service. To rent an apartment, press 1. For questions regarding existing lease contracts or repairs, choose 2. To speak with accounting, press 3."
        }
    },
    {
        "id": "hv_b1_3",
        "level": "B1",
        "type": "conversation",
        "title": {
            "ru": "Интервью с основателем стартапа (Radio-Interview)",
            "en": "Startup Founder Radio Interview"
        },
        "audio_text": (
            "Frau Schneider, Sie leiten seit fünf Jahren ein erfolgreiches Software-Startup in Hamburg. "
            "Was war für Sie am Anfang die größte Hürde? "
            "- Nun, das nötige Kapital war gar nicht das Problem. "
            "Die eigentliche Herausforderung bestand darin, qualifizierte Fachkräfte zu finden, "
            "die bereit waren, das Risiko eines jungen Unternehmens mitzutragen."
        ),
        "question": {
            "ru": "Что оказалось самой сложной задачей на этапе основания компании?",
            "en": "What proved to be the most challenging task during the founding phase?"
        },
        "options": {
            "ru": ["Поиск стартового капитала", "Поиск квалифицированных специалистов", "Аренда офиса в Гамбурге", "Разработка первой версии программы"],
            "en": ["Securing startup funding", "Finding qualified specialists", "Leasing an office in Hamburg", "Developing the first software version"]
        },
        "correct_index": 1,
        "explanation": {
            "ru": "Основатель отвечает: 'Die eigentliche Herausforderung bestand darin, qualifizierte Fachkräfte zu finden' (настоящей сложностью был поиск квалифицированных специалистов).",
            "en": "The founder states: 'Die eigentliche Herausforderung bestand darin, qualifizierte Fachkräfte zu finden' (the actual hurdle was finding qualified talent)."
        },
        "transcript_tr": {
            "ru": "Госпожа Шнайдер, вы уже пять лет руководите успешным стартапом в Гамбурге. Что было в начале самым большим барьером? - Финансирование не было проблемой. Настоящей сложностью было найти квалифицированные кадры, готовые разделить риски молодой компании.",
            "en": "Ms. Schneider, you have led a successful startup in Hamburg for 5 years. What was your biggest obstacle at the start? - Capital wasn't an issue at all. The real challenge was finding qualified specialists willing to take on the risk of a young company."
        }
    }
]

def get_listening_task(level: str = "ALL", task_id: Optional[str] = None) -> Dict[str, Any]:
    """Получить задание по аудированию с фильтрацией по уровню (A1, A2, B1, ALL)"""
    if task_id:
        for t in LISTENING_TASKS:
            if t["id"] == task_id:
                return t

    if level in ("A1", "A2", "B1"):
        pool = [t for t in LISTENING_TASKS if t["level"] == level]
    else:
        pool = LISTENING_TASKS

    if not pool:
        pool = LISTENING_TASKS

    return random.choice(pool)
