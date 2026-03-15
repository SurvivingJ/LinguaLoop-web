# services/exercise_generation/generators/verb_noun_match.py

from services.exercise_generation.base_generator import ExerciseGenerator


class VerbNounMatchGenerator(ExerciseGenerator):
    """
    Generates verb_noun_match grid exercises from corpus_collocations.
    No LLM. Queries VERB+NOUN pairs with PMI >= 3.0 for a corpus source.
    """

    exercise_type = 'verb_noun_match'
    source_type   = 'collocation'

    MIN_GRID_VERBS: int = 2
    MIN_GRID_NOUNS: int = 2
    PMI_THRESHOLD:  float = 3.0

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        col_row = self.db.table('corpus_collocations') \
            .select('corpus_source_id, language_id') \
            .eq('id', source_id).single().execute().data
        if not col_row:
            return None

        pairs = self._fetch_verb_noun_pairs(
            col_row['corpus_source_id'], col_row['language_id']
        )
        if not pairs:
            return None

        verbs      = list(dict.fromkeys(p[0] for p in pairs))
        nouns      = list(dict.fromkeys(p[1] for p in pairs))
        valid_pairs = [
            [verbs.index(v), nouns.index(n)] for v, n in pairs
            if v in verbs and n in nouns
        ]

        if len(verbs) < self.MIN_GRID_VERBS or len(nouns) < self.MIN_GRID_NOUNS:
            return None

        return {
            'verbs':            verbs,
            'nouns':            nouns,
            'valid_pairs':      valid_pairs,
            'corpus_source_id': col_row['corpus_source_id'],
        }

    def _fetch_verb_noun_pairs(
        self, corpus_source_id: int, language_id: int
    ) -> list[tuple[str, str]]:
        result = self.db.rpc('get_verb_noun_pairs', {
            'p_corpus_source_id': corpus_source_id,
            'p_language_id':      language_id,
            'p_pmi_threshold':    self.PMI_THRESHOLD,
        }).execute()
        return [(r['verb_phrase'], r['noun_phrase']) for r in (result.data or [])]
