"""
Pinyin Service — Deterministic tone tokenization and sandhi engine.

Converts Chinese text into a structured JSON payload for the Pinyin Tone Trainer.
Each character gets a token with base tone, context tone (after sandhi), and metadata.

Pipeline:
  1. jieba word segmentation
  2. pypinyin tone extraction per character
  3. Deterministic sandhi rules (三声变调, 一, 不)
  4. Polyphone flagging for LLM fallback
"""

import json
import logging
import re

import jieba
from pypinyin import pinyin, Style

logger = logging.getLogger(__name__)

# Characters that are always punctuation / whitespace — skip in gameplay
_PUNCTUATION = set("。，！？；：""''（）【】《》、…—·,.!?;:\"'()[]<>{}\n\r\t ")

# High-risk polyphones: when jieba segments these as single-char tokens,
# pypinyin's default reading may be wrong. Flag for LLM resolution.
POLYPHONE_WATCHLIST = frozenset({
    # Critical (high frequency, major grammatical shifts)
    "还", "行", "得", "地", "重", "教", "长", "少", "乐", "了",
    "着", "和", "分", "觉", "好", "干", "差",
    # Extended watchlist
    "把", "薄", "背", "奔", "便", "剥", "泊", "参", "藏", "曾",
    "刹", "场", "朝", "称", "澄", "乘", "冲", "处", "创", "答",
    "大", "当", "倒", "提", "调", "度", "都", "发", "坊", "缝",
    "佛", "给", "更", "供", "冠", "哈", "号", "喝", "横", "划",
    "会", "几", "济", "系", "假", "间", "将", "降", "角", "结",
    "解", "尽", "禁", "劲", "卷", "圈", "卡", "看", "壳", "空",
    "落", "累", "量", "凉", "撩", "露", "率", "绿", "抹", "埋",
    "没", "闷", "蒙", "模", "难", "宁", "弄", "排", "炮", "片",
    "屏", "铺", "曝", "栖", "强", "悄", "翘", "切", "亲", "曲",
    "撒", "塞", "散", "丧", "色", "煞", "扇", "折", "舍", "什",
    "省", "盛", "似", "熟", "数", "说", "弹", "挑", "帖", "吐",
    "鲜", "相", "削", "血", "应", "载", "脏", "择", "扎", "轧",
    "挣", "只", "中", "种", "转", "综", "钻", "作",
})


def process_passage(text: str) -> list[dict]:
    """Convert Chinese text into a list of pinyin tokens with sandhi applied.

    Returns a list of dicts, one per character (including punctuation).
    Punctuation tokens have is_punctuation=True and are skipped in gameplay.
    """
    if not text or not text.strip():
        return []

    words = jieba.lcut(text)
    tokens = _build_tokens(words)
    tokens = _apply_sandhi(tokens)
    _flag_polyphones(tokens, words)
    return tokens


def _build_tokens(words: list[str]) -> list[dict]:
    """Build token list from jieba-segmented words using pypinyin."""
    tokens = []

    for word in words:
        # Get pinyin with tone numbers for the whole word at once
        # This gives pypinyin context for better polyphone disambiguation
        word_pinyin = pinyin(word, style=Style.TONE3, v_to_u=True, neutral_tone_with_five=True)

        for i, char in enumerate(word):
            if char in _PUNCTUATION:
                tokens.append({
                    "char": char,
                    "word": word,
                    "pinyin_text": "",
                    "base_tone": 0,
                    "context_tone": 0,
                    "is_sandhi": False,
                    "sandhi_rule": None,
                    "is_punctuation": True,
                    "requires_review": False,
                })
                continue

            # Extract pinyin and tone number
            if i < len(word_pinyin):
                raw = word_pinyin[i][0]
            else:
                raw = ""

            base_tone, clean_pinyin = _parse_tone(raw)

            tokens.append({
                "char": char,
                "word": word,
                "pinyin_text": clean_pinyin,
                "base_tone": base_tone,
                "context_tone": base_tone,  # overridden by sandhi if applicable
                "is_sandhi": False,
                "sandhi_rule": None,
                "is_punctuation": False,
                "requires_review": False,
            })

    return tokens


def _parse_tone(raw_pinyin: str) -> tuple[int, str]:
    """Extract tone number and clean pinyin text from a TONE3-style string.

    Examples: 'ni3' -> (3, 'ni'), 'ma5' -> (5, 'ma'), 'a' -> (5, 'a')
    """
    if not raw_pinyin:
        return 5, ""

    if raw_pinyin[-1].isdigit():
        return int(raw_pinyin[-1]), raw_pinyin[:-1]

    return 5, raw_pinyin


def _apply_sandhi(tokens: list[dict]) -> list[dict]:
    """Apply deterministic tone sandhi rules to the token list.

    Rules applied in order:
    1. Third tone sandhi (two consecutive 3rd tones)
    2. 一 (yī) sandhi rules
    3. 不 (bù) sandhi rules
    """
    playable = [(i, t) for i, t in enumerate(tokens) if not t["is_punctuation"]]

    for pos in range(len(playable)):
        idx, token = playable[pos]

        # Find next playable token
        next_token = playable[pos + 1][1] if pos + 1 < len(playable) else None
        prev_token = playable[pos - 1][1] if pos > 0 else None

        # --- Rule 1: Third tone sandhi ---
        # When two 3rd tones are consecutive, the first becomes 2nd
        if (token["base_tone"] == 3
                and next_token is not None
                and next_token["base_tone"] == 3
                and token["char"] != "一" and token["char"] != "不"):
            token["context_tone"] = 2
            token["is_sandhi"] = True
            token["sandhi_rule"] = "Third tone sandhi: when two 3rd tones appear together, the first changes to a 2nd tone."

        # --- Rule 2: 一 sandhi ---
        if token["char"] == "一":
            if next_token is not None:
                # 2a: Between duplicated verbs → neutral tone
                if (prev_token is not None
                        and prev_token["char"] == next_token["char"]):
                    token["context_tone"] = 5
                    token["is_sandhi"] = True
                    token["sandhi_rule"] = "'一' becomes neutral tone when between a repeated verb (e.g., 看一看)."
                # 2b: Before a 4th tone → 2nd tone
                elif next_token["base_tone"] == 4:
                    token["context_tone"] = 2
                    token["is_sandhi"] = True
                    token["sandhi_rule"] = "'一' changes to 2nd tone when preceding a 4th tone."
                # 2c: Before 1st, 2nd, or 3rd tone → 4th tone
                elif next_token["base_tone"] in (1, 2, 3):
                    token["context_tone"] = 4
                    token["is_sandhi"] = True
                    token["sandhi_rule"] = "'一' changes to 4th tone when preceding a 1st, 2nd, or 3rd tone."
            # Default: remains 1st tone (end of phrase, counting, etc.)

        # --- Rule 3: 不 sandhi ---
        if token["char"] == "不":
            if next_token is not None:
                # 3a: A不A pattern → neutral tone
                if (prev_token is not None
                        and prev_token["char"] == next_token["char"]):
                    token["context_tone"] = 5
                    token["is_sandhi"] = True
                    token["sandhi_rule"] = "'不' becomes neutral tone in an A不A question pattern (e.g., 好不好)."
                # 3b: Before a 4th tone → 2nd tone
                elif next_token["base_tone"] == 4:
                    token["context_tone"] = 2
                    token["is_sandhi"] = True
                    token["sandhi_rule"] = "'不' changes to 2nd tone when preceding a 4th tone."

    return tokens


def _flag_polyphones(tokens: list[dict], words: list[str]) -> None:
    """Flag single-character tokens that are known polyphones.

    When jieba segments a polyphone as a standalone character (not part of
    a recognized compound), pypinyin may pick the wrong reading. These get
    flagged for optional LLM resolution at batch-processing time.
    """
    for token in tokens:
        if token["is_punctuation"]:
            continue
        if token["char"] in POLYPHONE_WATCHLIST and len(token["word"].strip()) == 1:
            token["requires_review"] = True


def resolve_polyphones_llm(sentence: str, tokens: list[dict]) -> list[dict]:
    """Resolve flagged polyphone tokens using LLM.

    Calls DeepSeek via llm_service.call_llm() for each flagged token.
    Updates tokens in-place and returns the modified list.
    """
    from services.llm_service import call_llm
    from config import Config

    flagged = [(i, t) for i, t in enumerate(tokens) if t.get("requires_review")]
    if not flagged:
        return tokens

    model = Config.get_model_for_language("chinese", "questions")

    for idx, token in flagged:
        prompt = (
            f'Analyze this Chinese sentence: "{sentence}"\n\n'
            f'The character "{token["char"]}" (at position {idx}) is a polyphone (多音字).\n'
            f'Based on the grammatical context, determine its correct pinyin and tone.\n\n'
            f'Respond in JSON: {{"pinyin_text": "string (pinyin without tone number, e.g. huan)", '
            f'"tone": integer (1-5, where 5 is neutral)}}'
        )

        try:
            result = call_llm(
                prompt,
                model=model,
                language="chinese",
                temperature=0.0,
                response_format="json",
                max_tokens=100,
            )

            if isinstance(result, dict) and "pinyin_text" in result and "tone" in result:
                token["pinyin_text"] = result["pinyin_text"]
                tone = int(result["tone"])
                token["base_tone"] = tone
                token["context_tone"] = tone
                token["requires_review"] = False
                logger.info(f"LLM resolved polyphone '{token['char']}' → {result['pinyin_text']}{tone}")
            else:
                logger.warning(f"Unexpected LLM response for '{token['char']}': {result}")

        except Exception as e:
            logger.warning(f"LLM resolution failed for '{token['char']}': {e}")
            # Keep default pypinyin reading — correct ~95% of the time

    # Re-apply sandhi after LLM corrections may have changed base tones
    tokens = _apply_sandhi(tokens)
    return tokens
