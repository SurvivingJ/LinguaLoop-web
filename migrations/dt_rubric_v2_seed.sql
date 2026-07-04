-- ============================================================================
-- Dual Translation - rubric v2 seed (TASK-616): per-language weight localisation
-- Bumps the active rubric to raise JA fidelity + ZH accuracy above the v1 baseline.
-- Band descriptors are byte-identical to v1 (generated from it); only weights change.
-- ============================================================================

BEGIN;

-- Enforce the single-active-row invariant: deactivate any other active row, then
-- upsert THIS version as the active one (idempotent: re-applying keeps exactly this
-- version active and deactivates the rest).
UPDATE public.dt_rubric_version SET is_active = false WHERE is_active AND version <> 2;

INSERT INTO public.dt_rubric_version (version, is_active, config, description)
VALUES (
    2,
    true,
    $rubric${
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
    'TASK-616 rubric v2 - per-language weight localisation. Raises by_language.ja.fidelity 0.25->0.30 (keigo/register as a first-class fidelity failure) and by_language.zh.accuracy 0.35->0.40 (classifier/aspect). Band descriptors unchanged from v1. Supersedes v1 (single active row). Resolves the TASK-604 open question on weight ownership: weights stay in dt_rubric_version, the sole reader (grader_cascade.compute_overall_band).'
)
ON CONFLICT (version) DO UPDATE
    SET config = EXCLUDED.config,
        description = EXCLUDED.description,
        is_active = true;

COMMIT;

-- ============================================================================
-- Verification (run manually after applying):
--   SELECT count(*) FROM public.dt_rubric_version WHERE is_active;   -- expect 1
--   SELECT version FROM public.dt_rubric_version WHERE is_active;    -- expect 2
-- ============================================================================
