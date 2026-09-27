# -*- coding: utf-8 -*-
"""Hand-transcribed subset of LinguaLoop's live DT rubric v6 config
(migrations/dt_rubric_v6_seed.sql) needed to build jev score/choice prompts,
plus the L2 instructional strings from services/dual_translation/prompts.py.

Hardcoded (not imported from services.*) so this experiment script never
imports repo modules with DB/side-effect-bearing imports at module load time.
Every string below is transcribed verbatim from the two source files cited.

Age tier per gold-set L2 (tests/fixtures/dt_gold/README.md):
  en -> age tier 3 (Arduino robot-arm passages)
  zh -> age tier 6 (favorite T-shirt passages)
  ja -> age tier 3 (robot-arm build passages)
"""

AGE_TIER = {"en": 3, "zh": 6, "ja": 3}

DIMENSIONS = ("accuracy", "fidelity", "understandability", "range", "naturalness")

# migrations/dt_rubric_v6_seed.sql "weights" block (carried unchanged from v5).
WEIGHTS_DEFAULT = {
    "accuracy": 0.3,
    "fidelity": 0.15,
    "naturalness": 0.1,
    "range": 0.15,
    "understandability": 0.3,
}
WEIGHTS_BY_LANGUAGE = {
    "ja": {"fidelity": 0.3},
    "zh": {"accuracy": 0.4},
}


def resolve_weights(lang: str) -> dict:
    overrides = WEIGHTS_BY_LANGUAGE.get(lang, {})
    return {d: overrides.get(d, WEIGHTS_DEFAULT[d]) for d in DIMENSIONS}

# services/dual_translation/prompts.py _DIMENSION_NAMES
DIMENSION_NAMES = {
    "en": {
        "accuracy": "accuracy (grammatical correctness)",
        "range": "range (articulateness / sophistication)",
        "understandability": "understandability (would a native speaker grasp the meaning)",
        "fidelity": "fidelity (meaning and register preserved)",
        "naturalness": "naturalness (how native it sounds)",
    },
    "zh": {
        "accuracy": "准确性（语法正确性）",
        "range": "丰富度（表达的成熟度与多样性）",
        "understandability": "可理解性（母语者能否理解原意）",
        "fidelity": "忠实度（意义与语域是否保留）",
        "naturalness": "自然度（是否像母语者的表达）",
    },
    "ja": {
        "accuracy": "正確さ（文法的な正しさ）",
        "range": "表現の幅（表現の成熟度・多様性）",
        "understandability": "理解可能性（母語話者が意味を理解できるか）",
        "fidelity": "忠実度（意味と文体・敬語レベルが保たれているか）",
        "naturalness": "自然さ（母語話者らしい表現かどうか）",
    },
}

# services/dual_translation/prompts.py _USER_PROMPT_LABELS -- also doubles as
# our jev `state` field labels (HARD RULE: state field labels wholly in L2).
REF_KEY = {"en": "reference", "zh": "参考译文", "ja": "参照文"}
LEARNER_KEY = {"en": "learner", "zh": "学习者译文", "ja": "学習者文"}

# Tier-invariant band descriptors (identical text at every tier 1-6 in the live
# seed) for accuracy / fidelity / understandability / range. Ascending order
# band1(worst) -> band4(best) for jev score-mode `criteria` arrays.
BAND_DESCRIPTORS_INVARIANT = {
    "accuracy": {
        "en": [
            "Multiple sentences break down grammatically; the reader has to reconstruct what was meant. (Four or more major errors, or a meaning-breaking one.)",
            "Grammar errors force rereading in at least one place; a pattern such as tense or agreement is unreliable. (Two or three major errors.)",
            "One or two slips a native reader notices but reads past without stopping. (One major error, or a few minor ones.)",
            "Grammatically clean throughout; a native reader moves through it without a stumble. (At most one minor slip.)",
        ],
        "zh": [
            "多个句子语法不成立，读者需要自行还原原意。（四处以上严重错误，或一处破坏理解的错误。）",
            "语法错误迫使读者至少在一处重读，某类结构（如语序或助词）不稳定。（两到三处严重错误。）",
            "有一两处母语者会察觉、但不影响阅读的小问题。（一处严重错误，或几处轻微错误。）",
            "通篇语法规范，母语者可以毫无停顿地读下来。（至多一处轻微问题。）",
        ],
        "ja": [
            "複数の文が文法的に成立せず、読者が意図を再構成する必要がある。（重大な誤り四個以上、または意味を壊す誤り一つ。）",
            "文法の誤りで少なくとも一箇所は読み直しが必要になり、ある構文パターン（助詞や時制など）が安定しない。（重大な誤り二〜三個。）",
            "母語話者は気づくが読み進めるのに支障のない誤りが一つ二つある。（重大な誤り一つ、または軽微な誤り数個。）",
            "全体を通して文法的に正しく、母語話者が引っかかることなく読み通せる。（あっても軽微な誤り一つ。）",
        ],
    },
    "fidelity": {
        "en": [
            "The reproduction states something the reference did not; meaning or register diverges far enough to mislead. (Four or more major departures, or a meaning-inverting one.)",
            "Part of the reference's message doesn't carry — the emphasis changes, or something the source made central is missing. (Two or three major departures.)",
            "A detail or nuance departs from the reference — a dropped modifier, an added aside, or a small tone shift a careful reader would flag. (One major departure, or a few minor ones.)",
            "Carries the reference's meaning and register faithfully — nothing added, dropped, or shifted in tone. (At most one minor wording difference.)",
        ],
        "zh": [
            "译文表达了参考译文没有的意思，意义或语域的偏离足以造成误导。（四处以上严重偏离，或一处意义相反的错误。）",
            "参考译文的部分信息没有传达——重心发生变化，或原文着重的内容缺失。（两到三处严重偏离。）",
            "有一处细节或语气与参考译文不符——遗漏修饰、添加补充，或语气略有变化，细心的读者会注意到。（一处严重偏离，或几处轻微偏离。）",
            "忠实传达参考译文的意义与语域，没有增添、遗漏或语气偏移。（至多一处轻微用词差异。）",
        ],
        "ja": [
            "参照文にない内容を述べており、意味または文体・敬語レベルのずれが誤解を招くほど大きい。（重大なずれ四個以上、または意味が逆転する誤り一つ。）",
            "参照文のメッセージの一部が伝わらない——重点が変わる、または原文が中心に据えた内容が欠ける。（重大なずれ二〜三個。）",
            "細部やニュアンスが参照文とずれている——修飾語の欠落、余分な補足、わずかな語調の変化など、注意深い読者なら気づく。（重大なずれ一つ、または軽微なずれ数個。）",
            "参照文の意味と文体・敬語レベルを忠実に伝え、追加・省略・語調のずれがない。（あっても軽微な語選択の違い一つ。）",
        ],
    },
    "range": {
        "en": [
            "Vocabulary and structure collapse to the simplest available forms — repetitive and generic against the reference. (Range far below the reference.)",
            "Reduced variety — leans on a few structures and generic vocabulary the reference avoided. (Range clearly below the reference.)",
            "Slightly narrower than the reference — a repeated structure, or a plainer word where the reference varied. (Minor flattening; most of the reference's range preserved.)",
            "Matches the variety of vocabulary and sentence structure the reference demands; no flattening into simpler forms. (Lexical and syntactic range on par with the reference.)",
        ],
        "zh": [
            "词汇与句式退化为最简单的形式——相较参考译文重复而笼统。（丰富度远低于参考译文。）",
            "变化明显减少——依赖少数句式与参考译文回避的笼统词汇。（丰富度明显低于参考译文。）",
            "比参考译文略窄——某处结构重复，或在参考译文有变化处用了更普通的词。（轻微简化，参考译文的大部分丰富度得以保留。）",
            "运用了与参考译文相当的词汇与句式变化，没有退化为更简单的形式。（词汇与句法的丰富度与参考译文相当。）",
        ],
        "ja": [
            "語彙と構文が最も単純な形へ収束している——参照文と比べて反復的で一般的。（幅が参照文より大幅に狭い。）",
            "幅が明らかに減っている——少数の構文と、参照文が避けた一般的な語彙に頼っている。（幅が参照文より明らかに狭い。）",
            "参照文よりわずかに狭い——構文の繰り返しや、参照文が変化させた箇所での平易な語の使用。（軽微な平板化、参照文の幅の大半は保たれている。）",
            "参照文が求めるのと同程度の語彙と構文の幅を用い、より単純な形へ平板化していない。（語彙・構文の幅が参照文と同等。）",
        ],
    },
    "understandability": {
        "en": [
            "A native reader cannot reliably recover the intended meaning without the reference. (Two or more meaning-breaking errors.)",
            "At least one passage leaves the reader unsure what was meant; the thread drops in places. (One meaning-breaking error, or four or more straining ones.)",
            "The message comes through, but the reader slows or guesses at one point to stay with it. (Two or three meaning-straining errors.)",
            "A native reader recovers the full intended meaning on one pass, without the reference. (At most one error that strains meaning.)",
        ],
        "zh": [
            "母语者在没有参考译文时无法可靠地还原原意。（两处以上破坏理解的错误。）",
            "至少有一处让读者无法确定原意，思路在部分地方中断。（一处破坏理解的错误，或四处以上影响理解的错误。）",
            "大意能够传达，但读者需要在某处放慢或猜测才能跟上。（两到三处影响理解的错误。）",
            "母语者一遍即可完全理解原意，无需参照参考译文。（至多一处影响理解的错误。）",
        ],
        "ja": [
            "母語話者は参照文なしでは意図した意味を確実に復元できない。（意味を壊す誤り二個以上。）",
            "少なくとも一箇所で読者が意図を確信できず、所々で筋が途切れる。（意味を壊す誤り一つ、または理解を妨げる誤り四個以上。）",
            "大意は伝わるが、ついていくために読者がどこか一箇所で読む速度を落とすか推測する必要がある。（理解を妨げる誤り二〜三個。）",
            "母語話者が一読で意図した意味を完全に把握でき、参照文を必要としない。（あっても理解を妨げる誤り一つ。）",
        ],
    },
}

# Naturalness is TIER-VARYING (ADR-018). Tier 3 (en/ja gold) and tier 6 (zh gold).
BAND_DESCRIPTORS_NATURALNESS = {
    3: {
        "en": [
            "Meaning survives but the phrasing is unnatural start to finish — assembled rather than spoken. (Non-native phrasing throughout.)",
            "Comprehensible but visibly non-native — word-for-word constructions a native teen would rephrase. (Several stilted or translated-sounding phrasings.)",
            "Clear and idiomatic apart from a phrasing choice or two a native teen wouldn't use. (One or two non-native turns of phrase.)",
            "Reads the way a native young teen would say it — plain, idiomatic phrasing for everyday topics. (A native peer would phrase it this way.)",
        ],
        "zh": [
            "意思能懂，但通篇表达都不自然——像拼凑而非自然说出。（通篇不地道。）",
            "能看懂但明显不像母语——逐字直译的结构，母语少年会重新组织。（若干生硬或翻译腔的表达。）",
            "清楚且地道，只有一两处母语少年不会用的说法。（一两处不地道的表达。）",
            "读起来就像母语少年的日常说法——用词朴素、地道。（母语同龄人也会这样表达。）",
        ],
        "ja": [
            "意味は通じるが全体を通して不自然——自然に発話されたというより組み立てられている。（全体を通して非母語的。）",
            "理解はできるが明らかに非母語的——逐語的な構文で、母語の中学生なら言い換える。（ぎこちない、または翻訳調の言い回しがいくつか。）",
            "明快で自然だが、母語の中学生なら使わない言い回しが一つ二つある。（不自然な言い回し一つ二つ。）",
            "母語話者の中学生が言うように読める——日常の話題を素朴で自然な言い回しで表す。（母語の同年代も同じ言い方をする。）",
        ],
    },
    6: {
        "en": [
            "Unidiomatic for the register start to finish — the reader registers a non-native writer throughout. (Non-native phrasing throughout.)",
            "Fluent but recognisably non-native — phrasing and register choices an educated native would not make. (Several stilted or translated-sounding phrasings.)",
            "Near-native, with a subtle collocation or register nuance that reveals a non-native hand. (One or two non-native turns of phrase.)",
            "Indistinguishable from an educated native writer — idiomatic, register-precise, naturally cohesive. (A native peer would phrase it this way.)",
        ],
        "zh": [
            "意思清楚，但就受过教育的语体而言通篇不地道。（通篇不地道。）",
            "流畅但明显非母语——受过教育的母语者不会做出的措辞与语体选择。（若干生硬或翻译腔的表达。）",
            "接近母语，只有一处细微的搭配或语体差别透露出非母语的痕迹。（一两处不地道的表达。）",
            "与受过教育的母语作者无异——地道、语体精准、衔接自然。（母语同龄人也会这样表达。）",
        ],
        "ja": [
            "意味は明快だが、教養ある語体としては全体を通して不自然。（全体を通して非母語的。）",
            "流暢だが明らかに非母語的——教養ある母語話者ならしない言い回しや語体の選択。（ぎこちない、または翻訳調の言い回しがいくつか。）",
            "ほぼ母語話者並みだが、非母語的な手つきを覗かせる微妙なコロケーションや語体のニュアンスが一つある。（不自然な言い回し一つ二つ。）",
            "教養ある母語話者の書き手と見分けがつかない——自然で、語体が精密、結束性も自然。（母語の同年代も同じ言い方をする。）",
        ],
    },
}


def band_descriptors(dim: str, lang: str) -> list:
    """4-level ascending (band1..band4) descriptor array for one (dim, lang)."""
    if dim == "naturalness":
        return BAND_DESCRIPTORS_NATURALNESS[AGE_TIER[lang]][lang]
    return BAND_DESCRIPTORS_INVARIANT[dim][lang]


# ---------------------------------------------------------------------------
# Instruction templates (native language). {dim} is filled with DIMENSION_NAMES.
# ---------------------------------------------------------------------------

SCORE_INSTRUCTION_TMPL = {
    "en": "Score the `{learner_key}` text's {dim}, judged against the `{ref_key}` text, using the ordered level descriptions in criteria (level 0 = worst, level 3 = best).",
    "zh": "请对照【{ref_key}】评估【{learner_key}】在“{dim}”方面的表现，依据 criteria 中由差到好排列的各等级描述评分。",
    "ja": "「{ref_key}」と「{learner_key}」を比較し、「{learner_key}」の{dim}を、criteria の悪い方から良い方へ並んだ各段階の説明に基づいて評価してください。",
}

CHOICE_INSTRUCTION_TMPL = {
    "en": "Which level best describes the `{learner_key}` text's {dim}, judged against the `{ref_key}` text? Pick exactly one option from criteria.",
    "zh": "对照【{ref_key}】，【{learner_key}】在“{dim}”方面最符合 criteria 中的哪一个等级？请从中选择唯一一项。",
    "ja": "「{ref_key}」と比較して、「{learner_key}」の{dim}に最もよく当てはまる段階はどれですか。criteria の中から一つだけ選んでください。",
}

CHOICE_LEVEL_KEYS = ["band1", "band2", "band3", "band4"]

# NR variant 2: reworded instructions anchoring naturalness on "would a
# native of this age tier phrase it this way" and range on "kept the
# reference's specific vocabulary/structures vs flattened to generic ones",
# instead of the generic "score X judged against Y" template. Same criteria
# (band_descriptors) -- only the instruction sentence changes, isolating
# wording sensitivity. Coordinator-specified anchors, authored natively.
SCORE_INSTRUCTION_V2 = {
    "naturalness": {
        "en": "Would a native speaker of the same age group phrase the `{learner_key}` text this way, judged against the `{ref_key}` text? Score using the ordered level descriptions in criteria (level 0 = worst, level 3 = best).",
        "zh": "同龄的母语者会像【{learner_key}】这样表达吗？请对照【{ref_key}】，依据 criteria 中由差到好排列的各等级描述评分。",
        "ja": "同年代の母語話者は「{learner_key}」のようにこの文を言うでしょうか。「{ref_key}」と比較して、criteria の悪い方から良い方へ並んだ各段階の説明に基づいて評価してください。",
    },
    "range": {
        "en": "Does the `{learner_key}` text keep the specific vocabulary and sentence structures the `{ref_key}` text uses, or does it flatten into more generic, simpler ones? Score using the ordered level descriptions in criteria (level 0 = worst, level 3 = best).",
        "zh": "【{learner_key}】是否保留了【{ref_key}】中使用的具体词汇和句式，还是退化成了更笼统、更简单的表达？请依据 criteria 中由差到好排列的各等级描述评分。",
        "ja": "「{learner_key}」は「{ref_key}」で使われている具体的な語彙や構文を保っていますか、それともより一般的で単純な表現に平板化していますか。criteria の悪い方から良い方へ並んだ各段階の説明に基づいて評価してください。",
    },
}

NOUL_OMISSION = {
    "en": {
        "instructions": "Does the `{learner_key}` text omit meaning that is present in the `{ref_key}` text?",
        "true": "Some idea, detail, or clause present in the reference is missing from the learner text.",
        "false": "Everything the reference expresses is also present in the learner text (paraphrase is fine).",
    },
    "zh": {
        "instructions": "【{learner_key}】是否遗漏了【{ref_key}】中出现的意思？",
        "true": "参考译文中出现的某个意思、细节或从句在学习者译文中缺失。",
        "false": "参考译文表达的内容在学习者译文中都有体现（改述也算）。",
    },
    "ja": {
        "instructions": "「{learner_key}」は「{ref_key}」にある意味を省略していますか？",
        "true": "参照文にある内容・細部・節のいずれかが学習者文に欠けている。",
        "false": "参照文が伝える内容はすべて学習者文にも表れている（言い換えは可）。",
    },
}

NOUL_GRAMMAR = {
    "en": {
        "instructions": "Does the `{learner_key}` text contain a grammar error?",
        "true": "The learner text has at least one grammatical mistake (e.g. tense, agreement, word form, article, particle).",
        "false": "The learner text is grammatically correct throughout.",
    },
    "zh": {
        "instructions": "【{learner_key}】中是否存在语法错误？",
        "true": "学习者译文中至少存在一处语法错误（如时态、一致性、词形、量词、语序等）。",
        "false": "学习者译文通篇语法正确。",
    },
    "ja": {
        "instructions": "「{learner_key}」に文法的な誤りがありますか？",
        "true": "学習者文に少なくとも一つ文法的な誤りがある（時制・助詞・活用・語順など）。",
        "false": "学習者文は全体を通して文法的に正しい。",
    },
}


# ---------------------------------------------------------------------------
# jev_dt_2026-09-26 additions: labels + instruction templates for the
# decomposed A1 (passage-level) / A2 (sentence-level-with-context) / NR
# (naturalness+range) arms. Native-language throughout, same discipline as
# the block above (REF_KEY/LEARNER_KEY/NOUL_*/SCORE_*/CHOICE_* templates).
# ---------------------------------------------------------------------------

# A2 needs four distinct state keys (full passage x2, focus sentence x2)
# instead of REF_KEY/LEARNER_KEY's two.
FULL_REF_KEY = {"en": "reference passage", "zh": "参考译文全文", "ja": "参照文全体"}
FULL_LEARNER_KEY = {"en": "learner passage", "zh": "学习者译文全文", "ja": "学習者文全体"}
FOCUS_REF_KEY = {"en": "focus reference sentence", "zh": "参考译文焦点句", "ja": "参照文の焦点文"}
FOCUS_LEARNER_KEY = {"en": "focus learner sentence", "zh": "学习者译文焦点句", "ja": "学習者文の焦点文"}

# has_error: noul, passage-level (A1: ref_key/learner_key) or sentence-level
# with passage context (A2: focus_ref_key/focus_learner_key).
HAS_ERROR_NOUL = {
    "en": {
        "instructions": "Does the `{learner_key}` text contain a translation error compared to the `{ref_key}` text?",
        "true": "The learner text contains at least one translation error relative to the reference (grammar, meaning, word choice, register, or naturalness).",
        "false": "The learner text contains no translation error relative to the reference.",
    },
    "zh": {
        "instructions": "【{learner_key}】相对于【{ref_key}】是否存在翻译错误？",
        "true": "学习者译文相对于参考译文至少存在一处翻译错误（语法、意义、用词、语域或自然度方面）。",
        "false": "学习者译文相对于参考译文没有翻译错误。",
    },
    "ja": {
        "instructions": "「{learner_key}」は「{ref_key}」と比べて翻訳の誤りがありますか？",
        "true": "学習者文には参照文と比べて少なくとも一つ翻訳の誤りがある（文法・意味・語彙選択・文体・自然さのいずれか）。",
        "false": "学習者文には参照文と比べて翻訳の誤りがない。",
    },
}

HAS_ERROR_NOUL_FOCUS_SUFFIX = {
    "en": " Judge the `{focus_learner_key}` sentence against the `{focus_ref_key}` sentence; the full passages are given only as context.",
    "zh": "请对照【{focus_ref_key}】评估【{focus_learner_key}】；完整段落仅作为上下文参考。",
    "ja": "「{focus_ref_key}」と比較して「{focus_learner_key}」を判断してください。全文は文脈として示しているだけです。",
}

# meaning_changed: noul, same two levels (passage / focus sentence).
MEANING_CHANGED_NOUL = {
    "en": {
        "instructions": "Does the `{learner_key}` text change the meaning conveyed by the `{ref_key}` text?",
        "true": "The learner text conveys a different meaning than the reference (something added, dropped, or altered enough to mislead).",
        "false": "The learner text conveys the same meaning as the reference (paraphrase is fine).",
    },
    "zh": {
        "instructions": "【{learner_key}】是否改变了【{ref_key}】所表达的意思？",
        "true": "学习者译文所表达的意思与参考译文不同（增添、遗漏或改变到足以造成误导的程度）。",
        "false": "学习者译文所表达的意思与参考译文相同（改述也算相同）。",
    },
    "ja": {
        "instructions": "「{learner_key}」は「{ref_key}」が伝える意味を変えていますか？",
        "true": "学習者文が伝える意味は参照文と異なる（追加・省略、または誤解を招くほどの変化がある）。",
        "false": "学習者文が伝える意味は参照文と同じである（言い換えは可）。",
    },
}

MEANING_CHANGED_NOUL_FOCUS_SUFFIX = HAS_ERROR_NOUL_FOCUS_SUFFIX

# subtype: choice mode. Options come from taxonomy_data.SUBTYPES[lang] +
# taxonomy_data.NO_ERROR_OPTION[lang], described natively via
# taxonomy_data.SUBTYPE_GLOSS[lang].
SUBTYPE_CHOICE_INSTRUCTION = {
    "en": "If the `{learner_key}` text contains a translation error compared to the `{ref_key}` text, which category best describes it? Pick \"no error\" if there is none.",
    "zh": "如果【{learner_key}】相对于【{ref_key}】存在翻译错误，最符合下列哪一类？如果没有错误，请选择“无错误”。",
    "ja": "「{learner_key}」が「{ref_key}」と比べて翻訳の誤りを含む場合、最も当てはまるのはどのカテゴリーですか？誤りがない場合は「誤りなし」を選んでください。",
}

SUBTYPE_CHOICE_FOCUS_SUFFIX = {
    "en": " Judge the `{focus_learner_key}` sentence against the `{focus_ref_key}` sentence; the full passages are given only as context.",
    "zh": "请对照【{focus_ref_key}】评估【{focus_learner_key}】；完整段落仅作为上下文参考。",
    "ja": "「{focus_ref_key}」と比較して「{focus_learner_key}」を判断してください。全文は文脈として示しているだけです。",
}


# ---------------------------------------------------------------------------
# Arm A3 additions (built, not yet run): narrow noul probes on the focus
# sentence + an explicit "acceptable variation is not an error" has_error
# variant. Native language throughout, same discipline as every block above.
# ---------------------------------------------------------------------------

# has_error, A3 variant: explicitly rules out acceptable variation as an
# error (synonym choice, kana/kanji or 得/地/的-class variants, punctuation).
HAS_ERROR_NOUL_VARIANT_ACCEPTABLE_VARIATION = {
    "en": {
        "instructions": ("Does the `{learner_key}` text contain a translation error compared to "
                          "the `{ref_key}` text? Acceptable variation is NOT an error: a synonym, "
                          "a kana/kanji or comparable script choice, an optional punctuation "
                          "difference, or another faithful paraphrase all count as correct."),
        "true": "The learner text contains at least one real translation error relative to the reference -- not mere acceptable variation.",
        "false": "The learner text has no translation error; any differences from the reference are acceptable variation (synonym, script choice, punctuation, faithful paraphrase) or none at all.",
    },
    "zh": {
        "instructions": ("【{learner_key}】相对于【{ref_key}】是否存在翻译错误？可接受的变化不算错误："
                          "同义词替换、假名/汉字或“的/地/得”一类的写法差异、可选的标点差异，"
                          "或其他忠实的改述，都算正确。"),
        "true": "学习者译文相对于参考译文至少存在一处真正的翻译错误——而不只是可接受的变化。",
        "false": "学习者译文没有翻译错误；与参考译文的差异（如同义词、写法选择、标点、忠实的改述）都是可接受的变化，或根本没有差异。",
    },
    "ja": {
        "instructions": ("「{learner_key}」は「{ref_key}」と比べて翻訳の誤りがありますか？許容範囲の"
                          "違いは誤りに数えません——同義語の言い換え、仮名/漢字などの表記の違い、"
                          "任意の句読点の違い、その他の忠実な言い換えはすべて正しいものとみなします。"),
        "true": "学習者文には参照文と比べて少なくとも一つ本当の翻訳の誤りがある——単なる許容範囲の違いではない。",
        "false": "学習者文には翻訳の誤りがない。参照文との違い（同義語、表記の選択、句読点、忠実な言い換えなど）はすべて許容範囲の変化であるか、そもそも違いがない。",
    },
}

# Narrow noul probes, sentence-level (focus sentence vs focus reference).
# Each key maps to reqbuild.NARROW_SUBTYPE_MAP's "best-matching v5 subtype".
NARROW_NOUL = {
    "negation": {
        "en": {
            "instructions": "Is the polarity (negation) of the `{focus_learner_key}` sentence reversed compared to the `{focus_ref_key}` sentence (e.g. affirmative vs negative, can vs cannot)?",
            "true": "The learner sentence asserts the opposite polarity of the reference (negative where the reference is affirmative, or vice versa).",
            "false": "The learner sentence's polarity matches the reference.",
        },
        "zh": {
            "instructions": "【{focus_learner_key}】句相对于【{focus_ref_key}】句，肯定／否定（极性）是否被反转了（例如肯定变否定、能变不能）？",
            "true": "学习者句子的极性与参考句相反（参考是肯定则学习者是否定，反之亦然）。",
            "false": "学习者句子的极性与参考句一致。",
        },
        "ja": {
            "instructions": "「{focus_learner_key}」の文は「{focus_ref_key}」の文に比べて、肯定・否定（極性）が逆転していますか（例：肯定と否定、できるとできない）？",
            "true": "学習者文の極性は参照文と逆である（参照文が肯定なら学習者文は否定、またはその逆）。",
            "false": "学習者文の極性は参照文と一致している。",
        },
        "subtype": "word_choice",
    },
    "quantity": {
        "en": {
            "instructions": "Is a quantity or number changed in the `{focus_learner_key}` sentence compared to the `{focus_ref_key}` sentence (e.g. singular vs plural, a different count or amount)?",
            "true": "A number/quantity in the learner sentence differs from the reference (wrong count, singular/plural, or amount).",
            "false": "Every number/quantity in the learner sentence matches the reference.",
        },
        "zh": {
            "instructions": "【{focus_learner_key}】句相对于【{focus_ref_key}】句，数量或数目是否发生了变化（例如单复数、数量或数目不同）？",
            "true": "学习者句子中的某个数量/数目与参考句不同（数量、单复数或数目有误）。",
            "false": "学习者句子中的所有数量/数目都与参考句一致。",
        },
        "ja": {
            "instructions": "「{focus_learner_key}」の文は「{focus_ref_key}」の文に比べて、数量や個数が変わっていますか（例：単数と複数、数量や個数の違い）？",
            "true": "学習者文の数量・個数のいずれかが参照文と異なる（数、単複、量の誤り）。",
            "false": "学習者文の数量・個数はすべて参照文と一致している。",
        },
        "subtype": "word_choice",
    },
    "agent_direction": {
        "en": {
            "instructions": "Is the agent (who does the action) or direction of the action swapped in the `{focus_learner_key}` sentence compared to the `{focus_ref_key}` sentence (e.g. active vs passive with a different actor, or a reversed direction such as give vs receive, to vs from)?",
            "true": "The learner sentence swaps who acts on whom, or reverses the direction of the action, compared to the reference.",
            "false": "The agent and direction of the action in the learner sentence match the reference.",
        },
        "zh": {
            "instructions": "【{focus_learner_key}】句相对于【{focus_ref_key}】句，动作的施事者（谁做动作）或方向是否被调换了（例如主动变被动且施事者不同，或方向相反，如“给”变“收到”、“去”变“来”）？",
            "true": "学习者句子中动作的施事者或方向与参考句相反或被调换了。",
            "false": "学习者句子中动作的施事者与方向都与参考句一致。",
        },
        "ja": {
            "instructions": "「{focus_learner_key}」の文は「{focus_ref_key}」の文に比べて、動作の主体（誰がするか）や方向が入れ替わっていますか（例：能動と受動で動作主が違う、あげるともらう、行くと来るなど方向が逆）？",
            "true": "学習者文では動作の主体や方向が参照文と入れ替わっている、または逆になっている。",
            "false": "学習者文の動作の主体と方向は参照文と一致している。",
        },
        "subtype": "word_order",
    },
    "meaning_omitted": {
        "en": {
            "instructions": "Does the `{focus_learner_key}` sentence omit meaning that is present in the `{focus_ref_key}` sentence?",
            "true": "Some idea, detail, or clause present in the reference sentence is missing from the learner sentence.",
            "false": "Everything the reference sentence expresses is also present in the learner sentence (paraphrase is fine).",
        },
        "zh": {
            "instructions": "【{focus_learner_key}】句是否遗漏了【{focus_ref_key}】句中出现的意思？",
            "true": "参考句中出现的某个意思、细节或从句在学习者句子中缺失。",
            "false": "参考句表达的内容在学习者句子中都有体现（改述也算）。",
        },
        "ja": {
            "instructions": "「{focus_learner_key}」の文は「{focus_ref_key}」の文にある意味を省略していますか？",
            "true": "参照文の文にある内容・細部・節のいずれかが学習者文の文に欠けている。",
            "false": "参照文の文が伝える内容はすべて学習者文の文にも表れている（言い換えは可）。",
        },
        "subtype": "omission",
    },
    "meaning_added": {
        "en": {
            "instructions": "Does the `{focus_learner_key}` sentence add meaning that is NOT present in the `{focus_ref_key}` sentence?",
            "true": "The learner sentence states an idea, detail, or clause the reference sentence does not contain.",
            "false": "The learner sentence adds nothing beyond what the reference sentence expresses.",
        },
        "zh": {
            "instructions": "【{focus_learner_key}】句是否添加了【{focus_ref_key}】句中没有的意思？",
            "true": "学习者句子表达了参考句没有的某个意思、细节或从句。",
            "false": "学习者句子没有添加参考句之外的内容。",
        },
        "ja": {
            "instructions": "「{focus_learner_key}」の文は「{focus_ref_key}」の文にない意味を加えていますか？",
            "true": "学習者文の文は参照文の文にない内容・細部・節を述べている。",
            "false": "学習者文の文は参照文の文が伝える以上のことを加えていない。",
        },
        "subtype": "addition",
    },
}

# ---------------------------------------------------------------------------
# Severity variants S2/S4 (S1 = existing meaning_changed noul; S3 is a pure
# Python prior over taxonomy_data.SUBTYPE_DEFAULT_SEVERITY, no new question).
# Coordinator correction: gold "major" != "meaning changed" (MQM major =
# clearly wrong / noticeably impairs quality even if meaning is still
# recoverable) -- these two new questions target THAT distinction directly,
# instead of inferring severity from meaning_changed alone.
#
# No literal "severity guidance" prose block exists in migrations/
# dt_rubric_v6_seed.sql (checked) -- only numeric severity_weights and 3
# worked `exemplars` (EN tense_aspect=minor "lives"/"has lived", JA
# particle_wa_ga=major, ZH aspect_marker=major). These native definitions
# are AUTHORED to match the coordinator's MQM gloss and calibrated against
# those exemplars, not transcribed from a taxonomy field -- flagged here
# the same way ADR-019 flags other AI-authored native strings pending review.
# ---------------------------------------------------------------------------

SEVERITY_CHOICE_LEVELS = {
    "en": {
        "minor": "A small slip a native reader notices, but the sentence still reads acceptably overall (e.g. a minor tense slip like \"lives\" for \"has lived\").",
        "major": "Clearly wrong to a native reader -- it noticeably impairs the sentence, even though the intended meaning can usually still be recovered (e.g. a wa/ga mix-up, a missing aspect marker).",
        "critical": "The meaning is lost, inverted, or actively misleading -- a native reader would come away with the wrong idea.",
    },
    "zh": {
        "minor": "母语者会注意到的小失误，但整句读起来仍然可以接受（例如轻微的时态问题，如把“has lived”写成“lives”）。",
        "major": "母语者会一眼看出明显错误——明显损害了这句话的质量，但通常仍能推断出原意（例如は/が混淆、体标记缺失）。",
        "critical": "意思丢失、被反转或具有误导性——母语者会因此得出错误的理解。",
    },
    "ja": {
        "minor": "母語話者が気づく程度の小さな誤りだが、文全体としてはまだ許容範囲で読める（例：“has lived”を“lives”と書くような軽い時制の誤り）。",
        "major": "母語話者が見て明らかに誤りだとわかる——文の質を明らかに損なうが、多くの場合まだ意図した意味を推測できる（例：は/がの混同、アスペクトマーカーの欠落）。",
        "critical": "意味が失われている、逆転している、または誤解を招く——母語話者はそこから誤った理解を持ち帰ってしまう。",
    },
}

SEVERITY_CHOICE_INSTRUCTION = {
    "en": "Which severity level best describes the translation error (if any) in the `{focus_learner_key}` sentence compared to the `{focus_ref_key}` sentence? Pick \"no_error\" if there is none.",
    "zh": "对照【{focus_ref_key}】，【{focus_learner_key}】句中的翻译错误（如果有的话）最符合下列哪个严重程度？如果没有错误，请选择“无错误”。",
    "ja": "「{focus_ref_key}」と比較して、「{focus_learner_key}」の文にある翻訳の誤り（もしあれば）の深刻度として最も当てはまるのはどれですか。誤りがない場合は「誤りなし」を選んでください。",
}

# S4: "would a native reader immediately see this as clearly wrong" noul,
# independent of whether meaning is still recoverable (unlike meaning_changed).
NATIVE_WRONG_NOUL = {
    "en": {
        "instructions": "Would a native reader immediately see the `{focus_learner_key}` sentence as clearly wrong compared to the `{focus_ref_key}` sentence, regardless of whether the intended meaning is still recoverable?",
        "true": "A native reader would immediately flag the learner sentence as wrong -- it stands out as incorrect on a first read.",
        "false": "A native reader would not immediately flag anything wrong (or the difference is at most a small, easy-to-miss slip).",
    },
    "zh": {
        "instructions": "无论是否仍能推断出原意，母语者是否会立刻觉得【{focus_learner_key}】句相对于【{focus_ref_key}】句明显有问题？",
        "true": "母语者一眼就会觉得学习者的句子有问题——第一次读就会察觉不对。",
        "false": "母语者不会立刻察觉问题（或者差异只是很小、容易被忽略的失误）。",
    },
    "ja": {
        "instructions": "意図した意味が推測できるかどうかにかかわらず、母語話者は「{focus_learner_key}」の文が「{focus_ref_key}」の文に比べて明らかにおかしいとすぐに気づきますか？",
        "true": "母語話者は一読してすぐに学習者文がおかしいと気づく。",
        "false": "母語話者はすぐには問題に気づかない（あるいは違いはごく小さく見逃しやすい程度である）。",
    },
}

