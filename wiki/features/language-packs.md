---
title: Language Packs
type: feature
status: in-progress
tech_page: ./language-packs.tech.md
last_updated: 2026-04-10
open_questions:
  - "Pack completion criteria — what defines 'finished'?"
  - "Can users study multiple packs concurrently, or one at a time?"
---

# Language Packs

## Purpose

Language Packs are themed bundles of simulated conversations (e.g. "Soccer", "Economics", "AI") that teach vocabulary and grammar in context. They are the primary vehicle for structured, progressive learning — moving the learner from isolated word study through contextual exercises to full conversation comprehension. The design follows a "Corpus-First" approach: conversations are generated naturally, then analyzed for key vocabulary, rather than engineering conversations around pre-selected words.

## User Story

A learner browses available packs for their target language and selects "Soccer". The system presents an adaptive study cycle:

1. **Primer** — Core vocabulary from the pack (8–12 words per micro-lesson) is introduced. The learner sees definitions and initial recognition exercises.

2. **Controlled Practice** — Exercises (across all 10 exercise types in the vocabulary ladder) drill the introduced words. The system gates progression by per-word BKT mastery, not aggregate score.

3. **Contextual Transfer** — Short conversation snippets containing the studied words are served with comprehension questions. High target-word density provides scaffolded context. These are unlocked as anchor items reach sufficient mastery.

4. **Full Conversation Tests** — Longer, natural conversations where studied words appear at natural (low) frequency are served as comprehension tests. These update the user's global ELO and BKT for each word.

5. **Adaptive Cycling** — Rather than a linear "study then test" path, the pack alternates: new vocabulary → exercises → snippet → more exercises → full conversation → review of weak items. This loop continues until pack mastery is achieved.

## How It Works

### Pack Creation (Admin/System)

1. **Domain Scenario Matrix** — LLM (Opus/Pro tier) generates a batch of 20–50 varied scenario seeds for the topic, ensuring sub-topic variety and semantic field coverage. Existing scenarios are passed as context to prevent overlap.

2. **Scenario Expansion** — Each seed is expanded by a cheaper model (Mini/Flash tier) into full scenario blueprints with narrative arcs, persona goals, context descriptions, and keywords.

3. **Conversation Generation** — Natural conversations are generated from each scenario using the existing multi-agent pipeline (persona designer → scenario planner → template generator → quality checker).

4. **Corpus Analysis** — NLP pipeline + Supabase text analysis plugin extract vocabulary, collocations, grammar patterns, and register markers from each conversation. LLM classifies items by register (standard/colloquial/slang/idiom).

5. **Key Word Assembly** — Both NLP-extracted and LLM-suggested key words are integrated. Items appearing across 3+ conversations are prioritized. Target: at least 50 words/phrases/idioms per pack.

6. **Conversation Designation** — Conversations covering the greatest proportion of studied words become final assessment conversations. Those with higher density of specific target words become snippet/mini-test material (inverted density logic: high density = scaffolding, low density = authentic assessment).

7. **Exercise Generation** — Exercises are generated for all key words using the 10-level vocabulary ladder pipeline (3-prompt architecture).

8. **Pack Published** — Pack becomes available for user selection.

### Pack Study (Learner)

1. Learner selects a pack → system checks existing BKT state for pack words.
2. System determines which words are unknown/learning/known and builds the first micro-lesson (8–12 words).
3. Exercises served for unknown words, progressing through the vocabulary ladder levels.
4. As anchor items reach mastery thresholds, conversation snippets unlock.
5. After snippet comprehension, more vocabulary + new exercises cycle.
6. Full conversation comprehension tests unlock when sufficient word coverage is achieved.
7. The adaptive loop continues — failed words return to lower ladder levels, new words are introduced.

### Conversations Per Pack

~10–20 conversations per pack depending on topic breadth. The LLM breaks the topic into multiple sub-scenarios to ensure variety. Broader topics (e.g. "Australian Flora") require more conversations than narrow ones (e.g. "Basketball Scoring").

## Constraints & Edge Cases

- A pack's vocabulary scope is bounded by its conversation corpus — only words that appear in the conversations are studied.
- If a learner already knows most words in a pack (high BKT p_known), the system should skip word study and go straight to comprehension.
- Packs are replayable — a learner can redo exercises or comprehension tests.
- Pack difficulty uses the Age Tier system (not CEFR) — Toddler through Educated Professional.
- Progression gates on competence by item (per-word BKT), not aggregate score.
- Final test conversations should have the user knowing >90–95% of the words, with the studied pack words among them at natural frequency.

## Business Rules

- Packs are system-generated, not user-created (for now).
- Pack content is generated at pack creation time (conversations + exercises), not on demand.
- A pack must have conversations and exercises before it can be published.
- Word sense linkage must be validated before exercises are served.
- Pack completion should primarily update BKT of user vocab. ELO updates happen on comprehension tests.
- Pack mastery is displayed as a tiered system (Novice → Familiar → Proficient → Mastered), driven by average Concept ELO of underlying words, weighted by lowest-performing words.

## Related Pages

- [[features/language-packs.tech]] — Technical specification
- [[features/exercises]] — Exercise types used within packs
- [[algorithms/vocabulary-ladder]] — 10-level vocabulary acquisition ladder
- [[features/vocabulary-knowledge]] — BKT tracking for pack words
- [[features/comprehension-tests]] — Comprehension test format used for pack assessments
- [[features/conversations]] — Conversation generation pipeline
- [[decisions/ADR-003-age-tiers]] — Age Tier difficulty system
