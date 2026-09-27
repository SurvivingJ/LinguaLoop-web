# -*- coding: utf-8 -*-
"""Per-language noul-question rubrics. HARD RULE: for zh/ja the instructions
and criteria text are entirely in the target language (JSON keys stay ASCII).
An English-language mirror of the zh/ja rubrics is provided for the
English-prompt control arm (same questions, same state field names, English
wording, run against a subset of zh/ja items)."""

# state key holding the sentence under judgment: "sentence"
# Two questions per item: grammatical + natural (covers the controlled set's
# grammar/naturalness axes). A third question, sense-correctness, is only
# asked when a target word is supplied (not used for the controlled set,
# since defects there are whole-sentence, but wired for reuse).

RUBRIC_NATIVE = {
    "zh": {
        "grammatical": {
            "type": "noul",
            "instructions": "sentence字段中的句子在语法上是否正确？",
            "criteria": {
                "true": "句子符合汉语语法规则，没有语序、虚词、量词、体标记等错误。",
                "false": "句子存在语序颠倒、虚词误用、量词错误、体标记（了/着/过）冲突等语法问题。",
            },
        },
        "natural": {
            "type": "noul",
            "instructions": "sentence字段中的句子是否语义自然、内容合理？",
            "criteria": {
                "true": "句子内容符合常理，母语者会觉得这是一句正常、连贯的话。",
                "false": "句子内容荒谬、不合逻辑，或用词的意思在这个语境下明显不对。",
            },
        },
    },
    "en": {
        "grammatical": {
            "type": "noul",
            "instructions": "Is the sentence in the `sentence` field grammatically correct English?",
            "criteria": {
                "true": "The sentence follows standard English grammar: correct word order, verb forms, prepositions, and agreement.",
                "false": "The sentence has a grammar error: broken word order, wrong verb form/tense, wrong preposition, or agreement error.",
            },
        },
        "natural": {
            "type": "noul",
            "instructions": "Is the sentence in the `sentence` field semantically natural and sensible?",
            "criteria": {
                "true": "The content makes sense; a native speaker would find it a normal, coherent statement.",
                "false": "The content is nonsensical, absurd, or a word is used with the wrong meaning for this context.",
            },
        },
    },
    "ja": {
        "grammatical": {
            "type": "noul",
            "instructions": "sentenceフィールドの文は文法的に正しいですか？",
            "criteria": {
                "true": "助詞の使い方、語順、活用形などに誤りがなく、自然な日本語の文法に従っている。",
                "false": "助詞の誤用、語順の乱れ、活用形の誤り（例:た形とる形の混同）などの文法的な問題がある。",
            },
        },
        "natural": {
            "type": "noul",
            "instructions": "sentenceフィールドの文は意味的に自然で理にかなっていますか？",
            "criteria": {
                "true": "内容が常識に合っていて、母語話者が読んで違和感のない、筋の通った文だと感じる。",
                "false": "内容が不合理・支離滅裂であるか、この文脈で言葉の意味が明らかに合っていない。",
            },
        },
    },
}

# --- Entailment gold-set question: does the passage support this candidate
# answer? state = {"passage":..., "question":..., "candidate":...}
RUBRIC_ENTAILMENT = {
    "zh": {
        "entailed": {
            "type": "noul",
            "instructions": "根据passage字段中的文章内容，candidate字段里的答案是否准确回答了question字段提出的问题？",
            "criteria": {
                "true": "文章明确陈述了该答案，或者该答案是文章内容唯一可以推出的结论。",
                "false": "文章没有支持该答案，该答案只是话题相关但未被文章证实，或者与文章内容矛盾。",
            },
        },
    },
    "en": {
        "entailed": {
            "type": "noul",
            "instructions": "Based on the article in the `passage` field, does the answer in the `candidate` field correctly answer the question in the `question` field?",
            "criteria": {
                "true": "The passage explicitly states this answer, or it is the uniquely inferable conclusion from the passage.",
                "false": "The passage does not support this answer -- it is merely on the same topic, unsupported, or contradicted by the passage.",
            },
        },
    },
    "ja": {
        "entailed": {
            "type": "noul",
            "instructions": "passageフィールドの文章の内容に基づくと、candidateフィールドの答えはquestionフィールドの質問に正しく答えていますか？",
            "criteria": {
                "true": "文章がその答えを明確に述べているか、文章の内容から一意に推論できる結論である。",
                "false": "文章はその答えを裏付けていない。話題は関連しているだけで文章に根拠がないか、文章の内容と矛盾している。",
            },
        },
    },
}

# --- Distractor-plausibility two-axis mirror of the live v7 judge
# (services/test_generation/schemas.py: fit<=2 reject/==3 flag/>=4 accept;
# confusability>=5 reject/==3 flag/<=1 flag/else accept). state =
# {"passage":..., "question":..., "answer":..., "distractor":...}
RUBRIC_DISTRACTOR = {
    "zh": {
        "fit": {
            "type": "score",
            "instructions": "distractor字段里的干扰项在多大程度上属于passage文章所在的学科／领域？",
            "criteria": [
                "完全不属于文章讨论的学科或领域，来自完全不相关的领域。",
                "与文章的学科有一定距离，联系很勉强。",
                "介于相关和不相关之间，难以判断。",
                "与文章讨论的学科相关，但不是文章直接提到的具体内容。",
                "明确属于文章讨论的学科／领域，是文章直接提到或紧密相关的内容。",
            ],
        },
        "confusability": {
            "type": "score",
            "instructions": "只读懂了一半文章的学习者，会不会把distractor字段里的干扰项误选为question字段问题的正确答案？",
            "criteria": [
                "完全没有迷惑性，没有人会选这个选项。",
                "迷惑性很低。",
                "有一定迷惑性，读者可能会犹豫。",
                "迷惑性较高，容易被选中。",
                "迷惑性极高，读起来就像是另一个正确答案（也可能确实是对的）。",
            ],
        },
    },
    "en": {
        "fit": {
            "type": "score",
            "instructions": "How much does the distractor in the `distractor` field belong to the subject/domain of the article in `passage`?",
            "criteria": [
                "Does not belong to the passage's subject at all; from a completely unrelated domain.",
                "Some distance from the passage's subject; the connection is a stretch.",
                "Ambiguous, hard to call related or unrelated.",
                "Related to the passage's subject, but not something the passage directly mentions.",
                "Clearly belongs to the passage's subject/domain -- something the passage directly mentions or closely implies.",
            ],
        },
        "confusability": {
            "type": "score",
            "instructions": "Would a learner who only understood half of the article in `passage` mistakenly pick the distractor in `distractor` as the correct answer to `question`?",
            "criteria": [
                "Not confusable at all; nobody would pick this.",
                "Low confusability.",
                "Somewhat confusable; a reader might hesitate.",
                "Highly confusable; easily mistaken for correct.",
                "Extremely confusable -- reads like another correct answer (and may in fact also be correct).",
            ],
        },
    },
    "ja": {
        "fit": {
            "type": "score",
            "instructions": "distractorフィールドの選択肢は、passageフィールドの文章が扱う分野・テーマにどの程度属していますか？",
            "criteria": [
                "文章の分野に全く属していない。完全に無関係な分野から来ている。",
                "文章の分野からやや距離があり、つながりが無理やりに感じられる。",
                "関連しているかどうか判断が難しい。",
                "文章の分野には関連しているが、文章が直接述べている内容ではない。",
                "文章が扱う分野・テーマに明確に属している。文章が直接述べているか、密接に関連する内容である。",
            ],
        },
        "confusability": {
            "type": "score",
            "instructions": "文章を半分程度しか理解していない学習者は、distractorフィールドの選択肢をquestionフィールドの質問の正解だと誤って選んでしまいますか？",
            "criteria": [
                "全く紛らわしくない。誰もこの選択肢を選ばない。",
                "紛らわしさは低い。",
                "ある程度紛らわしく、読者が迷う可能性がある。",
                "かなり紛らわしく、正解だと誤解されやすい。",
                "非常に紛らわしく、まるでもう一つの正解のように読める（実際に正しい可能性もある）。",
            ],
        },
    },
}

# English-prompt control mirror for zh/ja: SAME questions, English wording,
# but state still holds the original zh/ja sentence text.
RUBRIC_ENGLISH_CONTROL = {
    "zh": {
        "grammatical": {
            "type": "noul",
            "instructions": "Is the Chinese sentence in the `sentence` field grammatically correct?",
            "criteria": {
                "true": "The sentence follows standard Mandarin grammar: correct word order, function words, measure words, and aspect markers (了/着/过).",
                "false": "The sentence has a grammar error: broken word order, wrong function word, wrong measure word, or a clashing aspect marker.",
            },
        },
        "natural": {
            "type": "noul",
            "instructions": "Is the Chinese sentence in the `sentence` field semantically natural and sensible?",
            "criteria": {
                "true": "The content makes sense; a native Mandarin speaker would find it a normal, coherent statement.",
                "false": "The content is nonsensical or absurd, or a word is used with the wrong meaning for this context.",
            },
        },
    },
    "ja": {
        "grammatical": {
            "type": "noul",
            "instructions": "Is the Japanese sentence in the `sentence` field grammatically correct?",
            "criteria": {
                "true": "Particle usage, word order, and verb/adjective conjugation all follow natural Japanese grammar.",
                "false": "There is a grammar problem: wrong particle, scrambled word order, or a wrong conjugated form (e.g. confusing past/non-past).",
            },
        },
        "natural": {
            "type": "noul",
            "instructions": "Is the Japanese sentence in the `sentence` field semantically natural and sensible?",
            "criteria": {
                "true": "The content makes sense; a native Japanese speaker would find it a normal, coherent sentence.",
                "false": "The content is nonsensical or incoherent, or a word's meaning is clearly wrong for this context.",
            },
        },
    },
}
