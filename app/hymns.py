from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_HYMNS_PATH = Path(__file__).resolve().parent.parent / "data" / "hymns.json"


@lru_cache(maxsize=1)
def _load_hymns() -> list[str]:
    if not _HYMNS_PATH.exists():
        return [""]
    with _HYMNS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [""]


def hymn_title(number: int | None) -> str:
    if not number or number < 1:
        return ""
    hymns = _load_hymns()
    if number >= len(hymns):
        return ""
    return (hymns[number] or "").strip()


def hymn_line(number: int | None) -> str:
    if not number:
        return ""
    title = hymn_title(number)
    if not title:
        return f"#{number}"
    return f"#{number}  {title}"
