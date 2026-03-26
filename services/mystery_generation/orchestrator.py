"""
Mystery Generation Orchestrator

Coordinates the full mystery generation workflow:
1. PlotArchitect generates story bible
2. SceneWriter generates prose for each scene
3. MysteryQuestionGenerator creates MCQs per scene + finale deduction
4. ClueDesigner creates clue text per scene
5. AudioSynthesizer generates TTS audio (optional)
6. VocabularyExtractionPipeline extracts vocab
7. MysteryDatabaseClient saves everything

Uses per-language models from dim_languages (prose_model, question_model)
and per-language prompt templates from prompt_templates table.
"""

import logging
from typing import Optional, List, Dict
from uuid import uuid4

from .config import mystery_gen_config
from .database_client import MysteryDatabaseClient
from .agents import PlotArchitect, SceneWriter, MysteryQuestionGenerator, ClueDesigner

logger = logging.getLogger(__name__)


class MysteryGenerationOrchestrator:
    """Coordinates the mystery generation pipeline."""

    def __init__(self):
        if not mystery_gen_config.validate():
            raise ValueError("Invalid mystery generation configuration")

        self.db = MysteryDatabaseClient()
        self.plot_architect = PlotArchitect()
        self.scene_writer = SceneWriter()
        self.question_generator = MysteryQuestionGenerator()
        self.clue_designer = ClueDesigner()

        logger.info("MysteryGenerationOrchestrator initialized")

    def generate(
        self,
        language_id: int,
        difficulty: int,
        gen_user_id: str,
        archetype: str = 'alibi_trick',
        target_vocab: Optional[List[str]] = None,
        generate_audio: bool = False,
    ) -> str:
        """
        Generate a complete murder mystery.

        Args:
            language_id: Target language ID (1=Chinese, 2=English, 3=Japanese)
            difficulty: Difficulty level 1-9
            gen_user_id: User ID for the generator
            archetype: Mystery archetype
            target_vocab: Target vocabulary words
            generate_audio: Whether to generate TTS audio

        Returns:
            Mystery ID (UUID string)
        """
        # Get language config (includes prose_model, question_model from dim_languages)
        lang_config = self.db.get_language_config(language_id)
        if not lang_config:
            raise ValueError(f"Unknown language_id: {language_id}")

        language_name = lang_config.get('language_name', 'English')
        language_code = lang_config.get('language_code', 'en')
        prose_model = lang_config.get('prose_model', 'google/gemini-2.0-flash-exp')
        question_model = lang_config.get('question_model', 'google/gemini-2.0-flash-exp')
        cefr_level = mystery_gen_config.difficulty_to_cefr.get(difficulty, 'B1')

        logger.info(
            f"Starting mystery generation: {language_name} {cefr_level} "
            f"(difficulty={difficulty}, archetype={archetype}, "
            f"prose_model={prose_model}, question_model={question_model})"
        )

        # Fetch per-language prompt templates
        templates = self._load_prompt_templates(language_id)

        # Step 1: Generate story bible
        logger.info("Step 1: Generating story bible...")
        story_bible = self.plot_architect.generate(
            language_name=language_name,
            cefr_level=cefr_level,
            archetype=archetype,
            target_vocab=target_vocab,
            model_override=prose_model,
            prompt_template=templates.get('mystery_plot'),
        )

        # Step 2-4: Generate each scene
        scenes = []
        questions_by_scene: Dict[int, List[Dict]] = {}
        clue_texts = []
        previous_summary = ''

        for scene_outline in story_bible['scenes']:
            scene_num = scene_outline['scene_number']
            logger.info(f"Step 2-4: Processing scene {scene_num}...")

            # 2a: Write scene prose
            transcript = self.scene_writer.generate(
                story_bible=story_bible,
                scene_outline=scene_outline,
                language_name=language_name,
                cefr_level=cefr_level,
                previous_summary=previous_summary,
                model_override=prose_model,
                prompt_template=templates.get('mystery_scene'),
            )

            # 2b: Generate questions
            if scene_num < 5:
                questions = self.question_generator.generate_scene_questions(
                    scene_text=transcript,
                    story_bible=story_bible,
                    scene_number=scene_num,
                    language_name=language_name,
                    cefr_level=cefr_level,
                    num_questions=mystery_gen_config.questions_per_scene,
                    model_override=question_model,
                    prompt_template=templates.get('mystery_question'),
                )
            else:
                # Scene 5: comprehension questions + deduction question
                comprehension_qs = self.question_generator.generate_scene_questions(
                    scene_text=transcript,
                    story_bible=story_bible,
                    scene_number=scene_num,
                    language_name=language_name,
                    cefr_level=cefr_level,
                    num_questions=1,
                    model_override=question_model,
                    prompt_template=templates.get('mystery_question'),
                )
                deduction_qs = self.question_generator.generate_deduction_question(
                    story_bible=story_bible,
                    clue_texts=clue_texts,
                    model_override=question_model,
                    prompt_template=templates.get('mystery_deduction'),
                )
                questions = comprehension_qs + deduction_qs

            questions_by_scene[scene_num] = questions

            # 2c: Design clue
            clue_result = self.clue_designer.generate(
                story_bible=story_bible,
                scene_outline=scene_outline,
                previous_clues=clue_texts,
                model_override=prose_model,
                prompt_template=templates.get('mystery_clue'),
            )
            clue_text = clue_result.get('clue_text', '')
            clue_type = clue_result.get('clue_type', scene_outline.get('clue_type', 'evidence'))
            clue_texts.append(clue_text)

            # 2d: Generate audio (optional)
            audio_url = None
            if generate_audio:
                try:
                    from services.test_generation.agents import AudioSynthesizer
                    synth = AudioSynthesizer()
                    audio_url = synth.generate_and_upload(
                        text=transcript,
                        language_code=language_code,
                        slug=f"mystery-{uuid4().hex[:8]}-scene-{scene_num}",
                    )
                except Exception as e:
                    logger.warning(f"Audio generation failed for scene {scene_num}: {e}")

            scenes.append({
                'scene_number': scene_num,
                'title': scene_outline.get('title', f'Scene {scene_num}'),
                'transcript': transcript,
                'audio_url': audio_url,
                'clue_text': clue_text,
                'clue_type': clue_type,
                'target_words': scene_outline.get('vocab_focus'),
            })

            # Build summary for next scene
            previous_summary += f"\nScene {scene_num}: {scene_outline.get('events', '')}"

        # Step 5: Vocabulary extraction (optional)
        vocab_ids = []
        sense_ids = []
        try:
            from services.vocabulary.pipeline import VocabularyExtractionPipeline
            all_text = '\n'.join(s['transcript'] for s in scenes)
            pipeline = VocabularyExtractionPipeline(
                openai_client=self.plot_architect.client,
                db_client=self.db,
            )
            extraction = pipeline.extract_detailed(
                all_text, language_code,
            )
            vocab_ids = [item.get('vocab_id') for item in extraction if item.get('vocab_id')]
            sense_ids = [item.get('sense_id') for item in extraction if item.get('sense_id')]
            logger.info(f"Extracted {len(vocab_ids)} vocab items, {len(sense_ids)} senses")
        except Exception as e:
            logger.warning(f"Vocabulary extraction skipped: {e}")

        # Step 6: Save to database
        logger.info("Step 6: Saving to database...")
        solution = story_bible.get('solution', {})
        mystery_data = {
            'language_id': language_id,
            'difficulty': difficulty,
            'title': story_bible['title'],
            'premise': story_bible['premise'],
            'suspects': story_bible['suspects'],
            'solution_suspect': solution.get('suspect_name', ''),
            'solution_reasoning': solution.get('reasoning', ''),
            'archetype': archetype,
            'target_vocab_ids': vocab_ids,
            'vocab_sense_ids': sense_ids,
            'generation_model': prose_model,
        }

        mystery_id = self.db.save_mystery(
            mystery_data=mystery_data,
            scenes=scenes,
            questions_by_scene=questions_by_scene,
            gen_user_id=gen_user_id,
        )

        # Log stats
        total_questions = sum(len(qs) for qs in questions_by_scene.values())
        logger.info(
            f"Mystery generation complete: id={mystery_id}, "
            f"scenes={len(scenes)}, questions={total_questions}, "
            f"API calls={self._total_api_calls()}"
        )

        return mystery_id

    def _load_prompt_templates(self, language_id: int) -> Dict[str, str]:
        """Load all mystery prompt templates for a language."""
        template_names = [
            'mystery_plot',
            'mystery_scene',
            'mystery_question',
            'mystery_deduction',
            'mystery_clue',
        ]
        templates = {}
        for name in template_names:
            tmpl = self.db.get_prompt_template(name, language_id)
            if tmpl:
                templates[name] = tmpl
                logger.debug(f"Loaded prompt template: {name} for language_id={language_id}")
            else:
                logger.debug(f"No template found for {name}, using agent defaults")
        return templates

    def _total_api_calls(self) -> int:
        return (
            self.plot_architect.api_call_count +
            self.scene_writer.api_call_count +
            self.question_generator.api_call_count +
            self.clue_designer.api_call_count
        )
