"""Build the v7 ablation bodies: same two axes, no directional nudge.

WHY THIS EXISTS
---------------
The 2026-08-20 two-axis measurement compared v7 against the live v4/v6 rows and
found the review band going from ~0 to 22-47% of questions. That comparison
cannot say whether the judge became honest or merely compliant, because
**neither arm is a neutral observer** — each prompt contains an emphatic
instruction that would produce its own result on its own:

    v4/v6, band 5:  "THIS IS THE NORMAL, EXPECTED RATING for a sound
                     distractor - most good distractors should score 5."
    v7,     band 3:  "Use this whenever you are unsure ... Do not guess a 4
                     or a 2 instead."

This script produces the missing third arm: v7 with the *directional* language
removed from **both** ends, so the bands are defined but no band is advertised
as a default. If the unsure ratings largely survive, the items are doing the
work. If they collapse, the wording was.

    python scripts/build_distractor_judge_ablation.py
    python scripts/measure_judge_flag_rate.py --sample data/eval/task721_before.json \
        --arms "v7=7:,abl=@distractor_judge_abl:" --out data/eval/ablation.json

DELETION ONLY, AND THAT IS THE POINT
------------------------------------
Every edit below removes a span and stitches the remainder. Nothing is
rewritten and nothing is added, so the ablation differs from v7 in exactly the
manipulated variable and nothing else. A re-authored "neutral" prompt would be
a different prompt, not an ablation, and could not attribute anything.

Both directions are removed, not just the pushes toward 3. Stripping "use 3 if
unsure" while leaving "5 is the expected rating" and "4 is the target" standing
would build the answer into the instrument.

Every pattern is asserted to appear exactly once. A silent no-op here would
produce an "ablation" byte-identical to v7 that quietly reports "the wording
made no difference" — the most expensive possible failure, because it looks
like a result.
"""

from __future__ import annotations

import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL = os.path.join(ROOT, 'data', 'eval')

SRC = 'distractor_judge_v7_{lang}.txt'
DST = 'distractor_judge_abl_{lang}.txt'

# (description, exact span to find, replacement) per language.
# Descriptions are ASCII so failures print on a cp1252 console.
EDITS: dict[str, list[tuple[str, str, str]]] = {
    'en': [
        ('fit-5 default anchor',
         '5 = clearly the passage\'s subject or domain. THIS IS THE NORMAL, '
         'EXPECTED RATING — most sound distractors score 5.',
         '5 = clearly the passage\'s subject or domain.'),
        ('fit-3 use-if-unsure nudge',
         '3 = NOT CONFIDENT. You cannot decide whether it belongs to this '
         'subject. Use this whenever you are unsure — it sends the item to a '
         'human reviewer, which is what it is for. Do not guess a 4 or a 2 '
         'instead.',
         '3 = You cannot decide whether it belongs to this subject.'),
        ('confusability target statement',
         'Both ends of this axis are problems. The target is 4.',
         'Both ends of this axis are problems.'),
        ('confusability-4 target anchor',
         'yet a careful reader can rule it out. THIS IS THE TARGET.',
         'yet a careful reader can rule it out.'),
        ('confusability-3 use-if-unsure nudge',
         '3 = NOT CONFIDENT. You cannot judge how tempting it would be. Use '
         'this whenever you are unsure. Do not guess a 4 or a 2 instead.',
         '3 = You cannot judge how tempting it would be.'),
    ],
    'zh': [
        ('fit-5 default anchor',
         '5＝明确属于文章的学科／领域。这是合格干扰项正常且应有的评分，大多数好干扰项都是5。',
         '5＝明确属于文章的学科／领域。'),
        ('fit-3 use-if-unsure nudge',
         '3＝拿不准。你无法判断它到底属不属于这个学科。只要没有把握就打3——这一档会把该题送交'
         '人工复核，它就是为此设的。不要用4或2去蒙。',
         '3＝你无法判断它到底属不属于这个学科。'),
        ('confusability target statement',
         '这个轴的两端都是问题，目标值是4。',
         '这个轴的两端都是问题。'),
        ('confusability-4 target anchor',
         '而细心的读者能排除它。这是目标值。',
         '而细心的读者能排除它。'),
        ('confusability-3 use-if-unsure nudge',
         '3＝拿不准。你无法判断它到底有多大迷惑性。只要没有把握就打3。不要用4或2去蒙。',
         '3＝你无法判断它到底有多大迷惑性。'),
        ('restated use-3 rule in the scoring-procedure paragraph',
         '若任一轴拿不准，就给该轴3。若两轴都拿不准，就分别给3。',
         ''),
    ],
    'ja': [
        ('fit-5 default anchor',
         '- 5 ＝ 文章の分野・領域に明らかに属する。これは妥当な誤答にとって正常かつ期待される'
         '評価であり、良い誤答のほとんどは 5 になります。',
         '- 5 ＝ 文章の分野・領域に明らかに属する。'),
        ('fit-3 use-if-unsure nudge',
         '- 3 ＝ 確信が持てない。その分野に属するかどうか判断できない。少しでも迷ったら 3 を'
         '付けてください。この段階は人手の確認に回すためにあります。当て推量で 4 や 2 を付けて'
         'はいけません。',
         '- 3 ＝ その分野に属するかどうか判断できない。'),
        ('confusability target statement',
         'この軸は両端がどちらも問題で、目標値は 4 です。',
         'この軸は両端がどちらも問題です。'),
        ('confusability-4 target anchor',
         'しかし注意深い読み手は除外できる。これが目標値です。',
         'しかし注意深い読み手は除外できる。'),
        ('confusability-3 use-if-unsure nudge',
         '- 3 ＝ 確信が持てない。どれだけ引っかかりやすいか判断できない。迷ったら 3 を付け、'
         '当て推量で 4 や 2 を付けないこと。',
         '- 3 ＝ どれだけ引っかかりやすいか判断できない。'),
    ],
}


def build(lang: str) -> tuple[str, int]:
    src = os.path.join(EVAL, SRC.format(lang=lang))
    with open(src, encoding='utf-8') as fh:
        body = fh.read()
    before = len(body)

    for label, find, repl in EDITS[lang]:
        n = body.count(find)
        if n != 1:
            raise SystemExit(
                f'[error] {lang}: "{label}" matched {n} times, expected exactly 1. '
                f'The v7 body has changed; re-derive the span before trusting any '
                f'ablation result.'
            )
        body = body.replace(find, repl, 1)

    # The ablation must still be a valid judge prompt: six slots, doubled JSON
    # braces, renderable. An unrenderable body raises inside the judge's try
    # block and safe-accepts everything, which would read as "0 rejects".
    body.format('(passage)', '(question)', '(answer)', '1. A\n2. B\n3. C',
                'vocabulary_context', '(subject)')
    for i in range(6):
        if body.count('{%d}' % i) != 1:
            raise SystemExit(f'[error] {lang}: slot {{{i}}} is not present exactly once')

    # Nothing may have been ADDED. Deletion-only is the property that makes this
    # an ablation rather than a rewrite, so assert it rather than trusting it.
    if len(body) >= before:
        raise SystemExit(f'[error] {lang}: body did not shrink ({before} -> {len(body)})')

    dst = os.path.join(EVAL, DST.format(lang=lang))
    with open(dst, 'w', encoding='utf-8', newline='') as fh:
        fh.write(body)
    return dst, before - len(body)


def main() -> int:
    for lang in ('zh', 'en', 'ja'):
        dst, removed = build(lang)
        with open(dst, encoding='utf-8') as fh:
            body = fh.read()
        print(f'  {lang}: {len(body):>5} chars (-{removed})  '
              f'md5 {hashlib.md5(body.encode("utf-8")).hexdigest()}  -> {dst}')
    print('\nAblation arm:  --arms "abl=@distractor_judge_abl:"')
    return 0


if __name__ == '__main__':
    sys.exit(main())
