"""Re-author the zh/ja `question_vocabulary_context` generator prompt natively (TASK-722).

The live zh and ja rows are literal translations of the English one that kept the
English lexical targets: they teach with `'bright'`, `'pick up'` and
`'turn a blind eye'`, and embed those English idioms *inside* their CJK few-shot
passages (「共同'pick up the pieces'」; 「事態を収拾し（pick up the pieces）」). A
Chinese vocabulary-question generator is therefore few-shotted on English phrasal
verbs, a category Chinese does not have, and 成语/惯用语 are never mentioned.

This script does not translate. It hands a target-language authoring brief to a
strong target-language model and asks for a prompt written from scratch against
that language's own lexical categories, then *verifies* the result mechanically
before anything is written to a migration:

    python scripts/rewrite_vocab_context_prompt.py --lang zh --out data/eval/vocab_prompt_zh.txt
    python scripts/rewrite_vocab_context_prompt.py --lang ja --out data/eval/vocab_prompt_ja.txt

    # re-check a file that already exists, spending nothing
    python scripts/rewrite_vocab_context_prompt.py --lang zh --check data/eval/vocab_prompt_zh.txt

The verification is the point of the script. A model asked to "write only in
Chinese" will still leak English, and the failure is silent — the prompt reads
fluently and only the *examples* are wrong, which is precisely the bug being
fixed. `--attempts` retries with the offending runs quoted back at the model, so a
near-miss is repaired rather than hand-edited.

Latin runs are counted the same way for input and output, so the before/after
number in the task's acceptance criteria is comparable. The allowlist is exactly
the machinery the template cannot survive without: the JSON keys, the
`vocabulary_context` type code, and the `str.format` placeholder names.

Every call is logged to `llm_calls` under `pipeline='diag'` so authoring spend does
not contaminate per-pipeline production cost reporting.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

# Run-as-script bootstrap (mirrors scripts/measure_judge_flag_rate.py): repo root on
# the path and .env loaded before any app service is imported.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.llm_service import call_llm  # noqa: E402
from services.supabase_factory import SupabaseFactory  # noqa: E402


DEFAULT_MODEL = 'qwen/qwen3.8-max'

# `qwen3.8-max` is a *thinking* model and its reasoning tokens are drawn from the
# same completion budget as the answer. At 6,000 it burned the entire allowance on
# reasoning and returned `finish_reason='length'` with empty content, which surfaces
# from llm_service as a bare "LLM returned empty content" — a misleading error for
# what is really a budget problem. `llm_service.call_llm` exposes no reasoning-effort
# control (its only `extra_body` use is OpenRouter cost reporting), and widening that
# shared production path for a one-off authoring script is not worth the blast radius,
# so the budget is simply set high enough for reasoning plus a ~3,000-character
# template. Observed: ~7-9k reasoning tokens for this brief.
DEFAULT_MAX_TOKENS = 32000

# Placeholders the template is rendered with. `question_generator.py` calls
# str.format(), so each must survive verbatim and the JSON braces must stay doubled.
REQUIRED_PLACEHOLDERS = ('{prose}', '{difficulty}', '{previous_questions}')

# Keys the downstream MCQuestion schema parses. These are the *only* reason Latin
# characters may appear in a natively-authored prompt.
JSON_KEYS = (
    'question_text',
    'question_type',
    'choices',
    'answer',
    'explanation',
)

ALLOWED_LATIN_RUNS = frozenset(
    JSON_KEYS
    + ('vocabulary_context', 'JSON', 'prose', 'difficulty', 'previous_questions')
)

# Underscores are part of the run, not a separator. Splitting on them turns the
# one legitimate Latin token (`question_text`) into two illegitimate ones
# (`question`, `text`), which no allowlist can match — the first version of this
# script failed three clean rewrites that way.
LATIN_RUN = re.compile(r'[A-Za-z][A-Za-z_]*')


# ---------------------------------------------------------------------------
# Per-language authoring brief
# ---------------------------------------------------------------------------
# Written in the target language on purpose. A brief written in English invites an
# English-flavoured answer, which is the exact failure mode being repaired.

BRIEFS = {
    'zh': {
        'label': '中文',
        'brief': """\
你是一位中文母语的语言测评专家。请**从零开始**撰写一份「语境中的词汇」阅读理解题目生成提示词（prompt）。

这份提示词将被送给另一个模型，用来根据一段中文短文生成一道四选一的选择题。

## 背景：为什么要重写

现有的中文提示词是从英文逐字翻译过来的，它保留了英文的词汇目标：用 'bright'、'pick up'、
'turn a blind eye' 来举例，甚至把英文习语直接塞进中文例文里（「共同'pick up the pieces'」）。
这是错误的——中文没有「短语动词」这一范畴。请用中文自身的词汇范畴重新构思整份提示词。

## 分级要求（必须用中文自身的范畴表述）

- **1-4 级**：多义词、常用词在具体语境中的义项选择（如「打」「意思」「东西」这类一词多义）。
- **5-6 级**：常见惯用语、固定搭配、离合词、比喻义明显的双音节词。
- **7-9 级**：成语、谚语、歇后语、书面语固定表达。此级别**不得**考查单个的常用词。

「7-9 级必须考查多词表达」这条规则是英文思路的产物（英文靠词数区分）。请改用**中文自身**
的判准来表述这条限制——例如「必须是成语、谚语或固定表达，而不是一个可以逐字理解的普通词语」。

## 少量示例（few-shot）

请自行创作 **两个**完整示例：一个中级、一个高级。要求：

- 例文必须是**地道的现代汉语**，由你自己撰写，不得是英文的翻译。
- 被考查的词语必须是**汉语本身的词汇单位**（成语、惯用语、多义词），绝不能出现任何英文词语。
- 每个示例包含：例文、问题、四个选项、正确答案、解释。
- 四个干扰项必须都是**该词语在汉语中似是而非的其他解释**，不能是明显荒谬的选项。
""",
    },
    'ja': {
        'label': '日本語',
        'brief': """\
あなたは日本語母語の言語評価の専門家です。「文脈における語彙」を問う読解問題を生成するための
プロンプトを、**ゼロから**執筆してください。

このプロンプトは別のモデルに渡され、日本語の短い文章をもとに四択問題を1問生成させるために
使われます。

## 背景：なぜ書き直すのか

現行の日本語プロンプトは英語版の逐語訳で、英語の語彙ターゲットをそのまま残しています。
'bright'、'pick up'、'turn a blind eye' を例に用い、英語のイディオムを日本語の例文の中に
括弧書きで埋め込んでいます（「事態を収拾し（pick up the pieces）」）。これは誤りです。
日本語には「句動詞」という範疇がありません。日本語自身の語彙範疇でプロンプト全体を
構想し直してください。

## レベル別の要件（日本語自身の範疇で記述すること）

- **1-4**：多義語や基本語が文脈によってどの意味になるか（「かける」「あたる」「手」など）。
- **5-6**：慣用句、複合動詞、オノマトペ、比喩的に使われる和語。
- **7-9**：四字熟語、ことわざ、故事成語、慣用表現。このレベルでは単独の基本語を問っては**いけません**。

「7-9では複数語からなる表現を問うこと」という規則は英語的な発想（語数で区別する）の産物です。
**日本語自身**の基準で言い換えてください——たとえば「字義どおりに解釈できる普通の語ではなく、
四字熟語・ことわざ・慣用句であること」。

## フューショットの例

**2つ**の完全な例をご自身で創作してください（中級1つ、上級1つ）。要件：

- 例文は**自然な現代日本語**であり、あなた自身が書いたものであること。英語からの翻訳は不可。
- 問う対象は**日本語固有の語彙単位**（慣用句・四字熟語・多義語）であり、英単語は一切
  登場させないこと。ローマ字も不可。
- 各例に、例文・質問・4つの選択肢・正解・解説を含めること。
- 誤答の選択肢は、その語の**日本語における紛らわしい別解釈**であること。明らかに不合理な
  選択肢は不可。
""",
    },
}


CONTRACT = """\
## 出力契約（厳守）

1. 出力は**プロンプト本文そのもの**のみ。前置き・後書き・コードフェンス（```）は一切付けない。
2. 次の3つのプレースホルダを**各1回ずつ、この表記のまま**含めること：
   {prose} / {difficulty} / {previous_questions}
   - {prose} は問題の題材となる文章が差し込まれる位置。
   - {difficulty} は 1-9 の難易度が差し込まれる位置。
   - {previous_questions} は既出問題の一覧が差し込まれる位置（重複回避の指示と共に）。
3. 出力形式の指定として、次のJSONブロックを**波括弧を二重にしたまま**含めること：

{{
  "question_text": "...",
  "question_type": "vocabulary_context",
  "choices": ["...", "...", "...", "..."],
  "answer": "...",
  "explanation": "..."
}}

   キー名と "vocabulary_context" は英字のまま。値の例示は対象言語で書くこと。
   波括弧の二重化は差し込み処理の都合であり、**生成モデルに見せる説明ではない**。
   このブロックは「JSONオブジェクト」として説明すること。「二重波括弧」「波括弧を
   二つ」等の表記の話を本文に書いてはいけない（差し込み後には二重ではなくなるため、
   読み手を誤らせる）。
4. **上記3以外の箇所に英字（ラテン文字）を一切使わないこと。** 英単語・ローマ字・ピンイン・
   英語の術語（idiom, phrasal verb, few-shot, C2 など）はすべて対象言語の語に置き換える。
5. 正解の位置を固定しないこと。フューショットの例でも出力形式の例でも、正解が常に
   選択肢の1番目にあってはならない（例ごとに異なる位置に置く）。生成される問題の
   正解位置が偏らないよう、本文にもその旨の指示を1行入れること。
   ※ 下流の処理は選択肢をシャッフルしない。例の並びがそのまま位置バイアスになる。
6. 長さの目安は 1,500〜3,000 字。
"""


def _prompt_for(lang: str, retry_note: str = '') -> str:
    spec = BRIEFS[lang]
    return f"{spec['brief']}\n{CONTRACT}{retry_note}"


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def latin_runs(text: str) -> list[str]:
    """Every Latin-script token of 2+ characters, in order of appearance.

    Same metric applied to the incumbent row and the rewrite, so the before/after
    counts in the TASK-722 acceptance criteria are comparable.
    """
    return [run for run in LATIN_RUN.findall(text) if len(run) >= 2]


def offending_runs(text: str) -> list[str]:
    """Latin runs that are not template machinery — i.e. leaked English."""
    return [run for run in latin_runs(text)
            if len(run) >= 2 and run not in ALLOWED_LATIN_RUNS]


def verify(text: str) -> list[str]:
    """Return a list of contract violations. Empty means the rewrite is usable."""
    problems: list[str] = []

    for placeholder in REQUIRED_PLACEHOLDERS:
        count = text.count(placeholder)
        if count != 1:
            problems.append(f'placeholder {placeholder} appears {count}x, expected exactly 1')

    for key in JSON_KEYS:
        if f'"{key}"' not in text:
            problems.append(f'JSON key "{key}" missing from the output contract block')

    if '"vocabulary_context"' not in text:
        problems.append('question_type value "vocabulary_context" missing')

    # The template is rendered with str.format(): a literal brace must be doubled or
    # rendering raises KeyError/IndexError at generation time, not here.
    if '{{' not in text or '}}' not in text:
        problems.append('JSON block braces are not doubled ({{ / }}) — str.format will fail')

    leaked = offending_runs(text)
    if leaked:
        unique = sorted(set(leaked))
        problems.append(
            f'{len(leaked)} leaked Latin run(s), {len(unique)} distinct: '
            + ', '.join(repr(run) for run in unique[:20])
        )

    if text.lstrip().startswith('```'):
        problems.append('output is wrapped in a code fence')

    return problems


def strip_fence(text: str) -> str:
    """Drop a surrounding code fence if the model added one anyway."""
    stripped = text.strip()
    if not stripped.startswith('```'):
        return stripped
    lines = stripped.splitlines()
    lines = lines[1:]
    if lines and lines[-1].strip().startswith('```'):
        lines = lines[:-1]
    return '\n'.join(lines).strip()


def _render_check(text: str) -> str | None:
    """Actually run str.format the way question_generator.py will. Returns an error."""
    try:
        text.format(
            prose='（サンプル本文 / 示例段落）',
            difficulty=7,
            previous_questions='（なし / 无）',
        )
    except Exception as exc:  # KeyError, IndexError, ValueError — all fatal at gen time
        return f'{type(exc).__name__}: {exc}'
    return None


# ---------------------------------------------------------------------------
# Authoring loop
# ---------------------------------------------------------------------------

def author(lang: str, model: str, attempts: int, temperature: float,
           max_tokens: int) -> str:
    retry_note = ''
    last_text = ''

    for attempt in range(1, attempts + 1):
        print(f'[{lang}] attempt {attempt}/{attempts} on {model} ...', flush=True)
        try:
            raw = call_llm(
                _prompt_for(lang, retry_note),
                model=model,
                response_format='text',
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=300,
                pipeline='diag',
                task_name='question_vocabulary_context_rewrite',
            )
        except RuntimeError as exc:
            # See DEFAULT_MAX_TOKENS: on a thinking model this is nearly always the
            # reasoning budget, not a dead slug. Say so rather than let the caller
            # go hunting through prompt_templates.
            if 'empty content' in str(exc):
                print(f'[{lang}] empty content — likely reasoning exhausted the '
                      f'{max_tokens}-token budget; retry with a larger --max-tokens',
                      file=sys.stderr)
            raise
        last_text = strip_fence(str(raw))

        problems = verify(last_text)
        render_error = _render_check(last_text)
        if render_error:
            problems.append(f'str.format failed: {render_error}')

        if not problems:
            print(f'[{lang}] clean on attempt {attempt}', flush=True)
            return last_text

        print(f'[{lang}] {len(problems)} problem(s):', flush=True)
        for problem in problems:
            print(f'    - {problem}', flush=True)

        # Quote the failures back rather than restating the rules — a model that
        # ignored "no English" in the abstract usually complies when shown its own
        # leaked tokens.
        retry_note = (
            '\n\n## 前回の出力の問題点（必ず修正すること）\n\n'
            + '\n'.join(f'- {problem}' for problem in problems)
            + '\n\n同じ誤りを繰り返さず、契約を満たす完全な本文を再度出力してください。\n'
        )

    print(f'[{lang}] exhausted {attempts} attempts; returning the last output UNVERIFIED',
          file=sys.stderr)
    return last_text


def report(lang: str, text: str) -> None:
    problems = verify(text)
    render_error = _render_check(text)
    total = len(latin_runs(text))
    leaked = offending_runs(text)

    print()
    print(f'--- {lang} -------------------------------------------------')
    print(f'  length          : {len(text)} chars')
    print(f'  latin runs      : {total} total, {len(leaked)} leaked')
    if leaked:
        print(f'  leaked          : {sorted(set(leaked))}')
    print(f'  str.format      : {"OK" if render_error is None else render_error}')
    print(f'  contract        : {"PASS" if not problems else "FAIL"}')
    for problem in problems:
        print(f'    - {problem}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--lang', choices=sorted(BRIEFS), required=True)
    parser.add_argument('--model', default=DEFAULT_MODEL,
                        help=f'authoring model (default: {DEFAULT_MODEL})')
    parser.add_argument('--out', help='write the authored template here')
    parser.add_argument('--check', metavar='PATH',
                        help='verify an existing file instead of calling the model')
    parser.add_argument('--attempts', type=int, default=3,
                        help='authoring attempts before giving up (default: 3)')
    parser.add_argument('--temperature', type=float, default=0.7,
                        help='authoring temperature (default: 0.7 — prose, not extraction)')
    parser.add_argument('--max-tokens', type=int, default=DEFAULT_MAX_TOKENS,
                        help=f'completion budget, reasoning included '
                             f'(default: {DEFAULT_MAX_TOKENS})')
    args = parser.parse_args()

    # Without this, call_llm's own logging raises "SupabaseFactory not
    # initialized" and every authoring call lands in llm_calls as nothing at all
    # — so the run has no cost record. Mirrors measure_entailment_ab.py.
    if not args.check:
        SupabaseFactory.initialize()

    if args.check:
        with open(args.check, encoding='utf-8') as handle:
            text = handle.read()
        report(args.lang, text)
        return 0 if not verify(text) and _render_check(text) is None else 1

    text = author(args.lang, args.model, args.attempts, args.temperature,
                  args.max_tokens)
    report(args.lang, text)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(text)
        print(f'\nwrote {args.out}')

    return 0 if not verify(text) and _render_check(text) is None else 1


if __name__ == '__main__':
    raise SystemExit(main())
