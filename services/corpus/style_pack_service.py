"""
Style pack creation and management.

Materialises learnable items from a corpus_style_profiles row into
style_pack_items, then bundles them into a collocation_packs row
(pack_type='style') linked via pack_style_items.
"""

import logging

logger = logging.getLogger(__name__)


# Default item counts per category in a style pack
_PACK_COMPOSITION = {
    'frequent_ngram':       20,
    'characteristic_ngram': 15,
    'sentence_pattern':     10,
    'syntactic_feature':     5,
    'discourse_pattern':     5,
    'vocabulary_item':       5,
}


class StylePackService:
    """
    Create and manage style packs from corpus style profiles.
    """

    def __init__(self, db):
        self.db = db

    def create_pack_from_profile(
        self,
        corpus_source_id: int,
        pack_name: str,
        description: str,
        language_id: int,
    ) -> int:
        """
        Create a style pack from an existing style profile.

        1. Loads the corpus_style_profiles row.
        2. Materialises top items into style_pack_items.
        3. Creates a collocation_packs row (pack_type='style').
        4. Links items via pack_style_items.

        Returns:
            int: pack_id of the new pack.
        Raises:
            ValueError: If no style profile exists for the source.
        """
        # Load profile
        result = (
            self.db.table('corpus_style_profiles')
            .select('*')
            .eq('corpus_source_id', corpus_source_id)
            .execute()
        )
        if not result.data:
            raise ValueError(
                f"No style profile found for corpus_source_id={corpus_source_id}. "
                "Run style analysis first."
            )
        profile = result.data[0]

        # Materialise items
        items = self._materialise_items(profile, corpus_source_id, language_id)
        if not items:
            raise ValueError("Style profile produced no learnable items.")

        # Batch insert style_pack_items
        inserted_ids = []
        for i in range(0, len(items), 500):
            batch_result = (
                self.db.table('style_pack_items')
                .insert(items[i:i + 500])
                .execute()
            )
            inserted_ids.extend(row['id'] for row in batch_result.data)

        # Get source tags
        source = (
            self.db.table('corpus_sources')
            .select('tags')
            .eq('id', corpus_source_id)
            .single()
            .execute()
            .data
        )
        tags = source.get('tags', []) if source else []

        # Create the pack
        pack = self.db.table('collocation_packs').insert({
            'pack_name':   pack_name,
            'description': description,
            'language_id': language_id,
            'tags':        tags,
            'source_type': 'corpus',
            'pack_type':   'style',
            'total_items': len(inserted_ids),
            'is_public':   True,
        }).execute()
        pack_id = pack.data[0]['id']

        # Link items to pack
        joins = [
            {'pack_id': pack_id, 'style_item_id': item_id}
            for item_id in inserted_ids
        ]
        for i in range(0, len(joins), 500):
            self.db.table('pack_style_items').insert(joins[i:i + 500]).execute()

        logger.info(
            f"Created style pack '{pack_name}' (pack_id={pack_id}) "
            f"with {len(inserted_ids)} items"
        )
        return pack_id

    def _materialise_items(
        self,
        profile: dict,
        corpus_source_id: int,
        language_id: int,
    ) -> list[dict]:
        """
        Extract learnable items from a style profile's JSONB columns.
        Returns a list of style_pack_items rows ready for insertion.
        """
        items = []
        sort_order = 0

        # ── Frequent n-grams (mix of sizes 2-4) ──
        raw_ngrams = profile.get('raw_frequency_ngrams') or {}
        limit = _PACK_COMPOSITION['frequent_ngram']
        collected = []
        for n in ['2', '3', '4']:
            for entry in (raw_ngrams.get(n) or []):
                collected.append(entry)
        # Sort by frequency descending, take top N
        collected.sort(key=lambda x: x.get('frequency', 0), reverse=True)
        for entry in collected[:limit]:
            sort_order += 1
            items.append({
                'corpus_source_id': corpus_source_id,
                'language_id': language_id,
                'item_type': 'frequent_ngram',
                'item_text': entry['text'],
                'item_data': entry,
                'frequency': entry.get('frequency', 0),
                'keyness_score': 0.0,
                'sort_order': sort_order,
            })

        # ── Characteristic n-grams (highest keyness) ──
        char_ngrams = profile.get('characteristic_ngrams') or []
        limit = _PACK_COMPOSITION['characteristic_ngram']
        for entry in char_ngrams[:limit]:
            sort_order += 1
            items.append({
                'corpus_source_id': corpus_source_id,
                'language_id': language_id,
                'item_type': 'characteristic_ngram',
                'item_text': entry['text'],
                'item_data': entry,
                'frequency': entry.get('author_freq', 0),
                'keyness_score': entry.get('keyness_score', 0.0),
                'sort_order': sort_order,
            })

        # ── Sentence patterns (with examples) ──
        structures = profile.get('sentence_structures') or {}
        patterns = structures.get('patterns') or []
        limit = _PACK_COMPOSITION['sentence_pattern']
        for entry in patterns[:limit]:
            sort_order += 1
            items.append({
                'corpus_source_id': corpus_source_id,
                'language_id': language_id,
                'item_type': 'sentence_pattern',
                'item_text': entry['template'],
                'item_data': entry,
                'frequency': entry.get('frequency', 0),
                'keyness_score': 0.0,
                'sort_order': sort_order,
            })

        # ── Syntactic features (as descriptive items) ──
        syntactic = profile.get('syntactic_preferences') or {}
        limit = _PACK_COMPOSITION['syntactic_feature']
        synth_items = []
        for key, value in syntactic.items():
            if key in ('total_sentences_analyzed',):
                continue
            if isinstance(value, (int, float)) and value > 0:
                synth_items.append({
                    'feature': key,
                    'value': value,
                })
        # Sort by value descending (most prominent features first)
        synth_items.sort(key=lambda x: x['value'], reverse=True)
        for entry in synth_items[:limit]:
            sort_order += 1
            label = entry['feature'].replace('_', ' ').replace(' ratio', '')
            items.append({
                'corpus_source_id': corpus_source_id,
                'language_id': language_id,
                'item_type': 'syntactic_feature',
                'item_text': label,
                'item_data': entry,
                'frequency': 0,
                'keyness_score': 0.0,
                'sort_order': sort_order,
            })

        # ── Discourse patterns (top transitions) ──
        discourse = profile.get('discourse_patterns') or {}
        transitions = discourse.get('top_transitions') or []
        limit = _PACK_COMPOSITION['discourse_pattern']
        for entry in transitions[:limit]:
            sort_order += 1
            items.append({
                'corpus_source_id': corpus_source_id,
                'language_id': language_id,
                'item_type': 'discourse_pattern',
                'item_text': entry['text'],
                'item_data': entry,
                'frequency': entry.get('frequency', 0),
                'keyness_score': 0.0,
                'sort_order': sort_order,
            })

        # ── Vocabulary items (distinctive words from keyness, unigram) ──
        limit = _PACK_COMPOSITION['vocabulary_item']
        unigram_keyness = [
            e for e in char_ngrams if e.get('n_gram_size') == 1
        ]
        for entry in unigram_keyness[:limit]:
            sort_order += 1
            items.append({
                'corpus_source_id': corpus_source_id,
                'language_id': language_id,
                'item_type': 'vocabulary_item',
                'item_text': entry['text'],
                'item_data': entry,
                'frequency': entry.get('author_freq', 0),
                'keyness_score': entry.get('keyness_score', 0.0),
                'sort_order': sort_order,
            })

        return items

    def get_style_packs(self, language_id: int) -> list[dict]:
        """
        List all public style packs for a language.
        """
        result = (
            self.db.table('collocation_packs')
            .select('*')
            .eq('pack_type', 'style')
            .eq('language_id', language_id)
            .eq('is_public', True)
            .order('created_at', desc=True)
            .execute()
        )
        return result.data or []

    def get_pack_items(self, pack_id: int) -> list[dict]:
        """
        Get all style items for a pack, ordered by sort_order.
        """
        result = (
            self.db.table('pack_style_items')
            .select('style_item_id, style_pack_items(*)')
            .eq('pack_id', pack_id)
            .execute()
        )
        if not result.data:
            return []

        items = [row['style_pack_items'] for row in result.data if row.get('style_pack_items')]
        items.sort(key=lambda x: x.get('sort_order', 0))
        return items
