"""Validator for the grammar-drill course (data/particle_drill/ja-grammar).

The same checks and options as scripts/particle_drill_validate.py, pointed at
the grammar course:

    python scripts/grammar_drill_validate.py items/pt-tekudasai.jsonl
    python scripts/grammar_drill_validate.py --summary
"""
import os
import sys

os.environ['PD_COURSE'] = 'ja-grammar'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import particle_drill_validate  # noqa: E402

if __name__ == '__main__':
    sys.exit(particle_drill_validate.main())
