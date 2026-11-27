"""Check the particle-drill content and write its manifest.

    python scripts/particle_drill_build.py            # check and report (writes nothing)
    python scripts/particle_drill_build.py --apply    # also write data/particle_drill/ja/manifest.json

The manifest holds the item and pack count of every skill (the hub shows them
without reading the exercise files) and a content version: a hash of every
content file, used as the HTTP cache key of the content routes. Run it after
any change under data/particle_drill/ja/. It refuses to write while the
validator reports errors.
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import particle_drill_validate as validate  # noqa: E402
from services.particle_drill.content import Content  # noqa: E402

CONTENT_DIRS = ('items', 'packs', 'guides', 'conjugation', 'reading')


def content_files(root):
    paths = [os.path.join(root, 'catalog.json')]
    for sub in CONTENT_DIRS:
        d = os.path.join(root, sub)
        if os.path.isdir(d):
            paths += sorted(os.path.join(d, f) for f in os.listdir(d)
                            if f.endswith('.json') or f.endswith('.jsonl'))
    return paths


def content_version(root):
    digest = hashlib.sha1()
    for path in content_files(root):
        digest.update(os.path.relpath(path, root).encode('utf-8'))
        with open(path, 'rb') as fh:
            digest.update(fh.read())
    return digest.hexdigest()[:12]


def build_manifest(root):
    content = Content(root)
    skills = {sid: {'items': len(content.items(sid)), 'packs': len(content.packs(sid))}
              for sid in content.skills}
    conj = content.conjugation_payload()
    guides = sum(1 for gid in content.groups if content.guide(gid))
    katakana = len(content.reading_payload()['katakana'])
    return {
        'version': content_version(root),
        'totals': {
            **({'katakana': katakana} if katakana else {}),
            'skills': len(skills),
            'skills_with_items': sum(1 for c in skills.values() if c['items']),
            'items': sum(c['items'] for c in skills.values()),
            'packs': sum(c['packs'] for c in skills.values()),
            'guides': guides,
            'groups': len(content.groups),
            'verbs': len(conj['verbs']),
            'adjectives': len(conj['adjectives']),
            'conjugation_guides': len(conj['guide']),
        },
        'skills': skills,
    }


def validation_errors(root):
    catalog = validate.load_catalog(root)
    skills = {s['id']: s for s in catalog['skills']}
    errs = []
    for path in content_files(root)[1:]:
        kind = os.path.basename(os.path.dirname(path))
        if kind == 'items':
            errs += validate.check_items_file(path, skills)[0]
        elif kind == 'packs':
            errs += validate.check_packs_file(path, skills)[0]
        elif kind == 'guides':
            errs += validate.check_guide_file(path, catalog)
        elif kind == 'reading':
            errs += validate.check_katakana_file(path)[0]
        elif not os.path.basename(path).startswith('guide'):
            errs += validate.check_lexicon_file(path)[0]
    return errs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true', help='write manifest.json')
    ap.add_argument('--root', default=validate.ROOT)
    args = ap.parse_args()
    errs = validation_errors(args.root)
    for e in errs[:50]:
        print(e)
    manifest = build_manifest(args.root)
    print(json.dumps(manifest['totals'], indent=1), 'version', manifest['version'])
    if errs:
        print(f'{len(errs)} validation errors: manifest not written')
        return 1
    if args.apply:
        path = os.path.join(args.root, 'manifest.json')
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write('\n')
        print('wrote', path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
