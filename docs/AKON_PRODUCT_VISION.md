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

v0.5.6 introduces a consent-first Study Note Approval Flow.

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

## v0.5.5 Study Session UI

This milestone makes Study Retention Mode visible in the product interface.

Added direction:

- The empty chat state now presents study-session controls.
- The right context panel now includes a retention loop card.
- Study-mode replies receive visual treatment so users can recognize learning sessions quickly.
- The workspace now surfaces study-session activity as part of the top metrics.
- This prepares Akon for a richer learning workspace with session tracking, progress, quizzes, and saved study notes.

## v0.5.6 Study Note Approval Flow

This milestone connects Study Retention Mode to Akon's consent-controlled
memory system.

Added direction:

- Users can request a study note from the recent lesson.
- Akon derives the candidate from its latest substantive teaching response.
- Raw Markdown is cleaned before the candidate is displayed.
- The Memory panel opens automatically when a study note is ready.
- The candidate is never saved silently.
- Users must review and approve the study note before persistence.
- Crisis and high-risk safety flows remain excluded from memory extraction.


## v0.5.7 Persistent Conversation Continuity and Recovery

This milestone makes conversation history a dependable product capability
rather than a temporary sidebar view.

- Complete message threads remain stored on the backend.
- Conversation summaries include message counts and latest-message previews.
- History is ordered by recent persisted activity.
- Active-conversation recovery is isolated per authenticated user.
- Refreshing or signing back in restores the most recent valid conversation.
- Invalid or deleted recovery IDs are removed safely.
- Cancelled and failed optimistic messages do not remain as false chat history.
- Switching conversations cancels incompatible in-progress generation.
- Production requires persistent PostgreSQL storage.

## v0.6.0 Explainable Memory Intelligence and Control

This milestone turns Akon's memory retrieval from hidden prompt plumbing into a
transparent, consent-aware product capability.

- Users can preview which active memories match a query before involving the AI.
- Every selected memory includes a relevance score and human-readable reasons.
- Revoked memory is excluded from retrieval.
- High-sensitivity memory requires direct topic overlap before it can be recalled.
- Memory Health surfaces implicit consent, low confidence, sensitive records,
  duplicates, and memories recommended for review.
- Audit logs record memory IDs and counts without recording private memory content.

### Stage 2 — Live provenance and Memory Control Center

- Chat responses return the exact consent-active memories selected for a reply.
- Every live memory disclosure includes relevance, sensitivity, consent, and
  human-readable retrieval reasons.
- The Memory Control Center provides health metrics, a review queue, duplicate
  visibility, and recall previews.
- High-sensitivity matches are clearly marked in both preview and live-chat UX.
- Memory-use audit events store IDs and counts rather than private memory text.
