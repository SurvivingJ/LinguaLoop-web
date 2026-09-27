"""TASK-812 (Part C) — every render-judge `call_llm` site has an explicit cap.

Regression guard, source-level: `collocation_judge` used to have NO
`max_tokens` at all (a worst-case runaway completion was billed and
latency'd in full), and several others carried a stale cap sized from a
handful of pilot rows rather than the TASK-808 baseline. This pins "every
call_llm(...) call in these six judge modules names max_tokens explicitly"
so a future refactor -- or a new judge copy-pasted from one of these --
can't silently drop back to unbounded.

Source inspection rather than a mocked call, per the plan: constructing a
valid fixture per judge (six different template/candidate shapes) to reach
the call site would be much more code for the same guarantee, and this
survives a judge being refactored to call `call_llm` from a helper as long
as the call text itself is still visible in the module source.
"""

import inspect

from services.exercise_generation.judges import (
    cloze, collocation, l1_distractor, particle, relation, sentence_validity,
)


def _call_llm_blocks(module) -> list[str]:
    """Every `call_llm(...)` call expression in `module`'s source, whole.

    A regex anchored on the first `)` would stop inside a nested call (e.g.
    `_LANG_ID_TO_CODE.get(language_id)`), so this tracks paren depth instead.
    """
    source = inspect.getsource(module)
    blocks = []
    idx = 0
    needle = 'call_llm('
    while True:
        start = source.find(needle, idx)
        if start == -1:
            break
        depth = 1
        j = start + len(needle)
        while depth > 0 and j < len(source):
            if source[j] == '(':
                depth += 1
            elif source[j] == ')':
                depth -= 1
            j += 1
        blocks.append(source[start:j])
        idx = j
    return blocks


_JUDGE_MODULES = [
    sentence_validity, cloze, l1_distractor, relation, particle, collocation,
]


def test_every_judge_module_calls_call_llm_at_least_once():
    """Sanity check on the extraction itself, so a broken helper fails loud
    rather than every module silently reporting zero call sites (which would
    make the real assertion below vacuously true)."""
    for module in _JUDGE_MODULES:
        assert _call_llm_blocks(module), f'found no call_llm(...) site in {module.__name__}'


def test_every_judge_call_llm_site_has_an_explicit_max_tokens_cap():
    missing = []
    for module in _JUDGE_MODULES:
        for block in _call_llm_blocks(module):
            if 'max_tokens=' not in block:
                missing.append(module.__name__)
    assert not missing, (
        f'call_llm site(s) with no explicit max_tokens cap in: {missing}'
    )


def test_collocation_judge_is_no_longer_unbounded():
    """The specific regression this task exists for: collocation_judge had
    literally no max_tokens kwarg at its call_llm site."""
    blocks = _call_llm_blocks(collocation)
    assert len(blocks) == 1
    assert 'max_tokens=' in blocks[0]


def test_sentence_validity_cap_was_lowered_from_the_stale_19000():
    """19000 was never re-derived from real data; TASK-808's baseline (p99
    5247 over 94 real calls) grounds the new cap instead."""
    blocks = _call_llm_blocks(sentence_validity)
    assert 'max_tokens=19000' not in blocks[0]
    assert 'max_tokens=' in blocks[0]
