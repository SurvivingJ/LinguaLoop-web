"""
Conversation Writer Agent

The core agent that generates multi-turn dialogues between two personas.
Constructs system prompts embedding both personas' profiles and the scenario context,
then generates alternating turns.
"""

import json
import logging
import random
from typing import Dict, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from services.topic_generation.agents.base import BaseAgent
from ..config import conv_gen_config
from ..database_client import Persona, Scenario

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

# Language instructions for conversation generation
LANGUAGE_INSTRUCTIONS = {
    1: '只用中文回答。使用自然的普通话口语。',           # Chinese
    2: 'Respond ONLY in English.',                       # English
    3: '日本語のみで返答してください。自然な口語表現を使ってください。',  # Japanese
}


class ConversationWriter(BaseAgent):
    """Generates multi-turn dialogues between two personas."""

    def __init__(self, api_key: str = None, model: str = None):
        if conv_gen_config.llm_provider == 'ollama':
            super().__init__(
                model=model or conv_gen_config.ollama_model,
                api_key='ollama',
                base_url=conv_gen_config.ollama_base_url,
                name="ConversationWriter",
            )
        else:
            super().__init__(
                model=model or conv_gen_config.conversation_model,
                api_key=api_key or conv_gen_config.openrouter_api_key,
                base_url=OPENROUTER_BASE_URL,
                name="ConversationWriter",
            )

    def generate_conversation(
        self,
        prompt_template: str,
        scenario: Scenario,
        persona_a: Persona,
        persona_b: Persona,
        language_id: int,
        turn_count: int | None = None,
    ) -> List[Dict]:
        """
        Generate a complete multi-turn conversation.

        Args:
            prompt_template: Prompt template with placeholders
            scenario: Scenario object with context and goals
            persona_a: First persona
            persona_b: Second persona
            language_id: Language ID from dim_languages
            turn_count: Number of turns (defaults to config default_turns)

        Returns:
            List of turn dicts: [{"turn": 0, "speaker": "...", "persona_id": 1, "text": "..."}]
        """
        if turn_count is None:
            turn_count = random.randint(
                conv_gen_config.turns_min,
                conv_gen_config.turns_max,
            )

        language_instruction = LANGUAGE_INSTRUCTIONS.get(language_id, 'Respond naturally.')
        language_name = {1: 'Chinese', 2: 'English', 3: 'Japanese'}.get(language_id, 'English')
        cefr_level = scenario.cefr_level or 'B1'

        goals = scenario.goals or {}
        goal_a = goals.get('persona_a', 'Have a natural conversation.')
        goal_b = goals.get('persona_b', 'Have a natural conversation.')

        prompt = prompt_template.format(
            language_instruction=language_instruction,
            context_description=scenario.context_description,
            persona_a_name=persona_a.name,
            persona_a_system_prompt=persona_a.system_prompt,
            persona_b_name=persona_b.name,
            persona_b_system_prompt=persona_b.system_prompt,
            goal_persona_a=goal_a,
            goal_persona_b=goal_b,
            persona_a_id=persona_a.id,
            persona_b_id=persona_b.id,
            turn_count=turn_count,
            language_name=language_name,
            cefr_level=cefr_level,
        )

        response_text = self._call_llm(
            prompt=prompt,
            json_mode=True,
            temperature=conv_gen_config.temperature,
        )

        turns = json.loads(response_text) if isinstance(response_text, str) else response_text

        # Handle both {"turns": [...]} and [...] response formats
        if isinstance(turns, dict):
            turns = turns.get('turns', turns.get('conversation', []))

        if not isinstance(turns, list):
            raise ValueError(f"Expected list of turns, got {type(turns)}")

        # Validate and normalise turn structure
        validated_turns = []
        for i, turn in enumerate(turns):
            validated_turns.append({
                'turn': turn.get('turn', i),
                'speaker': turn.get('speaker', persona_a.name if i % 2 == 0 else persona_b.name),
                'persona_id': turn.get('persona_id', persona_a.id if i % 2 == 0 else persona_b.id),
                'text': turn.get('text', ''),
            })

        logger.info(
            "Generated %d-turn conversation: %s vs %s in scenario '%s'",
            len(validated_turns), persona_a.name, persona_b.name, scenario.title,
        )

        return validated_turns

    def generate_with_persona_reminders(
        self,
        prompt_template: str,
        scenario: Scenario,
        persona_a: Persona,
        persona_b: Persona,
        language_id: int,
        turn_count: int | None = None,
    ) -> List[Dict]:
        """
        Generate a conversation with periodic persona reminders.

        For longer conversations, inserts persona reminder prompts at
        regular intervals to prevent character drift. This uses multi-turn
        LLM calls rather than a single-shot generation.

        Falls back to single-shot for short conversations.
        """
        if turn_count is None:
            turn_count = conv_gen_config.default_turns

        # For short conversations, use single-shot
        if turn_count <= conv_gen_config.persona_reminder_interval * 2:
            return self.generate_conversation(
                prompt_template, scenario, persona_a, persona_b,
                language_id, turn_count,
            )

        # For longer conversations, generate in chunks with reminders
        all_turns = []
        chunk_size = conv_gen_config.persona_reminder_interval
        remaining = turn_count

        while remaining > 0:
            current_chunk = min(chunk_size, remaining)

            # Build context from previous turns for continuity
            context_text = ""
            if all_turns:
                recent = all_turns[-4:]  # Last 4 turns for context
                context_text = "\n\nPrevious conversation:\n" + "\n".join(
                    f"{t['speaker']}: {t['text']}" for t in recent
                )
                context_text += "\n\nContinue the conversation naturally."

            chunk_turns = self.generate_conversation(
                prompt_template=prompt_template,
                scenario=scenario,
                persona_a=persona_a,
                persona_b=persona_b,
                language_id=language_id,
                turn_count=current_chunk,
            )

            # Re-number turns sequentially
            for turn in chunk_turns:
                turn['turn'] = len(all_turns)
                all_turns.append(turn)

            remaining -= current_chunk

        return all_turns[:turn_count]

    # ── Per-turn generation ──────────────────────────────────────────

    def generate_conversation_per_turn(
        self,
        scenario: Scenario,
        persona_a: Persona,
        persona_b: Persona,
        language_id: int,
        turn_count: int | None = None,
    ) -> List[Dict]:
        """
        Generate a conversation by calling the LLM once per turn.

        Each persona gets their own system prompt. The conversation history
        is maintained from each speaker's perspective (their turns as
        'assistant', the other's as 'user'). Persona reminders are injected
        at regular intervals to prevent character drift.

        Returns:
            List of turn dicts (same format as generate_conversation).
        """
        if turn_count is None:
            turn_count = random.randint(
                conv_gen_config.turns_min,
                conv_gen_config.turns_max,
            )

        lang_instr = LANGUAGE_INSTRUCTIONS.get(language_id, 'Respond naturally.')
        language_name = {1: 'Chinese', 2: 'English', 3: 'Japanese'}.get(
            language_id, 'English'
        )

        goals = scenario.goals or {}
        goal_a = goals.get('persona_a', 'Have a natural conversation.')
        goal_b = goals.get('persona_b', 'Have a natural conversation.')

        system_a = self._build_per_turn_system_prompt(
            persona_a, scenario, goal_a, lang_instr, language_name,
        )
        system_b = self._build_per_turn_system_prompt(
            persona_b, scenario, goal_b, lang_instr, language_name,
        )

        # Message histories from each speaker's perspective
        messages_a: List[Dict] = []
        messages_b: List[Dict] = []
        all_turns: List[Dict] = []

        for i in range(turn_count):
            is_a = (i % 2 == 0)
            active_system = system_a if is_a else system_b
            active_persona = persona_a if is_a else persona_b
            active_messages = messages_a if is_a else messages_b

            # Inject persona reminder every N turns
            if i > 0 and i % conv_gen_config.persona_reminder_interval == 0:
                active_system = self._inject_per_turn_reminder(
                    active_system, active_persona, lang_instr,
                )

            text = self._call_llm_with_messages(
                system_prompt=active_system,
                messages=active_messages,
                max_tokens=conv_gen_config.per_turn_max_tokens,
                temperature=conv_gen_config.temperature,
            )

            # Strip any speaker name prefix the LLM might add
            text = self._strip_speaker_prefix(text, active_persona.name)

            # Update both message histories
            messages_a.append({
                'role': 'assistant' if is_a else 'user',
                'content': text,
            })
            messages_b.append({
                'role': 'user' if is_a else 'assistant',
                'content': text,
            })

            all_turns.append({
                'turn': i,
                'speaker': active_persona.name,
                'persona_id': active_persona.id,
                'text': text,
            })

        logger.info(
            "Per-turn generated %d turns: %s vs %s in scenario '%s'",
            len(all_turns), persona_a.name, persona_b.name, scenario.title,
        )
        return all_turns

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _call_llm_with_messages(
        self,
        system_prompt: str,
        messages: List[Dict],
        max_tokens: int = 200,
        temperature: float = 0.85,
    ) -> str:
        """
        Call the LLM with a full message history.

        Bypasses BaseAgent._call_llm to support the messages parameter,
        but uses the same self.client OpenAI instance.
        """
        full_messages = [{'role': 'system', 'content': system_prompt}] + messages

        response = self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content.strip()

    def _build_per_turn_system_prompt(
        self,
        persona: Persona,
        scenario: Scenario,
        goal: str,
        lang_instr: str,
        language_name: str,
    ) -> str:
        """Build a system prompt for per-turn generation."""
        return (
            f"{persona.system_prompt}\n\n"
            f"Conversation context: {scenario.context_description}\n"
            f"Your goal: {goal}\n\n"
            f"RULES:\n"
            f"- {lang_instr}\n"
            f"- Stay completely in character as {persona.name}.\n"
            f"- Keep turns conversational (1-4 sentences).\n"
            f"- React directly to what the other person just said.\n"
            f"- Do NOT greet or introduce yourself after the first turn.\n"
            f"- Do NOT translate or switch to another language under any circumstances.\n"
            f"- Respond with ONLY your dialogue line. No speaker name prefix."
        )

    @staticmethod
    def _inject_per_turn_reminder(
        system_prompt: str, persona: Persona, lang_instr: str,
    ) -> str:
        """Inject a character reminder into the system prompt."""
        traits = persona.personality.get('traits', [])[:3]
        trait_str = ', '.join(traits) if traits else 'your established personality'
        return (
            system_prompt
            + f"\n\n[CHARACTER REMINDER: You are {persona.name}. "
            f"Stay in character: {trait_str}. {lang_instr}]"
        )

    @staticmethod
    def _strip_speaker_prefix(text: str, name: str) -> str:
        """Remove 'Name: ' prefix if the LLM added one."""
        if text.startswith(f"{name}:"):
            text = text[len(name) + 1:].strip()
        elif text.startswith(f"{name} :"):
            text = text[len(name) + 2:].strip()
        return text
