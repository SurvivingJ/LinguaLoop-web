-- ============================================================================
-- Dual Translation - rubric v5 seed (TASK-627): derived-scoring config keys.
-- Adds the three keys the evidence-first derived scoring (tech spec §4;
-- services/dual_translation/scoring.py) reads, on top of the complete v4 config:
--   * severity_weights[sev]          - accuracy/fidelity penalty per severity
--                                      (minor 1 / major 5 / critical 25).
--   * understandability_weights[sev] - the SEPARATE understandability axis
--                                      (minor 0 / major 2 / critical 25); every
--                                      error feeds it, incl. naturalness-mapped ones.
--   * band_thresholds[dim] = [t4, t3, t2] (ascending) - penalty <= t4 -> band 4,
--                                      <= t3 -> 3, <= t2 -> 2, else 1. Flat per-
--                                      dimension shape (accuracy/fidelity 1/6/15,
--                                      understandability 2/6/25).
--
-- These are the APPROVED PROVISIONAL DEFAULTS (ADR-019), to be calibrated in
-- Phase 0. They are PINNED: the offline gold-seed fallback
-- (scripts/dt_gold_seed_helper.OFFLINE_SCORING_CONFIG) froze the
-- tests/fixtures/dt_gold/ expected_bands under exactly these values, and
-- tests/test_dual_translation_gold_seed_helper.py fails if this seed's values
-- disagree with that fallback. If these must change, RE-DERIVE the fixtures in
-- the same change - do not edit one side to match the other (TASK-641).
--
-- SELF-CONTAINED (TASK-636 / ADR-020). Like v1/v2/v4, this row states a COMPLETE
-- rubric config via VALUES, never `src.config || <additions>` from a superseded
-- row - that pattern could commit ZERO active rows on an env lacking the source
-- version, hard-downing every non-Tier-0 submission in get_active_rubric. The
-- inherited keys (band_descriptors, weights, acceptable_variation, exemplars) are
-- byte-value-equal to v4 by construction (generated from the v4 config) and held
-- equal to v2's descriptors/weights BY TEST
-- (test_dual_translation_scoring.py::test_v5_band_descriptors_and_weights_match_v2).
--
-- Rubric version 4 -> 5. The taxonomy stays v5 (dt_taxonomy_v5_seed.sql, TASK-626,
-- a taxonomy-only bump); the two version numbers now coincide but the tables are
-- independent. TASK-628 wires scoring.py into grade_submission and consumes these
-- keys; until then the grader still reads the weighted-mean overall via the legacy
-- compute_overall_band and this row's new keys are inert-but-present.
--
-- Single active row invariant: DB-enforced by the partial unique index
-- idx_dt_rubric_version_one_active (dual_translation_groundwork.sql), and
-- asserted before COMMIT below.
-- ============================================================================

BEGIN;

-- Guard 1 (TASK-636 pattern): refuse to DOWNGRADE. Re-running this file once a
-- newer rubric (v6+) is active would otherwise deactivate it and silently restore
-- v5 - exactly one row stays active, so no count check would notice.
DO $guard$
DECLARE
    newer integer;
BEGIN
    SELECT max(version) INTO newer
    FROM public.dt_rubric_version
    WHERE is_active AND version > 5;
    IF newer IS NOT NULL THEN
        RAISE EXCEPTION
            'refusing to downgrade the active rubric: v% is active (newer than this seed''s v5). '
            'Apply the newer seed instead, or explicitly deactivate v% first.', newer, newer;
    END IF;
END $guard$;

-- Enforce the single-active-row invariant: deactivate any other active row, then
-- upsert THIS version as the active one (idempotent: re-applying keeps exactly
-- version 5 active and deactivates the rest).
UPDATE public.dt_rubric_version SET is_active = false WHERE is_active AND version <> 5;

INSERT INTO public.dt_rubric_version (version, is_active, config, description)
VALUES (
    5,
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
          "1": "Pervasive grammatical errors; most sentences are malformed (content level: simple concrete content)",
          "2": "Frequent grammatical errors that disrupt sentences (content level: simple concrete content)",
          "3": "Mostly grammatical, with a few minor errors (content level: simple concrete content)",
          "4": "Consistently grammatical throughout (content level: simple concrete content)"
        },
        "ja": {
          "1": "文法的な誤りが多く、多くの文が成立していない（内容レベル：単純で具体的な内容）",
          "2": "文法的な誤りが多く、文の理解を妨げる（内容レベル：単純で具体的な内容）",
          "3": "概ね文法的に正しく、軽微な誤りが少しある（内容レベル：単純で具体的な内容）",
          "4": "全体を通して文法的に正しい（内容レベル：単純で具体的な内容）"
        },
        "zh": {
          "1": "语法错误普遍，多数句子不成立（内容层级：简单具体的内容）",
          "2": "语法错误较多，影响句子表达（内容层级：简单具体的内容）",
          "3": "基本符合语法，仅有少量小错误（内容层级：简单具体的内容）",
          "4": "全文语法正确（内容层级：简单具体的内容）"
        }
      },
      "fidelity": {
        "en": {
          "1": "Meaning or register departs substantially from the reference (content level: simple concrete content)",
          "2": "Noticeable loss of meaning or shift in register from the reference (content level: simple concrete content)",
          "3": "Meaning and register largely preserved, with minor drift (content level: simple concrete content)",
          "4": "Meaning and register faithfully preserved (content level: simple concrete content)"
        },
        "ja": {
          "1": "意味または文体・敬語レベルが参照文から大きく外れている（内容レベル：単純で具体的な内容）",
          "2": "参照文と比べ、意味の欠落や文体の変化が目立つ（内容レベル：単純で具体的な内容）",
          "3": "意味と文体・敬語レベルは概ね保たれ、わずかなずれがある（内容レベル：単純で具体的な内容）",
          "4": "意味と文体・敬語レベルが忠実に保たれている（内容レベル：単純で具体的な内容）"
        },
        "zh": {
          "1": "意义或语域与参考文本明显偏离（内容层级：简单具体的内容）",
          "2": "与参考文本相比有明显的意义缺失或语域偏移（内容层级：简单具体的内容）",
          "3": "意义与语域大体保留，仅有轻微偏差（内容层级：简单具体的内容）",
          "4": "忠实保留意义与语域（内容层级：简单具体的内容）"
        }
      },
      "range": {
        "en": {
          "1": "Extremely limited vocabulary and sentence structures (content level: simple concrete content)",
          "2": "Limited, repetitive vocabulary and structures (content level: simple concrete content)",
          "3": "Adequate variety of vocabulary and structures for the content (content level: simple concrete content)",
          "4": "Rich, varied, well-controlled vocabulary and structures (content level: simple concrete content)"
        },
        "ja": {
          "1": "語彙と構文が極めて限られている（内容レベル：単純で具体的な内容）",
          "2": "語彙と構文が限られ、繰り返しが多い（内容レベル：単純で具体的な内容）",
          "3": "内容に見合う語彙と構文の多様性がある（内容レベル：単純で具体的な内容）",
          "4": "豊かで多様な語彙と構文を使いこなしている（内容レベル：単純で具体的な内容）"
        },
        "zh": {
          "1": "词汇与句式极为有限（内容层级：简单具体的内容）",
          "2": "词汇与句式有限且重复（内容层级：简单具体的内容）",
          "3": "词汇与句式的多样性适合该内容（内容层级：简单具体的内容）",
          "4": "词汇与句式丰富、多样且运用自如（内容层级：简单具体的内容）"
        }
      },
      "understandability": {
        "en": {
          "1": "A native speaker could not reliably recover the intended meaning (content level: simple concrete content)",
          "2": "A native speaker recovers the meaning only with effort or guessing (content level: simple concrete content)",
          "3": "A native speaker understands the meaning with minor effort (content level: simple concrete content)",
          "4": "A native speaker understands the meaning immediately (content level: simple concrete content)"
        },
        "ja": {
          "1": "母語話者は意図された意味を確実には理解できない（内容レベル：単純で具体的な内容）",
          "2": "母語話者は努力や推測によってのみ意味を理解できる（内容レベル：単純で具体的な内容）",
          "3": "母語話者は少しの努力で意味を理解できる（内容レベル：単純で具体的な内容）",
          "4": "母語話者は即座に意味を理解できる（内容レベル：単純で具体的な内容）"
        },
        "zh": {
          "1": "母语者无法可靠地理解原意（内容层级：简单具体的内容）",
          "2": "母语者需费力或猜测才能理解（内容层级：简单具体的内容）",
          "3": "母语者稍加努力即可理解（内容层级：简单具体的内容）",
          "4": "母语者可立即理解原意（内容层级：简单具体的内容）"
        }
      }
    },
    "2": {
      "accuracy": {
        "en": {
          "1": "Pervasive grammatical errors; most sentences are malformed (content level: everyday content)",
          "2": "Frequent grammatical errors that disrupt sentences (content level: everyday content)",
          "3": "Mostly grammatical, with a few minor errors (content level: everyday content)",
          "4": "Consistently grammatical throughout (content level: everyday content)"
        },
        "ja": {
          "1": "文法的な誤りが多く、多くの文が成立していない（内容レベル：日常的な内容）",
          "2": "文法的な誤りが多く、文の理解を妨げる（内容レベル：日常的な内容）",
          "3": "概ね文法的に正しく、軽微な誤りが少しある（内容レベル：日常的な内容）",
          "4": "全体を通して文法的に正しい（内容レベル：日常的な内容）"
        },
        "zh": {
          "1": "语法错误普遍，多数句子不成立（内容层级：日常内容）",
          "2": "语法错误较多，影响句子表达（内容层级：日常内容）",
          "3": "基本符合语法，仅有少量小错误（内容层级：日常内容）",
          "4": "全文语法正确（内容层级：日常内容）"
        }
      },
      "fidelity": {
        "en": {
          "1": "Meaning or register departs substantially from the reference (content level: everyday content)",
          "2": "Noticeable loss of meaning or shift in register from the reference (content level: everyday content)",
          "3": "Meaning and register largely preserved, with minor drift (content level: everyday content)",
          "4": "Meaning and register faithfully preserved (content level: everyday content)"
        },
        "ja": {
          "1": "意味または文体・敬語レベルが参照文から大きく外れている（内容レベル：日常的な内容）",
          "2": "参照文と比べ、意味の欠落や文体の変化が目立つ（内容レベル：日常的な内容）",
          "3": "意味と文体・敬語レベルは概ね保たれ、わずかなずれがある（内容レベル：日常的な内容）",
          "4": "意味と文体・敬語レベルが忠実に保たれている（内容レベル：日常的な内容）"
        },
        "zh": {
          "1": "意义或语域与参考文本明显偏离（内容层级：日常内容）",
          "2": "与参考文本相比有明显的意义缺失或语域偏移（内容层级：日常内容）",
          "3": "意义与语域大体保留，仅有轻微偏差（内容层级：日常内容）",
          "4": "忠实保留意义与语域（内容层级：日常内容）"
        }
      },
      "range": {
        "en": {
          "1": "Extremely limited vocabulary and sentence structures (content level: everyday content)",
          "2": "Limited, repetitive vocabulary and structures (content level: everyday content)",
          "3": "Adequate variety of vocabulary and structures for the content (content level: everyday content)",
          "4": "Rich, varied, well-controlled vocabulary and structures (content level: everyday content)"
        },
        "ja": {
          "1": "語彙と構文が極めて限られている（内容レベル：日常的な内容）",
          "2": "語彙と構文が限られ、繰り返しが多い（内容レベル：日常的な内容）",
          "3": "内容に見合う語彙と構文の多様性がある（内容レベル：日常的な内容）",
          "4": "豊かで多様な語彙と構文を使いこなしている（内容レベル：日常的な内容）"
        },
        "zh": {
          "1": "词汇与句式极为有限（内容层级：日常内容）",
          "2": "词汇与句式有限且重复（内容层级：日常内容）",
          "3": "词汇与句式的多样性适合该内容（内容层级：日常内容）",
          "4": "词汇与句式丰富、多样且运用自如（内容层级：日常内容）"
        }
      },
      "understandability": {
        "en": {
          "1": "A native speaker could not reliably recover the intended meaning (content level: everyday content)",
          "2": "A native speaker recovers the meaning only with effort or guessing (content level: everyday content)",
          "3": "A native speaker understands the meaning with minor effort (content level: everyday content)",
          "4": "A native speaker understands the meaning immediately (content level: everyday content)"
        },
        "ja": {
          "1": "母語話者は意図された意味を確実には理解できない（内容レベル：日常的な内容）",
          "2": "母語話者は努力や推測によってのみ意味を理解できる（内容レベル：日常的な内容）",
          "3": "母語話者は少しの努力で意味を理解できる（内容レベル：日常的な内容）",
          "4": "母語話者は即座に意味を理解できる（内容レベル：日常的な内容）"
        },
        "zh": {
          "1": "母语者无法可靠地理解原意（内容层级：日常内容）",
          "2": "母语者需费力或猜测才能理解（内容层级：日常内容）",
          "3": "母语者稍加努力即可理解（内容层级：日常内容）",
          "4": "母语者可立即理解原意（内容层级：日常内容）"
        }
      }
    },
    "3": {
      "accuracy": {
        "en": {
          "1": "Pervasive grammatical errors; most sentences are malformed (content level: everyday content with some abstraction)",
          "2": "Frequent grammatical errors that disrupt sentences (content level: everyday content with some abstraction)",
          "3": "Mostly grammatical, with a few minor errors (content level: everyday content with some abstraction)",
          "4": "Consistently grammatical throughout (content level: everyday content with some abstraction)"
        },
        "ja": {
          "1": "文法的な誤りが多く、多くの文が成立していない（内容レベル：やや抽象を含む日常的な内容）",
          "2": "文法的な誤りが多く、文の理解を妨げる（内容レベル：やや抽象を含む日常的な内容）",
          "3": "概ね文法的に正しく、軽微な誤りが少しある（内容レベル：やや抽象を含む日常的な内容）",
          "4": "全体を通して文法的に正しい（内容レベル：やや抽象を含む日常的な内容）"
        },
        "zh": {
          "1": "语法错误普遍，多数句子不成立（内容层级：含一定抽象的日常内容）",
          "2": "语法错误较多，影响句子表达（内容层级：含一定抽象的日常内容）",
          "3": "基本符合语法，仅有少量小错误（内容层级：含一定抽象的日常内容）",
          "4": "全文语法正确（内容层级：含一定抽象的日常内容）"
        }
      },
      "fidelity": {
        "en": {
          "1": "Meaning or register departs substantially from the reference (content level: everyday content with some abstraction)",
          "2": "Noticeable loss of meaning or shift in register from the reference (content level: everyday content with some abstraction)",
          "3": "Meaning and register largely preserved, with minor drift (content level: everyday content with some abstraction)",
          "4": "Meaning and register faithfully preserved (content level: everyday content with some abstraction)"
        },
        "ja": {
          "1": "意味または文体・敬語レベルが参照文から大きく外れている（内容レベル：やや抽象を含む日常的な内容）",
          "2": "参照文と比べ、意味の欠落や文体の変化が目立つ（内容レベル：やや抽象を含む日常的な内容）",
          "3": "意味と文体・敬語レベルは概ね保たれ、わずかなずれがある（内容レベル：やや抽象を含む日常的な内容）",
          "4": "意味と文体・敬語レベルが忠実に保たれている（内容レベル：やや抽象を含む日常的な内容）"
        },
        "zh": {
          "1": "意义或语域与参考文本明显偏离（内容层级：含一定抽象的日常内容）",
          "2": "与参考文本相比有明显的意义缺失或语域偏移（内容层级：含一定抽象的日常内容）",
          "3": "意义与语域大体保留，仅有轻微偏差（内容层级：含一定抽象的日常内容）",
          "4": "忠实保留意义与语域（内容层级：含一定抽象的日常内容）"
        }
      },
      "naturalness": {
        "en": {
          "1": "Reads as clearly non-native throughout (content level: everyday content with some abstraction)",
          "2": "Frequently unnatural phrasing a native speaker would avoid (content level: everyday content with some abstraction)",
          "3": "Mostly natural, with occasional non-native phrasing (content level: everyday content with some abstraction)",
          "4": "Reads as natural, native-sounding expression (content level: everyday content with some abstraction)"
        },
        "ja": {
          "1": "全体を通して明らかに非母語話者の表現である（内容レベル：やや抽象を含む日常的な内容）",
          "2": "母語話者が使わない不自然な表現が頻繁にある（内容レベル：やや抽象を含む日常的な内容）",
          "3": "概ね自然だが、時折不自然な表現がある（内容レベル：やや抽象を含む日常的な内容）",
          "4": "母語話者のように自然な表現である（内容レベル：やや抽象を含む日常的な内容）"
        },
        "zh": {
          "1": "通篇明显不像母语者的表达（内容层级：含一定抽象的日常内容）",
          "2": "经常出现母语者不会使用的不自然表达（内容层级：含一定抽象的日常内容）",
          "3": "大体自然，偶有不地道之处（内容层级：含一定抽象的日常内容）",
          "4": "表达自然，宛如母语者（内容层级：含一定抽象的日常内容）"
        }
      },
      "range": {
        "en": {
          "1": "Extremely limited vocabulary and sentence structures (content level: everyday content with some abstraction)",
          "2": "Limited, repetitive vocabulary and structures (content level: everyday content with some abstraction)",
          "3": "Adequate variety of vocabulary and structures for the content (content level: everyday content with some abstraction)",
          "4": "Rich, varied, well-controlled vocabulary and structures (content level: everyday content with some abstraction)"
        },
        "ja": {
          "1": "語彙と構文が極めて限られている（内容レベル：やや抽象を含む日常的な内容）",
          "2": "語彙と構文が限られ、繰り返しが多い（内容レベル：やや抽象を含む日常的な内容）",
          "3": "内容に見合う語彙と構文の多様性がある（内容レベル：やや抽象を含む日常的な内容）",
          "4": "豊かで多様な語彙と構文を使いこなしている（内容レベル：やや抽象を含む日常的な内容）"
        },
        "zh": {
          "1": "词汇与句式极为有限（内容层级：含一定抽象的日常内容）",
          "2": "词汇与句式有限且重复（内容层级：含一定抽象的日常内容）",
          "3": "词汇与句式的多样性适合该内容（内容层级：含一定抽象的日常内容）",
          "4": "词汇与句式丰富、多样且运用自如（内容层级：含一定抽象的日常内容）"
        }
      },
      "understandability": {
        "en": {
          "1": "A native speaker could not reliably recover the intended meaning (content level: everyday content with some abstraction)",
          "2": "A native speaker recovers the meaning only with effort or guessing (content level: everyday content with some abstraction)",
          "3": "A native speaker understands the meaning with minor effort (content level: everyday content with some abstraction)",
          "4": "A native speaker understands the meaning immediately (content level: everyday content with some abstraction)"
        },
        "ja": {
          "1": "母語話者は意図された意味を確実には理解できない（内容レベル：やや抽象を含む日常的な内容）",
          "2": "母語話者は努力や推測によってのみ意味を理解できる（内容レベル：やや抽象を含む日常的な内容）",
          "3": "母語話者は少しの努力で意味を理解できる（内容レベル：やや抽象を含む日常的な内容）",
          "4": "母語話者は即座に意味を理解できる（内容レベル：やや抽象を含む日常的な内容）"
        },
        "zh": {
          "1": "母语者无法可靠地理解原意（内容层级：含一定抽象的日常内容）",
          "2": "母语者需费力或猜测才能理解（内容层级：含一定抽象的日常内容）",
          "3": "母语者稍加努力即可理解（内容层级：含一定抽象的日常内容）",
          "4": "母语者可立即理解原意（内容层级：含一定抽象的日常内容）"
        }
      }
    },
    "4": {
      "accuracy": {
        "en": {
          "1": "Pervasive grammatical errors; most sentences are malformed (content level: general and somewhat abstract content)",
          "2": "Frequent grammatical errors that disrupt sentences (content level: general and somewhat abstract content)",
          "3": "Mostly grammatical, with a few minor errors (content level: general and somewhat abstract content)",
          "4": "Consistently grammatical throughout (content level: general and somewhat abstract content)"
        },
        "ja": {
          "1": "文法的な誤りが多く、多くの文が成立していない（内容レベル：やや抽象的な一般的内容）",
          "2": "文法的な誤りが多く、文の理解を妨げる（内容レベル：やや抽象的な一般的内容）",
          "3": "概ね文法的に正しく、軽微な誤りが少しある（内容レベル：やや抽象的な一般的内容）",
          "4": "全体を通して文法的に正しい（内容レベル：やや抽象的な一般的内容）"
        },
        "zh": {
          "1": "语法错误普遍，多数句子不成立（内容层级：较为抽象的一般内容）",
          "2": "语法错误较多，影响句子表达（内容层级：较为抽象的一般内容）",
          "3": "基本符合语法，仅有少量小错误（内容层级：较为抽象的一般内容）",
          "4": "全文语法正确（内容层级：较为抽象的一般内容）"
        }
      },
      "fidelity": {
        "en": {
          "1": "Meaning or register departs substantially from the reference (content level: general and somewhat abstract content)",
          "2": "Noticeable loss of meaning or shift in register from the reference (content level: general and somewhat abstract content)",
          "3": "Meaning and register largely preserved, with minor drift (content level: general and somewhat abstract content)",
          "4": "Meaning and register faithfully preserved (content level: general and somewhat abstract content)"
        },
        "ja": {
          "1": "意味または文体・敬語レベルが参照文から大きく外れている（内容レベル：やや抽象的な一般的内容）",
          "2": "参照文と比べ、意味の欠落や文体の変化が目立つ（内容レベル：やや抽象的な一般的内容）",
          "3": "意味と文体・敬語レベルは概ね保たれ、わずかなずれがある（内容レベル：やや抽象的な一般的内容）",
          "4": "意味と文体・敬語レベルが忠実に保たれている（内容レベル：やや抽象的な一般的内容）"
        },
        "zh": {
          "1": "意义或语域与参考文本明显偏离（内容层级：较为抽象的一般内容）",
          "2": "与参考文本相比有明显的意义缺失或语域偏移（内容层级：较为抽象的一般内容）",
          "3": "意义与语域大体保留，仅有轻微偏差（内容层级：较为抽象的一般内容）",
          "4": "忠实保留意义与语域（内容层级：较为抽象的一般内容）"
        }
      },
      "naturalness": {
        "en": {
          "1": "Reads as clearly non-native throughout (content level: general and somewhat abstract content)",
          "2": "Frequently unnatural phrasing a native speaker would avoid (content level: general and somewhat abstract content)",
          "3": "Mostly natural, with occasional non-native phrasing (content level: general and somewhat abstract content)",
          "4": "Reads as natural, native-sounding expression (content level: general and somewhat abstract content)"
        },
        "ja": {
          "1": "全体を通して明らかに非母語話者の表現である（内容レベル：やや抽象的な一般的内容）",
          "2": "母語話者が使わない不自然な表現が頻繁にある（内容レベル：やや抽象的な一般的内容）",
          "3": "概ね自然だが、時折不自然な表現がある（内容レベル：やや抽象的な一般的内容）",
          "4": "母語話者のように自然な表現である（内容レベル：やや抽象的な一般的内容）"
        },
        "zh": {
          "1": "通篇明显不像母语者的表达（内容层级：较为抽象的一般内容）",
          "2": "经常出现母语者不会使用的不自然表达（内容层级：较为抽象的一般内容）",
          "3": "大体自然，偶有不地道之处（内容层级：较为抽象的一般内容）",
          "4": "表达自然，宛如母语者（内容层级：较为抽象的一般内容）"
        }
      },
      "range": {
        "en": {
          "1": "Extremely limited vocabulary and sentence structures (content level: general and somewhat abstract content)",
          "2": "Limited, repetitive vocabulary and structures (content level: general and somewhat abstract content)",
          "3": "Adequate variety of vocabulary and structures for the content (content level: general and somewhat abstract content)",
          "4": "Rich, varied, well-controlled vocabulary and structures (content level: general and somewhat abstract content)"
        },
        "ja": {
          "1": "語彙と構文が極めて限られている（内容レベル：やや抽象的な一般的内容）",
          "2": "語彙と構文が限られ、繰り返しが多い（内容レベル：やや抽象的な一般的内容）",
          "3": "内容に見合う語彙と構文の多様性がある（内容レベル：やや抽象的な一般的内容）",
          "4": "豊かで多様な語彙と構文を使いこなしている（内容レベル：やや抽象的な一般的内容）"
        },
        "zh": {
          "1": "词汇与句式极为有限（内容层级：较为抽象的一般内容）",
          "2": "词汇与句式有限且重复（内容层级：较为抽象的一般内容）",
          "3": "词汇与句式的多样性适合该内容（内容层级：较为抽象的一般内容）",
          "4": "词汇与句式丰富、多样且运用自如（内容层级：较为抽象的一般内容）"
        }
      },
      "understandability": {
        "en": {
          "1": "A native speaker could not reliably recover the intended meaning (content level: general and somewhat abstract content)",
          "2": "A native speaker recovers the meaning only with effort or guessing (content level: general and somewhat abstract content)",
          "3": "A native speaker understands the meaning with minor effort (content level: general and somewhat abstract content)",
          "4": "A native speaker understands the meaning immediately (content level: general and somewhat abstract content)"
        },
        "ja": {
          "1": "母語話者は意図された意味を確実には理解できない（内容レベル：やや抽象的な一般的内容）",
          "2": "母語話者は努力や推測によってのみ意味を理解できる（内容レベル：やや抽象的な一般的内容）",
          "3": "母語話者は少しの努力で意味を理解できる（内容レベル：やや抽象的な一般的内容）",
          "4": "母語話者は即座に意味を理解できる（内容レベル：やや抽象的な一般的内容）"
        },
        "zh": {
          "1": "母语者无法可靠地理解原意（内容层级：较为抽象的一般内容）",
          "2": "母语者需费力或猜测才能理解（内容层级：较为抽象的一般内容）",
          "3": "母语者稍加努力即可理解（内容层级：较为抽象的一般内容）",
          "4": "母语者可立即理解原意（内容层级：较为抽象的一般内容）"
        }
      }
    },
    "5": {
      "accuracy": {
        "en": {
          "1": "Pervasive grammatical errors; most sentences are malformed (content level: varied and more abstract content)",
          "2": "Frequent grammatical errors that disrupt sentences (content level: varied and more abstract content)",
          "3": "Mostly grammatical, with a few minor errors (content level: varied and more abstract content)",
          "4": "Consistently grammatical throughout (content level: varied and more abstract content)"
        },
        "ja": {
          "1": "文法的な誤りが多く、多くの文が成立していない（内容レベル：多様でより抽象的な内容）",
          "2": "文法的な誤りが多く、文の理解を妨げる（内容レベル：多様でより抽象的な内容）",
          "3": "概ね文法的に正しく、軽微な誤りが少しある（内容レベル：多様でより抽象的な内容）",
          "4": "全体を通して文法的に正しい（内容レベル：多様でより抽象的な内容）"
        },
        "zh": {
          "1": "语法错误普遍，多数句子不成立（内容层级：多样且较抽象的内容）",
          "2": "语法错误较多，影响句子表达（内容层级：多样且较抽象的内容）",
          "3": "基本符合语法，仅有少量小错误（内容层级：多样且较抽象的内容）",
          "4": "全文语法正确（内容层级：多样且较抽象的内容）"
        }
      },
      "fidelity": {
        "en": {
          "1": "Meaning or register departs substantially from the reference (content level: varied and more abstract content)",
          "2": "Noticeable loss of meaning or shift in register from the reference (content level: varied and more abstract content)",
          "3": "Meaning and register largely preserved, with minor drift (content level: varied and more abstract content)",
          "4": "Meaning and register faithfully preserved (content level: varied and more abstract content)"
        },
        "ja": {
          "1": "意味または文体・敬語レベルが参照文から大きく外れている（内容レベル：多様でより抽象的な内容）",
          "2": "参照文と比べ、意味の欠落や文体の変化が目立つ（内容レベル：多様でより抽象的な内容）",
          "3": "意味と文体・敬語レベルは概ね保たれ、わずかなずれがある（内容レベル：多様でより抽象的な内容）",
          "4": "意味と文体・敬語レベルが忠実に保たれている（内容レベル：多様でより抽象的な内容）"
        },
        "zh": {
          "1": "意义或语域与参考文本明显偏离（内容层级：多样且较抽象的内容）",
          "2": "与参考文本相比有明显的意义缺失或语域偏移（内容层级：多样且较抽象的内容）",
          "3": "意义与语域大体保留，仅有轻微偏差（内容层级：多样且较抽象的内容）",
          "4": "忠实保留意义与语域（内容层级：多样且较抽象的内容）"
        }
      },
      "naturalness": {
        "en": {
          "1": "Reads as clearly non-native throughout (content level: varied and more abstract content)",
          "2": "Frequently unnatural phrasing a native speaker would avoid (content level: varied and more abstract content)",
          "3": "Mostly natural, with occasional non-native phrasing (content level: varied and more abstract content)",
          "4": "Reads as natural, native-sounding expression (content level: varied and more abstract content)"
        },
        "ja": {
          "1": "全体を通して明らかに非母語話者の表現である（内容レベル：多様でより抽象的な内容）",
          "2": "母語話者が使わない不自然な表現が頻繁にある（内容レベル：多様でより抽象的な内容）",
          "3": "概ね自然だが、時折不自然な表現がある（内容レベル：多様でより抽象的な内容）",
          "4": "母語話者のように自然な表現である（内容レベル：多様でより抽象的な内容）"
        },
        "zh": {
          "1": "通篇明显不像母语者的表达（内容层级：多样且较抽象的内容）",
          "2": "经常出现母语者不会使用的不自然表达（内容层级：多样且较抽象的内容）",
          "3": "大体自然，偶有不地道之处（内容层级：多样且较抽象的内容）",
          "4": "表达自然，宛如母语者（内容层级：多样且较抽象的内容）"
        }
      },
      "range": {
        "en": {
          "1": "Extremely limited vocabulary and sentence structures (content level: varied and more abstract content)",
          "2": "Limited, repetitive vocabulary and structures (content level: varied and more abstract content)",
          "3": "Adequate variety of vocabulary and structures for the content (content level: varied and more abstract content)",
          "4": "Rich, varied, well-controlled vocabulary and structures (content level: varied and more abstract content)"
        },
        "ja": {
          "1": "語彙と構文が極めて限られている（内容レベル：多様でより抽象的な内容）",
          "2": "語彙と構文が限られ、繰り返しが多い（内容レベル：多様でより抽象的な内容）",
          "3": "内容に見合う語彙と構文の多様性がある（内容レベル：多様でより抽象的な内容）",
          "4": "豊かで多様な語彙と構文を使いこなしている（内容レベル：多様でより抽象的な内容）"
        },
        "zh": {
          "1": "词汇与句式极为有限（内容层级：多样且较抽象的内容）",
          "2": "词汇与句式有限且重复（内容层级：多样且较抽象的内容）",
          "3": "词汇与句式的多样性适合该内容（内容层级：多样且较抽象的内容）",
          "4": "词汇与句式丰富、多样且运用自如（内容层级：多样且较抽象的内容）"
        }
      },
      "understandability": {
        "en": {
          "1": "A native speaker could not reliably recover the intended meaning (content level: varied and more abstract content)",
          "2": "A native speaker recovers the meaning only with effort or guessing (content level: varied and more abstract content)",
          "3": "A native speaker understands the meaning with minor effort (content level: varied and more abstract content)",
          "4": "A native speaker understands the meaning immediately (content level: varied and more abstract content)"
        },
        "ja": {
          "1": "母語話者は意図された意味を確実には理解できない（内容レベル：多様でより抽象的な内容）",
          "2": "母語話者は努力や推測によってのみ意味を理解できる（内容レベル：多様でより抽象的な内容）",
          "3": "母語話者は少しの努力で意味を理解できる（内容レベル：多様でより抽象的な内容）",
          "4": "母語話者は即座に意味を理解できる（内容レベル：多様でより抽象的な内容）"
        },
        "zh": {
          "1": "母语者无法可靠地理解原意（内容层级：多样且较抽象的内容）",
          "2": "母语者需费力或猜测才能理解（内容层级：多样且较抽象的内容）",
          "3": "母语者稍加努力即可理解（内容层级：多样且较抽象的内容）",
          "4": "母语者可立即理解原意（内容层级：多样且较抽象的内容）"
        }
      }
    },
    "6": {
      "accuracy": {
        "en": {
          "1": "Pervasive grammatical errors; most sentences are malformed (content level: sophisticated and abstract content)",
          "2": "Frequent grammatical errors that disrupt sentences (content level: sophisticated and abstract content)",
          "3": "Mostly grammatical, with a few minor errors (content level: sophisticated and abstract content)",
          "4": "Consistently grammatical throughout (content level: sophisticated and abstract content)"
        },
        "ja": {
          "1": "文法的な誤りが多く、多くの文が成立していない（内容レベル：複雑で抽象的な内容）",
          "2": "文法的な誤りが多く、文の理解を妨げる（内容レベル：複雑で抽象的な内容）",
          "3": "概ね文法的に正しく、軽微な誤りが少しある（内容レベル：複雑で抽象的な内容）",
          "4": "全体を通して文法的に正しい（内容レベル：複雑で抽象的な内容）"
        },
        "zh": {
          "1": "语法错误普遍，多数句子不成立（内容层级：复杂抽象的内容）",
          "2": "语法错误较多，影响句子表达（内容层级：复杂抽象的内容）",
          "3": "基本符合语法，仅有少量小错误（内容层级：复杂抽象的内容）",
          "4": "全文语法正确（内容层级：复杂抽象的内容）"
        }
      },
      "fidelity": {
        "en": {
          "1": "Meaning or register departs substantially from the reference (content level: sophisticated and abstract content)",
          "2": "Noticeable loss of meaning or shift in register from the reference (content level: sophisticated and abstract content)",
          "3": "Meaning and register largely preserved, with minor drift (content level: sophisticated and abstract content)",
          "4": "Meaning and register faithfully preserved (content level: sophisticated and abstract content)"
        },
        "ja": {
          "1": "意味または文体・敬語レベルが参照文から大きく外れている（内容レベル：複雑で抽象的な内容）",
          "2": "参照文と比べ、意味の欠落や文体の変化が目立つ（内容レベル：複雑で抽象的な内容）",
          "3": "意味と文体・敬語レベルは概ね保たれ、わずかなずれがある（内容レベル：複雑で抽象的な内容）",
          "4": "意味と文体・敬語レベルが忠実に保たれている（内容レベル：複雑で抽象的な内容）"
        },
        "zh": {
          "1": "意义或语域与参考文本明显偏离（内容层级：复杂抽象的内容）",
          "2": "与参考文本相比有明显的意义缺失或语域偏移（内容层级：复杂抽象的内容）",
          "3": "意义与语域大体保留，仅有轻微偏差（内容层级：复杂抽象的内容）",
          "4": "忠实保留意义与语域（内容层级：复杂抽象的内容）"
        }
      },
      "naturalness": {
        "en": {
          "1": "Reads as clearly non-native throughout (content level: sophisticated and abstract content)",
          "2": "Frequently unnatural phrasing a native speaker would avoid (content level: sophisticated and abstract content)",
          "3": "Mostly natural, with occasional non-native phrasing (content level: sophisticated and abstract content)",
          "4": "Reads as natural, native-sounding expression (content level: sophisticated and abstract content)"
        },
        "ja": {
          "1": "全体を通して明らかに非母語話者の表現である（内容レベル：複雑で抽象的な内容）",
          "2": "母語話者が使わない不自然な表現が頻繁にある（内容レベル：複雑で抽象的な内容）",
          "3": "概ね自然だが、時折不自然な表現がある（内容レベル：複雑で抽象的な内容）",
          "4": "母語話者のように自然な表現である（内容レベル：複雑で抽象的な内容）"
        },
        "zh": {
          "1": "通篇明显不像母语者的表达（内容层级：复杂抽象的内容）",
          "2": "经常出现母语者不会使用的不自然表达（内容层级：复杂抽象的内容）",
          "3": "大体自然，偶有不地道之处（内容层级：复杂抽象的内容）",
          "4": "表达自然，宛如母语者（内容层级：复杂抽象的内容）"
        }
      },
      "range": {
        "en": {
          "1": "Extremely limited vocabulary and sentence structures (content level: sophisticated and abstract content)",
          "2": "Limited, repetitive vocabulary and structures (content level: sophisticated and abstract content)",
          "3": "Adequate variety of vocabulary and structures for the content (content level: sophisticated and abstract content)",
          "4": "Rich, varied, well-controlled vocabulary and structures (content level: sophisticated and abstract content)"
        },
        "ja": {
          "1": "語彙と構文が極めて限られている（内容レベル：複雑で抽象的な内容）",
          "2": "語彙と構文が限られ、繰り返しが多い（内容レベル：複雑で抽象的な内容）",
          "3": "内容に見合う語彙と構文の多様性がある（内容レベル：複雑で抽象的な内容）",
          "4": "豊かで多様な語彙と構文を使いこなしている（内容レベル：複雑で抽象的な内容）"
        },
        "zh": {
          "1": "词汇与句式极为有限（内容层级：复杂抽象的内容）",
          "2": "词汇与句式有限且重复（内容层级：复杂抽象的内容）",
          "3": "词汇与句式的多样性适合该内容（内容层级：复杂抽象的内容）",
          "4": "词汇与句式丰富、多样且运用自如（内容层级：复杂抽象的内容）"
        }
      },
      "understandability": {
        "en": {
          "1": "A native speaker could not reliably recover the intended meaning (content level: sophisticated and abstract content)",
          "2": "A native speaker recovers the meaning only with effort or guessing (content level: sophisticated and abstract content)",
          "3": "A native speaker understands the meaning with minor effort (content level: sophisticated and abstract content)",
          "4": "A native speaker understands the meaning immediately (content level: sophisticated and abstract content)"
        },
        "ja": {
          "1": "母語話者は意図された意味を確実には理解できない（内容レベル：複雑で抽象的な内容）",
          "2": "母語話者は努力や推測によってのみ意味を理解できる（内容レベル：複雑で抽象的な内容）",
          "3": "母語話者は少しの努力で意味を理解できる（内容レベル：複雑で抽象的な内容）",
          "4": "母語話者は即座に意味を理解できる（内容レベル：複雑で抽象的な内容）"
        },
        "zh": {
          "1": "母语者无法可靠地理解原意（内容层级：复杂抽象的内容）",
          "2": "母语者需费力或猜测才能理解（内容层级：复杂抽象的内容）",
          "3": "母语者稍加努力即可理解（内容层级：复杂抽象的内容）",
          "4": "母语者可立即理解原意（内容层级：复杂抽象的内容）"
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
    'TASK-627 rubric v5 - derived-scoring config keys. Adds severity_weights (minor 1/major 5/critical 25), understandability_weights (minor 0/major 2/critical 25) and band_thresholds (flat per-dimension [t4,t3,t2]: accuracy/fidelity 1/6/15, understandability 2/6/25) on top of the complete v4 config. Approved provisional defaults (ADR-019), pinned to the gold-seed offline fallback (TASK-641). band_descriptors + weights equal v2 (by test). Consumed by services/dual_translation/scoring.py; wired into grading by TASK-628. Supersedes v4 (single active row).'
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
    IF active_version <> 5 THEN
        RAISE EXCEPTION 'expected rubric v5 to be the active row after seeding, found v%.', active_version;
    END IF;
END $guard$;

COMMIT;

-- ============================================================================
-- Verification (run manually after applying):
--   SELECT count(*) FROM public.dt_rubric_version WHERE is_active;   -- expect 1
--   SELECT version FROM public.dt_rubric_version WHERE is_active;    -- expect 5
--   -- scoring keys present with the pinned provisional defaults:
--   SELECT config->'severity_weights', config->'understandability_weights',
--          config->'band_thresholds'
--   FROM dt_rubric_version WHERE version = 5;
--   -- band_descriptors + weights still equal v2 (expect both true):
--   SELECT (a.config->'band_descriptors') = (b.config->'band_descriptors'),
--          (a.config->'weights')          = (b.config->'weights')
--   FROM dt_rubric_version a, dt_rubric_version b
--   WHERE a.version = 5 AND b.version = 2;
-- ============================================================================
