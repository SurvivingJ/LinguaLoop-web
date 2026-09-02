"""Stem-template rotation for topic-independent question types (plan §1, T1.1).

The problem this solves is *not* duplicate content. Measured on the live
corpus, 9.4% of question stems repeat while the choice sets behind them are
almost entirely distinct — the worst offender is one Japanese stem appearing
36 times across 36 unrelated topics (fermentation, wine terroir, venture
capital):

    この文章における筆者の態度として最も適切なものはどれか。

The generator is doing its job; the *surface phrasing* is what reads as
repetitive. Duplication concentrates in the question types that are
topic-independent — the ones that ask about the passage as a whole rather than
about anything in it — so those are the only types with a pool here. A
literal_detail stem varies because the detail does.

Mechanism: pick a stem deterministically from the type's pool by hashing a
stable key for the test, and hand it to the prompt as the required phrasing.
No extra LLM call, so the marginal cost is zero. Deterministic so regenerating
the same test produces the same stem and a diff stays readable.

Note this is *complementary* to the TASK-740 dedup work, not covered by it:
``services/test_generation/dedup.py`` scopes both its checks to
(topic_id, target_age_tier) and deliberately never compares across tiers, and
only 5 of the 29 measured duplicate groups are within-topic.

zh/ja phrasings below are ordinary test-register wording, but they have not had
a native review pass. ``TEST_GEN_STEM_ROTATION`` (default on) is the kill
switch if any of them reads badly in production — one stilted stem is still a
better failure than the same stem 36 times, but the switch means that call can
be reversed without a deploy.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import List, Optional, Sequence

logger = logging.getLogger(__name__)

# Question types whose stem is a property of the *task*, not of the passage.
# Only these rotate; the rest get their variety from the passage itself.
ROTATED_QUESTION_TYPES = ('main_idea', 'author_purpose', 'inference')

# language_code -> question_type -> pool of equivalent stems.
# Each pool is 6-7 deep: enough that a stem recurring twice in a learner's
# recent history is unremarkable, small enough that every entry is one somebody
# has actually read.
STEM_POOLS: dict[str, dict[str, tuple[str, ...]]] = {
    'en': {
        'main_idea': (
            'What is the main idea of this passage?',
            'Which statement best expresses the central point of the passage?',
            'The passage is primarily about which of the following?',
            'Which of the following best summarises the passage as a whole?',
            "What is the writer's principal concern in this passage?",
            'Taken as a whole, this passage is best described as which of the following?',
        ),
        'author_purpose': (
            'Why did the author write this passage?',
            "The author's main purpose in this passage is to do which of the following?",
            "Which best describes the author's attitude towards the subject?",
            'The tone of this passage is best described as which of the following?',
            'What is the author trying to achieve in this passage?',
            'How does the author appear to regard the subject of the passage?',
            'This passage was most likely written in order to do which of the following?',
        ),
        'inference': (
            'What can be inferred from this passage?',
            'Which conclusion is best supported by the passage?',
            'The passage suggests which of the following?',
            'Based on the passage, which statement is most likely true?',
            'Which of the following can reasonably be concluded from the passage?',
            'Which of the following does the passage imply but not state directly?',
        ),
    },
    'zh': {
        'main_idea': (
            '这篇文章的主旨是什么？',
            '下列哪一项最能概括本文的中心内容？',
            '本文主要讨论的是什么？',
            '以下哪一项最能表达文章的核心观点？',
            '就全文而言，作者主要想说明什么？',
            '这段文字的主要内容是下列哪一项？',
        ),
        'author_purpose': (
            '作者写这篇文章的目的是什么？',
            '下列哪一项最能说明作者的写作意图？',
            '作者对这一主题的态度是怎样的？',
            '本文的语气最接近下列哪一项？',
            '作者写作本文最可能是为了什么？',
            '从文中可以看出作者的立场是什么？',
            '下列哪一项最符合作者在文中表现出的态度？',
        ),
        'inference': (
            '从这篇文章中可以推断出什么？',
            '下列哪一项结论最有文中依据？',
            '根据本文，以下哪一项最可能成立？',
            '文章暗示了下列哪一项？',
            '由本文可以合理推知什么？',
            '下列哪一项是文中未直接说明但可以推出的？',
        ),
    },
    'ja': {
        'main_idea': (
            'この文章の主旨として最も適切なものはどれか。',
            '本文の中心的な内容を最もよく表しているものはどれか。',
            'この文章は主に何について述べているか。',
            '全体として、この文章が伝えようとしていることはどれか。',
            '本文の要旨として最も適切なものはどれか。',
            '筆者がこの文章で最も述べたいことはどれか。',
        ),
        'author_purpose': (
            '筆者がこの文章を書いた目的として最も適切なものはどれか。',
            # The 36-times offender, kept as one of seven rather than banned:
            # it is correct Japanese, and the defect was its frequency.
            'この文章における筆者の態度として最も適切なものはどれか。',
            '本文の筆者の立場に最も近いものはどれか。',
            'この文章の調子を最もよく表しているものはどれか。',
            '筆者はこの主題をどのように捉えていると考えられるか。',
            'この文章が書かれた意図として最も適切なものはどれか。',
            '本文から読み取れる筆者の考え方はどれか。',
        ),
        'inference': (
            'この文章から推測できることとして最も適切なものはどれか。',
            '本文の内容から導かれる結論として最も適切なものはどれか。',
            'この文章が示唆していることはどれか。',
            '本文に基づくと、最も可能性が高いものはどれか。',
            '本文から合理的に推論できることはどれか。',
            '本文で直接は述べられていないが読み取れることはどれか。',
        ),
    },
}


def is_enabled() -> bool:
    """Whether stem rotation is active. Kill switch: TEST_GEN_STEM_ROTATION=0."""
    return os.getenv('TEST_GEN_STEM_ROTATION', '1').strip().lower() not in (
        '0', 'false', 'no', 'off',
    )


def pool_for(language_code: Optional[str], question_type: str) -> tuple[str, ...]:
    """The stem pool for a (language, type), or () when there isn't one."""
    if not language_code:
        return ()
    return STEM_POOLS.get(language_code.lower(), {}).get(question_type, ())


def select_stem(
    language_code: Optional[str],
    question_type: str,
    rotation_key: str,
) -> Optional[str]:
    """Pick this test's stem for ``question_type``, or None when not rotated.

    ``rotation_key`` is any stable identifier for the test being generated —
    the orchestrator passes ``f'{topic_id}:{tier_id}'``, since the test row
    does not exist yet when questions are written. Selection is a hash, not
    ``random``, so a regeneration of the same test produces the same stem.
    """
    if not is_enabled():
        return None
    pool = pool_for(language_code, question_type)
    if not pool:
        return None
    digest = hashlib.sha256(
        f'{rotation_key}|{question_type}'.encode('utf-8')
    ).digest()
    return pool[int.from_bytes(digest[:8], 'big') % len(pool)]


def build_directive(
    language_code: Optional[str],
    question_type: str,
    rotation_key: str,
    recent_stems: Optional[Sequence[str]] = None,
) -> str:
    """The prompt fragment to append, or '' when there is nothing to say.

    Two parts, either of which may be absent:

      * T1.1 — the rotated stem for this test.
      * T1.2 — the most recent stems already used for this (language, type),
        as a do-not-reuse list. This catches the case the pool cannot: a pool
        of six still repeats every sixth test, and the recency list pushes the
        model off a phrasing a learner has just seen.

    Appended in code rather than through a template placeholder so it needs no
    prompt_templates migration and works for both the DB-template and legacy
    inline paths — same approach as the ``avoid_context`` block.
    """
    parts: List[str] = []

    stem = select_stem(language_code, question_type, rotation_key)
    if stem:
        parts.append(
            'QUESTION STEM — use this exact wording for the question itself:\n'
            f'{stem}\n'
            'Write the four answer choices to fit this stem. Do not reword the '
            'stem, and do not append the topic to it.'
        )

    avoid = _recent_to_avoid(recent_stems, stem)
    if avoid:
        parts.append(
            'STEMS ALREADY IN RECENT USE — do NOT reuse any of these '
            'phrasings:\n'
            + '\n'.join(f'- {s}' for s in avoid)
        )

    return '\n\n'.join(parts)


def _recent_to_avoid(
    recent_stems: Optional[Sequence[str]], chosen: Optional[str],
) -> List[str]:
    """De-duplicated recent stems, minus the one we just asked for.

    Listing the chosen stem as forbidden while also requiring it is the kind of
    self-contradicting instruction that makes a model pick neither — the same
    trap recorded in the ja judge/generator doctrine.
    """
    if not recent_stems:
        return []
    seen = set()
    out: List[str] = []
    for stem in recent_stems:
        text = (stem or '').strip()
        if not text or text == chosen or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out
