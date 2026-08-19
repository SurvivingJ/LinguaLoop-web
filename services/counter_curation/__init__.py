"""Offline LLM-assisted curation of Japanese counter (助数詞) content.

The Japanese sibling of :mod:`services.classifier_curation`. An *authoring*
tool: it uses a Qwen model via OpenRouter to propose nouns + example phrases for
a counter, judges each pairing, and writes per-counter JSON for human review.
Nothing here runs at request time — ``get_counter_drill_session`` stays fully
deterministic.

Two failure modes are specific to Japanese counters and are modelled explicitly
rather than left for the reviewer to catch by eye:

* **Counters that count no noun.** 階 counts storeys; the counted thing is the
  floor itself, not a noun a learner could be shown. Asking a model for "nouns
  that take 階" reliably produces 建物/ビル, which are counted with 棟 — a
  plausible-looking answer that is simply wrong. ``CounterMeta.counts_nouns``
  lets the model decline, and a decline is recorded as a result rather than an
  empty failure.
* **Placeholder counters.** Not everything in the counters table is a real
  counter. ``CounterMeta.is_real_counter`` is a separate flag so "this is not a
  counter" and "this counter has no nouns" stay distinguishable in review.
"""
