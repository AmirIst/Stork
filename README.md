<p align="center">
  <img src="logo.jpg" alt="Stork Bot Logo" width="160" style="border-radius: 50%;">
</p>

<h1 align="center">Stork: AI-Powered German Language Tutor</h1>

<p align="center">
  <b>A modern, asynchronous Telegram bot for learning German featuring AI tutoring (Google Gemini), Anki-style spaced repetition, and grammar drills.</b>
</p>

<p align="center">
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://docs.aiogram.dev"><img src="https://img.shields.io/badge/Framework-Aiogram_3.31-informational?logo=telegram" alt="Aiogram 3"></a>
  <a href="https://ai.google.dev"><img src="https://img.shields.io/badge/AI_Engine-Google_Gemini_2.5_Flash-orange?logo=google" alt="Google Gemini"></a>
  <a href="https://sqlite.org"><img src="https://img.shields.io/badge/Database-SQLite_aiosqlite-lightgrey?logo=sqlite" alt="SQLite"></a>
  <a href="https://www.docker.com"><img src="https://img.shields.io/badge/Container-Docker_Ready-2496ED?logo=docker&logoColor=white" alt="Docker"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License"></a>
</p>

---

## 📖 Overview

**Stork** is an interactive language-learning Telegram bot designed to help learners break through the language barrier in German. By combining conversational AI with proven spaced-repetition memory mechanics, Stork provides an engaging, personalized learning experience directly in Telegram.

Whether practicing essential noun genders (*der, die, das*), training vocabulary using active recall flashcards, or engaging in contextual conversation with the AI tutor, Stork makes daily language learning intuitive and habit-forming.

---

## ✨ Key Features

### 🎙️ 1. Neural Voice Mode & Speech Recognition (edge-tts + Gemini Multimodal)
- **High-Definition Audio Pronunciation**: Studio-grade German pronunciation (`de-DE-KillianNeural`) for every word card, article drill, quiz, and AI conversation.
- **Voice-to-Voice AI Practice**: Students can speak directly to Stork via Telegram voice messages. The AI transcribes the speech, assesses phonetics and grammar, and responds in text with spoken German audio.
- **One-Tap Voice Buttons**: Tap `[ 🔊 Listen ]` under any card, quiz result, or AI reply to hear authentic German Hochdeutsch pronunciation.

### 🤖 2. Contextual AI Tutor with Dynamic Model Cascade
- **Sub-1.5s Latency & Memory Persistence**: Multi-turn conversation history stored in SQLite with resume/clear dialog controls.
- **Dynamic Failover Cascade**: Automatically routes requests across Google's fastest models (`gemini-3.5-flash-lite`, `gemini-3.5-flash`, `gemini-2.5-flash-lite`, `gemini-2.5-flash`) to ensure zero rate limit downtime.
- **Universal 4-Block Tutoring Format**: Any input in English, Russian, or other languages receives: (1) Natural German translation, (2) Vocabulary insight, (3) German response with translation, and (4) Practice follow-up question.

### 🧠 3. Spaced Repetition Flashcards (Anki-Style)
- **Active Recall**: Hidden translations with toggle-to-reveal cards, complete with plural forms and contextual usage examples.
- **Three-Tier Evaluation**: Rate retention with `[ 🔴 Don't Know ]`, `[ 🟡 Review ]`, or `[ 🟢 Know ]`.
- **Progress Tracking**: Every interaction updates the user's mastery level in a persistent asynchronous SQLite database.

### 📚 4. Curated 1,000-Word Vocabulary & Topic Filters
- **12 Real-Life Categories**: Food, Home, City & Transport, People & Family, Work, Study, Clothing, Health, Travel, Nature, Time, and Leisure.
- **CEFR Difficulty Levels**: Words tagged across `A1` (554 words), `A2` (399 words), and `B1` (47 words).
- **Dynamic Filters**: Learners can select specific difficulty levels or topics directly from the main menu.

### 🎯 5. German Gender Trainer (`der`, `die`, `das`)
- Interactive drills for mastering tricky German noun genders.
- Immediate visual feedback, audio pronunciation, and streak counters (🔥) to encourage daily practice.

### 📝 6. Translation Quiz
- Multiple-choice questions with 4 dynamically generated distractors and audio playback for rapid vocabulary consolidation.

### 🌐 7. Extensible Multi-Language Architecture (i18n)
- Clean, decoupled localization system powered by JSON dictionary catalogs (`locales/en.json`, `locales/ru.json`).
- Adding a new UI language takes under two minutes without touching core business logic.

---

## 🛠 Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Language** | Python 3.11+ | Modern, strongly-typed asynchronous Python |
| **Telegram Framework** | Aiogram 3.31 | High-performance asynchronous Telegram Bot API framework |
| **Database** | SQLite + `aiosqlite` | Non-blocking asynchronous persistence for progress and metrics |
| **AI / LLM** | Google Gemini API (`gemini-2.5-flash`) | Low-latency natural language processing and grammar analysis |
| **HTTP Client** | `httpx` | Asynchronous REST client for Gemini API endpoints |
| **Containerization** | Docker, Docker Compose | Production-ready multi-platform container setup |

---

## 📂 Project Structure

```text
Stork/
├── data/
│   └── words_500.json         # Curated 500-word dataset categorized by CEFR level & topic
├── database/
│   ├── db.py                  # Asynchronous SQLite connection manager, migrations & CRUD
│   └── words_data.py          # Initial database seeder for dictionary entries
├── handlers/
│   ├── ai_chat.py             # AI conversational tutor handler
│   ├── articles.py            # Article trainer (der/die/das)
│   ├── cards.py               # Flashcard repetition (Anki mechanic)
│   ├── filters.py             # Level & topic selection keyboards
│   ├── quiz.py                # Multiple-choice translation test
│   └── common.py              # Main menu navigation and user statistics
├── keyboards/
│   └── inline.py              # Reusable dynamic inline keyboard builders
├── locales/
│   ├── en.json                # English language localization bundle
│   ├── ru.json                # Russian language localization bundle
│   └── manager.py             # Locale manager and string interpolation service
├── services/
│   └── ai_tutor.py            # Gemini API client with prompt engineering guardrails
├── bot.py                     # Bot entrypoint & dispatcher orchestration
├── config.py                  # Configuration loader and environment validator
├── docker-compose.yml         # Container orchestration with volume persistence
├── Dockerfile                 # Multi-stage production container image
├── deploy.sh                  # One-click deployment script for Linux servers
├── requirements.txt           # Production dependencies
└── logo.jpg                   # Bot branding avatar
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11 or higher (or Docker)
- Telegram Bot Token (obtain from [@BotFather](https://t.me/BotFather))
- Google Gemini API Key (obtain from [Google AI Studio](https://aistudio.google.com/))

### 1. Clone the repository
```bash
git clone https://github.com/AmirIst/Stork.git
cd Stork
```

### 2. Configure environment variables
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Populate your credentials inside `.env`:
```env
BOT_TOKEN=your_telegram_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Run with Docker (Recommended)
```bash
docker-compose up -d --build
```

### 4. Or run locally
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the bot
python bot.py
```

---

## 🔒 Security & Privacy

- All API keys and authentication credentials are strictly isolated in `.env` and excluded from version control via `.gitignore`.
- Database volumes are persisted locally or mapped via Docker volumes, preventing sensitive user data leakage.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Created with ❤️ by <a href="https://github.com/AmirIst">AmirIst</a>
</p>
