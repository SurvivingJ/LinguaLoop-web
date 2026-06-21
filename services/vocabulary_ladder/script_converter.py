# services/vocabulary_ladder/script_converter.py
"""
Simplified → Traditional Chinese script converter (TASK-509).

Operator decision (plan §6.7): dual-store both scripts at generation time. ZH
vocab is authored in Simplified; this converter produces the Traditional (Taiwan
standard, phrase-aware: OpenCC config ``s2twp``) mirror that the renderer pins
onto ``content.hant`` and that fills ``dim_vocabulary.lemma_traditional``.

Two layers:
  1. OpenCC ``s2twp`` — phrase-aware conversion. Because it is phrase-aware it
     already resolves most one-to-many ambiguities (发 → 發/髮, 面 → 面/麵,
     干 → 乾/幹/干, 后 → 后/後) from surrounding context, so jieba pre-segmentation
     is unnecessary for the conversion itself.
  2. ``script_conversion_overrides`` (simplified PK → traditional) — a small
     human-curated table for the residual cases OpenCC still gets wrong. Overrides
     ALWAYS win: the simplified form is swapped for a private-use sentinel before
     OpenCC runs, then the sentinel is replaced with the curated traditional form,
     so OpenCC can never re-convert it. Correcting an override + re-running the
     backfill therefore updates only the affected mirror.

Non-Han characters (pinyin, ASCII, English definitions, punctuation) pass through
unchanged, so :meth:`convert_content` can be run over a whole exercise ``content``
dict safely — only Hanzi strings are transformed.
"""

import logging

logger = logging.getLogger(__name__)

# Private-use sentinels — never produced by OpenCC, never present in source text.
_SENT_OPEN = chr(0xE000)
_SENT_CLOSE = chr(0xE001)


def _has_han(text: str) -> bool:
    """True if the string contains at least one CJK ideograph worth converting."""
    for ch in text:
        o = ord(ch)
        if 0x3400 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF or 0x20000 <= o <= 0x2FA1F:
            return True
    return False


class ScriptConverter:
    """Stateless-ish Simplified→Traditional converter with curated overrides."""

    def __init__(self, overrides: dict[str, str] | None = None, config: str = 's2twp'):
        import opencc  # lazy: only ZH paths need it
        self._cc = opencc.OpenCC(config)
        # Longest simplified keys first so multi-char overrides win over any
        # single-char override that is a substring of them.
        self._overrides = dict(
            sorted((overrides or {}).items(), key=lambda kv: len(kv[0]), reverse=True)
        )

    @classmethod
    def from_db(cls, db, config: str = 's2twp') -> 'ScriptConverter':
        """Build a converter, loading curated overrides from the DB (best-effort)."""
        overrides: dict[str, str] = {}
        try:
            resp = (
                db.table('script_conversion_overrides')
                .select('simplified, traditional')
                .execute()
            )
            for row in (resp.data or []):
                simp = (row.get('simplified') or '').strip()
                trad = (row.get('traditional') or '').strip()
                if simp and trad:
                    overrides[simp] = trad
        except Exception as exc:
            logger.warning("Could not load script_conversion_overrides: %s", exc)
        return cls(overrides, config=config)

    def convert(self, text):
        """Convert a single string Simplified→Traditional. Non-str / non-Han pass through."""
        if not isinstance(text, str) or not text or not _has_han(text):
            return text

        work = text
        sentinels: dict[str, str] = {}
        for i, (simp, trad) in enumerate(self._overrides.items()):
            if simp in work:
                token = f'{_SENT_OPEN}{i}{_SENT_CLOSE}'
                sentinels[token] = trad
                work = work.replace(simp, token)

        converted = self._cc.convert(work)

        for token, trad in sentinels.items():
            converted = converted.replace(token, trad)
        return converted

    def convert_content(self, obj):
        """Deep-convert every string in a dict/list/scalar structure."""
        if isinstance(obj, str):
            return self.convert(obj)
        if isinstance(obj, list):
            return [self.convert_content(x) for x in obj]
        if isinstance(obj, dict):
            return {k: self.convert_content(v) for k, v in obj.items()}
        return obj
