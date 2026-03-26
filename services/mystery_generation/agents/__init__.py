"""
Mystery Generation Agents

Individual agents for the mystery generation pipeline:
- PlotArchitect: Generates story bible (plot, suspects, clues, solution)
- SceneWriter: Writes prose for each scene in target language
- MysteryQuestionGenerator: Creates MCQs per scene + finale deduction question
- ClueDesigner: Designs clue text revealed on correct answers
"""

from .plot_architect import PlotArchitect
from .scene_writer import SceneWriter
from .question_generator import MysteryQuestionGenerator
from .clue_designer import ClueDesigner

__all__ = [
    'PlotArchitect',
    'SceneWriter',
    'MysteryQuestionGenerator',
    'ClueDesigner',
]
