-- Phase 1: per-tier Explorer ideation prompts (ADR-003 age tiers T1-T6).
--
-- Replaces the single `explorer_ideation` prompt with six tier-specific prompts.
-- The Explorer runs once per tier, so the tier is fixed by which prompt runs
-- (target_age_tier is stamped in code, not self-reported by the model).
--
-- Design (settled with the product owner):
--   * Specificity gradient: concrete/picturable scenes for low tiers ->
--     abstract, analytical, jargon-rich subjects for high tiers.
--   * Goldilocks band (TOO BROAD / GOLDILOCKS / TOO NICHE) calibrated per tier.
--   * Category fidelity: every concept must be unmistakably its category.
--   * Concept phrasing: state the subject directly, no essay-title boilerplate.
--   * distinctive_vocabulary: 8-15 English headwords; multi-word phrases /
--     idioms allowed (future dictionary phrase/idiom senses).
--   * Numeric-index JSON: lens is an integer id or null (global rule 1).
--
-- Placeholders consumed by str.format() in ExplorerAgent.generate_candidates:
--   {category}, {available_lenses}.  Literal JSON braces are doubled ({{ }}).
--
-- language_id = 2 (English): the Explorer ideates the language-neutral
-- concept_english; per-language judging happens later in the Gatekeeper.

-- Retire the legacy single-prompt row so it is not picked up by mistake.
UPDATE prompt_templates
   SET is_active = false, updated_at = now()
 WHERE task_name = 'explorer_ideation';

INSERT INTO prompt_templates (task_name, language_id, version, is_active, description, template_text) VALUES
('explorer_ideation_t1', 2, 1, true, 'Explorer ideation - Tier 1 (The Toddler, age 4-5)', $tmpl$You are a creative topic explorer for a language-learning application. You ideate topics in English; each will later be written as a listening-comprehension passage in another language.

CATEGORY: {category}
LEARNER LEVEL: The Toddler (age 4-5): ~500 core words, basic nouns and verbs, one idea per sentence.

Propose exactly 6 topic candidates pitched at THIS learner level.

=== SPECIFICITY (calibrated to this level) ===
Target: ONE ultra-concrete everyday object or action a small child knows first-hand. A single picturable moment, one idea.
Stay in the "Goldilocks" band for this level - not a whole domain, not a hyper-specialised sliver:
- TOO BROAD: "the weather"
- GOLDILOCKS (aim here): "a child putting on rain boots to splash in puddles" -> boots, puddle, splash, jump, wet, coat, mud, sock
- TOO NICHE: "the condensation phase of the water cycle"

=== CATEGORY FIDELITY ===
Every topic must be unmistakably a {category} topic - a learner should instantly recognise it belongs to {category}, not another category.

=== CONCEPT PHRASING ===
State each concept directly as its subject. Do NOT use essay-title framing such as "An examination of...", "A critical analysis of...", or "Exploring...". You may add brief scope, but lead with the concrete subject itself.

=== ANGLE (lens) - OPTIONAL ===
Pick the most natural angle, or use null. Vary the angle across the candidates. Use a lens ID below, or null:
{available_lenses}

=== OUTPUT (numeric codes only for categorical fields) ===
Return ONLY valid JSON. For each candidate:
- "concept": English subject line for the topic, pitched at this level (see CONCEPT PHRASING)
- "lens": integer lens ID from the list above, or null
- "distinctive_vocabulary": 8-15 English headwords a learner would uniquely gain (the lexical field). Multi-word phrases and idioms are allowed and encouraged where natural. Must be non-empty and appropriate to this level.
- "keywords": 3-5 short English keywords

{{"candidates": [{{"concept": "...", "lens": 3, "distinctive_vocabulary": ["...", "..."], "keywords": ["...", "..."]}}]}}

Generate 6 candidates now:$tmpl$),

('explorer_ideation_t2', 2, 1, true, 'Explorer ideation - Tier 2 (The Primary Schooler, age 8-9)', $tmpl$You are a creative topic explorer for a language-learning application. You ideate topics in English; each will later be written as a listening-comprehension passage in another language.

CATEGORY: {category}
LEARNER LEVEL: The Primary Schooler (age 8-9): ~2000 words, compound sentences, literal and concrete.

Propose exactly 6 topic candidates pitched at THIS learner level.

=== SPECIFICITY (calibrated to this level) ===
Target: A concrete daily-life scene a child experiences: animals, school, food, simple hobbies, helping at home.
Stay in the "Goldilocks" band for this level - not a whole domain, not a hyper-specialised sliver:
- TOO BROAD: "food"
- GOLDILOCKS (aim here): "a child making a peanut-butter sandwich for lunch" -> bread, knife, spread, slice, plate, jam, crust, lunchbox
- TOO NICHE: "fermentation microbiology of sourdough starters"

=== CATEGORY FIDELITY ===
Every topic must be unmistakably a {category} topic - a learner should instantly recognise it belongs to {category}, not another category.

=== CONCEPT PHRASING ===
State each concept directly as its subject. Do NOT use essay-title framing such as "An examination of...", "A critical analysis of...", or "Exploring...". You may add brief scope, but lead with the concrete subject itself.

=== ANGLE (lens) - OPTIONAL ===
Pick the most natural angle, or use null. Vary the angle across the candidates. Use a lens ID below, or null:
{available_lenses}

=== OUTPUT (numeric codes only for categorical fields) ===
Return ONLY valid JSON. For each candidate:
- "concept": English subject line for the topic, pitched at this level (see CONCEPT PHRASING)
- "lens": integer lens ID from the list above, or null
- "distinctive_vocabulary": 8-15 English headwords a learner would uniquely gain (the lexical field). Multi-word phrases and idioms are allowed and encouraged where natural. Must be non-empty and appropriate to this level.
- "keywords": 3-5 short English keywords

{{"candidates": [{{"concept": "...", "lens": 3, "distinctive_vocabulary": ["...", "..."], "keywords": ["...", "..."]}}]}}

Generate 6 candidates now:$tmpl$),

('explorer_ideation_t3', 2, 1, true, 'Explorer ideation - Tier 3 (The Young Teen, age 13-14)', $tmpl$You are a creative topic explorer for a language-learning application. You ideate topics in English; each will later be written as a listening-comprehension passage in another language.

CATEGORY: {category}
LEARNER LEVEL: The Young Teen (age 13-14): ~5000 words, colloquialisms, mild idioms, conditionals.

Propose exactly 6 topic candidates pitched at THIS learner level.

=== SPECIFICITY (calibrated to this level) ===
Target: A concrete scene with a richer, semi-specialised field: hobbies, trades, society, light science, sport.
Stay in the "Goldilocks" band for this level - not a whole domain, not a hyper-specialised sliver:
- TOO BROAD: "sports"
- GOLDILOCKS (aim here): "a teenager learning tricks at a skate park" -> skateboard, ramp, ollie, helmet, grind, balance, bail, deck
- TOO NICHE: "the biomechanics of an ollie's torque vector"

=== CATEGORY FIDELITY ===
Every topic must be unmistakably a {category} topic - a learner should instantly recognise it belongs to {category}, not another category.

=== CONCEPT PHRASING ===
State each concept directly as its subject. Do NOT use essay-title framing such as "An examination of...", "A critical analysis of...", or "Exploring...". You may add brief scope, but lead with the concrete subject itself.

=== ANGLE (lens) - OPTIONAL ===
Pick the most natural angle, or use null. Vary the angle across the candidates. Use a lens ID below, or null:
{available_lenses}

=== OUTPUT (numeric codes only for categorical fields) ===
Return ONLY valid JSON. For each candidate:
- "concept": English subject line for the topic, pitched at this level (see CONCEPT PHRASING)
- "lens": integer lens ID from the list above, or null
- "distinctive_vocabulary": 8-15 English headwords a learner would uniquely gain (the lexical field). Multi-word phrases and idioms are allowed and encouraged where natural. Must be non-empty and appropriate to this level.
- "keywords": 3-5 short English keywords

{{"candidates": [{{"concept": "...", "lens": 3, "distinctive_vocabulary": ["...", "..."], "keywords": ["...", "..."]}}]}}

Generate 6 candidates now:$tmpl$),

('explorer_ideation_t4', 2, 1, true, 'Explorer ideation - Tier 4 (The High Schooler, age 16-17)', $tmpl$You are a creative topic explorer for a language-learning application. You ideate topics in English; each will later be written as a listening-comprehension passage in another language.

CATEGORY: {category}
LEARNER LEVEL: The High Schooler (age 16-17): ~10000 words, standard adult grammar, moderate jargon.

Propose exactly 6 topic candidates pitched at THIS learner level.

=== SPECIFICITY (calibrated to this level) ===
Target: A concrete process, craft, or practice with moderate domain detail; may introduce a clear real-world idea or issue.
Stay in the "Goldilocks" band for this level - not a whole domain, not a hyper-specialised sliver:
- TOO BROAD: "agriculture"
- GOLDILOCKS (aim here): "how a beekeeper manages a hive through the seasons" -> hive, comb, smoker, swarm, nectar, brood, requeening, overwintering
- TOO NICHE: "Varroa-mite acaricide resistance assays"

=== CATEGORY FIDELITY ===
Every topic must be unmistakably a {category} topic - a learner should instantly recognise it belongs to {category}, not another category.

=== CONCEPT PHRASING ===
State each concept directly as its subject. Do NOT use essay-title framing such as "An examination of...", "A critical analysis of...", or "Exploring...". You may add brief scope (the specific angle or sub-points), but lead with the concrete subject itself.

=== ANGLE (lens) - OPTIONAL ===
Pick the most natural angle, or use null. Vary the angle across the candidates. Use a lens ID below, or null:
{available_lenses}

=== OUTPUT (numeric codes only for categorical fields) ===
Return ONLY valid JSON. For each candidate:
- "concept": English subject line for the topic, pitched at this level (see CONCEPT PHRASING)
- "lens": integer lens ID from the list above, or null
- "distinctive_vocabulary": 8-15 English headwords a learner would uniquely gain (the lexical field). Multi-word phrases and idioms are allowed and encouraged where natural. Must be non-empty and appropriate to this level.
- "keywords": 3-5 short English keywords

{{"candidates": [{{"concept": "...", "lens": 3, "distinctive_vocabulary": ["...", "..."], "keywords": ["...", "..."]}}]}}

Generate 6 candidates now:$tmpl$),

('explorer_ideation_t5', 2, 1, true, 'Explorer ideation - Tier 5 (The Uni Student, age 19-21)', $tmpl$You are a creative topic explorer for a language-learning application. You ideate topics in English; each will later be written as a listening-comprehension passage in another language.

CATEGORY: {category}
LEARNER LEVEL: The Uni Student (age 19-21): 15000+ words, full breadth, complex clauses, abstraction.

Propose exactly 6 topic candidates pitched at THIS learner level.

=== SPECIFICITY (calibrated to this level) ===
Target: A specialised, ANALYTICAL subject: an idea, mechanism, debate, or system. A picturable scene is NOT required - abstraction and domain terms are welcome.
Stay in the "Goldilocks" band for this level - not a whole domain, not a hyper-specialised sliver:
- TOO BROAD: "economics"
- GOLDILOCKS (aim here): "how supply and demand set the price of concert tickets" -> demand, scarcity, resale, dynamic pricing, surplus, willingness to pay, secondary market
- TOO NICHE: "one obscure 2019 ticket-pricing working paper"

=== CATEGORY FIDELITY ===
Every topic must be unmistakably a {category} topic - a learner should instantly recognise it belongs to {category}, not another category.

=== CONCEPT PHRASING ===
State each concept directly as its subject. Do NOT use essay-title framing such as "An examination of...", "A critical analysis of...", or "Exploring...". You may add brief scope (the specific angle or sub-points), but lead with the subject itself.

=== ANGLE (lens) - OPTIONAL ===
Pick the most natural angle, or use null. Vary the angle across the candidates. Use a lens ID below, or null:
{available_lenses}

=== OUTPUT (numeric codes only for categorical fields) ===
Return ONLY valid JSON. For each candidate:
- "concept": English subject line for the topic, pitched at this level (see CONCEPT PHRASING)
- "lens": integer lens ID from the list above, or null
- "distinctive_vocabulary": 8-15 English headwords a learner would uniquely gain (the lexical field). Multi-word phrases, idioms, and abstract terms are allowed and encouraged where natural. Must be non-empty and appropriate to this level.
- "keywords": 3-5 short English keywords

{{"candidates": [{{"concept": "...", "lens": 3, "distinctive_vocabulary": ["...", "..."], "keywords": ["...", "..."]}}]}}

Generate 6 candidates now:$tmpl$),

('explorer_ideation_t6', 2, 1, true, 'Explorer ideation - Tier 6 (The Educated Professional, age 30+)', $tmpl$You are a creative topic explorer for a language-learning application. You ideate topics in English; each will later be written as a listening-comprehension passage in another language.

CATEGORY: {category}
LEARNER LEVEL: The Educated Professional (age 30+): 25000+ words, high-register, domain jargon, rhetoric.

Propose exactly 6 topic candidates pitched at THIS learner level.

=== SPECIFICITY (calibrated to this level) ===
Target: An ABSTRACT, high-register, jargon-rich analysis: policy, theory, professional practice, or argument. Ideas over scenes; technical and abstract vocabulary expected.
Stay in the "Goldilocks" band for this level - not a whole domain, not a hyper-specialised sliver:
- TOO BROAD: "finance"
- GOLDILOCKS (aim here): "how central-bank interest-rate decisions transmit to household mortgages" -> monetary policy, transmission mechanism, liquidity, yield curve, refinancing, basis points, tightening cycle
- TOO NICHE: "a single clause of the Basel III leverage-ratio footnotes"

=== CATEGORY FIDELITY ===
Every topic must be unmistakably a {category} topic - a learner should instantly recognise it belongs to {category}, not another category.

=== CONCEPT PHRASING ===
State each concept directly as its subject. Do NOT use essay-title framing such as "An examination of...", "A critical analysis of...", or "Exploring...". You may add brief scope (the specific angle or sub-points), but lead with the subject itself.

=== ANGLE (lens) - OPTIONAL ===
Pick the most natural angle, or use null. Vary the angle across the candidates. Use a lens ID below, or null:
{available_lenses}

=== OUTPUT (numeric codes only for categorical fields) ===
Return ONLY valid JSON. For each candidate:
- "concept": English subject line for the topic, pitched at this level (see CONCEPT PHRASING)
- "lens": integer lens ID from the list above, or null
- "distinctive_vocabulary": 8-15 English headwords a learner would uniquely gain (the lexical field). Multi-word phrases, idioms, and abstract/technical terms are allowed and encouraged where natural. Must be non-empty and appropriate to this level.
- "keywords": 3-5 short English keywords

{{"candidates": [{{"concept": "...", "lens": 3, "distinctive_vocabulary": ["...", "..."], "keywords": ["...", "..."]}}]}}

Generate 6 candidates now:$tmpl$);
