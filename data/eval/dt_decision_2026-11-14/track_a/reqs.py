# -*- coding: utf-8 -*-
"""Track A request builders.

Arm D ("diff-focused"): one call per non-identical sentence pair. State carries the
reference sentence, the learner sentence and an explicit, char/word-level DIFF
(changed fragments wrapped in [[ ]] + a numbered change list) so the model is
pointed at the exact edit instead of having to find it in two full passages.
Questions: strict has-error, learner-only grammaticality, bidirectional meaning
checks (reference->learner, learner->reference), 8 narrow error-family probes,
clearly-wrong / meaning-flip severity probes, a severity choice and the Sept
subtype choice.  variant "en" = English instructions; "l2" = instructions in the
target language (zh/ja), used for the question-language ensemble.
"""
from __future__ import annotations

import lib as L

LANG_NAME = {"zh": "Chinese", "ja": "Japanese", "en": "English"}

FUNC_EX = {
    "zh": "measure word (量词), 的/地/得, aspect marker 了/过/着, 把 or 被 construction, resultative or directional complement",
    "ja": "particle (は/が/を/に/で/も etc.), verb/adjective conjugation, tense/aspect form, counter word",
    "en": "article, preposition, tense/aspect, subject-verb agreement, plural/number, pronoun",
}

# name -> (instructions, true, false)   (English)
NOUL_EN = {
    "err": ("A learner re-translated a passage back into {lang}. Compare `learner_sentence` with `reference_sentence`; the differences are listed in `changes` and wrapped in [[ ]]. Would a strict native-speaker teacher mark at least one of these changes as an error (wrong word, missing or extra word, wrong grammar word, wrong word order, wrong register/politeness, misspelling/wrong character)? A true synonym or an equally correct alternative wording is NOT an error.",
            "At least one change is an error a strict teacher would correct, even a small one.",
            "Every change is an equally correct, natural alternative; nothing to correct."),
    "gram": ("Ignore the reference. Read only `learner_sentence` as a piece of {lang}. Is it ungrammatical, mis-ordered, misspelled, or stylistically inconsistent/unnatural at the [[ ]] positions, such that a native writer would not have written it this way?",
             "The learner sentence contains a grammar, word-order, spelling or style problem at a marked position.",
             "The learner sentence is fully correct, natural {lang} on its own."),
    "fwd": ("Does `reference_sentence` express some meaning, detail or nuance that `learner_sentence` fails to express or expresses differently (information lost or altered)?",
            "Some meaning of the reference is missing from or altered in the learner sentence.",
            "The learner sentence conveys everything the reference says."),
    "bwd": ("Does `learner_sentence` say something that `reference_sentence` does not say (added, repeated, or contradicting information)?",
            "The learner sentence adds, repeats or asserts something not in the reference.",
            "The learner sentence says nothing beyond the reference."),
    "f_order": ("Do the changes amount to a word-order problem: a word, modifier, adverbial, topic or clause placed in a wrong or unnatural position compared with the reference?",
                "Yes, something was moved to a wrong/unnatural position.", "No word-order problem."),
    "f_function": ("Do the changes involve a wrong, missing or superfluous grammar word or grammatical form: {func}?",
                   "Yes, a grammar word/form is wrong, missing or extra.", "No grammar-word/form problem."),
    "f_register": ("Do the changes shift the register, politeness level or style away from the reference (e.g. plain vs polite form, overly formal/bureaucratic or overly casual wording, sentence-final tone)?",
                   "Yes, the register/politeness/tone no longer matches the reference.", "No register problem."),
    "f_lexical": ("Do the changes replace a content word or phrase with a wrong, vaguer, or less fitting word (wrong word choice or unnatural collocation)?",
                  "Yes, a content word/phrase is wrong, vaguer or ill-fitting.", "No word-choice problem."),
    "f_ortho": ("Do the changes introduce a misspelling, a wrong/homophone character, wrong kana/okurigana or another purely written-form error (the intended word is clear)?",
                "Yes, a written-form/spelling error.", "No written-form error."),
    "f_omit": ("Did the learner leave out a word, phrase or clause that carries content in the reference?",
               "Yes, content from the reference is left out.", "Nothing with content is left out."),
    "f_add": ("Did the learner add or duplicate a word, phrase or clause that is not in the reference?",
              "Yes, something was added or repeated.", "Nothing was added."),
    "f_connective": ("Do the changes involve a connective or linking word (and, but, so, then, also ...) that is missing, added or replaced, changing how clauses are linked?",
                     "Yes, a connective is missing, added or wrong.", "No connective problem."),
    "clear_wrong": ("Would a native reader immediately notice the changes in `learner_sentence` as clearly wrong or clearly odd on a first read, regardless of whether the intended meaning is still recoverable?",
                    "Yes, it stands out as wrong or odd on first read.",
                    "No, it is correct, or at most a small slip that is easy to overlook."),
    "flip": ("Because of the changes, would a reader of `learner_sentence` come away with a substantively different or opposite idea than the reference conveys (negation or polarity reversed, quantity or actor/role changed, a key fact lost or replaced)?",
             "Yes, the message is reversed, lost or misleading.",
             "No, the main message is the same."),
}

SEV_EN = ("How severe is the worst error introduced by the changes in `learner_sentence` (if any)?",
          {"none": "No error: the changes are equally correct alternatives.",
           "minor": "A small slip a native reader notices, but the sentence still reads acceptably overall.",
           "major": "Clearly wrong to a native reader: it noticeably impairs the sentence, even though the intended meaning can usually still be recovered.",
           "critical": "The meaning is lost, inverted or actively misleading: a reader would come away with the wrong idea."})

SUBTYPE_EN = "Which error type best describes the main error introduced by the changes in `learner_sentence` compared with `reference_sentence`? Choose no_error if the changes are acceptable."

# ---------------------------------------------------------------- native (zh)
FUNC_L2 = {"zh": "量词、“的／地／得”、体标记“了／过／着”、把字句或被字句、结果补语或趋向补语",
           "ja": "助詞（は・が・を・に・で・も など）、動詞・形容詞の活用、時制・アスペクトの形、助数詞"}
NOUL_L2 = {
    "zh": {
        "err": ("学习者把一段文字回译成中文。请比较 `learner_sentence` 与 `reference_sentence`；差异列在 `changes` 中，并用 [[ ]] 标出。一位严格的母语教师是否会把其中至少一处改动判为错误（用词错误、缺词或多词、语法词错误、语序错误、语体不当、错别字）？真正的同义词或同样正确的说法不算错误。",
                "至少有一处改动是严格的教师会纠正的错误，哪怕很小。", "所有改动都是同样正确、自然的说法，无需纠正。"),
        "gram": ("不看参考译文，只把 `learner_sentence` 当作一句中文来读。在 [[ ]] 标出的位置，它是否不合语法、语序不当、有错别字，或语体不一致、不自然，以至于母语者不会这样写？",
                 "学习者的句子在标出的位置有语法、语序、书写或语体问题。", "学习者的句子本身是完全正确、自然的中文。"),
        "fwd": ("`reference_sentence` 中是否有某个意思、细节或语气，是 `learner_sentence` 没有表达出来或表达得不一样的（信息丢失或改变）？",
                "参考译文的某些意思在学习者的句子中缺失或被改变。", "学习者的句子表达了参考译文的全部意思。"),
        "bwd": ("`learner_sentence` 是否说了 `reference_sentence` 没有说的内容（添加、重复或相矛盾的信息）？",
                "学习者的句子添加、重复或断言了参考译文没有的内容。", "学习者的句子没有超出参考译文的内容。"),
        "f_order": ("这些改动是否构成语序问题：与参考译文相比，某个词、修饰语、状语、话题或分句被放在了错误或不自然的位置？",
                    "是，有成分被移到了错误或不自然的位置。", "没有语序问题。"),
        "f_function": ("这些改动是否涉及语法词或语法形式的误用、缺失或多余：{func}？",
                       "是，有语法词或语法形式错误、缺失或多余。", "没有语法词或语法形式问题。"),
        "f_register": ("这些改动是否使语体、正式程度或语气偏离了参考译文（例如过于书面、官腔，或过于口语、随意）？",
                       "是，语体或语气与参考译文不再一致。", "没有语体问题。"),
        "f_lexical": ("这些改动是否把某个实词或短语换成了错误、更笼统或不贴切的词（用词不当或搭配不自然）？",
                      "是，有实词或短语用错、变笼统或不贴切。", "没有用词问题。"),
        "f_ortho": ("这些改动是否造成了错别字、同音字误用或其他纯书写形式的错误（想表达的词是清楚的）？",
                    "是，有书写或错别字错误。", "没有书写错误。"),
        "f_omit": ("学习者是否漏掉了参考译文中带有实际内容的词、短语或分句？", "是，参考译文的内容被漏掉了。", "没有漏掉带内容的成分。"),
        "f_add": ("学习者是否添加或重复了参考译文中没有的词、短语或分句？", "是，有添加或重复的内容。", "没有添加。"),
        "f_connective": ("这些改动是否涉及连接词（并、但、所以、然后、也等）的缺失、添加或替换，从而改变了分句之间的衔接？",
                         "是，有连接词缺失、多余或用错。", "没有连接词问题。"),
        "clear_wrong": ("母语读者第一眼读到 `learner_sentence` 时，是否会立刻觉得这些改动明显是错的或明显别扭（不论原意是否仍能看懂）？",
                        "是，一读就觉得有错或别扭。", "不会；句子是正确的，或至多是容易忽略的小疏漏。"),
        "flip": ("由于这些改动，`learner_sentence` 的读者得到的意思是否与参考译文实质不同甚至相反（否定或肯定颠倒、数量或施事受事改变、关键信息丢失或被替换）？",
                 "是，意思被颠倒、丢失或会误导读者。", "不是，主要意思相同。"),
    },
    "ja": {
        "err": ("学習者がある文章を日本語に訳し戻しました。`learner_sentence` と `reference_sentence` を比べてください。違いは `changes` に列挙され、[[ ]] で示されています。厳しい母語話者の教師は、これらの変更のうち少なくとも一つを誤り（語の誤り、語の欠落・余分、文法語の誤り、語順の誤り、文体・丁寧さの不一致、誤字）と判定しますか。本当の同義語や同じくらい正しい言い方は誤りではありません。",
                "少なくとも一つの変更は、小さくても厳しい教師が直す誤りである。", "すべての変更は同じくらい正しく自然な言い方で、直す必要はない。"),
        "gram": ("参照訳は無視して、`learner_sentence` だけを日本語の文として読んでください。[[ ]] の位置で、文法的でない、語順がおかしい、誤字がある、または文体が不統一・不自然で、母語話者ならこう書かないという箇所がありますか。",
                 "学習者の文には、示された位置に文法・語順・表記・文体の問題がある。", "学習者の文はそれ自体、完全に正しく自然な日本語である。"),
        "fwd": ("`reference_sentence` が表している意味・詳細・ニュアンスのうち、`learner_sentence` が表していない、または違う形で表しているものがありますか（情報の欠落や変化）。",
                "参照訳の意味の一部が学習者の文で欠けている、または変わっている。", "学習者の文は参照訳の内容をすべて伝えている。"),
        "bwd": ("`learner_sentence` は `reference_sentence` が述べていないこと（追加・繰り返し・矛盾する情報）を述べていますか。",
                "学習者の文は参照訳にないことを追加・反復・主張している。", "学習者の文は参照訳を超える内容を述べていない。"),
        "f_order": ("これらの変更は語順の問題ですか。つまり、参照訳と比べて、語・修飾語・副詞句・主題・節が誤った、または不自然な位置に置かれていますか。",
                    "はい、何かが誤った・不自然な位置に移されている。", "語順の問題はない。"),
        "f_function": ("これらの変更は、文法語や文法形式の誤り・欠落・余分に関わりますか：{func}。",
                       "はい、文法語・文法形式が誤っている、欠けている、または余分である。", "文法語・文法形式の問題はない。"),
        "f_register": ("これらの変更によって、文体・丁寧さ・語調が参照訳からずれていますか（例：です・ます体と普通体の混在、くだけすぎ・硬すぎる表現、文末の語調）。",
                       "はい、文体・丁寧さ・語調が参照訳と一致しなくなっている。", "文体の問題はない。"),
        "f_lexical": ("これらの変更は、内容語や句を、誤った・あいまいな・ふさわしくない語に置き換えていますか（語の選択の誤りや不自然なコロケーション）。",
                      "はい、内容語・句が誤っている、あいまい、または不適切である。", "語の選択の問題はない。"),
        "f_ortho": ("これらの変更は、誤字、漢字の誤り、仮名・送り仮名の誤りなど、純粋に表記上の誤りを生じさせていますか（意図した語は明らか）。",
                    "はい、表記・つづりの誤りがある。", "表記の誤りはない。"),
        "f_omit": ("学習者は、参照訳で内容を担っている語・句・節を抜かしましたか。", "はい、参照訳の内容が抜けている。", "内容のある要素は抜けていない。"),
        "f_add": ("学習者は、参照訳にない語・句・節を追加または重複させましたか。", "はい、何かが追加または繰り返されている。", "追加はない。"),
        "f_connective": ("これらの変更は、接続語（そして、しかし、だから、それから、また など）の欠落・追加・置き換えに関わり、節のつながり方を変えていますか。",
                         "はい、接続語が欠けている、余分、または誤っている。", "接続語の問題はない。"),
        "clear_wrong": ("母語話者の読み手は、`learner_sentence` を最初に読んだとき、これらの変更を明らかな誤り、または明らかに不自然だとすぐに気づきますか（意図した意味がまだ分かるかどうかに関係なく）。",
                        "はい、一読して誤りや違和感が目立つ。", "いいえ。正しいか、せいぜい見落としやすい小さなミスである。"),
        "flip": ("これらの変更のために、`learner_sentence` の読み手は、参照訳が伝える内容と実質的に異なる、または逆の理解をしますか（否定・肯定の逆転、数量や動作主・役割の変化、重要な事実の欠落や置き換え）。",
                 "はい、内容が逆転・欠落している、または誤解を招く。", "いいえ、主な内容は同じである。"),
    },
}
SEV_L2 = {
    "zh": ("`learner_sentence` 中由这些改动造成的最严重的错误（如果有）有多严重？",
           {"none": "没有错误：这些改动是同样正确的说法。",
            "minor": "母语读者能注意到的小疏漏，但句子整体读起来仍可接受。",
            "major": "母语读者一看就觉得明显有错：明显损害了句子，尽管原意通常仍能看懂。",
            "critical": "意思丢失、颠倒或会误导读者：读者会得到错误的理解。"}),
    "ja": ("`learner_sentence` でこれらの変更が生んだ最も重い誤り（あれば）はどの程度ですか。",
           {"none": "誤りなし：変更は同じくらい正しい言い方である。",
            "minor": "母語話者が気づく小さなミスだが、文全体としてはまだ問題なく読める。",
            "major": "母語話者には明らかに誤りで、文を目立って損なっている。ただし意図した意味はたいてい読み取れる。",
            "critical": "意味が失われる、逆になる、または誤解を招く：読み手は誤った理解をする。"}),
}
SUBTYPE_L2 = {"zh": "与 `reference_sentence` 相比，`learner_sentence` 中由这些改动造成的主要错误属于哪一类？如果改动可以接受，请选 no_error。",
              "ja": "`reference_sentence` と比べて、`learner_sentence` でこれらの変更が生んだ主な誤りはどの種類ですか。変更が許容できる場合は no_error を選んでください。"}

NOUL_KEYS = list(NOUL_EN.keys())
FAMILIES = [k for k in NOUL_KEYS if k.startswith("f_")]


def build_state(u: dict) -> dict:
    ref_m, rep_m, changes = L.diff_marks(u["ref"], u["rep"], u["lang"])
    return {"language": LANG_NAME[u["lang"]], "reference_sentence": ref_m, "learner_sentence": rep_m,
            "changes": changes}


def build_D(u: dict, variant: str = "en", only: list[str] | None = None) -> tuple[dict, dict]:
    lang = u["lang"]
    state = build_state(u)
    q = {}
    if variant == "en" or lang == "en":
        table, sev, sub_instr, func = NOUL_EN, SEV_EN, SUBTYPE_EN, FUNC_EX[lang]
    else:
        table, sev, sub_instr, func = NOUL_L2[lang], SEV_L2[lang], SUBTYPE_L2[lang], FUNC_L2[lang]
    for k, (ins, t, f) in table.items():
        q[k] = {"type": "noul", "instructions": ins.format(lang=LANG_NAME[lang], func=func),
                "criteria": {"true": t.format(lang=LANG_NAME[lang]), "false": f.format(lang=LANG_NAME[lang])}}
    q["severity"] = {"type": "choice", "instructions": sev[0], "criteria": dict(sev[1])}
    q["subtype"] = {"type": "choice", "instructions": sub_instr, "criteria": L.REQ._subtype_choice_criteria(lang)}
    if only:
        q = {k: v for k, v in q.items() if k in only}
    return state, q


# ---------------------------------------------------------------- arm D2
# Supplementary questions (sent as a separate small call during the experiment;
# questions are answered independently, so in production they fold into arm D).
D2_EN = {
    "variant_ok": ("Look at the differences listed in `changes`. Are ALL of them merely another equally correct way of writing or saying exactly the same thing in {lang}: a different script for the same word (e.g. kanji vs kana, okurigana variant, simplified/traditional, UK/US spelling), punctuation or spacing, or a true synonym with the same meaning and the same register?",
                   "Yes: every change is only a script/spelling variant, punctuation, or a true same-register synonym. Nothing is wrong.",
                   "No: at least one change alters meaning, grammar, register, word order, or is a misspelling."),
    "teacher_fix": ("Imagine a native-speaker teacher correcting `learner_sentence` against `reference_sentence`. Would the teacher have to rewrite anything at the [[ ]] positions for the sentence to be correct {lang} that means the same as the reference?",
                    "Yes, at least one marked position needs a correction.",
                    "No, the learner sentence can stay exactly as it is."),
    "impair": ("Suppose the changes in `learner_sentence` are mistakes. Are they the kind of mistake that breaks a core grammar pattern, the word order, the politeness/register level, or drops/replaces real content (so the sentence is noticeably impaired), rather than a small surface slip such as a typo, a slightly-off word, a near-synonym, an optional particle or a measure word?",
               "Yes: structural, register-level or content-level damage.",
               "No: only a small surface slip, or no mistake at all."),
}


def build_D2(u: dict, variant: str = "en") -> tuple[dict, dict]:
    lang = u["lang"]
    q = {k: {"type": "noul", "instructions": ins.format(lang=LANG_NAME[lang]), "criteria": {"true": t, "false": f}}
         for k, (ins, t, f) in D2_EN.items()}
    return build_state(u), q


BUILDERS = {"D": build_D, "D2": build_D2}
