"""One hand-built FatSeed per language, run through validate_fat_seed().
Not a pytest file (kept out of tests/ deliberately) -- a one-shot smoke
check requested explicitly before trusting seed_schema.py further."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # sandbox/exercise-lab

from prototypes.fat_seed.seed_schema import (  # noqa: E402
    FatSeed, SeedSentence, MorphologicalForm, WrongForm, LabelledDistractor,
    LabelledWrongSentence, SynAntCandidate, WordFamilyForm, WordFamilyFakeForm,
    validate_fat_seed, ASK_SENTENCE_COUNT,
)


def _sentences(word: str, n: int) -> list[SeedSentence]:
    return [
        SeedSentence(index=i, text=f"This is sentence {i} about {word}.",
                     target_word=word, tier="T2")
        for i in range(n)
    ]


def build_en_decide() -> FatSeed:
    word = "decide"
    return FatSeed(
        sense_id=1, vocab_id=1, language_id=2, lemma=word,
        pos="verb", semantic_class_raw="action",
        definition_simple="to choose something", definition_standard="to make a choice after thinking",
        sentences=_sentences(word, ASK_SENTENCE_COUNT),
        morphological_forms=[MorphologicalForm("decided", "past_tense"),
                              MorphologicalForm("deciding", "gerund")],
        morphology_wrong_forms={"decided": [
            WrongForm("decideed", "double-suffix error"),
            WrongForm("decidded", "double consonant error"),
            WrongForm("decides", "wrong tense (present, not past)"),
        ]},
        primary_collocate="decide on",
        collocate_sentence_index=0,
        collocation_distractors=[
            LabelledDistractor("decide with", "wrong preposition, not a fixed collocate"),
            LabelledDistractor("decide for", "sounds plausible but not the fixed form"),
            LabelledDistractor("decide about", "close but not the corpus-attested collocate"),
        ],
        collocation_wrong_collocate=LabelledDistractor("decide of", "not a real collocation of decide"),
        cloze_sentence_index=1,
        cloze_distractors=[
            LabelledDistractor("wonder", "wrong sense — doesn't imply resolution"),
            LabelledDistractor("mention", "unrelated meaning"),
            LabelledDistractor("delay", "near-antonym, plausible surface fit"),
        ],
        discrimination_correct_index=2,
        discrimination_wrong_sentences=[
            LabelledWrongSentence("She decide to go home.", "missing 3rd person -s agreement"),
            LabelledWrongSentence("He decided on go home.", "wrong complement form after 'decide on'"),
            LabelledWrongSentence("They decide already left.", "wrong tense/aspect marking"),
        ],
        spot_incorrect_text="She have decided to leave.",
        spot_incorrect_reason="subject-verb agreement error: 'have' should be 'has'",
        spot_incorrect_corrected="She has decided to leave.",
        spot_incorrect_correct_sentence_indices=[3, 4],
        l1_audio_confusables=[],  # EN L1 optional in this smoke test
        word_family_forms=[WordFamilyForm("decision", "noun"), WordFamilyForm("decisive", "adjective")],
        word_family_fake_forms=[
            WordFamilyFakeForm("decisionment", "plausible but not a real English derivation"),
            WordFamilyFakeForm("decidity", "invented noun suffix, not attested"),
            WordFamilyFakeForm("decisement", "invented, mimics -ment pattern incorrectly"),
        ],
        syn_ant_candidates=[
            SynAntCandidate("resolve", "synonym", "close in this sense"),
            SynAntCandidate("hesitate", "antonym", "opposite of resolving to act"),
        ],
        ipa="/dɪˈsaɪd/",
    )


def build_zh_kafei() -> FatSeed:
    word = "咖啡"
    return FatSeed(
        sense_id=2, vocab_id=2, language_id=1, lemma=word,
        pos="名词", semantic_class_raw="concrete",
        definition_simple="喝的东西，早上喝的多", definition_standard="一种用烘焙咖啡豆制成的饮品",
        sentences=_sentences(word, ASK_SENTENCE_COUNT),
        l1_audio_confusables=[
            LabelledDistractor("卡飞", "invented near-homophone, not a real word (illustrative gap)"),
            LabelledDistractor("咖啡因", "shares 咖啡 as a substring, plausible confusable"),
            LabelledDistractor("咖喱", "shares initial syllable 咖, plausible confusable"),
        ],
        cloze_sentence_index=0,
        cloze_distractors=[
            LabelledDistractor("茶", "different beverage, plausible surface fit"),
            LabelledDistractor("牛奶", "different beverage, plausible surface fit"),
            LabelledDistractor("石头", "trivially wrong, semantically unrelated"),
        ],
    )


def build_ja_kikai() -> FatSeed:
    word = "機械"
    return FatSeed(
        sense_id=3, vocab_id=3, language_id=3, lemma=word,
        pos="名詞", semantic_class_raw="concrete",
        definition_simple="動く道具", definition_standard="動力で動く装置や道具の総称",
        sentences=_sentences(word, ASK_SENTENCE_COUNT),
        pronunciation="きかい",
        cloze_sentence_index=0,
        cloze_distractors=[
            LabelledDistractor("道具", "related but wrong register/specificity"),
            LabelledDistractor("建物", "semantically unrelated, trivially wrong"),
            LabelledDistractor("動物", "semantically unrelated, trivially wrong"),
        ],
        # l1_audio_confusables intentionally empty: ja L1 uses the real mora
        # trie (l1_lookup.build_candidates), never this field.
    )


def main() -> int:
    ok = True
    for label, builder in (("en/decide", build_en_decide), ("zh/咖啡", build_zh_kafei), ("ja/機械", build_ja_kikai)):
        seed = builder()
        result = validate_fat_seed(seed)
        print(f"=== {label} === passed={result.passed} normalized_class={result.normalized_semantic_class}")
        for e in result.errors:
            print(f"  ERROR: {e}")
        for w in result.warnings:
            print(f"  warn: {w}")
        if not result.passed:
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
