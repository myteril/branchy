from __future__ import annotations

import os
import unicodedata


def get_terminal_width(stream, default: int = 80) -> int:
    try:
        return os.get_terminal_size(stream.fileno()).columns
    except Exception:
        pass
    try:
        return int(os.environ.get("COLUMNS", default))
    except Exception:
        return default


def char_width(ch: str) -> int:
    if unicodedata.category(ch).startswith("M"):
        return 0
    if unicodedata.east_asian_width(ch) in ("F", "W"):
        return 2
    return 1


def str_width(s: str) -> int:
    return sum(char_width(ch) for ch in s)


def truncate(s: str, width: int) -> str:
    if str_width(s) <= width:
        return s
    parts = []
    w = 0
    for ch in s:
        cw = char_width(ch)
        if w + cw > width - 3:
            break
        parts.append(ch)
        w += cw
    return "".join(parts) + "..."


def wrap_text(text: str, width: int):
    if width <= 0:
        return [text]
    lines = []
    cur = []
    w = 0
    for ch in text:
        cw = char_width(ch)
        if cur and w + cw > width:
            lines.append("".join(cur))
            cur = [ch]
            w = cw
        else:
            cur.append(ch)
            w += cw
    if cur:
        lines.append("".join(cur))
    return lines

