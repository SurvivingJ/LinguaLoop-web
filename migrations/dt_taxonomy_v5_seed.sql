-- ============================================================================
-- Dual Translation - taxonomy v5 seed (TASK-626, Phase-2 taxonomy expansion)
-- Cumulative, self-contained: this row is a COMPLETE taxonomy the cascade loads
-- as the single active row. Supersedes v4 (dt_taxonomy_zh_seed.sql) which stays
-- in migrations/ as the historical v4 data row (NOT archived: version rows are
-- cumulative history, v5 is a NEW row and does not redefine v4).
--
-- WHAT'S NEW vs v4 (rubric stays v4 - this is a TAXONOMY-ONLY bump):
--   * Expanded per-L2 subtype sets to tech-spec 5 sizes: EN 15 / JA 17 / ZH 17
--     (shared core 8 + EN +7 + JA +9 + ZH +9). Order IS the _decode_error index
--     contract (grader_cascade._resolve_subtypes -> _enum_lookup).
--   * NEW top-level key `subtype_meta`: per-subtype
--       {dimension: accuracy|fidelity|naturalness, default_severity: minor|major,
--        treatable: bool, cloze_suitable: bool}
--     dimension + default_severity are the derived-scoring inputs TASK-627 reads
--     (see evidence-first-grading.tech.md 4/5); treatable/cloze_suitable feed the
--     Feature-2 exercise chooser. default_severity speaks the POST-TASK-625 triad
--     (minor/major), NOT the retired global/local.
--   * JA `particle` SPLIT (re-adjudication, not rename): particle_wa_ga (は/が
--     discourse) / particle_case (を・に・で・へ) / particle_other (並列・取り立て・
--     終助詞). Every historical JA `particle` gold item is re-adjudicated per
--     instance; live dt_error_instance carries no `particle` rows.
--
-- HISTORICAL ALIASES (so v1-v4 stored dt_error_instance.subtype free-text still
-- resolves under TASK-627 scoring): subtype_meta carries `particle` -> accuracy/
-- major (marked "historical_alias": true). It is deliberately NOT in any pairs
-- list (never shown to the model / never a new-error subtype); it only maps the
-- old name to a dimension. All other v4 subtypes (word_order, word_choice,
-- omission, register, article, preposition, phrasal_verb, tense_aspect,
-- subject_verb_agreement, keigo_register, counter_classifier, script_choice,
-- topic_comment, classifier, aspect_marker, ba_construction,
-- resultative_complement) survive verbatim in v5, so they need no alias.
--
-- NATIVE-REVIEW FLAG: the 15 NEW subtypes' ZH/JA glosses + templates
--   core: addition, collocation, orthography, cohesion_connective
--   EN:   plural_number, pronoun_reference
--   JA:   particle_wa_ga, particle_case, particle_other, verb_conjugation, tense_aspect_ja
--   ZH:   de_particles, bei_passive, directional_complement, adverbial_order
-- are AI-authored FIRST DRAFTS pending native review (same caveat as v1-v4 seeds
-- / ADR-019). The 17 carry-over subtypes reuse v4's reviewed strings verbatim.
--
-- Consumers: grader_cascade.{get_active_taxonomy,_resolve_subtypes,
-- _resolve_subtype_labels,render_explanation,_decode_error}. Shape/totality/alias
-- guarded by tests/test_dual_translation_taxonomy_v5.py.
-- ============================================================================

BEGIN;

-- Single-active-row invariant: deactivate any other active row, then upsert THIS
-- version as the active one (idempotent).
UPDATE public.dt_taxonomy_version SET is_active = false WHERE is_active AND version <> 5;

INSERT INTO public.dt_taxonomy_version (version, is_active, taxonomy, description)
VALUES (
    5,
    true,
    $taxonomy${
  "pairs": {
    "en": {
      "subtypes": [
        "omission",
        "addition",
        "word_choice",
        "collocation",
        "word_order",
        "register",
        "orthography",
        "cohesion_connective",
        "article",
        "preposition",
        "tense_aspect",
        "subject_verb_agreement",
        "plural_number",
        "phrasal_verb",
        "pronoun_reference"
      ]
    },
    "ja-en": {
      "subtypes": [
        "omission",
        "addition",
        "word_choice",
        "collocation",
        "word_order",
        "register",
        "orthography",
        "cohesion_connective",
        "article",
        "preposition",
        "tense_aspect",
        "subject_verb_agreement",
        "plural_number",
        "phrasal_verb",
        "pronoun_reference"
      ]
    },
    "zh-en": {
      "subtypes": [
        "omission",
        "addition",
        "word_choice",
        "collocation",
        "word_order",
        "register",
        "orthography",
        "cohesion_connective",
        "article",
        "preposition",
        "tense_aspect",
        "subject_verb_agreement",
        "plural_number",
        "phrasal_verb",
        "pronoun_reference"
      ]
    },
    "ja": {
      "subtypes": [
        "omission",
        "addition",
        "word_choice",
        "collocation",
        "word_order",
        "register",
        "orthography",
        "cohesion_connective",
        "particle_wa_ga",
        "particle_case",
        "particle_other",
        "verb_conjugation",
        "tense_aspect_ja",
        "keigo_register",
        "counter_classifier",
        "script_choice",
        "topic_comment"
      ]
    },
    "en-ja": {
      "subtypes": [
        "omission",
        "addition",
        "word_choice",
        "collocation",
        "word_order",
        "register",
        "orthography",
        "cohesion_connective",
        "particle_wa_ga",
        "particle_case",
        "particle_other",
        "verb_conjugation",
        "tense_aspect_ja",
        "keigo_register",
        "counter_classifier",
        "script_choice",
        "topic_comment"
      ]
    },
    "zh-ja": {
      "subtypes": [
        "omission",
        "addition",
        "word_choice",
        "collocation",
        "word_order",
        "register",
        "orthography",
        "cohesion_connective",
        "particle_wa_ga",
        "particle_case",
        "particle_other",
        "verb_conjugation",
        "tense_aspect_ja",
        "keigo_register",
        "counter_classifier",
        "script_choice",
        "topic_comment"
      ]
    },
    "zh": {
      "subtypes": [
        "omission",
        "addition",
        "word_choice",
        "collocation",
        "word_order",
        "register",
        "orthography",
        "cohesion_connective",
        "classifier",
        "aspect_marker",
        "de_particles",
        "ba_construction",
        "bei_passive",
        "resultative_complement",
        "directional_complement",
        "adverbial_order",
        "topic_comment"
      ]
    },
    "en-zh": {
      "subtypes": [
        "omission",
        "addition",
        "word_choice",
        "collocation",
        "word_order",
        "register",
        "orthography",
        "cohesion_connective",
        "classifier",
        "aspect_marker",
        "de_particles",
        "ba_construction",
        "bei_passive",
        "resultative_complement",
        "directional_complement",
        "adverbial_order",
        "topic_comment"
      ]
    },
    "ja-zh": {
      "subtypes": [
        "omission",
        "addition",
        "word_choice",
        "collocation",
        "word_order",
        "register",
        "orthography",
        "cohesion_connective",
        "classifier",
        "aspect_marker",
        "de_particles",
        "ba_construction",
        "bei_passive",
        "resultative_complement",
        "directional_complement",
        "adverbial_order",
        "topic_comment"
      ]
    }
  },
  "subtype_meta": {
    "omission": {
      "dimension": "fidelity",
      "default_severity": "major",
      "treatable": false,
      "cloze_suitable": false
    },
    "addition": {
      "dimension": "fidelity",
      "default_severity": "minor",
      "treatable": false,
      "cloze_suitable": false
    },
    "word_choice": {
      "dimension": "fidelity",
      "default_severity": "minor",
      "treatable": false,
      "cloze_suitable": false
    },
    "collocation": {
      "dimension": "naturalness",
      "default_severity": "minor",
      "treatable": false,
      "cloze_suitable": false
    },
    "word_order": {
      "dimension": "accuracy",
      "default_severity": "major",
      "treatable": true,
      "cloze_suitable": false
    },
    "register": {
      "dimension": "fidelity",
      "default_severity": "major",
      "treatable": false,
      "cloze_suitable": false
    },
    "orthography": {
      "dimension": "accuracy",
      "default_severity": "minor",
      "treatable": true,
      "cloze_suitable": false
    },
    "cohesion_connective": {
      "dimension": "naturalness",
      "default_severity": "minor",
      "treatable": true,
      "cloze_suitable": true
    },
    "article": {
      "dimension": "accuracy",
      "default_severity": "minor",
      "treatable": true,
      "cloze_suitable": true
    },
    "preposition": {
      "dimension": "accuracy",
      "default_severity": "minor",
      "treatable": true,
      "cloze_suitable": true
    },
    "tense_aspect": {
      "dimension": "accuracy",
      "default_severity": "major",
      "treatable": true,
      "cloze_suitable": true
    },
    "subject_verb_agreement": {
      "dimension": "accuracy",
      "default_severity": "minor",
      "treatable": true,
      "cloze_suitable": true
    },
    "plural_number": {
      "dimension": "accuracy",
      "default_severity": "minor",
      "treatable": true,
      "cloze_suitable": true
    },
    "phrasal_verb": {
      "dimension": "fidelity",
      "default_severity": "minor",
      "treatable": false,
      "cloze_suitable": true
    },
    "pronoun_reference": {
      "dimension": "accuracy",
      "default_severity": "major",
      "treatable": false,
      "cloze_suitable": false
    },
    "particle_wa_ga": {
      "dimension": "accuracy",
      "default_severity": "major",
      "treatable": true,
      "cloze_suitable": true
    },
    "particle_case": {
      "dimension": "accuracy",
      "default_severity": "major",
      "treatable": true,
      "cloze_suitable": true
    },
    "particle_other": {
      "dimension": "accuracy",
      "default_severity": "minor",
      "treatable": true,
      "cloze_suitable": true
    },
    "verb_conjugation": {
      "dimension": "accuracy",
      "default_severity": "major",
      "treatable": true,
      "cloze_suitable": true
    },
    "tense_aspect_ja": {
      "dimension": "accuracy",
      "default_severity": "major",
      "treatable": true,
      "cloze_suitable": true
    },
    "keigo_register": {
      "dimension": "fidelity",
      "default_severity": "major",
      "treatable": true,
      "cloze_suitable": true
    },
    "counter_classifier": {
      "dimension": "accuracy",
      "default_severity": "minor",
      "treatable": true,
      "cloze_suitable": true
    },
    "script_choice": {
      "dimension": "accuracy",
      "default_severity": "minor",
      "treatable": true,
      "cloze_suitable": false
    },
    "topic_comment": {
      "dimension": "naturalness",
      "default_severity": "minor",
      "treatable": false,
      "cloze_suitable": false
    },
    "classifier": {
      "dimension": "accuracy",
      "default_severity": "minor",
      "treatable": true,
      "cloze_suitable": true
    },
    "aspect_marker": {
      "dimension": "accuracy",
      "default_severity": "major",
      "treatable": true,
      "cloze_suitable": true
    },
    "de_particles": {
      "dimension": "accuracy",
      "default_severity": "minor",
      "treatable": true,
      "cloze_suitable": true
    },
    "ba_construction": {
      "dimension": "accuracy",
      "default_severity": "major",
      "treatable": true,
      "cloze_suitable": false
    },
    "bei_passive": {
      "dimension": "accuracy",
      "default_severity": "major",
      "treatable": true,
      "cloze_suitable": false
    },
    "resultative_complement": {
      "dimension": "accuracy",
      "default_severity": "major",
      "treatable": true,
      "cloze_suitable": true
    },
    "directional_complement": {
      "dimension": "accuracy",
      "default_severity": "minor",
      "treatable": true,
      "cloze_suitable": true
    },
    "adverbial_order": {
      "dimension": "accuracy",
      "default_severity": "major",
      "treatable": true,
      "cloze_suitable": false
    },
    "particle": {
      "dimension": "accuracy",
      "default_severity": "major",
      "treatable": true,
      "cloze_suitable": true,
      "historical_alias": true
    }
  },
  "subtype_glosses": {
    "word_order": {
      "en": "word order — words or phrases arranged in an unnatural or ungrammatical sequence",
      "ja": "語順——語や成分の並び順が不自然、または文法的に誤っている",
      "zh": "语序——词语或成分的排列顺序不自然或不合语法"
    },
    "word_choice": {
      "en": "word choice — a wrong or unnatural lexical choice (right idea, wrong word)",
      "ja": "語彙選択——語の選び方が誤っている、または不自然（意味は近いが語が不適切）",
      "zh": "词语选择——用词错误或不自然（意思接近但用词不当）"
    },
    "omission": {
      "en": "omission — a required word or element is missing",
      "ja": "要素の欠落——必要な語や要素が抜けている",
      "zh": "成分缺失——缺少必要的词或成分"
    },
    "register": {
      "en": "register — wrong level of formality or tone for the context",
      "ja": "文体・語調——場面に対して丁寧さや語調のレベルが合っていない",
      "zh": "语域——正式程度或语气与语境不符"
    },
    "addition": {
      "en": "addition — extra words or information not present in the reference (padding, redundant repetition, or an inserted element)",
      "ja": "余分な追加——参照文にない語や情報を加えている（冗長な繰り返しや不要な挿入など）",
      "zh": "多余添加——加入了参考译文中没有的词或信息（冗余重复或不必要的插入）"
    },
    "collocation": {
      "en": "collocation — the words are individually correct but do not naturally combine (e.g. “make a decision”, not “do a decision”)",
      "ja": "コロケーション——語自体は正しいが、組み合わせが不自然（自然には共起しない語の結び付き）",
      "zh": "词语搭配——单个词都对，但搭配不自然（不符合习惯的固定搭配）"
    },
    "orthography": {
      "en": "orthography — a spelling, capitalisation, or basic writing-form error (the intended word is clear)",
      "ja": "表記・綴り——綴り、送り仮名、記号など表記上の誤り（意図した語は明らか）",
      "zh": "拼写／书写——拼写、大小写或书写形式的错误（想表达的词是清楚的）"
    },
    "cohesion_connective": {
      "en": "cohesion/connective — a missing, wrong, or misused linking word (however, therefore, so, but) that weakens how sentences connect",
      "ja": "結束性・接続表現——接続語（しかし、したがって、だから等）の誤り・欠落により文のつながりが弱い",
      "zh": "衔接／连接词——连接词（然而、因此、所以、但是等）缺失或误用，导致句子衔接不畅"
    },
    "article": {
      "en": "article — wrong, missing, or extra a/an/the; covers definiteness (a vs the) and using no article where one is required (or vice versa) with countable/uncountable nouns"
    },
    "preposition": {
      "en": "preposition — wrong, missing, or extra preposition (in/on/at/to/for/of ...); usually governed by the specific verb, noun, or fixed expression, not by literal translation"
    },
    "phrasal_verb": {
      "en": "phrasal verb — wrong particle or wrong/avoided phrasal-verb form"
    },
    "tense_aspect": {
      "en": "tense/aspect — wrong verb tense or aspect"
    },
    "subject_verb_agreement": {
      "en": "subject-verb agreement — verb does not agree with its subject in number/person"
    },
    "plural_number": {
      "en": "plural/number — wrong singular/plural form or countability (e.g. a missing -s, or a plural on an uncountable noun)"
    },
    "pronoun_reference": {
      "en": "pronoun reference — a pronoun that is wrong, ambiguous, or does not agree with what it refers to (wrong gender/number, or an unclear antecedent)"
    },
    "keigo_register": {
      "ja": "敬語——敬語レベルの誤り。丁寧語（です・ます）、尊敬語（相手の動作を高める）、謙譲語（自分の動作をへりくだる）の使い分けを含む。文法的に正しくても、場面に求められる敬意レベルと異なれば誤りとする"
    },
    "counter_classifier": {
      "ja": "助数詞——数を数える際の助数詞（カウンター）の誤り"
    },
    "script_choice": {
      "ja": "表記の選択——仮名／漢字の使い分けの誤り（同じ語をどの文字種で書くか）"
    },
    "particle_wa_ga": {
      "ja": "助詞「は」／「が」——主題の「は」と主語（新情報）の「が」の使い分けの誤り。従属節・関係節の主語は「が」、既知の主題は「は」など"
    },
    "particle_case": {
      "ja": "格助詞——「を」（対象）、「に」（着点・時・相手）、「で」（場所・手段）、「へ」（方向）など格助詞の誤り"
    },
    "particle_other": {
      "ja": "その他の助詞——並列助詞（や・と・か）、取り立て助詞（も・だけ・しか）、終助詞など、格助詞以外の助詞の誤り"
    },
    "verb_conjugation": {
      "ja": "動詞の活用——て形、可能形、受身、使役などの活用の誤り（ら抜き言葉を含む）"
    },
    "tense_aspect_ja": {
      "ja": "テンス・アスペクト——「た」（完了・過去）と「ている」（進行・結果状態）などの使い分けの誤り"
    },
    "topic_comment": {
      "ja": "主題—解説構造——「は」による主題提示など、主題と解説の組み立て方の誤り",
      "zh": "话题—评论结构——话题/主语—述题结构使用不当（常为母语结构的过度迁移）"
    },
    "classifier": {
      "zh": "量词——量词使用错误或与名词搭配不当。常见错误是一律用“个”代替专用量词（如应为一本书、一件衣服、一只猫），或量词与名词不匹配"
    },
    "aspect_marker": {
      "zh": "体标记——“了／过／着”等体标记使用错误。汉语用体（aspect）而非时态：了表示完成，过表示曾经经历，着表示持续状态；不能按外语的时态直接对应"
    },
    "ba_construction": {
      "zh": "把字句——“把”字结构使用错误或缺失"
    },
    "resultative_complement": {
      "zh": "结果补语——结果补语使用错误或缺失"
    },
    "de_particles": {
      "zh": "结构助词“的／得／地”——三个 de 的误用：定语用“的”、状语用“地”、补语用“得”"
    },
    "bei_passive": {
      "zh": "被字句——“被”字被动结构使用错误或缺失（受事、施事、动词的语序与标记）"
    },
    "directional_complement": {
      "zh": "趋向补语——“来／去／上／下／进／出”等趋向补语使用错误或缺失，表示动作的方向"
    },
    "adverbial_order": {
      "zh": "状语语序——时间、地点、方式等状语的位置错误（汉语状语一般在动词之前，语序较固定）"
    }
  },
  "templates": {
    "word_order": {
      "en": "You wrote “{learner_form}”, but the natural order here is “{corrected_form}”. The target language orders these elements differently from a word-for-word rendering.",
      "ja": "「{learner_form}」と書いていますが、ここでは「{corrected_form}」の語順が自然です。目標言語ではこれらの成分の並び方が逐語訳とは異なります。",
      "zh": "你写的是“{learner_form}”，但这里自然的语序是“{corrected_form}”。目标语言中这些成分的排列与逐字翻译不同。"
    },
    "word_choice": {
      "en": "“{learner_form}” isn’t the right word here — the reference uses “{corrected_form}”. The meaning is close, but this isn’t how it’s normally expressed.",
      "ja": "「{learner_form}」は適切な語ではありません。参照文では「{corrected_form}」を使います。意味は近いですが、通常はこう表現します。",
      "zh": "“{learner_form}”用词不当——参考译文用的是“{corrected_form}”。意思接近，但通常不这样表达。"
    },
    "omission": {
      "en": "Something required is missing: you wrote “{learner_form}” where the reference has “{corrected_form}”.",
      "ja": "必要な要素が抜けています。「{learner_form}」と書いていますが、参照文では「{corrected_form}」です。",
      "zh": "缺少了必要成分：你写的是“{learner_form}”，而参考译文是“{corrected_form}”。"
    },
    "register": {
      "en": "“{learner_form}” is at the wrong level of formality. “{corrected_form}” matches the register (tone/politeness) of the original.",
      "ja": "「{learner_form}」は丁寧さ・語調のレベルが合っていません。「{corrected_form}」が原文の文体（語調・丁寧さ）に合います。",
      "zh": "“{learner_form}”的正式程度不合适。“{corrected_form}”更符合原文的语域（语气／礼貌程度）。"
    },
    "addition": {
      "en": "Extra material: you added “{learner_form}”, which the reference does not include. Keep only what the original says — don’t pad or repeat.",
      "ja": "余分な追加：「{learner_form}」を加えていますが、参照文にはありません。原文にある内容だけにとどめ、冗長な追加はしないでください。",
      "zh": "多余添加：你加入了“{learner_form}”，但参考译文中并没有。只保留原文的内容，不要添加或重复。"
    },
    "collocation": {
      "en": "Collocation: “{learner_form}” isn’t how these words naturally combine — use “{corrected_form}”. Each word is fine alone, but the pairing sounds unnatural to a native speaker.",
      "ja": "コロケーションの誤り：「{learner_form}」は語の組み合わせが不自然です。「{corrected_form}」を使ってください。語単体は正しくても、この組み合わせは母語話者には不自然に響きます。",
      "zh": "搭配错误：“{learner_form}”的词语搭配不自然，应为“{corrected_form}”。单个词没问题，但这样搭配在母语者听来不地道。"
    },
    "orthography": {
      "en": "Spelling/writing error: “{learner_form}” should be “{corrected_form}”. The word is right, but it’s written incorrectly.",
      "ja": "表記の誤り：「{learner_form}」は「{corrected_form}」と書きます。語は正しいものの、綴り・表記が誤っています。",
      "zh": "拼写／书写错误：“{learner_form}”应写作“{corrected_form}”。词是对的，但书写形式有误。"
    },
    "cohesion_connective": {
      "en": "Connective error: “{learner_form}” should be “{corrected_form}”. The linking word signals how this idea relates to the previous one — the wrong one breaks the flow.",
      "ja": "接続表現の誤り：「{learner_form}」は「{corrected_form}」とすべきです。接続語は前の内容との関係を示すため、誤ると文のつながりが崩れます。",
      "zh": "连接词错误：“{learner_form}”应为“{corrected_form}”。连接词表明这一句与上一句的关系，用错会打断行文的连贯。"
    },
    "article": {
      "en": "Article error: you wrote “{learner_form}”, but it should be “{corrected_form}”. English marks nouns for definiteness — use “the” for something specific or already known, “a/an” for one non-specific countable thing, and no article for general plurals or uncountables.",
      "ja": "冠詞の誤り：「{learner_form}」は「{corrected_form}」とすべきです。英語は名詞の「特定・不特定」を冠詞で示します——特定・既知は「the」、不特定で数えられる単数は「a/an」、総称の複数や不可算名詞は無冠詞です。",
      "zh": "冠词错误：你写的是“{learner_form}”，应为“{corrected_form}”。英语名词要区分“定/不定”——特指或已知用“the”，泛指的单数可数名词用“a/an”，泛指复数或不可数名词则不用冠词。"
    },
    "preposition": {
      "en": "Preposition error: “{learner_form}” should be “{corrected_form}”. The preposition here is fixed by the verb, noun, or set phrase (e.g. depend on, interested in, arrive at) — it isn’t chosen by literal translation.",
      "ja": "前置詞の誤り：「{learner_form}」は「{corrected_form}」とすべきです。ここでの前置詞は動詞・名詞・定型表現によって決まり（例：depend on、interested in、arrive at）、逐語訳では選べません。",
      "zh": "介词错误：“{learner_form}”应为“{corrected_form}”。这里的介词由动词、名词或固定搭配决定（如 depend on、interested in、arrive at），不能按字面直译选择。"
    },
    "phrasal_verb": {
      "en": "Phrasal-verb error: “{learner_form}” should be “{corrected_form}”. The particle (up/out/in …) changes the meaning, so it isn’t interchangeable.",
      "ja": "句動詞の誤り：「{learner_form}」は「{corrected_form}」とすべきです。不変化詞（up/out/in など）で意味が変わるため、入れ替えはできません。",
      "zh": "短语动词错误：“{learner_form}”应为“{corrected_form}”。小品词（up/out/in 等）会改变词义，不能随意替换。"
    },
    "tense_aspect": {
      "en": "Tense/aspect error: you wrote “{learner_form}”, but “{corrected_form}” is needed to express the correct time or aspect of the action.",
      "ja": "時制・相の誤り：「{learner_form}」と書いていますが、動作の時間や状態を正しく表すには「{corrected_form}」が必要です。",
      "zh": "时态／体错误：你写的是“{learner_form}”，需要用“{corrected_form}”来表达正确的时间或动作状态。"
    },
    "subject_verb_agreement": {
      "en": "Agreement error: “{learner_form}” doesn’t agree with its subject. Use “{corrected_form}” to match the subject in number and person.",
      "ja": "主語と動詞の一致の誤り：「{learner_form}」は主語と一致していません。数・人称を主語に合わせて「{corrected_form}」を使ってください。",
      "zh": "主谓一致错误：“{learner_form}”与主语不一致。应使用“{corrected_form}”，在数和人称上与主语保持一致。"
    },
    "plural_number": {
      "en": "Number error: “{learner_form}” should be “{corrected_form}”. Check whether the noun is singular or plural here — English marks countable nouns for number.",
      "ja": "数の誤り：「{learner_form}」は「{corrected_form}」とすべきです。ここで名詞が単数か複数かを確認してください。英語は数えられる名詞の単複を形で示します。",
      "zh": "单复数错误：“{learner_form}”应为“{corrected_form}”。请判断该名词在这里是单数还是复数——英语中可数名词要按数变化。"
    },
    "pronoun_reference": {
      "en": "Pronoun error: “{learner_form}” should be “{corrected_form}”. The pronoun must clearly and correctly point back to what it refers to (right gender, number, and antecedent).",
      "ja": "代名詞の誤り：「{learner_form}」は「{corrected_form}」とすべきです。代名詞は、指し示す対象（性・数・先行詞）に正しく一致し、明確に対応していなければなりません。",
      "zh": "代词指代错误：“{learner_form}”应为“{corrected_form}”。代词必须在性、数上与所指对象一致，并清楚地指回它所指代的内容。"
    },
    "keigo_register": {
      "en": "Politeness (keigo) error: “{learner_form}” is at the wrong honorific level; the reference uses “{corrected_form}”. Japanese distinguishes teineigo (です/ます polite), sonkeigo (exalting the other person’s actions), and kenjougo (humbling your own). Even a grammatically perfect sentence at the wrong keigo level is an error.",
      "ja": "敬語の誤り：「{learner_form}」は敬語レベルが誤っています。参照文では「{corrected_form}」を用います。日本語は丁寧語（です・ます）、尊敬語（相手の動作を高める）、謙譲語（自分の動作をへりくだる）を区別します。文法的に正しくても、敬意レベルが誤れば誤りです。",
      "zh": "敬语错误：“{learner_form}”的敬语层级不对，参考译文用的是“{corrected_form}”。日语区分丁宁语（です／ます）、尊敬语（抬高对方的动作）和自谦语（谦卑自己的动作）。即使句子语法正确，敬语层级用错也算错误。"
    },
    "counter_classifier": {
      "en": "Counter error: “{learner_form}” is the wrong counter. Use “{corrected_form}”, the counter that goes with this kind of noun.",
      "ja": "助数詞の誤り：「{learner_form}」は助数詞が誤っています。この種類の名詞に合う助数詞「{corrected_form}」を使ってください。",
      "zh": "助数词错误：“{learner_form}”用错了助数词。应使用“{corrected_form}”，它才是与这类名词搭配的助数词。"
    },
    "script_choice": {
      "en": "Script error: “{learner_form}” should be written as “{corrected_form}” (the expected kana/kanji choice here).",
      "ja": "表記の誤り：「{learner_form}」は「{corrected_form}」と書くべきです（ここで期待される仮名／漢字の使い分け）。",
      "zh": "书写（假名／汉字）错误：“{learner_form}”应写作“{corrected_form}”。"
    },
    "particle_wa_ga": {
      "en": "は/が error: you used “{learner_form}”, but “{corrected_form}” is needed. は marks a known topic; が marks the subject as new information (and is required for the subject inside a relative or subordinate clause) — the choice changes what the sentence emphasises.",
      "ja": "「は」「が」の誤り：「{learner_form}」ではなく「{corrected_form}」が必要です。「は」は既知の主題を、「が」は新情報の主語を示し、関係節・従属節の主語には「が」を用います。選択によって文の焦点が変わります。",
      "zh": "は／が 错误：你用的是“{learner_form}”，应为“{corrected_form}”。「は」提示已知主题，「が」标记作为新信息的主语（关系从句／从属句的主语必须用「が」）——用错会改变句子的强调重点。"
    },
    "particle_case": {
      "en": "Case-particle error: you used “{learner_form}”, but “{corrected_form}” is required. Particles を (object), に (goal/time), で (location/means), へ (direction) assign grammatical roles — the wrong one changes who does what to what.",
      "ja": "格助詞の誤り：「{learner_form}」ではなく「{corrected_form}」が必要です。を＝対象、に＝着点・時、で＝場所・手段、へ＝方向、のように格助詞は文法的役割を決めるため、誤ると意味関係が変わります。",
      "zh": "格助词错误：你用的是“{learner_form}”，应为“{corrected_form}”。を（对象）、に（到达点／时间）、で（地点／手段）、へ（方向）等格助词决定语法关系——用错会改变“谁对什么做了什么”。"
    },
    "particle_other": {
      "en": "Particle error: “{learner_form}” should be “{corrected_form}”. This is a linking or focus particle (や/と listing, も/だけ/しか focus, or a sentence-final particle) — the wrong one shifts the nuance.",
      "ja": "助詞の誤り：「{learner_form}」は「{corrected_form}」とすべきです。並列助詞（や・と）、取り立て助詞（も・だけ・しか）、終助詞などで、誤るとニュアンスが変わります。",
      "zh": "助词错误：“{learner_form}”应为“{corrected_form}”。这是并列助词（や／と）、提示助词（も／だけ／しか）或语气助词——用错会改变语气或细微含义。"
    },
    "verb_conjugation": {
      "en": "Conjugation error: “{learner_form}” should be “{corrected_form}”. The verb form (て-form, potential, passive, or causative) is built by a rule — check the conjugation, not just the dictionary word.",
      "ja": "活用の誤り：「{learner_form}」は「{corrected_form}」とすべきです。て形・可能・受身・使役などの活用は規則で作られます。辞書形ではなく活用の作り方を確認してください。",
      "zh": "动词活用错误：“{learner_form}”应为“{corrected_form}”。日语动词的て形、可能态、被动、使役等都按规则变化，要检查活用形式，而不只是词典形。"
    },
    "tense_aspect_ja": {
      "en": "Tense/aspect error: “{learner_form}” should be “{corrected_form}”. Japanese た marks completion/past and ている marks ongoing action or a resulting state — they aren’t interchangeable here.",
      "ja": "テンス・アスペクトの誤り：「{learner_form}」は「{corrected_form}」とすべきです。「た」は完了・過去を、「ている」は進行や結果状態を表し、ここでは置き換えられません。",
      "zh": "时体错误：“{learner_form}”应为“{corrected_form}”。日语「た」表示完成／过去，「ている」表示进行或结果状态，两者在此不能互换。"
    },
    "topic_comment": {
      "en": "Topic–comment error: you structured this as “{learner_form}”, but “{corrected_form}” presents the topic and comment the way the target language does.",
      "ja": "主題—解説構造の誤り：「{learner_form}」と組み立てていますが、「{corrected_form}」が目標言語に沿った主題と解説の示し方です。",
      "zh": "主题—评论结构错误：你写成了“{learner_form}”，而“{corrected_form}”按目标语言的方式来呈现主题与评论。"
    },
    "classifier": {
      "en": "Classifier error: “{learner_form}” uses the wrong measure word. Use “{corrected_form}” — the classifier that matches this noun (e.g. 本 for books, 件 for clothing, 只 for small animals). Don’t default everything to 个; Chinese pairs a specific classifier with each noun.",
      "ja": "量詞の誤り：「{learner_form}」は量詞が誤っています。この名詞に合う量詞「{corrected_form}」を使ってください（例：本＝本/冊、服＝件、小動物＝只）。なんでも「个」で済まず、中国語は名詞ごとに専用の量詞を用います。",
      "zh": "量词错误：“{learner_form}”用错了量词。应使用与该名词搭配的“{corrected_form}”（如书用“本”、衣服用“件”、小动物用“只”）。不要一律用“个”，汉语中每类名词都有其专用量词。"
    },
    "aspect_marker": {
      "en": "Aspect error: “{learner_form}” should be “{corrected_form}”. Chinese marks aspect, not tense: 了 = completed action, 过 = past experience (“have ever”), 着 = ongoing/durative state. Choose the marker by how the action unfolds, not by English tense.",
      "ja": "アスペクトの誤り：「{learner_form}」は「{corrected_form}」とすべきです。中国語は時制ではなくアスペクトを標示します：了＝完了、过＝経験（〜したことがある）、着＝持続・進行中の状態。英語などの時制ではなく、動作の様態で標識を選びます。",
      "zh": "体标记错误：“{learner_form}”应为“{corrected_form}”。汉语标示的是体而非时态：了表示动作完成，过表示曾经的经历，着表示持续／进行的状态。应按动作的展开方式选择，而不是按外语的时态对应。"
    },
    "ba_construction": {
      "en": "把-construction error: “{learner_form}” should be “{corrected_form}”. This sentence needs the 把 structure to show what happens to the object.",
      "ja": "「把」構文の誤り：「{learner_form}」は「{corrected_form}」とすべきです。この文では目的語に何が起きるかを示すために「把」構文が必要です。",
      "zh": "把字句错误：“{learner_form}”应为“{corrected_form}”。此句需要用“把”字结构来说明对宾语做了什么。"
    },
    "resultative_complement": {
      "en": "Resultative-complement error: “{learner_form}” should be “{corrected_form}”. The result of the action must be attached to the verb as a complement.",
      "ja": "結果補語の誤り：「{learner_form}」は「{corrected_form}」とすべきです。動作の結果は補語として動詞に付ける必要があります。",
      "zh": "结果补语错误：“{learner_form}”应为“{corrected_form}”。动作的结果应作为补语附在动词之后。"
    },
    "de_particles": {
      "en": "的/得/地 error: “{learner_form}” should be “{corrected_form}”. The three de have distinct jobs — 的 links a modifier to a noun, 地 marks an adverbial before a verb, 得 introduces a complement after a verb.",
      "ja": "「的／得／地」の誤り：「{learner_form}」は「{corrected_form}」とすべきです。三つの de は役割が異なります——的＝連体（名詞修飾）、地＝連用（動詞前の修飾）、得＝補語（動詞の後）。",
      "zh": "“的／得／地”错误：“{learner_form}”应为“{corrected_form}”。三个 de 分工不同：“的”接定语修饰名词，“地”作状语修饰动词，“得”引出动词后的补语。"
    },
    "bei_passive": {
      "en": "被-passive error: “{learner_form}” should be “{corrected_form}”. When the subject undergoes the action, Chinese marks it with 被 (被 + doer + verb) — this sentence needs or misuses that passive structure.",
      "ja": "「被」受身の誤り：「{learner_form}」は「{corrected_form}」とすべきです。主語が動作を受ける場合、中国語は「被」（被＋動作主＋動詞）で受身を示します。この文はその構文が必要・または誤用です。",
      "zh": "被字句错误：“{learner_form}”应为“{corrected_form}”。当主语是动作的承受者时，汉语用“被”（被＋施事＋动词）表示被动——此句需要或误用了该被动结构。"
    },
    "directional_complement": {
      "en": "Directional-complement error: “{learner_form}” should be “{corrected_form}”. Verbs take a directional complement (来/去/上/下/进/出…) to show which way the action moves relative to the speaker.",
      "ja": "方向補語の誤り：「{learner_form}」は「{corrected_form}」とすべきです。動詞は趨向補語（来／去／上／下／进／出など）を伴い、話し手を基準に動作の方向を示します。",
      "zh": "趋向补语错误：“{learner_form}”应为“{corrected_form}”。动词要用趋向补语（来／去／上／下／进／出等）表示动作相对于说话人的方向。"
    },
    "adverbial_order": {
      "en": "Adverbial-order error: “{learner_form}” should be “{corrected_form}”. Chinese fixes the order of adverbials (time, place, manner) before the verb — they can’t float to the end as in English.",
      "ja": "状語の語順の誤り：「{learner_form}」は「{corrected_form}」とすべきです。中国語では状語（時間・場所・方法）は動詞の前に置き、語順が比較的固定しています。英語のように文末へ移せません。",
      "zh": "状语语序错误：“{learner_form}”应为“{corrected_form}”。汉语的状语（时间、地点、方式）一般固定在动词之前，不能像英语那样放到句末。"
    },
    "particle": {
      "en": "Particle error: you used “{learner_form}”, but “{corrected_form}” is required here. Japanese particles mark grammatical role: は presents a known topic, が marks a new-information subject, を marks the direct object, and に/で mark destination/location — so the wrong particle changes how the sentence is read.",
      "ja": "助詞の誤り：「{learner_form}」ではなく、ここでは「{corrected_form}」が必要です。は＝既知の主題、が＝新情報の主語、を＝目的語、に／で＝着点・場所、のように助詞は文法的役割を示すため、誤ると文の解釈が変わります。",
      "zh": "助词错误：你用的是“{learner_form}”，这里需要用“{corrected_form}”。日语助词标示语法关系：は提示“已知主题”，が标记“新信息的主语”，を标记宾语，に／で标记方向／地点——用错助词会改变句子的意思。"
    }
  }
}$taxonomy$::jsonb,
    'TASK-626 dual-translation taxonomy v5 - Phase-2 expansion. Per-L2 subtype sets grown to spec sizes (EN 15 / JA 17 / ZH 17: shared core 8 + per-target). Adds top-level subtype_meta (dimension/default_severity/treatable/cloze_suitable) that TASK-627 derived scoring reads; default_severity speaks the minor/major triad. JA particle split into particle_wa_ga / particle_case / particle_other (re-adjudication). Historical alias `particle` -> accuracy kept in subtype_meta so v1-v4 rows still resolve (not in any pairs list). 15 new subtypes ZH/JA glosses+templates AI-drafted, pending native review; 17 carry-overs reuse v4 strings. Rubric stays v4 (taxonomy-only bump). Supersedes v4 (single active row).'
)
ON CONFLICT (version) DO UPDATE
    SET taxonomy = EXCLUDED.taxonomy,
        description = EXCLUDED.description,
        is_active = true;

COMMIT;

-- ============================================================================
-- Verification (run manually after applying):
--   SELECT count(*) FROM public.dt_taxonomy_version WHERE is_active;   -- expect 1
--   SELECT version FROM public.dt_taxonomy_version WHERE is_active;    -- expect 5
--   SELECT jsonb_object_keys(taxonomy) FROM public.dt_taxonomy_version WHERE is_active;
--       -- expect: pairs, subtype_meta, subtype_glosses, templates
-- ============================================================================
