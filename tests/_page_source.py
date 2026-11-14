"""Rendered page plus the first-party scripts it loads.

Page logic lives in static/js (templates only carry markup and <script src>
tags), so tests that assert on what a page's JavaScript does read both.
"""

import os
import re

_SCRIPT_SRC = re.compile(r'<script\b[^>]*\bsrc="(/static/js/[^"?]+)')


def page_source(client, path):
    """HTML of ``path`` followed by its /static/js scripts, in document order."""
    resp = client.get(path)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    static_root = client.application.static_folder
    parts = [html]
    for src in _SCRIPT_SRC.findall(html):
        file_path = os.path.join(static_root, *src[len('/static/'):].split('/'))
        with open(file_path, encoding='utf-8') as fh:
            parts.append(fh.read())
    return '\n'.join(parts)
