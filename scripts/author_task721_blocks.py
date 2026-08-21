"""Author the zh/ja distractor-construction blocks natively (TASK-721).

Follows TASK-722 / TASK-724: the text that goes into a zh or ja prompt row is
written *in* that language by `qwen/qwen3.8-max` against a brief *in* that
language, never translated from English.

WHY THIS IS NOT A FORK OF `rewrite_prompt_native.py`
----------------------------------------------------
That script rewrites a WHOLE prompt row, and its value is the contract it
enforces on the result: the three `str.format` placeholders survive, the JSON
keys and the `question_type` enum survive, the body still renders. A *block* has
none of those properties -- it is a fragment with no placeholders and no JSON --
so running it through `Spec`/`verify` would mean disabling precisely the checks
worth having, and the "extend the registry" path would need a second Spec shape
that means something different from the first.

So the shared machinery is imported rather than copied (`strip_fence`,
`latin_runs`, the retry framing, the model and token defaults), and the block's
real contract is checked where it becomes checkable: on the SPLICED row, in
`stage_task721_templates.py`, using the same placeholder / literal / render
assertions `rewrite_prompt_native.verify` would apply.

THE ONE CHECK THAT MATTERS MOST
-------------------------------
A block must contain no `{` or `}`. Every `question_*` row is `str.format`ed
with `prose` / `difficulty` / `previous_questions`, so a single stray brace in
authored prose raises KeyError or ValueError at generation time for every
question of that type. The authoring loop rejects and retries on it.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, '.env'))

from services.llm_service import call_llm  # noqa: E402
from services.prompt_service import get_template_config  # noqa: E402
from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

from rewrite_prompt_native import (  # noqa: E402
    DEFAULT_MAX_TOKENS, DEFAULT_MODEL, _RETRY_FOOTER, _RETRY_HEADER,
    latin_runs, strip_fence,
)
from task721_blocks import ANCHORS, FAMILY  # noqa: E402

BLOCK_DIR = os.path.join(ROOT, 'data', 'eval', 'task721', 'blocks')
LANG_ID = {'zh': 1, 'ja': 3}
JUDGE_TASK = 'test_distractor_plausibility'

MIN_CHARS, MAX_CHARS = 380, 1400

# Latin the block may legitimately carry. Everything else is leakage. `JSON` is
# here because the block sits next to the output contract and may refer to it --
# and because its ABSENCE from four rows is what broke them (see
# stage_task721_templates).
ALLOWED_LATIN = frozenset({'JSON'})

TYPE_LABEL = {
    'zh': {
        'literal_detail': '字面细节', 'supporting_detail': '支持性细节',
        'main_idea': '主旨大意', 'inference': '推理',
        'author_purpose': '作者意图／语气', 'vocabulary_context': '语境中的词汇',
    },
    'ja': {
        'literal_detail': '文字どおりの細部', 'supporting_detail': '裏づけとなる細部',
        'main_idea': '主旨', 'inference': '推論',
        'author_purpose': '筆者の意図・文章の調子', 'vocabulary_context': '文脈における語彙',
    },
}

FAMILY_NOTE = {
    'zh': {
        'fact': '这类题的干扰项，是同一领域中文章并不支持的事实或结论。'
                '最有力的写法是：文中从未陈述、但确实属于该领域的真实事物；'
                '文中确实提到、却被安到错误的人物、时间、地点或因果上的细节；'
                '以及超出文本证据所能支持范围的结论。',
        'intent': '这类题的干扰项，是读者可能归到作者身上的其他写作目的、语气或信息。'
                  '这里的「离题」指文章毫无迹象的意图，而**不是**文章碰巧没有提到的话题。'
                  '最有力的写法是：与文章自身措辞相抵触的立场；真实存在但只是次要的目的被当成主要目的；'
                  '以及过窄（只抓一个细节）或过宽（超出文章范围）的信息概括。',
        'sense': '这类题的干扰项，是目标词语的其他**义项**，因此要针对这个词本身去衡量，'
                 '而不是针对文章的主题。与文章主题毫无关系的选项在这类题里**不算离题**，'
                 '那才是正常情况。最有力的写法是：比喻性表达的字面义；多义词的另一个固定义项；'
                 '以及在程度、对象或语体色彩上有差别的近义解释。',
    },
    'ja': {
        'fact': 'この種類の問題では、誤答は同じ分野に属しながら本文が支持していない事実や結論です。'
                '最も強い作り方は、本文が一度も述べていないがその分野に実在するもの、'
                '本文が述べてはいるが人物・時点・場所・因果を取り違えて結びつけた細部、'
                'そして本文の根拠が許す範囲を超えて踏み込んだ結論です。',
        'intent': 'この種類の問題では、誤答は読者が筆者に帰しうる別の目的・調子・主張です。'
                  'ここでの「分野が違う」とは、本文に何の兆しもない意図のことであり、'
                  '本文がたまたま触れていない話題のことでは**ありません**。'
                  '最も強い作り方は、本文自身の言い回しと矛盾する立場、'
                  '実在するが副次的にすぎない目的を主目的として示すもの、'
                  'そして狭すぎる（細部一つ）あるいは広すぎる（本文の範囲を超える）主張です。',
        'sense': 'この種類の問題では、誤答は対象となる語句の別の**意味**です。'
                 'したがって本文の話題ではなく、語そのものに照らして判断します。'
                 '本文の話題と何の関係もない選択肢は、この種類では**話題外ではなく**、'
                 'むしろ通常の姿です。最も強い作り方は、比喩表現の字義どおりの読み、'
                 '多義語の別の確立した意味、そして程度・対象・語感の異なる近い意味です。',
    },
}

_BRIEF = {
    'zh': """\
你是一位中文母语的语言测评专家。

## 任务

下面是一份**评分标准**：题目生成之后，系统会用它给每一个干扰项打 1 到 5 分，
被打到 1 分或 2 分，整道题就会被丢弃。出题端从来没有见过这份标准，
也就是说，它一直在按一套自己不知道的规范被筛选。

请把这份标准**反过来**，写成一段「出题时应当如何构造干扰项」的指导文字，
这段文字将被插入到「<<LABEL>>」类阅读理解题的出题提示词里。

## 评分标准原文（据此反写）

<<RUBRIC>>

## 这段文字将要插入的提示词（请与它的术语、语气和已有例文保持一致）

<<ROW>>

## 必须写进去的内容

1. 干扰项必须与文章属于同一学科或领域。一个指向同领域真实事物的干扰项，
   即使文章从未提到它，也是**好**的干扰项——没有出现在文中，恰恰就是它错误的原因。
   不要仅仅因为文章没有提到就回避某个选项。
2. **绝对禁止**写出「结合题目也可以算作正确」的干扰项。只要认真的读者能为它辩护，
   这道题就有了两个答案，会被整题丢弃。这是危害最大的一种错误。
3. **绝对禁止**写出与正确答案同义改写的干扰项，也不得与正确答案接近到学习者无法区分。
4. 不要跨到另一个学科（例如在讲电路的文章里给出一种情绪），也不要写荒谬无意义的选项。
5. 四个选项在长度、句式和信息量上要尽量接近，不要让正确项因形式而暴露。
6. <<FAMILY>>

## 还必须包含一个完整示例

请创作**一个**示例。**优先直接沿用上面那份提示词里已有的例文**，以免引入第二个互不相关的场景。
示例要包含：
- 一个**好**的干扰项，并说明它为什么好；
- 一个被**否决**的干扰项，否决理由是「它也可以算作正确」；
- 一个被**否决**的干扰项，否决理由是「它是正确答案的同义改写」。

## 硬性格式要求

- 只输出这一段正文本身。不要输出任何前言、后记、说明或代码框。
- 全文使用地道现代汉语。不得出现任何英文单词、拼音或拉丁字母。
- **绝对不得出现半角大括号**。下游会对整段提示词做字符串格式化，
  出现一个半角大括号就会让整条生成流程报错。示例中的选项请用中文标点或顿号列出。
- 不得出现「<<ANCHOR>>」这几个字，它是插入位置的定位标记。
- 篇幅控制在 <<LO>> 到 <<HI>> 个字符之间。
""",
    'ja': """\
あなたは日本語母語の言語評価の専門家です。

## 課題

以下は**採点基準**です。問題が生成されたあと、システムはこれを使って誤答選択肢を
1 から 5 で採点し、1 または 2 が付くと問題ごと破棄されます。出題側はこの基準を
一度も見たことがありません。つまり、自分の知らない規範で選別され続けています。

この基準を**裏返して**、「出題時に誤答選択肢をどう作るか」という指導文に書き直してください。
この文は「<<LABEL>>」を問う読解問題の出題プロンプトに挿入されます。

## 採点基準の原文（これを裏返す）

<<RUBRIC>>

## 挿入先のプロンプト（用語・語調・既存の例と揃えること）

<<ROW>>

## 必ず書き込む内容

1. 誤答は本文と同じ分野・領域に属すること。同じ分野の実在するものを指す誤答は、
   本文が一度もそれに触れていなくても**良い**誤答です。本文に出てこないことこそ、
   それが誤りである理由です。本文に書かれていないという理由だけで選択肢を避けないこと。
2. 「問題に対して正解とも言える」誤答を書くことを**固く禁じます**。
   注意深い読者が正解に対してそれを擁護できるなら、その問題は答えが二つあることになり、
   問題ごと破棄されます。最も害の大きい失敗です。
3. 正解の**言い換え**にあたる誤答、および学習者が区別できないほど正解に近い誤答を、
   **固く禁じます**。
4. 別の分野に踏み込まないこと（電気回路の文章で感情を選択肢に出すなど）。
   不合理・無意味な選択肢も書かないこと。
5. 四つの選択肢は長さ・文の形・情報量をできるだけ揃え、形だけで正解が分からないようにすること。
6. <<FAMILY>>

## 完全な例も必ず含めること

例を**一つ**作ってください。**上のプロンプトに既にある例文をそのまま使うことを優先**し、
無関係な二つ目の場面を持ち込まないでください。例には次を含めます。
- **良い**誤答を一つ、なぜ良いのかの理由とともに。
- **却下**される誤答を一つ、理由は「正解とも言えてしまう」。
- **却下**される誤答を一つ、理由は「正解の言い換えである」。

## 出力形式の必須要件

- この本文だけを出力すること。前置き、後書き、説明、コードブロックは一切付けないこと。
- 全文を自然な現代日本語で書くこと。英単語・ローマ字・ラテン文字を含めないこと。
- **半角の波括弧を絶対に使わないこと**。下流でプロンプト全体に文字列書式化がかかるため、
  波括弧が一つあるだけで生成処理全体が失敗します。例の選択肢は日本語の記号で列挙してください。
- 「<<ANCHOR>>」という文字列を含めないこと。挿入位置の目印です。
- 分量は <<LO>> 字から <<HI>> 字のあいだに収めること。
""",
}


def build_brief(lang: str, tc: str, rubric: str, row: str) -> str:
    return (_BRIEF[lang]
            .replace('<<LABEL>>', TYPE_LABEL[lang][tc])
            .replace('<<RUBRIC>>', rubric)
            .replace('<<ROW>>', row)
            .replace('<<FAMILY>>', FAMILY_NOTE[lang][FAMILY[tc]])
            .replace('<<ANCHOR>>', ANCHORS[(f'question_{tc}', lang)])
            .replace('<<LO>>', str(MIN_CHARS))
            .replace('<<HI>>', str(MAX_CHARS)))


def verify_block(text: str, lang: str, tc: str) -> list[str]:
    problems = []
    if '{' in text or '}' in text:
        problems.append('正文中出现了半角大括号 / 半角の波括弧が含まれています'
                        if lang == 'zh' else
                        '本文に半角の波括弧が含まれています')
    leaked = sorted({r for r in latin_runs(text) if r not in ALLOWED_LATIN})
    if leaked:
        problems.append(f'残留拉丁字母 / 残存するラテン文字: {leaked}')
    if not (MIN_CHARS <= len(text) <= MAX_CHARS):
        problems.append(f'篇幅 {len(text)} 不在 {MIN_CHARS}-{MAX_CHARS} 之间 / '
                        f'分量が範囲外です')
    anchor = ANCHORS[(f'question_{tc}', lang)]
    if anchor in text:
        problems.append(f'包含了定位标记 / 位置目印を含んでいます: {anchor}')
    return problems


def author_block(db, lang: str, tc: str, model: str, attempts: int) -> str:
    rubric = get_template_config(db, JUDGE_TASK, LANG_ID[lang])['template']
    row = get_template_config(db, f'question_{tc}', LANG_ID[lang])['template']
    # The judge rubric and the row both carry `{n}` / `{prose}` slots. They are
    # shown to the authoring model as reference material only, and the model is
    # told not to emit braces at all, so they are stripped here rather than
    # risking their re-emission.
    rubric = rubric.replace('{', '［').replace('}', '］')
    row = row.replace('{', '［').replace('}', '］')

    retry = ''
    last = ''
    for attempt in range(1, attempts + 1):
        print(f'[{tc}/{lang}] attempt {attempt}/{attempts} on {model} ...', flush=True)
        raw = call_llm(
            build_brief(lang, tc, rubric, row) + retry,
            model=model,
            response_format='text',
            temperature=0.3,
            max_tokens=DEFAULT_MAX_TOKENS,
            timeout=300,
            pipeline='diag',
            task_name='task721_block_author',
        )
        last = strip_fence(str(raw))
        problems = verify_block(last, lang, tc)
        if not problems:
            print(f'[{tc}/{lang}] clean on attempt {attempt} ({len(last)} chars)',
                  flush=True)
            return last
        print(f'[{tc}/{lang}] {len(problems)} problem(s):', flush=True)
        for p in problems:
            print(f'    - {p}', flush=True)
        retry = (_RETRY_HEADER[lang] + '\n'.join(f'- {p}' for p in problems)
                 + _RETRY_FOOTER[lang])
    print(f'[{tc}/{lang}] exhausted {attempts} attempts; NOT written',
          file=sys.stderr)
    return ''


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--lang', required=True, choices=sorted(LANG_ID))
    ap.add_argument('--types', default=','.join(FAMILY))
    ap.add_argument('--model', default=DEFAULT_MODEL)
    ap.add_argument('--attempts', type=int, default=3)
    args = ap.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()
    os.makedirs(BLOCK_DIR, exist_ok=True)

    failed = []
    for tc in [t.strip() for t in args.types.split(',') if t.strip()]:
        path = os.path.join(BLOCK_DIR, f'question_{tc}_{args.lang}.txt')
        if os.path.exists(path):
            print(f'[{tc}/{args.lang}] already authored, skipping')
            continue
        text = author_block(db, args.lang, tc, args.model, args.attempts)
        if not text:
            failed.append(tc)
            continue
        # Block ends with a blank line so the following anchor starts cleanly.
        with open(path, 'w', encoding='utf-8', newline='') as fh:
            fh.write(text.rstrip() + '\n\n')

    if failed:
        print(f'\nFAILED: {failed}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
