# -*- coding: utf-8 -*-
"""Hand-transcribed subset of the live v5 DT error taxonomy
(migrations/dt_taxonomy_v5_seed.sql) needed to build jev subtype-choice
prompts natively per language, plus the "understandability" scoring rule
(every error counts) and per-subtype `dimension` (accuracy/fidelity/
naturalness) that services.dual_translation.scoring.compute_dimension_bands
consumes.

Hardcoded (not read from the DB) for the same reason as the prior exp_c
run's rubric_data.py: this experiment must never touch the DB, and the SQL
seed file is a static migration, not a live table read. Every string below
is transcribed verbatim from migrations/dt_taxonomy_v5_seed.sql.

Only the single-language ("en"/"zh"/"ja") subtype lists are used — the
per-L1-pair keys (ja-en, zh-ja, ...) in the live taxonomy are identical to
these for a given target L2, so there is nothing pair-specific to transcribe.
"""
from __future__ import annotations

# migrations/dt_taxonomy_v5_seed.sql "pairs" block, single-language entries.
SUBTYPES = {
    "en": [
        "omission", "addition", "word_choice", "collocation", "word_order",
        "register", "orthography", "cohesion_connective", "article",
        "preposition", "tense_aspect", "subject_verb_agreement",
        "plural_number", "phrasal_verb", "pronoun_reference",
    ],
    "zh": [
        "omission", "addition", "word_choice", "collocation", "word_order",
        "register", "orthography", "cohesion_connective", "classifier",
        "aspect_marker", "de_particles", "ba_construction", "bei_passive",
        "resultative_complement", "directional_complement",
        "adverbial_order", "topic_comment",
    ],
    "ja": [
        "omission", "addition", "word_choice", "collocation", "word_order",
        "register", "orthography", "cohesion_connective", "particle_wa_ga",
        "particle_case", "particle_other", "verb_conjugation",
        "tense_aspect_ja", "keigo_register", "counter_classifier",
        "script_choice", "topic_comment",
    ],
}

# migrations/dt_taxonomy_v5_seed.sql "subtype_meta" block: dimension only
# (the field compute_dimension_bands reads). "understandability" is not a
# subtype_meta dimension -- every non-is_mistake error feeds it regardless.
SUBTYPE_DIMENSION = {
    "omission": "fidelity",
    "addition": "fidelity",
    "word_choice": "fidelity",
    "collocation": "naturalness",
    "word_order": "accuracy",
    "register": "fidelity",
    "orthography": "accuracy",
    "cohesion_connective": "naturalness",
    "article": "accuracy",
    "preposition": "accuracy",
    "tense_aspect": "accuracy",
    "subject_verb_agreement": "accuracy",
    "plural_number": "accuracy",
    "phrasal_verb": "fidelity",
    "pronoun_reference": "accuracy",
    "particle_wa_ga": "accuracy",
    "particle_case": "accuracy",
    "particle_other": "accuracy",
    "verb_conjugation": "accuracy",
    "tense_aspect_ja": "accuracy",
    "keigo_register": "fidelity",
    "counter_classifier": "accuracy",
    "script_choice": "accuracy",
    "topic_comment": "naturalness",
    "classifier": "accuracy",
    "aspect_marker": "accuracy",
    "de_particles": "accuracy",
    "ba_construction": "accuracy",
    "bei_passive": "accuracy",
    "resultative_complement": "accuracy",
    "directional_complement": "accuracy",
    "adverbial_order": "accuracy",
}

# migrations/dt_taxonomy_v5_seed.sql "subtype_meta.default_severity" field --
# the taxonomy's own per-subtype severity prior (post-TASK-625 minor/major
# vocabulary; no subtype defaults to "critical" in the live seed). S3's
# Python-prior severity variant reads this.
SUBTYPE_DEFAULT_SEVERITY = {
    "omission": "major",
    "addition": "minor",
    "word_choice": "minor",
    "collocation": "minor",
    "word_order": "major",
    "register": "major",
    "orthography": "minor",
    "cohesion_connective": "minor",
    "article": "minor",
    "preposition": "minor",
    "tense_aspect": "major",
    "subject_verb_agreement": "minor",
    "plural_number": "minor",
    "phrasal_verb": "minor",
    "pronoun_reference": "major",
    "particle_wa_ga": "major",
    "particle_case": "major",
    "particle_other": "minor",
    "verb_conjugation": "major",
    "tense_aspect_ja": "major",
    "keigo_register": "major",
    "counter_classifier": "minor",
    "script_choice": "minor",
    "topic_comment": "minor",
    "classifier": "minor",
    "aspect_marker": "major",
    "de_particles": "minor",
    "ba_construction": "major",
    "bei_passive": "major",
    "resultative_complement": "major",
    "directional_complement": "minor",
    "adverbial_order": "major",
    "particle": "major",
}

# migrations/dt_taxonomy_v5_seed.sql "subtype_glosses" block -- short native
# descriptions, one per (subtype, language) pair actually used by that
# language's pairs list above. Transcribed verbatim.
SUBTYPE_GLOSS = {
    "zh": {
        "omission": "成分缺失——参考译文中的某个意思、细节或从句在学习者译文中完全没有出现（不是写错了形式，而是这层意思根本不存在）",
        "addition": "多余添加——加入了参考译文中没有的词或信息（冗余重复或不必要的插入）",
        "word_choice": "词语选择——用词错误或不自然（意思接近但用词不当）",
        "collocation": "词语搭配——单个词都对，但搭配不自然（不符合习惯的固定搭配）",
        "word_order": "语序——词语或成分的排列顺序不自然或不合语法",
        "register": "语域——正式程度或语气与语境不符",
        "orthography": "拼写／书写——拼写、大小写或书写形式的错误（想表达的词是清楚的）",
        "cohesion_connective": "衔接／连接词——连接词（然而、因此、所以、但是等）缺失或误用，导致句子衔接不畅",
        "classifier": "量词——量词使用错误或与名词搭配不当。常见错误是一律用“个”代替专用量词（如应为一本书、一件衣服、一只猫），或量词与名词不匹配",
        "aspect_marker": "体标记——“了／过／着”等体标记使用错误。汉语用体（aspect）而非时态：了表示完成，过表示曾经经历，着表示持续状态；不能按外语的时态直接对应",
        "de_particles": "结构助词“的／得／地”——三个 de 的误用：定语用“的”、状语用“地”、补语用“得”",
        "ba_construction": "把字句——“把”字结构使用错误或缺失",
        "bei_passive": "被字句——“被”字被动结构使用错误或缺失（受事、施事、动词的语序与标记）",
        "resultative_complement": "结果补语——结果补语使用错误或缺失",
        "directional_complement": "趋向补语——“来／去／上／下／进／出”等趋向补语使用错误或缺失，表示动作的方向",
        "adverbial_order": "状语语序——时间、地点、方式等状语的位置错误（汉语状语一般在动词之前，语序较固定）",
        "topic_comment": "话题—评论结构——话题/主语—述题结构使用不当（常为母语结构的过度迁移）",
    },
    "ja": {
        "omission": "要素の欠落——参照文にある意味・細部・節が学習者文に全く現れていない（形が間違っているのではなく、その意味自体が存在しない）",
        "addition": "余分な追加——参照文にない語や情報を加えている（冗長な繰り返しや不要な挿入など）",
        "word_choice": "語彙選択——語の選び方が誤っている、または不自然（意味は近いが語が不適切）",
        "collocation": "コロケーション——語自体は正しいが、組み合わせが不自然（自然には共起しない語の結び付き）",
        "word_order": "語順——語や成分の並び順が不自然、または文法的に誤っている",
        "register": "文体・語調——場面に対して丁寧さや語調のレベルが合っていない",
        "orthography": "表記・綴り——綴り、送り仮名、記号など表記上の誤り（意図した語は明らか）",
        "cohesion_connective": "結束性・接続表現——接続語（しかし、したがって、だから等）の誤り・欠落により文のつながりが弱い",
        "particle_wa_ga": "助詞「は」／「が」——主題の「は」と主語（新情報）の「が」の使い分けの誤り。従属節・関係節の主語は「が」、既知の主題は「は」など",
        "particle_case": "格助詞——「を」（対象）、「に」（着点・時・相手）、「で」（場所・手段）、「へ」（方向）など格助詞の誤り",
        "particle_other": "その他の助詞——並列助詞（や・と・か）、取り立て助詞（も・だけ・しか）、終助詞など、格助詞以外の助詞の誤り",
        "verb_conjugation": "動詞の活用——て形、可能形、受身、使役などの活用の誤り（ら抜き言葉を含む）",
        "tense_aspect_ja": "テンス・アスペクト——「た」（完了・過去）と「ている」（進行・結果状態）などの使い分けの誤り",
        "keigo_register": "敬語——敬語レベルの誤り。丁寧語（です・ます）、尊敬語（相手の動作を高める）、謙譲語（自分の動作をへりくだる）の使い分けを含む。文法的に正しくても、場面に求められる敬意レベルと異なれば誤りとする",
        "counter_classifier": "助数詞——数を数える際の助数詞（カウンター）の誤り",
        "script_choice": "表記の選択——仮名／漢字の使い分けの誤り（同じ語をどの文字種で書くか）",
        "topic_comment": "主題—解説構造——「は」による主題提示など、主題と解説の組み立て方の誤り",
    },
    "en": {
        "omission": "omission -- meaning content from the reference is entirely missing from the learner text (not a wrong form of something present, but a piece of meaning that is simply not there)",
        "addition": "addition -- extra words or information not present in the reference",
        "word_choice": "word choice -- a wrong or unnatural lexical choice",
        "collocation": "collocation -- individually correct words that do not naturally combine",
        "word_order": "word order -- words or phrases arranged in an unnatural or ungrammatical sequence",
        "register": "register -- wrong level of formality or tone for the context",
        "orthography": "orthography -- a spelling, capitalisation, or basic writing-form error",
        "cohesion_connective": "cohesion/connective -- a missing, wrong, or misused linking word",
        "article": "article -- wrong, missing, or extra a/an/the",
        "preposition": "preposition -- wrong, missing, or extra preposition",
        "tense_aspect": "tense/aspect -- wrong verb tense or aspect",
        "subject_verb_agreement": "subject-verb agreement -- verb does not agree with its subject",
        "plural_number": "plural/number -- wrong singular/plural form or countability",
        "phrasal_verb": "phrasal verb -- wrong particle or wrong/avoided phrasal-verb form",
        "pronoun_reference": "pronoun reference -- a pronoun that is wrong, ambiguous, or disagrees with its antecedent",
    },
}

# "no error" native option appended to every subtype-choice question, since
# the choice question is only meaningful when has_error fired -- but jev's
# Decisions API answers every question in one request regardless, so a
# native "no error" option must exist for items with none.
NO_ERROR_OPTION = {
    "en": "no error -- the learner text has no translation error here",
    "zh": "无错误——学习者译文在此处没有翻译错误",
    "ja": "誤りなし——学習者文にはここで翻訳の誤りがない",
}


def dimension_of(subtype: str) -> str | None:
    return SUBTYPE_DIMENSION.get(subtype)
