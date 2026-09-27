"""
Native-language prompt construction for the jev tier-classification experiment.
Reuses services.categorical_maps.TIER_CONSTRAINTS / TIER_DISPLAY_NAMES (LinguaLoop's
existing native-language tier descriptions) so this experiment does not invent new
rubric text.
"""
import sys

REPO = r"c:\Users\James\Documents\Coding\LinguaLoop\WebApp"
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from services.categorical_maps import TIER_CONSTRAINTS, TIER_DISPLAY_NAMES, VALID_TIERS  # noqa: E402

LANG_ID = {"zh": 1, "en": 2, "ja": 3}

STATE_KEY = {"zh": "文章", "en": "passage", "ja": "文章"}

INSTRUCTIONS_CHOICE = {
    "zh": f"{STATE_KEY['zh']}的语言难度最适合下列哪一个年龄层的读者？请根据每个年龄层的语言特征描述来判断。",
    "en": f"Which age group is the {STATE_KEY['en']}'s language difficulty best suited for? Judge using the language-feature description given for each age group.",
    "ja": f"{STATE_KEY['ja']}の言語的な難易度は、次のどの年齢層の読者に最も適していますか？各年齢層の言語的特徴の説明に基づいて判断してください。",
}

INSTRUCTIONS_SCORE = {
    "zh": f"请将{STATE_KEY['zh']}的语言难度，按从最简单（幼儿）到最高级（专业人士）排列的年龄层量表进行定位。",
    "en": f"Place the {STATE_KEY['en']}'s language difficulty on the age-tier scale, ordered from simplest (toddler) to most advanced (professional).",
    "ja": f"{STATE_KEY['ja']}の言語的な難易度を、最も簡単（幼児）から最も高度（専門家）まで並べた年齢層の尺度上に位置づけてください。",
}

# English-control variant: English instructions regardless of passage language
INSTRUCTIONS_CHOICE_EN_CONTROL = (
    "Which age group is the passage's language difficulty best suited for? "
    "Judge using the language-feature description given for each age group."
)
INSTRUCTIONS_SCORE_EN_CONTROL = (
    "Place the passage's language difficulty on the age-tier scale, ordered from "
    "simplest (toddler) to most advanced (professional)."
)


def tier_description(tier: str, lang: str) -> str:
    """Native-language display name + constraint text for one tier, one language."""
    lang_id = LANG_ID[lang]
    name = TIER_DISPLAY_NAMES[tier][lang_id]
    constraint = TIER_CONSTRAINTS[tier][lang_id]
    return f"{name}：{constraint}" if lang != "en" else f"{name}: {constraint}"


def tier_description_en(tier: str) -> str:
    name = TIER_DISPLAY_NAMES[tier][2]
    constraint = TIER_CONSTRAINTS[tier][2]
    return f"{name}: {constraint}"


def build_choice_question(lang: str, tier_order=None, english_control=False):
    tiers = tier_order or list(VALID_TIERS)
    if english_control:
        criteria = {t: tier_description_en(t) for t in tiers}
        instructions = INSTRUCTIONS_CHOICE_EN_CONTROL
    else:
        criteria = {t: tier_description(t, lang) for t in tiers}
        instructions = INSTRUCTIONS_CHOICE[lang]
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def build_score_question(lang: str, english_control=False):
    tiers = list(VALID_TIERS)  # score mode criteria is an ordered array, always T1..T6
    if english_control:
        criteria = [tier_description_en(t) for t in tiers]
        instructions = INSTRUCTIONS_SCORE_EN_CONTROL
    else:
        criteria = [tier_description(t, lang) for t in tiers]
        instructions = INSTRUCTIONS_SCORE[lang]
    return {"type": "score", "instructions": instructions, "criteria": criteria}


def build_request(lang: str, passage_text: str, tier_order=None, english_control=False,
                   include_choice=True, include_score=True):
    state = {STATE_KEY["en" if english_control else lang]: passage_text}
    questions = {}
    if include_choice:
        questions["tier_choice"] = build_choice_question(lang, tier_order=tier_order, english_control=english_control)
    if include_score:
        questions["tier_score"] = build_score_question(lang, english_control=english_control)
    return {
        "model": "typesafe/jev-1.13",
        "state": state,
        "questions": questions,
    }


if __name__ == "__main__":
    import json
    req = build_request("zh", "我今天很开心，因为天气很好。")
    print(json.dumps(req, ensure_ascii=False, indent=2))
