#!/usr/bin/env python3
"""
Display names for players whose names OCR cannot read consistently (decorative glyphs, emoji).

data/aliases.json (per site):
  [{"tag": "JKRS", "display": "°♡✧Jey✧♡°", "key": "^[o0]?[jl]ey[a-z0-9]{0,3}$"}, ...]
- tag: alliance tag the player is in (matched against the read's alliance text, case-insensitive)
- key: regex searched in the read's letters/digits core (NFKC, alphanumerics only, casefolded)
- raw: optional regex searched in the raw OCR text instead (for glyph names with no letter core)
Every read that matches becomes `display`, so votes agree and the player matches across tabs.
"""
import difflib
import json
import os
import re
import unicodedata

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_cache = None


def _core(name):
    return "".join(ch for ch in unicodedata.normalize("NFKC", name or "") if ch.isalnum()).casefold()


def load():
    global _cache
    if _cache is None:
        path = os.path.join(DATA_DIR, "aliases.json")
        rules = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else []
        _cache = [(r.get("tag", "").upper(), re.compile(r["key"]) if r.get("key") else None,
                   re.compile(r["raw"]) if r.get("raw") else None, r["display"]) for r in rules]
    return _cache


def _tag_in(tag, alliance_text):
    """Tag present at the start of the alliance text, allowing one OCR error."""
    ally = re.sub(r"[^A-Z0-9]", "", (alliance_text or "").upper())[: len(tag) + 4]
    if tag in ally:
        return True
    # one substituted, dropped or extra character ("[JKRS]" read as "UKRS" or "[KRS")
    return any(difflib.SequenceMatcher(None, tag, ally[i:i + n]).ratio() >= 0.75
               for n in (len(tag) - 1, len(tag), len(tag) + 1) for i in range(0, 3))


def apply(name, alliance_text=""):
    if not name:
        return name
    core = _core(name)
    for tag, key, raw, display in load():
        if tag and alliance_text and not _tag_in(tag, alliance_text):   # no alliance line read: name decides
            continue
        if (key and key.search(core)) or (raw and raw.search(name)):
            return display
    return name
