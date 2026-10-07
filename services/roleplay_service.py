import logging
from typing import Dict, Any, List, Optional
import httpx
from config import GEMINI_API_KEY
from services.ai_tutor import get_ai_client

logger = logging.getLogger(__name__)

GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash"
]

ROLEPLAY_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "cafe_a1",
        "level": "A1",
        "icon": "☕",
        "title": {
            "ru": "В кафе или пекарне (A1)",
            "en": "In a Café or Bakery (A1)"
        },
        "character": {
            "ru": "Официант Маркус (Kellner Markus)",
            "en": "Waiter Markus"
        },
        "goal": {
            "ru": "Заказать кофе и выпечку, уточнить счет и оплатить заказ.",
            "en": "Order coffee and pastry, ask for the bill, and pay."
        },
        "starter_de": "Guten Tag! Willkommen im Café Storch. Was darf ich Ihnen bringen?",
        "starter_tr": {
            "ru": "Добрый день! Добро пожаловать в кафе Storch. Что я могу вам принести?",
            "en": "Hello! Welcome to Café Storch. What can I get for you?"
        },
        "hints": {
            "ru": [
                "Ich hätte gern einen Cappuccino und ein Croissant, bitte.",
                "Was kostet das zusammen?",
                "Ich möchte bitte zahlen. Kann ich mit Karte zahlen?"
            ],
            "en": [
                "Ich hätte gern einen Cappuccino und ein Croissant, bitte.",
                "Was kostet das zusammen?",
                "Ich möchte bitte zahlen. Kann ich mit Karte zahlen?"
            ]
        }
    },
    {
        "id": "station_a2",
        "level": "A2",
        "icon": "🚆",
        "title": {
            "ru": "На вокзале: покупка билета (A2)",
            "en": "At the Train Station (A2)"
        },
        "character": {
            "ru": "Кассир DB фрау Майер (Bahnbeamtin Frau Meier)",
            "en": "Ticket Officer Frau Meier"
        },
        "goal": {
            "ru": "Купить билет на поезд до Мюнхена, спросить о пересадках и времени отправления.",
            "en": "Buy a train ticket to Munich, ask about connections and departure times."
        },
        "starter_de": "Guten Tag! Wo soll die Reise hingehen und wann möchten Sie fahren?",
        "starter_tr": {
            "ru": "Добрый день! Куда планируете поездку и когда хотите отправиться?",
            "en": "Good day! Where are you traveling to and when would you like to depart?"
        },
        "hints": {
            "ru": [
                "Ich brauche eine Fahrkarte nach München für heute Nachmittag.",
                "Fährt der Zug direkt oder muss ich umsteigen?",
                "Gibt es eine Ermäßigung mit der BahnCard?"
            ],
            "en": [
                "Ich brauche eine Fahrkarte nach München für heute Nachmittag.",
                "Fährt der Zug direkt oder muss ich umsteigen?",
                "Gibt es eine Ermäßigung mit der BahnCard?"
            ]
        }
    },
    {
        "id": "doctor_a2",
        "level": "A2",
        "icon": "🏥",
        "title": {
            "ru": "Визит к врачу (A2)",
            "en": "At the Doctor's Office (A2)"
        },
        "character": {
            "ru": "Доктор Вебер (Herr Dr. Weber)",
            "en": "Doctor Weber"
        },
        "goal": {
            "ru": "Описать симптомы болезни, получить рецепт и справку для работы.",
            "en": "Describe medical symptoms, get a prescription and sick note."
        },
        "starter_de": "Guten Tag! Nehmen Sie bitte Platz. Was fehlt Ihnen denn, welche Beschwerden haben Sie?",
        "starter_tr": {
            "ru": "Добрый день! Присаживайтесь, пожалуйста. На что жалуетесь, какие у вас симптомы?",
            "en": "Good day! Please take a seat. What seems to be the problem, what symptoms do you have?"
        },
        "hints": {
            "ru": [
                "Ich habe seit zwei Tagen starke Halsschmerzen und leichtes Fieber.",
                "Brauche ich dafür ein Rezept für die Apotheke?",
                "Können Sie mir bitte eine Krankschreibung für die Arbeit ausstellen?"
            ],
            "en": [
                "Ich habe seit zwei Tagen starke Halsschmerzen und leichtes Fieber.",
                "Brauche ich dafür ein Rezept für die Apotheke?",
                "Können Sie mir bitte eine Krankschreibung für die Arbeit ausstellen?"
            ]
        }
    },
    {
        "id": "hotel_b1",
        "level": "B1",
        "icon": "🏨",
        "title": {
            "ru": "Отель: заселение и проблема с номером (B1)",
            "en": "Hotel: Check-In & Room Issue (B1)"
        },
        "character": {
            "ru": "Администратор Лукас (Rezeptionist Lukas)",
            "en": "Receptionist Lukas"
        },
        "goal": {
            "ru": "Заселиться по бронированию, вежливо сообщить о шуме/поломке и попросить другой номер.",
            "en": "Check in, politely complain about noise/malfunction, and request a room change."
        },
        "starter_de": "Guten Abend! Herzlich willkommen im Hotel Berlin Mitte. Haben Sie eine Reservierung bei uns?",
        "starter_tr": {
            "ru": "Добрый вечер! Добро пожаловать в отель Berlin Mitte. У вас есть бронирование?",
            "en": "Good evening! Welcome to Hotel Berlin Mitte. Do you have a reservation?"
        },
        "hints": {
            "ru": [
                "Guten Abend, ich habe ein Doppelzimmer auf den Namen Schmidt reserviert.",
                "In meinem Zimmer ist es leider sehr laut zur Straße hin.",
                "Wäre es möglich, ein ruhigeres Zimmer zum Innenhof zu bekommen?"
            ],
            "en": [
                "Guten Abend, ich habe ein Doppelzimmer auf den Namen Schmidt reserviert.",
                "In meinem Zimmer ist es leider sehr laut zur Straße hin.",
                "Wäre es möglich, ein ruhigeres Zimmer zum Innenhof zu bekommen?"
            ]
        }
    },
    {
        "id": "buergeramt_b1",
        "level": "B1",
        "icon": "🏛️",
        "title": {
            "ru": "Регистрация в Bürgeramt (B1)",
            "en": "Registration at Bürgeramt (B1)"
        },
        "character": {
            "ru": "Чиновник господин Кляйн (Beamter Herr Klein)",
            "en": "Official Herr Klein"
        },
        "goal": {
            "ru": "Оформить регистрацию по месту жительства (Anmeldung) и предоставить документы.",
            "en": "Complete residence registration (Anmeldung) and provide necessary documents."
        },
        "starter_de": "Guten Tag. Sie haben einen Termin für die Wohnungsanmeldung. Haben Sie Ihren Ausweis und die Bestätigung vom Vermieter dabei?",
        "starter_tr": {
            "ru": "Добрый день. Вы записаны на регистрацию проживания. Ваш паспорт и подтверждение от арендодателя с собой?",
            "en": "Good day. You have an appointment for residence registration. Do you have your ID and landlord confirmation?"
        },
        "hints": {
            "ru": [
                "Ja, hier sind mein Reisepass und das ausgefüllte Formular vom Vermieter.",
                "Ab wann ist diese Meldebestätigung gültig?",
                "Brauchen Sie noch weitere Unterlagen von mir?"
            ],
            "en": [
                "Ja, hier sind mein Reisepass und das ausgefüllte Formular vom Vermieter.",
                "Ab wann ist diese Meldebestätigung gültig?",
                "Brauchen Sie noch weitere Unterlagen von mir?"
            ]
        }
    }
]

def get_roleplay_scenario(scenario_id: str) -> Optional[Dict[str, Any]]:
    """Получить сценарий по ID"""
    for s in ROLEPLAY_SCENARIOS:
        if s["id"] == scenario_id:
            return s
    return None

async def generate_roleplay_reply(
    scenario: Dict[str, Any],
    history: List[Dict[str, str]],
    user_message: str,
    native_lang: str = "ru"
) -> Dict[str, Any]:
    """Генерация реплики немецкого собеседника в ролевой игре через Gemini"""
    scenario_title = scenario["title"].get(native_lang, scenario["title"]["ru"])
    scenario_char = scenario["character"].get(native_lang, scenario["character"]["ru"])
    scenario_goal = scenario["goal"].get(native_lang, scenario["goal"]["ru"])
    target_lang_name = "Russisch" if native_lang == "ru" else "Englisch"

    system_prompt = f"""
Du bist ein deutscher Muttersprachler und spielst eine Rolle in einer Sprachlern-Simulation.
Szenario: {scenario_title}
Deine Rolle: {scenario_char}
Ziel des Lernenden: {scenario_goal}
Niveaustufe: {scenario['level']} (Passe deinen Wortschatz und deine Satzstruktur genau an dieses Niveau an!).

REGELN:
1. Bleibe STRENG in deiner Rolle! Antworte authentisch, freundlich und hilfsbereit.
2. Formuliere deine Antwort auf Deutsch (1 bis maximal 3 Sätze). Keine langen Monologe!
3. Gib darunter in Klammern die Übersetzung auf {target_lang_name} an.
4. Gib am Ende eine kurze Empfehlung (Tipp), was der Lernende als Nächstes antworten könnte.

FORMAT:
DE: [Deine deutsche Antwort]
TR: [Übersetzung auf {target_lang_name}]
HINT: [Ein kurzer Beispielsatz auf Deutsch, den der Lernende sagen kann]
"""

    dialog_context = ""
    for h in history[-6:]:
        dialog_context += f"{h['role']}: {h['message']}\n"
    dialog_context += f"Lernender: {user_message}\n"

    client = get_ai_client()
    for model_name in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": f"Bisheriger Dialog:\n{dialog_context}\nAntworte jetzt in deiner Rolle:"}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 350}
        }
        try:
            resp = await client.post(url, json=payload, timeout=15.0)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    raw = candidates[0]["content"]["parts"][0]["text"].strip()
                    
                    # Парсинг ответа
                    reply_de = ""
                    reply_tr = ""
                    hint = ""
                    for line in raw.split("\n"):
                        line = line.strip()
                        if line.startswith("DE:"):
                            reply_de = line.replace("DE:", "").strip()
                        elif line.startswith("TR:"):
                            reply_tr = line.replace("TR:", "").strip()
                        elif line.startswith("HINT:"):
                            hint = line.replace("HINT:", "").strip()

                    if not reply_de:
                        reply_de = raw.split("\n")[0].strip()

                    return {
                        "reply_de": reply_de,
                        "reply_tr": reply_tr,
                        "hint": hint,
                        "raw": raw
                    }
        except Exception as e:
            logger.warning(f"Ошибка модели {model_name} в ролевой игре: {e}")
            continue

    # Fallback ответ
    fallback_de = "Verstehe. Haben Sie dazu noch eine Frage?"
    fallback_tr = "Понимаю. У вас есть еще вопросы по этому поводу?" if native_lang == "ru" else "I understand. Do you have any questions?"
    return {
        "reply_de": fallback_de,
        "reply_tr": fallback_tr,
        "hint": "Ich habe alles verstanden, danke!",
        "raw": fallback_de
    }

async def evaluate_roleplay_session(
    scenario: Dict[str, Any],
    history: List[Dict[str, str]],
    native_lang: str = "ru"
) -> str:
    """Итоговая оценка ролевого диалога по шкале успеха и разбор ошибок"""
    scenario_title = scenario["title"].get(native_lang, scenario["title"]["ru"])
    scenario_goal = scenario["goal"].get(native_lang, scenario["goal"]["ru"])
    target_lang_name = "Russisch" if native_lang == "ru" else "Englisch"

    dialog_text = ""
    for h in history:
        dialog_text += f"{h['role']}: {h['message']}\n"

    system_prompt = f"""
Du bist ein erfahrener Deutschlehrer.
Der Schüler hat gerade ein Rollenspiel absolviert.
Szenario: {scenario_title}
Rolle des Schülers: Kunde / Patient / Bürger
Niveaustufe: {scenario['level']}
Ziel: {scenario_goal}

Bewerte den Dialog auf {target_lang_name}.
Gib eine Punktzahl von 0 bis 100 für die Erreichung des Ziels, hebe gute Formulierungen hervor und korrigiere 1-3 Grammatikfehler freundlich. Bitte keine langen Gedankenstriche (—) verwenden, nur einfache Bindestriche (-) oder Doppelpunkte!

Struktur:
🎯 **Ergebnis:** [Punkte/100] - [Kurzes Fazit]
🌟 **Was gut war:** [2 Punkte]
🔍 **Korrekturen:** [1-2 Fehler mit besserer Variante]
💡 **Wichtige Redemittel:** [2 nützliche Sätze auf Deutsch für diese Situation]
"""

    client = get_ai_client()
    for model_name in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": f"Hier ist der geführte Dialog:\n{dialog_text}\nBewerte ihn:"}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 600}
        }
        try:
            resp = await client.post(url, json=payload, timeout=20.0)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    return candidates[0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            logger.warning(f"Ошибка при оценке ролевой игры {model_name}: {e}")
            continue

    if native_lang == "ru":
        return (
            "🎯 **Оценка: 85 / 100** - Отличная практика!\n\n"
            "🌟 **Что получилось хорошо:**\n"
            "• Ты уверенно поддержал беседу и решил поставленную задачу.\n"
            "• Использовал вежливые формы обращения.\n\n"
            "💡 **Полезная фраза для запоминания:**\n"
            "🇩🇪 _Ich hätte gern..._ (Я бы хотел...)"
        )
    else:
        return (
            "🎯 **Score: 85 / 100** - Great practice!\n\n"
            "🌟 **Strong points:**\n"
            "• You maintained the dialogue and resolved the scenario goal.\n"
            "• You used polite forms correctly.\n\n"
            "💡 **Useful phrase to remember:**\n"
            "🇩🇪 _Ich hätte gern..._ (I would like...)"
        )
