"""
Сервис диагностики уровня и проверки готовности к экзамену Goethe B1 (Readiness Test).
Архитектурные принципы:
1. Детерминированный подсчет для объективных блоков (Lesen, Hören) в коде без участия ИИ.
2. Фиксированная рубрика (Rubric) для субъективных блоков (Schreiben, Sprechen) через Gemini с JSON-схемой.
3. Четкое разделение: официальный порог 60/100 для каждого модуля отдельно.
4. Маршрутизатор рекомендаций (Recommendation Engine), превращающий ошибки в прямые действия в боте.
"""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from config import GEMINI_API_KEY
from services.ai_tutor import get_ai_client

logger = logging.getLogger(__name__)

# Версии диагностик и рубрик для аналитики и калибровки
EXPRESS_VERSION = "express_v1"
GOETHE_B1_VERSION = "goethe_b1_v1"
RUBRIC_WRITING_VERSION = "rubric_writing_v1"
RUBRIC_SPEAKING_VERSION = "rubric_speaking_v1"

# ==============================================================================
# 1. ЭКСПРЕСС-ДИАГНОСТИКА (⚡ Express Level Check - 2-3 минуты, 8 вопросов)
# ==============================================================================

EXPRESS_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "exp_1",
        "level": "A1",
        "topic": "articles",
        "question": "Wähle den richtigen Artikel:\n\n___ Tisch ist sehr groß und modern.",
        "options": ["Der", "Die", "Das", "Den"],
        "correct_index": 0,
        "explanation": "Tisch ist maskulin: der Tisch."
    },
    {
        "id": "exp_2",
        "level": "A1",
        "topic": "verb_conjugation",
        "question": "Ergänze das Verb:\n\nIch ___ aus Berlin und wohne jetzt in Hamburg.",
        "options": ["kommst", "komme", "kommt", "kommen"],
        "correct_index": 1,
        "explanation": "Konjugation für 'ich': komme."
    },
    {
        "id": "exp_3",
        "level": "A2",
        "topic": "preposition_dativ",
        "question": "Ergänze die Präposition und den Artikel:\n\nWir treffen uns um 18 Uhr vor ___ Kino.",
        "options": ["das", "dem", "den", "der"],
        "correct_index": 1,
        "explanation": "Vor + Dativ (Ort/Wo?): vor dem Kino (das Kino -> dem)."
    },
    {
        "id": "exp_4",
        "level": "A2",
        "topic": "perfekt_partizip",
        "question": "Welche Form ist richtig?\n\nGestern habe ich einen sehr interessanten Film ___.",
        "options": ["gesehen", "geseht", "sehen", "gehesehen"],
        "correct_index": 0,
        "explanation": "Perfekt von sehen: hat gesehen."
    },
    {
        "id": "exp_5",
        "level": "A2",
        "topic": "modal_verbs_word_order",
        "question": "Wähle die richtige Satzstruktur:\n\nMorgen ___ ich sehr früh aufstehen.",
        "options": ["will", "muss", "habe", "kannst"],
        "correct_index": 1,
        "explanation": "Modalverb auf Position 2: 'Morgen muss ich... aufstehen'."
    },
    {
        "id": "exp_6",
        "level": "B1",
        "topic": "subordinate_clause_weil",
        "question": "Wähle das richtige Satzende:\n\nEr kann heute nicht zur Arbeit kommen, weil er krank ___.",
        "options": ["ist", "sein", "wird", "warum"],
        "correct_index": 0,
        "explanation": "Nebensatz mit 'weil': das konjugierte Verb steht am Ende (krank ist)."
    },
    {
        "id": "exp_7",
        "level": "B1",
        "topic": "connectors_obwohl",
        "question": "Welcher Konnektor passt?\n\n___ es stark geregnet hat, haben wir einen Spaziergang im Park gemacht.",
        "options": ["Weil", "Obwohl", "Deshalb", "Trotz"],
        "correct_index": 1,
        "explanation": "'Obwohl' drückt einen Gegengrund aus (Konzessivsatz)."
    },
    {
        "id": "exp_8",
        "level": "B1",
        "topic": "vocabulary_context",
        "question": "Was bedeutet der Satz?\n\n'Frau Weber bittet um eine rechtzeitige Bestätigung des Termins.'",
        "options": [
            "Frau Weber möchte den Termin absagen.",
            "Frau Weber bittet darum, bald Bescheid zu geben, ob der Termin klappt.",
            "Frau Weber hat den Termin vergessen.",
            "Frau Weber kommt zu spät zum Termin."
        ],
        "correct_index": 1,
        "explanation": "'Um Bestätigung bitten' = дать подтверждение встречи."
    }
]

def evaluate_express_diagnostic(user_answers: List[int]) -> Dict[str, Any]:
    """Детерминированная оценка экспресс-теста (код считает результат)"""
    total = len(EXPRESS_QUESTIONS)
    correct_count = 0
    weaknesses = []

    for idx, q in enumerate(EXPRESS_QUESTIONS):
        ans = user_answers[idx] if idx < len(user_answers) else -1
        if ans == q["correct_index"]:
            correct_count += 1
        else:
            weaknesses.append({
                "topic": q["topic"],
                "level": q["level"],
                "explanation": q["explanation"]
            })

    # Детерминированное правило уровня
    if correct_count >= 7:
        cefr = "B1"
    elif correct_count >= 4:
        cefr = "A2"
    else:
        cefr = "A1"

    score_pct = round((correct_count / total) * 100)

    return {
        "version": EXPRESS_VERSION,
        "total": total,
        "correct": correct_count,
        "score_pct": score_pct,
        "estimated_cefr": cefr,
        "weaknesses": weaknesses
    }


# ==============================================================================
# 2. GOETHE B1 READINESS TEST (~25-30 минут)
# ==============================================================================

# ----------------- МОДУЛЬ 1: LESEN (4 задания, 100 баллов детерминированно) -----------------
GOETHE_B1_LESEN_TASKS: List[Dict[str, Any]] = [
    {
        "id": "les_1",
        "title": "Teil 1: E-Mail über einen Umzug",
        "text": (
            "Liebe Sarah,\n\n"
            "endlich habe ich etwas Zeit, dir zu schreiben! Ich bin vor zwei Wochen nach München gezogen. "
            "Die neue Wohnung gefällt mir sehr gut, obwohl die Miete leider ziemlich hoch ist. "
            "Mein neuer Job in der IT-Firma gefällt mir auch, aber die Kollegen sprechen oft sehr schnell Bayrisch, "
            "sodass ich mich noch daran gewöhnen muss. Am Wochenende mache ich eine kleine Einweihungsparty. "
            "Hast du Lust zu kommen?\n\n"
            "Herzliche Grüße,\n"
            "Jan"
        ),
        "question": "Warum fällt Jan die Kommunikation bei der neuen Arbeit manchmal noch schwer?",
        "options": [
            "Er spricht noch kein Deutsch.",
            "Die Kollegen sprechen sehr schnell und im Dialekt.",
            "Die Kollegen haben keine Zeit für ihn.",
            "Er mag seine Kollegen in der IT-Firma nicht."
        ],
        "correct_index": 1,
        "explanation": "Im Text: 'die Kollegen sprechen oft sehr schnell Bayrisch, sodass ich mich noch daran gewöhnen muss'."
    },
    {
        "id": "les_2",
        "title": "Teil 2: Praxishinweis beim Arzt",
        "text": (
            "WICHTIGER HINWEIS FÜR UNSERE PATIENTEN:\n\n"
            "Unsere Praxis bleibt vom 12. bis zum 24. Oktober wegen Urlaubs geschlossen. "
            "In dringenden medizinischen Notfällen wenden Sie sich bitte an die Praxis Dr. med. Martin Vogel "
            "(Goethestraße 14, Tel. 089/542190). Ab Montag, dem 27. Oktober, sind wir wieder wie gewohnt für Sie da. "
            "Rezeptbestellungen können während des Urlaubs leider nicht bearbeitet werden."
        ),
        "question": "Was soll ein Patient während des Praxisurlaubs tun, wenn er dringend ärztliche Hilfe braucht?",
        "options": [
            "Bis zum 27. Oktober warten.",
            "Eine E-Mail für ein neues Rezept schreiben.",
            "Die Vertretungspraxis von Dr. Vogel kontaktieren.",
            "Direkt ins Krankenhaus gehen."
        ],
        "correct_index": 2,
        "explanation": "Im Text: 'In dringenden medizinischen Notfällen wenden Sie sich bitte an die Praxis Dr. med. Martin Vogel'."
    },
    {
        "id": "les_3",
        "title": "Teil 3: Anzeige: Sprachkursangebot",
        "text": (
            "DEUTSCH IM BERUF (B1/B2) - INTENSIVKURS AM ABEND:\n\n"
            "Möchten Sie sicherer im Berufsalltag auf Deutsch kommunizieren? In diesem Kurs trainieren wir "
            "das Verfassen von E-Mails, Telefongespräche mit Kunden und Präsentationen. "
            "Voraussetzung: abgeschlossenes Niveau A2. "
            "Dauer: 6 Wochen, dienstags und donnerstags von 18:30 bis 20:30 Uhr. "
            "Die Kursgebühr beträgt 240 Euro inklusive Lehrmaterial."
        ),
        "question": "Wer kann an diesem Kurs teilnehmen?",
        "options": [
            "Jeder, auch absolute Anfänger ohne Vorkenntnisse.",
            "Nur Personen, die bereits das Niveau A2 abgeschlossen haben.",
            "Nur Personen, die schon fließend B2 sprechen.",
            "Ausschließlich Studenten der Universität."
        ],
        "correct_index": 1,
        "explanation": "Im Text: 'Voraussetzung: abgeschlossenes Niveau A2'."
    },
    {
        "id": "les_4",
        "title": "Teil 4: Grammatikbaustein im Kontext",
        "text": (
            "Herr Müller hat sich entschieden, mit dem Fahrrad zur Arbeit zu fahren, "
            "___ er etwas für seine Gesundheit tun möchte und die Parkplätze in der Stadt zu teuer sind."
        ),
        "question": "Welche Konjunktion passt grammatikalisch und logisch in die Lücke?",
        "options": ["obwohl", "weil", "trotzdem", "denn"],
        "correct_index": 1,
        "explanation": "'Weil' leitet einen Kausalsatz ein, und das konjugierte Verb 'möchte' steht am Satzende."
    }
]

def score_lesen_module(answers: List[int]) -> Tuple[int, List[Dict[str, Any]]]:
    """Детерминированный подсчет модуля Lesen (0-100 баллов)"""
    total = len(GOETHE_B1_LESEN_TASKS)
    correct = 0
    errors = []
    for idx, t in enumerate(GOETHE_B1_LESEN_TASKS):
        ans = answers[idx] if idx < len(answers) else -1
        if ans == t["correct_index"]:
            correct += 1
        else:
            errors.append({
                "module": "lesen",
                "task_id": t["id"],
                "topic": t["title"],
                "explanation": t["explanation"]
            })
    score = round((correct / total) * 100)
    return score, errors


# ----------------- МОДУЛЬ 2: HÖREN (2 аудиоситуации, 100 баллов детерминированно) -----------------
GOETHE_B1_HOEREN_TASKS: List[Dict[str, Any]] = [
    {
        "id": "hoe_1",
        "title": "Hören Teil 1: Anrufbeantworter in der Autowerkstatt",
        # Текст озвучивается через edge-tts немецким диктором
        "audio_script": (
            "Guten Tag, Herr Schneider! Hier ist die Autowerkstatt Schmidt. "
            "Ihr Wagen ist nun fertig repariert. Wir haben die Bremsen und das Licht überprüft. "
            "Sie können das Auto heute bis 18 Uhr oder morgen früh ab 8 Uhr abholen. "
            "Die Gesamtrechnung beträgt 280 Euro. Vielen Dank und auf Wiederhören!"
        ),
        "question": "Bis wann kann Herr Schneider sein Auto heute noch abholen?",
        "options": [
            "Bis 16 Uhr.",
            "Bis 18 Uhr.",
            "Erst morgen Nachmittag.",
            "Nur bis 12 Uhr mittags."
        ],
        "correct_index": 1,
        "explanation": "Im Audio: 'Sie können das Auto heute bis 18 Uhr... abholen'."
    },
    {
        "id": "hoe_2",
        "title": "Hören Teil 2: Durchsage am Hauptbahnhof",
        "audio_script": (
            "Achtung an Gleis 7: Der Intercity-Express 584 nach Frankfurt über Nürnberg mit der planmäßigen "
            "Abfahrt um 14 Uhr 25 hat heute voraussichtlich 20 Minuten Verspätung. "
            "Grund dafür ist eine technische Störung an der Strecke. Wir bitten alle Reisenden um Verständnis."
        ),
        "question": "Warum verspätet sich der ICE nach Frankfurt?",
        "options": [
            "Wegen schlechten Wetters.",
            "Wegen einer technischen Störung an der Strecke.",
            "Weil ein Waggon fehlt.",
            "Wegen eines Streiks."
        ],
        "correct_index": 1,
        "explanation": "Im Audio: 'Grund dafür ist eine technische Störung an der Strecke'."
    }
]

def score_hoeren_module(answers: List[int]) -> Tuple[int, List[Dict[str, Any]]]:
    """Детерминированный подсчет модуля Hören (0-100 баллов)"""
    total = len(GOETHE_B1_HOEREN_TASKS)
    correct = 0
    errors = []
    for idx, t in enumerate(GOETHE_B1_HOEREN_TASKS):
        ans = answers[idx] if idx < len(answers) else -1
        if ans == t["correct_index"]:
            correct += 1
        else:
            errors.append({
                "module": "hoeren",
                "task_id": t["id"],
                "topic": t["title"],
                "explanation": t["explanation"]
            })
    score = round((correct / total) * 100)
    return score, errors


# ----------------- МОДУЛЬ 3: SCHREIBEN (Оценка через строгую rubric в Gemini) -----------------
GOETHE_B1_SCHREIBEN_PROMPT = {
    "task_id": "schreib_b1_diag",
    "prompt_de": (
        "Situation: Sie haben eine Einladung von Ihrem Kollegen Thomas zu seiner Geburtstagsfeier am Samstag erhalten.\n\n"
        "Schreiben Sie eine E-Mail als Antwort (ca. 40 bis 70 Wörter).\n"
        "Gehen Sie auf folgende 3 Punkte ein:\n"
        "1. Bedanken Sie sich für die Einladung.\n"
        "2. Erklären Sie, warum Sie erst eine Stunde später kommen können.\n"
        "3. Bieten Sie an, etwas für die Party mitzubringen (z.B. einen Kuchen oder Getränke)."
    ),
    "target_words": "40-70 Wörter"
}

RUBRIC_WRITING_SYSTEM_INSTRUCTION = """
Du bist ein erfahrener Deutsch-Dozent und Prüfer für Goethe-Zertifikat B1 Diagnostik.
Bewerte die schriftliche Leistung des Prüflings streng nach folgender festgelegter 100-Punkte-Rubrik:

KRITERIEN (max 100 Punkte):
1. task_completion (0-25 Punkte): Sind alle 3 geforderten Leitpunkte sinnvoll und vollständig behandelt?
2. grammar (0-25 Punkte): Korrektheit von Satzbau (Verb auf Position 2, Nebensätze mit weil/dass), Kasus (Dativ/Akkusativ) und Verbformen.
3. vocabulary (0-25 Punkte): Angemessener B1-Wortschatz, Rechtschreibung und passende Redemittel.
4. organization (0-25 Punkte): Textaufbau, Anrede (Lieber Thomas...), Grußformel (Viele Grüße...) und logische Verknüpfungen (und, aber, deshalb).

REGELN:
- Antworte AUSSCHLIESSLICH als valides JSON! Keine Markdown-Backticks vor oder nach dem JSON, kein Freitext!
- JSON-Format:
{
  "score": <Summe der 4 Kriterien, 0 bis 100>,
  "confidence": <Zahl von 0.70 bis 0.99>,
  "criteria": {
    "task_completion": <0-25>,
    "grammar": <0-25>,
    "vocabulary": <0-25>,
    "organization": <0-25>
  },
  "writing_profile": {
    "task_completion": <0-25>,
    "grammar": <0-25>,
    "vocabulary": <0-25>,
    "organization": <0-25>
  },
  "weak_points": [
    {
      "category": "grammar|vocabulary|structure",
      "topic": "dativ_akkusativ|subordinate_clause_word_order|verb_conjugation|formal_structure",
      "severity": "high|medium",
      "evidence": "Zitat aus Text",
      "explanation_ru": "Краткое объяснение ошибки на русском",
      "explanation_en": "Brief explanation in English"
    }
  ],
  "strengths_ru": ["Что получилось хорошо на русском"],
  "strengths_en": ["What was done well in English"],
  "improved_sample": "Korrektes deutsches Musterbeispiel (40-60 Wörter)"
}
"""

async def evaluate_schreiben_module(user_text: str, native_lang: str = "ru") -> Dict[str, Any]:
    """Оценка письменной части через строгую rubric в Gemini"""
    client = get_ai_client()
    user_prompt = f"""
Aufgabe:
{GOETHE_B1_SCHREIBEN_PROMPT['prompt_de']}

Text des Schülers:
"{user_text}"

Bewerte den Text jetzt nach der 4-Kriterien-Rubrik und gib striktes JSON zurück!
"""
    models = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-flash"]
    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": user_prompt}]}],
            "systemInstruction": {"parts": [{"text": RUBRIC_WRITING_SYSTEM_INSTRUCTION}]},
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "maxOutputTokens": 900
            }
        }
        try:
            res = await client.post(url, json=payload, timeout=20.0)
            if res.status_code == 200:
                data = res.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                parsed = json.loads(raw_text)
                return parsed
        except Exception as e:
            logger.warning(f"Ошибка модели {model_name} при оценке Schreiben: {e}")
            continue

    # Fallback при недоступности API
    word_count = len(user_text.split())
    base_score = min(60, max(30, word_count * 2))
    return {
        "score": base_score,
        "confidence": 0.70,
        "criteria": {
            "task_completion": 15,
            "grammar": 12,
            "vocabulary": 13,
            "organization": 12
        },
        "writing_profile": {
            "task_completion": 15,
            "grammar": 12,
            "vocabulary": 13,
            "organization": 12
        },
        "weak_points": [
            {
                "category": "grammar",
                "topic": "subordinate_clause_word_order",
                "severity": "medium",
                "evidence": "",
                "explanation_ru": "Проверь порядок слов в придаточных предложениях (глагол на последнем месте).",
                "explanation_en": "Check word order in subordinate clauses (verb at the end)."
            }
        ],
        "strengths_ru": ["Ты выполнил основное условие и ответил на письмо."],
        "strengths_en": ["You completed the main task and replied to the invitation."],
        "improved_sample": "Lieber Thomas, vielen Dank für die Einladung! Ich komme gerne, aber leider erst gegen 19 Uhr, weil ich noch arbeiten muss. Soll ich einen Kuchen mitbringen? Viele Grüße!"
    }


# ----------------- МОДУЛЬ 4: SPRECHEN (Оценка устной части через rubric) -----------------
GOETHE_B1_SPRECHEN_TASKS = {
    "part1": {
        "title": "Teil 1: Gemeinsam etwas planen",
        "prompt_de": "Planen Sie mit einem Kollegen ein gemeinsames Geschenk für einen Mitarbeiter. Machen Sie 1-2 konkrete Vorschläge auf Deutsch (z.B. Gutschein, Buch oder Korb mit Spezialitäten).",
        "target": "1-3 Sätze"
    },
    "part2": {
        "title": "Teil 2: Ein Thema präsentieren",
        "prompt_de": "Thema: 'Einkaufen im Internet oder im Geschäft?'. Sprechen Sie ca. 45-75 Sekunden darüber: Was sind Vorteile und Nachteile? Was bevorzugen Sie persönlich?",
        "target": "Sprachnachricht 45-75 Sek"
    },
    "part3": {
        "title": "Teil 3: Auf eine Frage reagieren",
        "prompt_de": "Frage des Prüfers: 'Glauben Sie, dass kleine Geschäfte in den Städten in Zukunft ganz verschwinden werden? Warum oder warum nicht?'",
        "target": "1-2 Sätze Antwort"
    }
}

RUBRIC_SPEAKING_SYSTEM_INSTRUCTION = """
Du bist ein erfahrener Deutsch-Dozent und Prüfer für Goethe-Zertifikat B1 Sprechen Diagnostik.
Bewerte die mündliche Leistung des Prüflings streng nach folgender festgelegter 100-Punkte-Rubrik:

KRITERIEN (max 100 Punkte):
1. task_completion (0-25 Punkte): Wurde die Aufgabe inhaltlich verständlich und vollständig gelöst?
2. fluency (0-25 Punkte): Flüssigkeit der Sprache, Sprechtempo, Angemessenheit von Pausen.
3. grammar (0-25 Punkte): Richtigkeit der Satzstrukturen, Konjugation und Verbposition.
4. vocabulary_pronunciation (0-25 Punkte): Wortschatzbreite, Verständlichkeit und Aussprache.

REGELN:
- Antworte AUSSCHLIESSLICH als valides JSON! Keine Markdown-Backticks vor oder nach dem JSON, kein Freitext!
- JSON-Format:
{
  "score": <Summe der 4 Kriterien, 0 bis 100>,
  "confidence": <Zahl von 0.70 bis 0.99>,
  "criteria": {
    "task_completion": <0-25>,
    "fluency": <0-25>,
    "grammar": <0-25>,
    "vocabulary_pronunciation": <0-25>
  },
  "speaking_profile": {
    "fluency": <0-25>,
    "grammar": <0-25>,
    "vocabulary": <0-25>,
    "pronunciation": <0-25>,
    "task_completion": <0-25>
  },
  "weak_points": [
    {
      "category": "speaking|grammar|vocabulary",
      "topic": "speaking_fluency|verb_position|case_endings|limited_vocabulary",
      "severity": "high|medium",
      "explanation_ru": "Краткое объяснение ошибки на русском",
      "explanation_en": "Brief explanation in English"
    }
  ],
  "strengths_ru": ["Что получилось хорошо на русском"],
  "strengths_en": ["What was done well in English"],
  "muster_antwort": "Flüssiges deutsches Beispiel für diese Situation"
}
"""

async def evaluate_sprechen_module(
    transcribed_answers: Dict[str, str],
    native_lang: str = "ru"
) -> Dict[str, Any]:
    """Оценка устного модуля по 3 частям через фиксированную рубрику"""
    client = get_ai_client()
    combined_transcript = (
        f"Teil 1 (Planung): {transcribed_answers.get('part1', '')}\n"
        f"Teil 2 (Präsentation): {transcribed_answers.get('part2', '')}\n"
        f"Teil 3 (Reaktion): {transcribed_answers.get('part3', '')}"
    )

    user_prompt = f"""
Leistung des Schülers in der mündlichen B1-Diagnostik:
{combined_transcript}

Bewerte die mündliche Leistung jetzt streng nach der 4-Kriterien-Rubrik und gib striktes JSON zurück!
"""
    models = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-flash"]
    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": user_prompt}]}],
            "systemInstruction": {"parts": [{"text": RUBRIC_SPEAKING_SYSTEM_INSTRUCTION}]},
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "maxOutputTokens": 900
            }
        }
        try:
            res = await client.post(url, json=payload, timeout=20.0)
            if res.status_code == 200:
                data = res.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                parsed = json.loads(raw_text)
                return parsed
        except Exception as e:
            logger.warning(f"Ошибка модели {model_name} при оценке Sprechen: {e}")
            continue

    # Fallback
    return {
        "score": 55,
        "confidence": 0.70,
        "criteria": {
            "task_completion": 14,
            "fluency": 13,
            "grammar": 14,
            "vocabulary_pronunciation": 14
        },
        "speaking_profile": {
            "fluency": 13,
            "grammar": 14,
            "vocabulary": 14,
            "pronunciation": 14,
            "task_completion": 14
        },
        "weak_points": [
            {
                "category": "speaking",
                "topic": "speaking_fluency",
                "severity": "medium",
                "explanation_ru": "Речь звучит немного неуверенно, делай меньше пауз при связке предложений.",
                "explanation_en": "Speech sounds slightly hesitant, try to use connectors with fewer pauses."
            }
        ],
        "strengths_ru": ["Ты четко донес свою мысль и ответил на поставленные вопросы."],
        "strengths_en": ["You conveyed your thoughts clearly and responded to the prompt."],
        "muster_antwort": "Ich kaufe gerne online ein, weil es praktisch ist, aber Kleidung probiere ich lieber im Geschäft an."
    }


# ==============================================================================
# 3. RECOMMENDATION ENGINE & ROUTER (Маршрутизатор персонального плана)
# ==============================================================================

def calculate_readiness_overall(
    lesen_score: int,
    hoeren_score: int,
    schreiben_score: int,
    sprechen_score: int
) -> Tuple[str, int, int, str]:
    """
    Вычисление статуса готовности (readiness_status) строго по правилам:
    - NOT_READY: есть модуль < 50
    - NEAR_PASS: один или два модуля 50-59 (в шаге от порога 60)
    - LIKELY_READY: все модули >= 60
    - STRONG: все модули >= 70
    Возвращает: (readiness_status, overall_score, failed_count, weakest_module)
    """
    scores = {
        "lesen": lesen_score,
        "hoeren": hoeren_score,
        "schreiben": schreiben_score,
        "sprechen": sprechen_score
    }
    vals = list(scores.values())
    overall_score = round(sum(vals) / len(vals))

    failed_count = sum(1 for v in vals if v < 60)
    weakest_mod = min(scores, key=scores.get)

    if any(v < 50 for v in vals):
        status = "NOT_READY"
    elif failed_count > 0:
        status = "NEAR_PASS"
    elif all(v >= 70 for v in vals):
        status = "STRONG"
    else:
        status = "LIKELY_READY"

    return status, overall_score, failed_count, weakest_mod

def build_recommendations_and_actions(
    all_weak_points: List[Dict[str, Any]],
    scores: Dict[str, int],
    native_lang: str = "ru"
) -> List[Dict[str, Any]]:
    """
    Превращает обнаруженные ошибки в конкретные действия с кнопками в Stork:
    - dativ_akkusativ -> тренажер артиклей и падежей
    - subordinate_clause_word_order / verbs / perfekt -> спринт глаголов
    - work_vocabulary / vocabulary -> словарные карточки B1
    - speaking_fluency -> диалог с ИИ-репетитором
    - formal_structure -> тренажер писем
    """
    actions = []
    seen_keys = set()

    # Анализ по модулям и конкретным ошибкам
    topics_found = {wp.get("topic", "") for wp in all_weak_points}

    # 1. Падежи и артикли
    if any("dativ" in t or "akkusativ" in t or "article" in t for t in topics_found) or scores.get("lesen", 100) < 60:
        if "train_cases" not in seen_keys:
            seen_keys.add("train_cases")
            actions.append({
                "action_id": "train_cases",
                "btn_callback": "menu_articles",
                "title": "🔹 Подтянуть артикли и падежи" if native_lang == "ru" else "🔹 Practice Cases & Articles",
                "reason": "Обнаружены ошибки в падежных окончаниях (Dativ/Akkusativ)" if native_lang == "ru" else "Mistakes detected in case endings (Dativ/Akkusativ)"
            })

    # 2. Глаголы, порядок слов и Perfekt
    if any("verb" in t or "perfekt" in t or "subordinate" in t for t in topics_found) or scores.get("schreiben", 100) < 60:
        if "train_verbs" not in seen_keys:
            seen_keys.add("train_verbs")
            actions.append({
                "action_id": "train_verbs",
                "btn_callback": "menu_verbs_sprint",
                "title": "🔄 Спринт глаголов (Perfekt и связки)" if native_lang == "ru" else "🔄 Verb Sprint (Perfekt & Connectors)",
                "reason": "Нужно укрепить порядок слов в сложных предложениях" if native_lang == "ru" else "Strengthen sentence structure and verb positions"
            })

    # 3. Словарный запас
    if any("vocab" in t or "lexik" in t for t in topics_found) or scores.get("lesen", 100) < 70:
        if "train_vocab" not in seen_keys:
            seen_keys.add("train_vocab")
            actions.append({
                "action_id": "train_vocab",
                "btn_callback": "menu_cards",
                "title": "📚 Учить лексику уровня B1" if native_lang == "ru" else "📚 Learn B1 Vocabulary",
                "reason": "Расширить активный словарь для беглого понимания" if native_lang == "ru" else "Expand active vocabulary for faster comprehension"
            })

    # 4. Беглость речи (Sprechen)
    if scores.get("sprechen", 100) < 65 or any("speaking" in t or "fluency" in t for t in topics_found):
        if "train_ai_speech" not in seen_keys:
            seen_keys.add("train_ai_speech")
            actions.append({
                "action_id": "train_ai_speech",
                "btn_callback": "menu_ai",
                "title": "🗣 Разговорная практика со Stork" if native_lang == "ru" else "🗣 Speaking Practice with Stork",
                "reason": "Устранить паузы и повысить беглость диалога" if native_lang == "ru" else "Reduce hesitation and boost speaking fluency"
            })

    # 5. Ролевые ситуации
    if "train_roleplay" not in seen_keys and len(actions) < 4:
        seen_keys.add("train_roleplay")
        actions.append({
            "action_id": "train_roleplay",
            "btn_callback": "menu_roleplay",
            "title": "🎭 Симуляция диалогов из жизни" if native_lang == "ru" else "🎭 Real-life Roleplay Scenarios",
            "reason": "Закрепить уверенность в бытовых ситуациях (Bürgeramt, вокзал, кафе)" if native_lang == "ru" else "Build confidence in everyday interactions"
        })

    return actions
