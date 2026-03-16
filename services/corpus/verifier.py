"""
Verification layer for corpus_collocations.
Adds substitution entropy — an MLM-based lexical resistance score.

Lower entropy = model is confident only specific words fit = stronger collocation.
Higher entropy = many substitutes possible = likely a productive pattern, not a collocation.

Run after ingestion via:
    python Corpuses/verify_collocations.py --language english --limit 500
"""
import math

# Lazy imports — heavy deps only loaded when this module is used
_mlm_pipelines = {}

# Per-model mask tokens (most BERT models use [MASK], RoBERTa uses <mask>)
_MASK_TOKENS = {
    1: '[MASK]',     # bert-base-chinese
    2: '<mask>',     # roberta-base
    3: '[MASK]',     # cl-tohoku/bert-base-japanese
}


def _get_mlm(language_id: int):
    """Load (and cache) the fill-mask pipeline for a language."""
    if language_id not in _mlm_pipelines:
        from transformers import pipeline as hf_pipeline
        model_map = {
            1: 'bert-base-chinese',
            2: 'roberta-base',
            3: 'cl-tohoku/bert-base-japanese-whole-word-masking',
        }
        model = model_map.get(language_id)
        if not model:
            raise ValueError(f"No MLM configured for language_id={language_id}")
        _mlm_pipelines[language_id] = hf_pipeline(
            'fill-mask', model=model, top_k=15, device=-1  # CPU
        )
    return _mlm_pipelines[language_id]


def substitution_entropy(
    collocation_text: str,
    language_id: int,
) -> float:
    """
    Average Shannon entropy of the MLM's probability distribution when
    each position in the collocation is masked in turn.

    Lower entropy = model is confident only specific words fit = stronger collocation.
    Higher entropy = many substitutes possible = likely a productive pattern.

    Args:
        collocation_text: The n-gram string (space-separated for EN/JA, no-space for ZH).
        language_id:      1=ZH, 2=EN, 3=JA.
    Returns:
        float: Mean entropy across all masked positions. Range: 0.0 (frozen) to ~3.9 (random).
    """
    mlm = _get_mlm(language_id)
    mask_token = _MASK_TOKENS.get(language_id, '[MASK]')

    # For Chinese: treat each character as a position
    # For EN/JA: split on spaces
    tokens = list(collocation_text) if language_id == 1 else collocation_text.split()

    if len(tokens) < 2:
        return 0.0

    entropies = []
    for i in range(len(tokens)):
        masked_tokens = tokens[:]
        masked_tokens[i] = mask_token
        masked_text = ''.join(masked_tokens) if language_id == 1 else ' '.join(masked_tokens)

        try:
            results = mlm(masked_text)
            probs = [r['score'] for r in results]
            total = sum(probs)
            if total == 0:
                continue
            probs = [p / total for p in probs]
            entropy = -sum(p * math.log2(p) for p in probs if p > 0)
            entropies.append(entropy)
        except Exception:
            continue  # Skip positions where masking fails (e.g. subword issues)

    return round(sum(entropies) / len(entropies), 4) if entropies else 0.0


def is_worth_keeping(
    substitution_entropy_score: float,
    pmi_score: float,
    entropy_threshold: float = 2.8,
    pmi_floor: float = 2.0,
) -> bool:
    """
    Combined gate: a collocation is worth keeping if it has:
      - Low substitution entropy (lexically restricted), AND
      - PMI above the floor (statistically associated)

    Thresholds are tuneable. Start with entropy_threshold=2.8:
      - Entropy ~0-1.5: near-frozen phrases (大相径庭, make a decision)
      - Entropy ~1.5-2.8: restricted collocations (提出建议, economic growth)
      - Entropy >2.8: productive patterns (半导体行业 — any industry noun fits)
    """
    return substitution_entropy_score < entropy_threshold and pmi_score >= pmi_floor
