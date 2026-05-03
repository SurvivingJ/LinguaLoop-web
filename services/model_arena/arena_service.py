"""Arena orchestration: runs trials across contestant models and judges blind."""

import json
import logging
import random
from datetime import datetime, timezone
from typing import Callable, Optional

from services.llm_output_cleaner import clean_text, clean_json_response
from services.conversation_generation.categorical_maps import DIFFICULTY_TO_TIER
from services.supabase_factory import get_supabase_admin

from .models import (
    ArenaConfig,
    ArenaResults,
    JudgeScores,
    ModelOutput,
    TrialResult,
)
from .pricing import compute_cost
from .llm_runner import call_model_with_usage
from .judge_prompts import (
    PROSE_DIMENSIONS,
    QUESTION_DIMENSIONS,
    build_prose_judge_prompt,
    build_questions_judge_prompt,
)

logger = logging.getLogger(__name__)

QUESTION_TYPE_CODES = [
    'literal_detail',
    'vocabulary_context',
    'main_idea',
    'supporting_detail',
    'inference',
]

WORD_COUNT_BY_TIER = {
    'T1': (40, 80),
    'T2': (60, 120),
    'T3': (100, 180),
    'T4': (150, 250),
    'T5': (200, 320),
    'T6': (260, 400),
}


class ArenaService:
    def __init__(self, config: ArenaConfig):
        self.config = config
        self.results = ArenaResults(
            config=config,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

    def run(self, stop_check: Optional[Callable[[], bool]] = None) -> ArenaResults:
        stop_check = stop_check or (lambda: False)

        logger.info("=" * 60)
        logger.info("MODEL ARENA — %s", self.config.language_name)
        logger.info("Judge: %s", self.config.judge_model)
        logger.info("Contestants: %s", ', '.join(self.config.contestant_models))
        logger.info("Generation types: %s", ', '.join(self.config.generation_types))
        logger.info("Trials: %d", self.config.num_trials)
        logger.info("=" * 60)

        topics = self._load_topics(self.config.num_trials)
        difficulties = self._spread_difficulties(self.config.num_trials)

        # Build trial schedule. If user picked both prose AND questions, run each as
        # a separate trial type so judging stays focused.
        gen_sequence: list[str] = []
        for gen_type in self.config.generation_types:
            gen_sequence.append(gen_type)
        # Round-robin if multiple types selected
        trial_specs: list[tuple[int, int, str, str]] = []
        for i in range(self.config.num_trials):
            difficulty = difficulties[i]
            tier = DIFFICULTY_TO_TIER.get(difficulty, 'T3')
            topic = topics[i % len(topics)] if topics else f'general topic {i}'
            gen_type = gen_sequence[i % len(gen_sequence)]
            trial_specs.append((difficulty, i + 1, gen_type, topic))
            _ = tier  # tier computed below

        for spec_idx, (difficulty, trial_num, gen_type, topic) in enumerate(trial_specs):
            if stop_check():
                logger.info("Stop requested — aborting before trial %d", trial_num)
                break

            tier = DIFFICULTY_TO_TIER.get(difficulty, 'T3')
            logger.info("")
            logger.info("─── Trial %d/%d: %s | difficulty=%d (%s) | topic=%s ───",
                        trial_num, self.config.num_trials, gen_type, difficulty, tier, topic)

            try:
                if gen_type == 'prose':
                    trial = self._run_prose_trial(trial_num, difficulty, tier, topic, stop_check)
                else:
                    trial = self._run_questions_trial(trial_num, difficulty, tier, topic, stop_check)
                self.results.trials.append(trial)
            except Exception as exc:
                logger.error("Trial %d failed: %s", trial_num, exc, exc_info=True)
                continue

        if not stop_check():
            self._aggregate()

        self.results.completed_at = datetime.now(timezone.utc).isoformat()
        logger.info("")
        logger.info("=" * 60)
        logger.info("ARENA COMPLETE")
        logger.info("Overall winner: %s", self.results.overall_winner or '(none)')
        logger.info("Total cost by model: %s",
                    {k: f"${v:.4f}" for k, v in self.results.total_cost_by_model.items()})
        logger.info("Judge cost: $%.4f", self.results.judge_cost)
        logger.info("=" * 60)

        return self.results

    # ── Trial helpers ──────────────────────────────────────────────────

    def _run_prose_trial(self, trial_num, difficulty, tier, topic, stop_check) -> TrialResult:
        word_min, word_max = WORD_COUNT_BY_TIER.get(tier, (100, 200))
        prompt = self._build_prose_prompt(topic, difficulty, tier, word_min, word_max)

        trial = TrialResult(
            trial_num=trial_num,
            difficulty=difficulty,
            tier=tier,
            topic_concept=topic,
            generation_type='prose',
        )

        # Generate with each contestant
        for model_id in self.config.contestant_models:
            if stop_check():
                break
            output = self._call_contestant(model_id, prompt, temperature=0.9)
            trial.model_outputs[model_id] = output
            logger.info("  %s → %d/%d tok, %.1fs, $%.5f%s",
                        model_id, output.prompt_tokens, output.completion_tokens,
                        output.latency_seconds, output.cost_usd,
                        f" ERROR: {output.error}" if output.error else '')

        if stop_check():
            return trial

        # Judge blind
        labeled = self._shuffle_for_judging(trial)
        judge_prompt = build_prose_judge_prompt(
            language_name=self.config.language_name,
            tier=tier,
            difficulty=difficulty,
            topic_concept=topic,
            word_count_min=word_min,
            word_count_max=word_max,
            labeled_responses=[(label, trial.model_outputs[mid].raw_output) for label, mid in labeled],
        )
        self._invoke_judge(trial, judge_prompt, labeled, dimensions=PROSE_DIMENSIONS)
        return trial

    def _run_questions_trial(self, trial_num, difficulty, tier, topic, stop_check) -> TrialResult:
        word_min, word_max = WORD_COUNT_BY_TIER.get(tier, (100, 200))

        # Step 1: judge model produces the shared prose
        prose_prompt = self._build_prose_prompt(topic, difficulty, tier, word_min, word_max)
        logger.info("  Generating shared prose via judge model (%s)...", self.config.judge_model)
        try:
            content, p_tok, c_tok, latency = call_model_with_usage(
                self.config.judge_model, prose_prompt, temperature=0.9, timeout=120,
            )
            shared_prose = clean_text(content.strip()).cleaned
            judge_pricing = self.config.model_pricing.get(self.config.judge_model, {})
            self.results.judge_cost += compute_cost(p_tok, c_tok, judge_pricing)
        except Exception as exc:
            logger.error("Shared prose generation failed: %s", exc)
            shared_prose = f"[Topic: {topic}]"

        trial = TrialResult(
            trial_num=trial_num,
            difficulty=difficulty,
            tier=tier,
            topic_concept=topic,
            generation_type='questions',
            shared_prose=shared_prose,
        )

        # Step 2: each contestant generates question set on the shared prose
        for model_id in self.config.contestant_models:
            if stop_check():
                break
            q_prompt = self._build_questions_prompt(shared_prose, difficulty, tier)
            output = self._call_contestant(model_id, q_prompt, temperature=0.7)
            trial.model_outputs[model_id] = output
            logger.info("  %s → %d/%d tok, %.1fs, $%.5f%s",
                        model_id, output.prompt_tokens, output.completion_tokens,
                        output.latency_seconds, output.cost_usd,
                        f" ERROR: {output.error}" if output.error else '')

        if stop_check():
            return trial

        # Step 3: judge blind on parsed question sets
        labeled = self._shuffle_for_judging(trial)
        labeled_qsets: list[tuple[str, list[dict]]] = []
        for label, model_id in labeled:
            parsed = self._parse_question_set(trial.model_outputs[model_id].raw_output)
            labeled_qsets.append((label, parsed))

        judge_prompt = build_questions_judge_prompt(
            language_name=self.config.language_name,
            tier=tier,
            difficulty=difficulty,
            shared_prose=shared_prose,
            labeled_question_sets=labeled_qsets,
        )
        self._invoke_judge(trial, judge_prompt, labeled, dimensions=QUESTION_DIMENSIONS)
        return trial

    # ── Contestant + judge calls ───────────────────────────────────────

    def _call_contestant(self, model_id: str, prompt: str, *, temperature: float) -> ModelOutput:
        pricing = self.config.model_pricing.get(model_id, {})
        try:
            content, p_tok, c_tok, latency = call_model_with_usage(
                model_id, prompt, temperature=temperature, timeout=120,
            )
            cost = compute_cost(p_tok, c_tok, pricing)
            return ModelOutput(
                model_id=model_id,
                raw_output=content.strip() if content else '',
                prompt_tokens=p_tok,
                completion_tokens=c_tok,
                cost_usd=cost,
                latency_seconds=latency,
            )
        except Exception as exc:
            return ModelOutput(model_id=model_id, error=str(exc))

    def _invoke_judge(self, trial: TrialResult, judge_prompt: str,
                      labeled: list[tuple[str, str]], *, dimensions: list[str]) -> None:
        logger.info("  Judging via %s...", self.config.judge_model)
        try:
            content, p_tok, c_tok, latency = call_model_with_usage(
                self.config.judge_model, judge_prompt,
                temperature=0.2, timeout=180,
            )
        except Exception as exc:
            logger.error("Judge call failed: %s", exc)
            for _, model_id in labeled:
                trial.judge_scores[model_id] = JudgeScores(judge_reasoning=f"[judge error: {exc}]")
            return

        judge_pricing = self.config.model_pricing.get(self.config.judge_model, {})
        judge_cost = compute_cost(p_tok, c_tok, judge_pricing)
        self.results.judge_cost += judge_cost
        trial.judge_output = ModelOutput(
            model_id=self.config.judge_model,
            raw_output=content,
            prompt_tokens=p_tok,
            completion_tokens=c_tok,
            cost_usd=judge_cost,
            latency_seconds=latency,
        )

        try:
            cleaned = clean_json_response(content)
            data = json.loads(cleaned)
            evaluations = data.get('evaluations', data) or {}
        except Exception as exc:
            logger.error("Failed to parse judge JSON: %s\nRaw: %s", exc, content[:500])
            evaluations = {}

        for label, model_id in labeled:
            scores = evaluations.get(label, {}) if isinstance(evaluations, dict) else {}
            js = JudgeScores()
            for dim in dimensions:
                val = scores.get(dim)
                if val is not None:
                    try:
                        setattr(js, dim, float(val))
                    except (TypeError, ValueError):
                        pass
            js.judge_reasoning = scores.get('reasoning', '') if isinstance(scores, dict) else ''
            trial.judge_scores[model_id] = js
            logger.info("    %s [%s] → %s",
                        label, model_id,
                        ', '.join(f"{d}={getattr(js, d)}" for d in dimensions if getattr(js, d) is not None))

    # ── Aggregation ────────────────────────────────────────────────────

    def _aggregate(self) -> None:
        # Cost totals per model
        cost_totals: dict[str, float] = {m: 0.0 for m in self.config.contestant_models}
        for trial in self.results.trials:
            for model_id, output in trial.model_outputs.items():
                cost_totals[model_id] = cost_totals.get(model_id, 0.0) + output.cost_usd
        self.results.total_cost_by_model = cost_totals

        # Aggregate scores: model_id -> {dimension: avg}
        all_dimensions = PROSE_DIMENSIONS + QUESTION_DIMENSIONS
        aggregate: dict[str, dict[str, float]] = {}
        for model_id in self.config.contestant_models:
            dim_totals: dict[str, list[float]] = {d: [] for d in all_dimensions}
            for trial in self.results.trials:
                js = trial.judge_scores.get(model_id)
                if js is None:
                    continue
                for d in all_dimensions:
                    val = getattr(js, d, None)
                    if val is not None:
                        dim_totals[d].append(val)
            aggregate[model_id] = {
                d: round(sum(vs) / len(vs), 2) for d, vs in dim_totals.items() if vs
            }
        self.results.aggregate_scores = aggregate

        # Winner per dimension
        winners: dict[str, str] = {}
        for d in all_dimensions:
            best_model = ''
            best_score = -1.0
            for model_id, dims in aggregate.items():
                if d in dims and dims[d] > best_score:
                    best_score = dims[d]
                    best_model = model_id
            if best_model:
                winners[d] = best_model
        self.results.winner_by_category = winners

        # Overall winner: highest mean of all available dimensions
        overall_means: dict[str, float] = {}
        for model_id, dims in aggregate.items():
            if dims:
                overall_means[model_id] = sum(dims.values()) / len(dims)
        if overall_means:
            self.results.overall_winner = max(overall_means.items(), key=lambda kv: kv[1])[0]

    # ── Misc helpers ───────────────────────────────────────────────────

    @staticmethod
    def _spread_difficulties(n: int) -> list[int]:
        """Spread `n` trials across difficulty levels 1-9."""
        if n <= 9:
            step = 9 / max(n, 1)
            return [max(1, min(9, round(step * (i + 0.5)))) for i in range(n)]
        # n > 9: cycle through 1-9 then fill remainder evenly
        base = list(range(1, 10))
        out = []
        for i in range(n):
            out.append(base[i % 9])
        return out

    def _load_topics(self, n: int) -> list[str]:
        """Pull `n` random concept_english strings from the topics table."""
        try:
            db = get_supabase_admin()
            res = db.table('topics').select('concept_english').limit(max(n * 3, 30)).execute()
            rows = [r.get('concept_english') for r in (res.data or []) if r.get('concept_english')]
            if not rows:
                return self._fallback_topics(n)
            random.shuffle(rows)
            return rows[:n] if len(rows) >= n else (rows * ((n // len(rows)) + 1))[:n]
        except Exception as exc:
            logger.warning("Failed to load topics from DB: %s — using fallback", exc)
            return self._fallback_topics(n)

    @staticmethod
    def _fallback_topics(n: int) -> list[str]:
        topics = [
            'a busy morning at the local market',
            'a tourist getting lost in a foreign city',
            'preparing a traditional meal',
            'a misunderstanding between neighbours',
            'a child learning to ride a bike',
            'an unexpected rain shower',
            'choosing the right gift',
            'a long-distance phone call from family',
            'the first day at a new job',
            'a quiet evening at the train station',
        ]
        random.shuffle(topics)
        if n <= len(topics):
            return topics[:n]
        return (topics * ((n // len(topics)) + 1))[:n]

    def _shuffle_for_judging(self, trial: TrialResult) -> list[tuple[str, str]]:
        """Return [(label, model_id), …] with labels A, B, C… in shuffled model order."""
        models = list(trial.model_outputs.keys())
        random.shuffle(models)
        labels = [chr(ord('A') + i) for i in range(len(models))]
        labeled = list(zip(labels, models))
        trial.label_to_model = dict(labeled)
        return labeled

    @staticmethod
    def _parse_question_set(raw: str) -> list[dict]:
        """Best-effort parse of a question generator's raw output."""
        if not raw:
            return []
        try:
            cleaned = clean_json_response(raw)
            data = json.loads(cleaned)
        except Exception:
            return [{'question': '[unparseable response]', 'choices': [], 'answer': '', 'type_code': ''}]

        # Normalise common shapes
        if isinstance(data, dict):
            for key in ('questions', 'items', 'data'):
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
            else:
                data = [data]
        if not isinstance(data, list):
            return []

        out = []
        for q in data:
            if not isinstance(q, dict):
                continue
            question = q.get('question') or q.get('Question') or q.get('1') or ''
            choices = q.get('choices') or q.get('Options') or q.get('options') or q.get('2') or []
            answer = q.get('answer') or q.get('Answer') or q.get('3') or ''
            type_code = q.get('type_code') or q.get('type') or ''
            out.append({
                'question': question,
                'choices': choices,
                'answer': answer,
                'type_code': type_code,
            })
        return out

    # ── Prompt builders (mirror production prompts) ────────────────────

    def _build_prose_prompt(self, topic: str, difficulty: int, tier: str,
                            word_min: int, word_max: int) -> str:
        return f"""Generate a natural, engaging prose passage in {self.config.language_name} for language learners.

TOPIC: {topic}
TARGET LEVEL: {tier}
DIFFICULTY: {difficulty}/9
WORD COUNT: {word_min}-{word_max} words

Requirements:
- Write ONLY in {self.config.language_name}
- Use vocabulary and grammar appropriate for complexity tier {tier}
- Create natural, flowing prose suitable for listening comprehension
- Include clear main ideas with supporting details
- Avoid overly complex or technical vocabulary for lower levels
- For higher levels, include nuanced expressions and complex structures

Style:
- Conversational but informative
- Clear paragraph structure
- Varied sentence lengths
- Culturally appropriate content

Return ONLY the prose text, with no additional commentary or formatting.
"""

    def _build_questions_prompt(self, prose: str, difficulty: int, tier: str) -> str:
        types_block = '\n'.join(f"  {i+1}. {tc}" for i, tc in enumerate(QUESTION_TYPE_CODES))
        return f"""Generate {len(QUESTION_TYPE_CODES)} multiple-choice comprehension questions in {self.config.language_name}
for the passage below. Use a different question type for each question, in this order:
{types_block}

Difficulty: {difficulty}/9 (tier {tier}).

PASSAGE:
{prose}

Requirements:
- Write all questions and ALL options ONLY in {self.config.language_name}.
- Each question has exactly 4 options. Exactly one is correct.
- Distractors must be plausible-but-wrong, not obviously wrong.
- Vary cognitive demand across types (literal vs inference etc.).

Return ONLY a valid JSON array (no markdown). Each element:
{{
  "question": "<question text in {self.config.language_name}>",
  "choices": ["<A>", "<B>", "<C>", "<D>"],
  "answer": "<must match one of the choices exactly>",
  "type_code": "<one of: {', '.join(QUESTION_TYPE_CODES)}>"
}}
"""
