class CollocationPackService:
    """
    Create and manage collocation packs from corpus sources.
    A pack is a curated, user-browsable set of collocations.
    """

    DEFAULT_TOP_N          = 100
    DEFAULT_MIN_PMI        = 3.0

    def __init__(self, db):
        """
        Args:
            db: Supabase client instance.
        """
        self.db = db

    def create_pack_from_corpus(
        self,
        corpus_source_id: int,
        pack_name: str,
        description: str,
        pack_type: str,
        language_id: int,
        top_n: int = DEFAULT_TOP_N,
        min_pmi: float = DEFAULT_MIN_PMI,
    ) -> int:
        """
        Create a collocation pack from the highest-PMI collocations of a
        corpus source.

        Returns:
            int: pack_id of the new collocation_packs row.
        Raises:
            ValueError: If no qualifying collocations exist for the source.
        """
        # Prefer validated collocations; fall back to all if none verified yet
        collocations = (
            self.db.table('corpus_collocations')
            .select('id, collocation_text, pmi_score, collocation_type')
            .eq('corpus_source_id', corpus_source_id)
            .eq('is_validated', True)
            .gte('pmi_score', min_pmi)
            .order('lmi_score', desc=True)
            .limit(top_n)
            .execute()
        )

        if not collocations.data:
            # Fallback: no verified collocations yet, use unfiltered
            collocations = (
                self.db.table('corpus_collocations')
                .select('id, collocation_text, pmi_score, collocation_type')
                .eq('corpus_source_id', corpus_source_id)
                .gte('pmi_score', min_pmi)
                .order('lmi_score', desc=True)
                .limit(top_n)
                .execute()
            )

        if not collocations.data:
            raise ValueError(
                f"No collocations with pmi >= {min_pmi} "
                f"for corpus_source_id={corpus_source_id}"
            )

        source = (
            self.db.table('corpus_sources')
            .select('tags')
            .eq('id', corpus_source_id)
            .single()
            .execute()
            .data
        )
        tags = source.get('tags', [])

        pack = self.db.table('collocation_packs').insert({
            'pack_name':   pack_name,
            'description': description,
            'language_id': language_id,
            'tags':        tags,
            'source_type': 'corpus',
            'pack_type':   pack_type,
            'total_items': len(collocations.data),
            'is_public':   True,
        }).execute()
        pack_id = pack.data[0]['id']

        joins = [
            {'pack_id': pack_id, 'collocation_id': c['id']}
            for c in collocations.data
        ]
        for i in range(0, len(joins), 500):
            self.db.table('pack_collocations').insert(joins[i : i + 500]).execute()

        return pack_id

    def create_cross_source_pack(
        self,
        source_ids: list[int],
        pack_name: str,
        description: str,
        pack_type: str,
        language_id: int,
        top_n: int = DEFAULT_TOP_N,
        min_pmi: float = DEFAULT_MIN_PMI,
    ) -> int:
        """
        Create a pack from the highest-PMI collocations across multiple sources.
        Uses the get_top_collocations_for_sources RPC.

        Returns:
            int: pack_id.
        Raises:
            ValueError: If source_ids is empty or no qualifying collocations found.
        """
        if not source_ids:
            raise ValueError("source_ids must be non-empty")

        result = self.db.rpc(
            'get_top_collocations_for_sources',
            {
                'p_source_ids': source_ids,
                'p_min_pmi':    min_pmi,
                'p_top_n':      top_n,
            }
        ).execute()

        if not result.data:
            raise ValueError("No qualifying collocations found for supplied sources")

        pack = self.db.table('collocation_packs').insert({
            'pack_name':   pack_name,
            'description': description,
            'language_id': language_id,
            'tags':        [],
            'source_type': 'corpus',
            'pack_type':   pack_type,
            'total_items': len(result.data),
            'is_public':   True,
        }).execute()
        pack_id = pack.data[0]['id']

        joins = [
            {'pack_id': pack_id, 'collocation_id': row['id']}
            for row in result.data
        ]
        for i in range(0, len(joins), 500):
            self.db.table('pack_collocations').insert(joins[i : i + 500]).execute()

        return pack_id

    def get_packs_for_user(
        self,
        language_id: int,
        user_id: str
    ) -> list[dict]:
        """
        Return all public collocation packs for a language, annotated with
        whether the user has selected each pack.

        Uses the get_packs_with_user_selection RPC.
        """
        result = self.db.rpc(
            'get_packs_with_user_selection',
            {'p_language_id': language_id, 'p_user_id': user_id}
        ).execute()
        return result.data or []

    def select_pack(self, user_id: str, pack_id: int) -> None:
        """
        Upsert a user_pack_selections row for the given user and pack.
        Idempotent — safe to call if the user has already selected the pack.
        """
        self.db.table('user_pack_selections').upsert({
            'user_id': user_id,
            'pack_id': pack_id,
        }).execute()
