"""
Pitch Accent Service — Japanese mora segmentation + pyopenjtalk accent extraction.

Converts Japanese text into a structured JSON payload for the Pitch Accent Trainer.
Each content word becomes one token with a mora array, accent nucleus, pattern
class (heiban / atamadaka / nakadaka / odaka), and an HL contour.

Pipeline:
  1. pyopenjtalk.run_frontend(text) → list of NJD per-word features
  2. For each content word: segment katakana pronunciation into mora
  3. Derive pattern_class + HL contour from accent nucleus + mora count
  4. Attach the next particle's first mora (for odaka/heiban disambiguation)
"""

import logging

import pyopenjtalk

logger = logging.getLogger(__name__)

# Small kana — combine with the preceding character to form ONE mora.
_SMALL_KANA = frozenset("ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ")

# pyopenjtalk POS tags
_PARTICLE_POS = "助詞"
_PUNCT_POS = frozenset(("記号",))
_AUX_VERB_POS = "助動詞"

# Punctuation glyphs that may slip through with a non-記号 POS
_PUNCTUATION_CHARS = set("。、！？・「」『』（）【】《》〈〉…—,.!?:;\"'()[]{}\n\r\t 　")


def process_passage(text: str) -> list[dict]:
    """Convert Japanese text into a list of pitch-accent tokens.

    Returns a list of dicts, one per content word (plus standalone punctuation).
    Punctuation tokens have is_punctuation=True and are skipped in gameplay.
    """
    if not text or not text.strip():
        return []

    try:
        result = pyopenjtalk.run_frontend(text)
    except Exception as e:
        logger.warning("pyopenjtalk.run_frontend failed: %s", e)
        return []

    # Older pyopenjtalk versions returned (njd, fullcontext); newer return just njd.
    if isinstance(result, tuple) and len(result) == 2:
        njd_features = result[0]
    else:
        njd_features = result

    return _build_tokens(njd_features)


def _build_tokens(njd_features: list[dict]) -> list[dict]:
    """Build pitch-accent tokens from a list of NJD per-word features."""
    tokens: list[dict] = []
    phrase_index = 0

    for i, feat in enumerate(njd_features):
        surface = feat.get("string", "") or ""
        pos = feat.get("pos", "") or ""
        pron = feat.get("pron", "") or ""
        acc_raw = feat.get("acc", 0)
        mora_size_raw = feat.get("mora_size", 0)
        try:
            acc = int(acc_raw)
            mora_size = int(mora_size_raw)
        except (TypeError, ValueError):
            acc = 0
            mora_size = 0

        # Punctuation: keep the token so the rendered grid preserves layout, but
        # mark it non-gameplay.
        is_punct_pos = pos in _PUNCT_POS
        is_punct_char = bool(surface) and all(c in _PUNCTUATION_CHARS for c in surface)
        if is_punct_pos or is_punct_char:
            tokens.append({
                "phrase_index": phrase_index,
                "surface": surface,
                "kana": "",
                "mora": [],
                "mora_count": 0,
                "accent": 0,
                "pattern_class": "punctuation",
                "contour": [],
                "trailing_particle": None,
                "trailing_particle_pitch": None,
                "pos": pos,
                "is_punctuation": True,
                "requires_review": False,
            })
            continue

        # Skip standalone particles / aux verbs as their own tokens — they're
        # represented as trailing_particle on the previous content word.
        if pos == _PARTICLE_POS or pos == _AUX_VERB_POS:
            continue

        # No pronunciation → skip (occasional symbol pyopenjtalk doesn't tag).
        if mora_size <= 0 or not pron:
            continue

        mora_list = _segment_kana_to_mora(pron)
        # If our segmentation disagrees with pyopenjtalk's mora_size, prefer
        # pyopenjtalk's count and pad/truncate our list — the difference is
        # almost always a long-vowel-mark edge case.
        if len(mora_list) != mora_size:
            logger.debug(
                "mora segmentation mismatch for '%s': njd=%d, segmented=%d",
                surface, mora_size, len(mora_list),
            )
            if len(mora_list) > mora_size:
                mora_list = mora_list[:mora_size]
            else:
                mora_list = mora_list + [""] * (mora_size - len(mora_list))

        if acc < 0:
            acc = 0
        if acc > mora_size:
            acc = mora_size

        pattern_class = _derive_pattern_class(acc, mora_size)
        contour = _derive_contour(acc, mora_size)

        # Lookahead for a trailing particle to show the H/L on the next mora.
        trailing_particle = None
        trailing_particle_pitch = None
        if i + 1 < len(njd_features):
            nxt = njd_features[i + 1]
            if (nxt.get("pos") or "") == _PARTICLE_POS:
                nxt_mora = _segment_kana_to_mora(nxt.get("pron", "") or "")
                if nxt_mora:
                    trailing_particle = nxt_mora[0]
                    trailing_particle_pitch = _derive_particle_pitch(acc, mora_size)

        tokens.append({
            "phrase_index": phrase_index,
            "surface": surface,
            "kana": pron,
            "mora": mora_list,
            "mora_count": mora_size,
            "accent": acc,
            "pattern_class": pattern_class,
            "contour": contour,
            "trailing_particle": trailing_particle,
            "trailing_particle_pitch": trailing_particle_pitch,
            "pos": pos,
            "is_punctuation": False,
            "requires_review": pattern_class == "unknown",
        })
        phrase_index += 1

    return tokens


def _segment_kana_to_mora(kana: str) -> list[str]:
    """Segment a kana string into mora units.

    Small kana (ゃゅょ etc.) merge with the preceding character to form one mora.
    Sokuon (っ), moraic nasal (ん), and long-vowel mark (ー) are each their own
    mora.
    """
    mora: list[str] = []
    for ch in kana:
        if ch in _SMALL_KANA and mora:
            mora[-1] = mora[-1] + ch
        else:
            mora.append(ch)
    return mora


def _derive_pattern_class(accent: int, mora_count: int) -> str:
    """Map (accent nucleus, mora count) to the conventional pattern class name."""
    if mora_count <= 0:
        return "unknown"
    if accent == 0:
        return "heiban"
    if accent == 1:
        return "atamadaka"
    if accent == mora_count:
        return "odaka"
    if 2 <= accent <= mora_count - 1:
        return "nakadaka"
    return "unknown"


def _derive_contour(accent: int, mora_count: int) -> list[str]:
    """Build the HL contour as a list of 'H'/'L', one entry per mora.

    Rules:
      - Heiban (accent=0):   L H H H ... (no drop)
      - Atamadaka (accent=1): H L L L ... (drop after mora 1)
      - Nakadaka/Odaka (accent=N): L H ... H L L (drop after mora N)
    Mora 1 and mora 2 always differ in pitch.
    """
    if mora_count <= 0:
        return []
    if accent == 0:
        return ["L"] + ["H"] * (mora_count - 1)
    if accent == 1:
        return ["H"] + ["L"] * (mora_count - 1)
    contour = ["L"]
    for pos in range(2, mora_count + 1):
        contour.append("H" if pos <= accent else "L")
    return contour


def _derive_particle_pitch(accent: int, mora_count: int) -> str:
    """H/L of the trailing particle, derived from the host word's accent.

    Heiban (no drop): particle stays H.
    Odaka (drop on the boundary): particle drops to L.
    Atamadaka / Nakadaka (drop already inside the word): particle is L.
    """
    if accent == 0:
        return "H"
    return "L"
