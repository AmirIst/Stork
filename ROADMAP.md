# 🗺️ Stork German Tutor: Product Roadmap & Commercialization Strategy

This document outlines the strategic product vision, feature backlog, monetization mechanics, and engineering milestones for transforming **Stork** into a production-grade commercial Telegram EdTech product.

---

## 🎯 Strategic Vision & Value Proposition

- **Core Goal**: Provide an accessible, habit-forming AI German tutor directly in Telegram that replaces expensive private tutoring for A1-B1 learners and test takers.
- **Target Audience**: 
  - Expats, students, and professionals moving to DACH countries (Germany, Austria, Switzerland).
  - Test candidates preparing for Goethe-Zertifikat, Telc (A1, A2, B1), and TestDaF.
  - Beginners seeking speaking confidence and noun gender mastery.
- **Commercial Model**: Freemium subscription powered by Telegram Stars and direct card payments.

---

## 📋 Feature Breakdown & Development Phases

### Phase 1: Core Experience & Conversational Memory (Current Priority)
- [ ] **Multi-Turn AI Context Memory**:
  - Implement rolling conversation buffer (last 8-10 turns) persisted in SQLite.
  - Enable Stork to remember learner preferences, ongoing topics, and recently corrected mistakes.
  - Add `/reset` or inline button to start a fresh conversation topic.
- [ ] **Vocabulary Expansion (1,000 Free Words)**:
  - Scale database from 500 to 1,000 curated nouns with gender, plurals, IPA, and contextual sentences.
  - Cover full A1-B1 core vocabulary across 12 daily life categories.
  - Fully accessible to all users for free to maximize user acquisition.

### Phase 2: Audio & Voice Mode (The "Killer" Feature)
- [ ] **Text-to-Speech (Natural German Voice Output)**:
  - Integrate neural German speech synthesis (`edge-tts` with native voices like Katja and Conrad).
  - Voice message responses from Stork for conversational realism.
  - Audio pronunciation preview button on flashcards and vocabulary lists.
- [ ] **Speech-to-Text & Pronunciation Feedback**:
  - Accept learner voice messages (`.ogg` Telegram voice notes).
  - Transcribe and evaluate pronunciation with Gemini Multimodal audio API.
  - Highlight mispronounced phonemes (e.g., "ch", umlauts "ä/ö/ü", "r").

### Phase 3: Exam Preparation Simulator (High-Monetization Module)
- [ ] **Goethe / Telc "Schreiben" (Writing) Trainer**:
  - Automated prompts matching real exam tasks (formal/informal letters, complaints, RSVPs, 30-80 words).
  - Multi-criteria AI grading: Task Completion, Coherence & Structure, Vocabulary Range, and Grammar Accuracy.
  - Detailed error markup with model answers and tips for improvement.
- [ ] **Oral Exam "Sprechen" Simulator**:
  - Turn-by-turn voice dialog simulating Part 1 (Introduction), Part 2 (Information exchange), and Part 3 (Joint planning).

### Phase 4: Diagnostic Level Test (Viral Acquisition Loop)
- [ ] **15-Question Adaptive Placement Test**:
  - Quick 3-minute diagnostic test evaluating grammar, vocabulary, and sentence structure.
  - Visual shareable result card (CEFR score, e.g., "A2.1 Intermediate Beginner").
  - Personalized learning plan based on test diagnosis.

### Phase 5: Monetization & Growth Infrastructure
- [ ] **Tiered Access & Usage Quotas**:
  - **Free Tier**: Full 1,000 words vocabulary, unlimited der/die/das drills, 5 AI messages per day.
  - **Stork Pro**: Unlimited AI dialogs, full voice mode, exam writing trainer, and advanced analytics.
- [ ] **Telegram Stars Integration**:
  - In-app 1-tap checkout via Telegram Bot Payments API (`createInvoiceLink`, Telegram Stars).
- [ ] **Social Media Acquisition Engine**:
  - Short-form content hooks (Instagram Reels / TikTok / YouTube Shorts) targeting common German language pains with direct deep-links to Stork.
