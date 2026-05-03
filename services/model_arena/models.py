"""Data classes for Model Arena runs."""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ArenaConfig:
    language_id: int
    language_name: str
    language_code: str
    judge_model: str
    contestant_models: list[str]
    generation_types: list[str]   # subset of ['prose', 'questions']
    num_trials: int
    model_pricing: dict[str, dict] = field(default_factory=dict)


@dataclass
class ModelOutput:
    model_id: str
    raw_output: str = ''
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_seconds: float = 0.0
    error: Optional[str] = None


@dataclass
class JudgeScores:
    # Prose rubric (1-10)
    naturalness: Optional[float] = None
    vocabulary_appropriateness: Optional[float] = None
    grammar_accuracy: Optional[float] = None
    topic_adherence: Optional[float] = None
    engagement: Optional[float] = None
    length_compliance: Optional[float] = None
    difficulty_calibration: Optional[float] = None
    # Question rubric (1-10)
    question_quality: Optional[float] = None
    distractor_quality: Optional[float] = None
    cognitive_level_match: Optional[float] = None
    answer_correctness: Optional[float] = None
    language_accuracy: Optional[float] = None
    # Free-form
    judge_reasoning: str = ''


@dataclass
class TrialResult:
    trial_num: int
    difficulty: int
    tier: str
    topic_concept: str
    generation_type: str           # 'prose' or 'questions'
    shared_prose: Optional[str] = None  # only set for question-mode trials
    label_to_model: dict[str, str] = field(default_factory=dict)  # 'A' -> model_id
    model_outputs: dict[str, ModelOutput] = field(default_factory=dict)
    judge_scores: dict[str, JudgeScores] = field(default_factory=dict)
    judge_output: ModelOutput = field(default_factory=lambda: ModelOutput(model_id=''))


@dataclass
class ArenaResults:
    config: ArenaConfig
    trials: list[TrialResult] = field(default_factory=list)
    started_at: str = ''
    completed_at: Optional[str] = None
    total_cost_by_model: dict[str, float] = field(default_factory=dict)
    judge_cost: float = 0.0
    aggregate_scores: dict[str, dict[str, float]] = field(default_factory=dict)
    winner_by_category: dict[str, str] = field(default_factory=dict)
    overall_winner: str = ''

    def to_dict(self) -> dict:
        return asdict(self)
