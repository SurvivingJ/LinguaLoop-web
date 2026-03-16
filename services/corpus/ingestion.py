import logging
import re
import httpx
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from services.corpus.tokenizers import get_tokenizer
from services.corpus.analyzer import CorpusAnalyzer
from services.corpus.classifier import CollocationClassifier
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
        tags: list[str]
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
        )

    def ingest_text(
        self,
        text: str,
        title: str,
        language_id: int,
        tags: list[str]
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
        )

    def ingest_author_corpus(
        self,
        author_name: str,
        texts: list[str],
        language_id: int,
        extra_tags: list[str] | None = None
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
        )

    def ingest_transcripts(
        self,
        language_id: int,
        extra_tags: list[str] | None = None
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
    ) -> int:
        """
        Core pipeline: store source -> analyse -> classify -> insert collocations
        -> mark processed.

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

        # 4. Batch insert in chunks of 500
        for i in range(0, len(rows), 500):
            self.db.table('corpus_collocations').insert(rows[i : i + 500]).execute()

        # 5. Mark source as processed
        self.db.table('corpus_sources').update({
            'processed_at': datetime.now(timezone.utc).isoformat(),
        }).eq('id', corpus_source_id).execute()

        return corpus_source_id
