import logging
import re
import httpx
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from services.corpus.tokenizers import get_tokenizer
from services.corpus.analyzer import CorpusAnalyzer
from services.corpus.classifier import CollocationClassifier
from services.corpus.style_analyzer import StyleAnalyzer
from services.corpus.collocation_validator import validate_collocations, MIN_PEDAGOGICAL_SCORE
from services.corpus.collocation_tagger import tag_collocations
from services.corpus.style_narrative import generate_narrative
from services.vocabulary.language_detection import check_text_language

logger = logging.getLogger(__name__)

# Language ID → language code used by check_text_language
_LANG_ID_TO_CODE = {1: 'cn', 2: 'en', 3: 'jp'}


class CorpusIngestionService:
    """
    Orchestrates ingestion of text from URLs, paste, transcripts, or author corpora.
    Composes CorpusAnalyzer and CollocationClassifier.
    """

    INLINE_TEXT_WORD_LIMIT = 50_000

    FETCH_TIMEOUT_SECONDS = 30
    HTTP_HEADERS = {
        'User-Agent': 'LinguaLoop-Corpus-Bot/1.0'
    }

    def __init__(self, db):
        """
        Args:
            db: Supabase client instance.
        """
        self.db = db

    def ingest_url(
        self,
        url: str,
        language_id: int,
        tags: list[str],
        analyze_style: bool = False,
        llm_enhance: bool = False,
    ) -> int:
        """
        Fetch a web page, extract main text, run corpus analysis pipeline.
        Removes <nav>, <footer>, <aside>, <script>, <style>, <header> before
        text extraction. Prefers <article> or <main> over full <body>.

        Returns:
            int: corpus_source_id of the newly created row.
        Raises:
            httpx.HTTPStatusError: On non-2xx HTTP response.
            ValueError: If no extractable text found.
        """
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=self.FETCH_TIMEOUT_SECONDS,
            headers=self.HTTP_HEADERS
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        for tag in soup(['nav', 'footer', 'aside', 'script', 'style', 'header']):
            tag.decompose()

        main = soup.find('article') or soup.find('main') or soup.body
        raw_text = main.get_text(separator=' ', strip=True) if main else soup.get_text()
        raw_text = re.sub(r'\s+', ' ', raw_text).strip()

        if not raw_text:
            raise ValueError(f"No extractable text at URL: {url}")

        title = soup.title.string.strip() if soup.title and soup.title.string else url

        return self._run_pipeline(
            raw_text=raw_text,
            source_type='url',
            source_url=url,
            source_title=title,
            language_id=language_id,
            tags=tags,
            analyze_style=analyze_style,
            llm_enhance=llm_enhance,
        )

    def ingest_text(
        self,
        text: str,
        title: str,
        language_id: int,
        tags: list[str],
        analyze_style: bool = False,
        llm_enhance: bool = False,
    ) -> int:
        """
        Ingest a plain text string directly (e.g. pasted by admin in UI).
        Returns:
            int: corpus_source_id.
        """
        raw_text = re.sub(r'\s+', ' ', text).strip()
        return self._run_pipeline(
            raw_text=raw_text,
            source_type='text',
            source_url=None,
            source_title=title,
            language_id=language_id,
            tags=tags,
            analyze_style=analyze_style,
            llm_enhance=llm_enhance,
        )

    def ingest_author_corpus(
        self,
        author_name: str,
        texts: list[str],
        language_id: int,
        extra_tags: list[str] | None = None,
        analyze_style: bool = False,
        llm_enhance: bool = False,
    ) -> int:
        """
        Ingest multiple public-domain texts attributed to one author as a
        single combined corpus source.

        Concatenating before analysis means collocations that appear across
        multiple works (author's idiolect markers) will cross the threshold.

        Returns:
            int: corpus_source_id.
        """
        combined = '\n\n'.join(texts)
        author_slug = author_name.lower().replace(' ', '_')
        tags = [f'author_{author_slug}', 'literature']
        if extra_tags:
            tags.extend(extra_tags)

        return self._run_pipeline(
            raw_text=combined,
            source_type='author',
            source_url=None,
            source_title=author_name,
            language_id=language_id,
            tags=tags,
            analyze_style=analyze_style,
            llm_enhance=llm_enhance,
        )

    def ingest_transcripts(
        self,
        language_id: int,
        extra_tags: list[str] | None = None,
        analyze_style: bool = False,
        llm_enhance: bool = False,
    ) -> int:
        """
        Build a corpus from all active test transcripts for a language.

        Concatenates every non-empty transcript from the tests table where
        language_id matches and is_active=True, then runs the full pipeline.
        This gives the best collocation coverage because it analyses the
        exact text that learners are already studying.

        Args:
            language_id: 1=ZH, 2=EN, 3=JA.
            extra_tags:  Additional tags beyond the auto-generated ones.
        Returns:
            int: corpus_source_id.
        Raises:
            ValueError: If no transcripts found for the language.
        """
        lang_name = _LANG_ID_TO_CODE.get(language_id, str(language_id))

        # Fetch all active transcripts for this language
        result = (
            self.db.table('tests')
            .select('transcript')
            .eq('language_id', language_id)
            .eq('is_active', True)
            .execute()
        )

        transcripts = [
            row['transcript']
            for row in (result.data or [])
            if row.get('transcript') and row['transcript'].strip()
        ]

        if not transcripts:
            raise ValueError(
                f"No active transcripts found for language_id={language_id}"
            )

        combined = '\n\n'.join(transcripts)
        tags = [f'transcripts_{lang_name}', 'internal']
        if extra_tags:
            tags.extend(extra_tags)

        logger.info(
            f"Ingesting {len(transcripts)} transcripts for language_id={language_id} "
            f"({len(combined):,} chars)"
        )

        return self._run_pipeline(
            raw_text=combined,
            source_type='text',
            source_url=None,
            source_title=f'All {lang_name.upper()} transcripts ({len(transcripts)} tests)',
            language_id=language_id,
            tags=tags,
            analyze_style=analyze_style,
            llm_enhance=llm_enhance,
        )

    @staticmethod
    def _passes_language_check(collocation_text: str, language_id: int) -> bool:
        """
        Verify a collocation is actually in the expected language.
        Rejects e.g. English acronyms ("GDP", "CEO") appearing as Chinese collocations,
        or CJK characters leaking into English results.
        """
        lang_code = _LANG_ID_TO_CODE.get(language_id)
        if not lang_code:
            return True  # unknown language — can't validate, let it through
        is_valid, _ = check_text_language(collocation_text, lang_code)
        return is_valid

    @staticmethod
    def _is_named_entity(
        collocation_text: str,
        head_word: str,
        entity_set: set[str],
    ) -> bool:
        """
        Check whether a collocation is a named entity (company name, place
        name, person name, etc.) that should be excluded.

        Matches when:
        - The full collocation text is an entity, OR
        - The head word (first token) is an entity.
        """
        if collocation_text in entity_set or head_word in entity_set:
            return True
        return False

    def _run_pipeline(
        self,
        raw_text: str,
        source_type: str,
        source_url: str | None,
        source_title: str,
        language_id: int,
        tags: list[str],
        analyze_style: bool = False,
        llm_enhance: bool = False,
    ) -> int:
        """
        Core pipeline: store source -> analyse -> classify -> insert collocations
        -> mark processed.

        When llm_enhance=True, additional LLM-powered steps run after
        statistical extraction:
          - Discourse marker discovery (reclassifies n-grams)
          - Pedagogical validation (scores 1-5, filters low-value)
          - Semantic tagging (domain/theme tags)

        Chunk size of 500 rows per insert matches Supabase recommended batch size.

        Returns:
            int: corpus_source_id of the inserted corpus_sources row.
        """
        word_count = len(raw_text.split())

        # 1. Insert corpus_sources row
        source_result = self.db.table('corpus_sources').insert({
            'source_type':   source_type,
            'source_url':    source_url,
            'source_title':  source_title,
            'language_id':   language_id,
            'tags':          tags,
            'raw_text':      raw_text if word_count < self.INLINE_TEXT_WORD_LIMIT else None,
            'raw_text_path': None,
            'word_count':    word_count,
            'processed_at':  None,
        }).execute()
        corpus_source_id = source_result.data[0]['id']

        # 2. Analyse text
        tokenizer  = get_tokenizer(language_id)
        analyzer   = CorpusAnalyzer(tokenizer)
        classifier = CollocationClassifier(tokenizer)

        scored = analyzer.score_ngrams(raw_text)

        # Tag n-gram results with extraction method
        for item in scored:
            item['extraction_method'] = 'ngram'
            item['dependency_relation'] = None

        # Extract dependency-based collocations (non-adjacent syntactic pairs)
        dep_scored = analyzer.score_dependency_pairs(raw_text)
        if dep_scored:
            logger.info(f"Found {len(dep_scored)} dependency-based collocations")
            # Merge, deduplicating: keep n-gram version if same text exists in both
            seen_texts = {item['collocation_text'] for item in scored}
            for dep_item in dep_scored:
                if dep_item['collocation_text'] not in seen_texts:
                    scored.append(dep_item)
                    seen_texts.add(dep_item['collocation_text'])

        # 2b. Extract named entities from the full text (once) for filtering
        entity_set = tokenizer.extract_named_entities(raw_text)
        if entity_set:
            logger.info(
                f"Found {len(entity_set)} named entities to filter "
                f"(e.g. {list(entity_set)[:5]})"
            )

        # 3. Enrich with classification, filtering out wrong-language
        #    collocations, named entities, and structurally invalid patterns
        rows = []
        filtered_count = 0
        ner_filtered_count = 0
        pos_filtered_count = 0
        stoplist_filtered_count = 0
        for item in scored:
            # Reject structurally invalid collocations (quote anchors, scaffold nouns)
            tokens = list(item['collocation_text']) if language_id == 1 else item['collocation_text'].split()
            if not classifier.is_valid_collocation(tokens):
                stoplist_filtered_count += 1
                continue

            # Reject collocations that aren't in the expected language
            if not self._passes_language_check(item['collocation_text'], language_id):
                filtered_count += 1
                continue

            # Reject named entities (company names, place names, etc.)
            if entity_set and self._is_named_entity(
                item['collocation_text'], item['head_word'], entity_set
            ):
                ner_filtered_count += 1
                continue

            classification = classifier.classify_and_tag(
                text=item['collocation_text'],
                pmi=item['pmi_score'],
                frequency=item['frequency'],
                n=item['n_gram_size'],
            )

            # Drop structurally invalid POS patterns (e.g. NOUN+VERB+NOUN spanning clause boundary)
            # Discourse markers and fixed phrases are exempt — they have non-standard patterns by nature
            if (classification['collocation_type'] == 'collocation'
                    and not classifier.is_valid_pattern(classification['pos_pattern'])):
                pos_filtered_count += 1
                continue

            rows.append({
                'corpus_source_id': corpus_source_id,
                'language_id':      language_id,
                'collocation_text': item['collocation_text'],
                'head_word':        item['head_word'],
                'collocate':        item['collocate'],
                'n_gram_size':      item['n_gram_size'],
                'frequency':        item['frequency'],
                'pmi_score':        item['pmi_score'],
                'log_likelihood':   item['log_likelihood'],
                't_score':          item['t_score'],
                'lmi_score':        item['lmi_score'],
                'collocation_type':    classification['collocation_type'],
                'pos_pattern':         classification['pos_pattern'],
                'extraction_method':   item.get('extraction_method', 'ngram'),
                'dependency_relation': item.get('dependency_relation', None),
                'tags':                tags,
                'is_validated':        None,
            })

        if filtered_count:
            logger.info(
                f"Filtered {filtered_count} wrong-language collocations "
                f"(language_id={language_id})"
            )
        if ner_filtered_count:
            logger.info(
                f"Filtered {ner_filtered_count} named-entity collocations "
                f"(language_id={language_id})"
            )
        if pos_filtered_count:
            logger.info(
                f"Filtered {pos_filtered_count} structurally invalid collocations "
                f"(language_id={language_id})"
            )
        if stoplist_filtered_count:
            logger.info(
                f"Filtered {stoplist_filtered_count} stoplist collocations "
                f"(language_id={language_id})"
            )

        # 4. LLM enhancement steps (optional)
        if llm_enhance and rows:
            # 4a. Discourse marker discovery — reclassify n-grams that
            #     the LLM identifies as discourse markers
            try:
                discovered_markers = classifier.discover_discourse_markers(rows)
                if discovered_markers:
                    reclassified = 0
                    for row in rows:
                        if (row['collocation_text'].lower() in discovered_markers
                                and row['collocation_type'] != 'discourse_marker'):
                            row['collocation_type'] = 'discourse_marker'
                            reclassified += 1
                    if reclassified:
                        logger.info(
                            f"Reclassified {reclassified} collocations as "
                            f"discourse markers via LLM discovery"
                        )
            except Exception as exc:
                logger.warning(f"Discourse marker discovery step failed: {exc}")

            # 4b. Pedagogical validation — score and filter
            try:
                validate_collocations(rows, language_id)
                pre_count = len(rows)
                rows = [r for r in rows if r.get('pedagogical_score', 3) >= MIN_PEDAGOGICAL_SCORE]
                removed = pre_count - len(rows)
                if removed:
                    logger.info(
                        f"LLM validation removed {removed} low-value collocations "
                        f"(score < {MIN_PEDAGOGICAL_SCORE})"
                    )
            except Exception as exc:
                logger.warning(f"Collocation validation step failed: {exc}")

            # 4c. Semantic tagging
            try:
                tag_collocations(rows, language_id)
            except Exception as exc:
                logger.warning(f"Semantic tagging step failed: {exc}")

        # 5. Prepare rows for insert — strip transient keys that aren't
        #    in the corpus_collocations table schema
        insert_keys = {
            'corpus_source_id', 'language_id', 'collocation_text', 'head_word',
            'collocate', 'n_gram_size', 'frequency', 'pmi_score',
            'log_likelihood', 't_score', 'lmi_score', 'collocation_type',
            'pos_pattern', 'extraction_method', 'dependency_relation',
            'tags', 'is_validated',
            # LLM-enriched fields (require corresponding DB columns)
            'pedagogical_score', 'semantic_tags',
        }
        clean_rows = [
            {k: v for k, v in row.items() if k in insert_keys}
            for row in rows
        ]

        # 6. Batch insert in chunks of 500
        for i in range(0, len(clean_rows), 500):
            self.db.table('corpus_collocations').insert(clean_rows[i : i + 500]).execute()

        # 7. Mark source as processed
        self.db.table('corpus_sources').update({
            'processed_at': datetime.now(timezone.utc).isoformat(),
        }).eq('id', corpus_source_id).execute()

        # 8. Optional: run style analysis pipeline
        if analyze_style:
            self._run_style_pipeline(
                raw_text=raw_text,
                corpus_source_id=corpus_source_id,
                language_id=language_id,
                source_title=source_title,
                tokenizer=tokenizer,
                llm_enhance=llm_enhance,
            )

        return corpus_source_id

    def _run_style_pipeline(
        self,
        raw_text: str,
        corpus_source_id: int,
        language_id: int,
        source_title: str = '',
        tokenizer=None,
        llm_enhance: bool = False,
    ) -> int:
        """
        Run style analysis on a corpus source and store the profile.

        When llm_enhance=True, also generates a human-readable narrative
        summary of the style profile via LLM.

        Can be called independently (for existing sources) or from _run_pipeline.
        Returns the style profile row id.
        """
        if tokenizer is None:
            tokenizer = get_tokenizer(language_id)

        style_analyzer = StyleAnalyzer(tokenizer)

        # Try to load reference corpus n-grams for keyness comparison
        reference_ngrams = None
        reference_total_tokens = 0
        reference_source_id = None
        try:
            reference_ngrams, reference_total_tokens, reference_source_id = (
                self._load_reference_corpus(language_id, tokenizer)
            )
        except Exception as exc:
            logger.warning(f"Could not load reference corpus for keyness: {exc}")

        profile = style_analyzer.analyze(
            text=raw_text,
            reference_ngrams=reference_ngrams,
            reference_total_tokens=reference_total_tokens,
        )

        # Upsert the profile (one per corpus source)
        row = {
            'corpus_source_id':      corpus_source_id,
            'language_id':           language_id,
            'raw_frequency_ngrams':  profile['raw_frequency_ngrams'],
            'characteristic_ngrams': profile['characteristic_ngrams'],
            'sentence_structures':   profile['sentence_structures'],
            'syntactic_preferences': profile['syntactic_preferences'],
            'discourse_patterns':    profile['discourse_patterns'],
            'vocabulary_profile':    profile['vocabulary_profile'],
            'total_tokens':          profile['total_tokens'],
            'total_sentences':       profile['total_sentences'],
            'reference_source_id':   reference_source_id,
        }

        # Generate narrative summary via LLM
        if llm_enhance:
            try:
                narrative = generate_narrative(
                    profile=profile,
                    language_id=language_id,
                    source_title=source_title,
                )
                row['narrative'] = narrative
                logger.info(
                    f"Style narrative generated for corpus_source_id={corpus_source_id}"
                )
            except Exception as exc:
                logger.warning(f"Style narrative generation failed: {exc}")

        self.db.table('corpus_style_profiles').upsert(
            row, on_conflict='corpus_source_id'
        ).execute()

        logger.info(
            f"Style profile stored for corpus_source_id={corpus_source_id} "
            f"({profile['total_tokens']:,} tokens)"
        )
        result = (
            self.db.table('corpus_style_profiles')
            .select('id')
            .eq('corpus_source_id', corpus_source_id)
            .single()
            .execute()
        )
        return result.data['id']

    def _load_reference_corpus(
        self,
        language_id: int,
        tokenizer,
    ) -> tuple[dict | None, int, int | None]:
        """
        Load the most recent transcript corpus for this language as a reference
        for keyness computation. Returns (ngrams_by_size, total_tokens, source_id).
        """
        # Find the most recent transcript source for this language
        result = (
            self.db.table('corpus_sources')
            .select('id, raw_text')
            .eq('language_id', language_id)
            .like('source_title', '%transcripts%')
            .order('created_at', desc=True)
            .limit(1)
            .execute()
        )

        if not result.data or not result.data[0].get('raw_text'):
            return None, 0, None

        source = result.data[0]
        analyzer = CorpusAnalyzer(tokenizer)
        ngrams = analyzer.extract_all_ngrams(source['raw_text'], max_n=5)
        total_tokens = sum(ngrams[1].values())

        logger.info(
            f"Loaded reference corpus (source_id={source['id']}, "
            f"{total_tokens:,} tokens) for keyness comparison"
        )
        return ngrams, total_tokens, source['id']
