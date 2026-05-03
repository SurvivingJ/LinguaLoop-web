"""Placeholder-only template renderer.

Substitutes `{name}` tokens whose name is a plain identifier and leaves all
other braces (including JSON example braces like `{"1": ...}`) untouched.
This avoids `str.format()` interpreting literal JSON in prompt templates as
field references.
"""

import re

_PLACEHOLDER_RE = re.compile(r'\{([A-Za-z_][A-Za-z0-9_]*)\}')


def render_template(template: str, **kwargs) -> str:
    def repl(match: re.Match) -> str:
        key = match.group(1)
        if key not in kwargs:
            raise KeyError(key)
        return str(kwargs[key])

    return _PLACEHOLDER_RE.sub(repl, template)
