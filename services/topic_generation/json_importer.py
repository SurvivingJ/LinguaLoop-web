"""
JSON Topic Importer

Parses JSON files containing topics and converts them to TopicCandidates
for the import pipeline.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .database_client import TopicCandidate

logger = logging.getLogger(__name__)


@dataclass
class JSONTopicEntry:
    """Represents a topic entry from JSON input."""
    topic: str                                  # Required: topic concept in English
    languages: List[str]                        # Required: target language codes
    keywords: List[str] = field(default_factory=list)  # Optional: tags
    lens_code: Optional[str] = None             # Optional: override default lens


class JSONTopicImporter:
    """Parses JSON files and converts entries to TopicCandidates."""

    REQUIRED_FIELDS = ['topic', 'languages']

    def __init__(self, default_lens_code: str = 'cultural'):
        """
        Initialize the importer.

        Args:
            default_lens_code: Default lens code for entries without one
        """
        self.default_lens_code = default_lens_code

    def validate_json(self, file_path: str) -> List[str]:
        """
        Validate JSON file format without parsing fully.

        Args:
            file_path: Path to JSON file

        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        path = Path(file_path)

        # Check file exists
        if not path.exists():
            errors.append(f"File not found: {file_path}")
            return errors

        # Check file extension
        if path.suffix.lower() != '.json':
            errors.append(f"Expected .json file, got: {path.suffix}")

        # Try to parse JSON
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {e}")
            return errors
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
            except Exception as e:
                errors.append(f"Encoding error: {e}")
                return errors

        # Validate structure
        if not isinstance(data, dict):
            errors.append("Root element must be an object with 'topics' array")
            return errors

        if 'topics' not in data:
            errors.append("Missing 'topics' key in root object")
            return errors

        topics = data['topics']
        if not isinstance(topics, list):
            errors.append("'topics' must be an array")
            return errors

        if len(topics) == 0:
            errors.append("'topics' array is empty")
            return errors

        # Validate each entry
        for i, entry in enumerate(topics):
            entry_errors = self._validate_entry(entry, i)
            errors.extend(entry_errors)

        return errors

    def _validate_entry(self, entry: dict, index: int) -> List[str]:
        """Validate a single topic entry."""
        errors = []
        prefix = f"Entry {index}"

        if not isinstance(entry, dict):
            errors.append(f"{prefix}: Must be an object")
            return errors

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in entry:
                errors.append(f"{prefix}: Missing required field '{field}'")

        # Validate topic
        if 'topic' in entry:
            if not isinstance(entry['topic'], str):
                errors.append(f"{prefix}: 'topic' must be a string")
            elif len(entry['topic'].strip()) == 0:
                errors.append(f"{prefix}: 'topic' cannot be empty")

        # Validate languages
        if 'languages' in entry:
            if not isinstance(entry['languages'], list):
                errors.append(f"{prefix}: 'languages' must be an array")
            elif len(entry['languages']) == 0:
                errors.append(f"{prefix}: 'languages' array cannot be empty")
            else:
                for j, lang in enumerate(entry['languages']):
                    if not isinstance(lang, str):
                        errors.append(f"{prefix}: 'languages[{j}]' must be a string")

        # Validate optional fields
        if 'keywords' in entry and entry['keywords'] is not None:
            if not isinstance(entry['keywords'], list):
                errors.append(f"{prefix}: 'keywords' must be an array")

        if 'lens_code' in entry and entry['lens_code'] is not None:
            if not isinstance(entry['lens_code'], str):
                errors.append(f"{prefix}: 'lens_code' must be a string")

        return errors

    def parse_json(self, file_path: str) -> List[JSONTopicEntry]:
        """
        Parse JSON file and return topic entries.

        Args:
            file_path: Path to JSON file

        Returns:
            List of JSONTopicEntry objects

        Raises:
            ValueError: If validation fails
        """
        # Validate first
        errors = self.validate_json(file_path)
        if errors:
            raise ValueError(f"JSON validation failed:\n" + "\n".join(errors))

        # Parse
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)

        entries = []
        for item in data['topics']:
            entry = JSONTopicEntry(
                topic=item['topic'].strip(),
                languages=[lang.strip().lower() for lang in item['languages']],
                keywords=[k.strip() for k in item.get('keywords', []) or []],
                lens_code=item.get('lens_code')
            )
            entries.append(entry)

        logger.info(f"Parsed {len(entries)} topic entries from {file_path}")
        return entries

    def entry_to_candidate(self, entry: JSONTopicEntry) -> TopicCandidate:
        """
        Convert a JSON topic entry to a TopicCandidate.

        Args:
            entry: JSONTopicEntry to convert

        Returns:
            TopicCandidate object
        """
        return TopicCandidate(
            concept=entry.topic,
            lens_code=entry.lens_code or self.default_lens_code,
            keywords=entry.keywords if entry.keywords else []
        )
