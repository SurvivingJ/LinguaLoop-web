"""Offline LLM-assisted curation of Mandarin measure-word (classifier) content.

This package is an *authoring* tool: it uses an LLM (qwen via OpenRouter) to
propose noun + example-sentence content for classifiers, validates it, and
writes per-classifier JSON for human review. Nothing here runs at request time;
the drill's runtime (get_classifier_drill_session) stays fully deterministic.
"""
