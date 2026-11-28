#!/usr/bin/env python3
"""Say what a language still needs before it can go live.

    python scripts/check_language.py            # every registered language, one line each
    python scripts/check_language.py it         # the full checklist for one language

Reads code and files only (services/language_readiness.py); the database
steps are printed for a person to verify. Exits 1 when the named language
fails a required check.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services import language_readiness, language_registry  # noqa: E402


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        for lang in language_registry.all_languages(include_planned=True):
            results = language_readiness.report(lang)
            req = [r for r in results if r.level == language_readiness.REQUIRED]
            opt = [r for r in results if r.level == language_readiness.OPTIONAL]
            print(f'{lang.id} {lang.code} {lang.display:<10} {lang.status:<8} '
                  f'required {sum(r.ok for r in req)}/{len(req)}, optional {sum(r.ok for r in opt)}/{len(opt)}')
        return 0
    try:
        lang = language_registry.get(argv[0], include_planned=True)
    except KeyError as exc:
        print(exc.args[0])
        print('Add it to services/language_registry.py first.')
        return 2
    print(f'{lang.display} (id {lang.id}, code {lang.code}, {lang.status}, {lang.script} script'
          f'{", features: " + ", ".join(sorted(lang.features)) if lang.features else ""})')
    failed = 0
    for r in language_readiness.report(lang):
        mark = 'ok     ' if r.ok else ('MISSING' if r.level == language_readiness.REQUIRED else 'default')
        print(f'  [{mark}] {r.level:<8} {r.what}')
        if not r.ok:
            print(f'            {r.detail}')
            print(f'            -> {r.where}')
            failed += r.level == language_readiness.REQUIRED
    print('  In the database (not checked here):')
    for step in language_readiness.DATABASE_STEPS:
        print(f'    - {step}')
    if lang.status == language_registry.PLANNED:
        print(f'  Then set status=ACTIVE for {lang.code!r} in services/language_registry.py and run '
              'scripts/build_language_registry_js.py.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
