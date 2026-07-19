-- ============================================================================
-- Dual Translation - rubric v6 seed (TASK-629): band descriptors v3 rewrite.
-- DESCRIPTORS ONLY. Replaces band_descriptors with the tech spec §8 pattern:
--   observable reader behaviour + a parenthetical error profile matched to
--   band_thresholds; no frequency adverbs; distinct content per band. Retires
--   the old "(content level: ...)" suffix carried since v1.
--
-- Voice split (ADR-018 + evidence-first §8):
--   * accuracy / fidelity / understandability - LEARNER-FACING (Python-derived
--     by services/dual_translation/scoring.py; shown in the feed-up panel +
--     result, never sent to a model). TIER-INVARIANT: the band is a pure penalty
--     function of the severity-weighted errors, identical at every age tier.
--   * range        - MODEL-FACING (enters the Verifier prompt via
--     prompts.JUDGE_DIMENSIONS). TIER-INVARIANT: judged relative to the
--     reference, whose range is already at the learner's level.
--   * naturalness  - MODEL-FACING and TIER-VARYING (the single level-dependent
--     dimension per ADR-018). ABSENT at tiers 1-2 (hidden to avoid demotivation;
--     the raw config omits it there, matching v1-v5 and the seed tests).
--
-- Error-profile parentheticals are consistent with band_thresholds (v5, carried
-- forward here unchanged): accuracy/fidelity severity 1/5/25, thresholds 1/6/15
-- (b4 <=1 minor; b3 one major or a few minors; b2 two-three majors; b1 worse or
-- a critical); understandability severity 0/2/25, thresholds 2/6/25 (minors do
-- not register; one critical -> b2; two criticals -> b1).
--
-- LANGUAGES: EN reviewed and approved by the user (2026-07-18). ZH + JA are
-- AI-DRAFTED and *** FLAGGED FOR NATIVE REVIEW *** (ADR-019 pattern, as with the
-- taxonomy v5 / rubric v4 strings): confirm idiom, register anchors per age tier,
-- and that no band pair separates on a frequency adverb before treating them as
-- final.
--
-- CARRIED FORWARD FROM v5, UNCHANGED (this is a descriptors-only bump): weights,
-- acceptable_variation, exemplars, severity_weights, understandability_weights,
-- band_thresholds. Held equal to v5 BY TEST (test_dual_translation_rubric_v6.py).
-- The three scoring keys stay pinned to the gold-seed offline fallback
-- (tests/test_dual_translation_gold_seed_helper.py globs every dt_rubric_v*_seed
-- and re-checks them) - band descriptors do not enter derived scoring, so the
-- frozen fixtures are untouched.
--
-- SELF-CONTAINED (TASK-636 / ADR-020): a COMPLETE config via VALUES, never
-- `src.config || <additions>` from a superseded row. Single active row invariant
-- is DB-enforced (idx_dt_rubric_version_one_active) and asserted before COMMIT.
--
-- Rubric version 5 -> 6. Taxonomy stays v5 (independent table).
-- ============================================================================

BEGIN;

-- Guard 1 (TASK-636 pattern): refuse to DOWNGRADE. Re-running this file once a
-- newer rubric (v7+) is active would otherwise deactivate it and silently
-- restore v6 - exactly one row stays active, so no count check would notice.
DO $guard$
DECLARE
    newer integer;
BEGIN
    SELECT max(version) INTO newer
    FROM public.dt_rubric_version
    WHERE is_active AND version > 6;
    IF newer IS NOT NULL THEN
        RAISE EXCEPTION
            'refusing to downgrade the active rubric: v% is active (newer than this seed''s v6). '
            'Apply the newer seed instead, or explicitly deactivate v% first.', newer, newer;
    END IF;
END $guard$;

-- Enforce the single-active-row invariant: deactivate any other active row, then
-- upsert THIS version as the active one (idempotent: re-applying keeps exactly
-- version 6 active and deactivates the rest).
UPDATE public.dt_rubric_version SET is_active = false WHERE is_active AND version <> 6;

INSERT INTO public.dt_rubric_version (version, is_active, config, description)
VALUES (
    6,
    true,
    $rubric${
  "acceptable_variation": {
    "en": [
      "synonyms that preserve meaning and register",
      "contractions where the register allows them",
      "optional commas",
      "equally natural clause order",
      "consistent British or American spelling"
    ],
    "ja": [
      "文脈上明らかな主語・主題の省略",
      "意味と敬語レベルを保つ同義の言い換え",
      "どちらも標準的な仮名・漢字表記",
      "どちらも自然な「へ」と「に」の方向表現"
    ],
    "zh": [
      "语境清晰时省略主语或代词",
      "意义与语域均保留的同义替换",
      "两种说法同样自然的语序",
      "标点全角与半角的差异"
    ]
  },
  "band_descriptors": {
    "1": {
      "accuracy": {
        "en": {
          "4": "Grammatically clean throughout; a native reader moves through it without a stumble. (At most one minor slip.)",
          "3": "One or two slips a native reader notices but reads past without stopping. (One major error, or a few minor ones.)",
          "2": "Grammar errors force rereading in at least one place; a pattern such as tense or agreement is unreliable. (Two or three major errors.)",
          "1": "Multiple sentences break down grammatically; the reader has to reconstruct what was meant. (Four or more major errors, or a meaning-breaking one.)"
        },
        "ja": {
          "4": "全体を通して文法的に正しく、母語話者が引っかかることなく読み通せる。（あっても軽微な誤り一つ。）",
          "3": "母語話者は気づくが読み進めるのに支障のない誤りが一つ二つある。（重大な誤り一つ、または軽微な誤り数個。）",
          "2": "文法の誤りで少なくとも一箇所は読み直しが必要になり、ある構文パターン（助詞や時制など）が安定しない。（重大な誤り二〜三個。）",
          "1": "複数の文が文法的に成立せず、読者が意図を再構成する必要がある。（重大な誤り四個以上、または意味を壊す誤り一つ。）"
        },
        "zh": {
          "4": "通篇语法规范，母语者可以毫无停顿地读下来。（至多一处轻微问题。）",
          "3": "有一两处母语者会察觉、但不影响阅读的小问题。（一处严重错误，或几处轻微错误。）",
          "2": "语法错误迫使读者至少在一处重读，某类结构（如语序或助词）不稳定。（两到三处严重错误。）",
          "1": "多个句子语法不成立，读者需要自行还原原意。（四处以上严重错误，或一处破坏理解的错误。）"
        }
      },
      "fidelity": {
        "en": {
          "4": "Carries the reference's meaning and register faithfully — nothing added, dropped, or shifted in tone. (At most one minor wording difference.)",
          "3": "A detail or nuance departs from the reference — a dropped modifier, an added aside, or a small tone shift a careful reader would flag. (One major departure, or a few minor ones.)",
          "2": "Part of the reference's message doesn't carry — the emphasis changes, or something the source made central is missing. (Two or three major departures.)",
          "1": "The reproduction states something the reference did not; meaning or register diverges far enough to mislead. (Four or more major departures, or a meaning-inverting one.)"
        },
        "ja": {
          "4": "参照文の意味と文体・敬語レベルを忠実に伝え、追加・省略・語調のずれがない。（あっても軽微な語選択の違い一つ。）",
          "3": "細部やニュアンスが参照文とずれている——修飾語の欠落、余分な補足、わずかな語調の変化など、注意深い読者なら気づく。（重大なずれ一つ、または軽微なずれ数個。）",
          "2": "参照文のメッセージの一部が伝わらない——重点が変わる、または原文が中心に据えた内容が欠ける。（重大なずれ二〜三個。）",
          "1": "参照文にない内容を述べており、意味または文体・敬語レベルのずれが誤解を招くほど大きい。（重大なずれ四個以上、または意味が逆転する誤り一つ。）"
        },
        "zh": {
          "4": "忠实传达参考译文的意义与语域，没有增添、遗漏或语气偏移。（至多一处轻微用词差异。）",
          "3": "有一处细节或语气与参考译文不符——遗漏修饰、添加补充，或语气略有变化，细心的读者会注意到。（一处严重偏离，或几处轻微偏离。）",
          "2": "参考译文的部分信息没有传达——重心发生变化，或原文着重的内容缺失。（两到三处严重偏离。）",
          "1": "译文表达了参考译文没有的意思，意义或语域的偏离足以造成误导。（四处以上严重偏离，或一处意义相反的错误。）"
        }
      },
      "range": {
        "en": {
          "4": "Matches the variety of vocabulary and sentence structure the reference demands; no flattening into simpler forms. (Lexical and syntactic range on par with the reference.)",
          "3": "Slightly narrower than the reference — a repeated structure, or a plainer word where the reference varied. (Minor flattening; most of the reference's range preserved.)",
          "2": "Reduced variety — leans on a few structures and generic vocabulary the reference avoided. (Range clearly below the reference.)",
          "1": "Vocabulary and structure collapse to the simplest available forms — repetitive and generic against the reference. (Range far below the reference.)"
        },
        "ja": {
          "4": "参照文が求めるのと同程度の語彙と構文の幅を用い、より単純な形へ平板化していない。（語彙・構文の幅が参照文と同等。）",
          "3": "参照文よりわずかに狭い——構文の繰り返しや、参照文が変化させた箇所での平易な語の使用。（軽微な平板化、参照文の幅の大半は保たれている。）",
          "2": "幅が明らかに減っている——少数の構文と、参照文が避けた一般的な語彙に頼っている。（幅が参照文より明らかに狭い。）",
          "1": "語彙と構文が最も単純な形へ収束している——参照文と比べて反復的で一般的。（幅が参照文より大幅に狭い。）"
        },
        "zh": {
          "4": "运用了与参考译文相当的词汇与句式变化，没有退化为更简单的形式。（词汇与句法的丰富度与参考译文相当。）",
          "3": "比参考译文略窄——某处结构重复，或在参考译文有变化处用了更普通的词。（轻微简化，参考译文的大部分丰富度得以保留。）",
          "2": "变化明显减少——依赖少数句式与参考译文回避的笼统词汇。（丰富度明显低于参考译文。）",
          "1": "词汇与句式退化为最简单的形式——相较参考译文重复而笼统。（丰富度远低于参考译文。）"
        }
      },
      "understandability": {
        "en": {
          "4": "A native reader recovers the full intended meaning on one pass, without the reference. (At most one error that strains meaning.)",
          "3": "The message comes through, but the reader slows or guesses at one point to stay with it. (Two or three meaning-straining errors.)",
          "2": "At least one passage leaves the reader unsure what was meant; the thread drops in places. (One meaning-breaking error, or four or more straining ones.)",
          "1": "A native reader cannot reliably recover the intended meaning without the reference. (Two or more meaning-breaking errors.)"
        },
        "ja": {
          "4": "母語話者が一読で意図した意味を完全に把握でき、参照文を必要としない。（あっても理解を妨げる誤り一つ。）",
          "3": "大意は伝わるが、ついていくために読者がどこか一箇所で読む速度を落とすか推測する必要がある。（理解を妨げる誤り二〜三個。）",
          "2": "少なくとも一箇所で読者が意図を確信できず、所々で筋が途切れる。（意味を壊す誤り一つ、または理解を妨げる誤り四個以上。）",
          "1": "母語話者は参照文なしでは意図した意味を確実に復元できない。（意味を壊す誤り二個以上。）"
        },
        "zh": {
          "4": "母语者一遍即可完全理解原意，无需参照参考译文。（至多一处影响理解的错误。）",
          "3": "大意能够传达，但读者需要在某处放慢或猜测才能跟上。（两到三处影响理解的错误。）",
          "2": "至少有一处让读者无法确定原意，思路在部分地方中断。（一处破坏理解的错误，或四处以上影响理解的错误。）",
          "1": "母语者在没有参考译文时无法可靠地还原原意。（两处以上破坏理解的错误。）"
        }
      }
    },
    "2": {
      "accuracy": {
        "en": {
          "4": "Grammatically clean throughout; a native reader moves through it without a stumble. (At most one minor slip.)",
          "3": "One or two slips a native reader notices but reads past without stopping. (One major error, or a few minor ones.)",
          "2": "Grammar errors force rereading in at least one place; a pattern such as tense or agreement is unreliable. (Two or three major errors.)",
          "1": "Multiple sentences break down grammatically; the reader has to reconstruct what was meant. (Four or more major errors, or a meaning-breaking one.)"
        },
        "ja": {
          "4": "全体を通して文法的に正しく、母語話者が引っかかることなく読み通せる。（あっても軽微な誤り一つ。）",
          "3": "母語話者は気づくが読み進めるのに支障のない誤りが一つ二つある。（重大な誤り一つ、または軽微な誤り数個。）",
          "2": "文法の誤りで少なくとも一箇所は読み直しが必要になり、ある構文パターン（助詞や時制など）が安定しない。（重大な誤り二〜三個。）",
          "1": "複数の文が文法的に成立せず、読者が意図を再構成する必要がある。（重大な誤り四個以上、または意味を壊す誤り一つ。）"
        },
        "zh": {
          "4": "通篇语法规范，母语者可以毫无停顿地读下来。（至多一处轻微问题。）",
          "3": "有一两处母语者会察觉、但不影响阅读的小问题。（一处严重错误，或几处轻微错误。）",
          "2": "语法错误迫使读者至少在一处重读，某类结构（如语序或助词）不稳定。（两到三处严重错误。）",
          "1": "多个句子语法不成立，读者需要自行还原原意。（四处以上严重错误，或一处破坏理解的错误。）"
        }
      },
      "fidelity": {
        "en": {
          "4": "Carries the reference's meaning and register faithfully — nothing added, dropped, or shifted in tone. (At most one minor wording difference.)",
          "3": "A detail or nuance departs from the reference — a dropped modifier, an added aside, or a small tone shift a careful reader would flag. (One major departure, or a few minor ones.)",
          "2": "Part of the reference's message doesn't carry — the emphasis changes, or something the source made central is missing. (Two or three major departures.)",
          "1": "The reproduction states something the reference did not; meaning or register diverges far enough to mislead. (Four or more major departures, or a meaning-inverting one.)"
        },
        "ja": {
          "4": "参照文の意味と文体・敬語レベルを忠実に伝え、追加・省略・語調のずれがない。（あっても軽微な語選択の違い一つ。）",
          "3": "細部やニュアンスが参照文とずれている——修飾語の欠落、余分な補足、わずかな語調の変化など、注意深い読者なら気づく。（重大なずれ一つ、または軽微なずれ数個。）",
          "2": "参照文のメッセージの一部が伝わらない——重点が変わる、または原文が中心に据えた内容が欠ける。（重大なずれ二〜三個。）",
          "1": "参照文にない内容を述べており、意味または文体・敬語レベルのずれが誤解を招くほど大きい。（重大なずれ四個以上、または意味が逆転する誤り一つ。）"
        },
        "zh": {
          "4": "忠实传达参考译文的意义与语域，没有增添、遗漏或语气偏移。（至多一处轻微用词差异。）",
          "3": "有一处细节或语气与参考译文不符——遗漏修饰、添加补充，或语气略有变化，细心的读者会注意到。（一处严重偏离，或几处轻微偏离。）",
          "2": "参考译文的部分信息没有传达——重心发生变化，或原文着重的内容缺失。（两到三处严重偏离。）",
          "1": "译文表达了参考译文没有的意思，意义或语域的偏离足以造成误导。（四处以上严重偏离，或一处意义相反的错误。）"
        }
      },
      "range": {
        "en": {
          "4": "Matches the variety of vocabulary and sentence structure the reference demands; no flattening into simpler forms. (Lexical and syntactic range on par with the reference.)",
          "3": "Slightly narrower than the reference — a repeated structure, or a plainer word where the reference varied. (Minor flattening; most of the reference's range preserved.)",
          "2": "Reduced variety — leans on a few structures and generic vocabulary the reference avoided. (Range clearly below the reference.)",
          "1": "Vocabulary and structure collapse to the simplest available forms — repetitive and generic against the reference. (Range far below the reference.)"
        },
        "ja": {
          "4": "参照文が求めるのと同程度の語彙と構文の幅を用い、より単純な形へ平板化していない。（語彙・構文の幅が参照文と同等。）",
          "3": "参照文よりわずかに狭い——構文の繰り返しや、参照文が変化させた箇所での平易な語の使用。（軽微な平板化、参照文の幅の大半は保たれている。）",
          "2": "幅が明らかに減っている——少数の構文と、参照文が避けた一般的な語彙に頼っている。（幅が参照文より明らかに狭い。）",
          "1": "語彙と構文が最も単純な形へ収束している——参照文と比べて反復的で一般的。（幅が参照文より大幅に狭い。）"
        },
        "zh": {
          "4": "运用了与参考译文相当的词汇与句式变化，没有退化为更简单的形式。（词汇与句法的丰富度与参考译文相当。）",
          "3": "比参考译文略窄——某处结构重复，或在参考译文有变化处用了更普通的词。（轻微简化，参考译文的大部分丰富度得以保留。）",
          "2": "变化明显减少——依赖少数句式与参考译文回避的笼统词汇。（丰富度明显低于参考译文。）",
          "1": "词汇与句式退化为最简单的形式——相较参考译文重复而笼统。（丰富度远低于参考译文。）"
        }
      },
      "understandability": {
        "en": {
          "4": "A native reader recovers the full intended meaning on one pass, without the reference. (At most one error that strains meaning.)",
          "3": "The message comes through, but the reader slows or guesses at one point to stay with it. (Two or three meaning-straining errors.)",
          "2": "At least one passage leaves the reader unsure what was meant; the thread drops in places. (One meaning-breaking error, or four or more straining ones.)",
          "1": "A native reader cannot reliably recover the intended meaning without the reference. (Two or more meaning-breaking errors.)"
        },
        "ja": {
          "4": "母語話者が一読で意図した意味を完全に把握でき、参照文を必要としない。（あっても理解を妨げる誤り一つ。）",
          "3": "大意は伝わるが、ついていくために読者がどこか一箇所で読む速度を落とすか推測する必要がある。（理解を妨げる誤り二〜三個。）",
          "2": "少なくとも一箇所で読者が意図を確信できず、所々で筋が途切れる。（意味を壊す誤り一つ、または理解を妨げる誤り四個以上。）",
          "1": "母語話者は参照文なしでは意図した意味を確実に復元できない。（意味を壊す誤り二個以上。）"
        },
        "zh": {
          "4": "母语者一遍即可完全理解原意，无需参照参考译文。（至多一处影响理解的错误。）",
          "3": "大意能够传达，但读者需要在某处放慢或猜测才能跟上。（两到三处影响理解的错误。）",
          "2": "至少有一处让读者无法确定原意，思路在部分地方中断。（一处破坏理解的错误，或四处以上影响理解的错误。）",
          "1": "母语者在没有参考译文时无法可靠地还原原意。（两处以上破坏理解的错误。）"
        }
      }
    },
    "3": {
      "accuracy": {
        "en": {
          "4": "Grammatically clean throughout; a native reader moves through it without a stumble. (At most one minor slip.)",
          "3": "One or two slips a native reader notices but reads past without stopping. (One major error, or a few minor ones.)",
          "2": "Grammar errors force rereading in at least one place; a pattern such as tense or agreement is unreliable. (Two or three major errors.)",
          "1": "Multiple sentences break down grammatically; the reader has to reconstruct what was meant. (Four or more major errors, or a meaning-breaking one.)"
        },
        "ja": {
          "4": "全体を通して文法的に正しく、母語話者が引っかかることなく読み通せる。（あっても軽微な誤り一つ。）",
          "3": "母語話者は気づくが読み進めるのに支障のない誤りが一つ二つある。（重大な誤り一つ、または軽微な誤り数個。）",
          "2": "文法の誤りで少なくとも一箇所は読み直しが必要になり、ある構文パターン（助詞や時制など）が安定しない。（重大な誤り二〜三個。）",
          "1": "複数の文が文法的に成立せず、読者が意図を再構成する必要がある。（重大な誤り四個以上、または意味を壊す誤り一つ。）"
        },
        "zh": {
          "4": "通篇语法规范，母语者可以毫无停顿地读下来。（至多一处轻微问题。）",
          "3": "有一两处母语者会察觉、但不影响阅读的小问题。（一处严重错误，或几处轻微错误。）",
          "2": "语法错误迫使读者至少在一处重读，某类结构（如语序或助词）不稳定。（两到三处严重错误。）",
          "1": "多个句子语法不成立，读者需要自行还原原意。（四处以上严重错误，或一处破坏理解的错误。）"
        }
      },
      "fidelity": {
        "en": {
          "4": "Carries the reference's meaning and register faithfully — nothing added, dropped, or shifted in tone. (At most one minor wording difference.)",
          "3": "A detail or nuance departs from the reference — a dropped modifier, an added aside, or a small tone shift a careful reader would flag. (One major departure, or a few minor ones.)",
          "2": "Part of the reference's message doesn't carry — the emphasis changes, or something the source made central is missing. (Two or three major departures.)",
          "1": "The reproduction states something the reference did not; meaning or register diverges far enough to mislead. (Four or more major departures, or a meaning-inverting one.)"
        },
        "ja": {
          "4": "参照文の意味と文体・敬語レベルを忠実に伝え、追加・省略・語調のずれがない。（あっても軽微な語選択の違い一つ。）",
          "3": "細部やニュアンスが参照文とずれている——修飾語の欠落、余分な補足、わずかな語調の変化など、注意深い読者なら気づく。（重大なずれ一つ、または軽微なずれ数個。）",
          "2": "参照文のメッセージの一部が伝わらない——重点が変わる、または原文が中心に据えた内容が欠ける。（重大なずれ二〜三個。）",
          "1": "参照文にない内容を述べており、意味または文体・敬語レベルのずれが誤解を招くほど大きい。（重大なずれ四個以上、または意味が逆転する誤り一つ。）"
        },
        "zh": {
          "4": "忠实传达参考译文的意义与语域，没有增添、遗漏或语气偏移。（至多一处轻微用词差异。）",
          "3": "有一处细节或语气与参考译文不符——遗漏修饰、添加补充，或语气略有变化，细心的读者会注意到。（一处严重偏离，或几处轻微偏离。）",
          "2": "参考译文的部分信息没有传达——重心发生变化，或原文着重的内容缺失。（两到三处严重偏离。）",
          "1": "译文表达了参考译文没有的意思，意义或语域的偏离足以造成误导。（四处以上严重偏离，或一处意义相反的错误。）"
        }
      },
      "naturalness": {
        "en": {
          "4": "Reads the way a native young teen would say it — plain, idiomatic phrasing for everyday topics. (A native peer would phrase it this way.)",
          "3": "Clear and idiomatic apart from a phrasing choice or two a native teen wouldn't use. (One or two non-native turns of phrase.)",
          "2": "Comprehensible but visibly non-native — word-for-word constructions a native teen would rephrase. (Several stilted or translated-sounding phrasings.)",
          "1": "Meaning survives but the phrasing is unnatural start to finish — assembled rather than spoken. (Non-native phrasing throughout.)"
        },
        "ja": {
          "4": "母語話者の中学生が言うように読める——日常の話題を素朴で自然な言い回しで表す。（母語の同年代も同じ言い方をする。）",
          "3": "明快で自然だが、母語の中学生なら使わない言い回しが一つ二つある。（不自然な言い回し一つ二つ。）",
          "2": "理解はできるが明らかに非母語的——逐語的な構文で、母語の中学生なら言い換える。（ぎこちない、または翻訳調の言い回しがいくつか。）",
          "1": "意味は通じるが全体を通して不自然——自然に発話されたというより組み立てられている。（全体を通して非母語的。）"
        },
        "zh": {
          "4": "读起来就像母语少年的日常说法——用词朴素、地道。（母语同龄人也会这样表达。）",
          "3": "清楚且地道，只有一两处母语少年不会用的说法。（一两处不地道的表达。）",
          "2": "能看懂但明显不像母语——逐字直译的结构，母语少年会重新组织。（若干生硬或翻译腔的表达。）",
          "1": "意思能懂，但通篇表达都不自然——像拼凑而非自然说出。（通篇不地道。）"
        }
      },
      "range": {
        "en": {
          "4": "Matches the variety of vocabulary and sentence structure the reference demands; no flattening into simpler forms. (Lexical and syntactic range on par with the reference.)",
          "3": "Slightly narrower than the reference — a repeated structure, or a plainer word where the reference varied. (Minor flattening; most of the reference's range preserved.)",
          "2": "Reduced variety — leans on a few structures and generic vocabulary the reference avoided. (Range clearly below the reference.)",
          "1": "Vocabulary and structure collapse to the simplest available forms — repetitive and generic against the reference. (Range far below the reference.)"
        },
        "ja": {
          "4": "参照文が求めるのと同程度の語彙と構文の幅を用い、より単純な形へ平板化していない。（語彙・構文の幅が参照文と同等。）",
          "3": "参照文よりわずかに狭い——構文の繰り返しや、参照文が変化させた箇所での平易な語の使用。（軽微な平板化、参照文の幅の大半は保たれている。）",
          "2": "幅が明らかに減っている——少数の構文と、参照文が避けた一般的な語彙に頼っている。（幅が参照文より明らかに狭い。）",
          "1": "語彙と構文が最も単純な形へ収束している——参照文と比べて反復的で一般的。（幅が参照文より大幅に狭い。）"
        },
        "zh": {
          "4": "运用了与参考译文相当的词汇与句式变化，没有退化为更简单的形式。（词汇与句法的丰富度与参考译文相当。）",
          "3": "比参考译文略窄——某处结构重复，或在参考译文有变化处用了更普通的词。（轻微简化，参考译文的大部分丰富度得以保留。）",
          "2": "变化明显减少——依赖少数句式与参考译文回避的笼统词汇。（丰富度明显低于参考译文。）",
          "1": "词汇与句式退化为最简单的形式——相较参考译文重复而笼统。（丰富度远低于参考译文。）"
        }
      },
      "understandability": {
        "en": {
          "4": "A native reader recovers the full intended meaning on one pass, without the reference. (At most one error that strains meaning.)",
          "3": "The message comes through, but the reader slows or guesses at one point to stay with it. (Two or three meaning-straining errors.)",
          "2": "At least one passage leaves the reader unsure what was meant; the thread drops in places. (One meaning-breaking error, or four or more straining ones.)",
          "1": "A native reader cannot reliably recover the intended meaning without the reference. (Two or more meaning-breaking errors.)"
        },
        "ja": {
          "4": "母語話者が一読で意図した意味を完全に把握でき、参照文を必要としない。（あっても理解を妨げる誤り一つ。）",
          "3": "大意は伝わるが、ついていくために読者がどこか一箇所で読む速度を落とすか推測する必要がある。（理解を妨げる誤り二〜三個。）",
          "2": "少なくとも一箇所で読者が意図を確信できず、所々で筋が途切れる。（意味を壊す誤り一つ、または理解を妨げる誤り四個以上。）",
          "1": "母語話者は参照文なしでは意図した意味を確実に復元できない。（意味を壊す誤り二個以上。）"
        },
        "zh": {
          "4": "母语者一遍即可完全理解原意，无需参照参考译文。（至多一处影响理解的错误。）",
          "3": "大意能够传达，但读者需要在某处放慢或猜测才能跟上。（两到三处影响理解的错误。）",
          "2": "至少有一处让读者无法确定原意，思路在部分地方中断。（一处破坏理解的错误，或四处以上影响理解的错误。）",
          "1": "母语者在没有参考译文时无法可靠地还原原意。（两处以上破坏理解的错误。）"
        }
      }
    },
    "4": {
      "accuracy": {
        "en": {
          "4": "Grammatically clean throughout; a native reader moves through it without a stumble. (At most one minor slip.)",
          "3": "One or two slips a native reader notices but reads past without stopping. (One major error, or a few minor ones.)",
          "2": "Grammar errors force rereading in at least one place; a pattern such as tense or agreement is unreliable. (Two or three major errors.)",
          "1": "Multiple sentences break down grammatically; the reader has to reconstruct what was meant. (Four or more major errors, or a meaning-breaking one.)"
        },
        "ja": {
          "4": "全体を通して文法的に正しく、母語話者が引っかかることなく読み通せる。（あっても軽微な誤り一つ。）",
          "3": "母語話者は気づくが読み進めるのに支障のない誤りが一つ二つある。（重大な誤り一つ、または軽微な誤り数個。）",
          "2": "文法の誤りで少なくとも一箇所は読み直しが必要になり、ある構文パターン（助詞や時制など）が安定しない。（重大な誤り二〜三個。）",
          "1": "複数の文が文法的に成立せず、読者が意図を再構成する必要がある。（重大な誤り四個以上、または意味を壊す誤り一つ。）"
        },
        "zh": {
          "4": "通篇语法规范，母语者可以毫无停顿地读下来。（至多一处轻微问题。）",
          "3": "有一两处母语者会察觉、但不影响阅读的小问题。（一处严重错误，或几处轻微错误。）",
          "2": "语法错误迫使读者至少在一处重读，某类结构（如语序或助词）不稳定。（两到三处严重错误。）",
          "1": "多个句子语法不成立，读者需要自行还原原意。（四处以上严重错误，或一处破坏理解的错误。）"
        }
      },
      "fidelity": {
        "en": {
          "4": "Carries the reference's meaning and register faithfully — nothing added, dropped, or shifted in tone. (At most one minor wording difference.)",
          "3": "A detail or nuance departs from the reference — a dropped modifier, an added aside, or a small tone shift a careful reader would flag. (One major departure, or a few minor ones.)",
          "2": "Part of the reference's message doesn't carry — the emphasis changes, or something the source made central is missing. (Two or three major departures.)",
          "1": "The reproduction states something the reference did not; meaning or register diverges far enough to mislead. (Four or more major departures, or a meaning-inverting one.)"
        },
        "ja": {
          "4": "参照文の意味と文体・敬語レベルを忠実に伝え、追加・省略・語調のずれがない。（あっても軽微な語選択の違い一つ。）",
          "3": "細部やニュアンスが参照文とずれている——修飾語の欠落、余分な補足、わずかな語調の変化など、注意深い読者なら気づく。（重大なずれ一つ、または軽微なずれ数個。）",
          "2": "参照文のメッセージの一部が伝わらない——重点が変わる、または原文が中心に据えた内容が欠ける。（重大なずれ二〜三個。）",
          "1": "参照文にない内容を述べており、意味または文体・敬語レベルのずれが誤解を招くほど大きい。（重大なずれ四個以上、または意味が逆転する誤り一つ。）"
        },
        "zh": {
          "4": "忠实传达参考译文的意义与语域，没有增添、遗漏或语气偏移。（至多一处轻微用词差异。）",
          "3": "有一处细节或语气与参考译文不符——遗漏修饰、添加补充，或语气略有变化，细心的读者会注意到。（一处严重偏离，或几处轻微偏离。）",
          "2": "参考译文的部分信息没有传达——重心发生变化，或原文着重的内容缺失。（两到三处严重偏离。）",
          "1": "译文表达了参考译文没有的意思，意义或语域的偏离足以造成误导。（四处以上严重偏离，或一处意义相反的错误。）"
        }
      },
      "naturalness": {
        "en": {
          "4": "Idiomatic and fluent for a high-schooler's register — natural collocations and connectives. (A native peer would phrase it this way.)",
          "3": "Fluent, with a collocation or connective a native high-schooler would swap. (One or two non-native turns of phrase.)",
          "2": "Non-native in places — literal renderings and awkward collocations a native high-schooler would avoid. (Several stilted or translated-sounding phrasings.)",
          "1": "Understandable but unidiomatic start to finish — phrasing built from the source, not spoken. (Non-native phrasing throughout.)"
        },
        "ja": {
          "4": "高校生の語体にふさわしく自然で流暢——コロケーションと接続が自然。（母語の同年代も同じ言い方をする。）",
          "3": "流暢だが、母語の高校生なら差し替えるコロケーションや接続語が一つある。（不自然な言い回し一つ二つ。）",
          "2": "所々で非母語的——逐語的な表現やぎこちないコロケーションを、母語の高校生なら避ける。（ぎこちない、または翻訳調の言い回しがいくつか。）",
          "1": "理解はできるが全体を通して不自然——原文から組み立てた言い回しで、自然な発話ではない。（全体を通して非母語的。）"
        },
        "zh": {
          "4": "地道流畅，符合高中生的语体——搭配与连接自然。（母语同龄人也会这样表达。）",
          "3": "流畅，只有一处搭配或连接词母语高中生会替换。（一两处不地道的表达。）",
          "2": "部分地方不像母语——直译式表达和生硬搭配，母语高中生会避免。（若干生硬或翻译腔的表达。）",
          "1": "能看懂但通篇不地道——表达是从原文拼凑出来的，而非自然说出。（通篇不地道。）"
        }
      },
      "range": {
        "en": {
          "4": "Matches the variety of vocabulary and sentence structure the reference demands; no flattening into simpler forms. (Lexical and syntactic range on par with the reference.)",
          "3": "Slightly narrower than the reference — a repeated structure, or a plainer word where the reference varied. (Minor flattening; most of the reference's range preserved.)",
          "2": "Reduced variety — leans on a few structures and generic vocabulary the reference avoided. (Range clearly below the reference.)",
          "1": "Vocabulary and structure collapse to the simplest available forms — repetitive and generic against the reference. (Range far below the reference.)"
        },
        "ja": {
          "4": "参照文が求めるのと同程度の語彙と構文の幅を用い、より単純な形へ平板化していない。（語彙・構文の幅が参照文と同等。）",
          "3": "参照文よりわずかに狭い——構文の繰り返しや、参照文が変化させた箇所での平易な語の使用。（軽微な平板化、参照文の幅の大半は保たれている。）",
          "2": "幅が明らかに減っている——少数の構文と、参照文が避けた一般的な語彙に頼っている。（幅が参照文より明らかに狭い。）",
          "1": "語彙と構文が最も単純な形へ収束している——参照文と比べて反復的で一般的。（幅が参照文より大幅に狭い。）"
        },
        "zh": {
          "4": "运用了与参考译文相当的词汇与句式变化，没有退化为更简单的形式。（词汇与句法的丰富度与参考译文相当。）",
          "3": "比参考译文略窄——某处结构重复，或在参考译文有变化处用了更普通的词。（轻微简化，参考译文的大部分丰富度得以保留。）",
          "2": "变化明显减少——依赖少数句式与参考译文回避的笼统词汇。（丰富度明显低于参考译文。）",
          "1": "词汇与句式退化为最简单的形式——相较参考译文重复而笼统。（丰富度远低于参考译文。）"
        }
      },
      "understandability": {
        "en": {
          "4": "A native reader recovers the full intended meaning on one pass, without the reference. (At most one error that strains meaning.)",
          "3": "The message comes through, but the reader slows or guesses at one point to stay with it. (Two or three meaning-straining errors.)",
          "2": "At least one passage leaves the reader unsure what was meant; the thread drops in places. (One meaning-breaking error, or four or more straining ones.)",
          "1": "A native reader cannot reliably recover the intended meaning without the reference. (Two or more meaning-breaking errors.)"
        },
        "ja": {
          "4": "母語話者が一読で意図した意味を完全に把握でき、参照文を必要としない。（あっても理解を妨げる誤り一つ。）",
          "3": "大意は伝わるが、ついていくために読者がどこか一箇所で読む速度を落とすか推測する必要がある。（理解を妨げる誤り二〜三個。）",
          "2": "少なくとも一箇所で読者が意図を確信できず、所々で筋が途切れる。（意味を壊す誤り一つ、または理解を妨げる誤り四個以上。）",
          "1": "母語話者は参照文なしでは意図した意味を確実に復元できない。（意味を壊す誤り二個以上。）"
        },
        "zh": {
          "4": "母语者一遍即可完全理解原意，无需参照参考译文。（至多一处影响理解的错误。）",
          "3": "大意能够传达，但读者需要在某处放慢或猜测才能跟上。（两到三处影响理解的错误。）",
          "2": "至少有一处让读者无法确定原意，思路在部分地方中断。（一处破坏理解的错误，或四处以上影响理解的错误。）",
          "1": "母语者在没有参考译文时无法可靠地还原原意。（两处以上破坏理解的错误。）"
        }
      }
    },
    "5": {
      "accuracy": {
        "en": {
          "4": "Grammatically clean throughout; a native reader moves through it without a stumble. (At most one minor slip.)",
          "3": "One or two slips a native reader notices but reads past without stopping. (One major error, or a few minor ones.)",
          "2": "Grammar errors force rereading in at least one place; a pattern such as tense or agreement is unreliable. (Two or three major errors.)",
          "1": "Multiple sentences break down grammatically; the reader has to reconstruct what was meant. (Four or more major errors, or a meaning-breaking one.)"
        },
        "ja": {
          "4": "全体を通して文法的に正しく、母語話者が引っかかることなく読み通せる。（あっても軽微な誤り一つ。）",
          "3": "母語話者は気づくが読み進めるのに支障のない誤りが一つ二つある。（重大な誤り一つ、または軽微な誤り数個。）",
          "2": "文法の誤りで少なくとも一箇所は読み直しが必要になり、ある構文パターン（助詞や時制など）が安定しない。（重大な誤り二〜三個。）",
          "1": "複数の文が文法的に成立せず、読者が意図を再構成する必要がある。（重大な誤り四個以上、または意味を壊す誤り一つ。）"
        },
        "zh": {
          "4": "通篇语法规范，母语者可以毫无停顿地读下来。（至多一处轻微问题。）",
          "3": "有一两处母语者会察觉、但不影响阅读的小问题。（一处严重错误，或几处轻微错误。）",
          "2": "语法错误迫使读者至少在一处重读，某类结构（如语序或助词）不稳定。（两到三处严重错误。）",
          "1": "多个句子语法不成立，读者需要自行还原原意。（四处以上严重错误，或一处破坏理解的错误。）"
        }
      },
      "fidelity": {
        "en": {
          "4": "Carries the reference's meaning and register faithfully — nothing added, dropped, or shifted in tone. (At most one minor wording difference.)",
          "3": "A detail or nuance departs from the reference — a dropped modifier, an added aside, or a small tone shift a careful reader would flag. (One major departure, or a few minor ones.)",
          "2": "Part of the reference's message doesn't carry — the emphasis changes, or something the source made central is missing. (Two or three major departures.)",
          "1": "The reproduction states something the reference did not; meaning or register diverges far enough to mislead. (Four or more major departures, or a meaning-inverting one.)"
        },
        "ja": {
          "4": "参照文の意味と文体・敬語レベルを忠実に伝え、追加・省略・語調のずれがない。（あっても軽微な語選択の違い一つ。）",
          "3": "細部やニュアンスが参照文とずれている——修飾語の欠落、余分な補足、わずかな語調の変化など、注意深い読者なら気づく。（重大なずれ一つ、または軽微なずれ数個。）",
          "2": "参照文のメッセージの一部が伝わらない——重点が変わる、または原文が中心に据えた内容が欠ける。（重大なずれ二〜三個。）",
          "1": "参照文にない内容を述べており、意味または文体・敬語レベルのずれが誤解を招くほど大きい。（重大なずれ四個以上、または意味が逆転する誤り一つ。）"
        },
        "zh": {
          "4": "忠实传达参考译文的意义与语域，没有增添、遗漏或语气偏移。（至多一处轻微用词差异。）",
          "3": "有一处细节或语气与参考译文不符——遗漏修饰、添加补充，或语气略有变化，细心的读者会注意到。（一处严重偏离，或几处轻微偏离。）",
          "2": "参考译文的部分信息没有传达——重心发生变化，或原文着重的内容缺失。（两到三处严重偏离。）",
          "1": "译文表达了参考译文没有的意思，意义或语域的偏离足以造成误导。（四处以上严重偏离，或一处意义相反的错误。）"
        }
      },
      "naturalness": {
        "en": {
          "4": "Sounds like an educated young adult — idiomatic, with natural register control and varied connectives. (A native peer would phrase it this way.)",
          "3": "Idiomatic apart from a phrasing or register choice an educated native would refine. (One or two non-native turns of phrase.)",
          "2": "Non-native phrasing recurs — collocations and register that read as translated rather than composed. (Several stilted or translated-sounding phrasings.)",
          "1": "Unidiomatic for the register start to finish — the reader registers a non-native writer throughout. (Non-native phrasing throughout.)"
        },
        "ja": {
          "4": "教養ある若者のように聞こえる——自然で、語体の制御が的確、接続も多様。（母語の同年代も同じ言い方をする。）",
          "3": "おおむね自然だが、教養ある母語話者なら磨きをかける言い回しや語体の選択が一つある。（不自然な言い回し一つ二つ。）",
          "2": "非母語的な言い回しが繰り返し現れる——コロケーションや語体が、創作ではなく翻訳のように読める。（ぎこちない、または翻訳調の言い回しがいくつか。）",
          "1": "その語体としては全体を通して不自然——読者は終始、非母語話者の書き手だと感じる。（全体を通して非母語的。）"
        },
        "zh": {
          "4": "听起来像受过教育的年轻人——地道、语体把握自然、连接多样。（母语同龄人也会这样表达。）",
          "3": "基本地道，只有一处措辞或语体受过教育的母语者会再打磨。（一两处不地道的表达。）",
          "2": "不地道的表达反复出现——搭配与语体读起来像翻译而非原创。（若干生硬或翻译腔的表达。）",
          "1": "就该语体而言通篇不地道——读者始终能感到这是非母语作者。（通篇不地道。）"
        }
      },
      "range": {
        "en": {
          "4": "Matches the variety of vocabulary and sentence structure the reference demands; no flattening into simpler forms. (Lexical and syntactic range on par with the reference.)",
          "3": "Slightly narrower than the reference — a repeated structure, or a plainer word where the reference varied. (Minor flattening; most of the reference's range preserved.)",
          "2": "Reduced variety — leans on a few structures and generic vocabulary the reference avoided. (Range clearly below the reference.)",
          "1": "Vocabulary and structure collapse to the simplest available forms — repetitive and generic against the reference. (Range far below the reference.)"
        },
        "ja": {
          "4": "参照文が求めるのと同程度の語彙と構文の幅を用い、より単純な形へ平板化していない。（語彙・構文の幅が参照文と同等。）",
          "3": "参照文よりわずかに狭い——構文の繰り返しや、参照文が変化させた箇所での平易な語の使用。（軽微な平板化、参照文の幅の大半は保たれている。）",
          "2": "幅が明らかに減っている——少数の構文と、参照文が避けた一般的な語彙に頼っている。（幅が参照文より明らかに狭い。）",
          "1": "語彙と構文が最も単純な形へ収束している——参照文と比べて反復的で一般的。（幅が参照文より大幅に狭い。）"
        },
        "zh": {
          "4": "运用了与参考译文相当的词汇与句式变化，没有退化为更简单的形式。（词汇与句法的丰富度与参考译文相当。）",
          "3": "比参考译文略窄——某处结构重复，或在参考译文有变化处用了更普通的词。（轻微简化，参考译文的大部分丰富度得以保留。）",
          "2": "变化明显减少——依赖少数句式与参考译文回避的笼统词汇。（丰富度明显低于参考译文。）",
          "1": "词汇与句式退化为最简单的形式——相较参考译文重复而笼统。（丰富度远低于参考译文。）"
        }
      },
      "understandability": {
        "en": {
          "4": "A native reader recovers the full intended meaning on one pass, without the reference. (At most one error that strains meaning.)",
          "3": "The message comes through, but the reader slows or guesses at one point to stay with it. (Two or three meaning-straining errors.)",
          "2": "At least one passage leaves the reader unsure what was meant; the thread drops in places. (One meaning-breaking error, or four or more straining ones.)",
          "1": "A native reader cannot reliably recover the intended meaning without the reference. (Two or more meaning-breaking errors.)"
        },
        "ja": {
          "4": "母語話者が一読で意図した意味を完全に把握でき、参照文を必要としない。（あっても理解を妨げる誤り一つ。）",
          "3": "大意は伝わるが、ついていくために読者がどこか一箇所で読む速度を落とすか推測する必要がある。（理解を妨げる誤り二〜三個。）",
          "2": "少なくとも一箇所で読者が意図を確信できず、所々で筋が途切れる。（意味を壊す誤り一つ、または理解を妨げる誤り四個以上。）",
          "1": "母語話者は参照文なしでは意図した意味を確実に復元できない。（意味を壊す誤り二個以上。）"
        },
        "zh": {
          "4": "母语者一遍即可完全理解原意，无需参照参考译文。（至多一处影响理解的错误。）",
          "3": "大意能够传达，但读者需要在某处放慢或猜测才能跟上。（两到三处影响理解的错误。）",
          "2": "至少有一处让读者无法确定原意，思路在部分地方中断。（一处破坏理解的错误，或四处以上影响理解的错误。）",
          "1": "母语者在没有参考译文时无法可靠地还原原意。（两处以上破坏理解的错误。）"
        }
      }
    },
    "6": {
      "accuracy": {
        "en": {
          "4": "Grammatically clean throughout; a native reader moves through it without a stumble. (At most one minor slip.)",
          "3": "One or two slips a native reader notices but reads past without stopping. (One major error, or a few minor ones.)",
          "2": "Grammar errors force rereading in at least one place; a pattern such as tense or agreement is unreliable. (Two or three major errors.)",
          "1": "Multiple sentences break down grammatically; the reader has to reconstruct what was meant. (Four or more major errors, or a meaning-breaking one.)"
        },
        "ja": {
          "4": "全体を通して文法的に正しく、母語話者が引っかかることなく読み通せる。（あっても軽微な誤り一つ。）",
          "3": "母語話者は気づくが読み進めるのに支障のない誤りが一つ二つある。（重大な誤り一つ、または軽微な誤り数個。）",
          "2": "文法の誤りで少なくとも一箇所は読み直しが必要になり、ある構文パターン（助詞や時制など）が安定しない。（重大な誤り二〜三個。）",
          "1": "複数の文が文法的に成立せず、読者が意図を再構成する必要がある。（重大な誤り四個以上、または意味を壊す誤り一つ。）"
        },
        "zh": {
          "4": "通篇语法规范，母语者可以毫无停顿地读下来。（至多一处轻微问题。）",
          "3": "有一两处母语者会察觉、但不影响阅读的小问题。（一处严重错误，或几处轻微错误。）",
          "2": "语法错误迫使读者至少在一处重读，某类结构（如语序或助词）不稳定。（两到三处严重错误。）",
          "1": "多个句子语法不成立，读者需要自行还原原意。（四处以上严重错误，或一处破坏理解的错误。）"
        }
      },
      "fidelity": {
        "en": {
          "4": "Carries the reference's meaning and register faithfully — nothing added, dropped, or shifted in tone. (At most one minor wording difference.)",
          "3": "A detail or nuance departs from the reference — a dropped modifier, an added aside, or a small tone shift a careful reader would flag. (One major departure, or a few minor ones.)",
          "2": "Part of the reference's message doesn't carry — the emphasis changes, or something the source made central is missing. (Two or three major departures.)",
          "1": "The reproduction states something the reference did not; meaning or register diverges far enough to mislead. (Four or more major departures, or a meaning-inverting one.)"
        },
        "ja": {
          "4": "参照文の意味と文体・敬語レベルを忠実に伝え、追加・省略・語調のずれがない。（あっても軽微な語選択の違い一つ。）",
          "3": "細部やニュアンスが参照文とずれている——修飾語の欠落、余分な補足、わずかな語調の変化など、注意深い読者なら気づく。（重大なずれ一つ、または軽微なずれ数個。）",
          "2": "参照文のメッセージの一部が伝わらない——重点が変わる、または原文が中心に据えた内容が欠ける。（重大なずれ二〜三個。）",
          "1": "参照文にない内容を述べており、意味または文体・敬語レベルのずれが誤解を招くほど大きい。（重大なずれ四個以上、または意味が逆転する誤り一つ。）"
        },
        "zh": {
          "4": "忠实传达参考译文的意义与语域，没有增添、遗漏或语气偏移。（至多一处轻微用词差异。）",
          "3": "有一处细节或语气与参考译文不符——遗漏修饰、添加补充，或语气略有变化，细心的读者会注意到。（一处严重偏离，或几处轻微偏离。）",
          "2": "参考译文的部分信息没有传达——重心发生变化，或原文着重的内容缺失。（两到三处严重偏离。）",
          "1": "译文表达了参考译文没有的意思，意义或语域的偏离足以造成误导。（四处以上严重偏离，或一处意义相反的错误。）"
        }
      },
      "naturalness": {
        "en": {
          "4": "Indistinguishable from an educated native writer — idiomatic, register-precise, naturally cohesive. (A native peer would phrase it this way.)",
          "3": "Near-native, with a subtle collocation or register nuance that reveals a non-native hand. (One or two non-native turns of phrase.)",
          "2": "Fluent but recognisably non-native — phrasing and register choices an educated native would not make. (Several stilted or translated-sounding phrasings.)",
          "1": "Meaning is clear but the prose is unidiomatic for an educated register throughout. (Non-native phrasing throughout.)"
        },
        "ja": {
          "4": "教養ある母語話者の書き手と見分けがつかない——自然で、語体が精密、結束性も自然。（母語の同年代も同じ言い方をする。）",
          "3": "ほぼ母語話者並みだが、非母語的な手つきを覗かせる微妙なコロケーションや語体のニュアンスが一つある。（不自然な言い回し一つ二つ。）",
          "2": "流暢だが明らかに非母語的——教養ある母語話者ならしない言い回しや語体の選択。（ぎこちない、または翻訳調の言い回しがいくつか。）",
          "1": "意味は明快だが、教養ある語体としては全体を通して不自然。（全体を通して非母語的。）"
        },
        "zh": {
          "4": "与受过教育的母语作者无异——地道、语体精准、衔接自然。（母语同龄人也会这样表达。）",
          "3": "接近母语，只有一处细微的搭配或语体差别透露出非母语的痕迹。（一两处不地道的表达。）",
          "2": "流畅但明显非母语——受过教育的母语者不会做出的措辞与语体选择。（若干生硬或翻译腔的表达。）",
          "1": "意思清楚，但就受过教育的语体而言通篇不地道。（通篇不地道。）"
        }
      },
      "range": {
        "en": {
          "4": "Matches the variety of vocabulary and sentence structure the reference demands; no flattening into simpler forms. (Lexical and syntactic range on par with the reference.)",
          "3": "Slightly narrower than the reference — a repeated structure, or a plainer word where the reference varied. (Minor flattening; most of the reference's range preserved.)",
          "2": "Reduced variety — leans on a few structures and generic vocabulary the reference avoided. (Range clearly below the reference.)",
          "1": "Vocabulary and structure collapse to the simplest available forms — repetitive and generic against the reference. (Range far below the reference.)"
        },
        "ja": {
          "4": "参照文が求めるのと同程度の語彙と構文の幅を用い、より単純な形へ平板化していない。（語彙・構文の幅が参照文と同等。）",
          "3": "参照文よりわずかに狭い——構文の繰り返しや、参照文が変化させた箇所での平易な語の使用。（軽微な平板化、参照文の幅の大半は保たれている。）",
          "2": "幅が明らかに減っている——少数の構文と、参照文が避けた一般的な語彙に頼っている。（幅が参照文より明らかに狭い。）",
          "1": "語彙と構文が最も単純な形へ収束している——参照文と比べて反復的で一般的。（幅が参照文より大幅に狭い。）"
        },
        "zh": {
          "4": "运用了与参考译文相当的词汇与句式变化，没有退化为更简单的形式。（词汇与句法的丰富度与参考译文相当。）",
          "3": "比参考译文略窄——某处结构重复，或在参考译文有变化处用了更普通的词。（轻微简化，参考译文的大部分丰富度得以保留。）",
          "2": "变化明显减少——依赖少数句式与参考译文回避的笼统词汇。（丰富度明显低于参考译文。）",
          "1": "词汇与句式退化为最简单的形式——相较参考译文重复而笼统。（丰富度远低于参考译文。）"
        }
      },
      "understandability": {
        "en": {
          "4": "A native reader recovers the full intended meaning on one pass, without the reference. (At most one error that strains meaning.)",
          "3": "The message comes through, but the reader slows or guesses at one point to stay with it. (Two or three meaning-straining errors.)",
          "2": "At least one passage leaves the reader unsure what was meant; the thread drops in places. (One meaning-breaking error, or four or more straining ones.)",
          "1": "A native reader cannot reliably recover the intended meaning without the reference. (Two or more meaning-breaking errors.)"
        },
        "ja": {
          "4": "母語話者が一読で意図した意味を完全に把握でき、参照文を必要としない。（あっても理解を妨げる誤り一つ。）",
          "3": "大意は伝わるが、ついていくために読者がどこか一箇所で読む速度を落とすか推測する必要がある。（理解を妨げる誤り二〜三個。）",
          "2": "少なくとも一箇所で読者が意図を確信できず、所々で筋が途切れる。（意味を壊す誤り一つ、または理解を妨げる誤り四個以上。）",
          "1": "母語話者は参照文なしでは意図した意味を確実に復元できない。（意味を壊す誤り二個以上。）"
        },
        "zh": {
          "4": "母语者一遍即可完全理解原意，无需参照参考译文。（至多一处影响理解的错误。）",
          "3": "大意能够传达，但读者需要在某处放慢或猜测才能跟上。（两到三处影响理解的错误。）",
          "2": "至少有一处让读者无法确定原意，思路在部分地方中断。（一处破坏理解的错误，或四处以上影响理解的错误。）",
          "1": "母语者在没有参考译文时无法可靠地还原原意。（两处以上破坏理解的错误。）"
        }
      }
    }
  },
  "exemplars": {
    "en": {
      "confidence": 0.95,
      "error": {
        "category": 0,
        "confidence": 0.95,
        "corrected_form": "has lived",
        "is_mistake": false,
        "learner_form": "lives",
        "severity_slug": "minor",
        "source": 1,
        "span_ref": [
          4,
          13
        ],
        "span_repro": [
          4,
          9
        ],
        "subtype_slug": "tense_aspect"
      },
      "learner": "She lives in Osaka since 2019, but she still cannot speak Kansai dialect.",
      "reference": "She has lived in Osaka since 2019, but she still cannot speak Kansai dialect.",
      "scores": {
        "accuracy": 3,
        "fidelity": 4,
        "naturalness": 4,
        "range": 4,
        "understandability": 4
      }
    },
    "ja": {
      "confidence": 0.9,
      "error": {
        "category": 0,
        "confidence": 0.9,
        "corrected_form": "部品がセット",
        "is_mistake": false,
        "learner_form": "部品はセット",
        "severity_slug": "major",
        "source": 1,
        "span_ref": [
          0,
          6
        ],
        "span_repro": [
          0,
          6
        ],
        "subtype_slug": "particle_wa_ga"
      },
      "learner": "部品はセットになっている。",
      "reference": "部品がセットになっている。",
      "scores": {
        "accuracy": 3,
        "fidelity": 4,
        "naturalness": 4,
        "range": 4,
        "understandability": 4
      }
    },
    "zh": {
      "confidence": 0.9,
      "error": {
        "category": 0,
        "confidence": 0.9,
        "corrected_form": "买了一",
        "is_mistake": false,
        "learner_form": "买一",
        "severity_slug": "major",
        "source": 1,
        "span_ref": [
          3,
          6
        ],
        "span_repro": [
          3,
          5
        ],
        "subtype_slug": "aspect_marker"
      },
      "learner": "我昨天买一本书。",
      "reference": "我昨天买了一本书。",
      "scores": {
        "accuracy": 3,
        "fidelity": 4,
        "naturalness": 4,
        "range": 4,
        "understandability": 4
      }
    }
  },
  "weights": {
    "by_language": {
      "ja": {
        "fidelity": 0.3
      },
      "zh": {
        "accuracy": 0.4
      }
    },
    "default": {
      "accuracy": 0.3,
      "fidelity": 0.15,
      "naturalness": 0.1,
      "range": 0.15,
      "understandability": 0.3
    }
  },
  "severity_weights": {
    "minor": 1,
    "major": 5,
    "critical": 25
  },
  "understandability_weights": {
    "minor": 0,
    "major": 2,
    "critical": 25
  },
  "band_thresholds": {
    "accuracy": [
      1,
      6,
      15
    ],
    "fidelity": [
      1,
      6,
      15
    ],
    "understandability": [
      2,
      6,
      25
    ]
  }
}$rubric$::jsonb,
    'TASK-629 rubric v6 - band descriptors v3 rewrite (tech spec §8): observable reader behaviour + parenthetical error profile matched to band_thresholds; no frequency adverbs; distinct per band; retires the (content level: ...) suffix. accuracy/fidelity/understandability learner-facing + tier-invariant; range model-facing + tier-invariant; naturalness model-facing + tier-varying, absent at tiers 1-2 (ADR-018). EN user-approved; ZH/JA AI-drafted, flagged for native review (ADR-019). weights/acceptable_variation/exemplars/severity_weights/understandability_weights/band_thresholds carried from v5 unchanged. Self-contained (TASK-636); supersedes v5 (single active row).'
)
ON CONFLICT (version) DO UPDATE
    SET config = EXCLUDED.config,
        description = EXCLUDED.description,
        is_active = true;

-- Guard 2 (TASK-636 pattern): assert the post-condition before COMMIT. The whole
-- file is one transaction, so a RAISE here rolls the migration back rather than
-- leaving the grader without a rubric.
DO $guard$
DECLARE
    active_count integer;
    active_version integer;
BEGIN
    SELECT count(*) INTO active_count
    FROM public.dt_rubric_version WHERE is_active;
    IF active_count <> 1 THEN
        RAISE EXCEPTION
            'expected exactly 1 active dt_rubric_version row after seeding, found %. '
            'Grading reads exactly one active row (grader_cascade.get_active_rubric).', active_count;
    END IF;

    SELECT version INTO active_version
    FROM public.dt_rubric_version WHERE is_active;
    IF active_version <> 6 THEN
        RAISE EXCEPTION 'expected rubric v6 to be the active row after seeding, found v%.', active_version;
    END IF;
END $guard$;

COMMIT;

-- ============================================================================
-- Verification (run manually after applying):
--   SELECT count(*) FROM public.dt_rubric_version WHERE is_active;   -- expect 1
--   SELECT version FROM public.dt_rubric_version WHERE is_active;    -- expect 6
--   -- band_descriptors changed vs v5; everything else equal (expect f, t, t, t, t):
--   SELECT (a.config->'band_descriptors') = (b.config->'band_descriptors'),
--          (a.config->'weights')          = (b.config->'weights'),
--          (a.config->'exemplars')        = (b.config->'exemplars'),
--          (a.config->'acceptable_variation') = (b.config->'acceptable_variation'),
--          (a.config->'band_thresholds')  = (b.config->'band_thresholds')
--   FROM dt_rubric_version a, dt_rubric_version b
--   WHERE a.version = 6 AND b.version = 5;
--   -- no legacy content-level suffix survives:
--   SELECT config::text NOT LIKE '%content level%'
--   FROM dt_rubric_version WHERE version = 6;                        -- expect t
-- ============================================================================
