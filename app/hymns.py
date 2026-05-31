from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_HYMNS_PATH = _DATA_DIR / "hymns.json"
_CHILDREN_HYMNS_PATH = _DATA_DIR / "children_hymns.json"
_CHILDREN_LYRICS_PATH = _DATA_DIR / "children_hymn_lyrics.json"

HYMN_BOOK_HYMNS = "hymns"
HYMN_BOOK_CHILDREN = "children"

_BOOK_PATHS = {
    HYMN_BOOK_HYMNS: _HYMNS_PATH,
    HYMN_BOOK_CHILDREN: _CHILDREN_HYMNS_PATH,
}


@lru_cache(maxsize=2)
def _load_hymns(book: str = HYMN_BOOK_HYMNS) -> list[str]:
    path = _BOOK_PATHS.get(book, _HYMNS_PATH)
    if not path.exists():
        return [""]
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [""]


def normalize_hymn_book(raw: str | None) -> str:
    book = (raw or HYMN_BOOK_HYMNS).strip().lower()
    return book if book in _BOOK_PATHS else HYMN_BOOK_HYMNS


def hymn_title(number: int | None, book: str = HYMN_BOOK_HYMNS) -> str:
    if not number or number < 1:
        return ""
    hymns = _load_hymns(normalize_hymn_book(book))
    if number >= len(hymns):
        return ""
    return (hymns[number] or "").strip()


def hymn_line(number: int | None, book: str = HYMN_BOOK_HYMNS) -> str:
    if not number:
        return ""
    title = hymn_title(number, book)
    if not title:
        return f"#{number}"
    return f"#{number}  {title}"


def hymn_display(num_raw: str | None, title: str | None, *, book_label: str | None = None) -> str:
    """Build program hymn text from optional number and free-text title."""
    title = (title or "").strip()
    num_raw = (num_raw or "").strip()
    prefix = ""
    if num_raw and title:
        num_part = num_raw if num_raw.startswith("#") else f"#{num_raw}"
        prefix = f"{num_part}  "
    elif num_raw and not title:
        return num_raw if num_raw.startswith("#") else f"#{num_raw}"
    elif not num_raw and not title:
        return ""

    line = prefix + title if title else prefix.rstrip()
    if book_label and line:
        return f"{line} ({book_label})"
    return line


def hymn_book_label(book: str) -> str:
    book = normalize_hymn_book(book)
    if book == HYMN_BOOK_CHILDREN:
        return "Children's Songbook"
    return "Hymns"


@lru_cache(maxsize=1)
def _load_children_lyrics() -> dict[str, str]:
    if not _CHILDREN_LYRICS_PATH.exists():
        return {}
    with _CHILDREN_LYRICS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def parse_hymn_number(num_raw: str | None) -> int | None:
    raw = (num_raw or "").strip().lstrip("#")
    if not raw:
        return None
    try:
        number = int(raw)
    except ValueError:
        return None
    return number if number > 0 else None


def hymn_lyrics(number: int | None, book: str = HYMN_BOOK_CHILDREN) -> str:
    if not number or normalize_hymn_book(book) != HYMN_BOOK_CHILDREN:
        return ""
    return (_load_children_lyrics().get(str(number)) or "").strip()
