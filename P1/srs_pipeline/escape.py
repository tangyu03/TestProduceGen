"""铁律4：字符安全。esc 用于写入期，find_* 用于 Step6 校验期（等效 json.loads 后扫描）。"""
from __future__ import annotations
import re

ARROW_MAP = {"→": "变为", "←": "回到", "↑": "升为", "↓": "降为"}
QUOTE_MAP = {"“": '"', "”": '"', "‘": "'", "’": "'"}
HTML_MAP = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}

_EXTRA_MAP: dict = {}

def register_extra_map(mapping: dict):
    """项目级扩展替换表（如某文档特有的符号→文字约定）。"""
    _EXTRA_MAP.update(mapping)

def esc(s, extra_map: dict | None = None) -> str:
    if s is None:
        return ""
    s = str(s)
    for k, v in HTML_MAP.items():          # & 必须先于 < > 替换
        s = s.replace(k, v)
    table = {**ARROW_MAP, **QUOTE_MAP, **_EXTRA_MAP, **(extra_map or {})}
    for k, v in table.items():
        s = s.replace(k, v)
    return s

FORBIDDEN_CHARS = tuple(ARROW_MAP) + tuple(QUOTE_MAP)
_UNESCAPED = re.compile(r"<|>|&(?!amp;|lt;|gt;)")

def iter_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_strings(k)
            yield from iter_strings(v)
    elif isinstance(obj, (list, tuple)):
        for it in obj:
            yield from iter_strings(it)

def find_forbidden(obj) -> list:
    return [(ch, s[:40]) for s in iter_strings(obj) for ch in FORBIDDEN_CHARS if ch in s]

def find_unescaped(obj) -> list:
    hits = []
    for s in iter_strings(obj):
        m = _UNESCAPED.search(s)
        if m:
            hits.append((m.group(0), s[:40]))
    return hits
