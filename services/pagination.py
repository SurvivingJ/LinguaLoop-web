"""Read every row of a PostgREST select, past the server's row cap.

PostgREST on this project returns at most 1000 rows per request and says
nothing when it cuts a result short. A chunked `.in_()` read whose chunk
matches more rows than that silently loses the rest (e.g. 200 senses can
have 2,500 active exercises). `fetch_all` pages with `.range()` until a
short page comes back.

`make_query` must build a FRESH query each call and give it a total order
(e.g. `.order('id')`), otherwise pages can overlap or skip rows;
postgrest-py's `.range()` mutates the builder, so a query object cannot be
reused across pages.
"""

from __future__ import annotations

from typing import Callable

PAGE_SIZE = 1000


def fetch_all(make_query: Callable[[], object], page_size: int = PAGE_SIZE) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while True:
        page = make_query().range(start, start + page_size - 1).execute().data or []
        rows.extend(page)
        if len(page) < page_size:
            return rows
        start += page_size
