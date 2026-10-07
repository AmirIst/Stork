import random
from typing import Dict, Any, List

GERMAN_VERBS_DATA = [
    {
        "verb": "warten",
        "forms": "wartet • wartete • hat gewartet",
        "perfekt": "hat gewartet",
        "praeteritum": "wartete",
        "prep_case": "auf + Akkusativ",
        "prep": "auf",
        "case": "Akkusativ",
        "meaning_ru": "ждать кого-то/что-то",
        "meaning_en": "to wait for",
        "example": "Ich warte auf den Bus.",
        "example_tr_ru": "Я жду автобус.",
        "example_tr_en": "I am waiting for the bus."
    },
    {
        "verb": "helfen",
        "forms": "hilft • half • hat geholfen",
        "perfekt": "hat geholfen",
        "praeteritum": "half",
        "prep_case": "bei + Dativ",
        "prep": "bei",
        "case": "Dativ",
        "meaning_ru": "помогать с чем-то",
        "meaning_en": "to help with",
        "example": "Er hilft mir bei den Hausaufgaben.",
        "example_tr_ru": "Он помогает мне с домашним заданием.",
        "example_tr_en": "He helps me with homework."
    },
    {
        "verb": "denken",
        "forms": "denkt • dachte • hat gedacht",
        "perfekt": "hat gedacht",
        "praeteritum": "dachte",
        "prep_case": "an + Akkusativ",
        "prep": "an",
        "case": "Akkusativ",
        "meaning_ru": "думать о ком-то/чем-то",
        "meaning_en": "to think of/about",
        "example": "Ich denke oft an dich.",
        "example_tr_ru": "Я часто думаю о тебе.",
        "example_tr_en": "I often think about you."
    },
    {
        "verb": "sprechen",
        "forms": "spricht • sprach • hat gesprochen",
        "perfekt": "hat gesprochen",
        "praeteritum": "sprach",
        "prep_case": "über + Akkusativ",
        "prep": "über",
        "case": "Akkusativ",
        "meaning_ru": "говорить о чем-то",
        "meaning_en": "to talk about",
        "example": "Wir sprechen über das neue Projekt.",
        "example_tr_ru": "Мы говорим о новом проекте.",
        "example_tr_en": "We are talking about the new project."
    },
    {
        "verb": "beginnen",
        "forms": "beginnt • begann • hat begonnen",
        "perfekt": "hat begonnen",
        "praeteritum": "begann",
        "prep_case": "mit + Dativ",
        "prep": "mit",
        "case": "Dativ",
        "meaning_ru": "начинать с чего-то",
        "meaning_en": "to begin with",
        "example": "Der Unterricht beginnt mit einer Übung.",
        "example_tr_ru": "Урок начинается с упражнения.",
        "example_tr_en": "The lesson begins with an exercise."
    },
    {
        "verb": "sich freuen",
        "forms": "freut sich • freute sich • hat sich gefreut",
        "perfekt": "hat sich gefreut",
        "praeteritum": "freute sich",
        "prep_case": "auf + Akkusativ",
        "prep": "auf",
        "case": "Akkusativ",
        "meaning_ru": "радоваться будущему (ждать с нетерпением)",
        "meaning_en": "to look forward to",
        "example": "Ich freue mich auf das Wochenende.",
        "example_tr_ru": "Я с нетерпением жду выходных.",
        "example_tr_en": "I am looking forward to the weekend."
    },
    {
        "verb": "bitten",
        "forms": "bittet • bat • hat gebeten",
        "perfekt": "hat gebeten",
        "praeteritum": "bat",
        "prep_case": "um + Akkusativ",
        "prep": "um",
        "case": "Akkusativ",
        "meaning_ru": "просить о чем-то",
        "meaning_en": "to ask for",
        "example": "Darf ich Sie um Hilfe bitten?",
        "example_tr_ru": "Могу я попросить вас о помощи?",
        "example_tr_en": "May I ask you for help?"
    },
    {
        "verb": "gehören",
        "forms": "gehört • gehörte • hat gehört",
        "perfekt": "hat gehört",
        "praeteritum": "gehörte",
        "prep_case": "zu + Dativ",
        "prep": "zu",
        "case": "Dativ",
        "meaning_ru": "относиться к / являться частью",
        "meaning_en": "to belong to",
        "example": "Das gehört zu meinen Aufgaben.",
        "example_tr_ru": "Это относится к моим задачам.",
        "example_tr_en": "That belongs to my duties."
    },
    {
        "verb": "teilnehmen",
        "forms": "nimmt teil • nahm teil • hat teilgenommen",
        "perfekt": "hat teilgenommen",
        "praeteritum": "nahm teil",
        "prep_case": "an + Dativ",
        "prep": "an",
        "case": "Dativ",
        "meaning_ru": "принимать участие в чем-то",
        "meaning_en": "to participate in",
        "example": "Wer nimmt an der Konferenz teil?",
        "example_tr_ru": "Кто участвует в конференции?",
        "example_tr_en": "Who is participating in the conference?"
    },
    {
        "verb": "sich interessieren",
        "forms": "interessiert sich • interessierte sich • hat sich interessiert",
        "perfekt": "hat sich interessiert",
        "praeteritum": "interessierte sich",
        "prep_case": "für + Akkusativ",
        "prep": "für",
        "case": "Akkusativ",
        "meaning_ru": "интересоваться чем-то",
        "meaning_en": "to be interested in",
        "example": "Er interessiert sich für deutsche Kultur.",
        "example_tr_ru": "Он интересуется немецкой культурой.",
        "example_tr_en": "He is interested in German culture."
    },
    {
        "verb": "träumen",
        "forms": "träumt • träumte • hat geträumt",
        "perfekt": "hat geträumt",
        "praeteritum": "träumte",
        "prep_case": "von + Dativ",
        "prep": "von",
        "case": "Dativ",
        "meaning_ru": "мечтать о чем-то",
        "meaning_en": "to dream of",
        "example": "Sie träumt von einer Reise nach Berlin.",
        "example_tr_ru": "Она мечтает о поездке в Берлин.",
        "example_tr_en": "She dreams of a trip to Berlin."
    },
    {
        "verb": "einladen",
        "forms": "lädt ein • lud ein • hat eingeladen",
        "perfekt": "hat eingeladen",
        "praeteritum": "lud ein",
        "prep_case": "zu + Dativ",
        "prep": "zu",
        "case": "Dativ",
        "meaning_ru": "приглашать на что-то",
        "meaning_en": "to invite to",
        "example": "Ich lade dich zu meiner Geburtstagsparty ein.",
        "example_tr_ru": "Я приглашаю тебя на мой день рождения.",
        "example_tr_en": "I invite you to my birthday party."
    },
    {
        "verb": "suchen",
        "forms": "sucht • suchte • hat gesucht",
        "perfekt": "hat gesucht",
        "praeteritum": "suchte",
        "prep_case": "nach + Dativ",
        "prep": "nach",
        "case": "Dativ",
        "meaning_ru": "искать что-то",
        "meaning_en": "to search for",
        "example": "Wir suchen nach einer Lösung.",
        "example_tr_ru": "Мы ищем решение.",
        "example_tr_en": "We are looking for a solution."
    },
    {
        "verb": "fragen",
        "forms": "fragt • fragte • hat gefragt",
        "perfekt": "hat gefragt",
        "praeteritum": "fragte",
        "prep_case": "nach + Dativ",
        "prep": "nach",
        "case": "Dativ",
        "meaning_ru": "спрашивать о ком-то/чем-то",
        "meaning_en": "to ask about",
        "example": "Der Tourist fragt nach dem Weg.",
        "example_tr_ru": "Турист спрашивает дорогу.",
        "example_tr_en": "The tourist is asking for directions."
    },
    {
        "verb": "gratulieren",
        "forms": "gratuliert • gratulierte • hat gratuliert",
        "perfekt": "hat gratuliert",
        "praeteritum": "gratulierte",
        "prep_case": "zu + Dativ",
        "prep": "zu",
        "case": "Dativ",
        "meaning_ru": "поздравлять с чем-то",
        "meaning_en": "to congratulate on",
        "example": "Ich gratuliere dir zum Geburtstag!",
        "example_tr_ru": "Я поздравляю тебя с днем рождения!",
        "example_tr_en": "I congratulate you on your birthday!"
    },
    {
        "verb": "sich erinnern",
        "forms": "erinnert sich • erinnerte sich • hat sich erinnert",
        "perfekt": "hat sich erinnert",
        "praeteritum": "erinnerte sich",
        "prep_case": "an + Akkusativ",
        "prep": "an",
        "case": "Akkusativ",
        "meaning_ru": "вспоминать о ком-то/чем-то",
        "meaning_en": "to remember",
        "example": "Er erinnert sich an die Schulzeit.",
        "example_tr_ru": "Он вспоминает школьные годы.",
        "example_tr_en": "He remembers his school days."
    },
    {
        "verb": "passen",
        "forms": "passt • passte • hat gepasst",
        "perfekt": "hat gepasst",
        "praeteritum": "passte",
        "prep_case": "zu + Dativ",
        "prep": "zu",
        "case": "Dativ",
        "meaning_ru": "подходить к чему-то (по стилю)",
        "meaning_en": "to match / go with",
        "example": "Die Hose passt gut zum Hemd.",
        "example_tr_ru": "Брюки хорошо подходят к рубашке.",
        "example_tr_en": "The pants match the shirt well."
    },
    {
        "verb": "verstehen",
        "forms": "versteht • verstand • hat verstanden",
        "perfekt": "hat verstanden",
        "praeteritum": "verstand",
        "prep_case": "von + Dativ",
        "prep": "von",
        "case": "Dativ",
        "meaning_ru": "разбираться в чем-то",
        "meaning_en": "to understand / know about",
        "example": "Er versteht viel von Autos.",
        "example_tr_ru": "Он много понимает в машинах.",
        "example_tr_en": "He knows a lot about cars."
    },
    {
        "verb": "fahren",
        "forms": "fährt • fuhr • ist gefahren",
        "perfekt": "ist gefahren",
        "praeteritum": "fuhr",
        "prep_case": "mit + Dativ",
        "prep": "mit",
        "case": "Dativ",
        "meaning_ru": "ехать на чем-то",
        "meaning_en": "to drive / ride with",
        "example": "Ich fahre mit dem Zug nach München.",
        "example_tr_ru": "Я еду на поезде в Мюнхен.",
        "example_tr_en": "I am traveling by train to Munich."
    },
    {
        "verb": "schreiben",
        "forms": "schreibt • schrieb • hat geschrieben",
        "perfekt": "hat geschrieben",
        "praeteritum": "schrieb",
        "prep_case": "an + Akkusativ",
        "prep": "an",
        "case": "Akkusativ",
        "meaning_ru": "писать кому-то",
        "meaning_en": "to write to",
        "example": "Ich schreibe eine E-Mail an den Chef.",
        "example_tr_ru": "Я пишу электронное письмо шефу.",
        "example_tr_en": "I write an email to the boss."
    }
]

ALL_PREP_CASES = [
    "auf + Akkusativ", "an + Akkusativ", "an + Dativ", "bei + Dativ",
    "mit + Dativ", "von + Dativ", "zu + Dativ", "nach + Dativ",
    "für + Akkusativ", "über + Akkusativ", "um + Akkusativ"
]

def generate_verb_sprint_question(lang: str = "ru") -> Dict[str, Any]:
    """Генерирует вопрос для спринта по глаголам и предлогам"""
    item = random.choice(GERMAN_VERBS_DATA)
    q_type = random.choice(["forms", "prep_case", "gap_fill"])

    meaning = item["meaning_ru"] if lang == "ru" else item["meaning_en"]

    if q_type == "forms":
        # Вопрос на 3 формы глагола
        correct = item["perfekt"]
        verb = item["verb"]

        # Создаем правдоподобные дистракторы
        distractors = set()
        aux = "ist" if "ist" in correct else "hat"
        other_aux = "hat" if aux == "ist" else "ist"
        
        # Меняем приставку или суффикс
        base_stem = verb.replace("en", "").replace("n", "")
        distractors.add(f"{aux} ge{base_stem}t")
        distractors.add(f"{other_aux} {correct.split()[-1]}")
        distractors.add(f"{aux} {item['praeteritum']}")
        distractors.discard(correct)

        options = list(distractors)[:3]
        while len(options) < 3:
            options.append(f"{aux} ge{base_stem}en")
        options.append(correct)
        random.shuffle(options)

        if lang == "ru":
            prompt = (
                f"⚡ *Спринт: Формы глагола*\n\n"
                f"Какая форма *Perfekt* у глагола:\n"
                f"🇩🇪 *{verb}* ({meaning})?"
            )
        else:
            prompt = (
                f"⚡ *Sprint: Verb Forms*\n\n"
                f"What is the *Perfekt* form of:\n"
                f"🇩🇪 *{verb}* ({meaning})?"
            )

        explanation = f"💡 *{item['verb']}* ➔ _{item['forms']}_\n💬 {item['example']}"

    elif q_type == "prep_case":
        # Вопрос на управление предлога и падеж
        correct = item["prep_case"]
        distractors = [pc for pc in ALL_PREP_CASES if pc != correct]
        options = random.sample(distractors, 3) + [correct]
        random.shuffle(options)

        if lang == "ru":
            prompt = (
                f"⚡ *Спринт: Управление глагола*\n\n"
                f"С каким предлогом и падежом употребляется:\n"
                f"🇩🇪 *{item['verb']}* ({meaning})?"
            )
        else:
            prompt = (
                f"⚡ *Sprint: Preposition & Case*\n\n"
                f"Which preposition and case belong to:\n"
                f"🇩🇪 *{item['verb']}* ({meaning})?"
            )

        explanation = f"💡 *{item['verb']} + {item['prep_case']}*\n💬 _{item['example']}_\n({item['example_tr_ru'] if lang == 'ru' else item['example_tr_en']})"

    else:
        # Вопрос на заполнение пропуска в предложении
        example_with_gap = item["example"].replace(f" {item['prep']} ", " [ ... ] ")
        correct = item["prep"]
        
        distractors = [p for p in ["auf", "an", "bei", "mit", "von", "zu", "nach", "für", "über", "um"] if p != correct]
        options = random.sample(distractors, 3) + [correct]
        random.shuffle(options)

        if lang == "ru":
            prompt = (
                f"⚡ *Спринт: Заполни пропуск*\n\n"
                f"🇩🇪 _{example_with_gap}_\n\n"
                f"💬 Перевод: {item['example_tr_ru']}\n\n"
                f"Какой предлог пропущен?"
            )
        else:
            prompt = (
                f"⚡ *Sprint: Fill the Blank*\n\n"
                f"🇩🇪 _{example_with_gap}_\n\n"
                f"💬 Translation: {item['example_tr_en']}\n\n"
                f"Which preposition is missing?"
            )

        explanation = f"💡 *{item['verb']} + {item['prep_case']}*\n💬 _{item['example']}_"

    return {
        "prompt": prompt,
        "options": options,
        "correct": correct,
        "explanation": explanation,
        "verb": item["verb"]
    }
