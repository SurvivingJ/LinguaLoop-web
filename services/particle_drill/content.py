"""Reads the built particle-drill content from ``data/particle_drill/<lang>/``.

The content is static and ships with the code (ADR-064): ``catalog.json``,
``guides/<group>.json``, ``items/<skill>.jsonl`` (plus the authoring part
files ``items/<skill>__<part>.jsonl``), ``packs/<skill>.json`` and
``conjugation/*.json``. ``scripts/particle_drill_build.py`` checks all of it
and writes ``manifest.json`` (counts and a content version). Files are read
on first use and kept in memory (about 5 MB for Japanese).
"""
import glob
import hashlib
import json
import logging
import os
import threading
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          '..', '..', 'data', 'particle_drill'))
LANGUAGES = {3: 'ja'}          # language_id -> content directory
CONJUGATION_LEXICONS = ('verbs', 'adjectives')

_lock = threading.Lock()
_cache: Dict[str, 'Content'] = {}


def _read_json(path: str, default=None):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default


def _read_jsonl(path: str) -> List[dict]:
    rows = []
    try:
        with open(path, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    except FileNotFoundError:
        pass
    return rows


def skill_files(root: str, sub: str, skill_id: str, ext: str) -> List[str]:
    """``<skill>.<ext>`` and its part files ``<skill>__*.<ext>``, in name order."""
    base = os.path.join(root, sub)
    paths = glob.glob(os.path.join(base, f'{glob.escape(skill_id)}__*.{ext}'))
    whole = os.path.join(base, f'{skill_id}.{ext}')
    return ([whole] if os.path.exists(whole) else []) + sorted(paths)


def item_id(jp: str) -> str:
    """Stable short id of an item: survives rebuilds while the text is unchanged."""
    return hashlib.sha1(jp.encode('utf-8')).hexdigest()[:10]


class Content:
    """One language's catalog, guides, exercise bank, packs and lexicon."""

    def __init__(self, root: str):
        self.root = root
        self.catalog = _read_json(os.path.join(root, 'catalog.json')) or {'stages': [], 'skills': []}
        self.skills = {s['id']: s for s in self.catalog['skills']}
        self.groups = {g['id']: g for st in self.catalog['stages'] for g in st['groups']}
        self._guides: Dict[str, Optional[dict]] = {}
        self._items: Dict[str, List[dict]] = {}
        self._packs: Dict[str, List[dict]] = {}
        self._conjugation: Optional[dict] = None
        self._counts: Optional[Dict[str, Dict[str, int]]] = None
        self._lock = threading.Lock()

    # -- per-skill content -------------------------------------------------
    def items(self, skill_id: str) -> List[dict]:
        if skill_id not in self._items:
            rows, seen = [], set()
            for path in skill_files(self.root, 'items', skill_id, 'jsonl'):
                for row in _read_jsonl(path):
                    row['id'] = item_id(row.get('jp', ''))
                    if row['id'] not in seen:       # the same sentence in two parts
                        seen.add(row['id'])
                        rows.append(row)
            self._items[skill_id] = rows
        return self._items[skill_id]

    def packs(self, skill_id: str) -> List[dict]:
        if skill_id not in self._packs:
            self._packs[skill_id] = _read_json(os.path.join(self.root, 'packs', f'{skill_id}.json')) or []
        return self._packs[skill_id]

    def guide(self, group_id: str) -> Optional[dict]:
        if group_id not in self._guides:
            self._guides[group_id] = _read_json(os.path.join(self.root, 'guides', f'{group_id}.json'))
        return self._guides[group_id]

    def skill_guide(self, skill_id: str) -> Optional[dict]:
        """The skill's own guide section plus its group's intro."""
        skill = self.skills.get(skill_id)
        guide = self.guide(skill['group']) if skill else None
        if not guide:
            return None
        for section in guide.get('skills') or []:
            if section.get('id') == skill_id:
                return {**section, 'intro': guide.get('intro', '')}
        return None

    # -- payloads ----------------------------------------------------------
    def counts(self) -> Dict[str, Dict[str, int]]:
        """{skill_id: {'items': n, 'packs': n}} from the manifest, else counted."""
        if self._counts is None:
            manifest = _read_json(os.path.join(self.root, 'manifest.json')) or {}
            counts = manifest.get('skills')
            if not isinstance(counts, dict):
                counts = {sid: {'items': len(self.items(sid)), 'packs': len(self.packs(sid))}
                          for sid in self.skills}
            self._counts = counts
        return self._counts

    def version(self) -> str:
        manifest = _read_json(os.path.join(self.root, 'manifest.json')) or {}
        return str(manifest.get('version') or self.catalog.get('version') or '0')

    def catalog_payload(self) -> dict:
        counts = self.counts()
        skills = []
        for s in self.catalog['skills']:
            c = counts.get(s['id']) or {}
            skills.append({'id': s['id'], 'group': s['group'], 'stage': s['stage'], 'p': s['p'],
                           'title': s['title'], 'lv': s['lv'],
                           'items': int(c.get('items') or 0), 'packs': int(c.get('packs') or 0)})
        return {'version': self.version(), 'stages': self.catalog['stages'], 'skills': skills}

    def skill_payload(self, skill_id: str) -> Optional[dict]:
        skill = self.skills.get(skill_id)
        if not skill:
            return None
        group = self.groups.get(skill['group']) or {}
        return {
            'skill': {k: skill[k] for k in ('id', 'group', 'stage', 'p', 'title', 'lv', 'conf')},
            'group': {'id': group.get('id'), 'p': group.get('p'), 'name': group.get('name'),
                      'skills': group.get('skills', [])},
            'guide': self.skill_guide(skill_id),
            'items': self.items(skill_id),
            'packs': self.packs(skill_id),
        }

    def conjugation_payload(self) -> dict:
        with self._lock:
            if self._conjugation is None:
                base = os.path.join(self.root, 'conjugation')
                self._conjugation = {'guide': _read_json(os.path.join(base, 'guide.json')) or []}
                for name in CONJUGATION_LEXICONS:        # verbs_n5.json, verbs_n4.json, ...
                    words, seen = [], set()
                    for path in sorted(glob.glob(os.path.join(base, f'{name}*.json'))):
                        for word in _read_json(path) or []:
                            key = (word.get('d'), word.get('k'))
                            if key not in seen:
                                seen.add(key)
                                words.append(word)
                    self._conjugation[name] = words
            return self._conjugation


def get_content(language_id: int) -> Optional[Content]:
    """The content for a language id, or None when the drill has none for it."""
    code = LANGUAGES.get(language_id)
    if not code:
        return None
    with _lock:
        if code not in _cache:
            _cache[code] = Content(os.path.join(DATA_ROOT, code))
        return _cache[code]


def reset_cache() -> None:
    """Drop the in-memory content (tests, and after a rebuild in a live process)."""
    with _lock:
        _cache.clear()
