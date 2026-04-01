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
from services.llm_output_cleaner import clean_text
from ..categorical_maps import get_tier_constraint, get_tier_display, localize_categorical
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

# Per-turn rules in target language to prevent English leaking into context window
PER_TURN_RULES = {
    1: (
        "{persona_prompt}\n\n"
        "对话背景：{context}\n"
        "你的目标：{goal}\n\n"
        "规则：\n"
        "- {lang_instr}\n"
        "- 始终保持{name}的角色。\n"
        "- 每轮对话保持1-4句。\n"
        "- 直接回应对方说的话。\n"
        "- 第一轮之后不要再打招呼或自我介绍。\n"
        "- 在任何情况下都不要切换到其他语言。\n"
        "- 只回复你的对话内容。不要加说话者名字前缀。"
    ),
    2: (
        "{persona_prompt}\n\n"
        "Conversation context: {context}\n"
        "Your goal: {goal}\n\n"
        "RULES:\n"
        "- {lang_instr}\n"
        "- Stay completely in character as {name}.\n"
        "- Keep turns conversational (1-4 sentences).\n"
        "- React directly to what the other person just said.\n"
        "- Do NOT greet or introduce yourself after the first turn.\n"
        "- Do NOT translate or switch to another language under any circumstances.\n"
        "- Respond with ONLY your dialogue line. No speaker name prefix."
    ),
    3: (
        "{persona_prompt}\n\n"
        "会話の背景：{context}\n"
        "あなたの目標：{goal}\n\n"
        "ルール：\n"
        "- {lang_instr}\n"
        "- 常に{name}として振る舞ってください。\n"
        "- 各ターンは1〜4文にしてください。\n"
        "- 相手の発言に直接反応してください。\n"
        "- 最初のターン以降は挨拶や自己紹介をしないでください。\n"
        "- いかなる場合も他の言語に切り替えないでください。\n"
        "- セリフのみを返答してください。話者名は付けないでください。"
    ),
}

# Character reminder templates in target language
REMINDER_TEMPLATES = {
    1: "\n\n[角色提醒：你是{name}。保持角色：{traits}。{lang_instr}]",
    2: "\n\n[CHARACTER REMINDER: You are {name}. Stay in character: {traits}. {lang_instr}]",
    3: "\n\n[キャラクターリマインダー：あなたは{name}です。キャラクターを維持：{traits}。{lang_instr}]",
}

# Default goal fallbacks in target language
DEFAULT_GOALS = {
    1: '进行自然的对话。',
    2: 'Have a natural conversation.',
    3: '自然な会話をしてください。',
}

# Default trait fallbacks in target language
_DEFAULT_TRAIT_LABELS = {
    1: '你既定的性格',
    2: 'your established personality',
    3: 'あなたの確立された性格',
}


# Narrative arc pacing templates (programmatic, no LLM call)
NARRATIVE_ARC_TEMPLATES = {
    1: (
        "节奏：\n"
        "- 第1-{p1_end}轮：建立情境，引出分歧或话题\n"
        "- 第{p2_start}-{p2_end}轮：加深讨论，展示不同立场，自然融入领域词汇\n"
        "- 第{p3_start}-{total}轮：寻求解决、妥协或达成某种结论。不要仓促结束"
    ),
    2: (
        "Pacing:\n"
        "- Turns 1-{p1_end}: Establish the situation, introduce the disagreement or topic\n"
        "- Turns {p2_start}-{p2_end}: Deepen the discussion, show different perspectives, "
        "weave in domain vocabulary naturally\n"
        "- Turns {p3_start}-{total}: Work toward resolution or conclusion. Do not rush the ending"
    ),
    3: (
        "ペーシング：\n"
        "- ターン1-{p1_end}：状況を確立し、意見の相違やテーマを導入する\n"
        "- ターン{p2_start}-{p2_end}：議論を深め、異なる視点を示し、分野の語彙を自然に織り込む\n"
        "- ターン{p3_start}-{total}：解決や結論に向かう。急いで終わらせないこと"
    ),
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
        model: str | None = None,
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

        # Complexity tier + constraint injection
        tier_code = scenario.complexity_tier or 'T3'
        tier_display = get_tier_display(tier_code, language_id)
        tier_constraint = get_tier_constraint(tier_code, language_id)

        # Narrative arc + semantic field + register
        narrative_arc = self._build_narrative_arc(turn_count, language_id)
        semantic_field = ', '.join(scenario.keywords) if scenario.keywords else ''
        register = scenario.required_register or 'informal'
        localized_register = localize_categorical('register', register, language_id)

        default_goal = DEFAULT_GOALS.get(language_id, 'Have a natural conversation.')
        goals = scenario.goals or {}
        goal_a = goals.get('persona_a', default_goal)
        goal_b = goals.get('persona_b', default_goal)

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
            complexity_tier=tier_display,
            complexity_constraint=tier_constraint,
            narrative_arc=narrative_arc,
            semantic_field=semantic_field,
            register=localized_register,
        )

        response_text = self._call_llm(
            prompt=prompt,
            json_mode=True,
            temperature=conv_gen_config.temperature,
            model=model,
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
                'text': clean_text(turn.get('text', '')).cleaned,
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
        model: str | None = None,
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
                language_id, turn_count, model=model,
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
                model=model,
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
        model: str | None = None,
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

        default_goal = DEFAULT_GOALS.get(language_id, 'Have a natural conversation.')
        goals = scenario.goals or {}
        goal_a = goals.get('persona_a', default_goal)
        goal_b = goals.get('persona_b', default_goal)

        system_a = self._build_per_turn_system_prompt(
            persona_a, scenario, goal_a, lang_instr, language_name, language_id,
        )
        system_b = self._build_per_turn_system_prompt(
            persona_b, scenario, goal_b, lang_instr, language_name, language_id,
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
                    active_system, active_persona, lang_instr, language_id,
                )

            text = self._call_llm_with_messages(
                system_prompt=active_system,
                messages=active_messages,
                max_tokens=conv_gen_config.per_turn_max_tokens,
                temperature=conv_gen_config.temperature,
                model=model,
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
        model: str | None = None,
    ) -> str:
        """
        Call the LLM with a full message history.

        Bypasses BaseAgent._call_llm to support the messages parameter,
        but uses the same self.client OpenAI instance.
        """
        full_messages = [{'role': 'system', 'content': system_prompt}] + messages

        response = self.client.chat.completions.create(
            model=model or self.model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return clean_text(response.choices[0].message.content.strip()).cleaned

    def _build_per_turn_system_prompt(
        self,
        persona: Persona,
        scenario: Scenario,
        goal: str,
        lang_instr: str,
        language_name: str,
        language_id: int = 2,
    ) -> str:
        """Build a system prompt for per-turn generation in the target language."""
        template = PER_TURN_RULES.get(language_id, PER_TURN_RULES[2])
        return template.format(
            persona_prompt=persona.system_prompt,
            context=scenario.context_description,
            goal=goal,
            lang_instr=lang_instr,
            name=persona.name,
        )

    @staticmethod
    def _inject_per_turn_reminder(
        system_prompt: str, persona: Persona, lang_instr: str,
        language_id: int = 2,
    ) -> str:
        """Inject a character reminder into the system prompt in the target language."""
        traits = persona.personality.get('traits', [])[:3]
        default_label = _DEFAULT_TRAIT_LABELS.get(language_id, 'your established personality')
        trait_str = ', '.join(traits) if traits else default_label
        template = REMINDER_TEMPLATES.get(language_id, REMINDER_TEMPLATES[2])
        return system_prompt + template.format(
            name=persona.name, traits=trait_str, lang_instr=lang_instr,
        )

    @staticmethod
    def _build_narrative_arc(turn_count: int, language_id: int) -> str:
        """Build a 3-phase pacing guide from the turn count."""
        p1_end = max(1, turn_count // 3)
        p2_start = p1_end + 1
        p2_end = max(p2_start, 2 * turn_count // 3)
        p3_start = p2_end + 1
        template = NARRATIVE_ARC_TEMPLATES.get(language_id, NARRATIVE_ARC_TEMPLATES[2])
        return template.format(
            p1_end=p1_end, p2_start=p2_start, p2_end=p2_end,
            p3_start=p3_start, total=turn_count,
        )

    @staticmethod
    def _strip_speaker_prefix(text: str, name: str) -> str:
        """Remove 'Name: ' prefix if the LLM added one."""
        if text.startswith(f"{name}:"):
            text = text[len(name) + 1:].strip()
        elif text.startswith(f"{name} :"):
            text = text[len(name) + 2:].strip()
        return text
