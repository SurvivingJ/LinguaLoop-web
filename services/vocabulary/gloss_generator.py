"""
Cross-language gloss generator -- RETIRED hosted path.

This module used to build a "translate this definition" prompt and call an
OpenRouter model to produce a cross-language dim_word_senses row (a definition
of a word written in a language other than the word's own -- e.g. an English
gloss for a Japanese word's Japanese definition).

That prompt's contract was:
    - "a natural {target} definition, not a word-for-word translation"
    - "keep it about the same length as the source definition"

Those two rules fight each other for exactly the words that need a gloss most.
"Natural, same-length definition" is how a plain equivalent word turns into a
paragraph: 緊張 (definition-length ja "a state of tense readiness...") became
a 145-character English paragraph instead of "tension; nervousness" -- 57-94
chars on average for ja->en, against 20-31 chars for ja->ja. This was the
prompt working as instructed, not a model failing to follow it.

Fixing the prompt in place would mean teaching it a definition_level it never
had (today neither level knows which one it is, which is exactly why both
came out as the same prose), and -- the part a prompt tweak can't shortcut --
deciding, per word, whether a clean equivalent exists (緊張 -> "tension") or
the mapping is lossy enough to need a clarifier (気 has no single English
equivalent; a hosted call has no way to tell those apart from a translation
instruction alone). That is the same judgment call this codebase already
keeps out of unattended LLM calls for definition quality -- see
.claude/skills/batch-sense-generation and .claude/skills/test-sense-linking,
both of which have Claude write the definition text in-session rather than
prompt a model for it. Running a second, automated implementation of that
same judgment call is how this codebase repeatedly ends up with one column
written in two formats (see the prompt-template drift and dual-writer notes
this repo's history is full of) -- so rather than patch this prompt a second
time, it is disabled.

Cross-language glosses are now written by Claude Code in-session:
    .claude/skills/cross-language-glosses/SKILL.md
    scripts/export_gloss_worklist.py   (stage 1: export)
    scripts/upload_glosses.py          (stage 3: write, via dim_word_senses
                                         directly -- SenseGenerator._write_two_levels
                                         hardcodes the WORD's own language and
                                         cannot be reused for a gloss row)

See scripts/backfill_gloss_definitions.py for the (also retired) batch driver
that used to call into this module.
"""

import logging

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
}

TASK_NAME = 'vocab_gloss_translation'

_RETIRED_MESSAGE = (
    "gloss_generator's hosted translate-a-definition prompt is retired -- it "
    "produced sentence-length prose for what should be a short equivalent set "
    "(see this module's docstring for why). Cross-language gloss definitions "
    "are now written by Claude Code in-session: run the cross-language-glosses "
    "skill (.claude/skills/cross-language-glosses/SKILL.md), which drives "
    "scripts/export_gloss_worklist.py and scripts/upload_glosses.py."
)


def build_gloss_prompt(*_args, **_kwargs) -> str:
    """Retired. See module docstring. Raises unconditionally."""
    raise NotImplementedError(_RETIRED_MESSAGE)


def translate_definition(*_args, **_kwargs) -> str | None:
    """Retired. See module docstring. Raises unconditionally.

    Kept as a function (rather than deleted) only so
    scripts/backfill_gloss_definitions.py's existing import keeps resolving
    and fails with this message instead of an ImportError.
    """
    raise NotImplementedError(_RETIRED_MESSAGE)
