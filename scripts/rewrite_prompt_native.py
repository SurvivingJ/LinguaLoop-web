"""Re-author zh/ja `prompt_templates` rows natively, with a mechanical contract check.

Generalises the TASK-722 harness (`rewrite_vocab_context_prompt.py`) from one task
to a registry. Each entry declares exactly what the rewrite must preserve, and the
script refuses to emit anything that violates it.

WHY A REGISTRY AND NOT A LOOP OVER EVERY ROW
--------------------------------------------
`audit_prompt_latin.py` reports Latin runs; it cannot tell which of them are
*load-bearing*. Most are. Translating them breaks the pipeline silently:

  * `no_relation` / `no_inflection` / `no_collocation` are typed-schema escape
    tokens (`ladder_typed.py:74` — `ERROR_TOKEN = 'no_relation'`)
  * `corpus_validated` / `llm_asserted` are grounding constants
    (`collocation_grounding.py:53-54`)
  * the 27 persona archetypes are matched literally (`scenario_generator.py:466`)
  * `plain/polite/honorific/humble/formal/casual` must match the `{register}`
    value injected into `ladder_p1_sentence_judge`

and worst of all:

  * `cloze.py:110` is `verdicts[d] = 'reject' if v == 'reject' else 'keep'`.
    A translated verdict word does not raise — it falls through to `keep`, so
    every distractor survives and the judge becomes an expensive no-op.

So each spec lists `required_literals`, and a rewrite that drops one is rejected
before it can reach a migration.

Usage::

    python scripts/rewrite_prompt_native.py --task cloze_distractor_judge --lang zh \\
        --out data/eval/cloze_distractor_judge_zh.txt

    # re-verify an existing file without spending anything
    python scripts/rewrite_prompt_native.py --task cloze_distractor_judge --lang zh \\
        --check data/eval/cloze_distractor_judge_zh.txt

Every call is logged to `llm_calls` under `pipeline='diag'` so authoring spend
does not contaminate per-pipeline production cost reporting.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.llm_service import call_llm  # noqa: E402
from services.supabase_factory import SupabaseFactory  # noqa: E402

DEFAULT_MODEL = 'qwen/qwen3.8-max'

# `qwen3.8-max` is a thinking model: reasoning tokens come out of the same
# completion budget as the answer. At 6,000 it spent the whole allowance on
# reasoning and returned `finish_reason='length'` with empty content, which
# surfaces as a bare "LLM returned empty content" — a misleading error for what is
# really a budget problem. Observed ~7-9k reasoning tokens for a brief this size.
DEFAULT_MAX_TOKENS = 32000

# Underscores bind. `question_text` is ONE run; splitting on them manufactures two
# unmatchable tokens (`question`, `text`) and fails clean rewrites.
LATIN_RUN = re.compile(r'[A-Za-z][A-Za-z_]*')

LANG_ID = {'zh': 1, 'ja': 3}
LANG_NAME = {'zh': '中文', 'ja': '日本語'}


@dataclass(frozen=True)
class Spec:
    """Everything a rewrite of one `prompt_templates` row must honour."""

    task_name: str
    langs: tuple[str, ...]
    # Must survive verbatim and appear exactly once — str.format renders these.
    placeholders: tuple[str, ...]
    # Human-readable gloss per placeholder, shown to the authoring model.
    placeholder_notes: dict[str, dict[str, str]]
    # Literal ASCII the downstream parser compares against. Dropping one is fatal.
    required_literals: tuple[str, ...]
    # The exact JSON shape the prompt must instruct the model to emit.
    json_block: str
    # Latin the rewrite may legitimately contain (machinery + proper nouns).
    allowed_latin: frozenset[str]
    # Per-language authoring brief. Written in the target language on purpose: a
    # brief in English invites an English-flavoured answer, the exact failure mode.
    brief: dict[str, str]
    # Arguments for the str.format smoke check. Rows are split between named
    # placeholders (`{prose}`) and positional ones (`{0}`); the judge rows in
    # services/exercise_generation/judges are all positional, so both have to
    # render or the check passes a row that will explode at judge time.
    render_args: dict = field(default_factory=dict)
    render_positional: tuple = ()
    length_hint: str = '1,200〜2,600'


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

SPECS: dict[str, Spec] = {}


def _register(spec: Spec) -> None:
    SPECS[spec.task_name] = spec


# --- cloze_distractor_judge -------------------------------------------------
# Judges TL-only material (a CJK sentence, a CJK answer, CJK distractors) with a
# wholly English prompt, byte-identical across zh and ja. The clearest case for a
# native rewrite in the whole table.

_register(Spec(
    task_name='cloze_distractor_judge',
    langs=('zh', 'ja'),
    placeholders=('{sentence_with_blank}', '{correct_answer}', '{distractors_numbered}'),
    placeholder_notes={
        'zh': {
            '{sentence_with_blank}': '带空格的句子（题干）',
            '{correct_answer}': '出题者指定的正确答案',
            '{distractors_numbered}': '待评判的干扰项列表（每行一个，从 1 开始编号）',
        },
        'ja': {
            '{sentence_with_blank}': '空欄のある文（問題文）',
            '{correct_answer}': '出題者が指定した正解',
            '{distractors_numbered}': '評価対象の誤答選択肢の一覧（1 から番号付き、1 行 1 件）',
        },
    },
    required_literals=('"verdict"', '"reason"', '"keep"', '"reject"'),
    json_block='{{"1": {{"verdict": "keep", "reason": "..."}}, '
               '"2": {{"verdict": "reject", "reason": "..."}}}}',
    allowed_latin=frozenset({'verdict', 'reason', 'keep', 'reject', 'JSON',
                             'sentence_with_blank', 'correct_answer',
                             'distractors_numbered'}),
    render_args={
        'sentence_with_blank': '（示例句子 / 例文）',
        'correct_answer': '（示例 / 例）',
        'distractors_numbered': '1. A\n2. B\n3. C',
    },
    brief={
        'zh': """\
你是一位中文母语的语言测评专家。请**从零开始**用中文撰写一份「完形填空干扰项评判」提示词（prompt）。

这份提示词会被送给另一个模型，让它逐一评判每个干扰项是否合格。

## 背景：为什么要重写

现有的中文提示词其实是一份**英文**提示词——它逐字逐句都是英文，而且和日语版一模一样。
但它评判的材料全部是中文：中文句子、中文正确答案、中文干扰项。用英文的语感去判断
「这个词填进这个中文句子里通不通顺」，会漏掉搭配、语体、离合词、量词、体标记等
汉语特有的问题。请用**汉语自身的语感和术语**重新构思整份提示词。

## 评判任务

学习者看到一个带空格的句子和四个选项。**只有一个**是预定的正确答案，另外三个
（干扰项）**每一个都必须在这个句子里明显说不通**。你要逐个评判干扰项。

- 判为「合格」：填进空格里语法上可能成立，但在**这个**句子里明显不对——语义不合、
  搭配不当、体或时态不合、语体不符、或者动词的配价（能带什么宾语）不对。
  一个称职的母语者绝不会把它判为正确。
- 判为「不合格」：这个干扰项本身也能被一个称职的读者选作**合理的填空答案**
  （即语法和语义都能接受，哪怕不如预定答案地道）。近义词、同义词、以及在语境中
  说得通的替代说法，**一律判为不合格**。

## 判断尺度

从严。若你**拿不准**某个干扰项在语境中是否可以接受，就判为不合格。
一份好的完形填空题，模棱两可的干扰项应当为零。

## 请在正文中体现的汉语特有考量

请自行判断并写入正文，例如：固定搭配与自由组合的区别、离合词能否带宾语、
量词与名词的匹配、「了 / 着 / 过」的体标记是否与句子时间信息一致、
书面语与口语的语体差异、单双音节的韵律搭配。请用中文的术语表述，不要照搬英文语法术语。
""",
        'ja': """\
あなたは日本語母語の言語評価の専門家です。「穴埋め問題の誤答選択肢を評価する」ための
プロンプトを、**ゼロから**日本語で執筆してください。

このプロンプトは別のモデルに渡され、誤答選択肢を 1 つずつ評価させるために使われます。

## 背景：なぜ書き直すのか

現行の日本語プロンプトは、実際には**英語**のプロンプトです。全文が英語であり、
しかも中国語版とまったく同じ文面です。しかし評価する材料はすべて日本語です——
日本語の文、日本語の正解、日本語の誤答選択肢。英語の語感で「この語をこの日本語の文に
入れて自然かどうか」を判断すると、助詞の適合、活用形、自他の対応、敬語レベル、
コロケーションといった日本語固有の問題を見落とします。**日本語自身の語感と用語**で
プロンプト全体を構想し直してください。

## 評価する作業

学習者は空欄のある文と 4 つの選択肢を見ます。**正解は 1 つだけ**で、残りの 3 つ
（誤答選択肢）は**どれもこの文では明らかに成り立たない**必要があります。
誤答選択肢を 1 つずつ評価してください。

- 「適格」と判定する場合：空欄に入れると文法的には成立しうるが、**この**文では
  明らかに誤り——意味が合わない、コロケーションが不自然、アスペクトやテンスが合わない、
  語域（丁寧さ）が合わない、あるいは項構造（どんな格をとるか）が合わない。
  力のある母語話者が正解と見なすことは決してない。
- 「不適格」と判定する場合：その誤答選択肢自体も、力のある読み手が**妥当な答え**として
  選びうる（文法的にも意味的にも許容できる。正解ほど自然でなくてもよい）。
  類義語・同義語・文脈上成り立つ言い換えは、**すべて不適格**とすること。

## 判定の厳しさ

厳しく判定してください。文脈上その選択肢が許容されるかどうか**確信が持てない**場合は、
不適格と判定します。良い穴埋め問題では、曖昧な誤答選択肢は 0 件であるべきです。

## 本文に盛り込むべき日本語固有の観点

ご自身の判断で本文に書き込んでください。例：格助詞との適合、自動詞と他動詞の対応、
活用形（テ形・タ形・可能形など）の妥当性、「ている / てある / ておく」の使い分け、
和語・漢語・外来語の文体差、敬語レベルの一致、慣用的なコロケーション。
英文法の用語をそのまま持ち込まず、日本語の用語で記述してください。
""",
    },
))


# --- test_distractor_plausibility (v7, two axes) ----------------------------
# TASK-719 splits the single 1-5 rating onto the two axes it was conflating.
# The bands themselves live in `schemas.axes_to_verdict`; the brief below has to
# restate them in the target language because the judging model only ever sees
# the prompt. If you change one, change both — a prompt whose bands disagree with
# the Python cut points is the failure mode TASK-723 spent a week unwinding.
#
# Slots {4} (question type) and {5} (subject keywords) stay LABELS, printed as
# context. TASK-717 measured a type-conditional rubric on {4} (prompt v5) and it
# was neutral-to-harmful under both judge models; do not let a rewrite
# reintroduce one.

_DISTRACTOR_PLACEHOLDER_NOTES = {
    'zh': {
        '{0}': '作为出题材料的文章',
        '{1}': '题目（问题）',
        '{2}': '出题者指定的正确答案',
        '{3}': '待评判的干扰项列表（每行一个，从 1 开始编号）',
        '{4}': '题目类型的代号（由程序注入，例如 vocabulary_context）',
        '{5}': '本文章的学科／领域关键词（由程序注入；缺省时是一句「请自行从文章推断」的说明）',
    },
    'ja': {
        '{0}': '出題の材料となる文章',
        '{1}': '問題（設問）',
        '{2}': '出題者が指定した正解',
        '{3}': '評価対象の誤答選択肢の一覧（1 から番号付き、1 行 1 件）',
        '{4}': '問題タイプの符号（プログラムが注入。例：vocabulary_context）',
        '{5}': 'この文章の分野・領域のキーワード（プログラムが注入。無い場合は「文章から推測せよ」という文が入る）',
    },
}

_register(Spec(
    task_name='test_distractor_plausibility',
    langs=('zh', 'ja'),
    placeholders=('{0}', '{1}', '{2}', '{3}', '{4}', '{5}'),
    placeholder_notes=_DISTRACTOR_PLACEHOLDER_NOTES,
    required_literals=('JSON',),
    json_block='{{"1": [5, 4, "……"], "2": [5, 5, "……"], "3": [2, 1, "……"]}}',
    allowed_latin=frozenset({'JSON', 'vocabulary_context'}),
    render_positional=(
        '（示例文章 / 例文）',
        '（示例题目 / 例の設問）',
        '（示例答案 / 例の正解）',
        '1. A\n2. B\n3. C',
        'vocabulary_context',
        '（示例学科 / 例の分野）',
    ),
    length_hint='1,400〜2,400',
    brief={
        'zh': """\
你是一位中文母语的语言测评专家。请**从零开始**用中文撰写一份「阅读理解题干扰项评判」
提示词（prompt）。这份提示词会被送给另一个模型，让它给每一个干扰项打**两个**分数。

## 背景：为什么要重写

现行提示词只让评判模型打**一个** 1 到 5 分，但这一个数字其实同时在回答两个互不相干的问题：

1. 这个选项属不属于文章所讲的那个学科／领域？
2. 学习者会不会把它和正确答案混淆？

这两件事是可以分开的：一个跑题的选项照样可能很有迷惑性（比如题目问「靠什么让灯亮」，
选项「阳光」并不属于电路这个领域，可是「光」字仍然会勾住粗心的读者）；反过来，一个
完全切题的选项也可能一眼就被排除。把两者压进一个整数，就分不清究竟是哪一种缺陷。
所以新版必须要求**两个轴分别打分**，并且明确交代：两轴独立评定，不得让一个轴的分数
牵动另一个轴。

## 必须写进正文的一段纠偏说明（放在两个轴的说明之前）

这一段在实测中是有效的，请务必用中文重新表述，不要删减它的要点：

干扰项的全部意义就在于它是**错误的**。在事实上不正确、「显然不是答案」、
或者文章里从头到尾没有提到，这些都是**必需的**——正是它们使一个选项成为干扰项，
而不是缺点。一个指向与文章同一学科的真实事物的干扰项，即使该事物从未在文中出现，
也是好的干扰项；它没有出现在文中，恰恰就是它为何是错误选项的原因。绝不要因为干扰项
没有出现在文章中、因为它是错的、或者因为它容易被排除，而压低它的评分。

## 第一个轴：切题度（这个选项属不属于文章的学科？）

只看学科归属，不看有没有迷惑性——迷惑性是第二个轴的事。
「另一个学科」是字面意思：在一篇讲电路的文章里，把一种情绪或一项社交活动作为选项。
它**不**表示「属于同一学科、只是文章碰巧没提到的事物」。

- 5 ＝ 明确属于文章的学科／领域。**这是合格干扰项正常且应有的评分，大多数好干扰项都是 5。**
- 4 ＝ 大致属于这个学科：相邻的领域，学习者仍会觉得它算是一路的。
- 3 ＝ **拿不准。** 你无法判断它到底属不属于这个学科。只要没有把握就打 3——
  这一档会把该题送交人工复核，它就是为此设的。不要用 4 或 2 去蒙。
- 2 ＝ 明显属于与文章不同的另一个学科。
- 1 ＝ 根本不是一个说得通的选项：它答非所问（不是这个问句所要的那类东西），或者是无意义的。

## 第二个轴：混淆度（这个选项和正确答案有多难区分？）

只看它把学习者从正确答案那里拉走的力量。一个完全切题的选项在这个轴上照样可能只得 1 分。
**这个轴的两端都是问题，目标值是 4。**

- 5 ＝ 学习者无法排除它，因为它**本身也算正确**：就这个题目而言，它也可以被辩护为
  一个正确答案，或者它和正确答案是一个意思。这会让整道题作废。
- 4 ＝ 很有迷惑性但确实是错的：一个只读懂一半的学习者很可能选它，而细心的读者能排除它。
  **这是目标值。**
- 3 ＝ **拿不准。** 你无法判断它到底有多大迷惑性。只要没有把握就打 3。不要用 4 或 2 去蒙。
- 2 ＝ 略有迷惑性；多数学习者很快就能排除。
- 1 ＝ 完全没有拉力：没有学习者会舍正确答案而选它。

## 示例（请自行创作，用地道的中文场景，不得出现任何外文人名或外文词）

请给出一个完整的示例：一段例文的梗概、一个问题、一个正确答案，以及**至少六个**
带两轴评分的干扰项。这六个必须覆盖下面这些格局，用来演示两个轴是各走各的：

- 切题度 5 ＋ 混淆度 4（理想的干扰项）
- 切题度 5 ＋ 混淆度 5（和正确答案同义——题目作废）
- 切题度 5 ＋ 混淆度 1（完全切题，却毫无拉力）
- 切题度 2 ＋ 混淆度 4（跑题，却仍然勾人）
- 切题度 2 ＋ 混淆度 1（跑题，也没人会选）
- 切题度 1 ＋ 混淆度 1（答非所问）

示例之后请补一句话，点明**两个轴在两个方向上都会分离**，所以必须分开评定。

## 其他要求

- 正文中要保留两行上下文：题目类型一行（用 {4}）和本文章的学科／领域关键词一行（用 {5}）。
  它们只是给评判模型的背景信息，**不要**据此写出「不同题型适用不同规则」之类的分支规则。
- 必须要求对**每一个**编号干扰项打分，个数不多不少。
- 必须明确要求：每个数组的前两个元素都是 1 到 5 的整数，**第一个是切题度，第二个是混淆度**，
  顺序不可颠倒；只给一个整数的回复无效。理由一栏里绝不能填数字、分数或单纯的标签。
""",
        'ja': """\
あなたは日本語母語の言語評価の専門家です。「読解問題の誤答選択肢を評価する」ための
プロンプトを、**ゼロから**日本語で執筆してください。このプロンプトは別のモデルに渡され、
誤答選択肢ごとに**2 つ**の点数を付けさせるために使われます。

## 背景：なぜ書き直すのか

現行のプロンプトは 1 から 5 の点数を**1 つ**だけ付けさせますが、その 1 つの数字は
互いに無関係な 2 つの問いに同時に答えています。

1. その選択肢は、文章が扱っている分野・領域に属するか。
2. 学習者はそれを正解と混同するか。

この 2 つは切り離せます。分野から外れた選択肢でも引っかかりやすいことはあります
（「灯りをつけるのに何が必要か」という問いに対する「日光」は、電気回路とは別の分野ですが、
「光」という語が不注意な読み手を引きつけます）。逆に、分野にぴったり合っていても
一目で除外できる選択肢もあります。両者を 1 つの整数に押し込めると、どちらの欠陥を
見ているのか分かりません。そこで新版では**2 つの軸で別々に採点**させ、
**一方の軸の点数が他方を引きずってはならない**ことを明示してください。

## 本文に必ず入れる是正の一段（2 つの軸の説明より前に置くこと）

この一段は実測で効果が確認されています。要点を落とさずに日本語で書き直してください。

誤答選択肢の存在意義は「誤っている」ことそのものです。事実として誤っている、
「明らかに正解ではない」、あるいは文章のどこにも書かれていない——これらはすべて
**必須**であり、まさにそれが選択肢を誤答たらしめるのであって、欠点ではありません。
文章と同じ分野の実在するものを指す誤答は、その当のものが文章に一度も現れなくても
良い誤答です。文章に出てこないことこそが、それが誤った選択肢である理由です。
文章に出てこないこと、誤っていること、簡単に除外できることを理由に点数を下げては
絶対にいけません。

## 第 1 の軸：分野適合（その選択肢は文章の分野に属するか）

分野への帰属だけを見ます。引っかかりやすさは第 2 の軸の話なので考慮しません。
「別の分野」とは文字どおりの意味です——電気回路の文章で、感情や社交的な活動を
選択肢として出すような場合。「同じ分野のものだが、たまたま文章が触れていないだけ」は
これに**当たりません**。

- 5 ＝ 文章の分野・領域に明らかに属する。**これは妥当な誤答にとって正常かつ期待される
  評価であり、良い誤答のほとんどは 5 になります。**
- 4 ＝ おおむねその分野の内側：隣接する領域で、学習者も同じ仲間だと見なす。
- 3 ＝ **確信が持てない。** その分野に属するかどうか判断できない。少しでも迷ったら 3 を
  付けてください。この段階は人手の確認に回すためにあります。当て推量で 4 や 2 を
  付けてはいけません。
- 2 ＝ 文章とは明らかに別の分野に属する。
- 1 ＝ そもそも成り立つ選択肢ではない：問いが求めている種類の答えになっていない、
  または無意味である。

## 第 2 の軸：紛らわしさ（正解とどれだけ区別しにくいか）

学習者を正解から引き離す力だけを見ます。分野にぴったり合っていても、この軸では
1 点ということがあります。**この軸は両端がどちらも問題で、目標値は 4 です。**

- 5 ＝ 学習者には除外できない。なぜなら**それ自体も正解といえる**からです——この設問に
  対して正しい答えとして擁護できる、あるいは正解と同じ意味である。設問そのものが
  壊れます。
- 4 ＝ 強く引っかかるが確実に誤り：半分しか読み取れていない学習者なら選びかねず、
  しかし注意深い読み手は除外できる。**これが目標値です。**
- 3 ＝ **確信が持てない。** どれだけ引っかかりやすいか判断できない。迷ったら 3 を付け、
  当て推量で 4 や 2 を付けないこと。
- 2 ＝ わずかに引っかかる程度；多くの学習者はすぐ除外する。
- 1 ＝ 引く力が皆無：正解を差し置いてこれを選ぶ学習者はいない。

## 例（自分で創作すること。自然な日本語の場面にし、外国語の人名や単語を出さないこと）

例文の概要・設問・正解、そして**6 つ以上**の誤答選択肢に 2 軸の点数を付けた完全な例を
1 つ挙げてください。次の組み合わせを必ず網羅し、2 つの軸が別々に動くことを示します。

- 分野適合 5 ＋ 紛らわしさ 4（理想的な誤答）
- 分野適合 5 ＋ 紛らわしさ 5（正解と同義——設問が壊れている）
- 分野適合 5 ＋ 紛らわしさ 1（分野は合うが引く力が皆無）
- 分野適合 2 ＋ 紛らわしさ 4（分野は外れているのに引っかかる）
- 分野適合 2 ＋ 紛らわしさ 1（分野も外れ、誰も選ばない）
- 分野適合 1 ＋ 紛らわしさ 1（問いに答えていない）

例のあとに、**2 つの軸は両方向のどちらにも分離する**ため別々に評価しなければ
ならない、という趣旨の一文を添えてください。

## その他の要件

- 本文に文脈として 2 行を残すこと：問題タイプの行（{4} を使う）と、この文章の
  分野・領域のキーワードの行（{5} を使う）。これらは判定モデルへの背景情報にすぎず、
  「問題タイプごとに別の規則を適用する」といった分岐規則を書いてはいけません。
- 番号付きの誤答**すべて**を採点するよう要求すること。個数は多くても少なくてもいけません。
- 各配列の最初の 2 要素は 1 から 5 の整数であり、**1 番目が分野適合、2 番目が紛らわしさ**
  で順序を入れ替えてはならないこと、整数が 1 つしかない返答は無効であることを明示すること。
  理由の欄に数字・点数・単なるラベルを入れてはいけないことも明示すること。
""",
    },
))

# --- translation_uniqueness_judge -------------------------------------------
# Cross-lingual by nature: a CJK source sentence, candidates in the learner's NL
# (injected as {nl_language}). The instruction body is still better in-language,
# because the hard reasoning is about what the CJK source leaves implicit.
#
# THE SCALE IS INVERTED relative to intuition and MUST NOT be "corrected":
# 5 = clearly NOT an acceptable translation = an ideal distractor = accept.
# Flipping it silently keeps exactly the distractors the judge exists to remove.
# See translation_uniqueness.py:13-26 and tests/test_translation_uniqueness_judge.py.

_register(Spec(
    task_name='translation_uniqueness_judge',
    langs=('zh', 'ja'),
    placeholders=('{tl_sentence}', '{correct_translation}', '{nl_language}',
                  '{candidates_numbered}'),
    placeholder_notes={
        'zh': {
            '{tl_sentence}': '作为原文的中文句子',
            '{correct_translation}': '被标为正确的那个译文选项',
            '{nl_language}': '各选项所使用的语言的名称（由程序注入，可能是英语、西班牙语等）',
            '{candidates_numbered}': '被标为错误的候选译文列表（每行一个，从 1 开始编号）',
        },
        'ja': {
            '{tl_sentence}': '原文となる日本語の文',
            '{correct_translation}': '正解とされている訳文の選択肢',
            '{nl_language}': '選択肢が書かれている言語の名称（プログラムが注入。英語やスペイン語などになりうる）',
            '{candidates_numbered}': '誤答とされている訳文候補の一覧（1 から番号付き、1 行 1 件）',
        },
    },
    required_literals=('"rating"', '"reason"'),
    json_block='{{"1": {{"rating": 5, "reason": "..."}}, '
               '"2": {{"rating": 1, "reason": "..."}}}}',
    allowed_latin=frozenset({'rating', 'reason', 'JSON', 'tl_sentence',
                             'correct_translation', 'nl_language',
                             'candidates_numbered'}),
    render_args={
        'tl_sentence': '（示例句子 / 例文）',
        'correct_translation': '(the keyed answer)',
        'nl_language': 'English',
        'candidates_numbered': '1. A\n2. B',
    },
    brief={
        'zh': """\
你是一位中文母语的语言测评专家。请**从零开始**用中文撰写一份「翻译题唯一性评判」提示词（prompt）。

## 背景：为什么要重写

现有的中文提示词整篇是英文写的。它要判断的核心问题却是**汉语**的问题：
一个候选译文和标准答案之间的差别，究竟是汉语本来就没有明说的东西（那就说明
两个选项都对，题目是坏的），还是真正的意思差别。这个判断需要汉语的语感。

## 评判任务

一道选择题给出一个**中文原句**和若干译文选项，其中一个被标为正确答案，其余被标为错误。
致命缺陷是：**不止一个选项是对的**。请逐个评判那些被标为错误的候选译文，判断它
究竟有多明显地**不是**该中文句子的可接受译文。

选项使用的语言由 {nl_language} 指明（可能是英语，也可能是其他语言）。

改述、近义词、语体或语序的不同，**并不**使一个译文变错。只要候选译文传达了相同的意思，
它就**也是正确的**，这道题就是坏题。

## 请特别注意汉语本身不明说的范畴

候选译文若**仅仅**在下列各项上与标准答案不同，通常仍然是可接受的译文：
- 单复数（汉语名词一般不标数）
- 时与体（只有「了 / 过 / 在 / 着」等才显性标记）
- 有定与无定（汉语没有冠词，「书」既可以是「那本书」也可以是「一本书」）
- 依靠语境可以还原的主语、宾语省略

反之，若在**事件本身、参与者、否定、情态**上有差别，那就确实是错误的译文。

## 评分尺度（方向必须严格照此表述，不得改动）

请让评判模型用 1 到 5 的整数打分。**请务必注意方向**：

- 5 ＝ 明显不是可接受的译文；它改变了意思、遗漏或增添了信息、或误译了关键词。是理想的干扰项。
- 4 ＝ 大概不可接受；称职的母语者会判它错，尽管比较接近。
- 3 ＝ 有争议；勉强可以辩护为一个宽松的译法。
- 2 ＝ 大概也可以接受；多数母语者会认可它。
- 1 ＝ 完全可以接受；它和原句意思相同。**该选项也是正确的，必须从题目中删除。**

这个方向是**反直觉**的（高分＝好干扰项＝该保留，低分＝也对＝该删除）。
请在正文中把方向写清楚，绝不可以写反。

## 其他要求

- 必须要求对**每一个**候选译文打分，不得遗漏。
""",
        'ja': """\
あなたは日本語母語の言語評価の専門家です。「翻訳問題の一意性を判定する」ための
プロンプトを、**ゼロから**日本語で執筆してください。

## 背景：なぜ書き直すのか

現行のプロンプトは全文が英語です。しかし判定の核心は**日本語**の問題です——
候補となる訳文と正解訳との差が、日本語がもともと明示しない事柄によるものなのか
（その場合、両方とも正解であり問題が壊れている）、それとも本当の意味の違いなのか。
この判断には日本語の語感が要ります。

## 判定する作業

ある多肢選択問題に、**日本語の原文**といくつかの訳文選択肢があり、1 つが正解、
残りが誤答とされています。致命的な欠陥は「**正解が 2 つ以上ある**」ことです。
誤答とされた候補訳を 1 つずつ、その日本語文の訳としてどれほど明確に
**受け入れられないか**を判定してください。

選択肢が書かれている言語は {nl_language} で示されます（英語とは限りません）。

言い換え、類義語、語域や語順の違いは、訳文を**誤りにしません**。候補訳が同じ意味を
伝えているなら、それも**正解**であり、この問題は壊れています。

## 日本語が明示しない範疇に特に注意すること

候補訳が次の点で**のみ**正解訳と異なる場合、なお受け入れ可能な訳であるのが普通です：
- 数（日本語の名詞は単数・複数を通常標示しない）
- 定・不定（冠詞がない）
- 文脈から復元できる主語・目的語の省略
- 丁寧さのレベル（命題内容はほとんど変わらない）

逆に、**出来事そのもの・参与者・否定・モダリティ**、および「誰が誰に何をしたか」
（助詞 は / が / を / に に注意）に違いがあれば、その訳は誤りです。

## 評価尺度（方向は厳密にこのとおりに記述すること）

判定モデルに 1 から 5 の整数で評価させてください。**方向に注意**：

- 5 ＝ 明らかに受け入れられない訳。意味を変える、情報を落とすか付け加える、
  重要語を誤訳している。理想的な誤答選択肢である。
- 4 ＝ おそらく受け入れられない。近くはあるが、力のある話者なら誤りと呼ぶ。
- 3 ＝ 議論の余地がある。緩い訳としてなら擁護できる。
- 2 ＝ おそらくこれも受け入れられる。多くの話者は認めるだろう。
- 1 ＝ 完全に受け入れられる。原文と同じ意味である。
  **この選択肢も正解であり、問題から取り除かなければならない。**

この方向は**直感に反します**（高得点＝良い誤答選択肢＝残すべき、
低得点＝これも正解＝取り除くべき）。本文で方向を明確に述べ、決して逆に書かないこと。

## その他の要件

- **すべての**候補訳を採点するよう必ず要求すること。漏らしてはいけません。
""",
    },
))


# --- reading-comprehension question generators ------------------------------
# Shared shape: same placeholders, same MCQuestion JSON, differing only in the
# question_type enum and the pedagogical brief.

_QUESTION_PLACEHOLDER_NOTES = {
    'zh': {
        '{prose}': '作为出题材料的文章',
        '{difficulty}': '难度等级（1-9）',
        '{previous_questions}': '已经出过的问题列表（用于避免重复）',
    },
    'ja': {
        '{prose}': '出題の材料となる文章',
        '{difficulty}': '難易度（1-9）',
        '{previous_questions}': 'すでに出題済みの質問の一覧（重複回避のため）',
    },
}

_QUESTION_JSON_KEYS = ('"question_text"', '"question_type"', '"choices"',
                       '"answer"', '"explanation"')


def _question_spec(task_name: str, type_code: str, langs: tuple[str, ...],
                   brief: dict[str, str]) -> Spec:
    return Spec(
        task_name=task_name,
        langs=langs,
        placeholders=('{prose}', '{difficulty}', '{previous_questions}'),
        placeholder_notes=_QUESTION_PLACEHOLDER_NOTES,
        required_literals=_QUESTION_JSON_KEYS + (f'"{type_code}"',),
        json_block=(
            '{{\n'
            '  "question_text": "...",\n'
            f'  "question_type": "{type_code}",\n'
            '  "choices": ["...", "...", "...", "..."],\n'
            '  "answer": "...",\n'
            '  "explanation": "..."\n'
            '}}'
        ),
        allowed_latin=frozenset({
            'question_text', 'question_type', 'choices', 'answer', 'explanation',
            type_code, 'JSON', 'prose', 'difficulty', 'previous_questions',
        }),
        render_args={'prose': '（示例文章 / 例文）', 'difficulty': 7,
                     'previous_questions': '（无 / なし）'},
        brief=brief,
        length_hint='1,200〜2,400',
    )


_register(_question_spec(
    'question_inference', 'inference', ('zh',),
    brief={
        'zh': """\
你是一位中文母语的语言测评专家。请**从零开始**用中文撰写一份「推理类阅读理解题」出题提示词（prompt）。

## 背景：为什么要重写

现有的中文提示词整体是从英文翻译过来的，最明显的破绽在少量示例（few-shot）里：
示例段落写的是「Martinez博士第三次看了手表……」——一个英文名字直接留在了中文例文中，
而整个场景（学术演示、与会者迟到）也是英文语境的移植。出题模型会照着这个示例的
文化背景和人名习惯去生成题目。请用**地道的中文场景**重新创作示例。

## 出题要求

生成**一道**四选一的推理题。所谓推理，是指答案在文中**没有直接说明**，
但可以从文中的线索合乎逻辑地推出来。

- 考查学生「听出言外之意」、把握未明说含义的能力。
- 正确答案必须有充分的文本证据支持，但不得是原文的直接复述。
- 干扰项要看似合理，但缺乏文中线索的支持。

## 少量示例（few-shot）

请自行创作**一个**完整示例，要求：

- 例文必须是**地道的现代汉语**，由你自己撰写，场景和人名都要符合中文语境
  （人名用中文姓名，不得出现任何外文人名）。
- 例文要留下足够的线索，使推理有据可依。
- 包含：例文、问题、四个选项、正确答案、解释。

## 其他要求

- 必须指示出题模型参考 {previous_questions}，在推理类型、关注点和提问方式上都与之不同。
- 正确答案在四个选项中的位置不要固定（下游不会打乱选项顺序，示例中的位置会形成偏差）。
""",
    },
))

_register(_question_spec(
    'question_main_idea', 'main_idea', ('ja',),
    brief={
        'ja': """\
あなたは日本語母語の言語評価の専門家です。「主旨（メインアイデア）を問う読解問題」を
生成するためのプロンプトを、**ゼロから**日本語で執筆してください。

## 背景：なぜ書き直すのか

現行のプロンプトは英語版の逐語訳です。見出しに「メインアイデア」というカタカナの
直訳語を使い、本文には「目的 vs テーマ vs 中心的メッセージ」のように英語の "vs" が
そのまま残っています。またフューショットの例文（都市農業・コミュニティガーデン・
垂直庭園）も英語圏の文章の翻訳で、日本語の文章として自然に書かれたものではありません。
**日本語として自然な用語と例文**で構想し直してください。

## 出題の要件

四択問題を**1 問**生成させます。文章全体の中心的な主題・主な目的・全体としての
メッセージを問うものです。

- 個々の細部ではなく、文章**全体**の理解を要求すること。
- 情報を統合し、その文章が主として何について書かれているかを見抜く力を測ること。
- 誤答は、具体的すぎる（些末な細部）、広すぎる（文章の範囲を超える）、
  または事実として誤っている、のいずれかであること。

## フューショットの例

**1 つ**の完全な例をご自身で創作してください。要件：

- 例文は**自然な現代日本語**であり、あなた自身が書いたものであること。
  英語からの翻訳や、英語圏の話題の移植は不可。
- 例文・質問・4 つの選択肢・正解・解説を含めること。

## その他の要件

- {previous_questions} を参照させ、問いの枠組み・表現・誤答の作り方を変えるよう
  指示すること。その際「vs」のような英字の記号を使わず、日本語で言い分けること。
- 正解の位置を固定しないこと（下流の処理は選択肢をシャッフルしないため、
  例の並びがそのまま位置の偏りになる）。
""",
    },
))

_register(_question_spec(
    'question_author_purpose', 'author_purpose', ('ja',),
    brief={
        'ja': """\
あなたは日本語母語の言語評価の専門家です。「筆者の意図・文章の調子を問う読解問題」を
生成するためのプロンプトを、**ゼロから**日本語で執筆してください。

## 背景：なぜ書き直すのか

現行のプロンプトは英語版の逐語訳で、見出しに「**著者の目的／口調（Author Purpose/Tone）**」
と英語の対訳が括弧書きで残り、本文にも「目的 vs 口調 vs 態度 vs 視点」のように
英語の "vs" が使われています。日本語の読解指導の用語で書き直してください。
なお「著者」よりも「筆者」のほうが、この文脈の日本語としては自然です。

## 出題の要件

四択問題を**1 問**生成させます。筆者が**なぜ**その文章を書いたのか、その態度・
調子・立場を問うものです。

- 筆者の意図、見方、感情的な立場の理解を測ること。
- 問える観点：書いた目的（説明する・説得する・楽しませる）、文章の調子
  （前向き・批判的・中立的）、立場（支持的・懐疑的）、あるいは論の運び方。
- 語の選び方・構成・全体のメッセージの分析を求めること。
- 答えは必ず本文中の根拠に裏づけられていること。

## フューショットの例

**1 つ**の完全な例をご自身で創作してください。要件：

- 例文は**自然な現代日本語**であり、あなた自身が書いたものであること。
- 筆者の立場が一様でない（留保や条件がついた）文章にすると、調子を問う設問が作りやすい。
- 例文・質問・4 つの選択肢・正解・解説を含めること。

## その他の要件

- {previous_questions} を参照させ、問う観点（目的か、調子か、態度か、視点か）を
  前回と変えるよう指示すること。その際、英字の記号ではなく日本語で言い分けること。
- 正解の位置を固定しないこと（下流の処理は選択肢をシャッフルしない）。
""",
    },
))


# ---------------------------------------------------------------------------
# Contract (rendered per spec, in the target language)
# ---------------------------------------------------------------------------

_CONTRACT = {
    'zh': """\

## 输出契约（必须严格遵守）

1. 只输出**提示词正文本身**。不要写前言、说明、后记，也不要用代码围栏（```）包裹。
2. 必须**原样**包含下列占位符，每个**恰好出现一次**：
{placeholder_lines}
3. 必须**原样**包含下面这个 JSON 输出块，**花括号保持双写**：

{json_block}

   其中的键名以及 {literals} 必须保持英文原样，**一个字母都不能改、不能翻译**——
   下游程序按字面匹配这些字符串，改了就会静默失效。
   花括号双写只是字符串插值的需要，**不是要讲给使用者听的内容**：正文里不得出现
   「双花括号」「两个花括号」之类的说明（插值之后就不再是双写了，会误导读者）。
   请把这一块称作「JSON 对象」。
4. **除第 3 条规定的部分之外，正文中不得出现任何拉丁字母。** 英文单词、罗马字、
   拼音、英文术语（idiom、tone、few-shot、C2 等）一律换成中文说法。
5. 篇幅约 {length_hint} 字。
""",
    'ja': """\

## 出力契約（厳守）

1. 出力は**プロンプト本文そのもの**のみ。前置き・後書き・コードフェンス（```）は
   一切付けないこと。
2. 次の占位子（プレースホルダ）を**この表記のまま、各 1 回ずつ**含めること：
{placeholder_lines}
3. 次の JSON 出力ブロックを、**波括弧を二重にしたまま**含めること：

{json_block}

   キー名および {literals} は英字のまま、**1 文字も変えず、翻訳もしないこと**。
   下流のプログラムがこれらの文字列を字面で照合しており、変えると無言で機能しなくなる。
   波括弧の二重化は差し込み処理の都合であり、**読み手に説明する内容ではない**：
   本文に「二重波括弧」「波括弧を二つ」等と書いてはいけない（差し込み後には
   二重ではなくなるため、読み手を誤らせる）。このブロックは「JSON オブジェクト」と呼ぶこと。
4. **上記 3 以外の箇所に英字（ラテン文字）を一切使わないこと。** 英単語・ローマ字・
   英語の術語（idiom、tone、few-shot、C2 など）はすべて日本語の語に置き換える。
5. 分量の目安は {length_hint} 字。
""",
}


def _prompt_for(spec: Spec, lang: str, retry_note: str = '') -> str:
    notes = spec.placeholder_notes[lang]
    placeholder_lines = '\n'.join(
        f'   - {p} … {notes.get(p, "")}' for p in spec.placeholders
    )
    contract = _CONTRACT[lang].format(
        placeholder_lines=placeholder_lines,
        json_block=spec.json_block,
        literals='、'.join(spec.required_literals) if lang == 'zh'
                 else '、'.join(spec.required_literals),
        length_hint=spec.length_hint,
    )
    return f'{spec.brief[lang]}{contract}{retry_note}'


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def latin_runs(text: str) -> list[str]:
    return [run for run in LATIN_RUN.findall(text) if len(run) >= 2]


def offending_runs(text: str, spec: Spec) -> list[str]:
    return [run for run in latin_runs(text) if run not in spec.allowed_latin]


def _render_check(text: str, spec: Spec) -> str | None:
    """Run str.format exactly as the judge/generator will. Returns an error string."""
    try:
        text.format(*spec.render_positional, **spec.render_args)
    except Exception as exc:  # KeyError / IndexError / ValueError — all fatal later
        return f'{type(exc).__name__}: {exc}'
    return None


def verify(text: str, spec: Spec) -> list[str]:
    problems: list[str] = []

    for placeholder in spec.placeholders:
        count = text.count(placeholder)
        if count != 1:
            problems.append(f'placeholder {placeholder} appears {count}x, expected exactly 1')

    for literal in spec.required_literals:
        if literal not in text:
            problems.append(
                f'required literal {literal} is missing — the parser matches it '
                f'verbatim, so the row would silently misbehave'
            )

    if '{{' not in text or '}}' not in text:
        problems.append('JSON braces are not doubled ({{ / }}) — str.format will fail')

    leaked = offending_runs(text, spec)
    if leaked:
        unique = sorted(set(leaked))
        problems.append(
            f'{len(leaked)} leaked Latin run(s), {len(unique)} distinct: '
            + ', '.join(repr(run) for run in unique[:20])
        )

    if text.lstrip().startswith('```'):
        problems.append('output is wrapped in a code fence')

    render_error = _render_check(text, spec)
    if render_error:
        problems.append(f'str.format failed: {render_error}')

    return problems


def strip_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith('```'):
        return stripped
    lines = stripped.splitlines()[1:]
    if lines and lines[-1].strip().startswith('```'):
        lines = lines[:-1]
    return '\n'.join(lines).strip()


# ---------------------------------------------------------------------------
# Authoring loop
# ---------------------------------------------------------------------------

_RETRY_HEADER = {
    'zh': '\n\n## 上一次输出的问题（必须逐条修正）\n\n',
    'ja': '\n\n## 前回の出力の問題点（必ず修正すること）\n\n',
}
_RETRY_FOOTER = {
    'zh': '\n\n请不要重复同样的错误，重新输出完整、符合契约的正文。\n',
    'ja': '\n\n同じ誤りを繰り返さず、契約を満たす完全な本文を再度出力してください。\n',
}


def author(spec: Spec, lang: str, model: str, attempts: int,
           temperature: float, max_tokens: int) -> str:
    retry_note = ''
    last_text = ''

    for attempt in range(1, attempts + 1):
        print(f'[{spec.task_name}/{lang}] attempt {attempt}/{attempts} on {model} ...',
              flush=True)
        try:
            raw = call_llm(
                _prompt_for(spec, lang, retry_note),
                model=model,
                response_format='text',
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=300,
                pipeline='diag',
                task_name=f'{spec.task_name}_rewrite',
            )
        except RuntimeError as exc:
            # On a thinking model this is nearly always the reasoning budget, not a
            # dead slug. Say so rather than let the caller go hunting.
            if 'empty content' in str(exc):
                print(f'[{spec.task_name}/{lang}] empty content — reasoning likely '
                      f'exhausted the {max_tokens}-token budget; raise --max-tokens',
                      file=sys.stderr)
            raise
        last_text = strip_fence(str(raw))

        problems = verify(last_text, spec)
        if not problems:
            print(f'[{spec.task_name}/{lang}] clean on attempt {attempt}', flush=True)
            return last_text

        print(f'[{spec.task_name}/{lang}] {len(problems)} problem(s):', flush=True)
        for problem in problems:
            print(f'    - {problem}', flush=True)

        # Quote the failures back rather than restating the rules — a model that
        # ignored "no English" in the abstract usually complies when shown its own
        # leaked tokens.
        retry_note = (_RETRY_HEADER[lang]
                      + '\n'.join(f'- {p}' for p in problems)
                      + _RETRY_FOOTER[lang])

    print(f'[{spec.task_name}/{lang}] exhausted {attempts} attempts; '
          f'returning last output UNVERIFIED', file=sys.stderr)
    return last_text


def report(spec: Spec, lang: str, text: str) -> list[str]:
    problems = verify(text, spec)
    leaked = offending_runs(text, spec)

    print()
    print(f'--- {spec.task_name} [{lang}] ------------------------------')
    print(f'  length     : {len(text)} chars')
    print(f'  latin runs : {len(latin_runs(text))} total, {len(leaked)} leaked')
    if leaked:
        print(f'  leaked     : {sorted(set(leaked))}')
    print(f'  str.format : {_render_check(text, spec) or "OK"}')
    print(f'  contract   : {"PASS" if not problems else "FAIL"}')
    for problem in problems:
        print(f'    - {problem}')
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--task', required=True, choices=sorted(SPECS))
    parser.add_argument('--lang', required=True, choices=sorted(LANG_ID))
    parser.add_argument('--model', default=DEFAULT_MODEL)
    parser.add_argument('--out', help='write the authored template here')
    parser.add_argument('--check', metavar='PATH',
                        help='verify an existing file instead of calling the model')
    parser.add_argument('--attempts', type=int, default=3)
    parser.add_argument('--temperature', type=float, default=0.7,
                        help='prose authoring, not extraction (default: 0.7)')
    parser.add_argument('--max-tokens', type=int, default=DEFAULT_MAX_TOKENS)
    args = parser.parse_args()

    spec = SPECS[args.task]
    if args.lang not in spec.langs:
        parser.error(f'{args.task} has no {args.lang} target '
                     f'(declared: {", ".join(spec.langs)})')

    if args.check:
        with open(args.check, encoding='utf-8') as handle:
            text = handle.read()
        return 1 if report(spec, args.lang, text) else 0

    # Without this, call_llm's own logging raises "SupabaseFactory not initialized"
    # and the run leaves no cost record at all.
    SupabaseFactory.initialize()

    text = author(spec, args.lang, args.model, args.attempts,
                  args.temperature, args.max_tokens)
    problems = report(spec, args.lang, text)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(text)
        print(f'\nwrote {args.out}')

    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
