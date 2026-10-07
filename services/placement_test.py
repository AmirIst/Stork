"""
Сервис комплексного адаптивного теста на определение уровня немецкого языка (A1-B1).
Включает расширенный пул из 60 верифицированных заданий по шкале CEFR (Goethe / Telc):
- 20 вопросов A1 (базовая грамматика, Präsens, Akkusativ, Negation, предлоги времени)
- 20 вопросов A2 (Perfekt, Dativ, Wechselpräpositionen, Nebensätze, Adjektivdeklination)
- 20 вопросов B1 (Passiv, Konjunktiv II, Genitiv, Relativsätze, Infinitiv mit zu)

На каждый проход теста случайно формируется сбалансированная сессия из 20 вопросов
(7 уровня A1, 7 уровня A2, 6 уровня B1), исключая предсказуемость при повторном прохождении.
"""
import random
from typing import List, Dict, Any, Tuple, Optional

PLACEMENT_QUESTION_POOL: List[Dict[str, Any]] = [
    # =========================================================================
    # === БЛОК A1: НАЧАЛЬНЫЙ УРОВЕНЬ (Вопросы 1 - 20) =========================
    # =========================================================================
    {
        "id": 1,
        "level": "A1",
        "topic": {"ru": "Спряжение глаголов в настоящем времени (Präsens)", "en": "Present tense verb conjugation (Präsens)"},
        "question": "Wie ___ du mit Vornamen?",
        "options": ["heißt", "heiße", "heißen", "heißt du"],
        "correct_index": 0,
        "explanation": {"ru": "С местоимением du глагол heißen принимает окончание -t: du heißt.", "en": "With pronoun 'du', the verb 'heißen' takes ending -t: du heißt."}
    },
    {
        "id": 2,
        "level": "A1",
        "topic": {"ru": "Винительный падеж (Akkusativ) и артикли", "en": "Accusative case (Akkusativ) & articles"},
        "question": "Ich kaufe ___ Apfel im Supermarkt.",
        "options": ["einen", "ein", "eine", "einem"],
        "correct_index": 0,
        "explanation": {"ru": "Мужской род (der Apfel) в Akkusativ меняет неопределенный артикль на einen.", "en": "Masculine noun (der Apfel) in Accusative takes 'einen'."}
    },
    {
        "id": 3,
        "level": "A1",
        "topic": {"ru": "Отрицание существительных (kein vs nicht)", "en": "Negation (kein vs nicht)"},
        "question": "Das ist ___ Problem, wir haben genug Zeit!",
        "options": ["kein", "nicht", "keine", "keinen"],
        "correct_index": 0,
        "explanation": {"ru": "Существительное среднего рода das Problem отрицается словом kein: kein Problem.", "en": "Neuter noun 'das Problem' is negated with 'kein': kein Problem."}
    },
    {
        "id": 4,
        "level": "A1",
        "topic": {"ru": "Предлоги времени (Präpositionen der Zeit)", "en": "Prepositions of time"},
        "question": "Der Deutschkurs beginnt ___ 18:30 Uhr.",
        "options": ["um", "am", "im", "an"],
        "correct_index": 0,
        "explanation": {"ru": "Точное время в часах всегда используется с предлогом um: um 18:30 Uhr.", "en": "Exact clock time always takes the preposition 'um': um 18:30 Uhr."}
    },
    {
        "id": 5,
        "level": "A1",
        "topic": {"ru": "Глагол sein (быть) в Präsens", "en": "Verb 'sein' (to be) in present tense"},
        "question": "Wo ___ ihr gestern Abend gewesen?",
        "options": ["seid", "sind", "bist", "waren"],
        "correct_index": 0,
        "explanation": {"ru": "Форма глагола sein для местоимения ihr (вы) в настоящем времени - seid.", "en": "Conjugation of 'sein' for pronoun 'ihr' is 'seid'."}
    },
    {
        "id": 6,
        "level": "A1",
        "topic": {"ru": "Вопросительные слова (W-Fragen)", "en": "Question words (W-Fragen)"},
        "question": "___ wohnst du? - In Frankfurt am Main.",
        "options": ["Wo", "Wohin", "Woher", "Was"],
        "correct_index": 0,
        "explanation": {"ru": "Вопрос о месте жительства/нахождении задается словом Wo (где).", "en": "Question about location takes 'Wo' (where)."}
    },
    {
        "id": 7,
        "level": "A1",
        "topic": {"ru": "Неопределенный артикль женского рода", "en": "Feminine indefinite article"},
        "question": "Ich habe ___ Frage an den Lehrer.",
        "options": ["eine", "ein", "einen", "einer"],
        "correct_index": 0,
        "explanation": {"ru": "Существительное die Frage женского рода, в Akkusativ неопределенный артикль - eine.", "en": "Feminine noun 'die Frage' takes indefinite article 'eine' in Accusative."}
    },
    {
        "id": 8,
        "level": "A1",
        "topic": {"ru": "Модальный глагол können (мочь, уметь)", "en": "Modal verb 'können'"},
        "question": "___ du gut Deutsch sprechen?",
        "options": ["Kannst", "Können", "Kann", "Könnt"],
        "correct_index": 0,
        "explanation": {"ru": "Спряжение können с местоимением du: du kannst.", "en": "Conjugation of 'können' with 'du' is 'kannst'."}
    },
    {
        "id": 9,
        "level": "A1",
        "topic": {"ru": "Предлоги направления с городами и странами", "en": "Preposition of direction with cities"},
        "question": "Morgen fliege ich ___ München.",
        "options": ["nach", "in", "zu", "nach dem"],
        "correct_index": 0,
        "explanation": {"ru": "С названиями городов и стран среднего рода без артикля используется предлог nach.", "en": "Cities and neuter countries without article take preposition 'nach'."}
    },
    {
        "id": 10,
        "level": "A1",
        "topic": {"ru": "Дни недели и предлог am", "en": "Days of week and preposition 'am'"},
        "question": "Wir treffen uns ___ Freitag um 19 Uhr.",
        "options": ["am", "im", "um", "an"],
        "correct_index": 0,
        "explanation": {"ru": "С днями недели и частями суток (кроме ночи) используется предлог am: am Freitag.", "en": "Days of the week always take 'am': am Freitag."}
    },
    {
        "id": 11,
        "level": "A1",
        "topic": {"ru": "Личные местоимения в Nominativ", "en": "Personal pronouns in Nominative"},
        "question": "Das ist Herr Müller. ___ arbeitet als Arzt.",
        "options": ["Er", "Es", "Ihm", "Ihn"],
        "correct_index": 0,
        "explanation": {"ru": "Мужской род (Herr Müller) заменяется личным местоимением Er (он).", "en": "Masculine subject (Herr Müller) is replaced by 'Er' (he)."}
    },
    {
        "id": 12,
        "level": "A1",
        "topic": {"ru": "Повелительное наклонение (Imperativ du)", "en": "Imperative mood (du)"},
        "question": "___ bitte das Fenster auf! Es ist warm.",
        "options": ["Mach", "Machest", "Macht", "Machen"],
        "correct_index": 0,
        "explanation": {"ru": "Форма повелительного наклонения для du образуется от основы глагола без окончания: Mach!", "en": "Imperative for 'du' drops ending: Mach!"}
    },
    {
        "id": 13,
        "level": "A1",
        "topic": {"ru": "Отделяемые приставки (Trennbare Verben)", "en": "Separable prefix verbs"},
        "question": "Ich stehe jeden Morgen um 7 Uhr ___.",
        "options": ["auf", "aus", "ein", "an"],
        "correct_index": 0,
        "explanation": {"ru": "Глагол aufstehen (вставать) отделяет приставку auf в конец простого предложения.", "en": "Verb 'aufstehen' separates prefix 'auf' to the end of clause."}
    },
    {
        "id": 14,
        "level": "A1",
        "topic": {"ru": "Форма множественного числа глагола", "en": "Plural verb form"},
        "question": "Wie viel ___ die Orangen hier?",
        "options": ["kosten", "kostet", "koste", "gekostet"],
        "correct_index": 0,
        "explanation": {"ru": "Существительное die Orangen во множественном числе требует глагол kosten: kosten die Orangen.", "en": "Plural subject 'die Orangen' takes plural verb form 'kosten'."}
    },
    {
        "id": 15,
        "level": "A1",
        "topic": {"ru": "Притяжательные местоимения (mein, dein)", "en": "Possessive pronouns"},
        "question": "Das ist ___ Schwester, sie heißt Laura.",
        "options": ["meine", "mein", "meinen", "meinem"],
        "correct_index": 0,
        "explanation": {"ru": "Существительное die Schwester женского рода, поэтому притяжательное местоимение - meine.", "en": "Feminine noun takes possessive 'meine'."}
    },
    {
        "id": 16,
        "level": "A1",
        "topic": {"ru": "Предлог ohne (без) + Akkusativ", "en": "Preposition 'ohne' + Accusative"},
        "question": "Ich trinke Kaffee immer ___ Zucker.",
        "options": ["ohne", "mit", "nach", "von"],
        "correct_index": 0,
        "explanation": {"ru": "Предлог ohne (без) требует винительного падежа: ohne Zucker.", "en": "Preposition 'ohne' takes Accusative: ohne Zucker."}
    },
    {
        "id": 17,
        "level": "A1",
        "topic": {"ru": "Спряжение глагола haben (иметь)", "en": "Conjugation of 'haben'"},
        "question": "___ ihr heute Nachmittag Zeit?",
        "options": ["Habt", "Haben", "Hast", "Hat"],
        "correct_index": 0,
        "explanation": {"ru": "Форма глагола haben с местоимением ihr (вы) - habt.", "en": "Conjugation of 'haben' with pronoun 'ihr' is 'habt'."}
    },
    {
        "id": 18,
        "level": "A1",
        "topic": {"ru": "Порядок слов в простом повествовательном предложении", "en": "Word order in simple statement"},
        "question": "Heute ___ ich meine Großeltern.",
        "options": ["besuche", "ich besuche", "besuchen", "habe besucht"],
        "correct_index": 0,
        "explanation": {"ru": "В немецком повествовательном предложении сказуемое всегда строго на 2-м месте: Heute besuche ich.", "en": "Conjugated verb always occupies 2nd position: Heute besuche ich."}
    },
    {
        "id": 19,
        "level": "A1",
        "topic": {"ru": "Времена года и месяцы с предлогом im", "en": "Months/seasons with preposition 'im'"},
        "question": "Mein Geburtstag ist ___ Juli.",
        "options": ["im", "am", "um", "in"],
        "correct_index": 0,
        "explanation": {"ru": "С названиями месяцев и времен года используется предлог im (in dem): im Juli.", "en": "Months always take preposition 'im': im Juli."}
    },
    {
        "id": 20,
        "level": "A1",
        "topic": {"ru": "Устойчивые разговорные конструкции", "en": "Common conversational idioms"},
        "question": "Sprechen Sie Deutsch? - Ja, ein ___.",
        "options": ["bisschen", "klein", "wenige", "kurz"],
        "correct_index": 0,
        "explanation": {"ru": "Устойчивое выражение 'немного': ein bisschen.", "en": "Idiomatic expression 'a little bit': ein bisschen."}
    },

    # =========================================================================
    # === БЛОК A2: РАЗГОВОРНЫЙ ЭЛЕМЕНТАРНЫЙ УРОВЕНЬ (Вопросы 21 - 40) ==========
    # =========================================================================
    {
        "id": 21,
        "level": "A2",
        "topic": {"ru": "Прошедшее время Perfekt со вспомогательным sein", "en": "Perfekt tense with auxiliary 'sein'"},
        "question": "Gestern ___ meine Schwester nach Berlin gefahren.",
        "options": ["ist", "hat", "wird", "war"],
        "correct_index": 0,
        "explanation": {"ru": "Глаголы движения с перемещением в пространстве (fahren) образуют Perfekt с sein: ist gefahren.", "en": "Verbs of motion with change of location form Perfekt with 'sein': ist gefahren."}
    },
    {
        "id": 22,
        "level": "A2",
        "topic": {"ru": "Предлоги двойного управления (Dativ / Где?)", "en": "Two-way prepositions (Dative / Where?)"},
        "question": "Das Buch liegt auf ___ Tisch.",
        "options": ["dem", "den", "das", "die"],
        "correct_index": 0,
        "explanation": {"ru": "Вопрос 'Где?' (Wo?) требует дательного падежа (Dativ). Der Tisch в Dativ -> dem Tisch.", "en": "Location question 'Where?' (Wo?) requires Dative. 'Der Tisch' becomes 'dem Tisch'."}
    },
    {
        "id": 23,
        "level": "A2",
        "topic": {"ru": "Модальные глаголы в прошедшем времени (Präteritum)", "en": "Modal verbs in past (Präteritum)"},
        "question": "Ich war gestern krank und ___ nicht zur Arbeit gehen.",
        "options": ["konnte", "kann", "gekonnt", "muss"],
        "correct_index": 0,
        "explanation": {"ru": "В прошедшем времени модальный глагол können имеет форму konnte (я не мог).", "en": "In past tense, modal verb 'können' takes form 'konnte'."}
    },
    {
        "id": 24,
        "level": "A2",
        "topic": {"ru": "Порядок слов в придаточных предложениях с союзом weil", "en": "Subordinate clause word order with 'weil'"},
        "question": "Ich lerne Deutsch, weil ich in Deutschland studieren ___.",
        "options": ["möchte", "möchten", "möchte ich", "will ich"],
        "correct_index": 0,
        "explanation": {"ru": "Союз weil отправляет спрягаемый глагол на самое последнее место в предложении.", "en": "Conjunction 'weil' sends the conjugated verb to the very end of clause."}
    },
    {
        "id": 25,
        "level": "A2",
        "topic": {"ru": "Предлоги двойного управления (Akkusativ / Куда?)", "en": "Two-way prepositions (Accusative / Where to?)"},
        "question": "Ich stelle die Vase auf ___ Tisch.",
        "options": ["den", "dem", "das", "der"],
        "correct_index": 0,
        "explanation": {"ru": "Вопрос 'Куда?' (Wohin?) требует винительного падежа (Akkusativ): auf den Tisch.", "en": "Direction question 'Where to?' (Wohin?) requires Accusative: auf den Tisch."}
    },
    {
        "id": 26,
        "level": "A2",
        "topic": {"ru": "Глаголы с постоянным управлением предлогами", "en": "Verbs with fixed prepositions"},
        "question": "Mein Bruder interessiert sich sehr ___ moderne Kunst.",
        "options": ["für", "über", "an", "mit"],
        "correct_index": 0,
        "explanation": {"ru": "Глагол sich interessieren требует предлога für + Akkusativ.", "en": "Verb 'sich interessieren' always takes preposition 'für' + Accusative."}
    },
    {
        "id": 27,
        "level": "A2",
        "topic": {"ru": "Дательный падеж во множественном числе", "en": "Dative plural declension"},
        "question": "Wir sind seit zwei Jahren mit unseren ___ befreundet.",
        "options": ["Nachbarn", "Nachbar", "Nachbars", "Nachbarin"],
        "correct_index": 0,
        "explanation": {"ru": "Во множественном числе в Dativ существительные получают окончание -(e)n: den Nachbarn.", "en": "In Dative plural, nouns take ending -(e)n: den Nachbarn."}
    },
    {
        "id": 28,
        "level": "A2",
        "topic": {"ru": "Придаточные условия с союзом wenn", "en": "Conditional clauses with 'wenn'"},
        "question": "Wenn das Wetter schön ist, ___ wir einen Spaziergang.",
        "options": ["machen", "wir machen", "machen wir", "gemacht"],
        "correct_index": 0,
        "explanation": {"ru": "Если придаточное предложение стоит первым, главное предложение начинается со сказуемого (Inversion): machen wir.", "en": "When subordinate clause comes first, main clause begins with verb: machen wir."}
    },
    {
        "id": 29,
        "level": "A2",
        "topic": {"ru": "Возвратные глаголы (Reflexive Verben)", "en": "Reflexive verbs"},
        "question": "Ich ziehe ___ eine warme Jacke an.",
        "options": ["mir", "mich", "sich", "dir"],
        "correct_index": 0,
        "explanation": {"ru": "Когда у возвратного глагола есть прямое дополнение (eine Jacke), возвратное местоимение стоит в Dativ: mir anziehen.", "en": "With a direct object present, reflexive pronoun takes Dative: mir anziehen."}
    },
    {
        "id": 30,
        "level": "A2",
        "topic": {"ru": "Сравнительная степень прилагательных (Komparativ)", "en": "Comparative degree of adjectives"},
        "question": "Mein neuer Laptop ist viel schneller ___ mein alter Computer.",
        "options": ["als", "wie", "von", "denn"],
        "correct_index": 0,
        "explanation": {"ru": "При сравнении в сравнительной степени используется союз als (быстрее, чем): schneller als.", "en": "Comparative degree uses 'als' for comparison: schneller als."}
    },
    {
        "id": 31,
        "level": "A2",
        "topic": {"ru": "Управление глагола sich freuen auf", "en": "Preposition with 'sich freuen auf'"},
        "question": "Ich freue mich schon sehr ___ den Urlaub nächste Woche.",
        "options": ["auf", "über", "an", "für"],
        "correct_index": 0,
        "explanation": {"ru": "Радость по поводу предстоящего события выражается конструкцией sich freuen auf + Akkusativ.", "en": "Anticipating future event takes 'sich freuen auf' + Accusative."}
    },
    {
        "id": 32,
        "level": "A2",
        "topic": {"ru": "Придаточные изъяснительные с союзом dass", "en": "Object clauses with 'dass'"},
        "question": "Der Arzt sagt, ___ du mehr Wasser trinken sollst.",
        "options": ["dass", "das", "weil", "ob"],
        "correct_index": 0,
        "explanation": {"ru": "Союз 'что' в придаточном предложении пишется с двумя s (dass) и отправляет глагол в конец.", "en": "Conjunction 'that' is spelled 'dass' and places verb at end."}
    },
    {
        "id": 33,
        "level": "A2",
        "topic": {"ru": "Прошедшее время глаголов haben и sein (Präteritum)", "en": "Simple past of 'haben' and 'sein'"},
        "question": "Letzten Sommer ___ wir zwei Wochen in Italien.",
        "options": ["waren", "hatten", "sind", "waren gewesen"],
        "correct_index": 0,
        "explanation": {"ru": "Для sein в разговорной речи всегда предпочитается форма Präteritum: wir waren.", "en": "Präteritum 'waren' is preferred for 'sein' in conversational past."}
    },
    {
        "id": 34,
        "level": "A2",
        "topic": {"ru": "Склонение прилагательных с неопределенным артиклем", "en": "Adjective declension with indefinite article"},
        "question": "Er hat gestern einen ___ Film im Kino gesehen.",
        "options": ["spannenden", "spannender", "spannendes", "spannendem"],
        "correct_index": 0,
        "explanation": {"ru": "Мужской род в Akkusativ с неопределенным артиклем получает окончание -en: einen spannenden Film.", "en": "Masculine Accusative with indefinite article takes ending -en: einen spannenden Film."}
    },
    {
        "id": 35,
        "level": "A2",
        "topic": {"ru": "Косвенный вопрос (Indirekte Frage)", "en": "Indirect questions"},
        "question": "Können Sie mir sagen, wann der nächste Zug ___?",
        "options": ["abfährt", "fährt ab", "abfahren", "abgefahren ist"],
        "correct_index": 0,
        "explanation": {"ru": "В косвенном вопросе порядок слов как в придаточном: глагол с отделяемой приставкой идет в конец в слитном виде: abfährt.", "en": "In indirect questions, the conjugated separable verb joins and moves to the end: abfährt."}
    },
    {
        "id": 36,
        "level": "A2",
        "topic": {"ru": "Сравнение равенства (so ... wie)", "en": "Comparison of equality (so ... wie)"},
        "question": "Meine Schwester ist genauso alt ___ ich.",
        "options": ["wie", "als", "denn", "so"],
        "correct_index": 0,
        "explanation": {"ru": "При сравнении одинаковых качеств используется союз wie (такой же ... как): genauso alt wie.", "en": "Equal comparison takes 'wie': genauso alt wie."}
    },
    {
        "id": 37,
        "level": "A2",
        "topic": {"ru": "Предлог mit + Dativ для транспорта", "en": "Preposition 'mit' + Dative for transport"},
        "question": "Ich fahre jeden Morgen mit ___ U-Bahn zur Arbeit.",
        "options": ["der", "die", "den", "dem"],
        "correct_index": 0,
        "explanation": {"ru": "Предлог mit всегда требует Dativ. Die U-Bahn в Dativ меняется на der: mit der U-Bahn.", "en": "Preposition 'mit' always governs Dative: die U-Bahn -> mit der U-Bahn."}
    },
    {
        "id": 38,
        "level": "A2",
        "topic": {"ru": "Уступительные придаточные с союзом obwohl", "en": "Concessive clauses with 'obwohl'"},
        "question": "Obwohl es kalt war, ___ er keine Mütze.",
        "options": ["trug", "er trug", "tragen", "hat getragen er"],
        "correct_index": 0,
        "explanation": {"ru": "После придаточного с obwohl главное предложение начинается с глагола (Inversion): trug er.", "en": "Main clause following 'obwohl' clause starts with verb: trug er."}
    },
    {
        "id": 39,
        "level": "A2",
        "topic": {"ru": "Модальный глагол + инфинитив в конце", "en": "Modal verb + infinitive in bracket structure"},
        "question": "Ich habe meinen Schlüssel verloren und kann ihn nicht ___.",
        "options": ["finden", "finde", "gefunden", "zu finden"],
        "correct_index": 0,
        "explanation": {"ru": "Модальный глагол kann требует чистый инфинитив смыслового глагола в конце предложения: finden.", "en": "Modal verb governs pure infinitive at the clause end: finden."}
    },
    {
        "id": 40,
        "level": "A2",
        "topic": {"ru": "Partizip II сильных глаголов", "en": "Past participle (Partizip II) of strong verbs"},
        "question": "Wir haben uns sehr lange nicht mehr ___.",
        "options": ["gesehen", "geseht", "sehen", "gesieht"],
        "correct_index": 0,
        "explanation": {"ru": "Форма Partizip II сильного глагола sehen - gesehen.", "en": "Past participle of strong verb 'sehen' is 'gesehen'."}
    },

    # =========================================================================
    # === БЛОК B1: СРЕДНИЙ / САМОСТОЯТЕЛЬНЫЙ УРОВЕНЬ (Вопросы 41 - 60) ========
    # =========================================================================
    {
        "id": 41,
        "level": "B1",
        "topic": {"ru": "Временные союзы в прошлом (als vs wenn)", "en": "Temporal conjunctions in the past (als vs wenn)"},
        "question": "___ ich ein Kind war, habe ich viel draußen gespielt.",
        "options": ["Als", "Wenn", "Wann", "Weil"],
        "correct_index": 0,
        "explanation": {"ru": "Для однократного периода или события в прошлом используется союз Als (когда).", "en": "For a single event or continuous period in the past, 'Als' (when) is required."}
    },
    {
        "id": 42,
        "level": "B1",
        "topic": {"ru": "Пассивный залог процесса (Vorgangspassiv)", "en": "Passive voice (Vorgangspassiv)"},
        "question": "Das neue Rathaus ___ gerade gebaut.",
        "options": ["wird", "ist", "hat", "wurde"],
        "correct_index": 0,
        "explanation": {"ru": "Настоящее время пассивного залога строится по схеме werden + Partizip II: wird gebaut.", "en": "Present passive is formed with 'werden' + Partizip II: wird gebaut."}
    },
    {
        "id": 43,
        "level": "B1",
        "topic": {"ru": "Сослагательное наклонение (Konjunktiv II)", "en": "Subjunctive mood (Konjunktiv II)"},
        "question": "Wenn ich mehr Geld ___, würde ich eine Weltreise machen.",
        "options": ["hätte", "habe", "hatte", "wäre"],
        "correct_index": 0,
        "explanation": {"ru": "Нереальное условие (если бы у меня было) выражается формой Konjunktiv II: hätte.", "en": "Hypothetical condition (if I had) requires Konjunktiv II: hätte."}
    },
    {
        "id": 44,
        "level": "B1",
        "topic": {"ru": "Относительные придаточные предложения с дательным падежом", "en": "Relative clauses with Dative case"},
        "question": "Das ist der Nachbar, ___ ich gestern beim Umzug geholfen habe.",
        "options": ["dem", "den", "der", "des"],
        "correct_index": 0,
        "explanation": {"ru": "Глагол helfen требует Dativ (helfen + Dativ). Мужской род в Dativ: dem.", "en": "Verb 'helfen' governs Dative. Masculine relative pronoun in Dative is 'dem'."}
    },
    {
        "id": 45,
        "level": "B1",
        "topic": {"ru": "Инфинитивный оборот um ... zu (целевой оборот)", "en": "Infinitive clause 'um ... zu' (purpose)"},
        "question": "Er lernt jeden Tag fleißig Deutsch, ___ eine gute Stelle zu finden.",
        "options": ["um", "damit", "für", "ohne"],
        "correct_index": 0,
        "explanation": {"ru": "Оборот um ... zu указывает на цель действия при совпадении субъектов: um zu finden.", "en": "Infinitive clause 'um ... zu' expresses purpose when subjects match."}
    },
    {
        "id": 46,
        "level": "B1",
        "topic": {"ru": "Предлог während + Родительный падеж (Genitiv)", "en": "Preposition 'während' + Genitive"},
        "question": "Während ___ Sommers habe ich ein Praktikum absolviert.",
        "options": ["des", "dem", "den", "der"],
        "correct_index": 0,
        "explanation": {"ru": "Предлог während управляет Genitiv. Мужской род der Sommer в Genitiv -> des Sommers.", "en": "Preposition 'während' governs Genitive: des Sommers."}
    },
    {
        "id": 47,
        "level": "B1",
        "topic": {"ru": "Прилагательные с предлогами (stolz auf + Akkusativ)", "en": "Adjectives with prepositions (stolz auf + Akk)"},
        "question": "Die Eltern sind sehr stolz ___ die Erfolge ihrer Kinder.",
        "options": ["auf", "über", "an", "für"],
        "correct_index": 0,
        "explanation": {"ru": "Конструкция 'гордиться чем-то': stolz sein auf + Akkusativ.", "en": "Expression 'to be proud of': stolz sein auf + Accusative."}
    },
    {
        "id": 48,
        "level": "B1",
        "topic": {"ru": "Пассивный залог в прошедшем времени (Präteritum Passiv)", "en": "Passive in simple past (Präteritum Passiv)"},
        "question": "Der wichtige Vertrag ___ gestern vom Direktor unterschrieben.",
        "options": ["wurde", "worden", "wird", "war"],
        "correct_index": 0,
        "explanation": {"ru": "Пассивный залог в Präteritum образуется с помощью wurde + Partizip II: wurde unterschrieben.", "en": "Past passive is formed with 'wurde' + Partizip II: wurde unterschrieben."}
    },
    {
        "id": 49,
        "level": "B1",
        "topic": {"ru": "Вежливая просьба с формой Konjunktiv II (könnten)", "en": "Polite requests with Konjunktiv II (könnten)"},
        "question": "___ Sie mir bitte das Salz reichen?",
        "options": ["Könnten", "Konnten", "Können", "Würden"],
        "correct_index": 0,
        "explanation": {"ru": "Вежливая просьба выражается формой Konjunktiv II от können: Könnten Sie bitte.", "en": "Polite request uses Konjunktiv II of 'können': Könnten Sie bitte."}
    },
    {
        "id": 50,
        "level": "B1",
        "topic": {"ru": "Относительные местоимения в Genitiv (deren)", "en": "Relative pronouns in Genitive (deren)"},
        "question": "Das ist die Kollegin, ___ Auto in der Garage steht.",
        "options": ["deren", "dessen", "der", "die"],
        "correct_index": 0,
        "explanation": {"ru": "Относительное местоимение женского рода в Genitiv (чья машина): deren Auto.", "en": "Feminine relative pronoun in Genitive is 'deren': deren Auto."}
    },
    {
        "id": 51,
        "level": "B1",
        "topic": {"ru": "Предлог trotz + Родительный падеж (Genitiv)", "en": "Preposition 'trotz' + Genitive"},
        "question": "Trotz ___ starken Regens gingen wir im Wald spazieren.",
        "options": ["des", "dem", "den", "der"],
        "correct_index": 0,
        "explanation": {"ru": "Предлог trotz требует Genitiv: trotz des starken Regens.", "en": "Preposition 'trotz' governs Genitive: trotz des starken Regens."}
    },
    {
        "id": 52,
        "level": "B1",
        "topic": {"ru": "Инфинитив с частицей zu", "en": "Infinitive with 'zu'"},
        "question": "Es ist wichtig, jeden Tag neue Wörter ___.",
        "options": ["zu lernen", "lernen", "gelernt", "zu gelernt"],
        "correct_index": 0,
        "explanation": {"ru": "Конструкция 'Es ist wichtig' требует инфинитива с zu: zu lernen.", "en": "Construction 'Es ist wichtig' governs infinitive with 'zu': zu lernen."}
    },
    {
        "id": 53,
        "level": "B1",
        "topic": {"ru": "Инфинитив с zu у глаголов с отделяемой приставкой", "en": "Infinitive with 'zu' in separable verbs"},
        "question": "Ich habe vor, morgen ganz früh ___.",
        "options": ["aufzustehen", "aufstehen", "zu aufstehen", "aufgestanden"],
        "correct_index": 0,
        "explanation": {"ru": "У глаголов с отделяемой приставкой частица -zu- вставляется между приставкой и корнем: auf-zu-stehen.", "en": "Separable verbs insert '-zu-' between prefix and stem: aufzustehen."}
    },
    {
        "id": 54,
        "level": "B1",
        "topic": {"ru": "Слабое склонение существительных (N-Deklination)", "en": "Weak noun declension (N-Deklination)"},
        "question": "Ich habe gestern mit einem netten ___ gesprochen.",
        "options": ["Herrn", "Herr", "Herren", "Herres"],
        "correct_index": 0,
        "explanation": {"ru": "Существительное der Herr относится к N-Deklination и во всех косвенных падежах единственного числа принимает окончание -n: mit dem Herrn.", "en": "Noun 'der Herr' belongs to weak declension and takes -n in singular oblique cases: dem Herrn."}
    },
    {
        "id": 55,
        "level": "B1",
        "topic": {"ru": "Причастие II в роли прилагательного (Partizip II als Adjektiv)", "en": "Participle II used as adjective"},
        "question": "Das vor kurzem ___ Haus sieht sehr modern aus.",
        "options": ["gebaute", "gebauten", "gebauter", "bauen"],
        "correct_index": 0,
        "explanation": {"ru": "Partizip II в роли определения среднего рода в Nominativ с определенным артиклем получает окончание -e: das gebaute Haus.", "en": "Participle II as neuter Nominative adjective takes ending -e: das gebaute Haus."}
    },
    {
        "id": 56,
        "level": "B1",
        "topic": {"ru": "Двойной союз je ... desto / umso (чем ... тем)", "en": "Correlative conjunction 'je ... desto'"},
        "question": "Je mehr man übt, ___ schneller lernt man die Sprache.",
        "options": ["desto", "denn", "als", "wie"],
        "correct_index": 0,
        "explanation": {"ru": "Парный союз: Je (чем) в придаточном ... desto / umso (тем) в главном предложении.", "en": "Correlative pair: 'Je' in subordinate ... 'desto / umso' in main clause."}
    },
    {
        "id": 57,
        "level": "B1",
        "topic": {"ru": "Придаточные с союзом ob (ли / косвенный вопрос)", "en": "Indirect questions with 'ob' (whether)"},
        "question": "Ich bin mir nicht sicher, ___ er morgen zur Konferenz kommt.",
        "options": ["ob", "dass", "wenn", "wann"],
        "correct_index": 0,
        "explanation": {"ru": "Неуверенность и вопрос без вопросительного слова выражаются союзом ob (придет ли он).", "en": "Uncertainty and yes/no indirect questions require 'ob' (whether)."}
    },
    {
        "id": 58,
        "level": "B1",
        "topic": {"ru": "Устойчивые глагольно-именные сочетания (Nomen-Verb-Verbindungen)", "en": "Noun-verb combinations (Nomen-Verb-Verbindungen)"},
        "question": "Wir müssen bis morgen eine wichtige Entscheidung ___.",
        "options": ["treffen", "machen", "tun", "geben"],
        "correct_index": 0,
        "explanation": {"ru": "Устойчивое сочетание 'принять решение': eine Entscheidung treffen.", "en": "Idiomatic collocation 'to make a decision': eine Entscheidung treffen."}
    },
    {
        "id": 59,
        "level": "B1",
        "topic": {"ru": "Относительные местоимения мужского/среднего рода в Genitiv (dessen)", "en": "Relative pronouns in Genitive masculine/neuter (dessen)"},
        "question": "Der Schriftsteller, ___ Buch ich gerade lese, kommt aus Wien.",
        "options": ["dessen", "deren", "dem", "den"],
        "correct_index": 0,
        "explanation": {"ru": "Относительное местоимение мужского рода в Genitiv (чью книгу я читаю): dessen Buch.", "en": "Masculine relative pronoun in Genitive is 'dessen'."}
    },
    {
        "id": 60,
        "level": "B1",
        "topic": {"ru": "Нереальное условие в прошлом (Konjunktiv II der Vergangenheit)", "en": "Past unreal conditional (Konjunktiv II past)"},
        "question": "Hätte ich den Wecker gehört, ___ ich nicht zu spät gekommen.",
        "options": ["wäre", "hätte", "würde", "war"],
        "correct_index": 0,
        "explanation": {"ru": "Нереальное условие в прошлом с глаголом движения (kommen) требует wäre + Partizip II: wäre ich nicht gekommen.", "en": "Past unreal condition with verb of motion requires 'wäre' + Partizip II."}
    }
]

# Быстрый индекс вопросов по ID
QUESTION_MAP: Dict[int, Dict[str, Any]] = {q["id"]: q for q in PLACEMENT_QUESTION_POOL}

# Первые 12 вопросов (4 A1, 4 A2, 4 B1) для обратной совместимости со старыми модулями/тестами
PLACEMENT_QUESTIONS: List[Dict[str, Any]] = PLACEMENT_QUESTION_POOL[:4] + PLACEMENT_QUESTION_POOL[20:24] + PLACEMENT_QUESTION_POOL[40:44]

def get_question_by_id(q_id: int) -> Dict[str, Any]:
    """Получить вопрос по его ID"""
    return QUESTION_MAP.get(q_id, PLACEMENT_QUESTION_POOL[0])

def generate_placement_session(
    count: int = 20,
    a1_count: int = 7,
    a2_count: int = 7,
    b1_count: int = 6
) -> List[Dict[str, Any]]:
    """
    Генерирует уникальную сбалансированную выборку из 20 вопросов:
    - 7 вопросов A1
    - 7 вопросов A2
    - 6 вопросов B1
    Вопросы внутри каждого уровня перемешиваются, но идут по возрастанию сложности (A1 -> A2 -> B1).
    При каждом новом старте теста пользователь получает свежий набор вопросов.
    """
    a1_pool = [q for q in PLACEMENT_QUESTION_POOL if q["level"] == "A1"]
    a2_pool = [q for q in PLACEMENT_QUESTION_POOL if q["level"] == "A2"]
    b1_pool = [q for q in PLACEMENT_QUESTION_POOL if q["level"] == "B1"]

    chosen_a1 = random.sample(a1_pool, min(a1_count, len(a1_pool)))
    chosen_a2 = random.sample(a2_pool, min(a2_count, len(a2_pool)))
    chosen_b1 = random.sample(b1_pool, min(b1_count, len(b1_pool)))

    return chosen_a1 + chosen_a2 + chosen_b1

def evaluate_placement_test(
    user_answers: List[int],
    question_ids: Optional[List[int]] = None,
    session_questions: Optional[List[Dict[str, Any]]] = None
) -> Tuple[str, int, Dict[str, Tuple[int, int]]]:
    """
    Рассчитывает уровень CEFR по ответам пользователя:
    - Если передан question_ids или session_questions, оценивает именно эту сессию (например, 20 вопросов).
    - Если ничего не передано, оценивает базовые PLACEMENT_QUESTIONS (12 вопросов) для обратной совместимости.

    Возвращает:
    - result_level: 'A1', 'A2' или 'B1'
    - total_score: общее число правильных ответов
    - level_breakdown: статистика по подуровням { 'A1': (correct, total), ... }
    """
    if session_questions:
        questions = session_questions
    elif question_ids:
        questions = [get_question_by_id(qid) for qid in question_ids]
    else:
        questions = PLACEMENT_QUESTIONS

    total_score = 0
    breakdown = {
        "A1": [0, 0],
        "A2": [0, 0],
        "B1": [0, 0]
    }

    for idx, q in enumerate(questions):
        lvl = q["level"]
        breakdown[lvl][1] += 1
        if idx < len(user_answers) and user_answers[idx] == q["correct_index"]:
            total_score += 1
            breakdown[lvl][0] += 1

    level_dict = {
        k: (v[0], v[1]) for k, v in breakdown.items()
    }

    total_questions = len(questions)

    # Градация уровней CEFR
    if total_questions >= 20:
        # Для расширенного теста из 20 вопросов:
        # >= 15 правильных (75%+): B1
        # 9 - 14 правильных (45% - 74%): A2
        # < 9 правильных (<45%): A1
        if total_score >= 15:
            result_level = "B1"
        elif total_score >= 9:
            result_level = "A2"
        else:
            result_level = "A1"
    else:
        # Для стандартного теста из 12 вопросов (обратная совместимость):
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
                "tip": "Подключай тренажер экзаменационных писем A2 и регулярный диалог с ИИ-Аистом."
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
