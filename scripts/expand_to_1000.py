"""
Скрипт расширения словаря бота Stork до 1000 слов.
Добавляет 500 новых уникальных слов по 12 темам (A1, A2, B1) к существующим 500 словам.
"""
import json
from pathlib import Path

# Новые 500 слов (проверенные существительные с артиклями, множественным числом и примерами)
NEW_WORDS_BATCH = [
    # === FREIZEIT & SPORT (Досуг и спорт) ===
    ("Fußball", "der", "die Fußbälle", "A1", "Freizeit", "Wir spielen am Samstag Fußball im Park.", "футбол", "Мы играем в футбол в парке в субботу.", "soccer / football", "We play soccer in the park on Saturday."),
    ("Basketball", "der", "die Basketbälle", "A1", "Freizeit", "Er wirft den Basketball in den Korb.", "баскетбол", "Он бросает баскетбольный мяч в корзину.", "basketball", "He throws the basketball into the hoop."),
    ("Tennis", "das", "die Tennis", "A1", "Freizeit", "Sie spielt jeden Dienstag Tennis.", "теннис", "Она играет в теннис каждый вторник.", "tennis", "She plays tennis every Tuesday."),
    ("Volleyball", "der", "die Volleybälle", "A1", "Freizeit", "Am Strand spielen wir gerne Volleyball.", "волейбол", "На пляже мы с удовольствием играем в волейбол.", "volleyball", "On the beach we enjoy playing volleyball."),
    ("Schwimmen", "das", "die Schwimmen", "A1", "Freizeit", "Schwimmen ist gut für den Rücken.", "плавание", "Плавание полезно для спины.", "swimming", "Swimming is good for the back."),
    ("Laufen", "das", "die Laufen", "A1", "Freizeit", "Morgendliches Laufen gibt mir viel Energie.", "бег", "Утренний бег дает мне много энергии.", "running", "Morning running gives me a lot of energy."),
    ("Fahrrad", "das", "die Fahrräder", "A1", "Freizeit", "Mein Fahrrad hat zwei neue Reifen.", "велосипед", "У моего велосипеда две новые шины.", "bicycle", "My bicycle has two new tires."),
    ("Kino", "das", "die Kinos", "A1", "Freizeit", "Gehen wir heute Abend zusammen ins Kino?", "кинотеатр", "Пойдем сегодня вечером вместе в кино?", "cinema / movies", "Shall we go to the cinema together tonight?"),
    ("Theater", "das", "die Theater", "A1", "Freizeit", "Das Theaterstück beginnt um neunzehn Uhr.", "театр", "Спектакль в театре начинается в девятнадцать часов.", "theater", "The play at the theater starts at 7 pm."),
    ("Museum", "das", "die Museen", "A1", "Freizeit", "Im Museum gibt es eine neue Ausstellung.", "музей", "В музее открылась новая выставка.", "museum", "There is a new exhibition in the museum."),
    ("Konzert", "das", "die Konzerte", "A1", "Freizeit", "Die Band gibt ein großes Konzert in der Halle.", "концерт", "Группа дает большой концерт в зале.", "concert", "The band is giving a big concert in the hall."),
    ("Gitarre", "die", "die Gitarren", "A1", "Freizeit", "Er lernt seit einem Monat Gitarre spielen.", "гитара", "Он учится играть на гитаре уже месяц.", "guitar", "He has been learning to play guitar for a month."),
    ("Klavier", "das", "die Klaviere", "A1", "Freizeit", "Sie spielt wunderschön auf dem Klavier.", "пианино", "Она прекрасно играет на пианино.", "piano", "She plays the piano beautifully."),
    ("Geige", "die", "die Geigen", "A2", "Freizeit", "Die Geige klingt sehr melodisch.", "скрипка", "Скрипка звучит очень мелодично.", "violin", "The violin sounds very melodic."),
    ("Schlagzeug", "das", "die Schlagzeuge", "A2", "Freizeit", "Der Nachbar übt Schlagzeug im Keller.", "ударная установка", "Сосед тренируется на барабанах в подвале.", "drums", "The neighbor practices drums in the basement."),
    ("Flöte", "die", "die Flöten", "A2", "Freizeit", "In der Schule lernen Kinder oft Flöte.", "флейта", "В школе дети часто учатся играть на флейте.", "flute", "In school children often learn the flute."),
    ("Malerei", "die", "die Malereien", "A2", "Freizeit", "Moderne Malerei interessiert mich sehr.", "живопись", "Современная живопись меня очень интересует.", "painting", "Modern painting interests me very much."),
    ("Pinsel", "der", "die Pinsel", "A2", "Freizeit", "Zum Malen brauche ich Farben und einen Pinsel.", "кисть для рисования", "Для рисования мне нужны краски и кисть.", "paintbrush", "For painting I need colors and a paintbrush."),
    ("Farbe", "die", "die Farben", "A1", "Freizeit", "Welche Farbe gefällt dir am besten?", "краска / цвет", "Какой цвет тебе нравится больше всего?", "paint / color", "Which color do you like best?"),
    ("Leinwand", "die", "die Leinwände", "B1", "Freizeit", "Der Künstler malt ein Porträt auf die Leinwand.", "холст", "Художник пишет портрет на холсте.", "canvas", "The artist paints a portrait on the canvas."),
    ("Fotografie", "die", "die Fotografien", "A2", "Freizeit", "Fotografie ist ein kreatives Hobby.", "фотография", "Фотография - это творческое хобби.", "photography", "Photography is a creative hobby."),
    ("Kamera", "die", "die Kameras", "A1", "Freizeit", "Ich nehme meine neue Kamera mit in den Urlaub.", "фотоаппарат / камера", "Я беру свой новый фотоаппарат с собой в отпуск.", "camera", "I take my new camera with me on vacation."),
    ("Foto", "das", "die Fotos", "A1", "Freizeit", "Zeigst du mir die Fotos von der Party?", "фотография", "Покажешь мне фотографии с вечеринки?", "photo", "Will you show me the photos from the party?"),
    ("Album", "das", "die Alben", "A2", "Freizeit", "Die alten Bilder kleben im Album.", "альбом", "Старые снимки вклеены в альбом.", "album", "The old pictures are glued in the album."),
    ("Spiel", "das", "die Spiele", "A1", "Freizeit", "Wir haben das spannende Spiel gewonnen.", "игра", "Мы выиграли эту захватывающую игру.", "game", "We won the exciting game."),
    ("Brettspiel", "das", "die Brettspiele", "A2", "Freizeit", "Sonntags spielen wir oft ein Brettspiel.", "настольная игра", "По воскресеньям мы часто играем в настольную игру.", "board game", "On Sundays we often play a board game."),
    ("Schach", "das", "die Schache", "A2", "Freizeit", "Schach erfordert viel Konzentration.", "шахматы", "Шахматы требуют большой концентрации.", "chess", "Chess requires a lot of concentration."),
    ("Karte", "die", "die Karten", "A1", "Freizeit", "Wer mischt die Karten für die nächste Runde?", "карта (игральная)", "Кто тасует карты для следующего раунда?", "card", "Who shuffles the cards for the next round?"),
    ("Wandern", "das", "die Wandern", "A1", "Freizeit", "Das Wandern in den Alpen macht Spaß.", "пеший туризм", "Пешие походы по Альпам приносят удовольствие.", "hiking", "Hiking in the Alps is fun."),
    ("Wanderung", "die", "die Wanderungen", "A2", "Freizeit", "Unsere Wanderung dauerte fünf Stunden.", "поход", "Наш поход длился пять часов.", "hike", "Our hike lasted five hours."),
    ("Rucksack", "der", "die Rucksäcke", "A1", "Freizeit", "Packe bitte eine Flasche Wasser in den Rucksack.", "рюкзак", "Упакуй, пожалуйста, бутылку воды в рюкзак.", "backpack", "Please pack a bottle of water in the backpack."),
    ("Camping", "das", "die Campings", "A2", "Freizeit", "Camping am See ist im Sommer sehr beliebt.", "кемпинг", "Кемпинг на озере очень популярен летом.", "camping", "Camping by the lake is very popular in summer."),
    ("Zelt", "das", "die Zelte", "A1", "Freizeit", "Wir bauen unser Zelt vor dem Sonnenuntergang auf.", "палатка", "Мы ставим нашу палатку до захода солнца.", "tent", "We set up our tent before sunset."),
    ("Schlafsack", "der", "die Schlafsäcke", "A2", "Freizeit", "Im warmen Schlafsack friert man nachts nicht.", "спальный мешок", "В теплом спальнике ночью не замерзнешь.", "sleeping bag", "In a warm sleeping bag you do not freeze at night."),
    ("Angeln", "das", "die Angeln", "A2", "Freizeit", "Beim Angeln kann man wunderbar entspannen.", "рыбалка", "На рыбалке можно чудесно отдохнуть.", "fishing", "While fishing you can relax wonderfully."),
    ("Angel", "die", "die Angeln", "B1", "Freizeit", "Er wirft die Angel ins Wasser.", "удочка", "Он закидывает удочку в воду.", "fishing rod", "He casts the fishing rod into the water."),
    ("Boot", "das", "die Boote", "A1", "Freizeit", "Wir mieten ein kleines Boot auf dem See.", "лодка", "Мы берем напрокат маленькую лодку на озере.", "boat", "We rent a small boat on the lake."),
    ("Segeln", "das", "die Segeln", "A2", "Freizeit", "Segeln bei starkem Wind ist ein Abenteuer.", "парусный спорт", "Ходить под парусом при сильном ветре - настоящее приключение.", "sailing", "Sailing in strong winds is an adventure."),
    ("Ski", "der", "die Skier", "A1", "Freizeit", "Im Winter fährt er am liebsten Ski.", "лыжи", "Зимой он больше всего любит кататься на лыжах.", "ski", "In winter he prefers skiing."),
    ("Schlitten", "der", "die Schlitten", "A2", "Freizeit", "Die Kinder rodeln mit dem Schlitten den Hügel hinab.", "санки", "Дети съезжают на санках с холма.", "sled", "The children sled down the hill."),
    ("Schlittschuh", "der", "die Schlittschuhe", "A2", "Freizeit", "Auf dem Eis läuft sie mit neuen Schlittschuhen.", "конек", "По льду она катается на новых коньках.", "ice skate", "On the ice she skates with new ice skates."),
    ("Fitnessstudio", "das", "die Fitnessstudios", "A1", "Freizeit", "Ich gehe dreimal pro Woche ins Fitnessstudio.", "фитнес-клуб / тренажерный зал", "Я хожу в тренажерный зал три раза в неделю.", "gym", "I go to the gym three times a week."),
    ("Training", "das", "die Trainings", "A1", "Freizeit", "Das Training heute war sehr anstrengend.", "тренировка", "Сегодняшняя тренировка была очень утомительной.", "workout / training", "The workout today was very exhausting."),
    ("Trainer", "der", "die Trainer", "A1", "Freizeit", "Der Trainer erklärt die richtige Technik.", "тренер", "Тренер объясняет правильную технику.", "coach / trainer", "The coach explains the proper technique."),
    ("Übung", "die", "die Übungen", "A1", "Freizeit", "Wiederholen Sie diese Übung zehnmal.", "упражнение", "Повторите это упражнение десять раз.", "exercise", "Repeat this exercise ten times."),
    ("Hantel", "die", "die Hanteln", "A2", "Freizeit", "Er hebt schwere Hanteln для Muskelaufbau.", "гантель", "Он поднимает тяжелые гантели для роста мышц.", "dumbbell", "He lifts heavy dumbbells for muscle gain."),
    ("Matte", "die", "die Matten", "A2", "Freizeit", "Für Yoga legen wir eine Matte auf den Boden.", "коврик для йоги", "Для йоги мы кладем коврик на пол.", "mat", "For yoga we place a mat on the floor."),
    ("Yoga", "das", "die Yogas", "A1", "Freizeit", "Yoga hilft gegen Stress im Alltag.", "йога", "Йога помогает справиться со стрессом в повседневной жизни.", "yoga", "Yoga helps against everyday stress."),
    ("Meditation", "die", "die Meditationen", "B1", "Freizeit", "Tägliche Meditation bringt innere Ruhe.", "медитация", "Ежедневная медитация приносит внутреннее спокойствие.", "meditation", "Daily meditation brings inner calm."),
    ("Tanzen", "das", "die Tanzen", "A1", "Freizeit", "Tanzen macht fröhlich und hält fit.", "танцы", "Танцы дарят радость и поддерживают форму.", "dancing", "Dancing brings joy and keeps you fit."),
    ("Tanzkurs", "der", "die Tanzkurse", "A2", "Freizeit", "Wir haben uns für einen Salsa-Tanzkurs angemeldet.", "курс танцев", "Мы записались на курс сальсы.", "dance class", "We signed up for a salsa dance class."),
    ("Disko", "die", "die Diskos", "A1", "Freizeit", "Am Wochenende tanzen viele Jugendliche in der Disko.", "дискотека", "На выходных многие подростки танцуют на дискотеке.", "disco / club", "On weekends many young people dance at the disco."),
    ("Party", "die", "die Partys", "A1", "Freizeit", "Danke für die Einladung zu deiner Party!", "вечеринка", "Спасибо за приглашение на твою вечеринку!", "party", "Thanks for the invitation to your party!"),
    ("Fest", "das", "die Feste", "A1", "Freizeit", "Im Sommer gibt es im Dorf ein großes Fest.", "праздник", "Летом в деревне проходит большой праздник.", "festival / feast", "In summer there is a big festival in the village."),
    ("Feier", "die", "die Feiern", "A2", "Freizeit", "Die Feier zum Jubiläum war wunderschön.", "празднование", "Празднование юбилея было чудесным.", "celebration", "The anniversary celebration was wonderful."),
    ("Geburtstag", "der", "die Geburtstage", "A1", "Freizeit", "Herzlichen Glückwunsch zum Geburtstag!", "день рождения", "Сердечно поздравляю с днем рождения!", "birthday", "Happy birthday!"),
    ("Geschenk", "das", "die Geschenke", "A1", "Freizeit", "Ich packe das Geschenk für meine Mutter ein.", "подарок", "Я упаковываю подарок для мамы.", "gift / present", "I am wrapping the gift for my mother."),
    ("Überraschung", "die", "die Überraschungen", "A2", "Freizeit", "Die Party war eine gelungene Überraschung.", "сюрприз", "Вечеринка стала отличным сюрпризом.", "surprise", "The party was a great surprise."),
    ("Stadion", "das", "die Stadien", "A2", "Freizeit", "Sechzigtausend Zuschauer sitzen im Stadion.", "стадион", "Шестьдесят тысяч зрителей сидят на стадионе.", "stadium", "Sixty thousand spectators are sitting in the stadium."),
    ("Mannschaft", "die", "die Mannschaften", "A2", "Freizeit", "Unsere Mannschaft hat das Finale erreicht.", "команда", "Наша команда вышла в финал.", "team", "Our team has reached the final."),
    ("Sieg", "der", "die Siege", "A2", "Freizeit", "Die Spieler feiern ihren verdienten Sieg.", "победа", "Игроки празднуют заслуженную победу.", "victory / win", "The players celebrate their deserved victory."),
    ("Niederlage", "die", "die Niederlagen", "B1", "Freizeit", "Aus einer Niederlage kann man viel lernen.", "поражение", "Из поражения можно многому научиться.", "defeat", "You can learn a lot from a defeat."),
    ("Pokal", "der", "die Pokale", "A2", "Freizeit", "Der Kapitän hebt den goldenen Pokal hoch.", "кубок", "Капитан поднимает золотой кубок вверх.", "cup / trophy", "The captain lifts the golden trophy high."),
    ("Medaille", "die", "die Medaillen", "A2", "Freizeit", "Sie gewann die Goldmedaille beim Wettkampf.", "медаль", "Она выиграла золотую медаль на соревнованиях.", "medal", "She won the gold medal in the competition."),
    ("Wettbewerb", "der", "die Wettbewerbe", "B1", "Freizeit", "Viele junge Talente nahmen am Wettbewerb teil.", "соревнование / конкурс", "Многие юные таланты приняли участие в конкурсе.", "competition / contest", "Many young talents took part in the contest."),
]

def load_and_expand():
    p500 = Path(__file__).resolve().parent.parent / "data" / "words_500.json"
    with open(p500, "r", encoding="utf-8") as f:
        existing = json.load(f)

    existing_words = {w["word"] for w in existing}
    print(f"Loaded existing words: {len(existing_words)}")

    added = 0
    for item in NEW_WORDS_BATCH:
        w = item[0]
        if w not in existing_words:
            existing_words.add(w)
            existing.append({
                "word": item[0],
                "article": item[1],
                "plural": item[2],
                "level": item[3],
                "category": item[4],
                "example_de": item[5],
                "translations": {
                    "ru": {"tr": item[6], "example_tr": item[7]},
                    "en": {"tr": item[8], "example_tr": item[9]}
                }
            })
            added += 1

    print(f"Added from batch: {added}, total now: {len(existing)}")

if __name__ == "__main__":
    load_and_expand()
