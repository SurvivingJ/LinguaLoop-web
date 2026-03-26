"""
Mystery Generation Module

Generates murder mystery comprehension series with 5-scene narrative arcs,
MCQ questions, clue reveals, and a deduction finale.
"""

from .config import mystery_gen_config, get_mystery_gen_config
from .orchestrator import MysteryGenerationOrchestrator

__all__ = [
    'mystery_gen_config',
    'get_mystery_gen_config',
    'MysteryGenerationOrchestrator',
]
