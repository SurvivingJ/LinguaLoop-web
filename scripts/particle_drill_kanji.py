"""Write compound particles in their normal kanji spelling, with furigana.

    python scripts/particle_drill_kanji.py            # report what would change
    python scripts/particle_drill_kanji.py --apply    # rewrite the files

Slot answers and distractors may be kana or kanji with furigana
(``{に対[たい]して|nitaishite}``). Content written while slots were kana-only
has にたいして where a reader expects に対して. This rewrites exactly those
answers: a whole slot answer, a whole alternative, or a whole distractor that
equals a kana spelling in ``KANJI_FORMS``. Sentence text outside slots is
never touched. Idempotent. Run scripts/particle_drill_build.py afterwards.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import particle_drill_validate as validate  # noqa: E402
from services.particle_drill import markup  # noqa: E402

# Marked spelling of every compound particle that is normally written with kanji.
MARKED = [
    'に対[たい]して', 'に関[かん]して', 'に比[くら]べて', 'を通[とお]して', 'を通[つう]じて',
    'に沿[そ]って', 'に基[もと]づいて', 'に加[くわ]えて', 'に従[したが]って', 'に伴[ともな]って',
    'に応[おう]じて', 'に反[はん]して', 'を問[と]わず', 'に限[かぎ]らず', 'に限[かぎ]って',
    'に限[かぎ]り', 'を中心[ちゅうしん]に', 'に際[さい]して', '際[さい]に', 'に先立[さきだ]って',
    'に続[つづ]いて', '上[うえ]で', '上[うえ]に', '上[うえ]は', 'や否[いな]や', 'が早[はや]いか',
    'を皮切[かわき]りに', 'を限[かぎ]りに', 'を機[き]に', 'を境[さかい]に', 'を除[のぞ]いて',
]
KANJI_FORMS = {markup.reading_of(m): m for m in MARKED}
_SLOT_RE = re.compile(r'\{([^{}|]*)((?:\|[^{}]*)?)\}')


def fix_answer(answer):
    return KANJI_FORMS.get(answer, answer)


def fix_text(text):
    """Rewrite slot answers inside marked-up text. Returns (text, changes)."""
    changes = 0

    def repl(m):
        nonlocal changes
        answers = [a.strip() for a in m.group(1).split('/')]
        fixed = [fix_answer(a) for a in answers]
        if fixed == answers:
            return m.group(0)
        changes += 1
        return '{' + '/'.join(fixed) + m.group(2) + '}'

    return _SLOT_RE.sub(repl, text), changes


def fix_value(value):
    """Rewrite every marked-up string in a JSON value. Returns (value, changes)."""
    if isinstance(value, str):
        return fix_text(value)
    if isinstance(value, list):
        out, total = [], 0
        for v in value:
            v2, n = fix_value(v)
            out.append(v2)
            total += n
        return out, total
    if isinstance(value, dict):
        out, total = {}, 0
        for k, v in value.items():
            if k == 'd' and isinstance(v, list):
                fixed = [fix_answer(x) if isinstance(x, str) else x for x in v]
                total += sum(1 for a, b in zip(v, fixed) if a != b)
                out[k] = fixed
            elif k in ('en', 'why', 'note', 'rule', 'explain', 'tip', 'intro', 'title'):
                out[k] = v                      # prose, never markup
            else:
                out[k], n = fix_value(v)
                total += n
        return out, total
    return value, 0


def process(path, apply):
    total = 0
    if path.endswith('.jsonl'):
        lines = []
        with open(path, encoding='utf-8') as fh:
            for line in fh:
                if not line.strip():
                    continue
                row, n = fix_value(json.loads(line))
                total += n
                lines.append(json.dumps(row, ensure_ascii=False) if n else line.rstrip('\n'))
        if apply and total:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write('\n'.join(lines) + '\n')
    else:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
        data, total = fix_value(data)
        if apply and total:
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(data, fh, ensure_ascii=False, indent=1)
                fh.write('\n')
    return total


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true', help='rewrite the files')
    ap.add_argument('--root', default=validate.ROOT)
    args = ap.parse_args()
    files = changed = total = 0
    for sub in ('items', 'packs', 'guides'):
        d = os.path.join(args.root, sub)
        for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if not (name.endswith('.json') or name.endswith('.jsonl')):
                continue
            files += 1
            n = process(os.path.join(d, name), args.apply)
            if n:
                changed += 1
                total += n
                print(f'{sub}/{name}: {n}')
    print(f'{files} files, {changed} with kana-only compound particles, {total} answers '
          f'{"rewritten" if args.apply else "to rewrite (use --apply)"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
