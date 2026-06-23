"""Unit tests for the dual-translation model router (TASK-600).

LLM-free and DB-free: every test mocks the router's two boundaries —
``get_template_config`` (the prompt_templates lookup) and ``fetch_model_list``
(the OpenRouter /models re-verification call) — exactly like the vocab-ladder
judge tests mock the same `services.prompt_service` boundary. Nothing here
touches Supabase or OpenRouter.
"""

import pytest

from services.dual_translation import router


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_router_cache():
    """The router caches prompt_templates rows per (tier, language_id); clear
    around every test so mocks from one test never leak into the next."""
    router.clear_caches()
    yield
    router.clear_caches()


def _cfg_for(mapping: dict[tuple[str, int], dict]):
    """Build a `get_template_config(db, task_name, language_id)` stand-in.

    `mapping` keys are (task_name, language_id); missing keys raise
    RuntimeError, mirroring the real prompt_service contract for an unseeded
    row.
    """
    def _get(db, task_name, language_id):
        key = (task_name, language_id)
        if key not in mapping:
            raise RuntimeError(f"no active prompt_templates row for {key}")
        return mapping[key]
    return _get


def _listed(*slugs: str):
    """Build a `fetch_model_list()` stand-in returning the given slugs as
    OpenRouter /models entries."""
    return lambda **kwargs: [{'id': s} for s in slugs]


# ---------------------------------------------------------------------------
# Basic resolution
# ---------------------------------------------------------------------------

def test_resolve_tier_returns_configured_slug_when_listed(monkeypatch):
    monkeypatch.setattr(router, 'get_template_config', _cfg_for({
        ('dual_translation_tier2', 2): {'model': 'google/gemini-3.5-flash', 'provider': 'openrouter', 'template': 'x', 'version': 1},
    }))
    monkeypatch.setattr(router, 'fetch_model_list', _listed('google/gemini-3.5-flash'))

    route = router.resolve_tier(db=None, tier='tier2', language_id=2)

    assert route.slug == 'google/gemini-3.5-flash'
    assert route.used_tier == 'tier2'
    assert route.requested_tier == 'tier2'
    assert route.fell_open is False
    assert route.reason is None


def test_resolve_tier_routes_en_to_gemini_zh_to_qwen(monkeypatch):
    """The split between Gemini (EN) and Qwen (ZH/JA) lives entirely in the
    prompt_templates data the router reads — never a code constant. This
    threads two different per-language configs through the same tier to
    prove the router is purely data-driven."""
    monkeypatch.setattr(router, 'get_template_config', _cfg_for({
        ('dual_translation_tier1', 2): {'model': 'google/gemini-2.5-flash-lite', 'provider': 'openrouter', 'template': 'x', 'version': 1},
        ('dual_translation_tier1', 1): {'model': 'qwen/qwen3.6-flash', 'provider': 'openrouter', 'template': 'x', 'version': 1},
        ('dual_translation_tier1', 3): {'model': 'qwen/qwen3.6-flash', 'provider': 'openrouter', 'template': 'x', 'version': 1},
    }))
    monkeypatch.setattr(router, 'fetch_model_list', _listed(
        'google/gemini-2.5-flash-lite', 'qwen/qwen3.6-flash',
    ))

    en = router.resolve_tier(db=None, tier='tier1', language_id=2)
    zh = router.resolve_tier(db=None, tier='tier1', language_id=1)
    ja = router.resolve_tier(db=None, tier='tier1', language_id=3)

    assert en.slug == 'google/gemini-2.5-flash-lite'
    assert zh.slug == 'qwen/qwen3.6-flash'
    assert ja.slug == 'qwen/qwen3.6-flash'


def test_resolve_tier_unknown_tier_raises():
    with pytest.raises(ValueError):
        router.resolve_tier(db=None, tier='tier99', language_id=2)


def test_resolve_tier_skip_verification_short_circuits(monkeypatch):
    calls = {'n': 0}

    def _boom(**kwargs):
        calls['n'] += 1
        raise AssertionError('fetch_model_list should not be called when verify=False')

    monkeypatch.setattr(router, 'get_template_config', _cfg_for({
        ('dual_translation_tier1', 2): {'model': 'google/gemini-2.5-flash-lite', 'provider': 'openrouter', 'template': 'x', 'version': 1},
    }))
    monkeypatch.setattr(router, 'fetch_model_list', _boom)

    route = router.resolve_tier(db=None, tier='tier1', language_id=2, verify=False)

    assert route.slug == 'google/gemini-2.5-flash-lite'
    assert calls['n'] == 0


def test_resolve_tier_caches_prompt_template_lookup(monkeypatch):
    calls = {'n': 0}

    def _get(db, task_name, language_id):
        calls['n'] += 1
        return {'model': 'qwen/qwen3.7-plus', 'provider': 'openrouter', 'template': 'x', 'version': 1}

    monkeypatch.setattr(router, 'get_template_config', _get)
    monkeypatch.setattr(router, 'fetch_model_list', _listed('qwen/qwen3.7-plus'))

    router.resolve_tier(db=None, tier='tier2', language_id=1)
    router.resolve_tier(db=None, tier='tier2', language_id=1)

    assert calls['n'] == 1


# ---------------------------------------------------------------------------
# Fail-open on a delisted / 404'd slug
# ---------------------------------------------------------------------------

def test_resolve_tier_falls_open_to_previous_tier_on_simulated_404(monkeypatch):
    """tier2's configured slug has been delisted (absent from OpenRouter's
    live model list — the same signature as a 404 calling that model). The
    router must fall open to tier1 and report the slug it actually used, not
    the dead tier2 slug, so grader_trace stays honest."""
    monkeypatch.setattr(router, 'get_template_config', _cfg_for({
        ('dual_translation_tier2', 1): {'model': 'qwen/qwen-max', 'provider': 'openrouter', 'template': 'x', 'version': 1},
        ('dual_translation_tier1', 1): {'model': 'qwen/qwen3.6-flash', 'provider': 'openrouter', 'template': 'x', 'version': 1},
    }))
    # qwen/qwen-max is NOT in the live list -> simulates the delisting.
    monkeypatch.setattr(router, 'fetch_model_list', _listed('qwen/qwen3.6-flash'))

    route = router.resolve_tier(db=None, tier='tier2', language_id=1)

    assert route.requested_tier == 'tier2'
    assert route.used_tier == 'tier1'
    assert route.slug == 'qwen/qwen3.6-flash'
    assert route.fell_open is True
    assert route.reason is not None

    trace_entry = route.as_trace_entry()
    assert trace_entry['slug'] == 'qwen/qwen3.6-flash'
    assert trace_entry['tier'] == 'tier1'
    assert trace_entry['fell_open'] is True


def test_resolve_tier_falls_open_through_tier3_to_tier1(monkeypatch):
    """A multi-step fall-open: tier3's slug is delisted AND tier2's row is
    missing entirely; only tier1 is usable."""
    monkeypatch.setattr(router, 'get_template_config', _cfg_for({
        ('dual_translation_tier3', 2): {'model': 'google/gemini-dead-slug', 'provider': 'openrouter', 'template': 'x', 'version': 1},
        ('dual_translation_tier1', 2): {'model': 'google/gemini-2.5-flash-lite', 'provider': 'openrouter', 'template': 'x', 'version': 1},
        # tier2 has no row at all for language_id=2 in this fixture.
    }))
    monkeypatch.setattr(router, 'fetch_model_list', _listed('google/gemini-2.5-flash-lite'))

    route = router.resolve_tier(db=None, tier='tier3', language_id=2)

    assert route.used_tier == 'tier1'
    assert route.slug == 'google/gemini-2.5-flash-lite'
    assert route.fell_open is True


def test_resolve_tier_falls_open_to_tier0_when_nothing_usable(monkeypatch):
    """Every paid tier is delisted/unseeded — never hard-fail; signal Tier 0
    deterministic marks instead."""
    monkeypatch.setattr(router, 'get_template_config', _cfg_for({
        ('dual_translation_tier2', 3): {'model': 'qwen/qwen-max', 'provider': 'openrouter', 'template': 'x', 'version': 1},
        ('dual_translation_tier1', 3): {'model': 'qwen/qwen-also-dead', 'provider': 'openrouter', 'template': 'x', 'version': 1},
    }))
    monkeypatch.setattr(router, 'fetch_model_list', _listed())  # nothing listed

    route = router.resolve_tier(db=None, tier='tier2', language_id=3)

    assert route.used_tier == 'tier0'
    assert route.slug is None
    assert route.fell_open is True


def test_resolve_tier_model_list_fetch_failure_assumes_slug_valid(monkeypatch):
    """If the verification call itself fails (network/API outage), the
    router must not treat that as a delisting and must not fall open."""
    monkeypatch.setattr(router, 'get_template_config', _cfg_for({
        ('dual_translation_tier1', 2): {'model': 'google/gemini-2.5-flash-lite', 'provider': 'openrouter', 'template': 'x', 'version': 1},
    }))

    def _raise(**kwargs):
        raise ConnectionError('openrouter unreachable')

    monkeypatch.setattr(router, 'fetch_model_list', _raise)

    route = router.resolve_tier(db=None, tier='tier1', language_id=2)

    assert route.slug == 'google/gemini-2.5-flash-lite'
    assert route.fell_open is False
