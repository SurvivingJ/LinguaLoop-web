"""TASK-983 — static guard: no exercise insert or content change outside the store.

ADR-047 §4: **all INSERTs into ``exercises`` and all changes to ``content`` go
through ``store.write_sense``** (in ``dual`` mode it writes the content file
first and commits the rows by compare-and-swap; a direct write would leave rows
whose content no file holds). DELETEs and metadata-only UPDATEs (``is_active``,
``irt_*``, counts, ``tags``) may stay direct.

The scanner reads every ``*.py`` under ``services/``, ``routes/``,
``scripts/``, ``utils/`` and ``web/`` except ``services/exercise_content/``
(the store itself) and flags:

* a ``table('exercises')`` / ``table("exercises")`` (or ``from_(...)``) chain,
  up to its ``.execute()`` and across lines, that calls ``.insert(`` or
  ``.upsert(``, or ``.update(`` with an argument that mentions ``content``
  (``content_version`` does not count); also the same calls on a name the bare
  ``table('exercises')`` builder was assigned to;
* string literals (adjacent literals joined, f-string text included) matching
  ``INSERT INTO [public.]exercises`` or ``UPDATE [public.]exercises ... SET
  ... content =`` (case-insensitive).

It works on Python tokens, so comments and prose inside strings never look like
calls. ``ALLOWLIST`` (path -> reason) is the only way to exempt a file; it is
empty, and an entry that no longer matches anything fails the suite.
"""

from __future__ import annotations

import ast
import io
import re
import token
import tokenize
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ('services', 'routes', 'scripts', 'utils', 'web')
EXCLUDED_PREFIXES = ('services/exercise_content/',)

#: path (repo-relative, POSIX) -> why that file may write content directly.
ALLOWLIST: dict[str, str] = {}

TABLE_METHODS = frozenset({'table', 'from_'})
WRITE_METHODS = frozenset({'insert', 'upsert'})
_MENTIONS_CONTENT = re.compile(r'content(?!_version)', re.IGNORECASE)

_TABLE = r'(?:"?public"?\s*\.\s*)?"?exercises"?(?![\w"])'
SQL_PATTERNS = (
    ('sql-insert', re.compile(r'\bINSERT\s+INTO\s+' + _TABLE, re.IGNORECASE)),
    ('sql-update-content', re.compile(
        r'\bUPDATE\s+(?:ONLY\s+)?' + _TABLE
        + r'[^;]*?\bSET\b(?:(?!\bWHERE\b|\bFROM\b|\bRETURNING\b|;).)*?'
          r'(?:\bcontent\b|"content")\s*=',
        re.IGNORECASE | re.DOTALL)),
)

_FSTRING_START = getattr(token, 'FSTRING_START', None)
_FSTRING_MIDDLE = getattr(token, 'FSTRING_MIDDLE', None)
_FSTRING_END = getattr(token, 'FSTRING_END', None)
_SKIPPED = {tokenize.COMMENT, tokenize.NL}
_STATEMENT_START = {tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str      # insert | upsert | update-content | sql-insert | sql-update-content | unparseable
    text: str

    def __str__(self) -> str:
        return f'{self.path}:{self.line}: {self.kind}: {self.text}'


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def _is_op(tok, value: str) -> bool:
    return tok.type == tokenize.OP and tok.string == value


def _string_value(tok) -> str:
    try:
        value = ast.literal_eval(tok.string)
    except (ValueError, SyntaxError):
        return tok.string
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace')
    return value if isinstance(value, str) else tok.string


def _close_paren(toks, start: int) -> int:
    """Index of the bracket closing the one at ``start`` (or the last token)."""
    depth = 0
    for k in range(start, len(toks)):
        if toks[k].type == tokenize.OP:
            if toks[k].string in '([{':
                depth += 1
            elif toks[k].string in ')]}':
                depth -= 1
                if depth == 0:
                    return k
    return len(toks) - 1


def _args_text(toks, open_idx: int, close_idx: int) -> str:
    return ' '.join(t.string for t in toks[open_idx + 1:close_idx])


def _is_exercises_base(toks, i: int) -> bool:
    """``toks[i]`` starts ``table('exercises')`` / ``from_("exercises")``."""
    if not (toks[i].type == tokenize.NAME and toks[i].string in TABLE_METHODS):
        return False
    if i + 3 >= len(toks) or not _is_op(toks[i + 1], '(') or not _is_op(toks[i + 3], ')'):
        return False
    arg = toks[i + 2]
    return arg.type == tokenize.STRING and _string_value(arg) == 'exercises'


def _method_findings(path, toks, name_idx: int, lines: list[str]) -> list[Finding]:
    """A ``.<method>(...)`` call at ``toks[name_idx]`` -> findings (insert/upsert/update)."""
    method = toks[name_idx].string
    if name_idx + 1 >= len(toks) or not _is_op(toks[name_idx + 1], '('):
        return []
    line = toks[name_idx].start[0]
    text = lines[line - 1].strip() if line - 1 < len(lines) else ''
    if method in WRITE_METHODS:
        return [Finding(path, line, method, text)]
    if method == 'update':
        close = _close_paren(toks, name_idx + 1)
        if _MENTIONS_CONTENT.search(_args_text(toks, name_idx + 1, close)):
            return [Finding(path, line, 'update-content', text)]
    return []


def _walk_chain(path, toks, start: int, lines: list[str]) -> tuple[int, list[Finding], bool]:
    """Walk ``(. NAME [(...)])*`` from ``start`` up to ``.execute()``.

    Returns (index after the chain, findings, whether any method followed the base).
    """
    findings: list[Finding] = []
    j = start
    had_method = False
    while j + 1 < len(toks) and _is_op(toks[j], '.') and toks[j + 1].type == tokenize.NAME:
        had_method = True
        name_idx = j + 1
        findings += _method_findings(path, toks, name_idx, lines)
        j = name_idx + 1
        if j < len(toks) and _is_op(toks[j], '('):
            j = _close_paren(toks, j) + 1
        if toks[name_idx].string == 'execute':
            break
    return j, findings, had_method


def _assigned_alias(toks, base_idx: int) -> str | None:
    """``alias = <dotted.receiver>.table('exercises')`` as a whole statement -> 'alias'."""
    j = base_idx - 1
    if j < 1 or not _is_op(toks[j], '.'):
        return None
    j -= 1
    while j >= 2 and toks[j].type == tokenize.NAME and _is_op(toks[j - 1], '.'):
        j -= 2
    if toks[j].type != tokenize.NAME:
        return None
    if j < 2 or not _is_op(toks[j - 1], '=') or toks[j - 2].type != tokenize.NAME:
        return None
    if j >= 3 and toks[j - 3].type not in _STATEMENT_START:
        return None
    return toks[j - 2].string


def _alias_findings(path, toks, alias: str, start: int, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for k in range(start, len(toks) - 2):
        if toks[k].type != tokenize.NAME or toks[k].string != alias:
            continue
        if _is_op(toks[k + 1], '=') and not (
                toks[k + 2].type == tokenize.NAME and toks[k + 2].string == alias):
            break      # rebound to something else
        if _is_op(toks[k + 1], '.') and toks[k + 2].type == tokenize.NAME:
            findings += _walk_chain(path, toks, k + 1, lines)[1]
    return findings


def _literal_groups(toks):
    """Yield (line, text) per run of adjacent string literals (f-string text included)."""
    k = 0
    while k < len(toks):
        tok = toks[k]
        if tok.type != tokenize.STRING and tok.type != _FSTRING_START:
            k += 1
            continue
        line, parts = tok.start[0], []
        while k < len(toks) and (toks[k].type == tokenize.STRING
                                 or toks[k].type == _FSTRING_START):
            if toks[k].type == tokenize.STRING:
                parts.append(_string_value(toks[k]))
                k += 1
                continue
            depth = 0
            while k < len(toks):
                t = toks[k]
                if t.type == _FSTRING_START:
                    depth += 1
                elif t.type == _FSTRING_END:
                    depth -= 1
                    if depth == 0:
                        k += 1
                        break
                elif t.type == _FSTRING_MIDDLE:
                    parts.append(t.string)
                elif _is_op(t, '{'):
                    parts.append('{}')
                k += 1
        yield line, ''.join(parts)


def scan_source(source: str, path: str = '<snippet>') -> list[Finding]:
    lines = source.splitlines()
    try:
        toks = [t for t in tokenize.generate_tokens(io.StringIO(source).readline)
                if t.type not in _SKIPPED]
    except (tokenize.TokenError, SyntaxError) as exc:
        return [Finding(path, 0, 'unparseable', str(exc))]

    findings: list[Finding] = []
    for i in range(len(toks)):
        if not _is_exercises_base(toks, i):
            continue
        end, chain_findings, had_method = _walk_chain(path, toks, i + 4, lines)
        findings += chain_findings
        if not had_method:
            alias = _assigned_alias(toks, i)
            if alias:
                findings += _alias_findings(path, toks, alias, end, lines)

    for line, text in _literal_groups(toks):
        for kind, pattern in SQL_PATTERNS:
            match = pattern.search(text)
            if match:
                findings.append(Finding(path, line, kind, match.group(0)[:120]))
    return sorted(set(findings), key=lambda f: (f.path, f.line, f.kind))


def iter_scanned_files(root: Path = ROOT):
    for folder in SCAN_DIRS:
        base = root / folder
        if not base.is_dir():
            continue
        for file in sorted(base.rglob('*.py')):
            rel = file.relative_to(root).as_posix()
            if '__pycache__' in file.parts or rel.startswith(EXCLUDED_PREFIXES):
                continue
            yield rel, file


def scan_repo(root: Path = ROOT) -> list[Finding]:
    findings: list[Finding] = []
    for rel, file in iter_scanned_files(root):
        findings += scan_source(file.read_text(encoding='utf-8'), rel)
    return findings


# ---------------------------------------------------------------------------
# The repository
# ---------------------------------------------------------------------------

def test_no_exercise_content_write_outside_the_store():
    offending = [f for f in scan_repo() if f.path not in ALLOWLIST]
    assert offending == [], (
        'ADR-047 §4: inserts into exercises and content changes go through '
        'services.exercise_content.store.write_sense:\n'
        + '\n'.join(str(f) for f in offending))


def test_allowlist_entries_are_justified_and_still_needed():
    assert isinstance(ALLOWLIST, dict)
    findings_by_path = {f.path for f in scan_repo()}
    for path, reason in ALLOWLIST.items():
        assert isinstance(reason, str) and reason.strip(), f'{path}: give a reason'
        assert (ROOT / path).is_file(), f'{path}: allowlisted file does not exist'
        assert path in findings_by_path, f'{path}: allowlisted but no longer flagged; remove it'


def test_the_scan_covers_the_writers_and_skips_only_the_store():
    scanned = {rel for rel, _ in iter_scanned_files()}
    assert len(scanned) > 100
    for writer in ('services/vocabulary_ladder/exercise_renderer.py',
                   'services/vocabulary_ladder/queue_drain.py',
                   'scripts/run_generation_batch.py', 'scripts/exercise_stage_runner.py',
                   'scripts/backfill_exercise_audio.py', 'scripts/backfill_hant_mirrors.py',
                   'routes/vocab_admin.py'):
        assert writer in scanned
    assert not any(rel.startswith('services/exercise_content/') for rel in scanned)


def test_the_store_itself_would_be_flagged():
    """Proves the exclusion matters: the db-mode write path is the very pattern guarded."""
    source = (ROOT / 'services/exercise_content/store.py').read_text(encoding='utf-8')
    kinds = {f.kind for f in scan_source(source, 'services/exercise_content/store.py')}
    assert {'insert', 'update-content'} <= kinds


# ---------------------------------------------------------------------------
# The scanner, on synthetic snippets
# ---------------------------------------------------------------------------

OFFENDING = {
    'insert one line': ("self.db.table('exercises').insert(rows).execute()\n", 'insert'),
    'upsert multi-line parenthesised': (
        'x = (db.table("exercises")\n'
        "       .upsert(rows, on_conflict='id')\n"
        '       .execute())\n', 'upsert'),
    'update content dict': (
        "db.table('exercises').update({'content': new}).eq('id', i).execute()\n",
        'update-content'),
    'update content multi-line (old audio backfill)': (
        "self.db.table('exercises').update(\n"
        "    {'content': content}\n"
        ").eq('id', row['id']).execute()\n", 'update-content'),
    'update with a content variable': (
        "db.table('exercises').update(new_content).eq('id', i).execute()\n",
        'update-content'),
    'backslash continuation': (
        "db.table('exercises') \\\n    .insert(rows) \\\n    .execute()\n", 'insert'),
    'insert after filters and a comment line': (
        "(db.table('exercises')\n"
        '   # replace the set\n'
        "   .insert(rows)\n"
        '   .execute())\n', 'insert'),
    'query built across statements': (
        "q = db.table('exercises').update({'content': c})\n"
        "q = q.eq('id', 1)\n"
        'q.execute()\n', 'update-content'),
    'aliased builder': (
        "t = self.db.table('exercises')\n"
        "t.insert(rows).execute()\n", 'insert'),
    'aliased builder, update content later': (
        "def f(db, c):\n"
        "    t = db.table('exercises')\n"
        "    t.eq('id', 1)\n"
        "    t.update({'content': c}).eq('id', 1).execute()\n", 'update-content'),
    'from_ alias of table': ("db.from_('exercises').insert(rows).execute()\n", 'insert'),
    'sql insert': (
        'SQL = "INSERT INTO public.exercises (id, content) VALUES (%s, %s)"\n', 'sql-insert'),
    'sql insert lower case': ("sql = 'insert into exercises (id) values (1)'\n", 'sql-insert'),
    'sql insert implicit concatenation': (
        'sql = ("INSERT INTO "\n       "exercises (id) VALUES (1)")\n', 'sql-insert'),
    'sql insert f-string': (
        'sql = f"INSERT INTO exercises ({cols}) VALUES ({vals})"\n', 'sql-insert'),
    'sql update set content': (
        "q = '''UPDATE exercises\n   SET content = %s\n WHERE id = %s'''\n",
        'sql-update-content'),
    'sql update content among other columns': (
        'q = "UPDATE public.exercises SET is_active = true, content = $1 WHERE id = $2"\n',
        'sql-update-content'),
    'sql update quoted names': (
        'q = \'UPDATE "public"."exercises" SET "content" = $1\'\n', 'sql-update-content'),
}

CLEAN = {
    'delete chain': (
        "db.table('exercises').delete().eq('word_sense_id', s)"
        ".not_.is_('word_asset_id', 'null').execute()\n"),
    'metadata update': (
        "db.table('exercises').update({'is_active': False}).in_('id', ids).execute()\n"),
    'update from a variable (attempt counters)': (
        "query = self.db.table('exercises').update(updates).eq('id', exercise_id)\n"),
    'content_version update': (
        "db.table('exercises').update({'content_version': 3}).eq('id', 1).execute()\n"),
    'select with content': (
        "db.table('exercises').select('id, content').eq('id', 1).execute()\n"),
    'select filtered on content in a later statement': (
        "rows = db.table('exercises').select('id').execute().data\n"
        "db.table('word_assets').update({'content': c}).eq('id', 1).execute()\n"),
    'other tables': (
        "db.table('exercise_attempts').insert(row).execute()\n"
        "db.table('word_assets').update({'content': c}).execute()\n"
        "db.table('exercises_archive').insert(rows).execute()\n"),
    'chain ends at execute (same line)': (
        "db.table('exercises').update({'is_active': False}).execute(); "
        "db.table('calibration_anchor_blocklist').insert(rows).execute()\n"),
    'chain ends at execute (next line)': (
        "db.table('exercises').update({'is_active': False}).in_('id', ids).execute()\n"
        "db.table('calibration_anchor_blocklist').insert(\n    rows).execute()\n"),
    'comment': ("# db.table('exercises').insert(rows).execute()\nx = 1\n"),
    'prose in a docstring': (
        '"""Never call db.table(\'exercises\').insert(rows) directly; '
        'Inserts into exercises go through the store."""\n'),
    'store call': ("store.write_sense(db, s, lang, insert_rows=rows)\n"),
    'sql content_version update': ("q = 'UPDATE exercises SET content_version = 1'\n"),
    'sql metadata update': (
        "q = 'UPDATE public.exercises SET is_active = false WHERE content IS NULL'\n"),
    'sql select': ("q = 'SELECT content FROM public.exercises WHERE id = $1'\n"),
    'sql other table': ("q = 'INSERT INTO exercises_archive SELECT * FROM exercises'\n"),
    'alias rebound before the write': (
        "t = db.table('exercises')\n"
        "t = db.table('word_assets')\n"
        "t.insert(rows).execute()\n"),
    'alias used for reads only': (
        "t = db.table('exercises')\n"
        "rows = t.select('id').execute().data\n"),
}


@pytest.mark.parametrize('name', sorted(OFFENDING))
def test_scanner_flags_offending_snippet(name):
    source, kind = OFFENDING[name]
    findings = scan_source(source)
    assert [f.kind for f in findings] == [kind], findings
    assert findings[0].line >= 1


@pytest.mark.parametrize('name', sorted(CLEAN))
def test_scanner_passes_clean_snippet(name):
    assert scan_source(CLEAN[name]) == []


def test_scanner_reports_the_line_of_the_offending_call():
    source = ("x = 1\n"
              "(db.table('exercises')\n"
              "   .delete().eq('word_sense_id', 1)\n"
              "   .execute())\n"
              "(db.table('exercises')\n"
              "   .insert(rows)\n"
              "   .execute())\n")
    assert [(f.line, f.kind) for f in scan_source(source, 'x.py')] == [(6, 'insert')]
    assert str(scan_source(source, 'x.py')[0]).startswith('x.py:6: insert: ')


def test_scanner_flags_the_pre_store_writers():
    """The calls TASK-980/981/982 replaced would all have been caught."""
    old = {
        'renderer': "        self.db.table('exercises').insert(rows).execute()\n",
        'queue_drain': (
            "delete_query = (\n"
            "    db.table('exercises').delete()\n"
            "    .eq('word_sense_id', sense_id)\n"
            "    .not_.is_('word_asset_id', 'null')\n"
            ")\n"
            "delete_query.execute()\n"
            "db.table('exercises').insert(new_rows).execute()\n"),
        'hant': ("db.table('exercises').update(\n"
                 "    {'content': new_content}).eq('id', r['id']).execute()\n"),
    }
    for name, source in old.items():
        assert scan_source(source), name


def test_unparseable_source_is_reported_not_skipped():
    findings = scan_source('x = (\n', 'broken.py')
    assert [f.kind for f in findings] == ['unparseable']
