# Akon Product Vision

## Product identity

Akon is a real-time AI memory companion.

The product starts as a web-based AI companion, but the long-term direction is bigger:
Akon should become a privacy-first human memory augmentation platform that helps people
remember, understand, translate, learn, and respond in daily life.

## Core problem

People are surrounded by too much information.

They read, study, attend meetings, hear instructions, talk to people, watch videos, and
consume knowledge every day, but they still forget important details. Modern AI can answer
questions and perform tasks, but most AI tools are still separate from the user's real
daily context.

Akon should close that gap.

## Core promise

Akon helps users carry useful intelligence with them.

It should help a person:

- Remember what matters.
- Recall what they studied.
- Organize personal knowledge.
- Translate unfamiliar language.
- Prepare answers during conversations.
- Understand complex topics quickly.
- Keep approved personal context under user control.
- Learn in a way that improves retention.

## Long-term product direction

Akon should evolve through these stages:

### Phase 1: Web AI companion

- Text chat
- Account system
- Conversation history
- Memory approval
- Saved memory
- Gemini provider integration
- Feedback and reflection

### Phase 2: Human memory core

- Better memory categories
- Better recall
- Study retention support
- User-approved knowledge vault
- Personal context ranking
- Review prompts
- "Help me remember this" workflows

### Phase 3: Voice companion

- Speech-to-text
- Text-to-speech
- Push-to-talk
- Voice replies
- Voice-safe response style
- Short spoken answers

### Phase 4: Real-time assist mode

- Listen only when the user activates it
- Summarize what was said
- Explain unclear phrases
- Suggest short answers
- Avoid always-on surveillance behavior

### Phase 5: Real-time translation

- Detect language
- Translate speech
- Simplify meaning
- Provide fast, natural explanations
- Keep translation mode privacy-controlled

### Phase 6: Wearable-ready API

Potential interfaces:

- Earpiece
- Wristwatch
- Smart glasses
- Mobile app
- Desktop app
- Dedicated wearable device

The intelligence should live in the Akon platform, while devices act as access points.

### Phase 7: Akon device

A comfortable wearable device could let users activate Akon wherever they are and receive
private spoken assistance in real time.

## Privacy principles

Akon must not become a spying product.

Core rules:

- No silent recording.
- No always-on listening without explicit user control.
- Activation-based listening only.
- Clear recording indicators.
- User approval before sensitive memory is saved.
- Easy memory review, edit, revoke, and delete.
- Strong encryption in future production architecture.
- Transparent logs for important memory actions.

## Product position

Akon is not merely a chatbot.

Akon is:

- A memory companion.
- A learning companion.
- A recall assistant.
- A translation assistant.
- A real-time thinking partner.
- A future wearable intelligence layer.

## Working tagline options

- Akon — Your Real-Time AI Memory Companion
- Akon — Remember More. Understand Faster.
- Akon — Intelligence You Can Carry
- Akon — Your Second Memory for Daily Life
- Akon — Private AI for Memory, Learning, and Real-Time Understanding

## Current milestone

v0.5.4 introduces Study Retention Mode on top of memory recall workflows.

The goal is not to build wearable hardware yet. The goal is to align the product identity,
system behavior, frontend language, and documentation with the long-term memory companion
vision.

## v0.5.3 Memory Recall Workflows

This milestone strengthens Akon's memory behavior without adding new database tables.

Added direction:

- Akon should recognize recall-style messages such as "what do you remember about..." and "remind me about..."
- Akon should handle "help me remember this" as an explicit memory candidate.
- Study notes, people, projects, decisions, facts, and language context are now treated as stronger memory categories.
- High-sensitivity memory should not be broadly surfaced unless the user's recall query overlaps that memory.
- Recall responses should be honest when saved memory is not enough.

## v0.5.4 Study Retention Mode

This milestone makes Akon more useful for learners.

Added direction:

- Akon can detect study, revision, practice, quiz, and retention requests.
- Akon can respond with a structured learning loop: understand, compress, recall, quiz, and save.
- Akon should help users actively recall information instead of only reading explanations.
- Akon should suggest study-note memories only after the user approves saving.
- This prepares Akon for stronger student workflows and future voice-based recall practice.
