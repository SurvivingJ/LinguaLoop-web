#!/usr/bin/env python3
"""
Base Test Generator - Shared functionality for batch test generation scripts.

This module provides:
- TOPIC_DIFFICULTY_CONFIGS: Topic-difficulty pairings for all languages
- BaseTestGenerator: Abstract base class with shared stats, config generation, and run loop
"""

import os
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict


# Shared topic-difficulty pairings across all batch scripts
TOPIC_DIFFICULTY_CONFIGS = {
    'english': {
        'beginner': [
            ('Daily routines', 1),
            ('Family members', 1),
            ('Basic greetings', 2),
            ('Weather descriptions', 2),
            ('Food and drinks', 3),
            ('Simple shopping', 3),
            ('Colors and numbers', 1),
            ('Transportation basics', 2),
            ('Asking directions', 3)
        ],
        'intermediate': [
            ('Travel planning', 4),
            ('Work and careers', 5),
            ('Health and fitness', 4),
            ('Technology use', 5),
            ('Environmental issues', 6),
            ('Social customs', 6),
            ('Education systems', 4),
            ('Media and news', 5),
            ('Cultural events', 6)
        ],
        'advanced': [
            ('Economic trends', 7),
            ('Political systems', 8),
            ('Scientific research', 7),
            ('Philosophy and ethics', 9),
            ('Global diplomacy', 8),
            ('Art history', 7),
            ('Legal frameworks', 8),
            ('Advanced technology', 9),
            ('Academic discourse', 9)
        ]
    },
    'chinese': {
        'beginner': [
            ('Self introduction', 1),
            ('Family structure', 1),
            ('Daily activities', 2),
            ('Food ordering', 2),
            ('Shopping basics', 3),
            ('Time and dates', 1),
            ('Locations', 2),
            ('Hobbies', 3),
            ('Weather talk', 2)
        ],
        'intermediate': [
            ('Chinese New Year', 4),
            ('Tea culture', 5),
            ('Modern cities', 4),
            ('Family values', 5),
            ('Traditional medicine', 6),
            ('Education system', 6),
            ('Work culture', 4),
            ('Food culture', 5),
            ('Social media', 6)
        ],
        'advanced': [
            ('Economic reform', 7),
            ('Ancient philosophy', 8),
            ('Technology innovation', 7),
            ('Cultural revolution', 9),
            ('Belt and Road', 8),
            ('Classical literature', 7),
            ('Modern governance', 8),
            ('Scientific achievements', 9),
            ('Historical dynasties', 9)
        ]
    },
    'japanese': {
        'beginner': [
            ('Greetings', 1),
            ('Family terms', 1),
            ('Daily life', 2),
            ('Food basics', 2),
            ('Numbers and counting', 3),
            ('Train travel', 1),
            ('School life', 2),
            ('Seasons', 3),
            ('Simple requests', 2)
        ],
        'intermediate': [
            ('Cherry blossoms', 4),
            ('Anime culture', 5),
            ('Tea ceremony', 4),
            ('Martial arts', 5),
            ('Traditional crafts', 6),
            ('Japanese cuisine', 6),
            ('Work etiquette', 4),
            ('Festival traditions', 5),
            ('Modern fashion', 6)
        ],
        'advanced': [
            ('Buddhism influence', 7),
            ('Corporate culture', 8),
            ('Technology innovation', 7),
            ('Post-war reconstruction', 9),
            ('Constitutional monarchy', 8),
            ('Classical poetry', 7),
            ('Economic miracle', 8),
            ('Architectural evolution', 9),
            ('Geopolitical role', 9)
        ]
    }
}

# Language emoji mapping
LANG_EMOJI = {'english': 'EN', 'chinese': 'CN', 'japanese': 'JP'}


class BaseTestGenerator(ABC):
    """
    Abstract base class for batch test generation.

    Subclasses must implement:
    - generate_test(config): Generate a single test from config
    - on_test_success(test, config): Handle successful generation
    """

    def __init__(self, name: str = "Batch Test Generation"):
        self.name = name
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }

    @abstractmethod
    def generate_test(self, config: Dict) -> bool:
        """
        Generate a single test from configuration.

        Args:
            config: Test configuration dict with language, difficulty, topic, style

        Returns:
            True if successful, False otherwise
        """
        pass

    def generate_test_configs(self, count: int = 250) -> List[Dict]:
        """
        Generate balanced test configurations.

        Distribution: 83 English, 83 Chinese, 84 Japanese
        Each language has balanced beginner/intermediate/advanced split.

        Args:
            count: Maximum number of configs to generate (default 250)

        Returns:
            List of test configuration dictionaries
        """
        configs = []
        TARGETS = {'english': 83, 'chinese': 83, 'japanese': 84}

        for language, target in TARGETS.items():
            per_level = target // 3
            remainder = target % 3

            level_targets = {
                'beginner': per_level + (1 if remainder > 0 else 0),
                'intermediate': per_level + (1 if remainder > 1 else 0),
                'advanced': per_level
            }

            for level in ['beginner', 'intermediate', 'advanced']:
                topic_pairs = TOPIC_DIFFICULTY_CONFIGS[language][level]
                c = 0
                while c < level_targets[level]:
                    pair = topic_pairs[c % len(topic_pairs)]
                    configs.append({
                        'language': language,
                        'difficulty': pair[1],
                        'topic': pair[0],
                        'style': 'conversational'
                    })
                    c += 1

        return configs[:count]

    def run(self, configs: List[Dict], delay: float = 2.0, start_from: int = 0):
        """
        Execute batch generation.

        Args:
            configs: List of test configurations
            delay: Seconds between requests (default 2.0)
            start_from: Index to resume from (default 0)
        """
        self._print_header(configs, delay, start_from)
        self.stats['start_time'] = datetime.now()

        for i, config in enumerate(configs[start_from:], start=start_from + 1):
            self.stats['total'] += 1

            emoji = LANG_EMOJI.get(config['language'], '??')
            print(f"[{i}/{len(configs)}] {emoji} {config['language'].title()} "
                  f"D{config['difficulty']} - {config['topic']}")

            if self.generate_test(config):
                self.stats['success'] += 1
            else:
                self.stats['failed'] += 1

            # Progress summary every 10 tests
            if i % 10 == 0:
                rate = (self.stats['success'] / self.stats['total']) * 100
                print(f"\n  Progress: {self.stats['success']}/{self.stats['total']} ({rate:.1f}%)\n")

            # Rate limiting (skip on last test)
            if delay > 0 and i < len(configs):
                time.sleep(delay)

        self.stats['end_time'] = datetime.now()
        self._print_stats()
        self._save_error_log()

    def _print_header(self, configs: List[Dict], delay: float, start_from: int):
        """Print batch generation header"""
        print("\n" + "=" * 70)
        print(f"  {self.name}")
        print("=" * 70)
        print(f"  Total tests: {len(configs)}")
        print(f"  Starting from: {start_from}")
        print(f"  Delay: {delay}s between requests")
        print("=" * 70 + "\n")

    def _print_stats(self):
        """Print final batch statistics"""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        mins = int(duration // 60)
        secs = int(duration % 60)

        print("\n" + "=" * 70)
        print("  BATCH COMPLETE")
        print("=" * 70)
        print(f"  Total: {self.stats['total']}")
        print(f"  Success: {self.stats['success']}")
        print(f"  Failed: {self.stats['failed']}")
        if self.stats['total'] > 0:
            print(f"  Success rate: {(self.stats['success']/self.stats['total']*100):.1f}%")
            print(f"  Avg time/test: {duration/self.stats['total']:.1f}s")
        print(f"  Duration: {mins}m {secs}s")
        print("=" * 70 + "\n")

    def _save_error_log(self):
        """Save error log to JSON if there were failures"""
        if self.stats['errors']:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = f"batch_errors_{timestamp}.json"
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'summary': {
                        'total_errors': len(self.stats['errors']),
                        'timestamp': datetime.now().isoformat()
                    },
                    'errors': self.stats['errors']
                }, f, indent=2, ensure_ascii=False)
            print(f"Error log saved: {log_file}")

    def record_error(self, config: Dict, error: str):
        """Record an error for later saving"""
        self.stats['errors'].append({
            'config': config,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })

    def print_config_summary(self, configs: List[Dict]):
        """Print summary of test configurations"""
        print(f"Generated {len(configs)} test configurations")
        print(f"  English: {len([c for c in configs if c['language'] == 'english'])}")
        print(f"  Chinese: {len([c for c in configs if c['language'] == 'chinese'])}")
        print(f"  Japanese: {len([c for c in configs if c['language'] == 'japanese'])}")

        # Difficulty distribution
        beginner = len([c for c in configs if c['difficulty'] in [1, 2, 3]])
        intermediate = len([c for c in configs if c['difficulty'] in [4, 5, 6]])
        advanced = len([c for c in configs if c['difficulty'] in [7, 8, 9]])

        print(f"\nDifficulty distribution:")
        print(f"  Beginner (D1-3): {beginner}")
        print(f"  Intermediate (D4-6): {intermediate}")
        print(f"  Advanced (D7-9): {advanced}")
