-- ============================================================================
-- Dual Translation - rubric v4 seed (TASK-624): Phase-1 prompt-content keys.
-- Adds two new top-level config keys the upgraded tier1/tier2 prompts consume:
--   * acceptable_variation[l2] - the L2-authored "these are NOT errors" bullets
--     (the main clean-passage false-positive lever; prompts._acceptable_variation_text).
--   * exemplars[l2] - one worked (reference, learner, scores, error) example per L2
--     (prompts._exemplar_text; the error's subtype and severity are stored as
--     stable subtype_slug/severity_slug and resolved to live indices at
--     prompt-build time).
--
-- SELF-CONTAINED (TASK-636). This row states a COMPLETE rubric config, exactly
-- like dt_rubric_v1_seed.sql and dt_rubric_v2_seed.sql. It previously built its
-- config as `src.config || <additions>` from an INSERT..SELECT gated on
-- `WHERE src.version = 2`, which made a SUPERSEDED row a hard runtime
-- dependency and had two silent failure modes:
--   * No v2 row and no v4 row: the deactivation UPDATE below still ran, the
--     INSERT..SELECT matched zero rows, and the migration COMMITted with ZERO
--     active rubric rows. Every subsequent non-Tier-0 submission then died in
--     grader_cascade.get_active_rubric ("No active dt_rubric_version row").
--   * No v2 row but v4 already active: the same gate made re-application a
--     silent no-op, so in-place config corrections (e.g. the TASK-625 severity
--     re-tag below) appeared to apply but did not.
-- It also meant dt_rubric_v2_seed.sql could never be archived per
-- migrations/CLAUDE.md without breaking this file. band_descriptors + weights
-- are now equal to v2 by TEST (test_dual_translation_rubric_v2.py
-- ::test_v4_band_descriptors_and_weights_match_v2) rather than by construction.
--
-- TASK-636 slug fix: the JA exemplar's subtype_slug was `particle`, which
-- taxonomy v5 (dt_taxonomy_v5_seed.sql, TASK-626) SPLIT into particle_wa_ga /
-- particle_case / particle_other and deliberately dropped from every pairs list.
-- prompts._exemplar_text resolves the slug with subtypes.index(); it missed and
-- silently fell back to index 0 (= `omission`), so every JA tier1/tier2 prompt
-- taught the model that a HA/GA swap is an omission. Now `particle_wa_ga`.
-- That fallback now DROPS the exemplar and logs (TASK-637) rather than guessing
-- an index - it does not raise, because a degraded prompt beats a grading outage.
--
-- This was NOT hypothetical: on 2026-07-15 the live DB held taxonomy v5 + rubric
-- v4 with subtype_slug `particle`, so production JA prompts had been carrying the
-- mislabelled exemplar. Applying this file fixed it. See ADR-020.
--
-- ZH/JA acceptable_variation bullets + exemplar prose are AI-authored first
-- drafts flagged for NATIVE REVIEW (same pending-review status as the ZH/JA
-- prompt strings in services/dual_translation/prompts.py).
--
-- Version jumps 2 -> 4 to align the rubric version with the taxonomy version it
-- was authored against; v3 is skipped deliberately (see
-- wiki/tasklist/evidence-first-grading.tasks TASK-624). The rubric stays v4
-- under taxonomy v5 - TASK-626 is a taxonomy-only bump.
--
-- TASK-637 severity_slug (in-place, no version bump): the exemplar severity is
-- now a stable `severity_slug` string ("minor"/"major"/"critical"), resolved to
-- an index against prompts.SEVERITY_ENUM at prompt-build time - the same
-- mechanism subtype_slug already used, for the same reason.
--
-- It used to be a bare integer, and that cost us twice. TASK-625 flipped
-- SEVERITY_ENUM from the 2-level global(0)/local(1) enum to the MQM triad
-- (0=minor / 1=major / 2=critical); the stored integers did not move, so they
-- silently re-read as the wrong triad level and had to be hand-retagged (EN
-- tense slip 1->0 minor; ZH aspect-marker omission 0->1 major; JA particle
-- HA/GA 0->1 major). Nothing failed - every index was still legal, just wrong.
-- A slug cannot rot that way: it either resolves or it doesn't, and
-- _exemplar_text now drops the exemplar and logs rather than guessing an index
-- (ADR-020). Kept on v4 (not a new version) so it does not collide with the
-- TASK-627 rubric v5 (severity_weights/thresholds); re-apply this file to
-- upgrade an already-seeded v4 row in place (ON CONFLICT DO UPDATE below).
--
-- Single active row invariant: DB-enforced by the partial unique index
-- idx_dt_rubric_version_one_active (dual_translation_groundwork.sql), and
-- asserted before COMMIT below.
-- ============================================================================

BEGIN;

-- Guard 1 (TASK-636): refuse to DOWNGRADE. Re-running this file once the
-- TASK-627 rubric v5 is active would otherwise deactivate v5 and silently
-- restore v4 - exactly one row stays active, so no count check would notice.
DO $guard$
DECLARE
    newer integer;
BEGIN
    SELECT max(version) INTO newer
    FROM public.dt_rubric_version
    WHERE is_active AND version > 4;
    IF newer IS NOT NULL THEN
        RAISE EXCEPTION
            'refusing to downgrade the active rubric: v% is active (newer than this seed''s v4). '
            'Apply the newer seed instead, or explicitly deactivate v% first.', newer, newer;
    END IF;
END $guard$;

-- Enforce the single-active-row invariant: deactivate any other active row, then
-- upsert THIS version as the active one (idempotent: re-applying keeps exactly
-- version 4 active and deactivates the rest).
UPDATE public.dt_rubric_version SET is_active = false WHERE is_active AND version <> 4;

INSERT INTO public.dt_rubric_version (version, is_active, config, description)
VALUES (
    4,
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
  }
}$rubric$::jsonb,
    'TASK-624 rubric v4 - Phase-1 prompt-content keys. Adds acceptable_variation[l2] (clean-passage FP lever) and exemplars[l2] (one worked example per L2) on top of v2. band_descriptors + weights equal v2 (pinned by test, no longer inherited via jsonb ||). Version aligned to taxonomy v4 naming (v3 skipped); runs under the taxonomy v5 row. ZH/JA strings pending native review. Supersedes v2 (single active row).'
)
ON CONFLICT (version) DO UPDATE
    SET config = EXCLUDED.config,
        description = EXCLUDED.description,
        is_active = true;

-- Guard 2 (TASK-636): assert the post-condition before COMMIT. The whole file is
-- one transaction, so a RAISE here rolls the migration back rather than leaving
-- the grader without a rubric.
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
    IF active_version <> 4 THEN
        RAISE EXCEPTION 'expected rubric v4 to be the active row after seeding, found v%.', active_version;
    END IF;
END $guard$;

COMMIT;

-- ============================================================================
-- Verification (run manually after applying):
--   SELECT count(*) FROM public.dt_rubric_version WHERE is_active;   -- expect 1
--   SELECT version FROM public.dt_rubric_version WHERE is_active;    -- expect 4
--   -- band_descriptors + weights still equal v2 (expect both true):
--   SELECT (a.config->'band_descriptors') = (b.config->'band_descriptors'),
--          (a.config->'weights')          = (b.config->'weights')
--   FROM dt_rubric_version a, dt_rubric_version b
--   WHERE a.version = 4 AND b.version = 2;
--   -- new keys present (expect 3 each):
--   SELECT jsonb_object_keys(config->'acceptable_variation'),
--          jsonb_object_keys(config->'exemplars')
--   FROM dt_rubric_version WHERE version = 4;
--   -- JA exemplar points at the taxonomy v5 slug (expect particle_wa_ga):
--   SELECT config->'exemplars'->'ja'->'error'->>'subtype_slug'
--   FROM dt_rubric_version WHERE version = 4;
--   -- exemplar severities are slugs, not integers (expect minor/major/major,
--   -- and NULL for the retired `severity` key on all three):
--   SELECT key,
--          value->'error'->>'severity_slug' AS severity_slug,
--          value->'error'->>'severity'      AS retired_severity_int
--   FROM dt_rubric_version, jsonb_each(config->'exemplars')
--   WHERE version = 4;
-- ============================================================================
