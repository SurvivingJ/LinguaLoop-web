-- ============================================================================
-- Vocabulary-ladder judge prompts (Phase 4 — "Extend the judge layer").
-- Date: 2026-06-07
--
-- Seeds per-language (English = 2, Chinese = 1) prompt_templates rows for the
-- new ladder judges that extend coverage from L3-only to every LLM-authored
-- level plus the P1 sentence corpus. Each judge is fail-open and DB-driven via
-- services.prompt_service.get_template_config — the model is paired with the
-- prompt here (single source of truth; no hardcoded model in Python).
--
-- This file is appended to as later judges land (TASK-406 l1_distractor,
-- TASK-409 collocation, TASK-412 sentence_validity). Each section is wrapped in
-- its own BEGIN/COMMIT so a partial apply is safe.
--
-- See wiki/tasklist/ladder-judge-layer.tasks.md and
-- wiki/reviews/exercise-generation-audit-2026-06-07.md (B3.1) for the spec.
--
-- ----------------------------------------------------------------------------
-- Output-schema contract (consumed by judges/p1_sentences.py):
--   JSON object keyed by the 1-based sentence number; each value is
--   {"rating": <int 1-5>, "reason": "<short string>"}. The Python side maps
--   rating -> verdict via schemas.likert_to_verdict (5/4 accept, 3 flag,
--   2/1 reject). A missing/unparseable entry safe-accepts that sentence.
--
-- Model rationale: the P1 judge runs once per sense over ~10 short sentences
-- and only needs reliable sense/register discrimination, so it uses the same
-- cheap per-language verifier tier as the existing ladder judges —
-- English: google/gemini-2.5-flash-lite ; Chinese: qwen/qwen-max (the model
-- used by the zh vocab_prompt2_exercises row in cloze_distractor_quality.sql).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. ladder_p1_sentence_judge — English (language_id = 2), v1
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_p1_sentence_judge',
    2,
    1,
    $PROMPT$You are a strict corpus editor for an English vocabulary course. A generator produced base example sentences for ONE target word in ONE specific sense. Every downstream exercise reuses these sentences, so a flawed sentence corrupts many exercises. Rate each sentence.

Target word: {lemma}
Intended definition (the ONE sense being taught): {definition}
Sense fingerprint (disambiguating gloss / typical collocates): {sense_fingerprint}
Declared register: {register}

Sentences:
{sentences_numbered}

Judge each sentence on THREE dimensions, all relative to the intended sense above:
1. Sense match — the target word in the sentence must carry the INTENDED sense, not a homonym or a different sense of the same spelling. (e.g. if the sense is "bank = financial institution", a sentence using "bank" as a riverbank FAILS.)
2. Register — the sentence's formality / domain must be consistent with the declared register. A markedly more formal or more casual sentence than declared is a partial failure.
3. Whole-word / whole-sense — the target must appear as a discrete whole word performing the intended sense's grammatical job: not embedded inside a longer word, and not swallowed by an idiom that shifts the sense.

Rate each sentence 1-5:
5 = clean on all three dimensions; an ideal teaching sentence.
4 = correct sense and whole-word; at most a mild register drift.
3 = usable but weak: borderline register, slightly unnatural, or sense correct yet faintly ambiguous.
2 = wrong sense, OR target not a whole-word / whole-sense, OR clearly off-register.
1 = unusable: wrong word sense, ungrammatical, target absent, or the sentence does not actually use the target word.

Return JSON ONLY, keyed by the 1-based sentence number. Each value is an object with an integer "rating" (1-5) and a short "reason" (<= 15 words naming the failing dimension, or "clean"):
{{"1": {{"rating": 5, "reason": "clean"}}, "2": {{"rating": 2, "reason": "sense: uses 'bank' as riverbank, not financial"}}}}

Rate EVERY sentence. No prose outside the JSON. No markdown fences.$PROMPT$,
    true,
    'google/gemini-2.5-flash-lite',
    'openrouter',
    'P1 sentence-corpus judge (English): rates each base sentence on sense-match, register, and whole-word/whole-sense before downstream levels consume it.'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

COMMIT;

-- ----------------------------------------------------------------------------
-- 2. ladder_p1_sentence_judge — Chinese (language_id = 1), v1
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_p1_sentence_judge',
    1,
    1,
    $PROMPT$你是一门中文词汇课程的严格语料编辑。生成器为某个目标词的某一个特定义项产出了基础例句。所有下游练习都会复用这些句子，因此一个有缺陷的句子会污染许多练习。请逐句评分。

目标词：{lemma}
锁定义项（正在教授的唯一义项）：{definition}
义项指纹（用于消歧的释义 / 典型搭配）：{sense_fingerprint}
声明语域：{register}

句子：
{sentences_numbered}

针对上述锁定义项，从三个维度评判每个句子：
1. 义项匹配 —— 句中目标词必须承担锁定义项，而非同形异义或该字 / 词的其它义项。（例如义项为"行 ＝ 银行"，若句子中"行"作"行走 / 可以"解，则不合格。）
2. 语域 —— 句子的正式程度 / 语体须与声明语域一致；明显更正式或更口语化均为部分不合格。
3. 整词 / 整义 —— 目标词须作为承担该义项句法角色的完整词出现：不能仅作为更长词语中的字符片段，也不能进入改变义项的固定成语。

每句评 1-5 分：
5 ＝ 三个维度全部干净，理想教学句。
4 ＝ 义项正确且整词出现，至多轻微语域偏移。
3 ＝ 可用但偏弱：语域临界、略不自然，或义项正确但略有歧义。
2 ＝ 义项错误，或目标词非整词 / 整义出现，或明显偏离语域。
1 ＝ 不可用：义项错误、不合语法、目标词缺失，或句子并未真正使用目标词。

仅返回 JSON，以 1 起始的句子编号为键，每个值为含整数 "rating"（1-5）与简短 "reason"（≤ 15 字，指出失败维度，或写"clean"）的对象：
{{"1": {{"rating": 5, "reason": "clean"}}, "2": {{"rating": 2, "reason": "义项：'行'作行走解，非银行"}}}}

每句都要评分。JSON 之外不要输出任何文字，不要使用 markdown 代码块。$PROMPT$,
    true,
    'qwen/qwen-max',
    'openrouter',
    'P1 sentence-corpus judge (Chinese): rates each base sentence on 义项匹配 (sense), 语域 (register), and 整词/整义 (whole-word/whole-sense) before downstream levels consume it.'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

COMMIT;

-- ----------------------------------------------------------------------------
-- 3. ladder_l1_distractor_judge — English (language_id = 2), v1
-- ----------------------------------------------------------------------------
-- Output-schema contract (consumed by judges/l1_distractor.py):
--   JSON keyed by the 1-based distractor index; each value is
--   {"verdict": "keep"|"reject", "reason": "<short string>"}. A missing or
--   non-"reject" verdict keeps the distractor (fail-open).
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_l1_distractor_judge',
    2,
    1,
    $PROMPT$You are a strict judge for a LISTENING vocabulary exercise. The learner HEARS the target word spoken aloud and must pick the matching written word from four options. The three distractors must be REAL words that a learner could plausibly MISHEAR as the target, but that mean something different. Rule on each candidate distractor.

Target word (spoken): {target}
Candidate distractors:
{distractors_numbered}

For EACH distractor decide:
- "keep" = a real English word that is genuinely AUDIO-CONFUSABLE with the target (a homophone / near-homophone, a minimal pair differing by one phoneme, or a same-stress rhyme a learner could mishear) AND is not a synonym of the target.
- "reject" = ANY of:
  * not a real English word;
  * a synonym or near-synonym of the target (a learner who heard the target could reasonably choose it);
  * similar to the target only in SPELLING, not in sound (e.g. "tough" vs "though", "through" vs "thorough") — spelling look-alikes defeat a listening test;
  * identical to the target, or merely the target with a different inflection.

Be strict: a listening distractor that cannot be confused BY EAR is useless. When unsure whether two words are confusable by ear, REJECT.

Return JSON ONLY, keyed by the 1-based index, each value {{"verdict": "keep|reject", "reason": "<= 12 words"}}:
{{"1": {{"verdict": "keep", "reason": "minimal pair /ɪ/ vs /iː/"}}, "2": {{"verdict": "reject", "reason": "synonym of target"}}, "3": {{"verdict": "reject", "reason": "spelling look-alike, sounds different"}}}}

No prose outside the JSON. No markdown fences.$PROMPT$,
    true,
    'google/gemini-2.5-flash-lite',
    'openrouter',
    'L1 listening-distractor judge (English): rejects non-words, synonyms, and spelling-only look-alikes; keeps only real, audio-confusable distractors.'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

COMMIT;

-- ----------------------------------------------------------------------------
-- 4. ladder_l1_distractor_judge — Chinese (language_id = 1), v1
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_l1_distractor_judge',
    1,
    1,
    $PROMPT$你是一道"听音辨字"词汇练习的严格评审。学习者听到目标词的读音，须从四个书面选项中选出正确写法。三个干扰项必须是真实的字 / 词，在"听感"上可能与目标词混淆（主要是声调混淆），但意义不同。请逐项评判候选干扰项。

目标词（语音）：{target}
候选干扰项：
{distractors_numbered}

对每个干扰项判定：
- "keep" ＝ 真实存在的汉字 / 词，与目标在听感上确实可混淆（声母韵母相同而声调不同的声调混淆词，或仅差一个音位的最小对立对），且不是目标的同义词。
- "reject" ＝ 满足以下任一条：
  * 不是真实存在的字 / 词；
  * 是目标的同义词或近义词（听到目标的人可能合理选它）；
  * 与目标仅"字形"相似而读音不同（纯形近字 —— 听不出区别会破坏听力测试）；
  * 与目标完全同音同调（纯靠听无法区分），或就是目标本身；
  * 与目标在字形和读音上都无关。

请从严：听不出区别的干扰项毫无意义。若不确定两者听感是否可混淆，一律 reject。

仅返回 JSON，以 1 起始的索引为键，每个值为 {{"verdict": "keep|reject", "reason": "<= 12 字"}}：
{{"1": {{"verdict": "keep", "reason": "声调混淆：mǎ vs mā"}}, "2": {{"verdict": "reject", "reason": "目标的同义词"}}, "3": {{"verdict": "reject", "reason": "形近但读音不同"}}}}

JSON 之外不要输出任何文字，不要使用 markdown 代码块。$PROMPT$,
    true,
    'qwen/qwen-max',
    'openrouter',
    'L1 listening-distractor judge (Chinese): keeps 声调混淆 / 最小对立干扰项；rejects 同义词、纯形近字、完全同音同调字。'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

COMMIT;

-- ----------------------------------------------------------------------------
-- 5. ladder_collocation_judge — English (language_id = 2), v1
-- ----------------------------------------------------------------------------
-- Output-schema contract (consumed by judges/collocation.py, BOTH call sites):
--   JSON keyed by the 1-based candidate index; each value is
--   {"rating": <int 1-5>, "reason": "<short string>"}. The Python side maps
--   the rating to a verdict via schemas.likert_to_verdict (5/4 accept, 3 flag,
--   2/1 reject) — a 5-point Likert, NOT a raw 0.0-1.0 float (tasklist decision
--   7 / memory distractor-judge-v3-likert). The rating measures how clearly the
--   candidate is a genuine NON-collocate of the target: 5 = obviously unnatural
--   (ideal wrong-answer), 1 = a fully idiomatic, also-correct collocate.
--   L5 filter_collocation_distractors: a "reject" verdict (rating 1-2) is an
--     also-valid collocate and is DROPPED; accept/flag are kept. A missing /
--     unparseable rating keeps the distractor (flag, fail-open).
--   L8 judge_collocation_repair: the single error_collocate's rating maps
--     straight to the verdict — 5/4 accepts the repair exercise, 2/1 rejects it.
--
-- Model rationale: same cheap per-language verifier tier as the other ladder
-- judges (English gemini-2.5-flash-lite, Chinese qwen-max); the judgement is a
-- single naturalness call per candidate, temperature 0, fail-open.
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_collocation_judge',
    2,
    1,
    $PROMPT$You are a strict judge of English COLLOCATION. In the sentence below, the TARGET word combines with a collocate word to fill the gap; the CORRECT collocate is given. For each CANDIDATE word, decide whether it could ALSO form a natural, idiomatic collocation with TARGET in this sentence, or whether it is clearly a non-collocate (unnatural / wrong with TARGET here).

Sentence: {sentence}
Target word: {target}
Correct collocate (the intended answer): {correct_collocate}
Candidate words:
{candidates_numbered}

For EACH candidate, rate how clearly it is a genuine NON-collocate of TARGET in this sentence — i.e. how clearly WRONG "candidate + target" sounds to a fluent native speaker — on a 1-5 scale:
5 = obviously not a collocate; the combination is clearly unnatural / wrong (an ideal wrong-answer).
4 = probably not a collocate; sounds off, though not absurd.
3 = borderline; could go either way.
2 = probably an acceptable collocate; a native speaker might well use it (likely an also-correct answer).
1 = a fully idiomatic, natural collocate of TARGET here — just as correct as the given answer, so it must NOT be used as a wrong answer.

Judge collocational naturalness, not mere grammaticality: a candidate can be perfectly grammatical yet still rate 5 (e.g. "make" vs "do" homework). When unsure whether a common partner of TARGET is acceptable, rate it LOW (1-2) — it is safer to drop a borderline distractor than to ship an also-correct one.

Return JSON ONLY, keyed by the 1-based index, each value {{"rating": <1-5>, "reason": "<= 12 words"}}:
{{"1": {{"rating": 5, "reason": "'cook coffee' is unidiomatic"}}, "2": {{"rating": 1, "reason": "'brew coffee' is also natural"}}}}

No prose outside the JSON. No markdown fences.$PROMPT$,
    true,
    'google/gemini-2.5-flash-lite',
    'openrouter',
    'Collocation judge (English): rules per candidate whether it is a genuine non-collocate of the target (good distractor / valid error word) or an also-valid collocate. Serves L5 filter + L8 repair verdict.'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

COMMIT;

-- ----------------------------------------------------------------------------
-- 6. ladder_collocation_judge — Chinese (language_id = 1), v1
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_collocation_judge',
    1,
    1,
    $PROMPT$你是中文"词语搭配"的严格评审。在下面的句子中，目标词须与一个搭配词组合填入空缺；已给出正确搭配词。对每个候选词，判断它是否也能与目标词在此句中构成自然、地道的搭配，还是明显不能搭配（与目标词组合不自然 / 错误）。

句子：{sentence}
目标词：{target}
正确搭配词（既定答案）：{correct_collocate}
候选词：
{candidates_numbered}

对每个候选词，评估它在此句中作为目标词的"非搭配"有多明显 —— 即"候选词＋目标词"在母语者听来有多么明显地不自然 / 错误 —— 用 1-5 分：
5 ＝ 明显不能搭配；组合明显不自然 / 错误（理想的错误选项）。
4 ＝ 很可能不能搭配；听起来不对，但不至于荒谬。
3 ＝ 临界；两可。
2 ＝ 很可能是可接受的搭配；母语者也许会这么用（很可能是另一个正确答案）。
1 ＝ 与目标词完全地道、自然的搭配，与既定答案同样正确，绝不可作错误选项。

判断"搭配"是否自然，而非仅判断语法：候选词可能合乎语法却仍应评 5 分（搭配不自然）。须特别注意量词与名词的搭配、动词的体标 / 时态搭配（了 / 着 / 过）、以及固定搭配的凝固性。若不确定某常见伙伴是否可接受，评低分（1-2）—— 宁可舍弃一个临界干扰项，也不要放过一个其实正确的选项。

仅返回 JSON，以 1 起始的索引为键，每个值为 {{"rating": <1-5>, "reason": "<= 12 字"}}：
{{"1": {{"rating": 5, "reason": "搭配不自然"}}, "2": {{"rating": 1, "reason": "亦为地道搭配"}}}}

JSON 之外不要输出任何文字，不要使用 markdown 代码块。$PROMPT$,
    true,
    'qwen/qwen-max',
    'openrouter',
    '搭配 judge (Chinese): rules per candidate whether it is a genuine 非搭配 of the target (good distractor / valid error word) or an also-valid 搭配. Serves L5 filter + L8 repair verdict; covers 量词/体标/固定搭配凝固性.'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

COMMIT;

-- ----------------------------------------------------------------------------
-- 7. ladder_sentence_validity_judge — English (language_id = 2), v1
-- ----------------------------------------------------------------------------
-- Output-schema contract (consumed by judges/sentence_validity.py; serves L6
-- "semantic discrimination" 3 wrong sentences + L7 "spot incorrect" 1 sentence):
--   JSON keyed by the 1-based sentence number; each value is
--   {"rating": <int 1-5>, "reason": "<short string>"}. Mapped to a verdict via
--   schemas.likert_to_verdict (5/4 accept, 3 flag, 2/1 reject) — a 5-point
--   Likert, NOT a float (tasklist decision 7 / memory distractor-judge-v3-likert).
--   The rating measures how cleanly the sentence is wrong FOR ITS LABELED REASON:
--   5 = clearly wrong exactly as labeled (keep); 2 = wrong for a DIFFERENT reason
--   than labeled (mislabeled, drop); 1 = actually acceptable / grammatical (drop).
--   The caller drops a sentence whose verdict is reject; a missing/unparseable
--   rating safe-accepts that sentence (fail-open).
--
-- Model rationale: same cheap per-language verifier tier as the other ladder
-- judges (English gemini-2.5-flash-lite, Chinese qwen-max); temperature 0,
-- fail-open.
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_sentence_validity_judge',
    2,
    1,
    $PROMPT$You are a strict judge for a vocabulary exercise that teaches learners to tell CORRECT sentences from deliberately WRONG ones. A generator produced sentences that are each supposed to be wrong for ONE specific labeled reason. Your job: for each sentence, decide whether it is wrong ONLY for its labeled reason.

Target word: {target}

Sentences (each with the reason it is supposed to be wrong):
{pairs_numbered}

For EACH sentence, rate 1-5 how cleanly it is wrong FOR ITS LABELED REASON:
5 = clearly incorrect, and incorrect precisely for the labeled reason — an ideal wrong sentence.
4 = incorrect for the labeled reason, with only minor doubt.
3 = borderline — arguably wrong, arguably acceptable.
2 = incorrect, BUT for a DIFFERENT reason than the one labeled (the shown explanation would mislead the learner).
1 = actually acceptable / grammatical / natural — NOT wrong at all, so it cannot be used as a wrong sentence.

A sentence must score LOW (1-2) if a fluent native speaker would accept it, or if its real defect differs from the labeled reason. Judge the labeled reason specifically, not just overall wrongness.

Return JSON ONLY, keyed by the 1-based index, each value {{"rating": <1-5>, "reason": "<= 15 words"}}:
{{"1": {{"rating": 5, "reason": "wrong tense, exactly as labeled"}}, "2": {{"rating": 1, "reason": "sentence is fully grammatical"}}}}

Rate EVERY sentence. No prose outside the JSON. No markdown fences.$PROMPT$,
    true,
    'google/gemini-2.5-flash-lite',
    'openrouter',
    'Sentence-validity judge (English): rules per crafted-wrong sentence whether it is wrong ONLY for its labeled reason; rejects accidentally-grammatical and mislabeled sentences. Serves L6 (3 wrong) + L7 (1 wrong).'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

COMMIT;

-- ----------------------------------------------------------------------------
-- 8. ladder_sentence_validity_judge — Chinese (language_id = 1), v1
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_sentence_validity_judge',
    1,
    1,
    $PROMPT$你是一道词汇练习的严格评审：该练习训练学习者区分正确句子与故意造错的句子。生成器产出的每个句子都应当因某个特定的标注原因而错误。你的任务：逐句判断该句是否仅因其标注原因而错误。

目标词：{target}

句子（附其应当错误的原因）：
{pairs_numbered}

对每个句子，评估它因标注原因而错误的"干净程度"，用 1-5 分：
5 ＝ 明显错误，且正是因标注原因而错 —— 理想的错误句。
4 ＝ 因标注原因而错，仅有轻微存疑。
3 ＝ 临界 —— 可算错也可算可接受。
2 ＝ 确实错误，但错因与标注不同（如标注为体标误用，实为语序错误），向学习者展示的解释会产生误导。
1 ＝ 实际上合乎语法、自然可接受 —— 根本没错，不能用作错误句。

若母语者会接受该句，或其真正的缺陷与标注原因不同，必须评低分（1-2）。请针对标注原因（量词、体标 了/着/过、语序、方向补语等）具体判断，而非仅看整体是否别扭。

仅返回 JSON，以 1 起始的索引为键，每个值为 {{"rating": <1-5>, "reason": "<= 15 字"}}：
{{"1": {{"rating": 5, "reason": "量词误用，与标注一致"}}, "2": {{"rating": 1, "reason": "句子完全合乎语法"}}}}

每句都要评分。JSON 之外不要输出任何文字，不要使用 markdown 代码块。$PROMPT$,
    true,
    'qwen/qwen-max',
    'openrouter',
    '句子有效性 judge (Chinese): rules per crafted-wrong sentence whether it is wrong ONLY for its labeled reason; covers 量词/体标/语序/方向补语 taxonomy; rejects accidentally-grammatical and mislabeled sentences. Serves L6 + L7.'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

COMMIT;

-- ----------------------------------------------------------------------------
-- Verification (run manually after applying)
-- ----------------------------------------------------------------------------
-- SELECT task_name, language_id, version, is_active, model
-- FROM public.prompt_templates
-- WHERE task_name IN ('ladder_p1_sentence_judge', 'ladder_l1_distractor_judge',
--                     'ladder_collocation_judge', 'ladder_sentence_validity_judge')
-- ORDER BY task_name, language_id, version;
