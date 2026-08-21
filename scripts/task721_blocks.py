"""TASK-721 distractor-construction blocks, their splice anchors, and the
type-family mapping.

WHAT THIS IS
------------
The live distractor judge (`test_distractor_plausibility`, zh v6 / en v4 / ja v4)
rates every generated distractor 1-5. Generators have never been shown that
scale, so content is filtered against a specification it was never given. These
blocks are that scale inverted -- from "rate this" into "build like this" -- and
are spliced into each `question_*` row immediately before its output contract.

The two prohibitions the judge's reject bands encode are stated explicitly in
every block, because they are the two the generators actually trip:

    judge band 1  a distractor that is ALSO ARGUABLY CORRECT
    judge band 3  a distractor that is a PARAPHRASE of the correct answer

Band 2 (different subject) is stated as the thing to avoid, and its inverse --
"a same-subject item the passage never mentions is a GOOD distractor" -- is
stated as the thing to do, because that inverse is the single most load-bearing
sentence in the judge prompt.

THE TYPE-FAMILY SPLIT IS A HYPOTHESIS, NOT A FINDING
----------------------------------------------------
sense / intent / fact comes from TASK-717, where it was measured ON THE JUDGE
SIDE and FAILED: zh `vocabulary_context` scored 9/16 in all four arms, and the
en rejects went 0 -> 5. Those v5 rows are retained inactive. Its value on the
GENERATOR side is untested -- that is exactly what the before/after measurement
in this task exists to find out. Nothing here should be read as established.

WHERE THE TEXT COMES FROM
-------------------------
* en -- hand-authored in this file, as a direct inversion of the live en v4
  judge rubric. `rewrite_prompt_native.py` cannot author English (its
  `LANG_ID` is {'zh': 1, 'ja': 3}), and the rationale that motivates it -- brief
  the model in the target language so it does not produce translationese -- is
  vacuous when the target language is the one the source rubric is already
  written in. Hand-authoring also makes each en block a checkable inversion of
  the live rubric rather than a model's paraphrase of it.
* zh / ja -- authored natively by `qwen/qwen3.8-max` via
  `scripts/author_task721_blocks.py`, following TASK-722 / TASK-724, and read
  from `data/eval/task721/blocks/`. Kept on disk rather than inline so the
  authored artefact, the staged template and the migration all derive from one
  file.
"""

from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCK_DIR = os.path.join(ROOT, 'data', 'eval', 'task721', 'blocks')

FAMILY = {
    'vocabulary_context': 'sense',
    'author_purpose': 'intent',
    'main_idea': 'intent',
    'literal_detail': 'fact',
    'supporting_detail': 'fact',
    'inference': 'fact',
}

# Exact substring that opens each row's output-contract section. The block is
# inserted immediately BEFORE it, so construction guidance lands after the
# pedagogical guidance and never disturbs the JSON contract. Each anchor is
# asserted to occur EXACTLY ONCE in its row -- see stage_task721_templates.
#
# Anchors never contain a newline: line endings in `prompt_templates` are MIXED
# (all six en rows plus zh inference, ja main_idea and ja author_purpose are
# CRLF; the other nine are LF), so an escaped newline inside an anchor silently
# matches nothing in half the table. The splice matches each block's EOL to the
# row it is going into.
#
# These are not uniform because the rows are not uniform: the four TASK-722 /
# TASK-724 native rewrites have their own structure, and the ja author_purpose
# row has no section headings at all, so its anchor is the output sentence
# itself (in its post-json-repair form).
ANCHORS: dict[tuple[str, str], str] = {
    ('question_literal_detail', 'en'): '**Your Task:**',
    ('question_supporting_detail', 'en'): '**Your Task:**',
    ('question_main_idea', 'en'): '**Your Task:**',
    ('question_inference', 'en'): '**Your Task:**',
    ('question_author_purpose', 'en'): '**Your Task:**',
    ('question_vocabulary_context', 'en'): '**Your Task:**',

    ('question_literal_detail', 'zh'): '**你的任务：**',
    ('question_supporting_detail', 'zh'): '**你的任务：**',
    ('question_main_idea', 'zh'): '**你的任务：**',
    ('question_author_purpose', 'zh'): '**你的任务：**',
    ('question_inference', 'zh'): '六、输出要求',
    ('question_vocabulary_context', 'zh'): '八、输出要求',

    ('question_literal_detail', 'ja'): '**あなたのタスク：**',
    ('question_supporting_detail', 'ja'): '**あなたのタスク：**',
    ('question_inference', 'ja'): '**あなたのタスク：**',
    ('question_main_idea', 'ja'): '出力：',
    ('question_vocabulary_context', 'ja'): '【出力形式】',
    ('question_author_purpose', 'ja'):
        '最終的な出力は、次の JSON 形式のみとしてください。',
}


# --------------------------------------------------------------------------- en
#
# One shared rule set (the inverted 1-5 scale), one family paragraph, one worked
# set per type. The worked sets deliberately reuse each row's OWN few-shot
# passage so the block does not introduce a second, unrelated scenario.

_EN_RULES = """\
**Building the three wrong choices**

Every wrong choice you write is scored 1-5 after generation, and a choice
scored 1 or 2 discards the whole question. Build to that scale:

- **Stay inside the passage's own subject.** A wrong choice that names a real
  thing from the same subject is a GOOD wrong choice *even when the passage
  never mentions it* — being absent from the text is precisely what makes it
  wrong. Never avoid an option merely because the passage does not contain it.
- **Never write a choice that is also arguably correct.** If a careful reader
  could defend it against your stated answer, the question has two answers and
  is thrown away. This is the most damaging failure mode.
- **Never write a choice that paraphrases the correct answer,** or sits so close
  to it that a learner cannot tell the two apart.
- **Never reach into a different subject** (an emotion offered as a choice in a
  passage about electrical circuits), and never write anything absurd.
- Keep all four choices comparable in length, grammatical shape and level of
  detail, so the answer is not identifiable by its form alone.
"""

_EN_FAMILY = {
    'fact': """\
For this question type the wrong choices are same-subject facts or conclusions
the passage does not support. The strongest ones are: a real item from the
passage's domain that the text never states; a detail the passage *does* state
but attached to the wrong person, time, place or cause; or a conclusion that
reaches further than the passage's evidence licenses.
""",
    'intent': """\
For this question type the wrong choices are other purposes, tones or messages a
reader might attribute to the author. "Different subject" here means an intent
the text gives no sign of — *not* a topic the passage happens to omit. The
strongest ones are: a stance the passage's own wording contradicts; a real but
secondary purpose offered as the main one; or a message that is too narrow (one
detail) or too broad (beyond the passage's scope).
""",
    'sense': """\
For this question type the wrong choices are competing MEANINGS of the target
expression, so weigh them against the word itself, not against the passage's
subject. An option with nothing to do with the passage's topic is NOT off-subject
here — it is the ordinary case. The strongest ones are: the literal reading of a
figurative expression; another established sense of a polysemous word; or a
near-sense that differs in degree, object or register.
""",
}

_EN_WORKED = {
    'literal_detail': """\
Worked example — using the passage above ("...designed by engineer Joseph
Strauss"), for the question "Who designed the Golden Gate Bridge?" with the
answer "Joseph Strauss":
  GOOD      — "Othmar Ammann": a real bridge engineer of the same era and
              domain whom the passage never names; that absence is why he is
              the wrong choice, and a reader who did not check will still be
              tempted.
  REJECTED  — "An American engineer": Strauss was one, so this is arguably
              correct. Two defensible answers, question discarded.
  REJECTED  — "The engineer who designed it": a paraphrase of the answer rather
              than a competitor to it.
""",
    'supporting_detail': """\
Worked example — using the passage above (profits up 15% from strong online
sales and reduced operating costs), for the question "What contributed to the
profit increase?" with the answer "Strong online sales and reduced operating
costs":
  GOOD      — "Higher prices and a new product line": ordinary drivers of profit
              in the same domain that the passage never claims, tempting to a
              reader who skimmed.
  REJECTED  — "The new e-commerce platform": the passage credits it with the
              traffic growth behind those online sales, so it is arguably
              correct.
  REJECTED  — "Good internet sales and lower running costs": the answer in
              synonyms.
""",
    'inference': """\
Worked example — using the passage above (Dr. Martinez, the empty doorway, the
unfilled chairs), for the question "What can be inferred about her situation?"
with the answer "She is waiting for attendees who are late or not coming":
  GOOD      — "She has come to the wrong room": entirely plausible in this
              scene, and nothing in the clues supports it — which is exactly why
              it is wrong.
  REJECTED  — "The presentation has not started yet": also a sound inference
              from the same clues, so it is arguably correct.
  REJECTED  — "She is expecting people who have not shown up": the answer
              restated.
""",
    'main_idea': """\
Worked example — using the passage above (community gardens, rooftop farms and
vertical gardens making cities more sustainable), for the question "What is the
main idea?" with the answer "Urban farming initiatives are making cities more
sustainable":
  GOOD      — "Cities are running out of space for conventional agriculture": a
              real urban-farming talking point that this passage never makes.
  REJECTED  — "Urban farming has several environmental benefits": true of the
              passage and defensible as its main idea — arguably correct.
  REJECTED  — "Urban agriculture is helping cities become more sustainable": the
              answer in synonyms.
""",
    'author_purpose': """\
Worked example — using the passage above (clear benefits, a rushed approval
process, a conditional positive close), for the question "What is the author's
overall tone?" with the answer "Cautiously optimistic with reservations":
  GOOD      — "Nostalgic for the previous policy": a real authorial stance that
              the passage's forward-looking close plainly contradicts.
  REJECTED  — "Critical of how the policy was approved": the passage does
              criticise the rushed process, so this is arguably correct.
  REJECTED  — "Hopeful but with some concerns": the answer reworded.
""",
    'vocabulary_context': """\
Worked example — using the passage above ("The CEO turned a blind eye to the
accounting irregularities"), for the question "What does 'turn a blind eye'
mean?" with the answer "To deliberately ignore something":
  GOOD      — "To lose sight in one eye": the literal reading of the idiom. It
              has nothing to do with accounting, and for THIS question type that
              is correct behaviour, not an off-subject error.
  REJECTED  — "To fail to notice something": a near-sense a reader can defend
              against the answer — arguably correct.
  REJECTED  — "To intentionally overlook something": a synonym of the answer.
""",
}


def _en_block(type_code: str) -> str:
    return (f'---\n\n{_EN_RULES}\n{_EN_FAMILY[FAMILY[type_code]]}\n'
            f'{_EN_WORKED[type_code]}\n---\n\n')


# ------------------------------------------------------------------- accessors


class _Blocks:
    """`BLOCKS[(family, lang)][type_code]` -> block text.

    en is generated from this module; zh/ja are read from the authored files on
    first access, so `stage_task721_templates.py --only before` works before the
    authoring run has happened.
    """

    def __getitem__(self, key: tuple[str, str]) -> dict[str, str]:
        family, lang = key
        types = [t for t, f in FAMILY.items() if f == family]
        if lang == 'en':
            return {t: _en_block(t) for t in types}
        out = {}
        for t in types:
            path = os.path.join(BLOCK_DIR, f'question_{t}_{lang}.txt')
            if not os.path.exists(path):
                raise SystemExit(
                    f'[error] missing authored block {path} — run '
                    f'scripts/author_task721_blocks.py --lang {lang}')
            with open(path, encoding='utf-8') as fh:
                out[t] = fh.read()
        return out


BLOCKS = _Blocks()
