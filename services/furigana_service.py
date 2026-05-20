"""
Furigana Service — deterministic kanji→hiragana ruby annotations.

Tokenizes Japanese text with fugashi (UniDic) and emits, for each token, either
a plain text span or a ruby span with per-run kanji/kana alignment.

Pipeline:
  1. fugashi tokenizes the input.
  2. For each token, read UniDic's `kana` feature (katakana catalogue reading);
     convert to hiragana with jaconv.
  3. Tokens with no kanji emit {"kind": "plain"}.
  4. Tokens with kanji are split into maximal kanji/kana runs; the reading is
     trimmed at both ends where the surface kana already matches. The middle
     (kanji-runs + their corresponding chunk of reading) becomes ordered ruby
     segments. We use *group ruby* per kanji-run rather than per-character
     alignment, which keeps the algorithm deterministic and correct for
     jukujikun (e.g. 今日 → きょう).
"""

import logging
import unicodedata

import jaconv

from services.vocabulary.model_cache import model_cache

logger = logging.getLogger(__name__)


def _load_fugashi():
    from fugashi import Tagger
    return Tagger()


def _get_tagger():
    return model_cache.get("fugashi_tagger", _load_fugashi)


def _is_kanji(ch: str) -> bool:
    """True for CJK Unified Ideographs (incl. Extension A)."""
    cp = ord(ch)
    return 0x3400 <= cp <= 0x4DBF or 0x4E00 <= cp <= 0x9FFF


def _has_kanji(text: str) -> bool:
    return any(_is_kanji(c) for c in text)


def _split_kanji_kana_runs(surface: str) -> list[tuple[str, str]]:
    """Split surface into ordered (kind, run) tuples where kind ∈ {"kanji", "kana"}."""
    if not surface:
        return []
    runs: list[tuple[str, str]] = []
    cur_kind = "kanji" if _is_kanji(surface[0]) else "kana"
    buf = [surface[0]]
    for ch in surface[1:]:
        kind = "kanji" if _is_kanji(ch) else "kana"
        if kind == cur_kind:
            buf.append(ch)
        else:
            runs.append((cur_kind, "".join(buf)))
            cur_kind = kind
            buf = [ch]
    runs.append((cur_kind, "".join(buf)))
    return runs


def _extract_reading(word) -> str:
    """Best-effort hiragana reading for a fugashi token.

    UniDic exposes `feature.kana` (catalogue kana) and `feature.pron`
    (pronunciation with long-vowel marks). Both are katakana — convert to
    hiragana. Returns '' if no reading is available.
    """
    feature = word.feature
    reading = getattr(feature, "kana", None) or getattr(feature, "pron", None)
    if not reading or reading == "*":
        return ""
    # Normalize and convert katakana → hiragana.
    reading = unicodedata.normalize("NFKC", reading)
    return jaconv.kata2hira(reading)


def _align_okurigana(surface: str, reading: str) -> list[dict]:
    """Align a surface containing at least one kanji with its kana reading.

    Returns a list of segments: each is either {"base": "...", "rt": "..."}
    for a kanji-run with its reading, or {"base": "...", "rt": ""} for a kana
    pass-through. The surface's kana characters at either end are stripped from
    the reading where they match; jukujikun-style middles get the remaining
    reading attached to the kanji-run as a whole.

    The reading is assumed to already be in hiragana; the surface kana may be
    hiragana or katakana — we compare both against the reading.
    """
    runs = _split_kanji_kana_runs(surface)
    reading_hira = reading
    # Convert surface kana to hiragana for comparison only; original kept for display.
    surface_hira = jaconv.kata2hira(surface)
    surface_runs_hira = _split_kanji_kana_runs(surface_hira)

    # Strip matching kana from the left.
    left_strip = 0
    for (kind, run), (_, run_hira) in zip(runs, surface_runs_hira):
        if kind != "kana":
            break
        if reading_hira.startswith(run_hira):
            reading_hira = reading_hira[len(run_hira):]
            left_strip += 1
        else:
            break

    # Strip matching kana from the right.
    right_strip = 0
    for (kind, run), (_, run_hira) in zip(reversed(runs), reversed(surface_runs_hira)):
        if kind != "kana":
            break
        if right_strip >= len(runs) - left_strip:
            break
        if reading_hira.endswith(run_hira):
            reading_hira = reading_hira[: -len(run_hira)] if run_hira else reading_hira
            right_strip += 1
        else:
            break

    middle_runs = runs[left_strip: len(runs) - right_strip] if right_strip else runs[left_strip:]
    head_runs = runs[:left_strip]
    tail_runs = runs[len(runs) - right_strip:] if right_strip else []

    segments: list[dict] = []
    for kind, run in head_runs:
        segments.append({"base": run, "rt": ""})

    if middle_runs:
        # If there's a single kanji-run flanked by kana that already got stripped,
        # the whole remaining reading belongs to that kanji-run.
        kanji_runs_in_middle = [r for r in middle_runs if r[0] == "kanji"]
        if len(kanji_runs_in_middle) == 1 and reading_hira:
            for kind, run in middle_runs:
                if kind == "kanji":
                    segments.append({"base": run, "rt": reading_hira})
                else:
                    segments.append({"base": run, "rt": ""})
        else:
            # Multiple kanji-runs interleaved with kana — we can't split the
            # reading reliably without per-character alignment, so group-ruby
            # the entire middle as one segment.
            middle_base = "".join(run for _, run in middle_runs)
            segments.append({"base": middle_base, "rt": reading_hira})

    for kind, run in tail_runs:
        segments.append({"base": run, "rt": ""})

    return segments


def _token_for_word(word) -> dict:
    """Build the furigana descriptor for one fugashi token."""
    surface = word.surface
    if not surface:
        return {"kind": "plain", "text": ""}

    if not _has_kanji(surface):
        return {"kind": "plain", "text": surface}

    reading = _extract_reading(word)
    if not reading:
        # No reading available — render the surface verbatim.
        return {"kind": "plain", "text": surface}

    segments = _align_okurigana(surface, reading)

    # If alignment collapsed to a single plain segment (shouldn't happen, but be safe).
    if not any(seg["rt"] for seg in segments):
        return {"kind": "plain", "text": surface}

    return {
        "kind": "ruby",
        "base": surface,
        "rt": reading,
        "segments": segments,
    }


def process_passage(text: str) -> list[dict]:
    """Tokenize text and return an ordered list of furigana descriptors.

    Each descriptor is either:
      {"kind": "plain", "text": "..."}                        # render verbatim
      {"kind": "ruby",  "base": "...", "rt": "...",           # render as <ruby>
       "segments": [{"base": "...", "rt": "..."}, ...]}

    Empty input returns []. Tokenizer failures are logged and degrade to a
    single plain token so callers can still render the original string.
    """
    if not text:
        return []
    try:
        tagger = _get_tagger()
        words = list(tagger(text))
    except Exception as e:
        logger.warning("furigana tokenization failed: %s", e)
        return [{"kind": "plain", "text": text}]

    return [_token_for_word(w) for w in words if w.surface]


def process_test_payload(transcript: str, questions: list[dict]) -> dict:
    """Build the full furigana payload for a Japanese test.

    Questions are emitted in input order; the frontend looks them up by index
    (which matches the render order on the test page) since the DB-assigned
    question UUIDs are not yet available at test creation time.

    Shape:
      {
        "transcript": [tokens...],
        "questions": [
          {"text": [tokens...], "choices": [[tokens...], ...]}
        ]
      }
    """
    payload: dict = {
        "transcript": process_passage(transcript or ""),
        "questions": [],
    }
    for q in questions or []:
        text = q.get("question_text") or q.get("question") or ""
        choices = q.get("choices") or []
        if isinstance(choices, str):
            choices = [choices]
        payload["questions"].append({
            "text": process_passage(text),
            "choices": [process_passage(c or "") for c in choices],
        })
    return payload
